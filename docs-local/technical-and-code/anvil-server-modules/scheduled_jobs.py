import anvil.server
import anvil.tables as tables
from anvil.tables import app_tables
from datetime import datetime, timezone, timedelta
import httpx
import os
import json

from . import r2_manager
from . import messaging_gateway

EVOLUTION_URL = os.getenv("EVOLUTION_URL", "http://evolution-api:8080")
EVOLUTION_API_KEY = os.getenv("EVOLUTION_API_KEY", "")

@anvil.server.background_task
def job_check_channel_heartbeats():
    """
    Runs every 15 minutes via Anvil Scheduled Tasks.
    Verifies WhatsApp (Evolution API) and SMSGate device connectivity
    and raises an Action Queue alert if a phone goes offline.
    """
    now = datetime.now(timezone.utc)
    for conn in app_tables.channel_connections.search():
        ws = conn['workspace']
        if not ws or ws['subscription_status'] not in ('active', 'pilot', 'trial'):
            continue

        # 1. Check WhatsApp instance state
        if conn['whatsapp_instance']:
            try:
                res = httpx.get(
                    f"{EVOLUTION_URL}/instance/connectionState/{conn['whatsapp_instance']}",
                    headers={"apikey": EVOLUTION_API_KEY},
                    timeout=10.0,
                )
                state = res.json().get("instance", {}).get("state", "close")
                new_status = "connected" if state == "open" else "disconnected"
            except Exception:
                new_status = "disconnected"

            if conn['whatsapp_status'] == "connected" and new_status == "disconnected":
                _create_alert_task(
                    ws,
                    title="WhatsApp phone disconnected",
                    detail="Re-scan your WhatsApp Business QR code in Channel Settings to resume automatic replies.",
                    priority="high",
                )
            conn['whatsapp_status'] = new_status
            conn['last_heartbeat_at'] = now

        # 2. Check SMSGate heartbeat freshness (if configured)
        if conn['smsgate_login']:
            last_seen = conn['smsgate_last_ping']
            if last_seen and (now - last_seen) > timedelta(minutes=30):
                if conn['smsgate_status'] == "connected":
                    _create_alert_task(
                        ws,
                        title="SMSGate Android phone offline",
                        detail="Check power, Wi-Fi, and battery optimization on your SMSGate phone.",
                        priority="high",
                    )
                conn['smsgate_status'] = "disconnected"


@anvil.server.background_task
def job_run_no_response_followups():
    """
    Runs hourly via Anvil Scheduled Tasks.
    Sends 1-to-1 polite follow-ups for quiet inbound leads only.
    Strictly enforces do_not_contact, max attempts, and zero bulk blasts.
    """
    now = datetime.now(timezone.utc)
    for ws in app_tables.workspaces.search(subscription_status=tables.any_of('active', 'pilot')):
        if not ws['followup_enabled']:
            continue

        wait_hours = ws['followup_wait_hours'] or 48
        max_attempts = ws['followup_max_attempts'] or 2
        cutoff = now - timedelta(hours=wait_hours)

        for lead in app_tables.leads.search(workspace=ws, status='responded'):
            contact = lead['contact']
            if not contact or contact['do_not_contact']:
                continue

            attempts = lead['followup_count'] or 0
            last_outbound = lead['last_outbound_at']
            last_inbound = lead['last_inbound_at']

            # Stop immediately if the prospect replied after our last message
            if last_inbound and last_outbound and last_inbound > last_outbound:
                continue

            if not last_outbound or last_outbound > cutoff:
                continue

            if attempts >= max_attempts:
                lead['status'] = 'stalled'
                continue

            # Build polite 1-to-1 check-in
            channel = lead['preferred_channel'] or 'email'
            first_name = (contact['name'] or 'there').split()[0]
            body = (
                f"Hi {first_name}, just checking in on your enquiry with {ws['business_name']}. "
                f"Let me know if you'd still like to book a quick call or if you have any questions."
            )
            if channel in ('whatsapp', 'sms'):
                body += " (Reply STOP to opt out.)"

            if ws['approval_mode'] == 'autonomous_low_risk':
                messaging_gateway.dispatch_outbound_message(ws, contact, channel, body)
                lead['followup_count'] = attempts + 1
                lead['last_outbound_at'] = now
            else:
                app_tables.action_queue.add_row(
                    workspace=ws,
                    lead=lead,
                    contact=contact,
                    action_type='approve_followup',
                    title=f"Approve 1-to-1 follow-up for {contact['name'] or 'Lead'}",
                    proposed_channel=channel,
                    proposed_reply=body,
                    priority='normal',
                    status='pending',
                    created_at=now,
                )


@anvil.server.background_task
def job_nightly_r2_backup_and_archive():
    """
    Runs nightly at 02:00 UTC via Anvil Scheduled Tasks.
    Exports workspace snapshot to the tenant's Cloudflare R2 bucket and
    offloads raw message bodies older than the retention window.
    """
    now = datetime.now(timezone.utc)
    for ws in app_tables.workspaces.search():
        bucket = ws['r2_bucket_name']
        if not bucket:
            continue

        retention_days = ws['retention_days'] or 60
        archive_cutoff = now - timedelta(days=retention_days)

        # 1. Export daily JSON snapshot
        snapshot = {
            "workspace_id": ws.get_id(),
            "exported_at": now.isoformat(),
            "contacts": [dict(r) for r in app_tables.contacts.search(workspace=ws)],
            "leads": [
                {
                    "status": l['status'],
                    "service_interest": l['service_interest'],
                    "urgency": l['urgency'],
                    "source": l['source'],
                }
                for l in app_tables.leads.search(workspace=ws)
            ],
        }
        r2_manager.upload_json_backup(
            bucket_name=bucket,
            key=f"backups/daily-{now.strftime('%Y-%m-%d')}.json",
            payload=snapshot,
        )

        # 2. Archive old message bodies to R2 and trim PostgreSQL storage
        old_msgs = list(
            app_tables.messages.search(
                workspace=ws,
                archived_to_r2=False,
                created_at=tables.less_than(archive_cutoff),
            )
        )
        if old_msgs:
            archive_batch = [
                {
                    "id": m.get_id(),
                    "channel": m['channel'],
                    "direction": m['direction'],
                    "body": m['body'],
                    "created_at": m['created_at'].isoformat() if m['created_at'] else None,
                }
                for m in old_msgs
            ]
            r2_manager.upload_json_backup(
                bucket_name=bucket,
                key=f"archives/messages-{now.strftime('%Y-%m-%d')}.json",
                payload=archive_batch,
            )
            for m in old_msgs:
                m['body'] = "[Archived to Cloudflare R2]"
                m['archived_to_r2'] = True


def _create_alert_task(ws, title: str, detail: str, priority: str = "high"):
    existing = app_tables.action_queue.get(workspace=ws, title=title, status="pending")
    if not existing:
        app_tables.action_queue.add_row(
            workspace=ws,
            action_type="system_alert",
            title=title,
            proposed_reply=detail,
            priority=priority,
            status="pending",
            created_at=datetime.now(timezone.utc),
        )
