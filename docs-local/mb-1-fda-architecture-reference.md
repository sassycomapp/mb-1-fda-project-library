---
title: "mb-1-fda-architecture-reference"
updated: "2026-11-17"
doc-id: "mb-ff6bca53"
---
# Mybizz FDA — Architecture Reference

## 0. Authority

This document is the build standard for the architecture of Mybizz FDA. Agents build from this document. Where `mb-1-fda-concept.md` or `mb-1-fda-architecture-explainer.md` differs from this document on a technical fact, this document is correct. Where this document differs from `mb-1-fda-concept.md` on intent (what the product does, for whom, under which rules), the concept is correct and this document is corrected.

Every feature carries the number and name it has in `mb-1-fda-concept.md` section 6 (F-01 to F-22); the client-facing list is `mb-1-fda-feature-list.md`. Detail that has its own home is linked, not repeated:

| Subject | Home |
|---|---|
| Data tables and fields | `authoritative-schema.md` |
| Brand and visual identity | `brand-profile.md`; palette colour values in `m3-custom-theme` |
| Legal texts shown to clients and customers | `legal-policies.md` |
| Roles and access | [[[default:specifications-global/spec-security-architecture]]](C:/dev/project-library-global/specifications-global/spec-security-architecture.md) |
| The Vault | [[[default:specifications-global/spec-vault-system]]](C:/dev/project-library-global/specifications-global/spec-vault-system.md) |
| Names | [[[default:specifications-global/spec-nomenclature]]](C:/dev/project-library-global/specifications-global/spec-nomenclature.md) |
| Anvil platform rules | [[[default:specifications-global/spec-anvil-platform-standards]]](C:/dev/project-library-global/specifications-global/spec-anvil-platform-standards.md) |
| UI rules | [[[default:specifications-global/spec-ui-standards]]](C:/dev/project-library-global/specifications-global/spec-ui-standards.md) |

---

## 1. The Five-App System

The five-app model is Mybizz-wide ([[[default:specifications-global/spec-five-app-architecture-model]]](C:/dev/project-library-global/specifications-global/spec-five-app-architecture-model.md)). This section is the Mybizz FDA instance of that model.

| App | Role | Repository | Hosted on | Web address |
|---|---|---|---|---|
| App 1 | Development workspace | `mb-1-fda-app1` | Mybizz's Anvil account | `mb-1-fda-app1.mybizz.live` |
| App 2 | `master_template` — the published dependency | `mb-1-fda-app2` | Mybizz's Anvil account | none |
| App 3 | `blank_client_template` — the client app | `mb-1-fda-app3` | Mybizz's Anvil account | none |
| App 4 | Client instances, one per client | release image defined in `mb-1-fda-app4` | Hetzner Cloud: one container and one database per client | `[client-name].fda.mybizz.live` |
| App 5 | Mybizz management app, shared by every Mybizz business | the Mybizz management app's repository | Mybizz's Anvil account | the Mybizz management app's address |

### App 1 — development workspace
- All feature development happens here. Holds every data table (development and test data), every form, every server module and all application code.
- Connected to GitHub as the shared source of truth between Anvil and the local copy agents work in.
- Each release is tagged here. Never a dependency for any client instance.

### App 2 — `master_template`
- The sole source of all server-side logic and all forms for every client instance.
- Receives App 1's tagged release.
- Stateless: holds no client data.
- Built into the release image with App 3.

### App 3 — `blank_client_template`
- The client app every client instance runs.
- Holds the full table definitions (no data), one startup module, the scheduled tasks, the Users service settings and `master_template` as a dependency. Zero server modules, zero forms.
- Each client's App Server builds the client's tables from App 3's table definitions and adds each release's new tables and columns.

### App 4 — client instances
- Each client instance runs on the Anvil App Server, unmodified, at the one version Mybizz pins, as one container named `[client-name]-fda` on a Mybizz Hetzner Cloud server, with its own database in Mybizz's Ubicloud managed PostgreSQL service (section 4).
- Runs the release image: App 3, `master_template` and the `m3` theme. Nothing else.
- Updated through the release image: App 5's Release action moves every client instance to each new release.
- The test client instance is a client instance of its own, holding test data only.
- Clients never have access to the container, the database, the server or any source code.

