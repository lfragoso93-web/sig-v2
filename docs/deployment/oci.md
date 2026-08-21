# SGI v2 on OCI Always Free

Last updated: 2026-08-21

This document records the read-only OCI inventory and ARM64 audit used before any SGI v2 production provisioning on Oracle Cloud Infrastructure.

## Rules

- Work from branch `stable-15jun`.
- Do not work directly on `main`.
- Do not create OCI resources unless the target resource is verified against real tenancy limits and can remain at expected cost `R$ 0.00`.
- Do not create NAT Gateway, Load Balancer, managed database, managed Redis, OKE, or extra nodes for the initial deployment.
- Do not expose PostgreSQL `5432`, Redis `6379`, or backend `8000` to the Internet.
- Do not copy local OCI API private keys to the VM.

## Git Baseline

- Local branch: `stable-15jun`.
- Local HEAD: `20813bf4e9c9eae74bb0f2a71bcd8364898e5b01`.
- Remote `stable-15jun`: `20813bf4e9c9eae74bb0f2a71bcd8364898e5b01`.
- Remote `main`: `75e6b176225618613ddb7b7624ecf2b5d9b43feb`.
- Migration issue: `#284`.
- Open PRs at inventory time: Dependabot PRs only.

## OCI Inventory

All OCI data below was collected read-only with OCI CLI `3.90.3` through `E:\OCI\oci.exe`.

### Identity and Regions

- Home region: `sa-saopaulo-1`.
- Region key: `GRU`.
- Region subscriptions: only `sa-saopaulo-1`, status `READY`.
- Availability Domain: `qWqO:SA-SAOPAULO-1-AD-1`.
- Additional compartments returned by subtree query: none.

### Compute

- Target shape: `VM.Standard.A1.Flex`.
- Shape billing type reported by OCI: `LIMITED_FREE`.
- Processor: Ampere Altra.
- Shape is flexible.
- Existing active compute instances: none.
- Existing terminated instance: `sgi`, shape `VM.Standard.E2.1.Micro`, lifecycle `TERMINATED`.

Real A1 limits and usage:

| Scope | OCPU limit | OCPU used | OCPU available | Memory limit | Memory used | Memory available |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Regional | 16 | 0 | 16 | 96 GB | 0 GB | 96 GB |
| AD | 41 | 0 | 41 | 277 GB | 0 GB | 277 GB |

Planning constraint: use the regional A1 limit as the conservative ceiling for initial sizing.

### Storage

- Free Block/Boot volume storage limit: `200 GB`.
- Free Block/Boot volume storage used by Limits API: `0 GB`.
- Free Block/Boot volume storage available: `200 GB`.
- Free backup count limit: `5`.
- Existing block volumes: none listed.
- Existing volume backups: none listed.
- Existing boot volume backups: none listed.
- Existing terminated boot volume: `sgi (Boot Volume)`, `47 GB`, lifecycle `TERMINATED`, system tag `free-tier-retained=true`.

Initial recommendation: use only the boot volume for OS, Docker, Docker volumes, PostgreSQL data, Redis data, and local artifacts. Do not create a separate Block Volume unless recovery design later proves it useful and still free.

### Object Storage

- Namespace: `gr9x8wmlo9ji`.
- Existing buckets: none listed.
- Limits API returned bucket and storage-byte limits, but not an Always Free usage classification.

Initial recommendation: do not create an Object Storage bucket until backup design, retention, request volume, and Always Free classification are confirmed.

### Network

Existing VCN:

- Name: `sgi-vcn-public`.
- CIDR: `10.0.0.0/24`.
- State: `AVAILABLE`.

Existing subnet:

- Name: `sgi-subnet-public`.
- CIDR: `10.0.0.0/24`.
- Public IP on VNIC allowed: yes.
- Internet ingress prohibited: no.

Gateways and routing:

