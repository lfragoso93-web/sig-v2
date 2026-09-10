# SGI v2 on OCI Always Free

Last updated: 2026-09-10

## Current operational contract

OCI is the homologation target for a SHA already developed and certified locally. It is not the primary development environment and must not become a place for permanent code fixes.

Current state:

- development/heavy certification: local Windows + PowerShell + Docker;
- mandatory branch: `stable-15jun`;
- OCI: deploy, migrations, smoke, restart, persistence, resource and network homologation;
- `user-test-readiness.v1 = GO_ASSISTED` in the recorded assisted evidence;
- `ready_for_real_data=false` remains mandatory;
- `/ready=503` is expected while the broad real-data gate is closed;
- deploy the exact locally certified SHA, not merely the latest branch HEAD;
- defects found on OCI are reproduced/fixed locally and generate a new SHA;
- #227 is the only formal broad real-data GO/NO-GO gate.

Operator entrypoint: `docs/deployment/oci-execution-index.md`.

## Promotion chain

```text
local development/certification
        |
#303 PORTFOLIO-TEST-READY / candidate SHA
        |
#226 -> #216 -> #158
        |
OCI homologates exact candidate SHA
        |
#227 GO / NO-GO
        |
only after GO: evaluate ready_for_real_data=true
```

## Assisted homologation

During `GO_ASSISTED`, OCI can validate infrastructure with controlled/disposable data. The expected state can legitimately be:

```text
/health=200
/ready=503
GO_ASSISTED=true
ready_for_real_data=false
```

Do not force readiness, execute real global seeds, restore broad real data or run destructive contraction merely to make an OCI smoke pass.

## Final promotion homologation

After #303/#226/#216/#158 identify the promotion SHA and dataset:

1. checkout exactly that SHA on OCI;
2. verify `APP_COMMIT_SHA == git rev-parse HEAD`;
3. apply only approved migrations;
4. validate Compose/network/tunnel;
5. validate `/health` and record `/ready` semantics;
6. validate restart and volume persistence;
7. observe CPU/RAM/disk;
8. run the OCI security/resilience smokes applicable to the candidate;
9. deliver evidence to #227.

OCI homologation does not replace the full local test battery.

## Architecture target

- preferred compute: `VM.Standard.A1.Flex` when free-tier capacity is available;
- Ubuntu ARM64;
- Docker Compose;
- PostgreSQL and Redis internal to Docker networking;
- frontend behind Cloudflare Tunnel;
- no direct public backend/database/cache exposure;
- E2 Micro is a constrained lab/fallback and not production-equivalent for capacity/performance.

## ARM64 record

The stack was previously audited as ARM64-compatible for Ampere A1: backend, frontend, PostgreSQL and Redis paths passed the architecture audit. That evidence is historical compatibility evidence; the exact promotion SHA still receives OCI homologation.

## Network contract

Cloudflare Tunnel remains the preferred application exposure path. OCI application ingress should stay closed. Never expose `5432`, `6379` or `8000`; do not open `80/443` merely to bypass tunnel problems.

Public IP, if needed for VM bootstrap/outbound routing, is not the public application endpoint.

## Cost guardrails

Do not create paid resources without explicit approval. The initial free architecture avoids:

- NAT Gateway;
- Load Balancer;
- managed database/Redis;
- OKE;
- unnecessary extra nodes/volumes.

Recheck current tenancy/free-tier limits before provisioning or resizing; historical inventory values are not a permanent entitlement guarantee.

## Secrets

- secrets are VM-local;
- no OCI API private keys copied to the VM unless an explicit future design requires it;
- no tunnel/provider/database secrets in Git, Issues or logs;
- `.env` must remain outside version control.

## Data policy

OCI availability never authorizes real data by itself. Backup/restore, seeds, import, rebuild and physical contraction follow their own gates.

Current broad-data order:

1. #303 — functional readiness and candidate SHA;
2. #226 — Proventos strategy;
3. #216 — aggregate seed reconciliation;
4. #158 — promotion reconciliation;
5. OCI — exact-SHA homologation;
6. #227 — GO/NO-GO.

## Rollback and recovery

Rollback returns to a known commit and verified backup while preserving volumes unless destructive reset is explicitly authorized. Never use `docker compose down -v` as a routine rollback.

## Supporting runbooks

- `docs/deployment/oci-execution-index.md` — canonical sequence;
- `docs/deployment/oci-first-deploy-runbook.md` — exact-SHA deployment;
- `docs/deployment/oci-backup-restore-runbook.md`;
- `docs/deployment/oci-cloudflare-tunnel-runbook.md`;
- `docs/deployment/oci-smoke-test-runbook.md`;
- `docs/deployment/oci-operations-runbook.md`;
- `docs/deployment/oci-disaster-recovery-runbook.md`;
- OCI certification quality/resilience/security documents.

## Historical note

The original OCI inventory/provisioning investigation from 21/08/2026 established ARM64 compatibility, Cloudflare Tunnel, A1 as preferred target, E2 Micro fallback, and free-tier guardrails. Those decisions remain traceable in Git history and Issue #284. Dated baseline SHAs and old "next OCI block" instructions must not override this current operator contract.
