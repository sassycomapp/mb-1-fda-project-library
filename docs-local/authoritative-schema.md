---
title: "authoritative-schema"
updated: "2026-11-16"
doc-id: "mb-025ce9f9"
---
# Mybizz FDA — Authoritative Database Schema

Every table and column of a Mybizz FDA client instance: name, type and allowed values.

**Authority:** this document is the single home of the schema. Where a technical fact here differs from `mb-1-fda-architecture-reference.md`, the architecture reference is correct. Feature numbers (F-01 to F-22) are those of `mb-1-fda-concept.md`.

**Platform:** Anvil Data Tables. Every table has `client: none` and `server: full`: the browser never reads a table directly; server functions return rows and results.

---

## Rules

- **One instance, one client.** No table carries a client or workspace column.
- **UTC.** Every `datetime` is stored in UTC and shown in `business_profile.timezone` (an IANA time zone).
- **Nothing overwritten.** Rows of `messages` are never edited after they are received, sent or approved, and never deleted while the contact exists; only their status columns change (Hard Rule 5).
- **A name on every action.** Every row that records an action carries the user who took it, or the actor `ai` or `system` (Hard Rule 6).
- **History outside the tables.** `activity_log` and `webhook_log` rows older than 30 days, backups and exports are kept in the client's R2 bucket (F-17).
- **Credentials only in the Vault**, encrypted ([[[default:specifications-global/spec-vault-system]]](C:/dev/project-library-global/specifications-global/spec-vault-system.md)).
- **Names** follow [[[default:specifications-global/spec-nomenclature]]](C:/dev/project-library-global/specifications-global/spec-nomenclature.md). A link column is named after its target table in the singular, or `{target}_id`.
- **Allowed values** are lowercase strings, written here as `value1` / `value2`. Code compares against these exact strings.
- **Standard columns.** Every table has `created_at`. Every table whose rows are edited after creation has `updated_at`. Every core table has `metadata` (`simpleObject`).

### Column types

| Type | Holds |
|---|---|
| `string` | Text |
| `number` | A number |
| `bool` | True or False |
| `date` | A date without time |
| `datetime` | A date and time, UTC |
| `simpleObject` | A list or dictionary (JSON) |
| `link → table` | One row of `table` |
| `links → table` | Several rows of `table` |

---

## Table Groups

| Group | Tables |
|---|---|
| Core and configuration | `users`, `business_profile`, `config`, `vault`, `channel_status` |
| Knowledge | `services`, `faqs`, `saved_replies` |
| Customers | `contacts`, `leads`, `notes` |
| Conversations | `messages`, `pending_bursts`, `webchat_sessions`, `action_queue` |
| Bookings | `team_calendars`, `appointments` |
| Records and summaries | `activity_log`, `webhook_log`, `ai_usage`, `daily_summary` |

---

## Core and configuration

### `users` (F-01)
| Column | Type | Values / notes |
|---|---|---|
| `email` | string | Anvil Users column |
| `enabled` | bool | Anvil Users column |
| `full_name` | string | |
| `role` | string | `owner` / `manager` / `admin` / `staff` |
| `language` | string | Screen language code, default `en` |
| `tooltips_on` | bool | F-18 |
| `created_at`, `updated_at` | datetime | |

Anvil Users service columns (password hash, MFA, remembered logins) are kept as Anvil defines them.

### `business_profile` (F-03)
| Column | Type | Values / notes |
|---|---|---|
| `business_name` | string | |
| `description` | string | |
| `audience` | string | |
| `website` | string | |
| `timezone` | string | IANA time zone |
| `tone` | string | `warm` / `formal` / `concise` / `technical` |
| `signature` | string | |
| `prohibited_claims` | simpleObject | List of strings |
| `lead_rules` | simpleObject | Qualified, urgent and decline rules |
| `privacy_notice_url` | string | Client's own privacy notice |
| `email_domain` | string | Verified sending domain, or empty |
| `email_from_address` | string | |
| `created_at`, `updated_at` | datetime | |
| `metadata` | simpleObject | |

### `config`
| Column | Type | Values / notes |
|---|---|---|
| `approval_mode` | string | `draft_only` / `approve_before_send` / `autonomous_low_risk` |
| `followup_delay_hours` | number | |
| `followup_max_attempts` | number | |
| `ai_preset` | string | `fast` / `balanced` / `premium` |
| `ai_monthly_ceiling` | number | In the currency of the client's OpenRouter account |
| `ai_month_spend` | number | Reset on the first day of each month |
| `ai_fallback_active` | bool | True when draft-only fallback is in force (F-15) |
| `natural_voice_on` | bool | F-07 |
| `natural_voice_name` | string | One of Groq's stock voices |
| `palette` | string | One of the eight `m3-custom-theme` palettes |
| `allowed_origins` | simpleObject | Website domains allowed to use the embeds |
| `whatsapp_available` | bool | Set by App 5 (F-08) |
| `setup_complete` | bool | F-02 |
| `setup_step` | number | Last completed wizard step |
| `created_at`, `updated_at` | datetime | |

