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
- for Brazilian listed assets, B3 is the official primary source for
  dividends and corporate events when its structured endpoint covers the
  asset; BRAPI may supplement only fields/events B3 does not publish;
- use Yahoo only as an explicitly identified fallback when B3 has no issuer
  coverage, never to replace a valid B3 response; preserve provenance;
- never compare or merge providers into a synthetic fact; retain distinct
  source identities so official B3 evidence can corroborate without replacing
  the underlying payload;
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
