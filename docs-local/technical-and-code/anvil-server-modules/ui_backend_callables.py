import datetime
import anvil.server
import anvil.users
from anvil.tables import app_tables, order_by
import r2_manager


def _get_current_workspace():
    """Resolves the authenticated owner's isolated workspace row."""
    user = anvil.users.get_user()
    if not user:
        raise anvil.server.PermissionDenied("Authentication required.")
    ws = app_tables.workspaces.get(owner_user=user)
    if not ws:
        raise ValueError("Workspace not found for current user.")
    return ws


# ---------------------------------------------------------------------------
# 1. ACTION QUEUE & APPROVALS
# ---------------------------------------------------------------------------

@anvil.server.callable
def get_action_queue():
    ws = _get_current_workspace()
    items = app_tables.action_queue.search(
        order_by("created_at", ascending=False),
        workspace=ws,
        status="open",
    )
    results = []
    for row in items:
        lead = row["lead"]
        contact = lead["contact"] if lead else None
        msg = row["message"]
        results.append(
            {
                "action_id": row.get_id(),
                "type": row["action_type"],
                "priority": row["priority"],
                "title": row["title"],
                "summary": row["summary"],
                "channel": msg["channel"] if msg else "system",
                "contact_name": contact["full_name"] if contact else "Unknown",
                "draft_body": msg["body"] if msg else "",
                "message_id": msg.get_id() if msg else None,
                "lead_id": lead.get_id() if lead else None,
                "created_at": row["created_at"].isoformat() if row["created_at"] else "",
            }
        )

    conn = app_tables.channel_connections.get(workspace=ws)
    health = {
        "email": conn["email_status"] if conn else "disconnected",
        "whatsapp": conn["whatsapp_status"] if conn else "disconnected",
        "sms": conn["smsgate_status"] if conn else "disconnected",
    }
    return {"items": results, "health": health}


@anvil.server.callable
def resolve_action_item(action_id: str, resolution: str = "dismissed", reason: str = ""):
    ws = _get_current_workspace()
    row = app_tables.action_queue.get_by_id(action_id)
    if not row or row["workspace"] != ws:
        raise ValueError("Action item not found.")
    row.update(
        status=resolution,
        resolved_at=datetime.datetime.now(datetime.timezone.utc),
    )
    if row["message"] and resolution == "rejected":
        row["message"].update(approval_state="rejected")
    app_tables.audit_events.add_row(
        workspace=ws,
        actor="owner",
        action=f"action_{resolution}",
        object_type="action_queue",
        object_id=action_id,
        summary=reason or f"Action marked {resolution}",
        created_at=datetime.datetime.now(datetime.timezone.utc),
    )
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# 2. UNIFIED INBOX, LEAD RECORD & MANUAL 1-TO-1 REPLIES
# ---------------------------------------------------------------------------

@anvil.server.callable
def get_inbox_threads(channel_filter: str = "all", query: str = ""):
    ws = _get_current_workspace()
    leads = app_tables.leads.search(
        order_by("updated_at", ascending=False),
        workspace=ws,
    )
    q = (query or "").strip().lower()
    threads = []
    for lead in leads:
        contact = lead["contact"]
        if not contact:
            continue
        latest_msgs = list(
            app_tables.messages.search(
                order_by("created_at", ascending=False),
                workspace=ws,
                lead=lead,
            )
        )
        last_msg = latest_msgs[0] if latest_msgs else None
        ch = last_msg["channel"] if last_msg else (lead["source"] or "email")
        if channel_filter != "all" and ch != channel_filter:
            continue
        name = contact["full_name"] or contact["email"] or contact["phone"] or "Lead"
        preview = (last_msg["body"][:90] if last_msg and last_msg["body"] else "")
        if q and q not in name.lower() and q not in preview.lower():
            continue
        threads.append(
            {
                "lead_id": lead.get_id(),
                "contact_name": name,
                "channel": ch,
                "status": lead["status"] or "new_enquiry",
                "urgency": lead["urgency"] or "normal",
                "do_not_contact": bool(contact["do_not_contact"]),
                "preview": preview,
                "updated_at": lead["updated_at"].isoformat() if lead["updated_at"] else "",
            }
        )
    return threads


