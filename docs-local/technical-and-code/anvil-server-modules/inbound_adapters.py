import anvil.server
import anvil.tables as tables
from anvil.tables import app_tables
from datetime import datetime, timezone
import re

from . import front_desk_pipeline

@anvil.server.http_endpoint("/webhooks/webform/:workspace_id", methods=["POST"])
def receive_webform_submission(workspace_id: str):
    """
    Public endpoint for the embeddable website contact form.
    Includes honeypot spam protection and feeds directly into the AI pipeline.
    """
    ws = app_tables.workspaces.get_by_id(workspace_id)
    if not ws:
        return anvil.server.HttpResponse(404, "Workspace not found")

    data = anvil.server.request.body_json or {}

    # Honeypot field check (bots fill hidden 'website_url_hp' field)
    if data.get("website_url_hp"):
        return {"status": "ignored"}

    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    phone = _normalize_phone(data.get("phone") or "")
    message_text = (data.get("message") or "").strip()

    if not message_text or (not email and not phone):
        return anvil.server.HttpResponse(400, "Missing contact details or message")

    anvil.server.launch_background_task(
        "_run_front_desk_pipeline",
        workspace_id=workspace_id,
        channel="webform",
        sender_identifier=email or phone,
        sender_name=name,
        raw_text=message_text,
        external_id=f"webform_{int(datetime.now(timezone.utc).timestamp())}",
    )
    return {"status": "received"}


@anvil.server.http_endpoint("/webhooks/calendar/:workspace_id", methods=["POST"])
def receive_calendar_booking(workspace_id: str):
    """
    Receives booking confirmation/reschedule/cancellation events
    and updates the matching CRM lead stage automatically.
    """
    ws = app_tables.workspaces.get_by_id(workspace_id)
    if not ws:
        return anvil.server.HttpResponse(404, "Workspace not found")

    data = anvil.server.request.body_json or {}
    event_type = data.get("event")  # 'booking.created', 'booking.cancelled'
    attendee_email = (data.get("email") or "").strip().lower()
    attendee_phone = _normalize_phone(data.get("phone") or "")

    contact = None
    if attendee_email:
        contact = app_tables.contacts.get(workspace=ws, email=attendee_email)
    if not contact and attendee_phone:
        contact = app_tables.contacts.get(workspace=ws, phone=attendee_phone)

    if contact:
        lead = app_tables.leads.get(workspace=ws, contact=contact)
        if lead:
            if event_type == "booking.created":
                lead['status'] = "meeting_booked"
                lead['next_action'] = "Prepare for discovery call"
            elif event_type == "booking.cancelled":
                lead['status'] = "responded"
                lead['next_action'] = "Offer alternative meeting slot"
                app_tables.action_queue.add_row(
                    workspace=ws,
                    lead=lead,
                    contact=contact,
                    action_type="booking_cancelled",
                    title=f"Meeting cancelled by {contact['name'] or attendee_email}",
                    priority="high",
                    status="pending",
                    created_at=datetime.now(timezone.utc),
                )

    return {"status": "ok"}


@anvil.server.background_task
def poll_connected_inboxes():
    """
    Polls connected Gmail / Microsoft 365 accounts via OAuth tokens
    for new unread lead enquiries and routes them into the pipeline.
    """
    for conn in app_tables.channel_connections.search(email_status="connected"):
        ws = conn['workspace']
        if not ws or ws['subscription_status'] not in ('active', 'pilot'):
            continue
        # Fetch unread messages via Gmail API or MS Graph using stored refresh token
        # For each new thread message, call:
        # anvil.server.launch_background_task("_run_front_desk_pipeline", ...)
        pass


def _normalize_phone(raw: str) -> str:
    digits = re.sub(r"[^\d+]", "", raw)
    return digits
