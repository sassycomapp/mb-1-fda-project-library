"""
ActionQueueForm.py — Main Shell & Action Queue for Front Desk Assistant
Built on m3-custom-theme v2.0.0 (Dependency ID: UGGJBAZUZ74XZ7VU)

REQUIRED SERVER CALLABLES (add to front_desk_pipeline.py if not yet added):
---------------------------------------------------------------------------
@anvil.server.callable
def get_action_queue(workspace_id: str) -> dict:
    # Returns:
    # {
    #   "channel_health": {"email": "connected", "whatsapp": "connected", "sms": "disconnected"},
    #   "pending_drafts_count": 3,
    #   "items": [
    #       {
    #           "item_id": "aq_101",
    #           "type": "approval_required",  # approval_required | urgent_enquiry | channel_offline | integration_error
    #           "priority": "high",           # high | normal
    #           "title": "Draft reply for Sarah Jenkins (WhatsApp)",
    #           "subtitle": "Enquiry: Tax advisory consultation next Thursday",
    #           "channel": "whatsapp",
    #           "contact_name": "Sarah Jenkins",
    #           "contact_handle": "+44 7700 900123",
    #           "inbound_text": "Hi, do you have availability next Thursday afternoon for a 30-min tax consult?",
    #           "draft_text": "Hi Sarah, thanks for reaching out! I have Thursday at 14:00 or 15:30 available...",
    #           "message_id": "msg_991",
    #           "lead_id": "lead_442",
    #           "created_at": "10 mins ago"
    #       }
    #   ]
    # }
    pass

@anvil.server.callable
def resolve_action_item(workspace_id: str, item_id: str, action: str) -> dict:
    # Marks non-draft tasks (e.g., channel_offline, urgent_enquiry) as resolved or snoozed.
    pass
"""

import anvil
import anvil.server
import m3.components as m3
from m3._utils import m3x_theming, m3x_motion


def init_theme(palette: str = "professional_blue", mode: str = "system"):
    """Call once at application startup (e.g. in startup.py before opening ActionQueueForm)."""
    m3x_theming.apply_saved()
    m3x_theming.set_palette(palette)
    m3x_theming.set_mode(mode)
    m3x_theming.set_menu_style("standard")
    m3x_motion.set_scheme("standard")


