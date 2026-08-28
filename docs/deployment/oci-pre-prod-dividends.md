# OCI pre-production dividends idempotency runbook

Last updated: 2026-08-28

This runbook prepares the Linux/OCI execution path for Issue #226 and contract `pre-prod-dividends-seed.v2`.

> Real execution was explicitly authorized in Issue #226 on 2026-08-28. The authorization applies only to the two controlled dividends seed runs on the exact `stable-15jun` SHA and date window recorded in the issue. It does not authorize any other real-data operation.

## Canonical wrappers

- Windows/PowerShell: `scripts/Invoke-PreProdDividendsIdempotency.ps1`
- OCI/Linux/POSIX: `scripts/oci_pre_prod_dividends_idempotency.sh`

Both wrappers preserve the same contract:

- branch must be exactly `stable-15jun`;
- full 40-character Git SHA is mandatory;
- backend `APP_COMMIT_SHA` must equal the requested SHA;
- working tree must be clean before execution;
- explicit confirmation string binds authorization to the SHA;
- start/end dates are mandatory;
- two distinct real seed runs execute in the same window;
- each seed run writes immutable evidence under `artifacts/pre-prod-rebuild`;
- the offline idempotency comparator produces a third evidence artifact;
- any non-zero seed/comparison exit code blocks the gate and preserves evidence.

## Runtime SHA authority

`docker-compose.yml` maps `APP_COMMIT_SHA` explicitly in both build args and backend runtime `environment`. This is intentional: the Compose/shell value must take precedence over any stale `APP_COMMIT_SHA` that may exist in `.env`. Runtime identity is part of the auditable pre-production contract.

This contract is protected by `backend/tests/test_compose_runtime_commit_identity.py`.

Before a real execution, rebuild/recreate the backend with the authorized SHA:

```bash
EXPECTED_SHA="<FULL_40_CHAR_SHA>"
export APP_COMMIT_SHA="$EXPECTED_SHA"

docker compose \
  -f docker-compose.yml \
  -f docker-compose.prod.yml \
  -f docker-compose.oci.yml \
  build backend

docker compose \
  -f docker-compose.yml \
  -f docker-compose.prod.yml \
  -f docker-compose.oci.yml \
  up -d --no-deps --force-recreate backend

docker compose \
  -f docker-compose.yml \
  -f docker-compose.prod.yml \
  -f docker-compose.oci.yml \
  exec -T backend printenv APP_COMMIT_SHA
```

The final command must match `EXPECTED_SHA` exactly before any real seed execution.

## Artifact bind-mount ownership

The backend runtime is intentionally non-root (UID 1000). The repository host directory `artifacts/` is bind-mounted at `/app/artifacts`, so the host directory must be writable by the operator and owned by the same UID used by the backend runtime. Do not use `chmod 777`.

Validate before execution:

```bash
id -u
stat -c '%u:%g %a %n' artifacts

docker compose \
  -f docker-compose.yml \
  -f docker-compose.prod.yml \
  -f docker-compose.oci.yml \
  exec -T backend sh -c 'id -u; stat -c "%u:%g %a %n" /app/artifacts'
```

On the OCI Ubuntu lab, if the operator and backend runtime both use UID 1000, the safe repair is:

```bash
sudo chown -R 1000:1000 artifacts
chmod u+rwx artifacts
```

After repair, re-run the validation above. The POSIX wrapper also blocks before any seed if the host artifacts path is not writable or if the bind-mounted owner UID differs from the backend UID.

## Required OCI variables

After explicit authorization, the operator must set all values deliberately:

```bash
export SGI_PREPROD_COMMIT_SHA="<FULL_40_CHAR_SHA>"
export SGI_PREPROD_CONFIRMATION="EXECUTE-DIVIDENDS-IDEMPOTENCY:<FULL_40_CHAR_SHA>"
export SGI_PREPROD_START_DATE="YYYY-MM-DD"
export SGI_PREPROD_END_DATE="YYYY-MM-DD"
```

Optional artifact root:

```bash
export SGI_PREPROD_ARTIFACT_ROOT="artifacts/pre-prod-rebuild"
```

The wrapper rejects artifact paths outside repository `artifacts/`.

## Preflight before execution

```bash
cd /opt/sgi-v2
git fetch origin
git switch stable-15jun
git pull --ff-only origin stable-15jun
git rev-parse HEAD
git status --short

docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.oci.yml ps
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.oci.yml exec -T backend printenv APP_COMMIT_SHA
```

Do not continue if Git HEAD and runtime `APP_COMMIT_SHA` differ.

## Execution

Only for the explicitly authorized SHA and window recorded in Issue #226:

```bash
sh scripts/oci_pre_prod_dividends_idempotency.sh 2>&1 | tee /tmp/sgi-pre-prod-dividends.log
```

Successful execution must preserve:

- `first.json`;
- `second.json`;
- `idempotency.json`;
- operation id, branch, SHA, date window and both run ids.

## Post-execution gate

Do not advance to CSV import or rebuild merely because the wrapper exits zero. First:

1. inspect the three evidence artifacts;
2. reconcile counts, sources, coverage and integrity in Issue #226;
3. update gate #216;
4. update Issue #158;
5. confirm no table outside `asset_dividends` was modified;
6. only then evaluate authorization for the next stage.

The protected physical contraction migration remains outside this runbook and must only execute in its dedicated #158 window with approved backup and zero-row legacy tables.
