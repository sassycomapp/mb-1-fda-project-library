---
title: "mb-1-fda-concept"
updated: "2026-11-17"
doc-id: "mb-cb01f21c"
---
# Mybizz FDA — Concept

**Front Desk Assistant · mybizz.live**

---

## Purpose of this document

This document is the concept of Mybizz FDA (Front Desk Assistant): what the business is, who it serves, what the product does, the rules it never breaks, and the operational, design and architectural parameters it is built within. Every statement in it is a decision.

Every feature of Mybizz FDA is named and numbered in section 6. The client-facing list of every feature is `mb-1-fda-feature-list.md`. The same feature number and name are used in `mb-1-fda-architecture-explainer.md`, which explains how each feature is built, and in `mb-1-fda-architecture-reference.md`, which specifies each feature for the build. Where a technical fact is stated, `mb-1-fda-architecture-reference.md` is the standard.

---

## 1. What Mybizz FDA Is

Mybizz FDA is an AI front desk for consulting businesses and service businesses, sold as a subscription. Mybizz FDA is one of the Mybizz businesses, with the slug `mb-1-fda`.

Mybizz FDA captures every enquiry, replies in the client's voice, records the customer, offers real meeting times, books the meeting and follows up one to one when the customer goes quiet.

Mybizz FDA is the proof of concept and minimum viable product of Mybizz CS. Mybizz FDA and Mybizz CS are separate products with separate sign-ups. Mybizz FDA's income funds Mybizz-Live Ltd and Mybizz CS.

**Promise:** never miss a qualified enquiry again. The front desk responds, books calls and follows up, using the client's email, website, WhatsApp, SMS and calendar, under the client's rules.

---

## 2. The Problem Mybizz FDA Solves

- A small consulting or service business loses work because enquiries arrive on several channels and wait hours or days for a reply.
- The person who should reply is busy delivering work, so the fastest competitor wins the enquiry.
- Booking a first call takes several messages back and forth.
- Customers who go quiet are never followed up.
- The business has no clear picture of how many enquiries came in, how fast they were answered, who handled them and how many became meetings.

---

## 3. Who Mybizz FDA Serves

- Independent consultants and coaches.
- Small agencies: marketing, design, development, recruitment, advisory, accounting and bookkeeping.
- Fractional executives, advisers and professional-service firms.
- Service businesses that book appointments.
- Size: one person to a team of about ten.
- Markets: the United Kingdom, the United States, Canada and Europe (the EU, the EEA and Switzerland). Registration accepts only businesses in these markets.

**The common workflow Mybizz FDA serves:** enquiry → qualified reply → booking → one-to-one follow-up → a clear view of the pipeline.

---

## 4. Names Used in This Document

The Mybizz nomenclature applies ([[[default:specifications-global/spec-nomenclature]]](C:/dev/project-library-global/specifications-global/spec-nomenclature.md)).

- **Mybizz:** the brand, used in every product, document and message.
- **The operator:** the legal party behind Mybizz FDA, named wherever a legal party is named (agreements, Paddle, policies and invoices). The operator is David trading as Mybizz, a sole proprietor, until Mybizz-Live Ltd is registered; Mybizz-Live Ltd is the operator from then on.
- **The developer:** David, who builds Mybizz FDA through PDLF.
- **Client:** the business or individual that subscribes to Mybizz FDA and is given its own client instance.
- **Owner:** the person responsible for a client instance: the client who signed up, once onboarded.
- **Roles:** Owner, Manager, Admin, Staff and Customer, the same as in every Mybizz application ([[[default:specifications-global/spec-security-architecture]]](C:/dev/project-library-global/specifications-global/spec-security-architecture.md)). In Mybizz FDA, customers never sign in, so the Customer role holds no users.
- **Team member:** a user with the role Owner, Manager, Admin or Staff.
- **Customer:** a client's own customer, including a person who contacts the client for the first time.
- **Visitor:** someone viewing a client's public website without logging in.
- **Channel:** a route an enquiry arrives by and a reply leaves by: email, web form, webchat, WhatsApp or SMS.
- **WhatsApp:** Meta's messaging service. It is unrelated to "WhatsUp", the team's voice control of Mybizz CS.

---

## 5. Hard Rules

