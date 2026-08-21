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

## OCI-03B Minimal Network Plan

Decision date: 2026-08-21

Goal: give the A1 VM outbound Internet access for OS packages, Docker image pulls, Git, and Cloudflare Tunnel, while keeping inbound OCI exposure closed by default.

### Reuse vs Recreate

Reuse the existing VCN if the following changes can be applied cleanly:

- VCN: `sgi-vcn-public`.
- Subnet: `sgi-subnet-public`.
- Keep CIDR: `10.0.0.0/24`.
- Add exactly one Internet Gateway to this VCN.
- Add one default route `0.0.0.0/0` to that Internet Gateway.
- Do not create NAT Gateway.
- Do not create Load Balancer.
- Do not reserve a public IP for the application.
- Use only an ephemeral public IP on the VM VNIC for outbound Internet access, not as an inbound application endpoint.

Reasoning: the existing VCN/subnet are empty enough to reuse and already scoped to SGI naming. Creating a duplicate VCN would add cleanup and drift risk without clear benefit.

### Public IP Policy

Preferred first deployment:

- Launch the VM with an ephemeral public IP so outbound Internet works through the Internet Gateway without a NAT Gateway.
- Use outbound-only Cloudflare Tunnel for web traffic.
- Use cloud-init to install the baseline packages and bootstrap access tooling.

Inbound policy for bootstrap:

- Do not treat the ephemeral public IP as a public application endpoint.
- Keep OCI ingress closed by default.
- If initial direct SSH is explicitly authorized, restrict SSH to a known administrative source IP.
- Disable password authentication and root login.
- Remove public SSH exposure after Tailscale or another safer access path is confirmed.

Do not use a reserved public IP for the first tunnel-based deployment.

### NSG Plan

Create a dedicated production NSG instead of relying on the default Security List:

- Name: `sgi-prod-vm-nsg`.
- Purpose: rules attached directly to the VM VNIC.

Ingress rules:

- Default: no inbound TCP application ports.
- No `22` from `0.0.0.0/0`.
- No `80/443` inbound for the Cloudflare Tunnel path.
- No `5432`, `6379`, or `8000` inbound.
- Optional temporary SSH rule only if explicitly needed for bootstrap, restricted to the administrative IP.

Egress rules:

- Allow outbound TCP `443` to `0.0.0.0/0` for OS repositories, Docker registries, GitHub, Cloudflare Tunnel, and TLS APIs.
- Allow outbound TCP `80` to `0.0.0.0/0` only if package repositories or redirects require it during bootstrap.
- Allow outbound UDP/TCP `53` if VCN DNS resolution requires explicit NSG egress.
- Allow outbound UDP `7844` to `0.0.0.0/0` for Cloudflare Tunnel if using QUIC transport.

Tightening path after the VM is stable:

- Prefer Cloudflare Tunnel over public app ingress.
- Confirm whether `cloudflared` uses HTTP/2 over TCP `443` or QUIC over UDP `7844`.
- Remove outbound `80` if not required.
- Keep database/cache/backend private to the Docker network.

### Security List Plan

Do not broaden the default Security List.

Before production exposure:

- Remove or stop relying on the default SSH ingress `22` from `0.0.0.0/0`.
- Use the NSG as the authoritative production control for VM traffic.
- Keep subnet-level rules minimal and non-contradictory.

### Linux Firewall

Apply a second layer on the VM:

- Default deny inbound.
- Allow loopback.
- Allow established/related.
- Allow outbound.
- Do not open PostgreSQL, Redis, or backend to non-local interfaces.
- If SSH is temporarily enabled, restrict it to the administrative source and disable it once safer access is active.

### Cloudflare Tunnel Runtime

Run `cloudflared` as part of the deployment, preferably in Docker Compose, after the tunnel token is created outside the repository.

Secret handling:

- Do not commit the tunnel token.
- Store the token in the VM-local `.env` or a VM-local systemd environment file.
- Do not print the token in logs, docs, or issues.

Expected route:

```text
Internet users
        |
Cloudflare DNS / Tunnel hostname
        |
Cloudflare network
        |
outbound tunnel from VM
        |
cloudflared on VM
        |
frontend nginx container :80
        |
/api -> backend:8000
```

### Minimal OCI Changes for OCI-05

When the plan is approved, the next OCI-changing block should create or update only:

1. Internet Gateway for `sgi-vcn-public`.
2. Default route in the existing route table to the Internet Gateway.
3. Dedicated NSG `sgi-prod-vm-nsg`.
4. NSG egress rules required for bootstrap and Cloudflare Tunnel.
5. Ephemeral public IP assignment on the VM VNIC for outbound connectivity.
6. No inbound rules except a temporary restricted SSH rule if explicitly authorized.

Expected monthly cost of this network plan: `R$ 0.00`, assuming personal traffic remains below the confirmed public egress free threshold and no paid network services are introduced.

NO-GO conditions:

- Any requirement to create NAT Gateway.
- Any requirement to create Load Balancer.
- Any requirement to expose SSH to `0.0.0.0/0`.
- Any uncertainty that a proposed network resource remains free.

## OCI-04 Production Compose and Tunnel Artifacts

Decision date: 2026-08-21

Goal: prepare the Docker Compose inputs for the OCI A1 VM without committing secrets and without publishing application ports directly on the VM public IP.

Artifacts added:

- `.env.oci.example`: production-shaped environment contract for the VM.
- `docker-compose.oci.yml`: OCI-specific Compose override for Cloudflare Tunnel and closed host ports.

Expected VM command shape:

```bash
cp .env.oci.example .env
# Fill real values only on the VM: passwords, SECRET_KEY, CORS hostname, API tokens, and CLOUDFLARE_TUNNEL_TOKEN.
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.oci.yml up -d --build
```

Production exposure behavior:

- `backend` keeps listening only inside Docker on `backend:8000`.
- `frontend` keeps listening only inside Docker on `frontend:80`.
- `cloudflared` joins the same Docker network and publishes the frontend through the outbound tunnel.
- Host `ports` are removed by the OCI override, so the VM public IP is not the application entrypoint.

Required manual VM values:

- `POSTGRES_PASSWORD`: strong VM-local password.
- `SECRET_KEY`: at least 32 random characters.
- `SUPERADMIN_PASSWORD`: strong non-default password.
- `CORS_ORIGINS`: final Cloudflare HTTPS hostname.
- `CLOUDFLARE_TUNNEL_TOKEN`: created in Cloudflare and stored only in VM `.env`.

Validation commands:

```bash
CLOUDFLARE_TUNNEL_TOKEN=dummy docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.oci.yml config
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.oci.yml build
```

NO-GO conditions:

- Any real tunnel token, password, API key, or production hostname secret appears in Git.
- The rendered OCI Compose publishes host ports for `frontend` or `backend`.
- The rendered OCI Compose requires a paid OCI service.

## OCI-05A Minimal Network Provisioning Script

Decision date: 2026-08-21

Goal: prepare an idempotent PowerShell script for the minimal OCI network changes approved in OCI-03B, while keeping the default execution mode as dry-run.

Artifact added:

- `scripts/oci_minimal_network.ps1`

What the script does in dry-run mode:

- Locates VCN `sgi-vcn-public`.
- Checks the default route table.
- Checks for Internet Gateway `sgi-prod-ig`.
- Checks for NSG `sgi-prod-vm-nsg`.
- Prints the changes it would apply.
- Creates nothing unless `-Execute` is passed.

What the script does with `-Execute`:

- Creates Internet Gateway `sgi-prod-ig` if missing.
- Adds route `0.0.0.0/0` to the Internet Gateway if missing.
- Creates NSG `sgi-prod-vm-nsg` if missing.
- Adds egress-only NSG rules for TCP `443`, TCP `80`, TCP `53`, UDP `53`, and UDP `7844`.
- Creates no ingress rules.

Manual Windows command:

```powershell
.\scripts\oci_minimal_network.ps1 `
  -TenancyId "<tenancy-ocid>" `
  -OciExe "E:\OCI\oci.exe"
```

Manual Windows apply command after reviewing dry-run output:

```powershell
.\scripts\oci_minimal_network.ps1 `
  -TenancyId "<tenancy-ocid>" `
  -OciExe "E:\OCI\oci.exe" `
  -Execute
```

Local execution note: OCI CLI calls from this Codex session timed out on 2026-08-21 before applying any network changes, so the script was not executed against OCI from here.

NO-GO conditions:

- VCN `sgi-vcn-public` is not `AVAILABLE`.
- Existing default route `0.0.0.0/0` points to a different network entity.
- Script proposes any ingress rule.
- Script proposes NAT Gateway, Load Balancer, managed database, Redis, Kubernetes, or reserved public IP.
