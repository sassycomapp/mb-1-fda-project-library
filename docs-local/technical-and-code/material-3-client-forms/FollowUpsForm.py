import anvil.server
import m3.components as m3


class FollowUpsForm(m3.NavigationRailLayout):
    """1-to-1 No-Response Follow-Up configuration screen (zero bulk marketing)."""

    def __init__(self, **properties):
        super().__init__(**properties)
        self.rail_style = "expressive"
        self.rail_adaptive = True
        self._max_attempts = 2
        self._build_shell()
        self._load_settings()

    def _build_shell(self):
        self.top_bar = m3.TopAppBar(title="1-to-1 Follow-Up Rules")
        self.add_component(self.top_bar, slot="top_app_bar")

        nav_items = [
            ("Action Queue", "mi:inbox", "ActionQueueForm"),
            ("Lead Inbox", "mi:forum", "InboxAndLeadForm"),
            ("Calendar", "mi:event_available", "CalendarSettingsForm"),
            ("Follow-Ups", "mi:schedule_send", "FollowUpsForm"),
            ("Dashboard", "mi:insights", "DashboardForm"),
            ("Setup Wizard", "mi:tune", "OnboardingWizardForm"),
        ]
        for label, icon, target in nav_items:
            link = m3.NavigationLink(
                text=label,
                icon=icon,
                selected=(target == "FollowUpsForm"),
            )
            link.set_event_handler("click", lambda t=target, **e: anvil.open_form(t))
            self.add_component(link, slot="navigation")

        self.root = m3.ColumnPanel(spacing="medium")
        self.add_component(self.root)

        # Compliance Banner Card
        policy_card = m3.Card(appearance="filled")
        policy_box = m3.ColumnPanel(spacing="small")
        policy_box.add_component(
            m3.Heading(text="1-to-1 Enquiry Follow-Up Only (Zero Bulk Blasts)", scale="small")
        )
        policy_box.add_component(
            m3.Text(
                text=(
                    "Front Desk Assistant only follows up on active inbound enquiries that "
                    "have not replied yet. Bulk SMS/WhatsApp campaigns are permanently disabled, "
                    "and any STOP/UNSUBSCRIBE reply halts automation immediately."
                )
            )
        )
        policy_card.add_component(policy_box)
        self.root.add_component(policy_card)

        # Configuration Card
        cfg_card = m3.Card(appearance="outlined")
        cfg_box = m3.ColumnPanel(spacing="medium")

        enable_row = m3.FlowPanel(spacing="medium")
        enable_row.add_component(m3.Text(text="Enable Automated 1-to-1 No-Response Follow-Up"))
        self.sw_enabled = m3.Switch(checked=True)
        enable_row.add_component(self.sw_enabled)
        cfg_box.add_component(enable_row)

        self.lbl_delay = m3.Text(text="Wait Before First Follow-Up: 24 hours")
        cfg_box.add_component(self.lbl_delay)
        self.sld_delay = m3.Slider(min=4, max=72, step=4, value=24, size="medium")
        self.sld_delay.set_event_handler("change", self._on_delay_change)
        cfg_box.add_component(self.sld_delay)

        cfg_box.add_component(m3.Text(text="Maximum 1-to-1 Follow-Up Attempts Before Marking Stalled"))
        self.bg_attempts = m3.ButtonGroup(
            items=[
                {"text": "1 Attempt", "value": 1},
                {"text": "2 Attempts", "value": 2},
                {"text": "3 Attempts", "value": 3},
            ],
            selection_mode="single",
        )
        self.bg_attempts.set_event_handler("change", self._on_attempts_change)
        cfg_box.add_component(self.bg_attempts)

        stop_row = m3.FlowPanel(spacing="medium")
        stop_row.add_component(m3.Text(text="Stop Immediately When Lead Replies or Books"))
        self.sw_stop_reply = m3.Switch(checked=True, enabled=False)
        stop_row.add_component(self.sw_stop_reply)
        cfg_box.add_component(stop_row)

        self.txt_template = m3.TextArea(
            label="Non-Pushy 1-to-1 Follow-Up Template",
            rows=4,
            text=(
                "Hi {{first_name}}, just checking in to see if you still needed help with "
                "{{service_interest}}. No rush at all—if you'd like to grab a quick slot, "
                "you can pick a time here: {{booking_link}}"
            ),
        )
        cfg_box.add_component(self.txt_template)

        self.btn_save = m3.Button(
            text="Save Follow-Up Rules",
            icon="mi:save",
            appearance="filled",
        )
        self.btn_save.set_event_handler("click", self._on_save)
        cfg_box.add_component(self.btn_save)

        cfg_card.add_component(cfg_box)
        self.root.add_component(cfg_card)

    def _load_settings(self):
        try:
            data = anvil.server.call("get_followup_settings")
            self.sw_enabled.checked = bool(data.get("followup_enabled", True))
            delay = int(data.get("followup_delay_hours", 24))
            self.sld_delay.value = delay
            self.lbl_delay.text = f"Wait Before First Follow-Up: {delay} hours"
            self._max_attempts = int(data.get("followup_max_attempts", 2))
            self.bg_attempts.selected_value = self._max_attempts
            if data.get("followup_template"):
                self.txt_template.text = data["followup_template"]
        except Exception as exc:
            m3.Snackbar(message=f"Could not load follow-up rules: {exc}").show()

    def _on_delay_change(self, **event_args):
        delay = int(self.sld_delay.value or 24)
        self.lbl_delay.text = f"Wait Before First Follow-Up: {delay} hours"

    def _on_attempts_change(self, **event_args):
        if self.bg_attempts.selected_value:
            self._max_attempts = int(self.bg_attempts.selected_value)

    def _on_save(self, **event_args):
        try:
            anvil.server.call(
                "save_followup_settings",
                {
                    "followup_enabled": bool(self.sw_enabled.checked),
                    "followup_delay_hours": int(self.sld_delay.value or 24),
                    "followup_max_attempts": self._max_attempts,
                    "followup_template": self.txt_template.text.strip(),
                },
            )
            m3.Snackbar(message="1-to-1 follow-up rules saved.").show()
        except Exception as exc:
            m3.Snackbar(message=f"Save failed: {exc}").show()