These rules hold in every feature, every screen and every line of code. No setting can switch them off.

1. **One to one only.** Mybizz FDA never sends marketing campaigns, cold outreach or bulk messages on any channel. Every outbound message answers or follows up one customer's own conversation. Sending to a list is impossible by design, and hard hourly sending limits apply to every channel.
2. **No payments.** Mybizz FDA never takes payments, creates payment links, or asks for or stores card, bank or other financial details of a customer.
3. **Approve before send by default.** A new client starts in approve-before-send mode. The AI never sends prices beyond the client's approved "from" prices, proposals, contracts, commitments or sensitive replies without a team member's approval, in any mode.
4. **Opt-out is immediate.** When a customer replies STOP, UNSUBSCRIBE or an equivalent on any channel, or a team member marks the customer "do not contact", every automated message to that customer stops at once and the customer receives nothing further.
5. **Nothing is overwritten.** An inbound message, an AI draft, a team member's edit and a sent message are each stored as a separate record. Nothing that was received or approved is ever changed.
6. **Every action has a name on it.** Every approval, edit, send, booking and change records the team member who made it, or records that the AI or the system made it.
7. **The model proposes; the application decides.** The AI suggests a classification, extracted details and a draft. Application code validates every field. Calendar logic, not the AI, decides which times are free and creates the booking.
8. **Facts come only from the client.** Every factual claim in a reply comes from the client's approved business profile, services, saved replies, FAQs and calendars. The AI never invents prices, guarantees, delivery dates or advice.
9. **The AI says it is an AI.** Every webchat opens with a line telling the customer that the customer is talking to the business's AI assistant.
10. **Failures are visible.** A disconnected channel, a failed send, an AI error or a spending ceiling reached creates a high-priority item in the action queue. Nothing fails silently.
11. **Every inbound connection is verified.** Every webhook (a message one system sends to another when something happens) is checked by its signature or secret before it is accepted.
12. **No voice cloning.** Mybizz FDA never copies or imitates a real person's voice.

---

## 6. The Product — Feature Set

Each feature is numbered. The same number and name are used in every later Mybizz FDA document.

### F-01 Accounts, roles and sign-in
- Anvil Users service; two-factor authentication required for every team member.
- Every team member is included in the price. The number of users in each role follows the per-instance limits of [[[default:specifications-global/spec-security-architecture]]](C:/dev/project-library-global/specifications-global/spec-security-architecture.md).
- Roles follow [[[default:specifications-global/spec-security-architecture]]](C:/dev/project-library-global/specifications-global/spec-security-architecture.md). The Owner controls settings, channels, AI, storage and billing; the other roles work the inbox, the action queue and bookings within the rights their role gives.
- A lost second factor is reset by the user by email; Mybizz does not reset it.

### F-02 Setup wizard
- A guided wizard of no more than 15 minutes turns the Owner's answers into a working front desk.
- Order: business basics; tone of voice and signature; services, "from" prices and qualifying questions; lead rules (qualified, urgent, politely declined); team members and their calendars; channel connections; storage; approval policy and the one-to-one pledge; follow-up rules; contact import from CSV with consent confirmed; the privacy notice and AI line for the client's website.
- It ends on a "Your front desk is live" screen: channel status, booking link, a test enquiry run end to end, the first AI draft, the contact created and the follow-up status.

### F-03 Business profile, knowledge and saved replies
- Business description, audience, tone (warm, formal, concise or technical), signature and prohibited claims.
- Service catalogue: name, duration, "from" price, delivery expectation, ideal client, qualifying questions and the team members who deliver the service.
- FAQs: approved questions and answers.
- Saved replies: every company-approved reply and message is kept in a library for reuse.
- When a customer asks a question the profile, FAQs and saved replies do not answer, the AI drafts an answer for approval; on approval, a team member saves the answer to the FAQs with one click.
- A structured profile only; no search across large document libraries.

### F-04 Email channel
- The client forwards enquiries from its business mailbox (Gmail, Microsoft 365 or any provider) to a unique Mybizz FDA inbound address. Mybizz receives the mail through Amazon SES.
- A client with its own domain verifies the domain once, by adding three records to its domain settings; replies then go out from the client's own address through Amazon SES, threaded to the original enquiry.
- A client without its own domain sends replies from a Mybizz FDA address carrying the client's business name, with the client's own address set as the reply address, so the customer's answer reaches the client's mailbox.

