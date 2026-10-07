---
name: sgi-development
description: Develop, review, diagnose, or document SGI v2 changes while preserving its branch, architecture, validation, and release-governance contracts. Use for general repository work that is not primarily a financial-data write, provider ingestion, or real-data certification operation.
---

# SGI Development

Work from the repository root on `stable-15jun`. Before editing, compare the
local HEAD with `origin/stable-15jun`, inspect the working tree, related Issues
and open PRs, and preserve unrelated user changes. Never rewrite published
history or develop directly on `main`.

Read only the sources relevant to the task:

- `README.md` and `docs/architecture.md` for the current project boundary;
- `docs/ARCHITECTURE_DOCTOR.md` when changing an architectural invariant;
- the linked Issue and `git log -- <file>` before modifying an existing file.

Keep changes narrow and reviewable. Prefer existing services and contracts to a
parallel abstraction. Update tests and living documentation in the same block
when behavior or an invariant changes.

For date-sensitive financial logic, inject `app.core.clock.Clock`; production
uses `SystemClock` and deterministic tests use timezone-aware `FrozenClock`.
Production configuration must fail before startup when its exact branch, SHA or
dataset identity is invalid, without logging received secret values. Protect
critical database readers with explicit query budgets when a stable ceiling is
known; do not hide N+1 regressions behind a broadly increased limit.

For portfolio-scoped sensitive data, pass `PortfolioAccessContext` across the
controller/service/repository boundary. Client-provided IDs are not authority.
User contexts require ownership and explicit permission; system jobs require a
non-empty purpose and must never rely on an implicit bypass.

Recurring global jobs that can run in multiple backend replicas require a
distributed lease with explicit TTL, owner-safe release and fail-closed
contention behavior. Keep database idempotency underneath the lease. Do not add
a transactional outbox until a concrete domain write and durable external work
must be committed atomically; document a no-outbox decision when that case is
absent.

Use the project `.venv` or Docker. Choose focused tests first, then gates
proportional to risk. Run `git diff --check`; use Flake8 with `--jobs=1` on
Windows when needed. A pytest `WinError 5` during temporary-directory setup is
an environment failure, not a test assertion; repeat in an approved workspace
temp directory or the project container.

For architectural work, run the applicable source tests and, when relevant:

```powershell
cd backend
..\.venv\Scripts\python.exe -m app.doctor --all-static --format json
```

The running environment may be certified for an exact SHA and dataset. A new
commit does not authorize rebuilding that runtime under a different identity.
Before deployment or readiness changes, route to the `sgi-certification` skill.

OCI/#284 is backlog unless the user explicitly brings it into scope. Never use
volume deletion or broad cleanup as a development shortcut.