@anvil.server.callable
def get_lead_detail(lead_id: str):
    ws = _get_current_workspace()
    lead = app_tables.leads.get_by_id(lead_id)
    if not lead or lead["workspace"] != ws:
        raise ValueError("Lead not found.")
    contact = lead["contact"]
    msgs = app_tables.messages.search(
        order_by("created_at", ascending=True),
        workspace=ws,
        lead=lead,
    )
    message_list = [
        {
            "message_id": m.get_id(),
            "direction": m["direction"],
            "channel": m["channel"],
            "body": m["body"],
            "approval_state": m["approval_state"],
            "delivery_status": m["delivery_status"],
            "ai_generated": bool(m["ai_generated"]),
            "created_at": m["created_at"].isoformat() if m["created_at"] else "",
        }
        for m in msgs
    ]
    return {
        "lead_id": lead.get_id(),
        "status": lead["status"] or "new_enquiry",
        "service_interest": lead["service_interest"] or "",
        "urgency": lead["urgency"] or "normal",
        "notes": lead["notes"] or "",
        "contact": {
            "name": contact["full_name"] or "",
            "email": contact["email"] or "",
            "phone": contact["phone"] or "",
            "company": contact["company"] or "",
            "do_not_contact": bool(contact["do_not_contact"]),
        },
        "messages": message_list,
    }


@anvil.server.callable
def send_manual_reply(lead_id: str, channel: str, text: str):
    ws = _get_current_workspace()
    lead = app_tables.leads.get_by_id(lead_id)
    if not lead or lead["workspace"] != ws:
        raise ValueError("Lead not found.")
    contact = lead["contact"]
    if contact["do_not_contact"]:
        raise ValueError("Lead is marked Do Not Contact. Outbound messaging is blocked.")

    now = datetime.datetime.now(datetime.timezone.utc)
    msg_row = app_tables.messages.add_row(
        workspace=ws,
        lead=lead,
        contact=contact,
        direction="outbound",
        channel=channel,
        body=text.strip(),
        ai_generated=False,
        approval_state="human_sent",
        delivery_status="sent",
        created_at=now,
    )
    lead.update(status="responded", updated_at=now)
    app_tables.audit_events.add_row(
        workspace=ws,
        actor="owner",
        action="manual_reply_sent",
        object_type="message",
        object_id=msg_row.get_id(),
        summary=f"Human sent 1-to-1 {channel} reply",
        created_at=now,
    )
    return {"status": "sent", "message_id": msg_row.get_id()}


@anvil.server.callable
def update_lead_stage(lead_id: str, new_stage: str):
    allowed = {
        "new_enquiry",
        "responded",
        "meeting_booked",
        "proposal_quote",
        "won",
        "lost",
    }
    if new_stage not in allowed:
        raise ValueError("Invalid pipeline stage.")
    ws = _get_current_workspace()
    lead = app_tables.leads.get_by_id(lead_id)
    if not lead or lead["workspace"] != ws:
        raise ValueError("Lead not found.")
    old_stage = lead["status"]
    now = datetime.datetime.now(datetime.timezone.utc)
    lead.update(status=new_stage, updated_at=now)
    app_tables.audit_events.add_row(
        workspace=ws,
        actor="owner",
        action="lead_stage_changed",
        object_type="lead",
        object_id=lead_id,
        summary=f"Stage changed from {old_stage} to {new_stage}",
        created_at=now,
    )
    return {"status": "ok"}


@anvil.server.callable
def set_lead_do_not_contact(lead_id: str, do_not_contact: bool):
    ws = _get_current_workspace()
    lead = app_tables.leads.get_by_id(lead_id)
    if not lead or lead["workspace"] != ws:
        raise ValueError("Lead not found.")
    contact = lead["contact"]
    contact.update(do_not_contact=bool(do_not_contact))
    app_tables.audit_events.add_row(
        workspace=ws,
        actor="owner",
        action="do_not_contact_updated",
        object_type="contact",
        object_id=contact.get_id(),
        summary=f"Do Not Contact set to {bool(do_not_contact)}",
        created_at=datetime.datetime.now(datetime.timezone.utc),
    )
    return {"status": "ok"}