### F-05 Web form channel
- An enquiry form that the client places on its own website by pasting one line of code once.
- Spam protection; a link to the client's privacy notice beside the form.

### F-06 Webchat channel
- A chat bubble that the client places on every page of its own website by pasting one line of code once.
- The chat opens with the AI line (Hard Rule 9) and a link to the client's privacy notice.
- The customer leaves an email address or phone number so the conversation can continue after the visit; the conversation becomes a contact and lead like any other channel.

### F-07 Voice in webchat
- A microphone button in the webchat. The customer speaks; Groq Whisper turns the speech into text; the AI replies; the reply is shown and read aloud.
- The reply is read aloud in the browser's own voice by default. The client may switch on a natural-sounding voice (Groq's speech service) and choose from its stock voices.

### F-08 WhatsApp channel
- Meta's official WhatsApp Business Platform (Cloud API).
- The operator is a Meta Tech Provider. The Owner connects the client's WhatsApp number in the setup wizard through Meta's Embedded Signup in a few minutes, and may keep using the WhatsApp Business app on the phone at the same time where Meta allows it.
- Each client's WhatsApp messages are delivered by Meta straight to that client's own instance (a callback address set per phone number).
- The client holds its own WhatsApp Business account and pays Meta directly for messages.
- Messages sent more than 24 hours after the customer's last message use Meta-approved templates, as Meta requires.
- The WhatsApp channel is built in full and stays switched off until Mybizz-Live Ltd is registered and verified by Meta.

### F-09 SMS channel
- SMS is sent and received through the client's own Android phone and number, running the SMSGate app in its cloud server mode. The Owner enters the SMSGate details in the wizard; Mybizz FDA registers its webhook.
- SMSGate's end-to-end message encryption and signed webhooks are switched on.
- Mybizz FDA checks the phone's health every 15 minutes.

### F-10 Enquiry handling
- WhatsApp, SMS and webchat messages arriving in a quick burst are combined into one enquiry after a short wait (12 seconds).
- Duplicate deliveries are ignored.
- The customer is matched to an existing contact by email or normalised phone number, or a new contact is created.
- The AI classifies the enquiry (new lead, existing client, supplier, spam, unsupported), extracts the details and drafts a reply in the language the customer wrote in.
- Urgent or high-value enquiries notify the assigned team member and the Owner.
- The reply goes back on the channel the enquiry came in on.

### F-11 Approval modes and action queue
- Three modes: draft only (a team member sends); approve before send (default; one-click approval); autonomous for selected low-risk actions (acknowledgements, booking confirmations and reminders), with Hard Rule 3 always in force.
- The action queue is the main screen: "the things that need you today", with approve, edit and send, reject with a reason, dismiss and snooze.
- Every item records who approved, edited, rejected or sent it (Hard Rule 6).

### F-12 Contacts and leads
- Contact: name, email and/or phone (at least one), company, source channel, tags, consent and do-not-contact status.
- Lead: contact, service interest, urgency, summary, assigned team member, next action and its date.
- Fixed stages: New enquiry → Responded → Meeting booked → Proposal/quote → Won → Lost / not a fit, plus Stalled after the final follow-up. Stages are not customisable; tags are.
- Notes and a full communications log on every customer, across every channel.

### F-13 Booking
- Each team member connects the team member's own Google Calendar.
- The Owner sets working hours, meeting types, durations, buffers and booking links, for each team member and for the company.
- A customer assigned to a team member is offered that team member's free times.
- A customer not yet assigned is offered the company's free times across the team members who deliver the service; the team member who is booked becomes the assigned team member.
- Free times are calculated from the calendars in the client's own time zone; the customer's choice is booked by calendar logic.
- Confirmation, reminder, reschedule and cancellation are handled, and the lead stage updates with them.

### F-14 One-to-one follow-up
- When a customer has not replied after the Owner's set delay, a short, non-pushy follow-up goes on the same conversation.
- Follow-ups stop on any reply, on opt-out, or after the set number of attempts; the lead then becomes Stalled.
- Post-meeting follow-up drafts are created for the assigned team member.

### F-15 AI with the client's own key
- The client brings its own OpenRouter key (BYOK). Mybizz does not resell AI for replies.
- Three presets: Fast, Balanced (default) and Premium.
- A key test in the wizard, a monthly spending ceiling, and a usage page showing actions, model and estimated spend.
- When the key fails, the quota runs out or the model keeps failing, Mybizz FDA falls back to draft-only and tells the Owner.
- Prompts and AI replies are never logged; only metadata and redacted diagnostics are kept.
- Voice transcription and the natural-sounding voice (F-07) run on Groq, paid by Mybizz.

### F-16 Dashboard
- Enquiries answered within 5, 15 and 60 minutes; meetings booked; show rate; follow-ups completed; stage movement; drafts approved without major edits; AI success and failure reasons; channel and backup errors.
- Statistics for each channel.
- An activity log for each team member.
- A link from every customer to that customer's full communications log (F-12).

### F-17 Data, backups and history
- The client's data store is the client's own Cloudflare R2 account. During registration the client opens a free Cloudflare account, switches R2 on and invites Mybizz's Cloudflare user; Mybizz then creates the client's bucket and a key that reaches that bucket only.
- A nightly backup of the client's data goes to the client's R2 account.
- The audit trail and raw webhook records stay in the app for 30 days, then move to the client's R2 account.
- The client can export all its data at any time. The client keeps its R2 account, and with it its data, when it leaves.

### F-18 Help, tooltips and in-app guidance
- The Mybizz always-available controls on every page: a tooltips on/off button, a tooltip on every actionable component, a help video menu for the page, and a dashboard quick-link; the dashboard has a clear Return button.
- Short, single-topic help videos replace a guided setup call.

### F-19 Language
- The AI replies to each customer in the language the customer wrote in.
- The screens and help videos are in English at launch. French, German, Spanish and Italian are added one at a time, on the Mybizz phrase-key translation pattern, and the client chooses the screen language.

### F-20 Plan and billing
- One fixed monthly price for every client, with every team member included.
- Sold and billed through Paddle and managed in the Mybizz management app (F-21).
- Month to month, no contract. Non-payment leads to a short grace period, then suspension; the client's data is never withheld.
- Mybizz may credit the unused part of a client's paid Mybizz FDA term to a new Mybizz CS account, as an administrative action.

### F-21 Mybizz management app
- One management app (App 5) serves every Mybizz business, Mybizz FDA included.
- It creates, updates, suspends and removes Mybizz FDA client instances, receives Paddle notifications, and shows each client's health (channels, backups, errors).
- It holds only basic contact details of each client, the client's Paddle references, the subscription status and a minimal billing log. Paddle holds all payment data.

---

### F-22 Mybizz's own front desk
- Mybizz runs its own Mybizz FDA instance as the front desk of mybizz.live. A prospective client tests Mybizz FDA by sending an enquiry through the mybizz.live web form or webchat and receiving the reply.

---

## 7. Price and Sales

- **Price:** one fixed monthly price of £45, with every team member included. Paddle charges a fixed local price in each market: £45 (United Kingdom), $59 (United States), C$79 (Canada), €55 (Europe) and CHF 55 (Switzerland).
- **No other plans:** no annual plan, no setup fee, no founding offer and no add-ons sold by Mybizz.
- **Costs outside the price, paid by the client directly:** AI use on the client's own OpenRouter key; WhatsApp messages charged by Meta; SMS charged by the client's phone plan; R2 storage above Cloudflare's free tier.
- **Trial:** a prospective client tests Mybizz FDA on Mybizz's own front desk (F-22).
- **Separate from Mybizz CS:** a Mybizz FDA client who wants Mybizz CS signs up to Mybizz CS separately; Mybizz may credit the unused part of the client's paid Mybizz FDA month to the new Mybizz CS account.

---

## 8. Brand

- **Brand:** Mybizz. **Product name:** Mybizz FDA, written in full as Mybizz Front Desk Assistant.
- **Primary message:** Never miss a qualified enquiry again.
- **Supporting message:** Your AI front desk replies in your voice, books the call and follows up, and nothing goes out without your approval until you say so.
- **Tone:** clear, calm, practical and honest; no technical jargon, no hype and no promises the product cannot keep.
- **Look:** Professional Blue, Roboto and Material Design 3, as `brand-profile.md` sets out.
- **Founder story:** a project manager who ran life-support operations at remote sites, from the Congo jungle to Antarctica, where systems had to be simple, self-contained and dependable.

