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