### `vault`
As [[[default:specifications-global/spec-vault-system]]](C:/dev/project-library-global/specifications-global/spec-vault-system.md) defines it. Holds: the Bearer token for App 5, the R2 bucket token, the OpenRouter key, the Groq key, the SMSGate username, password, encryption passphrase and webhook signing key, the Meta business token and verify token, and each team member's Google refresh token.

### `channel_status` (F-04, F-08, F-09)
| Column | Type | Values / notes |
|---|---|---|
| `channel` | string | `email` / `webform` / `webchat` / `whatsapp` / `sms` |
| `status` | string | `unconfigured` / `connected` / `disconnected` |
| `detail` | simpleObject | Channel identifiers (phone number id, SMSGate device id, inbound address) |
| `last_checked_at` | datetime | |
| `created_at`, `updated_at` | datetime | |

---

## Knowledge

### `services` (F-03, F-13)
| Column | Type | Values / notes |
|---|---|---|
| `name` | string | |
| `description` | string | |
| `duration_minutes` | number | |
| `from_price` | string | Price text as the client approves it, e.g. "from £300" |
| `delivery_expectation` | string | |
| `ideal_client` | string | |
| `qualifying_questions` | simpleObject | List of strings |
| `team_members` | links → users | Who delivers the service |
| `active` | bool | |
| `created_at`, `updated_at` | datetime | |
| `metadata` | simpleObject | |

### `faqs` (F-03)
| Column | Type | Values / notes |
|---|---|---|
| `question` | string | |
| `answer` | string | |
| `approved_by` | link → users | |
| `active` | bool | |
| `created_at`, `updated_at` | datetime | |

### `saved_replies` (F-03)
| Column | Type | Values / notes |
|---|---|---|
| `title` | string | |
| `body` | string | |
| `approved_by` | link → users | |
| `active` | bool | |
| `created_at`, `updated_at` | datetime | |

---

## Customers

### `contacts` (F-12)
| Column | Type | Values / notes |
|---|---|---|
| `full_name` | string | |
| `email` | string | Lowercase; email or phone required |
| `phone` | string | E.164 form |
| `company` | string | |
| `source` | string | `email` / `webform` / `webchat` / `whatsapp` / `sms` / `import` / `manual` |
| `language` | string | Language of the customer's messages |
| `tags` | simpleObject | List of strings |
| `consent` | simpleObject | Consent given at import or capture, with date and source |
| `do_not_contact` | bool | Hard Rule 4 |
| `do_not_contact_at` | datetime | |
| `email_undeliverable` | bool | Set by SES bounces and complaints |
| `created_at`, `updated_at` | datetime | |
| `metadata` | simpleObject | |

### `leads` (F-12)
| Column | Type | Values / notes |
|---|---|---|
| `contact` | link → contacts | |
| `stage` | string | `new_enquiry` / `responded` / `meeting_booked` / `proposal_quote` / `won` / `lost_not_fit` / `stalled` |
| `service` | link → services | Service of interest |
| `urgency` | string | `normal` / `high` |
| `summary` | string | One sentence |
| `assigned_to` | link → users | |
| `next_action` | string | |
| `next_action_at` | datetime | |
| `followup_count` | number | |
| `created_at`, `updated_at` | datetime | |
| `metadata` | simpleObject | |

### `notes` (F-12)
| Column | Type | Values / notes |
|---|---|---|
| `contact` | link → contacts | |
| `body` | string | |
| `author` | link → users | |
| `created_at` | datetime | |

---

## Conversations

### `messages` (F-10, F-11, F-12)
| Column | Type | Values / notes |
|---|---|---|
| `contact` | link → contacts | |
| `lead` | link → leads | |
| `channel` | string | `email` / `webform` / `webchat` / `whatsapp` / `sms` |
| `direction` | string | `inbound` / `outbound` |
| `subject` | string | Email only |
| `body` | string | |
| `language` | string | |
| `external_id` | string | Provider message id; duplicates ignored |
| `thread_ref` | string | Email thread or chat session reference |
| `status` | string | `received` / `draft` / `superseded` / `approved` / `rejected` / `sent` / `delivered` / `failed` |
| `ai_generated` | bool | |
| `replaces` | link → messages | The draft this edited message replaces |
| `actor` | string | `user` / `ai` / `system` |
| `actor_user` | link → users | When `actor` is `user` |
| `approved_by` | link → users | |
| `approved_at` | datetime | |
| `rejection_reason` | string | |
| `created_at`, `updated_at` | datetime | `updated_at` changes only with a status change |
| `metadata` | simpleObject | |