---

## 9. What Mybizz FDA Is Not

- Not a marketing tool: no campaigns, broadcasts, cold outreach or list sending, ever.
- Not a payment or invoicing tool.
- Not a general-purpose chatbot or a custom agent builder; the AI answers enquiries within Hard Rules 7 and 8.
- Not a full CRM: no custom objects, custom pipelines or complex permissions.
- Not a website builder or landing-page builder.
- No voice calls, Instagram or LinkedIn messages.
- No native mobile apps; Mybizz FDA is a web application that works on every screen size.
- No white-label agency portal and no deep third-party CRM integrations.

---

## 10. Architectural Parameters

### 10.1 The five-app structure

| App | Name | Role | Runs on |
|---|---|---|---|
| App 1 | `mb-1-fda-app1` | Development workspace; built by PDLF | Mybizz's Anvil account (Anvil.works) |
| App 2 | `master_template` | Release of App 1; the dependency that holds all logic and forms | Mybizz's Anvil account |
| App 3 | `blank_client_template` | Client instance template: startup module, table definitions, scheduled tasks, Users settings; no forms or server modules | Mybizz's Anvil account |
| App 4 | `[client-name]-fda` | One client instance per client, built from App 3 and depending on App 2; its release image is defined in `mb-1-fda-app4` | Anvil App Server (the open-source Anvil runtime) on Hetzner Cloud: one container and one database per client |
| App 5 | Mybizz management app | One management app for every Mybizz business | Mybizz's Anvil account |

### 10.2 One client, one instance, one database
- Mybizz FDA is never multi-tenant. Every client has its own instance and its own database, and stores its data in its own R2 account. No table carries a client column, because each instance holds one client only.
- Every channel delivers straight to the client's own instance: email by its unique inbound address, WhatsApp by its per-number callback address, SMS by its registered webhook, web form and webchat by the client's own code line.

### 10.3 Hetzner hosting
- Client instances run on Hetzner Cloud servers in the EU, each client in its own container running the Anvil App Server at the one version Mybizz pins, with its own PostgreSQL database.
- Every container runs the same release image, holding App 3, App 2 and the `m3` theme.
- Mybizz runs these servers itself, so the design covers operating-system security updates, container restarts, monitoring and alerts, nightly database backups held off the server, and restore.
- Each instance answers over HTTPS at its own address, `[client-name].fda.mybizz.live`. Mybizz FDA has no public website of its own for a client, so a client needs no domain for its instance.

### 10.4 No messaging servers
- Mybizz FDA runs no messaging gateway, no queue server and no cache server.
- WhatsApp runs on Meta's Cloud API; email on Amazon SES; SMS on the client's phone through SMSGate.
- Burst handling, duplicate checks, follow-up timing and health checks use Anvil Data Tables, Anvil background tasks and Anvil scheduled tasks.

### 10.5 Platform and code standards
- Built on Anvil to the Anvil standard (the `anvil-docs` compilation in `project-library-global` and Anvil Agent References) and to `project-library-global` specifications, ADRs and policies.
- Secrets live in Anvil App Secrets and the Mybizz Vault; client credentials (OpenRouter key, SMSGate password, R2 key, Google and Meta tokens) are stored encrypted.
- Server functions are written first; every client call goes through a server function that checks the signed-in user's role.
- Python version and packages match across App 1 and the App 4 release image.

### 10.6 External services

| Service | Used for | Paid by |
|---|---|---|
| Anvil | Apps 1, 2, 3 and 5; App Server runtime for App 4 | Mybizz |
| Hetzner Cloud | App 4 servers and databases | Mybizz |
| Cloudflare R2 | The client's backups and history, in the client's own account | Client (free tier covers typical use) |
| Amazon SES | Email channel, inbound and outbound | Mybizz |
| Meta WhatsApp Cloud API | WhatsApp channel | Client, directly to Meta |
| SMSGate | SMS channel through the client's phone | Client's phone plan |
| Google Calendar API | Booking | Free |
| OpenRouter | AI replies, with the client's own key | Client, directly to OpenRouter |
| Groq | Voice transcription and natural-sounding voice | Mybizz |
| Paddle | Subscription billing | Mybizz (fee per sale) |

