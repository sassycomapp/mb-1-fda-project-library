"""
front_desk_pipeline.py
Anvil Server Module for Front Desk Assistant:
- Classifies and extracts structured lead data via OpenRouter BYOK
- Checks deterministic Google Calendar slots
- Creates CRM records (Contact, Lead, Message) without overwriting history
- Populates the Material 3 Action Queue and handles one-click Owner Approval
"""

import json
import datetime as dt
import httpx
import anvil.server
import anvil.secrets
from anvil.tables import app_tables

from messaging_gateway import (
    call_openrouter_byok,
    send_whatsapp_text,
    send_sms_text,
)


def _utc_now():
    return dt.datetime.now(dt.timezone.utc)


def _log_audit(workspace, actor: str, action: str, obj_type: str, obj_id: str, summary: str):
    app_tables.audit_events.add_row(
        workspace=workspace,
        actor=actor,
        action=action,
        object_type=obj_type,
        object_id=str(obj_id),
        summary=summary,
        created_at=_utc_now(),
    )


# ---------------------------------------------------------------------------
# 1. DETERMINISTIC GOOGLE CALENDAR SLOT LOOKUP
# ---------------------------------------------------------------------------

def get_next_available_slots(workspace, days_ahead: int = 3, max_slots: int = 3) -> list[str]:
    """
    Fetches real free/busy windows from Google Calendar using the workspace's
    encrypted refresh token. AI never invents availability.
    """
    refresh_token_enc = workspace["google_refresh_token_enc"]
    if not refresh_token_enc:
        return []

    try:
        refresh_token = anvil.secrets.decrypt_with_key("VAULT_MASTER_KEY", refresh_token_enc)
        client_id = anvil.secrets.get_secret("GOOGLE_CLIENT_ID")
        client_secret = anvil.secrets.get_secret("GOOGLE_CLIENT_SECRET")

        with httpx.Client(timeout=10.0) as http:
            tok_res = http.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
            )
            tok_res.raise_for_status()
            access_token = tok_res.json()["access_token"]

            now = _utc_now()
            time_min = (now + dt.timedelta(hours=2)).isoformat()
            time_max = (now + dt.timedelta(days=days_ahead)).isoformat()
            cal_id = workspace["google_calendar_id"] or "primary"

            fb_res = http.post(
                "https://www.googleapis.com/calendar/v3/freeBusy",
                headers={"Authorization": f"Bearer {access_token}"},
                json={
                    "timeMin": time_min,
                    "timeMax": time_max,
                    "timeZone": workspace["timezone"] or "Europe/London",
                    "items": [{"id": cal_id}],
                },
            )
            fb_res.raise_for_status()
            busy_blocks = fb_res.json()["calendars"][cal_id].get("busy", [])

        # Simple deterministic slot generator (10:00 and 14:00 local business days)
        candidate_slots = []
        for d in range(1, days_ahead + 1):
            day = now.date() + dt.timedelta(days=d)
            if day.weekday() >= 5:  # Skip Saturday/Sunday by default
                continue
            for hour in (10, 14):
                slot_start = dt.datetime(day.year, day.month, day.day, hour, 0, tzinfo=dt.timezone.utc)
                slot_end = slot_start + dt.timedelta(minutes=30)
                is_busy = any(
                    slot_start < dt.datetime.fromisoformat(b["end"].replace("Z", "+00:00"))
                    and slot_end > dt.datetime.fromisoformat(b["start"].replace("Z", "+00:00"))
                    for b in busy_blocks
                )
                if not is_busy:
                    candidate_slots.append(slot_start.strftime("%A %d %b at %H:%M UTC"))
                if len(candidate_slots) >= max_slots:
                    return candidate_slots
        return candidate_slots
    except Exception:
        return []


# ---------------------------------------------------------------------------
# 2. MAIN BACKGROUND AI ENQUIRY PIPELINE
# ---------------------------------------------------------------------------