class ActionQueueForm(m3.NavigationRailLayout):
    """
    Primary daily workspace: "Here are the things that need you today."
    Uses M3 Expressive NavigationRailLayout + TopAppBar + ListItem + SplitButton + Dialog + Snackbar.
    """

    def __init__(self, workspace_id: str, **properties):
        super().__init__(**properties)
        self.workspace_id = workspace_id
        self.queue_items = []
        self.channel_health = {"email": "disconnected", "whatsapp": "disconnected", "sms": "disconnected"}

        # Configure M3 Expressive Navigation Rail
        self.rail_style = "expressive"
        self.rail_adaptive = True

        self._build_shell()
        self.refresh_queue()

    # -------------------------------------------------------------------------
    # SHELL & NAVIGATION RAIL
    # -------------------------------------------------------------------------
    def _build_shell(self):
        # Top App Bar
        self.top_bar = m3.TopAppBar(
            title="Front Desk Assistant",
            variant="small",
        )
        self.btn_refresh = m3.IconButton(icon="mi:refresh", tooltip="Refresh Queue")
        self.btn_refresh.set_event_handler("click", lambda **e: self.refresh_queue())
        self.top_bar.add_component(self.btn_refresh)
        self.add_component(self.top_bar, slot="top_app_bar")

        # Navigation Rail Links
        self.nav_badge = m3.Badge(count=0, visible=False)
        nav_items = [
            ("action_queue", "Today's Queue", "mi:bolt", True),
            ("inbox", "Unified Inbox", "mi:inbox", False),
            ("approvals", "Approval Queue", "mi:fact_check", False),
            ("calendar", "Calendar & Rules", "mi:event_available", False),
            ("followups", "1-to-1 Follow-Ups", "mi:repeat", False),
            ("dashboard", "Value Dashboard", "mi:insights", False),
            ("wizard", "Setup & Channels", "mi:tune", False),
        ]

        for route_key, label, icon, selected in nav_items:
            link = m3.NavigationLink(
                text=label,
                icon=icon,
                selected=selected,
            )
            link.set_event_handler("click", lambda rk=route_key, **e: self._navigate(rk))
            self.add_component(link, slot="navigation")

        # Main Content Container
        self.main_col = anvil.ColumnPanel(spacing="medium")
        self.add_component(self.main_col)

        # Header & Channel Health Strip
        self._build_header_strip()

        # Loading Indicator (M3 Expressive shape-morphing loader)
        self.loader = m3.LoadingIndicator(contained=True, visible=False)
        self.main_col.add_component(self.loader)

        # Queue List Container
        self.list_container = anvil.ColumnPanel(spacing="small")
        self.main_col.add_component(self.list_container)

    def _build_header_strip(self):
        header_card = m3.Card(appearance="outlined")
        header_box = anvil.ColumnPanel(spacing="small")

        title_row = anvil.FlowPanel(align="justify", vertical_align="center")
        title_box = anvil.ColumnPanel(spacing="none")
        title_box.add_component(m3.Heading(text="Action Queue", scale="headline", size="medium"))
        self.lbl_subtitle = m3.Text(
            text="Review AI drafts, urgent enquiries, and channel alerts needing your attention today.",
            scale="body",
            size="medium",
        )
        title_box.add_component(self.lbl_subtitle)
        title_row.add_component(title_box)

        # Live Channel Health Chips
        self.health_panel = anvil.FlowPanel(spacing="small", vertical_align="center")
        self.chip_email = m3.Chip(text="Email: Checking...", variant="assist", icon="mi:mail")
        self.chip_wa = m3.Chip(text="WhatsApp: Checking...", variant="assist", icon="mi:chat")
        self.chip_sms = m3.Chip(text="SMSGate: Checking...", variant="assist", icon="mi:sms")

        for ch in (self.chip_email, self.chip_wa, self.chip_sms):
            ch.set_event_handler("click", lambda **e: self._navigate("wizard"))
            self.health_panel.add_component(ch)

        title_row.add_component(self.health_panel)
        header_box.add_component(title_row)
        header_card.add_component(header_box)
        self.main_col.add_component(header_card)

    # -------------------------------------------------------------------------
    # DATA LOADING & RENDERING
    # -------------------------------------------------------------------------
    def refresh_queue(self):
        self.loader.visible = True
        self.list_container.clear()
        try:
            data = anvil.server.call("get_action_queue", self.workspace_id)
            self.queue_items = data.get("items", [])
            self.channel_health = data.get("channel_health", {})
            self._update_health_chips()
            self._render_items()
        except Exception as err:
            m3.Snackbar(
                message=f"Could not load action queue: {err}",
                action_text="Retry",
                on_action=self.refresh_queue,
            ).show()
        finally:
            self.loader.visible = False

    def _update_health_chips(self):
        mapping = [
            (self.chip_email, "Email", self.channel_health.get("email", "disconnected")),
            (self.chip_wa, "WhatsApp", self.channel_health.get("whatsapp", "disconnected")),
            (self.chip_sms, "SMSGate", self.channel_health.get("sms", "disconnected")),
        ]
        for chip, label, status in mapping:
            is_ok = status == "connected"
            chip.text = f"{label}: {'Online' if is_ok else 'Offline'}"
            chip.icon = "mi:check_circle" if is_ok else "mi:warning"

    def _render_items(self):
        self.list_container.clear()

        if not self.queue_items:
            empty_card = m3.Card(appearance="filled")
            empty_box = anvil.ColumnPanel(spacing="small")
            empty_box.add_component(
                m3.Heading(text="You are all caught up", scale="title", size="large")
            )
            empty_box.add_component(
                m3.Text(
                    text="No drafts awaiting approval, urgent leads, or offline channel alerts right now.",
                    scale="body",
                    size="medium",
                )
            )
            btn_sim = m3.Button(
                text="Simulate Test Enquiry",
                appearance="outlined",
                icon="mi:science",
            )
            btn_sim.set_event_handler("click", self._simulate_test_lead)
            empty_box.add_component(btn_sim)
            empty_card.add_component(empty_box)
            self.list_container.add_component(empty_card)
            return

        for item in self.queue_items:
            self.list_container.add_component(self._build_queue_card(item))

    def _build_queue_card(self, item: dict) -> m3.Card:
        card = m3.Card(appearance="elevated" if item.get("priority") == "high" else "outlined")
        wrapper = anvil.ColumnPanel(spacing="small")

        # Lead-in ListItem
        icon_map = {
            "approval_required": "mi:rate_review",
            "urgent_enquiry": "mi:priority_high",
            "channel_offline": "mi:portable_wifi_off",
            "integration_error": "mi:error_outline",
        }
        leading_icon = m3.IconButton(
            icon=icon_map.get(item.get("type"), "mi:notifications"),
            enabled=False,
        )

        row_item = m3.ListItem(
            headline=item.get("title", "Action needed"),
            supporting_text=f"{item.get('subtitle', '')}  •  {item.get('created_at', '')}",
        )
        row_item.add_component(leading_icon, slot="leading")

        # Trailing Quick Action
        if item.get("type") == "approval_required":
            split_btn = m3.SplitButton(
                text="Approve & Send",
                icon="mi:send",
                menu_items=[
                    m3.MenuItem(text="Edit Draft Before Sending", icon="mi:edit"),
                    m3.MenuItem(text="Reject Draft", icon="mi:close"),
                    m3.MenuItem(text="Mark Contact 'Do Not Contact'", icon="mi:block"),
                ],
            )
            split_btn.set_event_handler(
                "click", lambda it=item, **e: self._approve_draft(it, edited_text=None)
            )
            split_btn.set_event_handler(
                "menu_item_click",
                lambda menu_item, it=item, **e: self._handle_draft_menu(menu_item.text, it),
            )
            row_item.add_component(split_btn, slot="trailing")
        else:
            btn_fix = m3.Button(
                text="Reconnect" if item.get("type") == "channel_offline" else "Review & Resolve",
                appearance="filled",
            )
            btn_fix.set_event_handler(
                "click", lambda it=item, **e: self._handle_system_alert(it)
            )
            row_item.add_component(btn_fix, slot="trailing")

        wrapper.add_component(row_item)

        # Preview box for inbound message + proposed AI reply
        if item.get("type") == "approval_required":
            preview_panel = anvil.ColumnPanel(spacing="xsmall")
            preview_panel.add_component(
                m3.Text(
                    text=f"Customer ({item.get('channel', '').upper()}): {item.get('inbound_text', '')}",
                    scale="body",
                    size="small",
                )
            )
            preview_panel.add_component(
                m3.Text(
                    text=f"Proposed AI Reply: {item.get('draft_text', '')}",
                    scale="body",
                    size="medium",
                )
            )
            wrapper.add_component(preview_panel)

        card.add_component(wrapper)
        return card

    # -------------------------------------------------------------------------
    # APPROVAL & EDIT DIALOG ACTIONS
    # -------------------------------------------------------------------------
    def _handle_draft_menu(self, choice: str, item: dict):
        if "Edit" in choice:
            self._open_edit_dialog(item)
        elif "Reject" in choice:
            self._reject_draft(item)
        elif "Do Not Contact" in choice:
            self._mark_do_not_contact(item)

    def _open_edit_dialog(self, item: dict):
        body_col = anvil.ColumnPanel(spacing="small")
        body_col.add_component(
            m3.Text(
                text=f"Original message from {item.get('contact_name')}: {item.get('inbound_text')}",
                scale="body",
                size="small",
            )
        )
        txt_editor = m3.TextArea(
            text=item.get("draft_text", ""),
            label="Edit reply before sending",
            rows=5,
        )
        body_col.add_component(txt_editor)

        dlg = m3.Dialog(
            title=f"Edit {item.get('channel', '').upper()} Reply",
            content=body_col,
            confirm_text="Send Edited Reply",
            cancel_text="Cancel",
        )
        if dlg.show():
            self._approve_draft(item, edited_text=txt_editor.text.strip())

    def _approve_draft(self, item: dict, edited_text: str | None):
        try:
            anvil.server.call(
                "approve_and_send_draft",
                workspace_id=self.workspace_id,
                message_id=item["message_id"],
                final_text=edited_text,
            )
            m3.Snackbar(message=f"Reply sent to {item.get('contact_name')}.").show()
            self.refresh_queue()
        except Exception as err:
            m3.Snackbar(message=f"Send failed: {err}").show()

    def _reject_draft(self, item: dict):
        try:
            anvil.server.call(
                "resolve_action_item",
                workspace_id=self.workspace_id,
                item_id=item["item_id"],
                action="rejected",
            )
            m3.Snackbar(message="Draft discarded.").show()
            self.refresh_queue()
        except Exception as err:
            m3.Snackbar(message=f"Error: {err}").show()

    def _mark_do_not_contact(self, item: dict):
        try:
            anvil.server.call(
                "resolve_action_item",
                workspace_id=self.workspace_id,
                item_id=item["item_id"],
                action="do_not_contact",
            )
            m3.Snackbar(message=f"{item.get('contact_name')} marked Do Not Contact. All follow-ups halted.").show()
            self.refresh_queue()
        except Exception as err:
            m3.Snackbar(message=f"Error: {err}").show()

    def _handle_system_alert(self, item: dict):
        if item.get("type") == "channel_offline":
            self._navigate("wizard")
            return
        try:
            anvil.server.call(
                "resolve_action_item",
                workspace_id=self.workspace_id,
                item_id=item["item_id"],
                action="resolved",
            )
            m3.Snackbar(message="Alert marked resolved.").show()
            self.refresh_queue()
        except Exception as err:
            m3.Snackbar(message=f"Error: {err}").show()

    def _simulate_test_lead(self, **event_args):
        try:
            anvil.server.call("simulate_test_enquiry", self.workspace_id)
            m3.Snackbar(message="Test enquiry created! Refreshing queue...").show()
            self.refresh_queue()
        except Exception as err:
            m3.Snackbar(message=f"Simulation failed: {err}").show()

    # -------------------------------------------------------------------------
    # NAVIGATION ROUTING
    # -------------------------------------------------------------------------
    def _navigate(self, route_key: str):
        route_map = {
            "action_queue": lambda: ActionQueueForm(self.workspace_id),
            "wizard": lambda: anvil.open_form("OnboardingWizardForm", self.workspace_id),
            "inbox": lambda: anvil.open_form("UnifiedInboxForm", self.workspace_id),
            "approvals": lambda: anvil.open_form("ApprovalQueueForm", self.workspace_id),
            "calendar": lambda: anvil.open_form("CalendarSettingsForm", self.workspace_id),
            "followups": lambda: anvil.open_form("FollowUpsForm", self.workspace_id),
            "dashboard": lambda: anvil.open_form("DashboardForm", self.workspace_id),
        }
        if route_key == "action_queue":
            self.refresh_queue()
        elif route_key in route_map:
            route_map[route_key]()