---

## 11. Design Parameters

- Material Design 3 through `m3-custom-theme`, the package `m3`, making full creative use of its components. Anvil's own M3 theme is never used.
- Forms are built per feature by `mb-form-builder` from approved screen requirements, after the feature's server functions exist.
- Professional Blue is the default palette. The client may choose any of the eight `m3-custom-theme` palettes in Settings. Light and dark mode follow the device. Roboto throughout.
- Working screens: action queue (home screen), inbox and customer record, approval, calendar and booking, follow-ups, saved replies and FAQs, dashboard, settings and setup wizard.
- Mybizz FDA does not open on a chat screen; the action queue is home.
- The web form and webchat follow the client's chosen palette.
- Accessible to WCAG AA.

---

## 12. Operational Parameters

- **Operator:** David trading as Mybizz, a sole proprietor, until Mybizz-Live Ltd is registered. Paddle and Wise serve the operator in both forms.
- **Legal documents published by the operator:** terms of service, privacy policy, data processing agreement, sub-processor list and acceptable use policy (holding the one-to-one rule). The client accepts them at sign-up.
- **Legal notices shown by the client:** a privacy notice on the client's website, linked beside the web form and in the webchat, and the AI line in every webchat. The setup wizard supplies ready-made wording for both.
- **Compliance:** UK GDPR and EU GDPR, with the operator as processor and the client as controller; UK PECR and equivalent opt-out rules; Meta's WhatsApp Business policies; Google's API user-data policy; encryption in transit and at rest; no client data used to train AI models.
- **Releases:** every release passes the full test suite in App 1, is released to App 2, and reaches every client instance through the release image.
- **Support:** self-service first, through tooltips and help videos; direct support by email. Mybizz does not reset clients' second factors.
- **Monitoring:** channel health every 15 minutes; nightly backup status, AI errors and spending ceilings appear in the client's action queue and in App 5; server health alerts reach the developer.
- **Client exit:** the client exports its data and keeps its R2 account; the instance, database and channel connections are then removed.

---

## 13. How Mybizz FDA Is Built

- Mybizz FDA enters PDLF at Step 3, new application with context. Its context is the existing material in `mb-1-fda-project-library`, read as intent.
- PDLF Step 11 moves the context into the project library's standard structure; Step 12 designs from this concept and the rest of the context.
- The context is this concept, `mb-1-fda-architecture-reference.md` (for the agent; the technical standard), `mb-1-fda-architecture-explainer.md` (for the developer), `mb-1-fda-feature-list.md`, `authoritative-schema.md`, `brand-profile.md` and `legal-policies.md`. PDLF adds user flows, screen requirements, specifications, ADRs and policies as the Mybizz project library structure requires.
- Every feature number F-01 to F-22 appears in this concept and in both architecture documents.
- Code files never carry front matter; documents carry `title`, `doc-id` and `updated`.

---

## 14. Success Measures

- A client goes from sign-up to a live front desk in under 30 minutes.
- Enquiries are answered within minutes, measured at 5, 15 and 60 minutes.
- No message is ever sent to a customer who opted out.
- No silent failure: every failure appears in the action queue.
- Clients see, on the dashboard, enquiries answered, meetings booked, activity by channel and activity by team member each month.

---

## 15. Risks and How Mybizz FDA Answers Them

| Risk | Answer |
|---|---|
| A WhatsApp number is banned | Only Meta's official Cloud API is used, one to one only, with opt-out enforced |
| The AI writes something wrong | Approve before send by default; facts only from the client's own content; nothing overwritten, and every action carries a name |
| AI costs run away | The client's own key with a monthly ceiling and draft-only fallback |
| The client's phone is off, so SMS stops | Health check every 15 minutes; a high-priority item in the action queue |
| Customer data leaks between clients | One instance and one database per client; cross-client access is impossible by design |
| A Hetzner server fails | Nightly database backups held off the server, monitoring alerts to the developer and a tested restore procedure |
| Spam floods the web form or webchat | Spam protection on both, rules first, then AI classification |
| Mail provider rules block access | The email channel uses forwarding and Amazon SES, not mailbox-reading permissions |
