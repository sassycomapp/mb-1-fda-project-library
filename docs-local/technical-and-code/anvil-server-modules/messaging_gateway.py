import os
import json
import time
import uuid
import httpx
import redis
import anvil.server
import anvil.tables as tables
from anvil.tables import app_tables
from android_sms_gateway import client as sms_client, domain as sms_domain

# Environment configuration from docker-compose.yml
EVOLUTION_URL = os.getenv("EVOLUTION_URL", "http://evolution-api:8080")
EVOLUTION_API_KEY = os.getenv("EVOLUTION_API_KEY", "")
PUBLIC_WEBHOOK_BASE = os.getenv("PUBLIC_WEBHOOK_BASE", "https://app.yourdomain.com")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Debounce window in seconds for multi-bubble WhatsApp/SMS bursts
DEBOUNCE_SECONDS = 12

# Hard anti-spam rate limits (1-to-1 replies & follow-ups only)
MAX_OUTBOUND_PER_HOUR = 40

redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)


# ==============================================================================
# 1. CLIENT ONBOARDING: WHATSAPP (EVOLUTION API) & SMS (SMSGATE)
# ==============================================================================

@anvil.server.callable
def create_whatsapp_instance(workspace_id: str) -> dict:
    """
    Creates an isolated Evolution API instance for a workspace and returns
    the base64 QR code image for the Material 3 onboarding wizard.
    """
    instance_name = f"fda_{workspace_id}"
    headers = {"apikey": EVOLUTION_API_KEY, "Content-Type": "application/json"}

    with httpx.Client(timeout=20.0) as http:
        res = http.post(
            f"{EVOLUTION_URL}/instance/create",
            headers=headers,
            json={
                "instanceName": instance_name,
                "qrcode": True,
                "integration": "WHATSAPP-BAILEYS",
            },
        )
        res.raise_for_status()
        data = res.json()

    return {
        "instance_name": instance_name,
        "qr_base64": data.get("qrcode", {}).get("base64"),
        "status": "awaiting_scan",
    }


@anvil.server.callable
def check_whatsapp_status(workspace_id: str) -> str:
    """Checks whether the workspace's WhatsApp Linked Device is active."""
    instance_name = f"fda_{workspace_id}"
    headers = {"apikey": EVOLUTION_API_KEY}

    with httpx.Client(timeout=10.0) as http:
        res = http.get(
            f"{EVOLUTION_URL}/instance/connectionState/{instance_name}",
            headers=headers,
        )
        if res.status_code != 200:
            return "disconnected"
        state = res.json().get("instance", {}).get("state", "close")
        return "connected" if state == "open" else "disconnected"


@anvil.server.callable
def register_smsgate_device(workspace_id: str, sms_login: str, sms_password: str) -> dict:
    """
    Registers the Anvil HTTP webhook on the client's Android SMSGate app
    (Cloud Server mode) and verifies credentials.
    """
    webhook_url = f"{PUBLIC_WEBHOOK_BASE}/_/api/webhooks/sms/{workspace_id}"
    with sms_client.APIClient(sms_login, sms_password) as c:
        c.register_webhook(
            sms_domain.Webhook(
                id=f"fda_{workspace_id}",
                url=webhook_url,
                event="sms:received",
            )
        )
    return {"status": "connected", "webhook_url": webhook_url}


# ==============================================================================
# 2. HTTP WEBHOOK RECEIVERS (WHATSAPP & SMSGATE)
# ==============================================================================