### App 5 — Mybizz management app
- One management app serves every Mybizz business. For Mybizz FDA it registers clients, provisions, releases to, suspends and removes client instances, receives Paddle notifications and shows each client's health (F-21).
- Communicates with client instances through HTTP endpoints secured with a per-client Bearer token ([[[default:specifications-global/spec-api-specification]]](C:/dev/project-library-global/specifications-global/spec-api-specification.md)).
- Reaches the Hetzner servers only through the provisioning runner (section 5).
- Holds client-level records only: the client's business name, contact name, email address, phone number and billing address, the Paddle customer and subscription references, the subscription status, the instance address, usage and health figures, and a minimal billing log. Payment data stays with Paddle.

---

## 2. Rule: No Forms or Server Modules in App 3

Every client instance runs App 3 on `master_template`. A form or server module added to App 3 silently overrides `master_template` for every client, and later fixes to that form or module stop reaching clients.

- App 3 holds only its startup module, table definitions, scheduled tasks and Users settings.
- A change needed for one client is made in App 1, tested on the test client instance, and released into `master_template`; every client instance then receives it.
- App 3's repository and `mb-1-fda-app4` carry a README stating this rule ([[[default:adr-global/adr-client-instance-readme-five-app-system]]](C:/dev/project-library-global/adr-global/adr-client-instance-readme-five-app-system.md)).

---

## 3. Data Isolation

- Each client instance is a separate App Server with a separate database. `app_tables` always resolves to the current client's data. Cross-client access is architecturally impossible.
- No table carries a client or workspace column.
- `master_template` holds no client data. All state lives in the client's own database and the client's own R2 bucket.
- Mybizz does not copy a client's customer data into App 5.
- Each client's database has its own database user, which can reach that database only.

---

## 4. Hosting (Hetzner Cloud)

