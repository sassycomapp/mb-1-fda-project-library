import anvil.server
import anvil.js
import m3.components as m3
from m3._utils import m3x_theming, m3x_adaptive


class CalendarSettingsForm(m3.NavigationRailLayout):
    """Calendar & Booking settings screen built on m3-custom-theme v2.0.0."""

    def __init__(self, **properties):
        super().__init__(**properties)
        self.rail_style = "expressive"
        self.rail_adaptive = True
        self._booking_url = ""
        self._selected_duration = 30
        self._build_shell()
        self._load_settings()

    def _build_shell(self):
        self.top_bar = m3.TopAppBar(title="Calendar & Booking")
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
                selected=(target == "CalendarSettingsForm"),
            )
            link.set_event_handler("click", lambda t=target, **e: anvil.open_form(t))
            self.add_component(link, slot="navigation")

        self.root = m3.ColumnPanel(spacing="medium")
        self.add_component(self.root)

        # Card 1: Google Calendar Connection & Public Booking Link
        conn_card = m3.Card(appearance="outlined")
        conn_box = m3.ColumnPanel(spacing="small")
        conn_box.add_component(m3.Heading(text="Google Calendar & Booking Link", scale="small"))

        self.chip_gcal_status = m3.Chip(text="Checking Google Calendar...", icon="mi:sync")
        conn_box.add_component(self.chip_gcal_status)

        link_row = m3.FlowPanel(spacing="small")
        self.txt_booking_link = m3.TextBox(
            label="Your Public Booking Link",
            enabled=False,
        )
        self.btn_copy_link = m3.Button(
            text="Copy Link",
            icon="mi:content_copy",
            appearance="tonal",
        )
        self.btn_copy_link.set_event_handler("click", self._on_copy_link)
        link_row.add_component(self.txt_booking_link)
        link_row.add_component(self.btn_copy_link)
        conn_box.add_component(link_row)

        self.btn_connect_gcal = m3.Button(
            text="Reconnect Google Calendar",
            icon="mi:link",
            appearance="outlined",
        )
        self.btn_connect_gcal.set_event_handler("click", self._on_connect_gcal)
        conn_box.add_component(self.btn_connect_gcal)

        conn_card.add_component(conn_box)
        self.root.add_component(conn_card)

        # Card 2: Working Hours, Meeting Duration & Buffer
        rules_card = m3.Card(appearance="outlined")
        rules_box = m3.ColumnPanel(spacing="medium")
        rules_box.add_component(m3.Heading(text="Availability & Meeting Rules", scale="small"))

        hours_row = m3.FlowPanel(spacing="medium")
        self.tp_start = m3.TimePicker(label="Working Day Start")
        self.tp_end = m3.TimePicker(label="Working Day End")
        hours_row.add_component(self.tp_start)
        hours_row.add_component(self.tp_end)
        rules_box.add_component(hours_row)

        rules_box.add_component(m3.Text(text="Default Consultation Duration (minutes)"))
        self.bg_duration = m3.ButtonGroup(
            items=[
                {"text": "15 min", "value": 15},
                {"text": "30 min", "value": 30},
                {"text": "45 min", "value": 45},
                {"text": "60 min", "value": 60},
            ],
            selection_mode="single",
        )
        self.bg_duration.set_event_handler("change", self._on_duration_change)
        rules_box.add_component(self.bg_duration)

        self.lbl_buffer = m3.Text(text="Buffer Between Meetings: 15 minutes")
        rules_box.add_component(self.lbl_buffer)
        self.sld_buffer = m3.Slider(min=0, max=60, step=5, value=15, size="medium")
        self.sld_buffer.set_event_handler("change", self._on_buffer_change)
        rules_box.add_component(self.sld_buffer)

        self.btn_save = m3.Button(
            text="Save Calendar Rules",
            icon="mi:save",
            appearance="filled",
        )
        self.btn_save.set_event_handler("click", self._on_save)
        rules_box.add_component(self.btn_save)

        rules_card.add_component(rules_box)
        self.root.add_component(rules_card)

    def _load_settings(self):
        try:
            data = anvil.server.call("get_calendar_settings")
            connected = data.get("google_calendar_connected", False)
            self.chip_gcal_status.text = (
                "Google Calendar Connected" if connected else "Google Calendar Not Connected"
            )
            self.chip_gcal_status.icon = "mi:check_circle" if connected else "mi:warning"
            self._booking_url = data.get("booking_link", "")
            self.txt_booking_link.text = self._booking_url

            if data.get("work_start"):
                self.tp_start.time = data["work_start"]
            if data.get("work_end"):
                self.tp_end.time = data["work_end"]

            self._selected_duration = int(data.get("meeting_duration_mins", 30))
            self.bg_duration.selected_value = self._selected_duration

            buf = int(data.get("buffer_mins", 15))
            self.sld_buffer.value = buf
            self.lbl_buffer.text = f"Buffer Between Meetings: {buf} minutes"
        except Exception as exc:
            m3.Snackbar(message=f"Could not load calendar settings: {exc}").show()

    def _on_duration_change(self, **event_args):
        if self.bg_duration.selected_value:
            self._selected_duration = int(self.bg_duration.selected_value)

    def _on_buffer_change(self, **event_args):
        buf = int(self.sld_buffer.value or 0)
        self.lbl_buffer.text = f"Buffer Between Meetings: {buf} minutes"

    def _on_copy_link(self, **event_args):
        if not self._booking_url:
            m3.Snackbar(message="No booking link configured yet.").show()
            return
        try:
            anvil.js.window.navigator.clipboard.writeText(self._booking_url)
            m3.Snackbar(message="Booking link copied to clipboard.").show()
        except Exception:
            m3.Snackbar(message=f"Booking link: {self._booking_url}").show()

    def _on_connect_gcal(self, **event_args):
        m3.Snackbar(message="Opening Google Calendar OAuth connection flow...").show()

    def _on_save(self, **event_args):
        try:
            anvil.server.call(
                "save_calendar_settings",
                {
                    "work_start": str(self.tp_start.time or "09:00"),
                    "work_end": str(self.tp_end.time or "17:00"),
                    "meeting_duration_mins": self._selected_duration,
                    "buffer_mins": int(self.sld_buffer.value or 15),
                },
            )
            m3.Snackbar(message="Calendar & booking rules saved.").show()
        except Exception as exc:
            m3.Snackbar(message=f"Save failed: {exc}").show()
