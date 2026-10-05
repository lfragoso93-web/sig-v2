# 2026-09-14 - #226 dividends decision

## Decision

The existing portfolio-scoped and idempotent Proventos evidence is sufficient
for the current controlled promotion path.

No global dividends seed will be executed mechanically for #226.

## Canonical Boundary

- `asset_dividends` remains the only canonical global persistence for dividend
  events.
- Portfolio rights remain calculated on demand from historical positions.
- No per-portfolio materialization is reintroduced.
- BRAPI remains authoritative when it has valid coverage; Yahoo remains
  fallback-only.

## When a Global Run Is Allowed

A controlled global run can only be reconsidered if #216 or #158 identifies a
material, specific gap that cannot be closed with the already certified
portfolio-scoped evidence.

## Next Gate

Track A advances to #216, consuming this #226 decision and the already
consolidated benchmark/FX evidence.
