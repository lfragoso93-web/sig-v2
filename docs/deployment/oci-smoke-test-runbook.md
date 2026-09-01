# SGI v2 OCI Smoke Test Runbook

Status: validated on the OCI E2 Micro lab on 2026-08-25.

Goal: validate the deployed OCI stack without opening public OCI ingress.

## 1. Automated Smoke Test

Run from `/opt/sgi-v2` after the stack is up:

```bash
sh scripts/oci_smoke_test.sh
```

The script checks:

- Compose can list services.
- backend `/health` succeeds inside the backend container.
- Postgres is ready.
- Redis returns `PONG`.
- `cloudflared` logs are available without obvious token-like content.
- rendered Compose config has no published host ports.

## 2. Manual Public Check

Current lab hostname:

```text
https://sgi.lfconsultoria.dpdns.org
```

From the operator machine:

```bash
curl -I https://sgi.lfconsultoria.dpdns.org
curl -f https://sgi.lfconsultoria.dpdns.org/api/health
```

Expected:

- frontend responds over Cloudflare.
- `/api/health` responds over Cloudflare and nginx proxy.

If VM-local DNS has stale propagation during validation, use an operator machine or a temporary `curl --resolve` check instead of changing OCI ingress.

NO-GO:

- opening OCI ingress `80/443`.
- publishing frontend/backend ports in Compose.
- sharing logs that contain token-like values.

## 3. Seed/Bootstrap Contract Readiness

Run this after merge syncs or before a larger lab rehearsal:

```bash
sh scripts/oci_lab_seed_readiness_check.sh
```

The script checks:

- OCI smoke test passes.
- Seed/bootstrap contract suites pass in temporary containers.
- No real seed is executed.
- backend `/ready` remains HTTP `503` with `ready_for_real_data=false`.
- the public frontend hostname responds through Cloudflare Tunnel.

## 4. Disposable HTTP Journey

Run this before or after backend changes that affect login, portfolios,
transactions, summary, rentabilidade, dividends or IRPF:

```bash
sh scripts/oci_lab_disposable_http_smoke.sh
```

The script executes `backend/scripts/test_ready_http_smoke.py` inside the
backend container. It creates only synthetic/disposable data, then removes the
temporary user and any synthetic USD-BRL row it created for the test.

Expected output includes:

```text
TEST-READY-HTTP-SMOKE:PASS
TEST-READY-HTTP-SMOKE-CLEANUP:PASS
```

If the lab database has no persisted USD-BRL rate for the current date, the
smoke inserts a synthetic `USD-BRL = 5.00000000` row and removes it during
cleanup. This is only a test fixture and does not authorize real data,
production snapshots or real seed execution.
