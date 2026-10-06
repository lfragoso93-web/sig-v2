---
name: sgi-certification
description: Inspect, reproduce, promote, revoke, or deploy SGI v2 real-data certification and readiness state. Use for /ready, runtime identity, dataset backups, certification evidence, guarded promotion/revocation, or any rebuild that changes the certified SHA or dataset.
---

# SGI Certification

Read `docs/REAL_DATA_CERTIFICATION_RUNBOOK.md` and `docs/operations.md`. Query
the live runtime and `real_data_certification_events`; do not infer current
certification from README text, process memory, or an old artifact.

Certification identity is exact: environment, `stable-15jun`, full runtime SHA,
canonical dataset reference, single Alembic revision, gate #227 and PR #362.
The dataset reference must come from a validated consistent
`pre-prod-backup.v3` artifact via `app.cli.real_data_dataset_identity`.

Promotion and revocation are append-only events. The DB-first reader used by
`/ready` is authoritative. `GO_ASSISTED` is a separate diagnostic and neither
opens nor closes the productive gate.

For every action:

1. audit branch/remote/tree, service health, runtime identity, Alembic and the
   current event chain;
2. collect inventory/readiness/identity evidence read-only with zero writes;
3. create a new evidence artifact for the exact state;
4. run the certification CLI without `--execute`, preserve the plan, event key,
   evidence hash and confirmation, and prove events before/after are unchanged;
5. use `--execute` only after the user explicitly authorizes that exact action;
6. validate the committed event, `/ready`, restart persistence and a read-only
   recovery/revocation plan.

Any identity or predecessor change makes a previous plan stale. Never edit or
delete certification rows, reuse a confirmation across plans, convert
`GO_ASSISTED` mechanically into `GO`, or use a historical backup as the current
dataset identity.

Code or deployment changes that alter the runtime SHA require a new certified
identity cycle. Keep the existing runtime fail-closed when candidate evidence
is incomplete. Preserve database volumes and backups; never use `down -v` or
volume pruning. OCI/#284 is outside the local certification path unless the
user explicitly resumes it.