@anvil.server.http_endpoint("/webhooks/whatsapp", methods=["POST"])
def whatsapp_webhook(**params):
    """Receives incoming WhatsApp webhooks from Evolution API."""
    body = anvil.server.request.body_json
    if not body:
        return anvil.server.HttpResponse(400, "Invalid JSON")

    event = body.get("event")
    instance_name = body.get("instance", "")

    if event == "messages.upsert" and instance_name.startswith("fda_"):
        workspace_id = instance_name.replace("fda_", "", 1)
        msg_data = body.get("data", {})
        key = msg_data.get("key", {})

        # Ignore our own outbound messages and group chats
        remote_jid = key.get("remoteJid", "")
        if key.get("fromMe") or "@g.us" in remote_jid:
            return {"status": "ignored"}

        ext_msg_id = key.get("id", str(uuid.uuid4()))
        sender_phone = remote_jid.split("@")[0]
        message_obj = msg_data.get("message", {})
        text = (
            message_obj.get("conversation")
            or message_obj.get("extendedTextMessage", {}).get("text")
            or ""
        ).strip()

        if text:
            _enqueue_inbound_message(
                workspace_id=workspace_id,
                channel="whatsapp",
                sender=sender_phone,
                external_id=ext_msg_id,
                text=text,
            )

    return {"status": "ok"}


@anvil.server.http_endpoint("/webhooks/sms/:workspace_id", methods=["POST"])
def smsgate_webhook(workspace_id: str, **params):
    """Receives incoming SMS webhooks from a client's Android SMSGate device."""
    body = anvil.server.request.body_json
    if not body:
        return anvil.server.HttpResponse(400, "Invalid JSON")

    if body.get("event") == "sms:received":
        payload = body.get("payload", {})
        sender_phone = payload.get("phoneNumber", "").strip()
        ext_msg_id = payload.get("messageId", str(uuid.uuid4()))
        text = payload.get("message", "").strip()

        if sender_phone and text:
            _enqueue_inbound_message(
                workspace_id=workspace_id,
                channel="sms",
                sender=sender_phone,
                external_id=ext_msg_id,
                text=text,
            )

    return {"status": "ok"}


# ==============================================================================
# 3. 12-SECOND REDIS BURST DEBOUNCER & OPT-OUT GUARDRAIL
# ==============================================================================

def _enqueue_inbound_message(
    workspace_id: str, channel: str, sender: str, external_id: str, text: str
):
    """
    Deduplicates webhook retries, enforces immediate STOP/UNSUBSCRIBE opt-outs,
    and buffers burst messages for 12 seconds before launching the background AI task.
    """
    # 1. Deduplicate webhook retries
    dedup_key = f"dedup:{workspace_id}:{external_id}"
    if not redis_client.set(dedup_key, "1", ex=86400, nx=True):
        return

    # 2. Immediate STOP / UNSUBSCRIBE compliance check (even in approve-before-send mode)
    normalized = text.strip().upper()
    if normalized in {"STOP", "UNSUBSCRIBE", "OPT OUT", "OPTOUT"}:
        _mark_contact_do_not_contact(workspace_id, sender)
        return

    # 3. Buffer burst bubbles into a Redis list and reset the 12-second timer
    buffer_key = f"buf:{workspace_id}:{channel}:{sender}"
    token_key = f"tok:{workspace_id}:{channel}:{sender}"
    batch_token = str(uuid.uuid4())

    pipe = redis_client.pipeline()
    pipe.rpush(buffer_key, text)
    pipe.expire(buffer_key, 300)
    pipe.set(token_key, batch_token, ex=300)
    pipe.execute()

    anvil.server.launch_background_task(
        "process_debounced_enquiry",
        workspace_id,
        channel,
        sender,
        batch_token,
    )


@anvil.server.background_task
def process_debounced_enquiry(
    workspace_id: str, channel: str, sender: str, batch_token: str
):
    """
    Waits DEBOUNCE_SECONDS; if no newer bubble arrived during that window,
    combines all buffered messages and runs the constrained AI front desk pipeline.
    """
    time.sleep(DEBOUNCE_SECONDS)

    buffer_key = f"buf:{workspace_id}:{channel}:{sender}"
    token_key = f"tok:{workspace_id}:{channel}:{sender}"

    # If a newer message updated the token while we were sleeping, let that worker handle it
    if redis_client.get(token_key) != batch_token:
        return

    pipe = redis_client.pipeline()
    pipe.lrange(buffer_key, 0, -1)
    pipe.delete(buffer_key)
    pipe.delete(token_key)
    results = pipe.execute()

    messages = results[0]
    if not messages:
        return

    combined_enquiry = "\n".join(messages)
    _run_front_desk_pipeline(workspace_id, channel, sender, combined_enquiry)


