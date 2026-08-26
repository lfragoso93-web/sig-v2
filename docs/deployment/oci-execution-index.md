# SGI v2 OCI Execution Index

Status: use this as the top-level sequence when A1 capacity becomes available.

Before retrying or deploying from Windows, run:

```powershell
.\scripts\oci_local_readiness.ps1
```

## Phase 1. Retry OCI Stack

Use:

- `docs/deployment/oci-capacity-fallbacks.md`
- `docs/deployment/oci-micro-lab-runbook.md`
- `docs/deployment/oci-stack-retry-runbook.md`
- `docs/deployment/oci-cost-guardrails.md`
- `docs/deployment/oci.md`

Do:

- retry saved Stack `sgi-prod-a1-01`;
- keep `VM.Standard.A1.Flex`;
- keep initial `1 OCPU / 6 GB`;
- keep boot `80 GB`;
- keep `sgi-prod-vm-nsg`;
- reject paid resources.

## Phase 2. Validate VM Baseline

Use:

- `docs/deployment/oci-cloud-init.yaml`
- `docs/deployment/oci-vm-handoff-template.md`
- `docs/deployment/oci-first-deploy-runbook.md`
- `scripts/oci_vm_baseline_check.sh`

Do:

- wait for cloud-init;
- verify Docker;
- verify UFW;
- verify `/opt/sgi-v2`.

## Phase 3. Place Source

Use:

- `docs/deployment/oci-source-transfer-runbook.md`
- `scripts/oci_source_tree_check.sh`

Do:

- prefer Git clone of `stable-15jun` after intended commits are pushed;
- fallback to `git archive` when local commits are not pushed yet;
- keep `.env` and backups out of source package.

## Phase 4. Configure Environment

Use:

- `.env.oci.example`
- `scripts/oci_generate_env_secrets.ps1`
- `scripts/oci_env_preflight.sh`

Do:

- create VM-local `.env`;
- fill secrets only on VM;
- run env preflight.

## Phase 5. Restore Data

Use:

- `docs/deployment/oci-backup-restore-runbook.md`
- `scripts/oci_backup_artifact_check.ps1`

Do:

- create/verify backup artifact;
- transfer full artifact directory;
- verify checksum;
- restore only into empty target.

## Phase 6. Start App

Use:

- `docs/deployment/oci-first-deploy-runbook.md`
- `scripts/oci_compose_preflight.ps1` before VM deploy if validating from Windows.

Do:

- render Compose;
- confirm no published backend/frontend ports;
- build and start.

## Phase 7. Publish Through Tunnel

Use:

- `docs/deployment/oci-cloudflare-handoff-template.md`
- `docs/deployment/oci-cloudflare-tunnel-runbook.md`

Do:

- create Cloudflare tunnel token;
- route hostname to `http://frontend:80`;
- keep OCI `80/443` closed.

## Phase 8. Smoke Test

Use:

- `scripts/oci_smoke_test.sh`
- `docs/deployment/oci-smoke-test-runbook.md`

Do:

- check backend health;
- check Postgres;
- check Redis;
- check tunnel;
- confirm no host ports.

## Phase 9. Operate And Recover

Use:

- `docs/deployment/oci-operations-runbook.md`
- `docs/deployment/oci-disaster-recovery-runbook.md`

Do:

- monitor daily first week;
- preserve volumes on rollback;
- recover only from known commit and verified backup.
