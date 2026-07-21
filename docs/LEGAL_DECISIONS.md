# Legal & licensing decisions

Decisions taken by DataFabricX Pvt Ltd on the licensing and compliance items
raised by WP1.

**Decided by:** DataFabricX Pvt Ltd (product owner)
**Date:** 2026-07-21
**Basis:** the WP1 engineering diligence in
[LICENSE_COMPLIANCE.md](LICENSE_COMPLIANCE.md),
[PROVIDER_TERMS.md](PROVIDER_TERMS.md) and
[THIRD-PARTY-NOTICES.md](../THIRD-PARTY-NOTICES.md)

> **What this file is, and is not.** This records **business decisions to
> accept, assign or defer** each risk. It is **not** a legal opinion and does
> not record review by qualified counsel. The engineering diligence behind each
> item is documented and verifiable; the legal conclusions drawn from it are the
> company's own. Where an item is later reviewed by counsel, add the reviewer
> and date to the relevant row.

---

## Summary

| # | Item | Decision | Status |
|---|---|---|---|
| 1 | SurrealDB BSL position | Accept — keep SurrealDB | ✅ Closed |
| 2 | Single-container redistributes BSL | **Fixed in code** — license ships in the image | ✅ Closed |
| 3 | PRC-jurisdiction providers | Assign to client | ⚠️ Product action outstanding |
| 4 | ElevenLabs commercial audio rights | Accept — client-operated accounts | ⚠️ Revisit if we host TTS |
| 5 | Local model weight licences | Assign to client | ✅ Closed (ToS wording needed) |
| 6 | Customer-configured endpoints | Assign to client | ✅ Closed (ToS wording needed) |

**The distinction that governs items 3–6:** in the intended deployment model
(single-tenant per client — see [TENANCY.md](TENANCY.md)), **the client
operates the instance and supplies their own AI provider credentials.** The
provider relationship is therefore between the client and the provider, not
DataFabricX and the provider. That is what makes assignment legitimate rather
than wishful.

**It stops being true the moment DataFabricX hosts an instance or supplies its
own API keys.** If the commercial model ever shifts to us running instances on
customers' behalf with our credentials, items 3, 4, 5 and 6 revert to
DataFabricX and must be re-decided. This is the single most important condition
in this document.

---

## 1. SurrealDB BSL 1.1 — accepted

**Decision:** Keep SurrealDB. No migration.

BSL 1.1 is source-available, not OSI open source. The v2.6.5 Additional Use
Grant permits embedding it in a product, shipping that product to customers, and
running it as a hosted service at any scale. The sole prohibition is offering
SurrealDB *itself* as a "Database Service" — letting third parties create or
manage tables whose schemas they control. That is not our business.

This version converts to **Apache 2.0 on 2029-09-17**.

The alternative — migrating to PostgreSQL + pgvector — was assessed at 6–10
engineer-weeks with **zero user-visible benefit**: it would buy a licence label.
Rejected.

**Revisit if:** a client contract or procurement policy mandates OSI-approved
licences only, or the product pivots to offering database services.

## 2. Single-container BSL redistribution — fixed, not just noted

**Decision:** Fix in code. Done.

The default multi-container deployment pulls the official
`surrealdb/surrealdb:v2` image as a separate container. Depending on software is
not redistributing it, so nothing is owed.

`Dockerfile --target single` **copies the SurrealDB binary into our own image**,
which *is* redistribution and requires the licence to travel with it.

**Resolved:** the BSL 1.1 text is vendored at
[`licenses/SURREALDB-BSL-1.1.txt`](../licenses/SURREALDB-BSL-1.1.txt), taken
verbatim from the `v2.6.5` tag, and copied into `/app/licenses/` in the `single`
image.

Two details worth preserving:

- The official SurrealDB image ships **no licence file of its own** (verified by
  exporting its filesystem: 1400 files, none a licence), so the text could not
  be copied from it and is vendored here instead.
- BSL parameters are **per-release**. `main` currently carries SurrealDB 3.0
  terms with a Change Date of 2030-01-01, which do not apply to our v2 binary.
  Always cite the version tag.

**If the pinned SurrealDB version changes, re-fetch the licence from the
matching tag.** The Change Date and Licensed Work version will differ.

## 3. PRC-jurisdiction providers — assigned to client, with a product action

**Providers:** DeepSeek, DashScope (Qwen), MiniMax.

**Decision:** Accepted as a client-side choice. The client operates the
deployment, supplies their own credentials, and chooses which providers to
enable. Where their data is processed is consequently their decision.

**⚠️ Outstanding product action:** these providers should be **opt-in per
deployment rather than enabled by default**. Assignment to the client is only
meaningful if the client actually *chooses* — a provider enabled by default that
silently routes research content to a PRC jurisdiction is not a choice they
made. The UI should surface the residency implication at the point of enabling.

Tracked for the WP2/WP3 window, since it touches provider configuration UI.

## 4. ElevenLabs commercial audio rights — accepted on the client-operated basis

**Decision:** Accepted. Clients supply their own ElevenLabs credentials and
their own plan tier, so rights to commercially use generated speech are governed
by *their* contract with ElevenLabs.

**⚠️ Condition:** this holds only while clients bring their own keys. The
podcast feature produces distributable audio; if DataFabricX ever hosts TTS
under its own account — including for trials, demos or a shared tier — the
commercial-use and voice-cloning terms of *our* plan apply, and this item must
be re-decided before that ships.

## 5. Local model weight licences — assigned to client

**Providers:** Ollama, oMLX.

**Decision:** Assigned to the client, who selects and runs the models.

There is no service ToS for local inference, but the obligation does not vanish
— it moves to the **model weights**. Llama's community licence imposes
conditions above a monthly-active-user threshold plus naming requirements;
Gemma carries a use policy; many others are Apache-2.0 or MIT and unencumbered.

**Required follow-through:** the customer terms of service must state that
model selection, and compliance with the selected model's licence, is the
customer's responsibility. Without that wording this assignment is not recorded
anywhere the customer has agreed to.

## 6. Customer-configured endpoints — assigned to client

**Providers:** OpenAI Compatible, Anthropic Compatible.

**Decision:** Assigned to the client. These point at whatever URL the operator
configures — vLLM, LM Studio, llama.cpp, or a third-party reseller — and
whoever runs that endpoint sets the terms. Central clearance is impossible by
construction.

**Required follow-through:** same as item 5 — the customer terms of service must
place responsibility for customer-configured endpoints on the customer.

---

## What remains open

Three follow-through actions, none blocking development:

1. **Customer ToS wording** for items 5 and 6 (and ideally 3). The assignments
   above are only effective once the customer has agreed to them in writing.
2. **Make PRC providers opt-in** rather than default (item 3).
3. **Re-verify provider terms links** in [PROVIDER_TERMS.md](PROVIDER_TERMS.md)
   before commercial launch — they were captured during WP1 and providers change
   terms without notice.

And one standing condition, repeated because it is the thing most likely to be
forgotten:

> **If DataFabricX begins hosting instances or supplying its own AI provider
> credentials, items 3–6 revert to DataFabricX and must be re-decided.**
