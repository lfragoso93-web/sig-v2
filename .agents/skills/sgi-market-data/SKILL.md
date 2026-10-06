---
name: sgi-market-data
description: Develop or operate SGI v2 market-data, asset catalog, prices, FX, benchmark, dividend, or corporate-event provider flows. Use for provider adapters, synchronization, provenance, coverage, seeds, and external-data reconciliation.
---

# SGI Market Data

Start from `docs/BOOTSTRAP_DATA_FLOW.md`, `docs/providers.md`, and the relevant
domain contract. For corporate actions also read `docs/CORPORATE_ACTIONS.md`
and the current state of Issue #370.

Keep provider access outside financial read paths. External facts must be
normalized, carry provenance, pass domain validation, and be persisted before
financial services consume them.

Apply the current source policy precisely:

- use B3/COTAHIST as the baseline authority for B3 catalog/history fields
  assigned to it; BRAPI may enrich without silently overwriting official facts;
- for dividends and corporate-event collection, BRAPI is primary;
- call Yahoo only when BRAPI is unavailable or collection fails, record
  `provider_fallback=brapi_unavailable`, and never compare or merge providers
  into a synthetic fact;
- a valid BRAPI response, including an empty result, does not trigger Yahoo;
- invalid BRAPI payloads fail closed rather than falling back silently.

Do not invent prices or turn provider absence into coverage. Preserve
`HISTORY_END_UNAVAILABLE` and other incomplete-coverage states until factual
data exists.

Corporate events marked `CONFLICT`, `UNRECONCILED`, `requires_review=true`, or
non-canonical remain outside projections. #370 permits continued development
with its accepted fail-closed conflicts, but does not authorize `MATCHED` for
KLBN11 or any other event without the required broker/issuer evidence and
fraction/residue policy.

Seeds and syncs are dry-run-first, idempotent, auditable, and scoped by explicit
date/assets/run identity. Report provider calls, facts accepted/rejected and
database writes. Use `--execute` only after explicit authorization for the
exact plan.
