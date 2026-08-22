# SGI v2 OCI First Deploy Runbook

Status: prepared before the VM exists.

Target VM profile:

- Shape: `VM.Standard.A1.Flex`.
- Initial size: `1 OCPU / 6 GB`.
- Boot volume: `80 GB`.
- OS: Ubuntu ARM64.
- App directory: `/opt/sgi-v2`.
- Network entrypoint: Cloudflare Tunnel only.

## 1. Post-Boot Baseline Checks

Run after the VM reaches `RUNNING` and cloud-init has had time to finish.

```bash
cloud-init status --wait
cloud-init status --long
docker --version
docker compose version
sudo systemctl status docker --no-pager
sudo ufw status verbose
ls -ld /opt/sgi-v2
```

Expected:

- `cloud-init` is done.
- Docker and Docker Compose plugin are installed.
- Docker service is active.
- UFW default incoming is deny.
- UFW default outgoing is allow.
- `/opt/sgi-v2` exists and is owned by `ubuntu`.

NO-GO:

- Docker is missing.
- UFW is disabled or allows public inbound by default.
- `/opt/sgi-v2` is missing.

## 2. Deployment Source

Use the current `stable-15jun` source state.

Preferred if GitHub access is available from the VM:

```bash
cd /opt
git clone --branch stable-15jun <repo-url> sgi-v2
cd /opt/sgi-v2
git rev-parse HEAD
```

Fallback if GitHub auth is not available:

```bash
cd /opt/sgi-v2
# Copy the repo contents from the operator machine by the approved transfer method.
git rev-parse HEAD
```

Expected:

- The deployed commit is known and recorded in `.env` as `APP_COMMIT_SHA`.
- No local `.env` is committed.

## 3. VM-Local Environment

Create the VM-local environment file:

```bash
cd /opt/sgi-v2
cp .env.oci.example .env
chmod 600 .env
```

Fill these values only on the VM:

- `APP_COMMIT_SHA`: deployed Git commit.
- `POSTGRES_PASSWORD`: strong generated value.
- `DATABASE_URL`: same Postgres password.
- `ASYNC_DATABASE_URL`: same Postgres password.
- `SECRET_KEY`: at least 32 random characters.
- `CORS_ORIGINS`: final Cloudflare HTTPS hostname.
- `SUPERADMIN_EMAIL`: production admin email.
- `SUPERADMIN_PASSWORD`: strong non-default password.
- `BRAPI_TOKEN` or compatible market-data token if needed.
- `ALPHA_VANTAGE_API_KEY` if needed.
- `CLOUDFLARE_TUNNEL_TOKEN`: token created in Cloudflare.

Suggested local generation commands:

```bash
openssl rand -base64 24
openssl rand -hex 32
```

NO-GO:

- `.env` contains default production-blocked values.
- `.env` is copied back into Git.
- Cloudflare tunnel token appears in logs, docs, issues, or commits.

Run the env preflight:

```bash
cd /opt/sgi-v2
sh scripts/oci_env_preflight.sh .env
```

Expected:

- Required production values are present.
- Placeholders are gone.
- Database URLs use the same VM-local `POSTGRES_PASSWORD` and Docker host `db:5432`.
- `POSTGRES_PASSWORD` is URL-safe so it can be embedded in both database URLs.
- `CORS_ORIGINS` uses the final HTTPS hostname, not localhost.
- Initial OCI worker/profile values are safe.

## 4. Render Compose Before Start

```bash
cd /opt/sgi-v2
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.oci.yml config > /tmp/sgi-compose-rendered.yml
grep -n "published:" /tmp/sgi-compose-rendered.yml || true
grep -n "cloudflared:" /tmp/sgi-compose-rendered.yml
```

Expected:

- No `published:` entries for `backend` or `frontend`.
- `cloudflared` is present.

NO-GO:

- Backend or frontend publishes a host port.
- Cloudflare Tunnel service is missing.

## 5. Build And Start

```bash
cd /opt/sgi-v2
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.oci.yml up -d --build
```

Follow startup:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.oci.yml ps
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.oci.yml logs --tail=100
```

For the initial `1 OCPU / 6 GB` VM, keep:

```env
BACKEND_WORKERS=1
```

## 6. Local Container Health Checks

```bash
cd /opt/sgi-v2
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.oci.yml exec backend curl -f http://localhost:8000/health
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.oci.yml exec db pg_isready -U "${POSTGRES_USER:-sgi}"
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.oci.yml exec redis redis-cli ping
```

Expected:

- Backend health endpoint returns success.
- Postgres is ready.
- Redis returns `PONG`.

## 7. Tunnel Check

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.oci.yml logs cloudflared --tail=100
```

Expected:

- Tunnel connects successfully.
- Public hostname reaches the frontend through Cloudflare.
- `/api` requests are proxied to backend internally.

NO-GO:

- Opening OCI ingress for `80` or `443` to bypass the tunnel.
- Exposing backend, Postgres, or Redis publicly.

## 8. Rollback

Stop application stack:

```bash
cd /opt/sgi-v2
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.oci.yml down
```

Keep volumes unless an explicit data reset is approved.

Do not run:

```bash
docker compose down -v
```

without a verified backup and explicit approval.
