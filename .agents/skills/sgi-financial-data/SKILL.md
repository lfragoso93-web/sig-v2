---
name: sgi-financial-data
description: Change or diagnose SGI v2 transactions, positions, valuation, snapshots, dividends, profitability, IRPF, goals, or portfolio data paths. Use when financial correctness, canonical persistence, rebuilds, imports, or database writes are materially involved.
---

# SGI Financial Data

Read `docs/architecture.md` and `docs/canonical-data.md` before changing a
financial path. Read the domain-specific runbook or contract linked by the
Issue instead of reconstructing policy from old changelogs.

Preserve these boundaries:

- `transactions` is the canonical lifecycle ledger, including fixed income and
  Treasury; use `transaction_write_service.py` rather than a second writer;
- positions, cost and realized result are projections from persisted facts;
- `asset_dividends` stores global monetary events and portfolio entitlements
  are derived on demand;
- `corporate_events` remains fail-closed for unresolved or conflicting events;
- snapshots have a single canonical writer and feed historical/TWR readers;
- financial GET/calculation paths are DB-first and never call providers;
- missing price, FX, benchmark or coverage stays explicit and never becomes
  zero, fixed parity, or an invented value.

Diagnose read-only first. For any operational CLI, prove the target identity,
show write counts, rollback by default, and require explicit user authorization
immediately before a real write. Never mutate historical transactions to apply
a corporate action. Never promote `MATCHED` without the evidence and
fraction/residue policy required by the corporate-event contracts.

Before a rebuild, seed, cleanup, import, or migration against the canonical
database, inspect its dedicated runbook under `docs/`, preserve a consistent
backup, and validate the post-state. Do not delete PostgreSQL volumes.

Test the canonical writer/projector and every downstream contract materially
affected: snapshots, summary, profitability, dividends and IRPF as applicable.