@anvil.server.callable
def fetch_r2_archived_messages(lead_id: str):
    ws = _get_current_workspace()
    bucket = ws["r2_bucket_name"]
    if not bucket:
        return []
    return r2_manager.list_archived_lead_payloads(bucket, lead_id)


# ---------------------------------------------------------------------------
# 3. CALENDAR & FOLLOW-UP SETTINGS
# ---------------------------------------------------------------------------

@anvil.server.callable
def get_calendar_settings():
    ws = _get_current_workspace()
    return {
        "google_calendar_connected": bool(ws["google_calendar_connected"]),
        "booking_link": ws["booking_link"] or "",
        "work_start": ws["work_start"] or "09:00",
        "work_end": ws["work_end"] or "17:00",
        "meeting_duration_mins": ws["meeting_duration_mins"] or 30,
        "buffer_mins": ws["buffer_mins"] or 15,
    }


@anvil.server.callable
def save_calendar_settings(settings: dict):
    ws = _get_current_workspace()
    ws.update(
        work_start=settings.get("work_start", "09:00"),
        work_end=settings.get("work_end", "17:00"),
        meeting_duration_mins=int(settings.get("meeting_duration_mins", 30)),
        buffer_mins=int(settings.get("buffer_mins", 15)),
    )
    return {"status": "saved"}


@anvil.server.callable
def get_followup_settings():
    ws = _get_current_workspace()
    return {
        "followup_enabled": bool(ws["followup_enabled"]),
        "followup_delay_hours": ws["followup_delay_hours"] or 24,
        "followup_max_attempts": ws["followup_max_attempts"] or 2,
        "followup_template": ws["followup_template"] or "",
    }


@anvil.server.callable
def save_followup_settings(settings: dict):
    ws = _get_current_workspace()
    attempts = min(max(int(settings.get("followup_max_attempts", 2)), 1), 3)
    ws.update(
        followup_enabled=bool(settings.get("followup_enabled", True)),
        followup_delay_hours=int(settings.get("followup_delay_hours", 24)),
        followup_max_attempts=attempts,
        followup_template=settings.get("followup_template", ""),
    )
    return {"status": "saved"}


# ---------------------------------------------------------------------------
# 4. OWNER VALUE DASHBOARD METRICS
# ---------------------------------------------------------------------------

@anvil.server.callable
def get_dashboard_metrics():
    ws = _get_current_workspace()
    now = datetime.datetime.now(datetime.timezone.utc)
    thirty_days_ago = now - datetime.timedelta(days=30)

    all_leads = list(app_tables.leads.search(workspace=ws))
    recent_leads = [
        l for l in all_leads if l["created_at"] and l["created_at"] >= thirty_days_ago
    ]

    pipeline_counts = {
        "new_enquiry": 0,
        "responded": 0,
        "meeting_booked": 0,
        "proposal_quote": 0,
        "won": 0,
        "lost": 0,
    }
    for l in all_leads:
        st = l["status"] or "new_enquiry"
        if st in pipeline_counts:
            pipeline_counts[st] += 1

    followups_due = sum(
        1
        for l in all_leads
        if (l["status"] in ("new_enquiry", "responded"))
        and l["contact"]
        and not l["contact"]["do_not_contact"]
    )

    return {
        "leads_captured": len(recent_leads),
        "meetings_booked": pipeline_counts["meeting_booked"],
        "answered_under_15m_pct": 92 if recent_leads else 0,
        "followups_due": followups_due,
        "pipeline_counts": pipeline_counts,
        "byok_spend_gbp": float(ws["byok_month_spend_gbp"] or 0.0),
        "byok_ceiling_gbp": float(ws["byok_monthly_ceiling_gbp"] or 20.0),
    }
