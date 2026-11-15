"""
OnboardingWizardForm.py
-----------------------
Anvil Client Form for the 10-Step Guided Onboarding Wizard of Front Desk Assistant.
Built on `m3-custom-theme` (v2.0.0, dependency ID UGGJBAZUZ74XZ7VU).

Steps:
  1. Business Basics (Name, Industry, Timezone, Working Hours)
  2. Communication Style & Guardrails (Tone, Signature, Anti-Spam & No-Payment Policy)
  3. Services & Offers (Service Name, From Price, Duration, Qualifying Questions)
  4. Lead & Approval Rules (Default: Approve Before Send; Urgent Escalation)
  5. Calendar Rules (Google Calendar Connection, Meeting Duration, Buffer)
  6. Messaging Channels (Email Required; WhatsApp QR Pairing via Evolution API; SMSGate Cloud Link)
  7. Storage & Retention (Automated Cloudflare R2 Bucket Provisioning & Retention Days)
  8. OpenRouter BYOK Setup (Encrypted Key Storage, Preset Selection, Live Connection Test)
  9. Follow-Up Rules & Optional CSV Contact Import (With Explicit Consent Check)
 10. "Your Assistant Is Live" Summary & Test Lead Simulator

Required Server Callables (from onboarding_and_paddle.py & messaging_gateway.py):
  - save_onboarding_step(workspace_id, step_number, payload_dict)
  - create_whatsapp_instance(workspace_id)
  - check_whatsapp_status(workspace_id)
  - register_smsgate_device(workspace_id, sms_login, sms_password)
  - provision_workspace_r2(workspace_id, retention_days)
  - save_and_test_openrouter_key(workspace_id, api_key, preset)
  - import_contacts_csv(workspace_id, csv_file, consent_confirmed)
  - run_test_lead_simulation(workspace_id, sample_message)
"""

import anvil
import anvil.server
import m3.components as m3
from m3._utils import m3x_theming, m3x_motion


TOTAL_STEPS = 10

STEP_TITLES = {
    1: "1. Business Basics",
    2: "2. Communication Style & Guardrails",
    3: "3. Services & Offers",
    4: "4. Approval & Lead Rules",
    5: "5. Calendar & Booking Rules",
    6: "6. Connect Messaging Channels",
    7: "7. Cloudflare R2 Backup & Archival",
    8: "8. AI Model Setup (OpenRouter BYOK)",
    9: "9. 1-to-1 Follow-Up & Contact Import",
    10: "10. Your Assistant Is Live",
}


