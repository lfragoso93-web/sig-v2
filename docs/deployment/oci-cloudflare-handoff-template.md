# OCI Cloudflare Tunnel Handoff Template

Fill this after the Cloudflare Tunnel and public hostname are created.

Do not record the tunnel token, connector secret, account secret, or API token in this file.

## Tunnel

- Tunnel name:
- Cloudflare account:
- Public hostname:
- Service target: `http://frontend:80`
- Connector type: Docker
- Token stored only in VM-local `.env`: yes/no

## DNS

- Hostname:
- DNS route created by Cloudflare Tunnel: yes/no
- Proxied through Cloudflare: yes/no

## Application Environment

Expected VM-local values:

```env
CORS_ORIGINS=https://<final-hostname>
VITE_API_URL=
CLOUDFLARE_TUNNEL_TOKEN=<vm-local-only>
```

Do not paste the real token here.

## OCI Security Confirmation

- NSG `sgi-prod-vm-nsg` has no ingress rules: yes/no
- OCI ingress `80` is closed: yes/no
- OCI ingress `443` is closed: yes/no
- Backend `8000` is not exposed publicly: yes/no
- PostgreSQL `5432` is not exposed publicly: yes/no
- Redis `6379` is not exposed publicly: yes/no

## Public Checks

Run from the operator machine:

```bash
curl -I https://<final-hostname>
curl -f https://<final-hostname>/api/health
```

Expected:

- Frontend responds through Cloudflare.
- `/api/health` responds through the frontend nginx proxy.
- No direct OCI app port is opened.

## Log Check

Run on the VM:

```bash
cd /opt/sgi-v2
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.oci.yml logs cloudflared --tail=150
```

Record only non-secret status:

- Tunnel connected:
- Error count:
- Last checked at:

