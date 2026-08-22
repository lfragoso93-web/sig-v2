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

Windows CLI note: the first manual `-Execute` run created Internet Gateway `sgi-prod-ig`, then failed because OCI CLI did not accept a temporary `file://C:\...` JSON path for `--route-rules`. Later runs confirmed PowerShell/OCI CLI JSON argument handling is fragile on Windows. The script now writes compact JSON arrays to UTF-8 temporary files and passes them as `file:///C:/...` URIs; it is safe to rerun and should detect the existing Internet Gateway before continuing with route table and NSG steps.

NO-GO conditions:

- VCN `sgi-vcn-public` is not `AVAILABLE`.
- Existing default route `0.0.0.0/0` points to a different network entity.
- Script proposes any ingress rule.
- Script proposes NAT Gateway, Load Balancer, managed database, Redis, Kubernetes, or reserved public IP.

## OCI-05B Minimal Network Created

Completion date: 2026-08-21

Result: minimal OCI network path created manually in the OCI Console after Windows OCI CLI JSON handling blocked the scripted route-table update.

Confirmed resources:

- Internet Gateway: `sgi-prod-ig`.
- Internet Gateway state: `AVAILABLE`.
- Internet Gateway status: enabled.
- Route table: default route table for `sgi-vcn-public`.
- Route: `0.0.0.0/0` to Internet Gateway `sgi-prod-ig`.
- NSG: `sgi-prod-vm-nsg`.
- NSG ingress: no ingress rules intentionally created.
- NSG egress:
  - TCP `443` to `0.0.0.0/0`.
  - TCP `80` to `0.0.0.0/0`.
  - TCP `53` to `0.0.0.0/0`.
  - UDP `53` to `0.0.0.0/0`.
  - UDP `7844` to `0.0.0.0/0`.

Cost posture:

- No NAT Gateway created.
- No Load Balancer created.
- No reserved public IP created.
- No managed database, Redis, or Kubernetes created.
- Expected incremental monthly cost: `R$ 0.00`.

Next gate before VM creation:

- Create VM only with `VM.Standard.A1.Flex`.
- Keep total A1 allocation within Always Free limits.
- Use an ephemeral public IP only for outbound connectivity.
- Attach `sgi-prod-vm-nsg` to the VM VNIC.
- Do not add public application ingress.

## OCI-06 VM A1 Flex Plan

Decision date: 2026-08-21

Goal: define the VM creation parameters before launching the production host.

Read-only preflight confirmed:

- Region: `sa-saopaulo-1`.
- Availability Domain: `qWqO:SA-SAOPAULO-1-AD-1`.
- A1 AD availability: `41` OCPUs available, `0` used.
- Existing minimal network path is ready: `sgi-prod-ig`, default route, and `sgi-prod-vm-nsg`.

Planned instance:

- Display name: `sgi-prod-a1-01`.
- Shape: `VM.Standard.A1.Flex`.
- OCPUs: `2`.
- Memory: `12 GB`.
- Boot volume: `80 GB`.
- Image family: Canonical Ubuntu ARM64, prefer Ubuntu `24.04` if available for `VM.Standard.A1.Flex`; use Ubuntu `22.04` ARM64 only if `24.04` is unavailable.
- Subnet: `sgi-subnet-public`.
- Public IP: ephemeral public IP enabled on the primary VNIC for outbound Internet connectivity through the Internet Gateway.
- Reserved public IP: none.
- NSG: attach `sgi-prod-vm-nsg`.
- Security List: do not broaden default Security List rules.
- SSH ingress: do not open `22` to `0.0.0.0/0`; use Console/VNC/bootstrap path until a restricted admin access path is explicitly approved.

Capacity posture:

- Planned A1 allocation after create: `2` OCPUs, `12 GB`.
- Always Free A1 envelope previously checked: up to `4` OCPUs and `24 GB` total for Ampere A1.
- Remaining planned A1 headroom after create: `2` OCPUs, `12 GB`.
- Planned boot volume after create: `80 GB`.
- Always Free block/boot volume envelope previously checked: `200 GB` total.
- Remaining planned storage headroom after create: at least `120 GB`, assuming no other retained volumes are introduced.

Cloud-init responsibilities:

- Update OS packages.
- Install Docker Engine and Docker Compose plugin.
- Enable Docker service.
- Create `/opt/sgi-v2`.
- Configure a conservative Linux firewall:
  - default deny inbound;
  - allow loopback;
  - allow established/related;
  - allow outbound;
  - no PostgreSQL, Redis, backend, frontend, or SSH public ingress by default.