- Internet Gateway: none listed.
- NAT Gateway: none listed.
- Route table: no route rules.
- Public regional IPs: none listed.
- NSGs: none listed.

Security List:

- Egress: all protocols to `0.0.0.0/0`.
- Ingress: SSH `22` from `0.0.0.0/0`.
- Ingress: ICMP type 3/code 4 from `0.0.0.0/0`.
- Ingress: ICMP type 3 from `10.0.0.0/24`.

Security finding: the default SSH rule is not acceptable for production. Before any public VM exposure, SSH must be restricted or replaced with a safer access pattern.

## ARM64 Audit

Docker Buildx supports `linux/arm64` locally.

Static search found no hardcoded `linux/amd64` in active Dockerfiles or Compose files. Architecture strings in `frontend/package-lock.json` are optional multi-architecture package entries. A `Win64; x64` string exists only in an HTTP User-Agent and is not a binary download.

### Backend

- Build command: `docker buildx build --platform linux/arm64 -t sig-v2-backend:arm64-audit --load ./backend`.
- Result: success.
- Image architecture: `arm64/linux`.
- `app.main` import: OK.
- `pg_dump --version`: PostgreSQL client `16.15`.
- Native dependency smoke tests: OK for `psycopg2`, `asyncpg`, `cryptography`, `bcrypt`, `numpy`, `pandas`, `reportlab`, `uvloop`, `httptools`, and `pyyaml`.

Finding: backend Docker context is about `56 MB` and includes enough content to make ARM64 builds unnecessarily slow. Audit `.dockerignore` in a later small block.

### Frontend

- Build command: `docker buildx build --platform linux/arm64 -t sig-v2-frontend:arm64-audit --load ./frontend`.
- Result: success.
- Image architecture: `arm64/linux`.
- `npm install`: 347 packages, `0 vulnerabilities`.
- Vite build: success, 3445 modules transformed.
- Runtime smoke: `nginx -t` OK with a temporary host mapping for `backend`.

### Database and Cache Images

- `postgres:16-alpine`: ARM64 smoke OK, PostgreSQL `16.15`.
- `redis:7-alpine`: ARM64 smoke OK, Redis `7.4.11`.

### Classification

The SGI v2 Docker stack is ARM64 COMPATIBLE for OCI Ampere A1.

## Initial Provisioning Proposal

Use one VM only:

- Shape: `VM.Standard.A1.Flex`.
- OCPU: `2`.
- RAM: `12 GB`.
- Boot Volume: `80 GB` or `100 GB`.
- Block Volume: none.
- OS: Ubuntu Server 24.04 ARM64.
- Database: PostgreSQL container.
- Cache: Redis container.
- App runtime: Docker Compose.
- NAT Gateway: none.
- Load Balancer: none.
- Object Storage: not yet.

The proposal intentionally uses less than the confirmed A1 regional limit of `16 OCPU / 96 GB` and less than the confirmed free Block/Boot storage limit of `200 GB`.

## Cost Guardrail Table

| Resource | Configuration | Free limit verified | Planned use | Expected cost |
| --- | --- | ---: | ---: | ---: |
| Compute | `VM.Standard.A1.Flex` | 16 OCPU / 96 GB regional A1 available, shape `LIMITED_FREE` | 2 OCPU / 12 GB | R$ 0 |
| Boot Volume | Balanced boot volume | 200 GB free storage available | 80-100 GB | R$ 0 |
| Block Volume | None | 200 GB free storage shared with boot volumes | 0 GB | R$ 0 |
| Object Storage | None initially | Not classified enough for backup use yet | 0 buckets | R$ 0 |
| Network | VCN/subnet, no NAT, no LB | No NAT/LB planned | Direct VM or tunnel path | R$ 0 |

## Security Gates Before Provisioning

