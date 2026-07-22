# Tenancy model: single-tenant per client (Model A)

**Decision:** Every client gets their **own isolated instance** — own database,
own deployment, own branding.

**Decided by:** DataFabricX Pvt Ltd
**Date:** 2026-07-21
**Status:** Accepted. WP2, WP3, WP5 and WP7 are built against this.
**Corresponds to:** WP-DEC in the
[master implementation plan](commercialization/open-notebook-master-implementation-plan.md)

---

## The decision

| | **Model A — single-tenant (chosen)** | Model B — multi-tenant |
|---|---|---|
| Deployment | One instance per client | One instance serves all clients |
| Data isolation | **Physical** — separate databases | Logical — `tenant_id` on every row, enforced in every query |
| Branding | Per-deployment config | Resolved per-tenant at request time |
| Engineering cost | Low | High — row-level isolation across ~121 query sites |
| Ops cost | Higher per client | Lower per client |
| Security burden | Low — a query bug cannot leak across clients | High — one missing filter leaks another client's data |

## Why Model A

**1. Isolation becomes a property of the architecture, not of our discipline.**
This is the decisive argument. Under Model B, client data is separated only by a
`tenant_id` filter being present and correct in every one of ~121 query sites,
forever, including in code not yet written. One omission leaks one client's
research to another. Under Model A that failure mode does not exist — there is
no other client's data in the database to leak.

**2. It matches how the product is actually sold.** The program already assumes
per-client installations: WP7 builds a cross-platform installer, and WP3 builds
per-client white-label theming. Model A is the model those work packages were
written for.

**3. It is dramatically cheaper to build.** Model B would expand WP2, WP3 and
WP5 substantially — tenant context threaded through every query, per-tenant
theme resolution at runtime, and a much larger security surface to test.

**4. It preserves the option to change.** WP2 adds a `client_id` column even
though single-tenancy does not require one, so a future Model B migration has a
place to put tenant identity without a schema rewrite. Choosing A now does not
foreclose B later; choosing B now cannot be undone cheaply.

**5. It suits the current codebase.** There is no user model and no tenancy
today — all data is global to the instance. Model A is closer to that starting
point, so WP2 adds identity without simultaneously retrofitting isolation.

The accepted cost is **operational**: N clients means N deployments to install,
monitor, back up and upgrade. That cost is real and grows linearly. It is
mitigated by WP7's installer and is the expected trigger for revisiting this
decision.

## What this means for the work packages

- **WP2 (auth):** users belong to one instance. Add `user_id` and `client_id` to
  notebooks/sources — `client_id` is effectively constant per deployment, kept
  for future optionality.
- **WP3 (theming):** brand config is resolved **once at app startup** from a
  per-deployment source (`BRAND_CONFIG_PATH` or `/config/brand`), not per request.
- **WP5 (connectors):** OAuth tokens are stored per user within the instance.
- **WP7 (packaging):** the installer stands up one branded, configured instance
  per client. This is the deployment unit.

## Revisit this if

- **Per-client operational cost becomes the bottleneck.** The clearest trigger.
  At tens of clients, N deployments starts to dominate engineering time.
- **A self-service or free tier is introduced.** Provisioning a full instance
  per sign-up does not work for that model.
- **Clients demand cross-client features** (shared corpora, benchmarking across
  organisations) that physical separation makes impossible.

Migrating A → B later means introducing tenant context across the data layer and
merging databases — expensive, but a known and bounded piece of work, and
cheaper than having built B unnecessarily.

## Consequence for legal assignments

Model A is what makes the risk assignments in
[LEGAL_DECISIONS.md](LEGAL_DECISIONS.md) coherent: **the client operates their
own instance and supplies their own AI provider credentials**, so provider terms
run between the client and the provider.

**If that changes — if DataFabricX begins hosting instances or supplying its own
provider keys — both this decision and the legal assignments must be
re-examined together.** They stand or fall on the same premise.