- Do not write application secrets into cloud-init.

Deployment responsibilities after VM creation:

- Copy or clone the `stable-15jun` deployment source.
- Create VM-local `.env` from `.env.oci.example`.
- Fill secrets only on the VM.
- Start Compose with:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.oci.yml up -d --build
```

NO-GO conditions:

- Shape is not `VM.Standard.A1.Flex`.
- Proposed OCPUs or memory exceed Always Free A1 envelope.
- Boot volume pushes total block/boot usage above Always Free storage envelope.
- Any reserved public IP is required.
- Any NAT Gateway, Load Balancer, managed database, Redis, Kubernetes, or other paid service is required.
- Any app or data service must be exposed through public ingress.

## OCI-07 VM Console Creation Checklist

Decision date: 2026-08-21

Goal: provide the exact manual Console checklist for creating the A1 VM without relying on OCI CLI JSON handling.

Cloud-init artifact:

- `docs/deployment/oci-cloud-init.yaml`

Console values:

- Name: `sgi-prod-a1-01`.
- Region: `sa-saopaulo-1`.
- Availability Domain: `qWqO:SA-SAOPAULO-1-AD-1`.
- Image: Canonical Ubuntu ARM64, Ubuntu `24.04` preferred.
- Shape: `VM.Standard.A1.Flex`.
- OCPUs: `2`.
- Memory: `12 GB`.
- Boot volume size: `80 GB`.
- VCN: `sgi-vcn-public`.
- Subnet: `sgi-subnet-public`.
- Public IPv4 address: assign ephemeral public IPv4.
- Reserved public IP: do not assign.
- NSG: attach `sgi-prod-vm-nsg`.
- SSH keys: add only the operator's public SSH key if the Console requires one; do not create any broad SSH ingress rule.
- Initialization script: paste the contents of `docs/deployment/oci-cloud-init.yaml`.

Expected cloud-init result:

- OS packages updated.
- Docker Engine installed from Docker's Ubuntu ARM64 repository.
- Docker Compose plugin installed.
- Docker service enabled and running.
- `/opt/sgi-v2` created and owned by `ubuntu`.
- `ubuntu` added to the `docker` group.
- UFW enabled with default deny inbound and allow outbound.
- No application secrets written to the VM by cloud-init.

Post-create checks from the OCI Console:

- Instance lifecycle state is `RUNNING`.
- Shape is `VM.Standard.A1.Flex`.
- OCPU count is `2`.
- Memory is `12 GB`.
- Boot volume is `80 GB`.
- Primary VNIC is attached to `sgi-subnet-public`.
- Primary VNIC is associated with `sgi-prod-vm-nsg`.
- Public IPv4 is ephemeral, not reserved.
- No new ingress rule was created for SSH, HTTP, HTTPS, PostgreSQL, Redis, or backend.

Post-create checks from the VM Console or Cloud Shell session:

```bash
cloud-init status --wait
docker --version
docker compose version
sudo ufw status verbose
ls -ld /opt/sgi-v2
```

Expected UFW posture:

- Default incoming: deny.
- Default outgoing: allow.
- No explicit public inbound allow rules.

NO-GO conditions:

- Console suggests any non-free shape or paid image.
- Console requires a reserved public IP.
- Console requires opening SSH, HTTP, or HTTPS ingress to the Internet.
- Cloud-init fails before Docker is installed.
- VM is created without `sgi-prod-vm-nsg`.

## OCI-07B VM Creation Capacity Block

Event date: 2026-08-21

Result: VM creation was attempted from the OCI Console with the safe Always Free configuration, but OCI returned insufficient host capacity for `VM.Standard.A1.Flex` in `AD-1`.

Observed OCI error:

- Capacity insufficient for shape `VM.Standard.A1.Flex` in availability domain `AD-1`.
- OCI suggested trying a different availability domain, retrying later, or creating without a fault domain selection.

Operational response:

- Do not switch to a paid shape.
- Do not increase OCPUs or memory.
- Do not add paid network or managed services.
- Save the request as an OCI Stack for later retry.

Current VM status:

- VM was not created.
- A stack was saved from the Console configuration for retry.
- Network resources remain ready: `sgi-prod-ig`, default route, and `sgi-prod-vm-nsg`.

Retry guidance:

- Retry only `VM.Standard.A1.Flex`.
- Keep `1 OCPU / 6 GB` if OCI capacity remains constrained.
- Scale later toward `2 OCPU / 12 GB` only if available and still within Always Free limits.
- Keep boot volume at `80 GB`.
- Keep ephemeral public IPv4 and no reserved public IP.
- Keep `sgi-prod-vm-nsg` attached.
- Keep cloud-init unchanged unless a specific boot error requires adjustment.

## OCI-08 First Deploy Runbook

Decision date: 2026-08-21

Goal: prepare the first deployment sequence while waiting for A1 capacity.

Artifact added:

- `docs/deployment/oci-first-deploy-runbook.md`

Key decisions:

- Initial backend worker count is `1` for the constrained `1 OCPU / 6 GB` A1 VM.
- Do not publish backend or frontend host ports.
- Do not bypass Cloudflare Tunnel by opening OCI ingress for `80` or `443`.
- Keep `.env` VM-local and out of Git.
- Stop rollback preserves Docker volumes by default.

Ready-to-run phases once the VM exists:

1. Post-boot baseline checks.
2. Deployment source placement in `/opt/sgi-v2`.
3. VM-local `.env` creation.
4. Compose render verification.
5. Build and start.
6. Backend/Postgres/Redis health checks.
7. Cloudflare Tunnel check.
8. Rollback without volume deletion.

## OCI-09 Backup And Restore Runbook

Decision date: 2026-08-21

Goal: prepare the database migration path before the OCI VM exists.

Artifact added:

- `docs/deployment/oci-backup-restore-runbook.md`

Key decisions:

- Use the existing backend backup/restore CLIs instead of a new migration script.
- Backup must run from `stable-15jun` with a full 40-character commit SHA.
- Backup artifacts must include dump, SHA-256, inventory, contents listing, and manifest.
- Restore validation should target an isolated empty PostgreSQL database before the final OCI restore.
- Restore uses checksum validation and single-transaction `pg_restore`.
- Rollback preserves Docker volumes by default.

## OCI-10 Cloudflare Tunnel Runbook

Decision date: 2026-08-21

Goal: prepare public app exposure without OCI inbound web ports.

Artifact added:

- `docs/deployment/oci-cloudflare-tunnel-runbook.md`

Key decisions:

- Cloudflare Tunnel is the only public web entrypoint.
- Tunnel routes to `http://frontend:80` inside Docker.
- `VITE_API_URL` remains empty so the frontend uses `/api`.
- `CORS_ORIGINS` must be the final Cloudflare HTTPS hostname.
- Tunnel token lives only in the VM-local `.env`.
- OCI NSG remains without ingress rules for `80/443`.

