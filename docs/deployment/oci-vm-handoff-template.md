# OCI VM Handoff Template

Fill this immediately after the saved Stack creates the VM successfully.

Do not add secrets, tunnel tokens, private keys, passwords, or full backup contents to this file.

## Instance

- Instance name:
- Lifecycle state:
- Region: `sa-saopaulo-1`
- Availability domain:
- Fault domain:
- Shape:
- OCPU:
- Memory:
- Image:
- Created at:

## Network

- VCN: `sgi-vcn-public`
- Subnet: `sgi-subnet-public`
- NSG: `sgi-prod-vm-nsg`
- Public IPv4:
- Public IPv4 type: ephemeral
- Private IPv4:
- Ingress rules added: none expected

## Storage

- Boot volume size:
- Boot volume performance:
- Extra block volumes: none expected

## Cloud-Init

Record only status and non-secret output.

```bash
cloud-init status --wait
cloud-init status --long
docker --version
docker compose version
sudo ufw status verbose
ls -ld /opt/sgi-v2
```

Expected:

- Cloud-init completed.
- Docker is installed.
- Docker Compose plugin is installed.
- UFW default incoming is deny.
- UFW default outgoing is allow.
- `/opt/sgi-v2` exists and is owned by `ubuntu`.

## Cost Guardrail

- Estimated cost at creation:
- Shape remained `VM.Standard.A1.Flex`: yes/no
- Reserved public IP created: no expected
- NAT Gateway created: no expected
- Load Balancer created: no expected
- Managed database/Redis/Kubernetes created: no expected

## Next Phase

After filling this template, continue with:

- `docs/deployment/oci-execution-index.md` Phase 2.
- `docs/deployment/oci-first-deploy-runbook.md`.

