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

Mandatory Continuous Documentation Rule: On every instruction, feature addition,
refactoring, bug fix, migration, or route creation, update all affected documentation
files (root README.md, backend/README.md, frontend/README.md, docs/ROADMAP.md,
docs/DOCUMENTACAO_DO_SISTEMA.md, and domain docs) in the exact same work block.
Never deliver code changes with outdated or diverged documentation.

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

Windows with `stable-15jun` is the development and validation environment;
OCI runs production from `main` through the GitHub Actions release flow. Do not
develop on the OCI host or perform normal releases by SSH. Never use volume
deletion or broad cleanup as a development shortcut.

For every validation that needs the application runtime, use the local Docker
development stack and localhost. First confirm the Docker Linux engine is
available and the checkout is on `stable-15jun`. Start only the services from
the base `docker-compose.yml`; do not include `docker-compose.oci.yml` or any
OCI override, so `cloudflared` and its tunnel are never started locally. Do not
load production secrets or point local services at production data. If Docker
is unavailable, report validation as blocked rather than claiming it passed.
After validation, stop the local stack with `docker compose down` (without
`-v`) and confirm it is stopped. Preserve named volumes and local database
contents. If validation fails, stop the services started for that validation
the same way.