# ==============================================================================
# 4. OPENROUTER BYOK MODEL ROUTER & OUTBOUND DISPATCH
# ==============================================================================

def call_openrouter_byok(
    openrouter_api_key: str,
    model_id: str,
    system_prompt: str,
    user_message: str,
    max_tokens: int = 450,
) -> dict:
    """
    ModelProvider interface using the workspace's encrypted OpenRouter BYOK key.
    Never logs prompt or completion text; returns content and token usage metadata.
    """
    headers = {
        "Authorization": f"Bearer {openrouter_api_key}",
        "HTTP-Referer": PUBLIC_WEBHOOK_BASE,
        "X-Title": "Mybizz Front Desk Assistant",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.3,
    }

    with httpx.Client(timeout=30.0) as http:
        res = http.post(OPENROUTER_API_URL, headers=headers, json=payload)
        res.raise_for_status()
        data = res.json()

    choice = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})
    return {
        "text": choice.strip(),
        "prompt_tokens": usage.get("prompt_tokens", 0),
        "completion_tokens": usage.get("completion_tokens", 0),
        "model": data.get("model", model_id),
    }


def send_channel_reply(
    workspace_id: str,
    channel: str,
    recipient: str,
    reply_text: str,
    sms_creds: dict | None = None,
) -> dict:
    """
    Dispatches an approved 1-to-1 message via Evolution API (WhatsApp) or SMSGate (SMS).
    Enforces strict hourly rate limits to prohibit bulk marketing blasts.
    """
    rate_key = f"rate:{workspace_id}:{channel}"
    current_count = redis_client.incr(rate_key)
    if current_count == 1:
        redis_client.expire(rate_key, 3600)

    if current_count > MAX_OUTBOUND_PER_HOUR:
        raise RuntimeError(
            "Hourly 1-to-1 messaging safety limit reached. Bulk campaigns are not permitted."
        )

    if channel == "whatsapp":
        instance_name = f"fda_{workspace_id}"
        headers = {"apikey": EVOLUTION_API_KEY, "Content-Type": "application/json"}
        with httpx.Client(timeout=15.0) as http:
            res = http.post(
                f"{EVOLUTION_URL}/message/sendText/{instance_name}",
                headers=headers,
                json={"number": recipient, "text": reply_text},
            )
            res.raise_for_status()
            return {"status": "sent", "provider_response": res.json()}

    elif channel == "sms":
        if not sms_creds:
            raise ValueError("Missing SMSGate credentials for workspace.")
        msg = sms_domain.Message(
            phone_numbers=[recipient],
            text_message=sms_domain.TextMessage(text=reply_text),
        )
        with sms_client.APIClient(sms_creds["login"], sms_creds["password"]) as c:
            result = c.send(msg)
            return {"status": "sent", "message_id": getattr(result, "id", None)}

    raise ValueError(f"Unsupported messaging channel: {channel}")


# ==============================================================================
# 5. PLACEHOLDER HOOKS FOR YOUR ANVIL DATA TABLES & WORKFLOW ENGINE
# ==============================================================================

def _mark_contact_do_not_contact(workspace_id: str, phone: str):
    """Sets do_not_contact = True on the matching Contact row in Anvil Data Tables."""
    contact = app_tables.contacts.get(workspace_id=workspace_id, phone=phone)
    if contact:
        contact["do_not_contact"] = True


def _run_front_desk_pipeline(
    workspace_id: str, channel: str, sender: str, combined_enquiry: str
):
    """
    Orchestrates:
    1. Contact lookup/creation & Do-Not-Contact check
    2. Scoped prompt assembly (business profile + services + FAQs + calendar slots)
    3. OpenRouter BYOK call (with automatic fallback to draft-only if key/quota fails)
    4. Storing inbound + draft Message events (never overwriting original enquiry)
    5. Queueing in Action Queue (approve-before-send default) or sending low-risk ack
    """
    # Connect your Anvil Data Table lookups and approval policy logic here
    pass