@anvil.server.background_task
def _run_front_desk_pipeline(workspace_id: str, channel: str, sender: str, combined_text: str):
    """
    Triggered after the 12-second Redis burst buffer settles.
    Creates/updates Contact & Lead, calls OpenRouter BYOK for structured
    classification + draft reply, and routes to Action Queue or auto-send.
    """
    workspace = app_tables.workspaces.get_by_id(workspace_id)
    if not workspace:
        return

    # 1. Find or create Contact (strictly within this workspace)
    if channel == "email":
        contact = app_tables.contacts.get(workspace=workspace, email=sender.lower())
    else:
        contact = app_tables.contacts.get(workspace=workspace, phone=sender)

    if not contact:
        contact = app_tables.contacts.add_row(
            workspace=workspace,
            full_name=sender,
            email=sender.lower() if channel == "email" else None,
            phone=sender if channel != "email" else None,
            source=channel,
            do_not_contact=False,
            created_at=_utc_now(),
        )

    if contact["do_not_contact"]:
        return

    # 2. Find active Lead or create a new one
    lead = app_tables.leads.get(workspace=workspace, contact=contact)
    if not lead:
        lead = app_tables.leads.add_row(
            workspace=workspace,
            contact=contact,
            status="new_enquiry",
            urgency="normal",
            followup_count=0,
            updated_at=_utc_now(),
        )

    # 3. Store immutable inbound message
    inbound_msg = app_tables.messages.add_row(
        workspace=workspace,
        lead=lead,
        contact=contact,
        channel=channel,
        direction="inbound",
        body=combined_text,
        approval_status="received",
        delivery_status="delivered",
        ai_generated=False,
        created_at=_utc_now(),
    )

    # 4. Build tightly scoped context (no RAG bloat, strict safety rules)
    available_slots = get_next_available_slots(workspace)
    booking_link = workspace["booking_link"] or ""

    system_prompt = (
        f"You are the Front Desk Assistant for {workspace['business_name']}. "
        f"Tone of voice: {workspace['tone_of_voice'] or 'warm and professional'}.\n"
        "STRICT RULES:\n"
        "1. Never invent prices, guarantees, legal/financial advice, or delivery dates.\n"
        "2. Never request or process payments, card numbers, or customer bank details.\n"
        "3. Use ONLY the approved services, FAQs, and available calendar slots below.\n"
        "4. Return ONLY valid JSON matching the requested schema.\n\n"
        f"APPROVED SERVICES: {json.dumps(workspace['services_json'] or [])}\n"
        f"APPROVED FAQS: {json.dumps(workspace['faqs_json'] or [])}\n"
        f"AVAILABLE SLOTS: {json.dumps(available_slots)}\n"
        f"BOOKING LINK: {booking_link}"
    )

    user_prompt = (
        f"Inbound {channel} message from {contact['full_name']}:\n"
        f"\"{combined_text}\"\n\n"
        "Respond with valid JSON containing exactly these keys:\n"
        "{\n"
        '  "classification": "new_lead | existing_client | spam | unsupported",\n'
        '  "extracted_name": "string or null",\n'
        '  "company": "string or null",\n'
        '  "service_interest": "string or null",\n'
        '  "urgency": "normal | high",\n'
        '  "requires_custom_pricing_or_commitment": true or false,\n'
        '  "summary": "1-sentence summary of enquiry",\n'
        '  "draft_reply": "ready-to-send reply in owner voice"\n'
        "}"
    )

    try:
        raw_ai = call_openrouter_byok(
            workspace=workspace,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            tier=workspace["model_preset"] or "balanced",
        )
        # Strip markdown fences if model included them
        cleaned = raw_ai.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        result = json.loads(cleaned)
    except Exception as exc:
        # Fail visibly into the Action Queue rather than silently dropping the lead
        app_tables.action_queue.add_row(
            workspace=workspace,
            lead=lead,
            message=inbound_msg,
            task_type="ai_error",
            title=f"AI drafting failed for {contact['full_name']} — manual reply needed",
            priority="high",
            status="open",
            created_at=_utc_now(),
        )
        _log_audit(workspace, "ai_assistant", "ai_pipeline_error", "lead", lead.get_id(), str(exc)[:120])
        return

    # 5. Update Contact & Lead with validated AI extraction
    if result.get("extracted_name") and contact["full_name"] == sender:
        contact["full_name"] = result["extracted_name"]
    if result.get("company") and not contact["company"]:
        contact["company"] = result["company"]

    if result.get("classification") == "spam":
        lead["status"] = "lost_not_fit"
        lead["summary"] = "Classified as spam/irrelevant."
        lead["updated_at"] = _utc_now()
        _log_audit(workspace, "ai_assistant", "classified_spam", "lead", lead.get_id(), "Marked spam")
        return

    lead["service_interest"] = result.get("service_interest") or lead["service_interest"]
    lead["urgency"] = "high" if result.get("urgency") == "high" else "normal"
    lead["summary"] = result.get("summary") or ""
    lead["updated_at"] = _utc_now()

    draft_text = result.get("draft_reply", "").strip()
    if not draft_text:
        return

    # 6. Approval Policy Check (Conservative Default)
    is_low_risk = (
        workspace["approval_mode"] == "autonomous_low_risk"
        and not result.get("requires_custom_pricing_or_commitment", True)
        and lead["urgency"] != "high"
    )

    if is_low_risk and channel in ("whatsapp", "sms"):
        # Auto-send safe acknowledgement/booking reply and record audit trail
        if channel == "whatsapp":
            send_whatsapp_text(workspace_id, sender, draft_text)
        elif channel == "sms":
            send_sms_text(workspace_id, sender, draft_text)

        out_msg = app_tables.messages.add_row(
            workspace=workspace,
            lead=lead,
            contact=contact,
            channel=channel,
            direction="outbound",
            body=draft_text,
            approval_status="auto_sent",
            delivery_status="sent",
            ai_generated=True,
            created_at=_utc_now(),
        )
        lead["status"] = "responded"
        _log_audit(workspace, "ai_assistant", "auto_sent_low_risk_reply", "message", out_msg.get_id(), "Sent low-risk reply")
    else:
        # Queue draft in Action Queue for one-click owner approval
        draft_msg = app_tables.messages.add_row(
            workspace=workspace,
            lead=lead,
            contact=contact,
            channel=channel,
            direction="outbound",
            body=draft_text,
            approval_status="pending_approval",
            delivery_status="queued",
            ai_generated=True,
            created_at=_utc_now(),
        )
        priority = "high" if lead["urgency"] == "high" else "normal"
        app_tables.action_queue.add_row(
            workspace=workspace,
            lead=lead,
            message=draft_msg,
            task_type="urgent_enquiry" if priority == "high" else "approve_reply",
            title=f"Approve {channel.upper()} reply to {contact['full_name']}",
            priority=priority,
            status="open",
            created_at=_utc_now(),
        )
        _log_audit(workspace, "ai_assistant", "draft_queued_for_approval", "message", draft_msg.get_id(), "Queued for owner")


