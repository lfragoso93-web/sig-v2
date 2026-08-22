# SGI v2 OCI Cloudflare Tunnel Runbook

Status: prepared before the VM exists.

Goal: publish SGI v2 through Cloudflare Tunnel without exposing OCI inbound `80/443`.

Handoff template:

- `docs/deployment/oci-cloudflare-handoff-template.md`

## 1. Decisions

- Cloudflare Tunnel is the only public web entrypoint.
- OCI NSG remains without inbound `80/443`.
- Frontend nginx listens only inside Docker on `frontend:80`.
- Backend listens only inside Docker on `backend:8000`.
- Cloudflare tunnel token is stored only in the VM-local `.env`.

## 2. Cloudflare Setup

In Cloudflare Zero Trust:

1. Create a tunnel for SGI v2.
2. Choose Docker connector instructions.
3. Create a public hostname for the app.
4. Route the hostname to the local service:

```text
http://frontend:80
```

5. Copy only the tunnel token to the VM `.env`:

```env
CLOUDFLARE_TUNNEL_TOKEN=<vm-local-token>
```

Do not copy the token into Git, issues, docs, shell history snippets, screenshots, or support tickets.

After setup, fill `docs/deployment/oci-cloudflare-handoff-template.md` with hostname and status only. Do not paste the token into the template.

## 3. DNS And App Environment

Set the production hostname in `.env`:

```env
CORS_ORIGINS=https://<final-hostname>
VITE_API_URL=
```

Expected behavior:

- Browser loads the frontend from the Cloudflare hostname.
- Frontend calls `/api`.
- Nginx proxies `/api` to `backend:8000` inside Docker.
- No public OCI port receives web traffic.

## 4. Compose Validation

Before starting the stack:

```bash
cd /opt/sgi-v2
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.oci.yml config > /tmp/sgi-compose-rendered.yml
grep -n "published:" /tmp/sgi-compose-rendered.yml || true
grep -n "cloudflared:" /tmp/sgi-compose-rendered.yml
```

Expected:

- No `published:` entries for `backend`.
- No `published:` entries for `frontend`.
- `cloudflared` service is present.

## 5. Tunnel Startup Check

After app start:

```bash
cd /opt/sgi-v2
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.oci.yml logs cloudflared --tail=150
```

Expected:

- Tunnel authenticates successfully.
- Tunnel connection is established.
- No token value appears in copied logs.

## 6. Public Smoke Checks

From the operator machine:

```bash
curl -I https://<final-hostname>
curl -f https://<final-hostname>/api/health
```

Expected:

- Frontend returns HTTP success.
- `/api/health` returns HTTP success through nginx.

## 7. OCI Security Recheck

After tunnel works, verify OCI still has no public app ingress:

- NSG `sgi-prod-vm-nsg` has no ingress rules.
- Default Security List is not broadened.
- No Load Balancer exists.
- No reserved public IP exists.
- No NAT Gateway exists.

NO-GO:

- Opening OCI ingress `80` or `443` to work around tunnel errors.
- Publishing backend/frontend host ports in Compose.
- Exposing PostgreSQL, Redis, or backend publicly.
- Committing the tunnel token.
