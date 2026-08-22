# SGI v2 OCI Operations Runbook

Status: prepared before the VM exists.

Goal: define routine operations for the single-VM OCI deployment without introducing paid services or public ingress.

## 1. Daily Status

Run from `/opt/sgi-v2`:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.oci.yml ps
docker system df
sudo ufw status verbose
df -h /
free -h
```

Expected:

- App containers are running or healthy.
- Disk usage leaves room for logs, images, and backups.
- UFW default incoming is deny.
- Memory pressure is acceptable for `1 OCPU / 6 GB`.

## 2. Logs

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.oci.yml logs --tail=200 backend
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.oci.yml logs --tail=200 frontend
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.oci.yml logs --tail=200 cloudflared
```

Do not paste logs externally until checking they contain no tokens, passwords, API keys, or personal data.

## 3. Controlled Restart

Restart app services without touching data volumes:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.oci.yml restart backend frontend cloudflared
sh scripts/oci_smoke_test.sh
```

Restart database/cache only if needed:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.oci.yml restart db redis
```

## 4. Update Deployment

Before update:

```bash
git status --short
git fetch origin stable-15jun
git log --oneline HEAD..origin/stable-15jun
```

Apply update:

```bash
git pull --ff-only origin stable-15jun
APP_COMMIT_SHA="$(git rev-parse HEAD)"
sed -i "s/^APP_COMMIT_SHA=.*/APP_COMMIT_SHA=${APP_COMMIT_SHA}/" .env
sh scripts/oci_env_preflight.sh .env
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.oci.yml up -d --build
sh scripts/oci_smoke_test.sh
```

NO-GO:

- local uncommitted changes on the VM.
- `.env` missing or failing preflight.
- update requires opening OCI ingress.

## 5. Rollback Code

Rollback code without deleting volumes:

```bash
git log --oneline -5
git checkout <previous-good-sha>
APP_COMMIT_SHA="$(git rev-parse HEAD)"
sed -i "s/^APP_COMMIT_SHA=.*/APP_COMMIT_SHA=${APP_COMMIT_SHA}/" .env
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.oci.yml up -d --build
sh scripts/oci_smoke_test.sh
```

Return to branch tracking after incident:

```bash
git checkout stable-15jun
git pull --ff-only origin stable-15jun
```

## 6. Cleanup

Safe cleanup:

```bash
docker image prune
docker builder prune
```

Do not run:

```bash
docker volume prune
docker compose down -v
```

unless backups are verified and data deletion is explicitly approved.

## 7. Cost And Security Recheck

Weekly:

- OCI Cost Analysis has no unexpected charges.
- No NAT Gateway exists.
- No Load Balancer exists.
- No reserved public IP exists.
- NSG `sgi-prod-vm-nsg` has no ingress rules.
- Cloudflare Tunnel remains healthy.