# ---------------------------------------------------------------------------
# 3. ONE-CLICK OWNER APPROVAL ENDPOINT (Called from Material 3 Approval Queue)
# ---------------------------------------------------------------------------

@anvil.server.callable
def approve_and_send_draft(action_item_id: str, final_text: str):
    """
    Called when the owner clicks 'Approve & Send' in the Material 3 Approval Queue.
    Preserves the original AI draft if edited, sends via WhatsApp/SMS, and updates CRM.
    """
    user = anvil.users.get_user()
    if not user:
        raise anvil.server.PermissionDenied("Authentication required.")

    action_item = app_tables.action_queue.get_by_id(action_item_id)
    if not action_item or action_item["workspace"]["owner_email"] != user["email"]:
        raise anvil.server.PermissionDenied("Access denied.")

    workspace = action_item["workspace"]
    draft_msg = action_item["message"]
    lead = action_item["lead"]
    contact = draft_msg["contact"]

    if contact["do_not_contact"]:
        raise ValueError("Contact is marked Do Not Contact.")

    clean_final = final_text.strip()
    channel = draft_msg["channel"]
    recipient = contact["email"] if channel == "email" else contact["phone"]

    # Send on the originating channel
    if channel == "whatsapp":
        send_whatsapp_text(workspace.get_id(), recipient, clean_final)
    elif channel == "sms":
        send_sms_text(workspace.get_id(), recipient, clean_final)

    # Never overwrite the original AI draft if the owner edited it
    if clean_final != draft_msg["body"]:
        draft_msg["approval_status"] = "edited_superseded"
        sent_msg = app_tables.messages.add_row(
            workspace=workspace,
            lead=lead,
            contact=contact,
            channel=channel,
            direction="outbound",
            body=clean_final,
            approval_status="approved_sent",
            delivery_status="sent",
            ai_generated=False,
            created_at=_utc_now(),
        )
    else:
        draft_msg["approval_status"] = "approved_sent"
        draft_msg["delivery_status"] = "sent"
        sent_msg = draft_msg

    # Update Lead status & close Action Queue item
    if lead["status"] == "new_enquiry":
        lead["status"] = "responded"
    lead["next_action"] = "Check for reply"
    lead["next_action_at"] = _utc_now() + dt.timedelta(days=2)
    lead["updated_at"] = _utc_now()

    action_item["status"] = "completed"
    _log_audit(workspace, "owner", "reply_approved_and_sent", "message", sent_msg.get_id(), f"Approved {channel} reply")
    return {"status": "sent"}
