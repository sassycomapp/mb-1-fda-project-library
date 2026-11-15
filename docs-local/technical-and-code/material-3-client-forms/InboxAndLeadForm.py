"""
InboxAndLeadForm.py
===================
Anvil Client Form for Front Desk Assistant: Unified Lead Inbox & Lead Record.
Built on m3-custom-theme (v2.0.0, ID: UGGJBAZUZ74XZ7VU).

Features:
- Adaptive M3 Expressive PaneLayout (list-detail split on >=840px, single-pane on mobile)
- TopAppBar + NavigationRailLayout ("expressive", adaptive)
- SearchBar + Channel Filter Chips (All, Email, WhatsApp, SMS, Webform)
- Lead ListItems with channel badges, urgency indicators, and pipeline stage pills
- Right Detail Pane:
  - Contact & Lead Metadata Card (service interest, budget, timeline, stage selector)
  - Full Immutable Conversation Thread (Inbound, AI Drafts, Outbound with delivery status)
  - Manual 1-to-1 Reply Composer (with strict zero bulk-blast & opt-out safeguards)
  - One-click "Do Not Contact" toggle (halts all sequences immediately)
  - Cloudflare R2 Historical Archive Lookup button (for messages > retention window)

Required Server Callables (add to front_desk_pipeline.py / r2_manager.py):
- list_workspace_leads(workspace_id: str, channel_filter: str = "all", search_query: str = "") -> list[dict]
- get_lead_detail_and_thread(workspace_id: str, lead_id: str) -> dict
- update_lead_stage(workspace_id: str, lead_id: str, new_stage: str) -> dict
- set_contact_do_not_contact(workspace_id: str, contact_id: str, dnc: bool) -> dict
- send_manual_one_to_one_reply(workspace_id: str, lead_id: str, channel: str, body: str) -> dict
- fetch_archived_messages_from_r2(workspace_id: str, contact_id: str) -> list[dict]
"""

import anvil
import anvil.server
import m3.components as m3
from m3._utils import m3x_theming, m3x_motion


PIPELINE_STAGES = [
    ("New Enquiry", "new_enquiry"),
    ("Responded", "responded"),
    ("Meeting Booked", "meeting_booked"),
    ("Proposal / Quote", "proposal_quote"),
    ("Won", "won"),
    ("Lost / Not a Fit", "lost_not_a_fit"),
]