- Do not reuse the default SSH-open security list as production ingress.
- Prefer Tailscale or Cloudflare Tunnel for administrative/app exposure if it keeps the design simpler and free.
- If public IP plus reverse proxy is used, allow only necessary ports.
- Never expose PostgreSQL, Redis, or backend directly.
- Disable password SSH and root login on the VM.
- Keep app secrets in VM-local environment files, not in Git.

## GO / NO-GO

Status: GO for minimal provisioning planning, not yet for blind resource creation.

Before creating the VM, choose the network exposure model:

1. Cloudflare Tunnel, with no inbound public web ports required on OCI.
2. Public IP plus Caddy, with hardened OCI ingress and Linux firewall.

Recommended next block: `OCI-03A` network decision and minimal resource plan. Only after that should `OCI-06` compute provisioning run.

## OCI-03A Network Decision

Decision date: 2026-08-21

Recommended initial exposure model: Cloudflare Tunnel.

Rationale:

- The current OCI VCN has no Internet Gateway and no default route, so direct public exposure would require adding an Internet Gateway and route rule.
- The current default Security List allows SSH `22` from `0.0.0.0/0`, which must not be carried into production.
- Cloudflare Tunnel publishes HTTP applications through outbound-only connections from the VM to Cloudflare and does not require public inbound ports on OCI.
- Cloudflare documentation states Cloudflare Tunnel is available on all plans and that publishing an application through Tunnel does not require a paid Cloudflare Access plan. Access seats are only needed for Access policy login controls.
- `cloudflared` has Linux ARM64 support, matching the A1 target.
- OCI networking pricing states public internet egress includes the first 10 TB/month free. For this personal production deployment, expected Cloudflare Tunnel egress is far below that threshold.
- Avoiding public inbound HTTP/HTTPS and SSH on day one keeps the first production shape simpler: one VM, one Docker Compose stack, no NAT Gateway, no Load Balancer, no public IP dependency for the application.

Public IP plus Caddy remains a valid fallback if Cloudflare Tunnel is operationally unsuitable. That fallback would require:

- Internet Gateway.
- Route rule `0.0.0.0/0` to the Internet Gateway.
- Hardened ingress for only `80/443`, or `443` if certificate flow allows.
- No direct exposure for `5432`, `6379`, or `8000`.
- SSH access restricted by Tailscale, Bastion, or a known administrative IP.
- Linux firewall rules aligned with OCI Security List or NSG rules.

Initial Cloudflare Tunnel target:

```text
Cloudflare DNS / Tunnel
        |
outbound cloudflared connection
        |
OCI VM.Standard.A1.Flex
        |
Docker Compose
        |
frontend nginx :80 -> /api -> backend:8000
backend -> PostgreSQL / Redis on Docker network
```

OCI resources required for the first Tunnel-based VM:

- One `VM.Standard.A1.Flex`.
- One boot volume.
- One VCN/subnet path with outbound Internet access.
- No NAT Gateway.
- No Load Balancer.
- No Object Storage bucket yet.
- No reserved public IP for the application.

Open design item: outbound Internet from the VM still requires a valid route. Because the existing VCN currently has no Internet Gateway and no route rules, the minimal network plan must either add an Internet Gateway to the existing VCN or create a clean dedicated VCN with an Internet Gateway. NAT Gateway remains prohibited.

Recommendation for the next block: create a minimal network plan that reuses `sgi-vcn-public` only if it can be hardened cleanly. Prefer a dedicated NSG over broad default Security List edits for production ingress/egress clarity.

References checked on 2026-08-21:

- Cloudflare Tunnel documentation: `https://developers.cloudflare.com/tunnel/`
- Cloudflare Tunnel published applications: `https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/routing-to-tunnel/`
- Cloudflare Tunnel downloads: `https://developers.cloudflare.com/tunnel/downloads/`
- OCI VCN pricing: `https://www.oracle.com/cloud/networking/virtual-cloud-network/pricing/`
- OCI Public IP documentation: `https://docs.oracle.com/en-us/iaas/Content/Network/Tasks/managingpublicIPs.htm`