### `pending_bursts` (F-10)
| Column | Type | Values / notes |
|---|---|---|
| `channel` | string | `webchat` / `whatsapp` / `sms` |
| `sender` | string | Phone number or chat session token |
| `messages` | links → messages | Messages in the burst |
| `last_arrival_at` | datetime | |
| `created_at`, `updated_at` | datetime | |

### `webchat_sessions` (F-06, F-07)
| Column | Type | Values / notes |
|---|---|---|
| `session_token` | string | |
| `contact` | link → contacts | Once the customer leaves contact details |
| `origin` | string | Website the chat ran on |
| `voice_used` | bool | |
| `last_activity_at` | datetime | |
| `created_at`, `updated_at` | datetime | |

### `action_queue` (F-11)
| Column | Type | Values / notes |
|---|---|---|
| `item_type` | string | `approve_reply` / `urgent_enquiry` / `new_question` / `channel_disconnected` / `ai_error` / `ai_ceiling_reached` / `send_failed` / `booking_changed` / `backup_failed` |
| `priority` | string | `high` / `normal` |
| `title` | string | |
| `contact` | link → contacts | |
| `lead` | link → leads | |
| `message` | link → messages | |
| `assigned_to` | link → users | |
| `status` | string | `open` / `snoozed` / `done` / `dismissed` |
| `snoozed_until` | datetime | |
| `closed_by` | link → users | |
| `closed_at` | datetime | |
| `created_at`, `updated_at` | datetime | |

---

## Bookings

### `team_calendars` (F-13)
| Column | Type | Values / notes |
|---|---|---|
| `user` | link → users | |
| `google_calendar_id` | string | |
| `working_hours` | simpleObject | Per weekday, start and end times |
| `buffer_minutes` | number | |
| `booking_link` | string | |
| `connected` | bool | |
| `watch_expires_at` | datetime | Google calendar watch |
| `created_at`, `updated_at` | datetime | |

### `appointments` (F-13)
| Column | Type | Values / notes |
|---|---|---|
| `contact` | link → contacts | |
| `lead` | link → leads | |
| `service` | link → services | |
| `team_member` | link → users | |
| `start_at` | datetime | |
| `end_at` | datetime | |
| `google_event_id` | string | |
| `meeting_link` | string | |
| `status` | string | `booked` / `rescheduled` / `cancelled` / `attended` / `no_show` |
| `reminder_sent_at` | datetime | |
| `created_at`, `updated_at` | datetime | |
| `metadata` | simpleObject | |

---

## Records and summaries

### `activity_log` (F-01, F-16)
| Column | Type | Values / notes |
|---|---|---|
| `actor` | string | `user` / `ai` / `system` |
| `actor_user` | link → users | |
| `action` | string | e.g. `reply_approved`, `reply_sent`, `contact_opted_out`, `booking_created`, `setting_changed` |
| `object_type` | string | `contact` / `lead` / `message` / `appointment` / `setting` / `channel` / `user` |
| `object_id` | string | |
| `summary` | string | Redacted; never prompt or AI text |
| `created_at` | datetime | |

### `webhook_log` (F-17)
| Column | Type | Values / notes |
|---|---|---|
| `channel` | string | `email` / `whatsapp` / `sms` / `google` / `management` |
| `external_id` | string | |
| `signature_valid` | bool | |
| `payload` | simpleObject | |
| `created_at` | datetime | |

### `ai_usage` (F-15)
| Column | Type | Values / notes |
|---|---|---|
| `purpose` | string | `classify_draft` / `followup` / `webchat` / `transcribe` / `speech` |
| `provider` | string | `openrouter` / `groq` |
| `model` | string | |
| `input_tokens` | number | |
| `output_tokens` | number | |
| `cost` | number | |
| `outcome` | string | `ok` / `invalid_output` / `provider_error` |
| `created_at` | datetime | |

### `daily_summary` (F-16)
| Column | Type | Values / notes |
|---|---|---|
| `day` | date | |
| `enquiries_by_channel` | simpleObject | |
| `answered_within` | simpleObject | Counts within 5, 15 and 60 minutes |
| `meetings_booked` | number | |
| `meetings_attended` | number | |
| `followups_sent` | number | |
| `stage_moves` | simpleObject | |
| `approvals_unedited` | number | |
| `ai_outcomes` | simpleObject | |
| `activity_by_user` | simpleObject | Actions per team member |
| `created_at` | datetime | |