class InboxAndLeadForm(m3.NavigationRailLayout):
    """Unified Multi-Channel Lead Inbox & Lead Record built with M3 PaneLayout."""

    def __init__(self, workspace_id: str, initial_lead_id: str = None, **properties):
        super().__init__(**properties)
        self.workspace_id = workspace_id
        self.selected_lead_id = initial_lead_id
        self.channel_filter = "all"
        self.search_query = ""
        self.leads_cache = []
        self.current_detail = None

        # Configure M3 Expressive Navigation Rail
        self.rail_style = "expressive"
        self.rail_adaptive = True

        self._build_shell()
        self._build_pane_layout()
        self.load_leads_list()

    def _build_shell(self):
        # Top App Bar
        self.top_bar = m3.TopAppBar(title="Lead Inbox & Records")
        self.btn_refresh = m3.IconButton(icon="mi:refresh", tooltip="Refresh Inbox")
        self.btn_refresh.set_event_handler("click", lambda **e: self.load_leads_list())
        self.top_bar.add_component(self.btn_refresh)
        self.add_component(self.top_bar, slot="app_bar")

        # Navigation Rail Links
        nav_items = [
            ("Action Queue", "mi:bolt", "ActionQueueForm"),
            ("Lead Inbox", "mi:inbox", "InboxAndLeadForm"),
            ("Calendar", "mi:event", "CalendarSettingsForm"),
            ("Follow-Ups", "mi:schedule_send", "FollowUpsForm"),
            ("Dashboard", "mi:analytics", "DashboardForm"),
            ("Setup Wizard", "mi:tune", "OnboardingWizardForm"),
        ]
        for label, icon, target_form in nav_items:
            link = m3.NavigationLink(
                text=label,
                icon=icon,
                selected=(target_form == "InboxAndLeadForm"),
            )
            link.set_event_handler(
                "click",
                lambda target=target_form, **e: self._navigate(target),
            )
            self.add_component(link, slot="navigation")

    def _navigate(self, target_form: str):
        if target_form == "InboxAndLeadForm":
            return
        try:
            anvil.open_form(target_form, workspace_id=self.workspace_id)
        except Exception:
            m3.Snackbar(message=f"Form '{target_form}' not wired yet.").show()

    def _build_pane_layout(self):
        """Constructs the adaptive M3 list-detail PaneLayout."""
        self.pane_layout = m3.PaneLayout(layout_type="list_detail")
        self.add_component(self.pane_layout)

        # --- LEFT PANE: Search, Filter Chips, and Lead List ---
        self.left_pane = anvil.ColumnPanel(spacing="small")
        self.pane_layout.add_component(self.left_pane, slot="list")

        self.search_bar = m3.SearchBar(placeholder="Search name, email, phone, or service...")
        self.search_bar.set_event_handler("change", self._on_search_change)
        self.left_pane.add_component(self.search_bar)

        # Channel Filter Chips
        self.filter_row = anvil.FlowPanel(spacing="tiny")
        self.filter_chips = {}
        for label, code in [
            ("All", "all"),
            ("Email", "email"),
            ("WhatsApp", "whatsapp"),
            ("SMS", "sms"),
            ("Webform", "webform"),
        ]:
            chip = m3.Chip(
                text=label,
                variant="filter",
                selected=(code == "all"),
            )
            chip.set_event_handler("click", lambda c=code, **e: self._on_filter_select(c))
            self.filter_chips[code] = chip
            self.filter_row.add_component(chip)
        self.left_pane.add_component(self.filter_row)

        self.list_loader = m3.LoadingIndicator(visible=False)
        self.left_pane.add_component(self.list_loader)

        self.leads_list_panel = anvil.ColumnPanel(spacing="tiny")
        self.left_pane.add_component(self.leads_list_panel)

        # --- RIGHT PANE: Lead Record & Conversation Thread ---
        self.right_pane = anvil.ColumnPanel(spacing="medium")
        self.pane_layout.add_component(self.right_pane, slot="detail")

        self._render_empty_detail()

    def _render_empty_detail(self):
        self.right_pane.clear()
        empty_card = m3.Card(variant="outlined")
        box = anvil.ColumnPanel(spacing="small", align="center")
        box.add_component(m3.Heading(text="Select a lead to view history", scale="title"))
        box.add_component(
            m3.Text(
                text="Choose any enquiry on the left to inspect extracted details, review the full Email/WhatsApp/SMS thread, or send a 1-to-1 reply."
            )
        )
        empty_card.add_component(box)
        self.right_pane.add_component(empty_card)

    def _on_search_change(self, **event_args):
        self.search_query = (self.search_bar.text or "").strip()
        self.load_leads_list()

    def _on_filter_select(self, code: str):
        self.channel_filter = code
        for c_key, chip in self.filter_chips.items():
            chip.selected = (c_key == code)
        self.load_leads_list()

    def load_leads_list(self):
        self.list_loader.visible = True
        self.leads_list_panel.clear()
        try:
            self.leads_cache = anvil.server.call(
                "list_workspace_leads",
                self.workspace_id,
                self.channel_filter,
                self.search_query,
            )
        except Exception as err:
            self.list_loader.visible = False
            m3.Snackbar(message=f"Could not load leads: {err}").show()
            return

        self.list_loader.visible = False

        if not self.leads_cache:
            self.leads_list_panel.add_component(
                m3.Text(text="No enquiries match the current filter.")
            )
            return

        for lead in self.leads_cache:
            lead_id = lead["lead_id"]
            is_selected = (lead_id == self.selected_lead_id)
            channel_tag = lead.get("last_channel", "email").upper()
            stage_label = lead.get("status", "new_enquiry").replace("_", " ").title()
            urgency = " [URGENT]" if lead.get("urgency") == "high" else ""
            dnc_tag = " [DO NOT CONTACT]" if lead.get("do_not_contact") else ""

            item = m3.ListItem(
                headline=f"{lead.get('contact_name', 'Unknown Contact')}{urgency}{dnc_tag}",
                supporting_text=f"{channel_tag} · {lead.get('service_interest', 'General Enquiry')} · {stage_label}",
                selected=is_selected,
            )
            item.set_event_handler(
                "click",
                lambda lid=lead_id, **e: self.select_lead(lid),
            )
            self.leads_list_panel.add_component(item)

        if self.selected_lead_id:
            self.select_lead(self.selected_lead_id)

    def select_lead(self, lead_id: str):
        self.selected_lead_id = lead_id
        # Update selection state in list items
        for idx, child in enumerate(self.leads_list_panel.get_components()):
            if idx < len(self.leads_cache):
                child.selected = (self.leads_cache[idx]["lead_id"] == lead_id)

        self.right_pane.clear()
        self.right_pane.add_component(m3.LoadingIndicator())

        try:
            detail = anvil.server.call(
                "get_lead_detail_and_thread",
                self.workspace_id,
                lead_id,
            )
            self.current_detail = detail
            self._render_lead_detail(detail)
            # Show detail pane on compact screens (<840px)
            self.pane_layout.show_detail()
        except Exception as err:
            self.right_pane.clear()
            m3.Snackbar(message=f"Error loading lead record: {err}").show()

    def _render_lead_detail(self, detail: dict):
        self.right_pane.clear()
        contact = detail.get("contact", {})
        lead = detail.get("lead", {})
        messages = detail.get("messages", [])

        # Back button for compact mobile screens
        btn_back = m3.Button(text="Back to List", icon="mi:arrow_back", variant="text")
        btn_back.set_event_handler("click", lambda **e: self.pane_layout.show_list())
        self.right_pane.add_component(btn_back)

        # --- 1. CONTACT & LEAD SUMMARY CARD ---
        header_card = m3.Card(variant="elevated")
        header_box = anvil.ColumnPanel(spacing="small")

        title_row = anvil.FlowPanel(spacing="small", align="left")
        title_row.add_component(
            m3.Heading(text=contact.get("name", "Unnamed Prospect"), scale="headline_small")
        )
        if lead.get("urgency") == "high":
            title_row.add_component(m3.Badge(text="HIGH URGENCY"))
        if contact.get("do_not_contact"):
            title_row.add_component(m3.Badge(text="DO NOT CONTACT"))
        header_box.add_component(title_row)

        meta_lines = [
            f"Email: {contact.get('email') or 'Not provided'}  |  Phone: {contact.get('phone') or 'Not provided'}",
            f"Company: {contact.get('company') or 'Individual'}  |  Source: {lead.get('source', 'Direct')}",
            f"Service Interest: {lead.get('service_interest') or 'Not extracted yet'}  |  Timeline: {lead.get('timeline') or 'Unspecified'}",
        ]
        for line in meta_lines:
            header_box.add_component(m3.Text(text=line))

        # Pipeline Stage & Do-Not-Contact Controls
        controls_row = anvil.FlowPanel(spacing="medium", align="left")
        stage_dropdown = m3.DropdownMenu(
            label="Pipeline Stage",
            items=PIPELINE_STAGES,
            selected_value=lead.get("status", "new_enquiry"),
        )
        stage_dropdown.set_event_handler(
            "change",
            lambda **e: self._handle_stage_change(lead["lead_id"], stage_dropdown.selected_value),
        )
        controls_row.add_component(stage_dropdown)

        is_dnc = bool(contact.get("do_not_contact"))
        btn_dnc = m3.Button(
            text="Allow Contact Again" if is_dnc else "Mark Do Not Contact",
            icon="mi:check_circle" if is_dnc else "mi:block",
            variant="outlined",
        )
        btn_dnc.set_event_handler(
            "click",
            lambda **e: self._handle_dnc_toggle(contact["contact_id"], not is_dnc),
        )
        controls_row.add_component(btn_dnc)

        btn_r2_history = m3.Button(
            text="Load R2 Archive",
            icon="mi:cloud_download",
            variant="text",
        )
        btn_r2_history.set_event_handler(
            "click",
            lambda **e: self._load_r2_archive(contact["contact_id"]),
        )
        controls_row.add_component(btn_r2_history)

        header_box.add_component(controls_row)
        header_card.add_component(header_box)
        self.right_pane.add_component(header_card)

        # --- 2. CONVERSATION THREAD (IMMUTABLE AUDIT VIEW) ---
        self.right_pane.add_component(m3.Heading(text="Message History", scale="title"))
        self.thread_panel = anvil.ColumnPanel(spacing="small")
        self.right_pane.add_component(self.thread_panel)

        if not messages:
            self.thread_panel.add_component(m3.Text(text="No messages recorded in active database."))
        else:
            for msg in messages:
                self._append_message_card(msg)

        # --- 3. 1-TO-1 MANUAL REPLY COMPOSER ---
        composer_card = m3.Card(variant="outlined")
        comp_box = anvil.ColumnPanel(spacing="small")
        comp_box.add_component(m3.Heading(text="Send 1-to-1 Reply", scale="title"))

        if is_dnc:
            comp_box.add_component(
                m3.Text(
                    text="This contact is marked Do Not Contact (or replied STOP). All outbound messaging is halted."
                )
            )
        else:
            available_channels = []
            if contact.get("email"):
                available_channels.append(("Email", "email"))
            if contact.get("phone"):
                available_channels.append(("WhatsApp", "whatsapp"))
                available_channels.append(("SMS", "sms"))

            if not available_channels:
                comp_box.add_component(
                    m3.Text(text="No email address or phone number on file for this contact.")
                )
            else:
                default_ch = lead.get("last_channel") if lead.get("last_channel") in [c[1] for c in available_channels] else available_channels[0][1]
                ch_selector = m3.DropdownMenu(
                    label="Reply Channel",
                    items=available_channels,
                    selected_value=default_ch,
                )
                comp_box.add_component(ch_selector)

                reply_box = m3.TextArea(
                    label="Personalised 1-to-1 Message",
                    placeholder="Write your reply (do not include payment links or bulk promotional text)...",
                    rows=4,
                )
                comp_box.add_component(reply_box)

                btn_send = m3.Button(
                    text="Send Reply",
                    icon="mi:send",
                    variant="filled",
                    shape="round",
                )
                btn_send.set_event_handler(
                    "click",
                    lambda **e: self._send_manual_reply(
                        lead["lead_id"],
                        ch_selector.selected_value,
                        reply_box.text,
                    ),
                )
                comp_box.add_component(btn_send)

        composer_card.add_component(comp_box)
        self.right_pane.add_component(composer_card)

    def _append_message_card(self, msg: dict):
        direction = msg.get("direction", "inbound")
        channel = msg.get("channel", "email").upper()
        status = msg.get("status", "")
        delivery = msg.get("delivery_status", "")
        ai_flag = " · AI-Drafted" if msg.get("ai_generated") else " · Human"
        timestamp = msg.get("created_at", "")

        variant = "tonal" if direction == "outbound" else "outlined"
        card = m3.Card(variant=variant)
        box = anvil.ColumnPanel(spacing="tiny")

        header_text = f"{direction.upper()} ({channel}){ai_flag} · {timestamp}"
        if delivery:
            header_text += f" · Delivery: {delivery}"
        elif status:
            header_text += f" · Status: {status}"

        box.add_component(m3.Text(text=header_text))
        if msg.get("subject"):
            box.add_component(m3.Heading(text=msg["subject"], scale="title"))
        box.add_component(m3.Text(text=msg.get("body", "")))

        card.add_component(box)
        self.thread_panel.add_component(card)

    def _handle_stage_change(self, lead_id: str, new_stage: str):
        try:
            anvil.server.call("update_lead_stage", self.workspace_id, lead_id, new_stage)
            m3.Snackbar(message=f"Lead moved to {new_stage.replace('_', ' ').title()}.").show()
            self.load_leads_list()
        except Exception as err:
            m3.Snackbar(message=f"Could not update stage: {err}").show()

    def _handle_dnc_toggle(self, contact_id: str, dnc_state: bool):
        try:
            anvil.server.call(
                "set_contact_do_not_contact",
                self.workspace_id,
                contact_id,
                dnc_state,
            )
            msg = "Contact marked Do Not Contact. Sequences halted." if dnc_state else "Do Not Contact removed."
            m3.Snackbar(message=msg).show()
            self.select_lead(self.selected_lead_id)
        except Exception as err:
            m3.Snackbar(message=f"Error updating contact status: {err}").show()

    def _send_manual_reply(self, lead_id: str, channel: str, body: str):
        clean_body = (body or "").strip()
        if not clean_body:
            m3.Snackbar(message="Please enter a message before sending.").show()
            return
        try:
            anvil.server.call(
                "send_manual_one_to_one_reply",
                self.workspace_id,
                lead_id,
                channel,
                clean_body,
            )
            m3.Snackbar(message=f"Reply sent via {channel.upper()}.").show()
            self.select_lead(lead_id)
        except Exception as err:
            m3.Snackbar(message=f"Send failed: {err}").show()

    def _load_r2_archive(self, contact_id: str):
        try:
            archived = anvil.server.call(
                "fetch_archived_messages_from_r2",
                self.workspace_id,
                contact_id,
            )
            if not archived:
                m3.Snackbar(message="No older archived messages found in Cloudflare R2.").show()
                return
            for msg in archived:
                self._append_message_card(msg)
            m3.Snackbar(message=f"Loaded {len(archived)} archived messages from Cloudflare R2.").show()
        except Exception as err:
            m3.Snackbar(message=f"R2 archive retrieval failed: {err}").show()
