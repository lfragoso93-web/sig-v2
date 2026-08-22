# OCI E2 Micro Lab Runbook

Use this only if A1 capacity remains unavailable and an Always Free lab host is useful.

## Purpose

Create a disposable `VM.Standard.E2.1.Micro` instance to validate OCI basics while waiting for the real production A1 VM.

This host is not production and must not receive real production data.

## Allowed Shape

- Shape: `VM.Standard.E2.1.Micro`.
- Purpose: lab only.
- Expected cost: `R$ 0.00` if OCI marks the shape/image as Always Free eligible.
- Boot volume: minimum/default size, preferably `47 GB`.
- OS: Ubuntu Always Free eligible image.
- Cloud-init: use `docs/deployment/oci-cloud-init-lab-e2micro.yaml`, not the A1 ARM64 production cloud-init.
- Public IPv4: ephemeral only.
- Reserved public IP: no.
- NSG: preferably a separate lab NSG, or reuse `sgi-prod-vm-nsg` only if no ingress is added.

## What To Test

Safe tests:

- OCI instance creation flow.
- Cloud-init syntax.
- Outbound Internet through the existing VCN route.
- Docker installation.
- UFW baseline.
- `/opt/sgi-v2` directory creation.
- Cloudflare Tunnel connector startup only if memory allows.
- Source package transfer mechanics.

Avoid full-stack validation on this host. With about `1 GB` RAM, PostgreSQL, Redis, backend, frontend build, and `cloudflared` are likely to be unreliable together.

## What Not To Do

- Do not restore production backup artifacts.
- Do not run the full production SGI stack as the target architecture validation.
- Do not publish the production hostname through this VM.
- Do not create reserved public IP, NAT Gateway, Load Balancer, managed DB, managed Redis, or OKE.
- Do not treat this boot volume as the future production boot volume.

## Suggested Name

- Instance name: `sgi-lab-e2micro-01`.

Using a distinct name makes it harder to confuse this lab host with `sgi-prod-a1-01`.

## Post-Create Checks

Run:

```bash
cloud-init status --wait
docker --version
docker compose version
sudo ufw status verbose
ls -ld /opt/sgi-v2
free -h
df -h /
```

For the current lab VM created with the A1 cloud-init, repair Docker first:

```bash
cd /opt/sgi-v2
sudo sh scripts/oci_lab_e2micro_repair.sh
```

Then reconnect SSH and run:

```bash
cd /opt/sgi-v2
sh scripts/oci_lab_e2micro_baseline_check.sh
```

Expected:

- Cloud-init completes.
- Docker and Compose are installed.
- UFW is active with deny incoming.
- Outbound package/download access works.
- Memory is recognized as constrained.

## Current Verification Notes

2026-08-22 read-only OCI CLI verification found:

- Instance `sgi` is `RUNNING`.
- Shape is `VM.Standard.E2.1.Micro`.
- OCPU is `1`.
- Memory is `1 GB`.
- Processor is AMD/x86.
- Public IPv4 is ephemeral.
- Boot volume is `80 GB`.
- NSG has egress-only rules and no ingress.
- The subnet default Security List still allows SSH `22` from `0.0.0.0/0`.
- No NAT Gateway or Load Balancer was listed.

Finding:

- The VM was created with the A1 cloud-init, which hardcodes Docker repository `arch=arm64`.
- On `VM.Standard.E2.1.Micro`, use `docs/deployment/oci-cloud-init-lab-e2micro.yaml` or manually repair the Docker apt source to the host architecture before validating Docker.
- The bundled repair path is `scripts/oci_lab_e2micro_repair.sh`, followed by `scripts/oci_lab_e2micro_baseline_check.sh`.

## Current Repair Result

2026-08-22 manual VM execution completed:

- Docker apt source repaired to `arch=amd64`.
- Docker Engine installed.
- Docker Compose plugin installed.
- Docker service enabled.
- `/opt/sgi-v2` exists and is owned by `ubuntu`.
- `ubuntu` added to the Docker group.
- UFW default incoming set to deny.
- UFW default outgoing set to allow.
- Lab baseline check passed.

Observed versions:

- Docker `29.7.2`.
- Docker Compose `v5.5.0`.

Next lab-safe checks:

- Reconnect SSH so Docker group membership applies.
- Verify `docker ps` as `ubuntu`.
- Test source package transfer mechanics.
- Run `scripts/oci_source_tree_check.sh` after extracting the source package.
- Source tree check passed on 2026-08-22.
- Docker runtime pull test passed on 2026-08-22 with `hello-world:latest`.
- OCI Compose render check passed on 2026-08-22 with no `published:` entries and `cloudflared` present.
- Do not restore production data or publish the production hostname.

## Cleanup

Terminate the lab instance after the tests are complete or after the A1 VM is created.

Before termination:

- Confirm no production data exists on the host.
- Confirm no tunnel token or real `.env` remains on the host.
- Confirm no reserved public IP was created.
