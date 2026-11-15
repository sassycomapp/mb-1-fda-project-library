import anvil.server
import m3.components as m3


class DashboardForm(m3.NavigationRailLayout):
    """Owner Value Dashboard showing leads, response times, bookings, and BYOK spend."""

    def __init__(self, **properties):
        super().__init__(**properties)
        self.rail_style = "expressive"
        self.rail_adaptive = True
        self._build_shell()
        self._load_metrics()

    def _build_shell(self):
        self.top_bar = m3.TopAppBar(title="Performance Dashboard")
        self.btn_refresh = m3.IconButton(icon="mi:refresh")
        self.btn_refresh.set_event_handler("click", lambda **e: self._load_metrics())
        self.top_bar.add_component(self.btn_refresh, slot="actions")
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
                selected=(target == "DashboardForm"),
            )
            link.set_event_handler("click", lambda t=target, **e: anvil.open_form(t))
            self.add_component(link, slot="navigation")

        self.root = m3.ColumnPanel(spacing="medium")
        self.add_component(self.root)

        self.lbl_headline = m3.Heading(
            text="Loading your 30-day front desk summary...",
            scale="small",
        )
        self.root.add_component(self.lbl_headline)

        # KPI Cards Row
        self.kpi_row = m3.FlowPanel(spacing="medium")
        self.card_leads = self._make_kpi_card("Enquiries Captured", "0")
        self.card_speed = self._make_kpi_card("Answered < 15 mins", "0%")
        self.card_booked = self._make_kpi_card("Meetings Booked", "0")
        self.card_followups = self._make_kpi_card("Follow-Ups Due", "0")
        for c in (self.card_leads, self.card_speed, self.card_booked, self.card_followups):
            self.kpi_row.add_component(c)
        self.root.add_component(self.kpi_row)

        # Pipeline Breakdown Card
        pipe_card = m3.Card(appearance="outlined")
        self.pipe_box = m3.ColumnPanel(spacing="small")
        self.pipe_box.add_component(m3.Heading(text="Fixed Pipeline by Stage", scale="small"))
        self.pipe_list = m3.ColumnPanel(spacing="none")
        self.pipe_box.add_component(self.pipe_list)
        pipe_card.add_component(self.pipe_box)
        self.root.add_component(pipe_card)

        # OpenRouter BYOK Spend & Ceiling Card
        ai_card = m3.Card(appearance="outlined")
        ai_box = m3.ColumnPanel(spacing="small")
        ai_box.add_component(m3.Heading(text="OpenRouter BYOK Monthly Spend", scale="small"))
        self.lbl_spend = m3.Text(text="Estimated spend: £0.00 / £20.00 ceiling")
        ai_box.add_component(self.lbl_spend)
        self.prog_spend = m3.LinearProgressIndicator(progress=0.0, wavy=True)
        ai_box.add_component(self.prog_spend)
        ai_card.add_component(ai_box)
        self.root.add_component(ai_card)

    def _make_kpi_card(self, title: str, initial_value: str):
        card = m3.Card(appearance="elevated")
        box = m3.ColumnPanel(spacing="none")
        val_lbl = m3.Heading(text=initial_value, scale="medium")
        title_lbl = m3.Text(text=title)
        box.add_component(val_lbl)
        box.add_component(title_lbl)
        card.add_component(box)
        card.tag.val_lbl = val_lbl
        return card

    def _load_metrics(self):
        try:
            m = anvil.server.call("get_dashboard_metrics")
            leads = m.get("leads_captured", 0)
            booked = m.get("meetings_booked", 0)
            pct_fast = m.get("answered_under_15m_pct", 0)
            due = m.get("followups_due", 0)

            self.lbl_headline.text = (
                f"Your assistant captured {leads} enquiries and booked {booked} calls this month."
            )
            self.card_leads.tag.val_lbl.text = str(leads)
            self.card_speed.tag.val_lbl.text = f"{pct_fast}%"
            self.card_booked.tag.val_lbl.text = str(booked)
            self.card_followups.tag.val_lbl.text = str(due)

            self.pipe_list.clear()
            stages = m.get("pipeline_counts", {})
            stage_labels = [
                ("new_enquiry", "1. New Enquiry"),
                ("responded", "2. Responded"),
                ("meeting_booked", "3. Meeting Booked"),
                ("proposal_quote", "4. Proposal / Quote"),
                ("won", "5. Won"),
                ("lost", "6. Lost / Not a Fit"),
            ]
            for key, label in stage_labels:
                count = stages.get(key, 0)
                item = m3.ListItem(
                    headline_text=label,
                    supporting_text=f"{count} active lead(s)",
                    trailing_text=str(count),
                )
                self.pipe_list.add_component(item)

            spend = float(m.get("byok_spend_gbp", 0.0))
            ceiling = max(float(m.get("byok_ceiling_gbp", 20.0)), 1.0)
            ratio = min(spend / ceiling, 1.0)
            self.lbl_spend.text = f"Estimated spend: £{spend:.2f} / £{ceiling:.2f} monthly ceiling"
            self.prog_spend.progress = ratio
        except Exception as exc:
            m3.Snackbar(message=f"Could not load dashboard metrics: {exc}").show()
