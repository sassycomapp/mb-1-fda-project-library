---
title: "mb-1-fda-architecture-explainer"
updated: "2026-11-17"
doc-id: "mb-ebfd9d25"
---
# Mybizz FDA — Architecture Explainer

This document explains, in plain language, how Mybizz FDA is built and why it is built that way. It is written for the developer. The build does not depend on it: the build standard is `mb-1-fda-architecture-reference.md`.

---

## 1. The Big Picture

Mybizz FDA is one Mybizz business. Like every Mybizz business, it is made of five apps.

- **App 1** is the workshop. All building and testing happens here, on Anvil.works.
- **App 2** is the finished product. When App 1 is ready, a copy of it is released into App 2. App 2 holds every screen and every piece of logic.
- **App 3** is the empty shell a client gets. It holds the list of tables, the startup routine and the scheduled jobs, and it relies on App 2 for everything else.
- **App 4** is a client's own running copy: App 3 and App 2 together, with the client's own data. Every client has one, and each one runs on Mybizz's own Hetzner servers.
- **App 5** is Mybizz's control room. One control room serves every Mybizz business. It signs up clients, starts their copies, updates them, and shows whether each one is healthy.

**Why:** building once in App 1 and releasing to App 2 means every client gets every fix at the same moment. Keeping App 3 empty means no client copy can drift away from the product.

---

## 2. One Client, One Copy

Every client has its own copy of Mybizz FDA, with its own database. No client's data ever sits in the same database as another client's data.

**Why:** a mistake in one client's copy cannot leak into another client's copy. Data protection is built into the structure, not left to careful coding.

Each copy has its own web address, such as `smithconsulting.fda.mybizz.live`. The client's team signs in there. The client needs no website domain for this.

---

## 3. Where the Copies Run

The client copies run on rented Hetzner servers in the EU.

- One **application server** runs every client copy, each in its own sealed box (a container).
- One managed **database service**, run by Ubicloud, holds one database per client. A second database keeps a live copy and takes over by itself if the first fails, and Ubicloud keeps continuous backups.
- **Caddy**, a small program on the application server, gives every client copy its secure web address (HTTPS) automatically.

**Why Hetzner:** Hetzner costs a fraction of managed hosting, which keeps Mybizz FDA affordable at £45 a month.

**What it takes:** because Mybizz runs these servers itself, the servers update their own security patches, report their health to App 5, and are watched by an outside check every minute. Nightly backups of each client's data go to the client's own storage.

App 5 never logs into the servers. A small program on the server, the provisioning runner, reaches out to App 5 and accepts only a short list of fixed jobs: start a copy, update a copy, resize, suspend, resume, remove, and report health.

**Why:** nothing on the server is open to the internet for control, so there is nothing for an attacker to reach.

---

## 4. How an Enquiry Travels

1. A customer writes to the client by email, the website form, the website chat, WhatsApp or SMS.
2. The message arrives straight at that client's own copy:
   - **Email:** the client forwards its business mail to its own Mybizz FDA address. Amazon SES receives the mail and hands it to the copy.
   - **Website form and chat:** the client pasted one line of code into its website once. The form and chat bubble send straight to the copy.
   - **WhatsApp:** Meta delivers each client's WhatsApp messages to that client's copy.
   - **SMS:** the client's own Android phone, running the SMSGate app, passes each SMS to the copy.
3. The copy checks that the message is genuine, ignores duplicates, and waits 12 seconds in case the customer sends several short messages in a row.
4. If the message says STOP or similar, the customer is marked "do not contact" at once, and nothing else happens.
5. The copy finds or creates the customer, then asks the AI to classify the enquiry and draft a reply, using only the client's own business profile, services, FAQs, saved replies and free calendar times.
6. The copy checks every part of the AI's answer. Then, under the client's approval mode, the draft either waits in the action queue for a team member or, for simple acknowledgements, goes out by itself.
7. The reply goes back on the channel the enquiry came in on, and the name of whoever approved it is recorded.

**Why the AI only proposes:** the AI can be wrong. The application checks everything, the calendar decides free times, and a person approves anything that matters.

---

## 5. The Channels in More Detail

- **Email by forwarding:** reading a client's Gmail directly would require Google's yearly paid security audit. Forwarding works with every mail provider and needs no audit. A client with its own domain sends replies from its own address; a client with only a free address sends from a Mybizz FDA address, with replies coming back to the client's inbox.
- **WhatsApp:** Meta's official service. Mybizz signs up as a Meta Tech Provider once, and each client then connects its number in a few minutes. WhatsApp is built from the start and stays switched off until Mybizz-Live Ltd is registered and verified by Meta.
- **SMS:** the client's own phone and number send and receive, so there is no SMS provider charge. The phone is checked every 15 minutes.
- **Website chat with voice:** a customer can speak into the chat. Groq turns the speech into text, the AI replies, and the browser reads the reply aloud, in the browser's voice or in a natural voice the client chooses. No real person's voice is ever copied.

---

## 6. Calendars

Each team member connects their own Google Calendar. A customer who already has a team member is offered that team member's free times. A new customer is offered the free times of any team member who delivers the service, and whoever is booked becomes that customer's team member.

**Why:** a small team shares enquiries, but each customer should deal with one person.

---

## 7. AI and Its Costs

- Replies use the client's own OpenRouter key. The client sets a monthly ceiling; when the ceiling is reached, Mybizz FDA stops sending by itself and only drafts.
- Voice uses Mybizz's own Groq key, because voice costs very little.
- No prompt and no AI reply is ever written to a log.

**Why:** the client controls its AI spending, and Mybizz never resells AI.

---

## 8. The Client's Data

- Each client's data store is its own Cloudflare account. Every night the client's copy backs up there, and old history moves there after 30 days.
- When a client leaves, a final backup goes to the client's own storage, and the client keeps all of its data.
- App 5 holds only the client's basic contact details, its Paddle references and a short billing record. Paddle holds all payment details.

---

## 9. What Has to Happen Before Launch

- The Hetzner servers, Caddy, the provisioning runner and the Ubicloud database service are set up and tested.
- Amazon SES is set up for `in.fda.mybizz.live` and `reply.fda.mybizz.live`.
- Google approves Mybizz FDA's calendar access (a sensitive-scope verification, without a security audit).
- Paddle accepts the operator and the £45 price.
- Mybizz's own front desk runs on mybizz.live, so prospects can try Mybizz FDA.
- After Mybizz-Live Ltd is registered: Meta verifies the company as a Tech Provider, and App 5 switches WhatsApp on for every client.