## OCI-11 Cost Guardrails

Decision date: 2026-08-21

Goal: keep every Stack retry and post-create check inside the approved cost envelope.

Artifact added:

- `docs/deployment/oci-cost-guardrails.md`

Key decisions:

- Retry only `VM.Standard.A1.Flex`.
- Initial retry size remains `1 OCPU / 6 GB`.
- Boot volume remains `80 GB`.
- Public IPv4 must be ephemeral, not reserved.
- NAT Gateway, Load Balancer, managed DB, Redis, Kubernetes, and reserved public IP remain forbidden.
- Check billing/cost daily for the first week after VM creation.

## OCI-12 Compose Preflight

Decision date: 2026-08-21

Goal: provide a local check that the OCI Compose overlay remains safe before deployment.

Artifact added:

- `scripts/oci_compose_preflight.ps1`

The preflight checks:

- backend does not publish host ports.
- frontend does not publish host ports.
- `cloudflared` service is present.
- backend worker count renders as `1`.
- no real-looking tunnel token appears in rendered config.

## OCI-13 Source Transfer Runbook

Decision date: 2026-08-21

Goal: prepare a fallback source transfer path if the VM cannot clone the repository directly.

Artifact added:

- `docs/deployment/oci-source-transfer-runbook.md`

Key decisions:

- Prefer `git clone --branch stable-15jun` on the VM.
- Fallback package uses `git archive` from the operator machine.
- Source package must not include `.env`, `.git`, `node_modules`, Terraform exports, or backup artifacts.
- Source transfer must not require opening OCI web ingress.

## OCI-14 Backend Docker Context Trim

Decision date: 2026-08-21

Goal: reduce backend Docker build context for the constrained initial A1 VM.

Change:

- Expanded `backend/.dockerignore`.

Excluded from backend production build context:

- Python/tool caches.
- Codex/runtime temp directories.
- pytest cache directories.
- review temp directories.
- backend tests and test-only requirements.

Expected effect:

- Smaller upload/build context.
- Less chance of Windows permission-denied temp directories affecting Docker builds.
- Lower I/O pressure on `1 OCPU / 6 GB` VM builds.

## OCI-15 Environment Preflight

Decision date: 2026-08-21

Goal: fail fast if the VM-local `.env` still contains placeholders or unsafe initial values.

Artifact added:

- `scripts/oci_env_preflight.sh`

The preflight checks:

- required production values are non-empty.
- placeholder values from `.env.oci.example` are gone.
- `SECRET_KEY` is at least 32 characters.
- `ENVIRONMENT=production`.
- `APP_DEBUG=false`.
- initial `BACKEND_WORKERS=1`.
- `VITE_API_URL` remains empty for nginx `/api` proxying.

## OCI-16 Smoke Test

Decision date: 2026-08-21

Goal: provide a post-deploy smoke test that verifies the stack without opening OCI ingress.

Artifacts added:

- `scripts/oci_smoke_test.sh`
- `docs/deployment/oci-smoke-test-runbook.md`

The smoke test checks:

- Compose service listing.
- backend `/health`.
- Postgres readiness.
- Redis ping.
- Cloudflare Tunnel logs availability.
- no published host ports in rendered Compose config.

## OCI-17 Line Endings And Operations

Decision date: 2026-08-21

Goal: make VM scripts safe to execute on Ubuntu and prepare routine operations.

Artifacts added:

- `.gitattributes`
- `docs/deployment/oci-operations-runbook.md`

Key decisions:

- Shell scripts and YAML files are forced to LF line endings.
- Routine operations preserve Docker volumes by default.
- Code updates use `git pull --ff-only`.
- Rollback changes code only unless data reset is explicitly approved.
- Weekly cost/security recheck remains part of operations.

## OCI-18 Disaster Recovery

Decision date: 2026-08-21

Goal: prepare a recovery path for VM loss, app regression, tunnel token rotation, and data restore without paid OCI services.

Artifact added:

- `docs/deployment/oci-disaster-recovery-runbook.md`

Key decisions:

- Recover VM via saved OCI Stack.
- Recover code from `stable-15jun` and known commit SHA.
- Recover data only from verified backup artifacts.
- Do not create paid services during recovery.
- Do not open OCI `80/443` ingress to work around tunnel failures.

## OCI-19 Execution Index

Decision date: 2026-08-21

Goal: provide one ordered entrypoint for all OCI runbooks.

Artifact added:

- `docs/deployment/oci-execution-index.md`

Execution phases:

1. Retry OCI Stack.
2. Validate VM baseline.
3. Place source.
4. Configure environment.
5. Restore data.
6. Start app.
7. Publish through tunnel.
8. Smoke test.
9. Operate and recover.

## OCI-20 Source Package Script

Decision date: 2026-08-21

Goal: make fallback source transfer repeatable without packaging local secrets or untracked files.

Artifact added:

- `scripts/oci_source_package.ps1`

The script:

- requires branch `stable-15jun`.
- requires a clean working tree.
- creates a `git archive` tarball.
- writes a manifest with commit and SHA-256.
- checks that `.env`, `.git`, `node_modules`, and backup artifacts are not in the archive.

## OCI-21 Stack Retry Runbook

Decision date: 2026-08-21

Goal: keep manual retries of the saved OCI Stack safe while A1 host capacity is unavailable.

Artifact added:

- `docs/deployment/oci-stack-retry-runbook.md`

Key decisions:

- Retry only the saved Stack `sgi-prod-a1-01`.
- Keep shape `VM.Standard.A1.Flex`.
- Keep initial size `1 OCPU / 6 GB`.
- Keep boot volume `80 GB`.
- Keep ephemeral public IPv4, not reserved public IP.
- Do not add ingress rules or paid OCI services during retries.

## OCI-22 Environment Preflight Hardening

Decision date: 2026-08-22

Goal: reduce first-deploy mistakes in the VM-local `.env` before Compose starts.

Change:

- Hardened `scripts/oci_env_preflight.sh`.
- Updated `docs/deployment/oci-first-deploy-runbook.md`.

Additional checks:

- `POSTGRES_PASSWORD` must be URL-safe.
- `DATABASE_URL` must use the configured `POSTGRES_PASSWORD`.
- `ASYNC_DATABASE_URL` must use the configured `POSTGRES_PASSWORD`.
- Both database URLs must target Docker service host `db:5432`.
- `CORS_ORIGINS` must start with `https://`.
- `CORS_ORIGINS` must not point to localhost.

## OCI-23 VM Handoff Template

Decision date: 2026-08-22

Goal: make the first successful VM creation auditable without recording secrets.

Artifact added:

- `docs/deployment/oci-vm-handoff-template.md`

Use it immediately after the saved Stack creates the VM to record:

- instance shape, image, OCPU, memory, and lifecycle state.
- public/private IP facts without creating a reserved IP.
- NSG and subnet attachment.
- cloud-init, Docker, Compose, UFW, and `/opt/sgi-v2` baseline checks.
- cost guardrail confirmations.

## OCI-24 Environment Secret Generator

Decision date: 2026-08-22

Goal: reduce manual `.env` mistakes without committing or storing secrets.

Artifact added:

- `scripts/oci_generate_env_secrets.ps1`

The script prints fresh values for:

- `POSTGRES_PASSWORD`, generated from URL-safe characters.
- `SECRET_KEY`, generated as 32 random bytes in hex.
- `SUPERADMIN_PASSWORD`, generated from URL-safe characters.

Operational rule: generated values are pasted only into the VM-local `.env`; they are not committed, documented, screenshotted, or copied into tickets.

## OCI-25 Cloudflare Tunnel Handoff Template

Decision date: 2026-08-22

Goal: make tunnel setup auditable without storing the tunnel token.

Artifact added:

- `docs/deployment/oci-cloudflare-handoff-template.md`

Use it after Cloudflare setup to record:

- tunnel name and public hostname.
- service target `http://frontend:80`.
- DNS route status.
- VM-local `.env` expectations without token value.
- OCI no-ingress confirmation.
- public smoke checks through Cloudflare.

## OCI-26 VM Baseline Check Script

Decision date: 2026-08-22

Goal: make post-boot VM validation repeatable once A1 capacity is available.

Artifact added:

- `scripts/oci_vm_baseline_check.sh`

The script checks:

- host architecture is ARM64.
- cloud-init status is readable.
- Docker and Docker Compose plugin are installed.
- Docker service is active.
- `/opt/sgi-v2` exists and is owned by `ubuntu`.
- UFW is active with deny incoming and allow outgoing defaults.
- root filesystem is below 80 percent used.
- no pre-deploy app/data TCP listener is present on `80`, `443`, `8000`, `5432`, or `6379`.

## OCI-27 Backup Artifact Check Script

Decision date: 2026-08-22

Goal: validate backup artifacts on Windows before transfer to OCI.

Artifact added:

- `scripts/oci_backup_artifact_check.ps1`

The script checks:

- required backup files are present.
- `database.dump` is non-empty.
- `database.dump.sha256` has a recognized SHA-256 format.
- `database.dump` hash matches the manifest.
- `origin-inventory.json` and `backup-report.json` parse as JSON.
- `database.contents.txt` is non-empty.

## OCI-28 Local Readiness Script

Decision date: 2026-08-22

Goal: aggregate Windows-side checks before retrying the Stack or transferring source.

Artifact added:

- `scripts/oci_local_readiness.ps1`

The script checks:

- branch is `stable-15jun`.
- tracked files are clean.
- `.env`, local env files, backup artifacts, source packages, `node_modules`, private keys, and Terraform state are not tracked.
- OCI Compose preflight passes.
- OCI source package can be generated.

## OCI-29 Capacity Fallback Decision

Decision date: 2026-08-22

Goal: define what to do when A1 capacity is unavailable without drifting into paid or incompatible production resources.

Artifact added:

- `docs/deployment/oci-capacity-fallbacks.md`

Decision:

- Do not create a different production VM shape as a placeholder.
- Keep retrying the saved Stack with `VM.Standard.A1.Flex`.
- Treat resize as acceptable only within A1, for example `1 OCPU / 6 GB` to `2 OCPU / 12 GB`.
- Do not rely on converting an AMD/x86 `VM.Standard.E2.1.Micro` placeholder into the ARM64 A1 production VM.
- A disposable `VM.Standard.E2.1.Micro` lab host is allowed for non-production OCI/cloud-init/Docker/firewall/transfer testing only.

## OCI-30 E2 Micro Lab Runbook

Decision date: 2026-08-22

