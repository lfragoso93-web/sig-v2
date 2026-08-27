# OCI certification resilience gate

Last updated: 2026-08-27

CERT-02 validates operational resilience of the OCI lab after CERT-01A quality and CERT-01B security have passed.

The gate does not authorize real seeds, real portfolio data, or `ready_for_real_data=true`.

## Scope

`script/oci_certification_resilience.sh` validates:

- exact clean `stable-15jun` checkout;
- OCI Compose still publishes no host ports;
- PostgreSQL persistent volume exists;
- a disposable DB marker survives container restart;
- DB, Redis, backend and frontend recover after restart;
- PostgreSQL volume identity remains the same;
- Alembic remains at head and the drift gate still passes after restart;
- Redis outage does not terminate the backend;
- cache operations remain fail-open while Redis is unavailable;
- Redis recovery allows the cache boundary to reconnect;
- disposable marker is removed at the end;
- working tree remains clean.

The script uses the existing `postgres_data` named volume and never runs `docker compose down -v`.

## Execution

```bash
cd /opt/sgi-v2
git fetch origin
git switch stable-15jun
git pull --ff-only origin stable-15jun

git rev-parse HEAD
git status --short

export SGI_CERT_EXPECTED_SHA="$(git rev-parse HEAD)"
sh scripts/oci_certification_resilience.sh 2>&1 | tee /tmp/sgi-cert-02.log
```

Expected final markers:

```text
REDIS-FAIL-OPEN:PASS
REDIS-RECOVERY:PASS
[oci-cert-resilience] CERT-02 resilience gate passed for <sha>
```

If the script stops during the Redis outage phase, recover Redis before further testing:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.oci.yml start redis
```

If it stops after creating the marker table, cleanup is safe after diagnosing the failure:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.oci.yml exec -T db \
  psql -U sgi -d sgi -c 'DROP TABLE IF EXISTS sgi_cert_persistence_marker;'
```

## Interpretation

Failure to preserve the marker or volume identity is a P0 persistence blocker. Failure of services to recover after restart is an operational blocker. Redis fail-open failure is a resilience blocker because Redis is cache infrastructure and must not become a hard dependency for DB-backed requests.
