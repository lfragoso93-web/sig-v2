# SGI v2 OCI Backup And Restore Runbook

Status: prepared before the VM exists.

Goal: move data to the OCI VM with an auditable PostgreSQL backup, checksum verification, empty-target restore preflight, and explicit rollback points.

## 1. Backup Source Preconditions

Run the backup only from the intended source environment.

Required:

- Branch: `stable-15jun`.
- Commit SHA: full 40-character Git SHA.
- Source database is PostgreSQL.
- Source app can run the backend CLI.
- `pg_dump`, `pg_restore`, and `psql` versions match PostgreSQL server major.

NO-GO:

- Branch is not `stable-15jun`.
- Commit SHA is unknown.
- Inventory reports blocking findings or unclassified tables.
- Backup command prints or stores secrets outside the generated artifacts.

## 2. Create Auditable Backup

Inside the source backend container:

```bash
cd /app
python -m app.cli.pre_prod_backup \
  --branch stable-15jun \
  --commit-sha "$APP_COMMIT_SHA"
```

Expected artifact root:

```text
artifacts/pre-prod-rebuild/<run-id>/
```

Expected files:

- `database.dump`
- `database.dump.sha256`
- `database.contents.txt`
- `origin-inventory.json`
- `backup-report.json`
- `pg-client-version.txt`
- `source-server-version.txt`

The backup CLI enforces:

- `stable-15jun` branch.
- Full 40-character commit SHA.
- read-only repeatable-read source snapshot.
- matching PostgreSQL client/server major versions.
- non-empty custom-format dump.
- SHA-256 manifest.

## 3. Preserve Backup Artifact

Copy the whole run directory as one unit.

Recommended local naming:

```text
sgi-v2-backup-<run-id>.tar.gz
```

Do not commit backup artifacts to Git.

NO-GO:

- Moving only `database.dump` without `backup-report.json`.
- Editing generated artifact JSON manually.
- Losing `database.dump.sha256`.

## 4. Transfer To OCI VM

Preferred destination after VM exists:

```text
/opt/sgi-v2/artifacts/pre-prod-rebuild/<run-id>/
```

Transfer can use any approved operator path, for example:

- `scp`, if restricted SSH is explicitly enabled for the operator.
- Cloud Shell file transfer.
- temporary operator-controlled download URL.

Do not open public OCI application ingress for transfer.

## 5. Optional Isolated Restore Validation

Before using the backup for the OCI production VM, prefer validating it in a separate local or pre-production PostgreSQL database.

The existing restore CLI is designed for that isolated validation:

```bash
python -m app.cli.pre_prod_restore \
  artifacts/pre-prod-rebuild/<run-id> \
  --target-database-url "$PRE_PROD_RESTORE_DATABASE_URL" \
  --confirm-isolated-target
```

Use this when the source database remains accessible as `DATABASE_URL` and the target is a different empty PostgreSQL database.

Do not use this CLI as-is for the final OCI production restore after `.env` points `DATABASE_URL` to the OCI target database. In that final position, the CLI would treat the OCI database as the source identity and reject restoring into itself.

## 6. OCI Restore Target Preconditions

The first OCI restore target is the Docker Postgres container database.

Before restore:

```bash
cd /opt/sgi-v2
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.oci.yml up -d db
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.oci.yml exec db pg_isready -U "${POSTGRES_USER:-sgi}"
```

The OCI target database must be empty. The OCI production restore must be performed only before the app creates or migrates data in that target database.

NO-GO:

- Restoring into a non-empty target database.
- Running `docker compose down -v` without a verified backup and explicit approval.

## 7. Verify Backup On OCI VM

Inside the OCI backend container, after the full app source and `.env` exist, verify the artifact before restore:

```bash
cd /opt/sgi-v2
BACKUP_DIR=artifacts/pre-prod-rebuild/<run-id>
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.oci.yml up -d db
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.oci.yml run --rm -e BACKUP_DIR="$BACKUP_DIR" backend \
  sh -lc 'cd "$BACKUP_DIR" && sha256sum -c database.dump.sha256 && pg_restore --list database.dump > /tmp/database.contents.check.txt'
```

Expected:

- SHA-256 check succeeds.
- `pg_restore --list` succeeds.

## 8. Confirm Empty OCI Target

```bash
cd /opt/sgi-v2
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.oci.yml exec db \
  sh -lc 'psql --no-psqlrc --tuples-only --no-align --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --command "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = '\''public'\'';"'
```

Expected:

```text
0
```

NO-GO:

- Any public schema table exists in the target database.
- Alembic migrations or app startup already created tables before restore.

## 9. Restore Backup Into Empty OCI Target

Run restore through the backend image so `pg_restore` major version matches the project runtime:

```bash
cd /opt/sgi-v2
BACKUP_DIR=artifacts/pre-prod-rebuild/<run-id>
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.oci.yml run --rm -e BACKUP_DIR="$BACKUP_DIR" backend \
  sh -lc 'pg_restore --exit-on-error --single-transaction --no-owner --no-privileges --dbname "$DATABASE_URL" "$BACKUP_DIR/database.dump"'
```

Expected:

- `pg_restore` exits `0`.
- No partial restore because `--single-transaction` is used.

Create a restore note next to the artifact:

```bash
cd /opt/sgi-v2
BACKUP_DIR=artifacts/pre-prod-rebuild/<run-id>
date -u +"%Y-%m-%dT%H:%M:%SZ" > "$BACKUP_DIR/oci-restore-completed-at.txt"
```

Expected source artifact files:

- `database.dump`
- `database.dump.sha256`
- `database.contents.txt`
- `origin-inventory.json`
- `backup-report.json`

## 10. Post-Restore App Checks

Start the app stack:

```bash
cd /opt/sgi-v2
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.oci.yml up -d
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.oci.yml ps
```

Health checks:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.oci.yml exec backend curl -f http://localhost:8000/health
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.oci.yml exec db pg_isready -U "${POSTGRES_USER:-sgi}"
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.oci.yml exec redis redis-cli ping
```

Expected:

- Backend health succeeds.
- Postgres is ready.
- Redis returns `PONG`.
- Cloudflare Tunnel reaches frontend.
- `/api` traffic reaches backend through frontend nginx internally.

## 11. Rollback And Retry

Stop app containers while preserving volumes:

```bash
cd /opt/sgi-v2
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.oci.yml down
```

If a restore must be retried, create a fresh empty target database or explicitly approve volume reset after verifying the backup artifacts.

Do not run:

```bash
docker compose down -v
```

unless the backup run directory and checksum have been verified and data reset is explicitly approved.