Goal: permit useful Always Free testing while A1 capacity is unavailable, without confusing lab and production.

Artifact added:

- `docs/deployment/oci-micro-lab-runbook.md`

Rules:

- Use `VM.Standard.E2.1.Micro` only as `sgi-lab-e2micro-01` or similarly explicit lab naming.
- Keep it disposable.
- Use minimum/default boot volume where possible.
- Do not restore production data.
- Do not publish the production hostname.
- Do not use it as the future production boot volume.

## OCI-31 E2 Micro Lab Verification

Decision date: 2026-08-22

Goal: record read-only OCI CLI verification of the temporary lab VM.

Artifacts added:

- `docs/deployment/oci-cloud-init-lab-e2micro.yaml`

Verified:

- Instance `sgi` is `RUNNING`.
- Shape is `VM.Standard.E2.1.Micro`.
- Memory is `1 GB`.
- Public IPv4 is ephemeral.
- Boot volume is `80 GB`.
- NSG has no ingress rules.
- Route table sends `0.0.0.0/0` to Internet Gateway `sgi-prod-ig`.
- No NAT Gateway or Load Balancer was listed.

Findings:

- The subnet default Security List still allows SSH `22` from `0.0.0.0/0`.
- The lab VM was created with the A1 ARM64 cloud-init. On E2 Micro this can break Docker install because the Docker apt source is pinned to `arch=arm64`.
- Use `docs/deployment/oci-cloud-init-lab-e2micro.yaml` for future E2 Micro lab recreation, or manually repair Docker apt architecture on the current lab host.

## OCI-32 E2 Micro Lab Repair Scripts

Decision date: 2026-08-22

Goal: make the current E2 Micro lab host usable after it was created with the A1 ARM64 cloud-init.

Artifacts added:

- `scripts/oci_lab_e2micro_repair.sh`
- `scripts/oci_lab_e2micro_baseline_check.sh`

Use:

- Run the repair script with `sudo` on the lab VM.
- Reconnect SSH so `ubuntu` receives Docker group membership.
- Run the lab baseline as `ubuntu`.

Scope:

- Lab only.
- Does not replace the ARM64 A1 production baseline.
- Does not permit production data restore or production hostname publishing on E2 Micro.

## OCI-33 E2 Micro Lab Baseline Passed

Decision date: 2026-08-22

Goal: record successful repair and baseline validation on the temporary E2 Micro lab VM.

Result:

- Docker apt source was repaired to `arch=amd64`.
- Docker Engine installed successfully.
- Docker Compose plugin installed successfully.
- UFW baseline applied.
- `/opt/sgi-v2` ownership is correct.
- `scripts/oci_lab_e2micro_baseline_check.sh` passed.

Observed:

- Docker `29.7.2`.
- Docker Compose `v5.5.0`.

Remaining guardrails:

- Reconnect SSH before using Docker as `ubuntu`.
- Use this VM for lab validation only.
- Do not restore production data.
- Do not publish the production hostname.

## OCI-34 Source Tree Check Script

Decision date: 2026-08-22

Goal: validate extracted source packages on OCI hosts before any environment or data restore step.

Artifact added:

- `scripts/oci_source_tree_check.sh`

The script checks:

- required deployment files exist.
- `.env`, `.git`, `node_modules`, and backup artifacts are absent.
- source package is not a Git working tree.
- OCI Compose renders with `cloudflared` and without published host ports when Docker is available.

## OCI-35 E2 Micro Source Tree Check Passed

Decision date: 2026-08-22

Goal: record successful source package extraction validation on the temporary E2 Micro lab VM.

Result:

- `scripts/oci_source_tree_check.sh` passed on `/opt/sgi-v2`.
- Required deployment files are present.
- `.env`, `.git`, `node_modules`, and backup artifacts are absent.
- OCI Compose renders without published host ports.

Scope:

- Lab validation only.
- No production data restored.
- No production hostname published.

## OCI-36 E2 Micro Docker Runtime Check Passed

Decision date: 2026-08-22

Goal: record Docker runtime and outbound registry validation on the temporary E2 Micro lab VM.

Result:

- `docker ps` ran as `ubuntu`.
- `docker run --rm hello-world` pulled `hello-world:latest`.
- Docker Hub pull succeeded.
- Container executed successfully.
- Image architecture was `amd64`, matching E2 Micro.

Scope:

- Lab validation only.
- SGI stack was not started.
- No production data restored.
- No production hostname published.
