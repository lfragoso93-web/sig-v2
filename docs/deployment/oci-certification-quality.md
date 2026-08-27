# OCI certification quality gate

Last updated: 2026-08-27

This runbook defines CERT-01A, the repeatable application-quality gate for the OCI lab. It does not authorize real seeds, real portfolio data, or `ready_for_real_data=true`.

## Scope

CERT-01A validates one exact `stable-15jun` checkout with a clean working tree.

It runs:

- backend test dependency image from the existing Dockerfile `deps` stage;
- isolated temporary PostgreSQL 16 database;
- backend flake8;
- backend mypy;
- Python compileall and `import app.main`;
- Alembic upgrade/current and the canonical metadata drift gate;
- full backend pytest suite;
- `pip-audit` with the same explicit ignore already present in CI;
- frontend `npm ci` in an isolated Node 22 container;
- frontend lint, typecheck, Vitest serial run, production build and `audit-ci`;
- existing OCI stack smoke;
- existing seed/bootstrap contract suites without real seed execution;
- existing disposable HTTP journey;
- final `ready_for_real_data=false` preservation through the existing smoke contract;
- final clean-working-tree check.

The backend test container mounts `backend/` at `/app` and exposes the three canonical Compose files read-only at the repository-root paths expected by structural tests (`/docker-compose.yml`, `/docker-compose.prod.yml`, `/docker-compose.oci.yml`). This preserves the same schema/entrypoint authority checks used by CI without weakening those tests.

The temporary certification PostgreSQL container and network are removed on exit.

## Preconditions

- branch must be `stable-15jun`;
- working tree must be clean;
- Docker must be available;
- the OCI Compose stack used by the smoke scripts must already be running;
- `.env` must satisfy the existing OCI scripts;
- no real seed authorization is implied by this runbook.

## Command

From the repository root on the OCI lab host:

```bash
git fetch origin
git switch stable-15jun
git pull --ff-only origin stable-15jun

export SGI_CERT_EXPECTED_SHA="$(git rev-parse HEAD)"
sh scripts/oci_certification_quality.sh
```

For an auditable run, record the full SHA before execution and confirm the final line reports the same SHA.

## Expected result

Successful CERT-01A ends with:

```text
[oci-cert-quality] CERT-01A application quality gate passed for <full-sha>
[oci-cert-quality] Run CERT-01B repository/image security scanners separately before TEST-GO
```

Any failure is a blocker for CERT-01A and must be recorded in Issue #227 before retrying.

## Security boundary

CERT-01A includes Python and Node dependency audits but intentionally does not duplicate the complete repository/image scanner orchestration from GitHub Actions.

CERT-01B remains a separate small block for:

- Gitleaks;
- Trivy filesystem;
- Hadolint;
- backend/frontend image scanning where applicable;
- CodeQL/Code Scanning and external alert reconciliation when accessible.

The last fully observed PR CI before this runbook was the PR #292 baseline, where backend quality, frontend quality, pip-audit, npm audit, Gitleaks, Trivy filesystem and Hadolint all completed successfully. That evidence is historical and must not be presented as certification of a later HEAD.

## No-go conditions

- branch differs from `stable-15jun`;
- working tree is dirty;
- expected SHA differs from HEAD;
- fresh migrations fail;
- Alembic drift exceeds the accepted `goals` exception;
- backend or frontend quality fails;
- dependency audit fails;
- OCI smoke fails;
- seed/bootstrap contract suite attempts or requires real seed execution;
- disposable HTTP smoke changes `ready_for_real_data` away from `false`;
- the certification run modifies tracked files.
