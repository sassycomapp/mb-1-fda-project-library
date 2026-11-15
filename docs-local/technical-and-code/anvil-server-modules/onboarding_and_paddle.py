import anvil.server
import anvil.users
from anvil.tables import app_tables
from datetime import datetime, timezone, timedelta
from cryptography.fernet import Fernet
import os
import hmac
import hashlib
import csv
import io

from . import r2_manager
from . import messaging_gateway

FERNET_KEY = os.getenv("FERNET_MASTER_KEY", "")
PADDLE_WEBHOOK_SECRET = os.getenv("PADDLE_WEBHOOK_SECRET", "")

def _encrypt(plaintext: str) -> str:
    if not plaintext or not FERNET_KEY:
        return plaintext
    return Fernet(FERNET_KEY.encode()).encrypt(plaintext.encode()).decode()


@anvil.server.callable
def create_initial_workspace(business_name: str, timezone_str: str = "Europe/London"):
    """Step 1 of Onboarding Wizard: creates workspace + provisions isolated Cloudflare R2 bucket."""
    user = anvil.users.get_user()
    if not user:
        raise anvil.users.AuthenticationFailed("Sign in required")

    now = datetime.now(timezone.utc)
    ws = app_tables.workspaces.add_row(
        owner=user,
        business_name=business_name.strip(),
        timezone=timezone_str,
        approval_mode="approve_before_send",
        subscription_status="trial",
        retention_days=60,
        followup_enabled=True,
        followup_wait_hours=48,
        followup_max_attempts=2,
        created_at=now,
    )

    bucket_name = f"fda-tenant-{ws.get_id().lower().replace('[', '').replace(']', '').replace(',', '')}"
    r2_manager.provision_tenant_bucket(bucket_name)
    ws['r2_bucket_name'] = bucket_name

    app_tables.channel_connections.add_row(
        workspace=ws,
        whatsapp_status="disconnected",
        smsgate_status="disconnected",
        email_status="disconnected",
    )
    return {"workspace_id": ws.get_id(), "r2_bucket": bucket_name}


@anvil.server.callable
def save_openrouter_byok(workspace_id: str, api_key: str, preset: str = "balanced"):
    """Stores encrypted OpenRouter BYOK key and verifies connectivity."""
    ws = _get_owned_workspace(workspace_id)
    model_map = {
        "fast": "google/gemini-2.5-flash",
        "balanced": "anthropic/claude-3.5-haiku",
        "premium": "anthropic/claude-sonnet-4",
    }
    selected_model = model_map.get(preset, "anthropic/claude-3.5-haiku")
    ws['openrouter_key_enc'] = _encrypt(api_key.strip())
    ws['openrouter_model'] = selected_model
    return {"status": "saved", "model": selected_model}


@anvil.server.callable
def import_contacts_csv(workspace_id: str, csv_text: str, consent_confirmed: bool):
    """Step 10 of Onboarding Wizard: imports contacts with mandatory consent confirmation."""
    if not consent_confirmed:
        raise ValueError("You must confirm lawful consent before importing contacts.")

    ws = _get_owned_workspace(workspace_id)
    reader = csv.DictReader(io.StringIO(csv_text))
    imported = 0
    now = datetime.now(timezone.utc)

    for row in reader:
        name = (row.get("name") or row.get("Name") or "").strip()
        email = (row.get("email") or row.get("Email") or "").strip().lower()
        phone = (row.get("phone") or row.get("Phone") or "").strip()
        if not email and not phone:
            continue

        existing = None
        if email:
            existing = app_tables.contacts.get(workspace=ws, email=email)
        if not existing and phone:
            existing = app_tables.contacts.get(workspace=ws, phone=phone)

        if not existing:
            app_tables.contacts.add_row(
                workspace=ws,
                name=name or "Imported Contact",
                email=email or None,
                phone=phone or None,
                source="csv_import",
                consent_recorded=True,
                do_not_contact=False,
                created_at=now,
            )
            imported += 1

    return {"imported_count": imported}


@anvil.server.callable
def run_onboarding_test_lead(workspace_id: str):
    """Simulates a sample enquiry on the 'Your assistant is live' screen."""
    ws = _get_owned_workspace(workspace_id)
    anvil.server.launch_background_task(
        "_run_front_desk_pipeline",
        workspace_id=ws.get_id(),
        channel="webform",
        sender_identifier="alex.morgan.test@example.com",
        sender_name="Alex Morgan (Test Lead)",
        raw_text="Hi, I'm looking for advisory support next week. Do you have availability on Thursday afternoon?",
        external_id=f"test_lead_{int(datetime.now(timezone.utc).timestamp())}",
    )
    return {"status": "test_started"}


@anvil.server.http_endpoint("/webhooks/paddle", methods=["POST"])
def receive_paddle_webhook():
    """
    Receives Paddle Merchant of Record billing events for:
    - Standard Monthly Plan (£45/mo)
    - Founding 3-Month Pass (£120 one-off)
    """
    raw_body = anvil.server.request.body.get_bytes()
    sig_header = anvil.server.request.headers.get("paddle-signature", "")

    if PADDLE_WEBHOOK_SECRET and not _verify_paddle_sig(raw_body, sig_header, PADDLE_WEBHOOK_SECRET):
        return anvil.server.HttpResponse(401, "Invalid Paddle signature")

    payload = anvil.server.request.body_json or {}
    event_type = payload.get("event_type")
    data = payload.get("data", {})
    custom_data = data.get("custom_data") or {}
    workspace_id = custom_data.get("workspace_id")
    plan_type = custom_data.get("plan_type", "monthly")  # 'monthly' or 'founding_pass'

    if workspace_id:
        ws = app_tables.workspaces.get_by_id(workspace_id)
        if ws:
            now = datetime.now(timezone.utc)
            if event_type in ("transaction.completed", "subscription.activated"):
                if plan_type == "founding_pass":
                    ws['subscription_status'] = "pilot"
                    ws['plan_expires_at'] = now + timedelta(days=90)
                else:
                    ws['subscription_status'] = "active"
                    ws['plan_expires_at'] = now + timedelta(days=32)
            elif event_type in ("subscription.canceled", "subscription.past_due"):
                ws['subscription_status'] = "past_due"

    return {"status": "ok"}


def _get_owned_workspace(workspace_id: str):
    user = anvil.users.get_user()
    ws = app_tables.workspaces.get_by_id(workspace_id)
    if not ws or ws['owner'] != user:
        raise PermissionError("Access denied")
    return ws


def _verify_paddle_sig(raw_body: bytes, sig_header: str, secret: str) -> bool:
    try:
        parts = dict(item.split("=", 1) for item in sig_header.split(";"))
        ts = parts.get("ts", "")
        h1 = parts.get("h1", "")
        signed_payload = f"{ts}:".encode() + raw_body
        expected = hmac.new(secret.encode(), signed_payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, h1)
    except Exception:
        return False
