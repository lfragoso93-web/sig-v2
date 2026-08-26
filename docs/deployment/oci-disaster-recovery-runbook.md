# SGI v2 OCI Disaster Recovery Runbook

Status: prepared before the VM exists.

Goal: recover the single-VM deployment without adding paid managed services.

## 1. Assumptions

- The authoritative source code is Git branch `stable-15jun`.
- Application data lives in Docker volumes on the VM boot volume.
- Auditable database backup artifacts are kept outside Git.
- Cloudflare Tunnel token can be recreated if lost.
- OCI Stack `sgi-prod-a1-01` preserves the VM create configuration.

## 2. Minimum Recovery Inputs

Needed to rebuild:

- Latest good Git commit SHA.
- Latest verified backup artifact directory.
- VM-local production values for `.env`.
- Cloudflare hostname and tunnel token, or ability to create a new token.
- OCI Stack saved configuration.

NO-GO:

- Rebuilding from an unknown commit.
- Restoring from a backup without checksum.
- Creating paid OCI resources for recovery.

## 3. VM Loss Recovery

1. Retry/apply the saved OCI Stack.
2. Confirm the VM is `VM.Standard.A1.Flex`.
3. Confirm boot volume size remains `80 GB`.
4. Confirm VNIC has `sgi-prod-vm-nsg`.
5. Confirm no ingress rules were added.
6. Run cloud-init baseline checks.
7. Place source in `/opt/sgi-v2`.
8. Recreate `.env` locally on the VM.
9. Transfer verified backup artifact.
10. Restore database with `docs/deployment/oci-backup-restore-runbook.md`.
11. Start app and run `sh scripts/oci_smoke_test.sh`.

## 4. App Regression Recovery

If a deploy fails but the VM and data are intact:

```bash
cd /opt/sgi-v2
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.oci.yml down
git checkout <previous-good-sha>
APP_COMMIT_SHA="$(git rev-parse HEAD)"
sed -i "s/^APP_COMMIT_SHA=.*/APP_COMMIT_SHA=${APP_COMMIT_SHA}/" .env
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.oci.yml up -d --build
sh scripts/oci_smoke_test.sh
```

Do not delete volumes for an app regression.

## 5. Tunnel Recovery

If Cloudflare Tunnel token is lost or revoked:

1. Create or rotate the token in Cloudflare.
2. Update only VM-local `.env`.
3. Restart only `cloudflared`.

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.oci.yml restart cloudflared
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.oci.yml logs --tail=100 cloudflared
```

Do not open OCI `80/443` ingress as a tunnel workaround.

## 6. Data Reset Recovery

Only after verified backup and explicit approval:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.oci.yml down
```

Then use an approved process to create a fresh empty target database or reset volumes. Re-run restore from the verified backup.

Never run destructive volume deletion during diagnosis.

## 7. Post-Recovery Checks

- `sh scripts/oci_env_preflight.sh .env`
- `sh scripts/oci_smoke_test.sh`
- OCI Cost Analysis has no unexpected charges.
- NSG has no ingress rules.
- Public hostname works through Cloudflare Tunnel.