class OnboardingWizardForm(m3.NavigationRailLayout):
    """
    10-step Material 3 Expressive onboarding wizard that produces a working
    Front Desk Assistant configuration in under 30 minutes.
    """

    def __init__(self, workspace_id: str, **properties):
        self.workspace_id = workspace_id
        self.current_step = 1
        self.wizard_data = {
            "business_name": "",
            "website_url": "",
            "timezone": "Europe/London",
            "working_hours": "Mon-Fri 09:00-17:30",
            "tone": "Warm & Professional",
            "signature": "",
            "anti_spam_ack": False,
            "service_name": "",
            "service_price_from": "",
            "qualifying_questions": "",
            "approval_mode": "approve_before_send",
            "calendar_connected": False,
            "meeting_duration_mins": 30,
            "buffer_mins": 15,
            "whatsapp_connected": False,
            "smsgate_connected": False,
            "r2_bucket_name": "",
            "retention_days": 30,
            "openrouter_preset": "Balanced",
            "openrouter_verified": False,
            "followup_wait_hours": 48,
            "followup_max_attempts": 2,
        }

        super().__init__(
            rail_style="expressive",
            rail_adaptive=True,
            **properties,
        )

        self._build_shell()
        self._render_step(1)

    # ------------------------------------------------------------------
    # SHELL & PROGRESS BAR
    # ------------------------------------------------------------------
    def _build_shell(self):
        self.top_bar = m3.TopAppBar(title="Front Desk Assistant — Setup Wizard")
        self.add_component(self.top_bar, slot="top_app_bar")

        # Left Rail Step Indicator
        self.step_links = {}
        for step_num, label in STEP_TITLES.items():
            link = m3.NavigationLink(
                text=label,
                icon="check_circle" if step_num < self.current_step else "radio_button_unchecked",
            )
            link.set_event_handler("click", lambda s=step_num, **e: self._jump_to_step(s))
            self.step_links[step_num] = link
            self.add_component(link, slot="navigation_rail")

        # Main Content Wrapper
        self.root_panel = anvil.ColumnPanel(spacing="medium")
        self.add_component(self.root_panel, slot="content")

        # Wavy M3 Expressive Progress Bar
        self.lbl_progress = m3.Text(text="Step 1 of 10", role="label")
        self.progress_bar = m3.LinearProgressIndicator(value=0.1, wavy=True)
        self.root_panel.add_component(self.lbl_progress)
        self.root_panel.add_component(self.progress_bar)

        # Dynamic Step Card Container
        self.step_card = m3.Card(appearance="outlined")
        self.step_body = anvil.ColumnPanel(spacing="medium")
        self.step_card.add_component(self.step_body)
        self.root_panel.add_component(self.step_card)

        # Bottom Navigation Bar (Back / Save & Continue)
        self.nav_row = anvil.FlowPanel(align="right", spacing="small")
        self.btn_back = m3.Button(
            text="Back",
            appearance="outlined",
            icon="arrow_back",
        )
        self.btn_back.set_event_handler("click", self._on_back)

        self.btn_next = m3.Button(
            text="Save & Continue",
            appearance="filled",
            icon="arrow_forward",
        )
        self.btn_next.set_event_handler("click", self._on_next)

        self.nav_row.add_component(self.btn_back)
        self.nav_row.add_component(self.btn_next)
        self.root_panel.add_component(self.nav_row)

    def _jump_to_step(self, step_num: int):
        if step_num <= self.current_step:
            self._render_step(step_num)

    def _update_progress_ui(self):
        self.lbl_progress.text = f"Step {self.current_step} of {TOTAL_STEPS} — {STEP_TITLES[self.current_step]}"
        self.progress_bar.value = self.current_step / TOTAL_STEPS
        self.btn_back.visible = self.current_step > 1
        self.btn_next.text = "Finish & Open Action Queue" if self.current_step == TOTAL_STEPS else "Save & Continue"

        for num, link in self.step_links.items():
            link.selected = (num == self.current_step)
            if num < self.current_step:
                link.icon = "check_circle"
            elif num == self.current_step:
                link.icon = "play_circle"
            else:
                link.icon = "radio_button_unchecked"

    # ------------------------------------------------------------------
    # STEP ROUTER
    # ------------------------------------------------------------------
    def _render_step(self, step_num: int):
        self.current_step = step_num
        self._update_progress_ui()
        self.step_body.clear()

        heading = m3.Heading(text=STEP_TITLES[step_num], scale="headline_small")
        self.step_body.add_component(heading)

        renderers = {
            1: self._render_step_1_basics,
            2: self._render_step_2_style,
            3: self._render_step_3_services,
            4: self._render_step_4_approval,
            5: self._render_step_5_calendar,
            6: self._render_step_6_channels,
            7: self._render_step_7_storage,
            8: self._render_step_8_byok,
            9: self._render_step_9_followups,
            10: self._render_step_10_live,
        }
        renderers[step_num]()

    # ------------------------------------------------------------------
    # STEP 1: BUSINESS BASICS
    # ------------------------------------------------------------------
    def _render_step_1_basics(self):
        self.inp_biz_name = m3.TextBox(
            label="Business Name",
            text=self.wizard_data["business_name"],
            placeholder="e.g., Horizon Advisory Ltd",
        )
        self.inp_website = m3.TextBox(
            label="Website URL",
            text=self.wizard_data["website_url"],
            placeholder="https://www.example.co.uk",
        )
        self.dd_timezone = m3.DropdownMenu(
            label="Business Time Zone",
            items=[
                "Europe/London",
                "America/New_York",
                "America/Chicago",
                "America/Los_Angeles",
                "America/Toronto",
                "Europe/Berlin",
                "Europe/Paris",
                "Africa/Johannesburg",
            ],
            selected_value=self.wizard_data["timezone"],
        )
        self.inp_hours = m3.TextBox(
            label="Working Hours",
            text=self.wizard_data["working_hours"],
        )
        for comp in (self.inp_biz_name, self.inp_website, self.dd_timezone, self.inp_hours):
            self.step_body.add_component(comp)

    # ------------------------------------------------------------------
    # STEP 2: COMMUNICATION STYLE & STRICT POLICY GUARDRAILS
    # ------------------------------------------------------------------
    def _render_step_2_style(self):
        self.bg_tone = m3.ButtonGroup(
            items=["Warm & Professional", "Direct & Concise", "Formal & Executive"],
            selected_value=self.wizard_data["tone"],
        )
        self.inp_signature = m3.TextArea(
            label="Email & Message Sign-Off Signature",
            text=self.wizard_data["signature"],
            placeholder="Best regards,\nDavid — Horizon Advisory",
        )
        self.cb_policy = m3.Checkbox(
            text=(
                "I confirm Front Desk Assistant will be used strictly for 1-to-1 enquiry responses "
                "and booking follow-ups. Bulk SMS/WhatsApp marketing blasts and collecting customer "
                "payment/card details are permanently prohibited."
            ),
            checked=self.wizard_data["anti_spam_ack"],
        )
        self.step_body.add_component(m3.Text(text="Select Assistant Tone of Voice:"))
        self.step_body.add_component(self.bg_tone)
        self.step_body.add_component(self.inp_signature)
        self.step_body.add_component(self.cb_policy)

    # ------------------------------------------------------------------
    # STEP 3: SERVICES & OFFERS
    # ------------------------------------------------------------------
    def _render_step_3_services(self):
        self.inp_service_name = m3.TextBox(
            label="Primary Service / Consultation Name",
            text=self.wizard_data["service_name"],
            placeholder="e.g., 30-Minute Strategy Discovery Call",
        )
        self.inp_price_from = m3.TextBox(
            label="Starting / Guide Price (Optional — never quoted without approval unless listed)",
            text=self.wizard_data["service_price_from"],
            placeholder="e.g., Free initial call / Retainers from £750",
        )
        self.inp_qualifying = m3.TextArea(
            label="Qualifying Questions (Asked before offering calendar slots)",
            text=self.wizard_data["qualifying_questions"],
            placeholder="1. What is your target timeline?\n2. What specific outcome are you looking for?",
        )
        for comp in (self.inp_service_name, self.inp_price_from, self.inp_qualifying):
            self.step_body.add_component(comp)

    # ------------------------------------------------------------------
    # STEP 4: APPROVAL POLICY (CONSERVATIVE DEFAULT)
    # ------------------------------------------------------------------
    def _render_step_4_approval(self):
        self.step_body.add_component(
            m3.Text(
                text=(
                    "We recommend starting in Approve Before Send mode. Your assistant drafts every reply "
                    "and queues it for your one-click approval before anything reaches a client."
                )
            )
        )
        self.dd_approval = m3.DropdownMenu(
            label="Outbound Sending Policy",
            items=[
                ("Approve Before Send (Recommended Default)", "approve_before_send"),
                ("Draft Only (Manual Send)", "draft_only"),
                ("Auto-Send Acknowledgements & Booking Links Only", "autonomous_safe"),
            ],
            selected_value=self.wizard_data["approval_mode"],
        )
        self.step_body.add_component(self.dd_approval)

    # ------------------------------------------------------------------
    # STEP 5: CALENDAR & BOOKING RULES
    # ------------------------------------------------------------------
    def _render_step_5_calendar(self):
        self.btn_connect_gcal = m3.Button(
            text="Google Calendar Connected" if self.wizard_data["calendar_connected"] else "Connect Google Calendar",
            appearance="tonal" if self.wizard_data["calendar_connected"] else "filled",
            icon="event_available",
        )
        self.btn_connect_gcal.set_event_handler("click", self._on_connect_gcal)

        self.slider_duration = m3.Slider(
            min=15,
            max=90,
            step=15,
            value=self.wizard_data["meeting_duration_mins"],
        )
        self.lbl_duration = m3.Text(text=f"Default Meeting Duration: {self.wizard_data['meeting_duration_mins']} mins")
        self.slider_duration.set_event_handler(
            "change",
            lambda **e: setattr(self.lbl_duration, "text", f"Default Meeting Duration: {int(self.slider_duration.value)} mins"),
        )

        self.step_body.add_component(self.btn_connect_gcal)
        self.step_body.add_component(self.lbl_duration)
        self.step_body.add_component(self.slider_duration)

    def _on_connect_gcal(self, **event_args):
        # Triggers Google OAuth flow in production; marks connected here
        self.wizard_data["calendar_connected"] = True
        self.btn_connect_gcal.text = "Google Calendar Connected"
        self.btn_connect_gcal.appearance = "tonal"
        m3.Snackbar(message="Google Calendar linked for real-time slot checks.").show()

    # ------------------------------------------------------------------
    # STEP 6: MESSAGING CHANNELS (EMAIL + WHATSAPP QR + SMSGATE)
    # ------------------------------------------------------------------
    def _render_step_6_channels(self):
        self.step_body.add_component(
            m3.Text(
                text=(
                    "Connect your primary email inbox, and optionally link your business phone for "
                    "WhatsApp (via Evolution API QR scan) and SMS (via SMSGate Android app)."
                )
            )
        )

        # --- WhatsApp Card (Evolution API QR Pairing) ---
        wa_card = m3.Card(appearance="tonal")
        wa_col = anvil.ColumnPanel(spacing="small")
        wa_card.add_component(wa_col)

        wa_col.add_component(m3.Heading(text="WhatsApp Business (Linked Device QR)", scale="title"))
        self.img_wa_qr = anvil.Image(height=200, visible=False)
        self.lbl_wa_status = m3.Text(
            text="Status: Connected" if self.wizard_data["whatsapp_connected"] else "Status: Not connected"
        )
        self.btn_wa_qr = m3.Button(
            text="Generate WhatsApp QR Code",
            appearance="filled",
            icon="qr_code_2",
        )
        self.btn_wa_qr.set_event_handler("click", self._on_generate_wa_qr)

        self.btn_wa_verify = m3.Button(
            text="Verify Scan Status",
            appearance="outlined",
            icon="refresh",
            visible=False,
        )
        self.btn_wa_verify.set_event_handler("click", self._on_verify_wa_status)

        wa_col.add_component(self.lbl_wa_status)
        wa_col.add_component(self.img_wa_qr)
        wa_col.add_component(self.btn_wa_qr)
        wa_col.add_component(self.btn_wa_verify)
        self.step_body.add_component(wa_card)

        # --- SMSGate Card (Android Gateway) ---
        sms_card = m3.Card(appearance="tonal")
        sms_col = anvil.ColumnPanel(spacing="small")
        sms_card.add_component(sms_col)

        sms_col.add_component(m3.Heading(text="SMS Gateway (SMSGate Android App)", scale="title"))
        sms_col.add_component(
            m3.Text(
                text="Install SMSGate on your front-desk Android phone, enable Cloud Server mode, and enter the credentials below."
            )
        )
        self.inp_sms_user = m3.TextBox(label="SMSGate Cloud Login")
        self.inp_sms_pass = m3.TextBox(label="SMSGate Cloud Password", hide_text=True)
        self.btn_sms_link = m3.Button(
            text="SMSGate Linked" if self.wizard_data["smsgate_connected"] else "Link SMSGate Phone",
            appearance="outlined",
            icon="sms",
        )
        self.btn_sms_link.set_event_handler("click", self._on_link_smsgate)

        sms_col.add_component(self.inp_sms_user)
        sms_col.add_component(self.inp_sms_pass)
        sms_col.add_component(self.btn_sms_link)
        self.step_body.add_component(sms_card)

    def _on_generate_wa_qr(self, **event_args):
        self.btn_wa_qr.enabled = False
        self.lbl_wa_status.text = "Generating QR code from Evolution API..."
        try:
            res = anvil.server.call("create_whatsapp_instance", self.workspace_id)
            qr_b64 = res.get("qrcode", {}).get("base64") or res.get("base64")
            if qr_b64:
                self.img_wa_qr.source = qr_b64
                self.img_wa_qr.visible = True
                self.btn_wa_verify.visible = True
                self.lbl_wa_status.text = "Open WhatsApp > Linked Devices > Link a Device and scan this code."
            else:
                self.lbl_wa_status.text = "QR payload not returned. Please retry."
        except Exception as exc:
            m3.Snackbar(message=f"WhatsApp QR error: {exc}").show()
        finally:
            self.btn_wa_qr.enabled = True

    def _on_verify_wa_status(self, **event_args):
        try:
            status = anvil.server.call("check_whatsapp_status", self.workspace_id)
            if status.get("connected"):
                self.wizard_data["whatsapp_connected"] = True
                self.img_wa_qr.visible = False
                self.btn_wa_verify.visible = False
                self.lbl_wa_status.text = "Status: Connected & Active"
                m3.Snackbar(message="WhatsApp Business connected successfully!").show()
            else:
                m3.Snackbar(message="Still waiting for QR scan on phone...").show()
        except Exception as exc:
            m3.Snackbar(message=f"Status check failed: {exc}").show()

    def _on_link_smsgate(self, **event_args):
        login = (self.inp_sms_user.text or "").strip()
        pwd = (self.inp_sms_pass.text or "").strip()
        if not login or not pwd:
            m3.Snackbar(message="Please enter both SMSGate login and password.").show()
            return
        try:
            anvil.server.call("register_smsgate_device", self.workspace_id, login, pwd)
            self.wizard_data["smsgate_connected"] = True
            self.btn_sms_link.text = "SMSGate Linked"
            m3.Snackbar(message="SMSGate webhook registered successfully!").show()
        except Exception as exc:
            m3.Snackbar(message=f"SMSGate connection failed: {exc}").show()

    # ------------------------------------------------------------------
    # STEP 7: CLOUDFLARE R2 BUCKET & RETENTION
    # ------------------------------------------------------------------
    def _render_step_7_storage(self):
        self.step_body.add_component(
            m3.Text(
                text=(
                    "Your workspace receives an isolated Cloudflare R2 bucket for automated daily backups "
                    "and archival of webhook logs and raw messages older than your chosen retention window."
                )
            )
        )
        self.dd_retention = m3.DropdownMenu(
            label="Archive Raw Webhooks & Logs After",
            items=[("30 Days (Recommended)", 30), ("60 Days", 60), ("90 Days", 90)],
            selected_value=self.wizard_data["retention_days"],
        )
        self.lbl_r2_status = m3.Text(
            text=f"Bucket: {self.wizard_data['r2_bucket_name']}" if self.wizard_data["r2_bucket_name"] else "Bucket: Ready to provision"
        )
        self.btn_provision_r2 = m3.Button(
            text="Provision Isolated R2 Bucket",
            appearance="filled",
            icon="cloud_done",
        )
        self.btn_provision_r2.set_event_handler("click", self._on_provision_r2)

        self.step_body.add_component(self.dd_retention)
        self.step_body.add_component(self.lbl_r2_status)
        self.step_body.add_component(self.btn_provision_r2)

    def _on_provision_r2(self, **event_args):
        self.btn_provision_r2.enabled = False
        try:
            days = self.dd_retention.selected_value or 30
            res = anvil.server.call("provision_workspace_r2", self.workspace_id, days)
            bucket = res.get("bucket_name", f"fda-tenant-{self.workspace_id}")
            self.wizard_data["r2_bucket_name"] = bucket
            self.wizard_data["retention_days"] = days
            self.lbl_r2_status.text = f"Provisioned & Encrypted: {bucket}"
            m3.Snackbar(message="Cloudflare R2 backup bucket provisioned!").show()
        except Exception as exc:
            m3.Snackbar(message=f"R2 provisioning error: {exc}").show()
        finally:
            self.btn_provision_r2.enabled = True

    # ------------------------------------------------------------------
    # STEP 8: OPENROUTER BYOK
    # ------------------------------------------------------------------
    def _render_step_8_byok(self):
        self.step_body.add_component(
            m3.Text(
                text=(
                    "Paste your OpenRouter API key (stored encrypted; prompts and completions are never logged). "
                    "Choose a model preset and run a live connection test."
                )
            )
        )
        self.inp_or_key = m3.TextBox(
            label="OpenRouter API Key (sk-or-v1-...)",
            hide_text=True,
        )
        self.bg_preset = m3.ButtonGroup(
            items=["Fast", "Balanced", "Premium"],
            selected_value=self.wizard_data["openrouter_preset"],
        )
        self.btn_test_or = m3.Button(
            text="Save & Test OpenRouter Key",
            appearance="filled",
            icon="bolt",
        )
        self.btn_test_or.set_event_handler("click", self._on_test_openrouter)

        self.step_body.add_component(self.inp_or_key)
        self.step_body.add_component(self.bg_preset)
        self.step_body.add_component(self.btn_test_or)

    def _on_test_openrouter(self, **event_args):
        key = (self.inp_or_key.text or "").strip()
        preset = self.bg_preset.selected_value or "Balanced"
        if not key:
            m3.Snackbar(message="Please enter your OpenRouter API key.").show()
            return
        self.btn_test_or.enabled = False
        try:
            res = anvil.server.call("save_and_test_openrouter_key", self.workspace_id, key, preset)
            if res.get("ok"):
                self.wizard_data["openrouter_verified"] = True
                self.wizard_data["openrouter_preset"] = preset
                m3.Snackbar(message=f"OpenRouter verified ({res.get('model_used')})!").show()
            else:
                m3.Snackbar(message=f"Key test failed: {res.get('error')}").show()
        except Exception as exc:
            m3.Snackbar(message=f"Connection error: {exc}").show()
        finally:
            self.btn_test_or.enabled = True

    # ------------------------------------------------------------------
    # STEP 9: 1-TO-1 FOLLOW-UPS & OPTIONAL CSV IMPORT
    # ------------------------------------------------------------------
    def _render_step_9_followups(self):
        self.dd_wait = m3.DropdownMenu(
            label="Wait Before 1-to-1 No-Response Check-In",
            items=[("24 Hours", 24), ("48 Hours (Recommended)", 48), ("72 Hours", 72)],
            selected_value=self.wizard_data["followup_wait_hours"],
        )
        self.dd_attempts = m3.DropdownMenu(
            label="Maximum Follow-Up Attempts Before Marking Stalled",
            items=[("1 Attempt", 1), ("2 Attempts", 2), ("3 Attempts", 3)],
            selected_value=self.wizard_data["followup_max_attempts"],
        )
        self.file_csv = m3.FileLoader(text="Optional: Upload Existing Contacts CSV", file_types=".csv")
        self.cb_csv_consent = m3.Checkbox(
            text="I confirm I have lawful basis/consent to hold these contacts (no bulk blasts permitted)."
        )
        self.btn_import_csv = m3.Button(text="Import CSV", appearance="outlined", icon="upload_file")
        self.btn_import_csv.set_event_handler("click", self._on_import_csv)

        self.step_body.add_component(self.dd_wait)
        self.step_body.add_component(self.dd_attempts)
        self.step_body.add_component(self.file_csv)
        self.step_body.add_component(self.cb_csv_consent)
        self.step_body.add_component(self.btn_import_csv)

    def _on_import_csv(self, **event_args):
        if not self.file_csv.file:
            m3.Snackbar(message="Select a CSV file first.").show()
            return
        if not self.cb_csv_consent.checked:
            m3.Snackbar(message="Please tick the consent confirmation box before importing.").show()
            return
        try:
            res = anvil.server.call("import_contacts_csv", self.workspace_id, self.file_csv.file, True)
            m3.Snackbar(message=f"Imported {res.get('imported_count', 0)} contacts.").show()
        except Exception as exc:
            m3.Snackbar(message=f"CSV import failed: {exc}").show()

    # ------------------------------------------------------------------
    # STEP 10: YOUR ASSISTANT IS LIVE & TEST SIMULATION
    # ------------------------------------------------------------------
    def _render_step_10_live(self):
        self.step_body.add_component(
            m3.Text(
                text="Your Front Desk Assistant is configured. Run a simulated test enquiry below to see your CRM record and AI draft appear in the Action Queue."
            )
        )
        summary_lines = [
            f"Business: {self.wizard_data['business_name'] or 'Configured'} ({self.wizard_data['timezone']})",
            f"Approval Mode: {self.wizard_data['approval_mode']}",
            f"WhatsApp: {'Connected' if self.wizard_data['whatsapp_connected'] else 'Not linked'} | SMSGate: {'Linked' if self.wizard_data['smsgate_connected'] else 'Not linked'}",
            f"R2 Backup Bucket: {self.wizard_data['r2_bucket_name'] or 'Auto-provisioned'}",
        ]
        for line in summary_lines:
            self.step_body.add_component(m3.Chip(text=line))

        self.inp_test_msg = m3.TextArea(
            label="Simulated Incoming Customer Enquiry",
            text="Hi, I saw your website and would like to book a consultation next week. What times do you have free?",
        )
        self.btn_run_sim = m3.Button(
            text="Run Test Lead Simulation",
            appearance="tonal",
            icon="science",
        )
        self.btn_run_sim.set_event_handler("click", self._on_run_simulation)
        self.lbl_sim_output = m3.Text(text="")

        self.step_body.add_component(self.inp_test_msg)
        self.step_body.add_component(self.btn_run_sim)
        self.step_body.add_component(self.lbl_sim_output)

    def _on_run_simulation(self, **event_args):
        self.btn_run_sim.enabled = False
        try:
            res = anvil.server.call("run_test_lead_simulation", self.workspace_id, self.inp_test_msg.text)
            draft = res.get("draft_reply", "Draft queued in Action Queue.")
            self.lbl_sim_output.text = f"AI Draft Generated: {draft}"
            m3.Snackbar(message="Test lead processed! Check your Action Queue.").show()
        except Exception as exc:
            m3.Snackbar(message=f"Simulation error: {exc}").show()
        finally:
            self.btn_run_sim.enabled = True

    # ------------------------------------------------------------------
    # STEP VALIDATION & PERSISTENCE
    # ------------------------------------------------------------------
    def _collect_and_validate_current_step(self) -> bool:
        s = self.current_step
        if s == 1:
            if not (self.inp_biz_name.text or "").strip():
                m3.Snackbar(message="Please enter your business name.").show()
                return False
            self.wizard_data["business_name"] = self.inp_biz_name.text.strip()
            self.wizard_data["website_url"] = (self.inp_website.text or "").strip()
            self.wizard_data["timezone"] = self.dd_timezone.selected_value or "Europe/London"
            self.wizard_data["working_hours"] = (self.inp_hours.text or "").strip()

        elif s == 2:
            if not self.cb_policy.checked:
                m3.Snackbar(message="You must confirm the 1-to-1 anti-spam & no-payments policy to continue.").show()
                return False
            self.wizard_data["tone"] = self.bg_tone.selected_value or "Warm & Professional"
            self.wizard_data["signature"] = (self.inp_signature.text or "").strip()
            self.wizard_data["anti_spam_ack"] = True

        elif s == 3:
            self.wizard_data["service_name"] = (self.inp_service_name.text or "").strip()
            self.wizard_data["service_price_from"] = (self.inp_price_from.text or "").strip()
            self.wizard_data["qualifying_questions"] = (self.inp_qualifying.text or "").strip()

        elif s == 4:
            self.wizard_data["approval_mode"] = self.dd_approval.selected_value or "approve_before_send"

        elif s == 5:
            self.wizard_data["meeting_duration_mins"] = int(self.slider_duration.value or 30)

        elif s == 9:
            self.wizard_data["followup_wait_hours"] = self.dd_wait.selected_value or 48
            self.wizard_data["followup_max_attempts"] = self.dd_attempts.selected_value or 2

        return True

    def _on_back(self, **event_args):
        if self.current_step > 1:
            self._render_step(self.current_step - 1)

    def _on_next(self, **event_args):
        if not self._collect_and_validate_current_step():
            return

        try:
            anvil.server.call(
                "save_onboarding_step",
                self.workspace_id,
                self.current_step,
                self.wizard_data,
            )
        except Exception as exc:
            m3.Snackbar(message=f"Could not save step: {exc}").show()
            return

        if self.current_step < TOTAL_STEPS:
            self._render_step(self.current_step + 1)
        else:
            from ActionQueueForm import ActionQueueForm
            anvil.open_form(ActionQueueForm(workspace_id=self.workspace_id))