### 4.1 Servers
| Server | Role | Notes |
|---|---|---|
| Application server(s) | `CPX42`; runs the client containers, Caddy and the provisioning runner | Ubuntu LTS; Docker; Hetzner firewall allows ports 22 (SSH, key only, from the developer's addresses), 80 and 443 |
| Database service | Mybizz's Ubicloud managed PostgreSQL, shared by every Mybizz business: one database and one database user per client, with a standby promoted automatically if the primary fails | Accepts connections only from Mybizz's Hetzner servers, over TLS with full verification |

- Region: Hetzner Nuremberg for the application servers; Ubicloud Germany for the database service. Hosting follows `spec-client-instance-hosting` in `project-library-global`.
- Hetzner automated server backups are switched on for every server.
- Operating-system security updates install automatically (`unattended-upgrades`); a reboot that an update needs happens in the Sunday 06:00 UK maintenance window.

### 4.2 Client containers
- One Docker container per client from the release image, named `[client-name]-fda`, started with the client's database address, the instance's `encryption_key` and its origin `https://[client-name].fda.mybizz.live`.
- Memory: 1 GiB to start; App 5 raises a container to 2 GiB above 80% memory use and messages the developer. App 5 never reduces a size.
- Caddy, the reverse proxy on each application server, gives every instance its HTTPS certificate automatically and routes `[client-name].fda.mybizz.live` to the client's container.
- DNS: a wildcard record `*.fda.mybizz.live` in Cloudflare points to the application server.

### 4.3 Capacity and fair use
| Resource | Limit per client | Action at the limit |
|---|---|---|
| Database connections | 3 per database user | Further requests queue |
| Query time | 60 seconds | Query cancelled and logged |
| Idle open transaction | 120 seconds | Session ended |
| Database size | Warning at 1 GiB; limit 2 GiB | Imports pause; developer notified |
| Container memory | Warning at 80% of 1 GiB; limit 2 GiB | App 5 raises to 2 GiB; developer notified above that |
| Outbound messages, every channel | Hard hourly limit per channel (section 12, F-10) | Further sends refused and queued for the next hour |
| Data transfer | Warning at 150 GB a month; limit 500 GB | Client and developer notified |

The database limits are held by PostgreSQL on each client's database user; App 5 measures the rest.

### 4.4 Monitoring
- Every client instance reports its memory, database size, message volumes, channel health and last team-member sign-in to App 5 on a schedule.
- UptimeRobot calls App 5's status endpoint every 5 minutes and alerts the developer if App 5 fails or a client instance has not reported for 30 minutes.
- Disk use above 75% on any server alerts the developer.

### 4.5 Backups and restore
- Nightly at 02:00 UTC each client instance writes an encrypted backup of its data to the client's own R2 bucket (F-17).
- R2 Object Lock keeps daily backups for 7 days and weekly backups for 28 days, so no key can delete them early.
- Ubicloud backs up the database service continuously, kept 7 days with restore to any minute; Hetzner server backups cover the application servers.
- Each month the test client instance restores one client backup into a scratch database, checks the row counts against the source and drops the scratch database.

---

## 5. Provisioning, Registration and Exit (F-02, F-21)

### 5.1 The provisioning runner
- A small Python service, the provisioning runner, runs on the application server and connects out to App 5 through Anvil Uplink. No inbound port is opened for it.
- The runner exposes only these functions to App 5: create instance, release instance, resize container, suspend instance, resume instance, remove instance, and report server health.
- Each function uses fixed commands with checked arguments; the runner never runs free-form commands.

### 5.2 Registration
1. The client registers on mybizz.live and pays through Paddle checkout. App 5 creates the client record.
2. As part of registration, the client opens a free Cloudflare account in the client's own name, switches R2 on and invites Mybizz's Cloudflare user as a member with access to R2 only.
3. App 5's New client action, through the runner, creates the client's database and database user, the instance's `encryption_key` and Bearer token, and the container `[client-name]-fda`; the App Server builds the client's tables.
4. App 5 accepts the Cloudflare invitation, creates the client's R2 bucket and a token for that bucket only, creates the client's Amazon SES inbound address, and writes every key into the instance's Vault.
5. App 5 creates the Owner's user and sends the Owner the sign-in link. The Owner completes the setup wizard in the instance (F-02).

### 5.3 Non-payment
Driven by Paddle notifications to App 5: a grace warning on day 1, suspension on day 7 (the instance shows a payment notice and stops all channels), and on day 37 the instance is removed after a final backup to the client's R2 bucket. The client's data is never withheld: the client keeps its R2 bucket.

### 5.4 Exit
On cancellation the instance runs a final backup and export to the client's R2 bucket, the channels are disconnected (webhooks removed, WhatsApp callback removed, SMSGate webhook removed), App 5 removes Mybizz's Cloudflare membership, and the runner removes the container, the database and the database user.

---

## 6. Development Workflow

- Agents work in the local copy of App 1; the developer pushes to GitHub; Anvil syncs from GitHub.
- Changes made in the Anvil Designer are pulled into the local copy before any agent edits code.
- Server functions for a feature are written first; then `mb-form-builder` builds the feature's forms from the approved screen requirements; then the Anvil agent wires the forms to the server functions.
- This workflow applies to App 1 only (section 2).

---

## 7. Package Structure

```
client_code/
  layouts/      shared/       components/   dashboard/
  queue/        inbox/        contacts/     bookings/
  followups/    knowledge/    settings/     onboarding/
  webchat/

server_code/
  server_shared/     server_auth/       server_channels/   server_pipeline/
  server_contacts/   server_bookings/   server_followups/  server_knowledge/
  server_ai/         server_storage/    server_dashboard/  server_settings/
  server_management/ server_webchat/
```

- `server_channels/` holds one module per channel (`email_channel`, `webform_channel`, `whatsapp_channel`, `sms_channel`) with that channel's webhook endpoint, signature check and send function, and the shared outbound rate limit.
- `server_pipeline/` holds enquiry handling (F-10): burst combining, duplicate check, contact matching, AI classification and drafting, validation and routing to the action queue.
- `server_ai/` holds the OpenRouter client (F-15) and the Groq voice client (F-07).
- `server_storage/` holds all Cloudflare R2 access (F-17).
- `server_management/` holds the management HTTP endpoints called by App 5.
- `webchat/` and `server_webchat/` hold the embeddable web form and chat bubble (F-05, F-06, F-07).
- `shared/translations/` holds one phrase file per screen language (F-19).

---

## 8. Module Architecture

The three-tier module pattern (forms, client modules, server modules, pure logic modules) is defined in [[[default:specifications-global/spec-anvil-platform-standards]]](C:/dev/project-library-global/specifications-global/spec-anvil-platform-standards.md) section 3. Every server function a form calls checks the signed-in user's role before doing anything.

---

## 9. Navigation

- Team members use the `m3` `NavigationRailLayout` on wide screens and `NavigationDrawerLayout` on narrow screens, with `NavigationLink` items: Action queue (home), Inbox, Contacts, Bookings, Follow-ups, Knowledge, Dashboard, Settings.
- Every page carries the Mybizz always-available controls (F-18).
- Customers never see the app; they see only the web form and the chat bubble on the client's website (section 11).

---

## 10. Startup and Authentication Routing

- The startup module applies the saved palette and mode, then routes: no signed-in user → sign-in; signed-in user with setup incomplete → setup wizard (Owner only; other roles see a "setup in progress" page); otherwise → action queue.
- Anvil Users service: email and password, two-factor authentication required for every team member, the Owner on FIDO2 ([[[default:specifications-global/spec-security-architecture]]](C:/dev/project-library-global/specifications-global/spec-security-architecture.md)).
- New sign-ups are off; users are created by App 5 (the Owner) or by the Owner (other team members).

---

## 11. The Website Embeds (F-05, F-06, F-07)

- Each instance serves one small script at `https://[client-name].fda.mybizz.live/_/api/embed.js`. The client pastes one script line into its website; the script adds the enquiry form where the client places it and the chat bubble on every page.
- The form and chat talk only to the client's own instance, through HTTP endpoints that accept requests from the domains the client lists in Settings.
- Spam protection: a hidden field, a minimum fill time and a per-address rate limit, then AI classification.
- The chat bubble opens with the AI line (Hard Rule 9) and the client's privacy notice link.

---

## 12. Feature Architecture

### F-01 Accounts, roles and sign-in
- `users` table with role per [[[default:specifications-global/spec-security-architecture]]](C:/dev/project-library-global/specifications-global/spec-security-architecture.md); one Owner and any number of team members in the other roles, per that specification.
- Two-factor reset by email only; Mybizz does not reset second factors.
- Every action that changes data writes an `activity_log` row with the user, or `ai` or `system` (Hard Rule 6).

### F-02 Setup wizard
- One wizard form with a step indicator; each step saves on completion and can be resumed.
- Steps, in order: business basics; tone and signature; services and qualifying questions; lead rules; team members and calendars; channels; storage check; approval policy and one-to-one pledge; follow-up rules; CSV contact import with consent confirmation; website code line, privacy notice and AI line.
- The final step runs a test enquiry through the web form channel end to end and shows the result.

### F-03 Business profile, knowledge and saved replies
- `business_profile`, `services`, `faqs`, `saved_replies`.
- The AI's knowledge for each enquiry is assembled from these tables only, never from free text outside them.
- A new question answered and approved offers "Save to FAQs", which writes a `faqs` row with the approver.

### F-04 Email channel
- Inbound: each instance has the address `[client-name]@in.fda.mybizz.live`. Amazon SES receives mail for `in.fda.mybizz.live`, stores it in an S3 bucket and posts a notification to the instance's email endpoint, which fetches, parses and deletes the stored mail. Raw stored mail is deleted within 7 days at the latest.
- Outbound with a verified domain: SES domain identity with DKIM, SPF and DMARC records that the Owner adds once; replies go from the client's chosen address, threaded with `In-Reply-To` and `References` headers.
- Outbound without a domain: replies go from `[client-name]@reply.fda.mybizz.live` with the client's business name as display name and the client's own address as `Reply-To`.
- SES bounce and complaint notifications set the contact's email as undeliverable and raise an action-queue item.

### F-05 Web form channel
- Endpoint `/_/api/webform`; fields name, email, phone (email or phone required), message, consent; spam protection per section 11.

### F-06 Webchat channel
- Endpoint `/_/api/webchat` holding a conversation per browser session token.
- The AI replies in the chat within the hard rules; a reply the approval mode requires to be approved is shown to the customer as "A team member will reply shortly", and the approved reply is delivered by email or SMS to the details the customer left.
- The chat asks for an email address or phone number before the customer leaves.

### F-07 Voice in webchat
- The microphone records in the browser; the audio is sent to the instance, which sends it to Groq Whisper for transcription and discards the audio.
- The reply is read by the browser's `SpeechSynthesis` by default. With the natural voice switched on, the instance calls Groq's speech service with the voice the client chose and returns the audio.
- Mybizz's Groq key is in the instance's Vault; Groq usage is reported to App 5.
- No voice is ever cloned or imitated (Hard Rule 12).

### F-08 WhatsApp channel
- Meta WhatsApp Cloud API through Meta's Embedded Signup v4 in the setup wizard; the operator is a Meta Tech Provider.
- On completion the instance exchanges the returned code for a business token, stores it in the Vault, registers the phone number, subscribes the operator's Meta app to the client's WhatsApp Business account, and sets the phone number's callback address to `https://[client-name].fda.mybizz.live/_/api/whatsapp` with its own verify token.
- Every webhook is checked against Meta's `X-Hub-Signature-256` header.
- Free-form replies are sent only within 24 hours of the customer's last message; follow-ups after that use approved utility templates.
- A Settings flag `whatsapp_available` is false until Mybizz-Live Ltd is registered and Meta-verified; while false, the WhatsApp step and screens are hidden. The flag is set by App 5 for every instance at once.

### F-09 SMS channel
- SMSGate in cloud server mode; the Owner enters the SMSGate username and password in the wizard; the instance registers its webhook `https://[client-name].fda.mybizz.live/_/api/sms` for `sms:received` and the delivery events.
- SMSGate end-to-end encryption and webhook signing are switched on; the passphrase and signing key are in the Vault; every webhook signature is checked.
- A scheduled task every 15 minutes checks the device's last-seen time; a stale device raises a high-priority action-queue item.

### F-10 Enquiry handling
- Every inbound message is stored first as an `inbound` row in `messages` with its external id; a repeat external id is ignored.
- WhatsApp, SMS and webchat messages from the same sender within 12 seconds of each other are combined: each arrival writes a `pending_bursts` row and starts a background task that waits 12 seconds, and only the task holding the latest arrival processes the burst.
- STOP, UNSUBSCRIBE, STOPALL, END, CANCEL, QUIT and OPT OUT (any case, the whole message) set `do_not_contact` at once and end processing (Hard Rule 4).
- The contact is matched by normalised email or by phone number in E.164 form; otherwise created.
- The AI returns strict JSON: classification, extracted details, urgency, whether the reply needs custom pricing or a commitment, a one-sentence summary and a draft in the customer's language. The server validates every field; a failed validation raises an `ai_error` item.
- Outbound rate limit: 40 messages per hour per channel per instance; a list or batch send function does not exist.

### F-11 Approval modes and action queue
- `approval_mode`: `draft_only` / `approve_before_send` (default) / `autonomous_low_risk`.
- Autonomous sending applies only to acknowledgements, booking confirmations and reminders, and only when the AI marked no custom pricing or commitment and the urgency is normal.
- An edited draft is stored as a new message; the draft row keeps its text and is marked `superseded` (Hard Rule 5).
- Every approval, edit, rejection, dismissal and send records the user and the time.

### F-12 Contacts and leads
- `contacts`, `leads`, `notes`, `tags`; the communications log of a customer is every `messages` row of that contact in time order, across channels.
- Lead stages fixed: `new_enquiry`, `responded`, `meeting_booked`, `proposal_quote`, `won`, `lost_not_fit`, `stalled`.

### F-13 Booking
- Each team member connects Google Calendar through Google OAuth with the `calendar.events` and `calendar.freebusy` scopes; the refresh token is in the Vault.
- Free times: the free/busy of the assigned team member, or the union of the free times of every team member who delivers the service when no team member is assigned, inside working hours and minus buffers, in the client's time zone.
- The AI never proposes a time; the server offers the computed times and creates the event when the customer chooses one.
- Booking changes made in Google Calendar are picked up by a calendar watch per team member and update the appointment and the lead stage.

### F-14 One-to-one follow-up
- A scheduled task every hour selects leads whose next action date has passed, whose contact has no reply since the last outbound message and is not `do_not_contact`, and whose attempt count is below the limit; it drafts the follow-up under the approval mode.
- Any inbound message from the contact stops the sequence.

### F-15 AI with the client's own key
- OpenRouter key in the Vault; presets `fast` / `balanced` / `premium` map to models listed in Settings, chosen by Mybizz and reviewed at each release.
- Spend per call is read from OpenRouter's usage data and added to the month's total; at the ceiling, the instance switches to draft-only and raises an item.
- Prompt and completion text are never written to any log.

### F-16 Dashboard
- `daily_summary` rows are written each night: enquiries by channel, response times, meetings booked, show rate, follow-ups, stage movement, approvals without major edit, AI outcomes, activity by team member.
- The dashboard reads `daily_summary` only; each customer links to the communications log.

### F-17 Data, backups and history
- `server_storage/` writes to the client's R2 bucket with the bucket-only token.
- `activity_log` and `webhook_log` rows older than 30 days are written to R2 and deleted from the tables nightly.
- Export: every table to CSV in one archive, written to R2 and offered for download.

### F-18 Help, tooltips and in-app guidance
- Per [[[default:specifications-global/spec-ui-standards]]](C:/dev/project-library-global/specifications-global/spec-ui-standards.md): tooltip toggle, tooltip on every actionable component, page help-video menu, dashboard quick-link, Return button on the dashboard.

### F-19 Language
- AI replies in the language of the customer's message.
- Screens read every text from `shared/translations/`; English at launch.

### F-20 Plan and billing
- One Paddle price per market; App 5 handles every Paddle notification; the instance shows the plan status read from App 5.

### F-21 Mybizz management app
- Section 1 (App 5) and section 5.

### F-22 Mybizz's own front desk
- Mybizz's own instance is a normal client instance, `mybizz.fda.mybizz.live`, whose embed runs on mybizz.live.

---

## 13. Technical Stack

| Layer | Technology |
|---|---|
| Platform | Anvil.works for Apps 1, 2, 3 and 5; Anvil App Server on Hetzner Cloud for App 4 |
| UI | `m3-custom-theme` (package `m3`) |
| Database | Anvil Data Tables on PostgreSQL, one database per client |
| Reverse proxy and HTTPS | Caddy |
| Email | Amazon SES (inbound and outbound) |
| WhatsApp | Meta WhatsApp Cloud API |
| SMS | SMSGate cloud server mode with the client's Android phone |
| Calendar | Google Calendar API |
| AI replies | OpenRouter with the client's own key |
| Voice | Groq Whisper (speech to text); browser SpeechSynthesis or Groq speech (text to speech) |
| Storage | Cloudflare R2 in the client's own account |
| Billing | Paddle, through App 5 |
| DNS | Cloudflare (mybizz.live) |

---

## 14. Platform Constraints

- The Anvil App Server version is pinned by Mybizz; every upgrade is the developer's decision and passes the full test suite first.
- Background tasks run inside the client's container; long waits use scheduled tasks, not sleeping background tasks, except the 12-second burst wait.
- HTTP endpoints of a client instance are public by nature; each one checks a signature, a token or an allowed origin before acting.
- Google OAuth uses only sensitive scopes (no restricted Gmail scopes), so Google app verification applies without a security assessment.
