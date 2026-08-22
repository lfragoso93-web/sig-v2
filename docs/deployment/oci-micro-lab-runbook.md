# OCI E2 Micro Lab Runbook

Use this only if A1 capacity remains unavailable and an Always Free lab host is useful.

## Purpose

Create a disposable `VM.Standard.E2.1.Micro` instance to rehearse the production operating model while waiting for the real production A1 VM.

This host should mirror production configuration as closely as the shape allows, but it is not production and must not receive real production data.

Important boundary:

- Operational configuration should be production-like.
- Architecture and performance are not production-like because E2 Micro is AMD/x86 with about `1 GB` RAM, while the final A1 VM is ARM64 with more memory.

## Allowed Shape

- Shape: `VM.Standard.E2.1.Micro`.
- Purpose: lab only.
- Expected cost: `R$ 0.00` if OCI marks the shape/image as Always Free eligible.
- Boot volume: minimum/default size, preferably `47 GB`.
- OS: Ubuntu Always Free eligible image.
- Cloud-init: use `docs/deployment/oci-cloud-init-lab-e2micro.yaml`, not the A1 ARM64 production cloud-init. The lab cloud-init must allow OpenSSH before enabling UFW.
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
- UFW is active with deny incoming and SSH allowed for lab administration.
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
- UFW must allow OpenSSH while this lab host uses VS Code Remote.
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
- Run `scripts/oci_lab_image_pull_check.sh` to validate external image pulls without building SGI.
- Do not restore production data or publish the production hostname.

## SSH Lab Exception

Decision date: 2026-08-22

For the temporary E2 Micro lab VM, SSH `22` may remain reachable from `0.0.0.0/0` because the operator uses dynamic IPs, multiple locations, and VS Code Remote over SSH during validation.

This is a temporary administrative access path while the lab is being configured. Close or restrict SSH after another access path is validated.

Compensating controls:

- Production-like lab only.
- SSH key authentication only.
- No password SSH.
- No production data on the host.
- No production `.env` on the host.
- No production hostname published through this host.
- UFW remains active with default deny incoming and explicit SSH allow.
- Remove or restrict SSH when Cloudflare/Tailscale/another administrative access path is validated.
- Remove or restrict SSH before any production A1 deployment.

This exception does not apply to `sgi-prod-a1-01`.

## Cleanup

Terminate the lab instance after the tests are complete or after the A1 VM is created.

Before termination:

- Confirm no production data exists on the host.
- Confirm no tunnel token or real `.env` remains on the host.
- Confirm no reserved public IP was created.

## SSH Lockout Recovery

If SSH is blocked by UFW and no session remains open, prefer recreating the disposable lab VM with `docs/deployment/oci-cloud-init-lab-e2micro.yaml`.

Reason:

- The lab has no production data.
- OCI security rules can still allow `22`, while UFW inside the OS blocks it.
- Reboot does not clear persistent UFW rules.
- Serial console recovery is possible but slower than recreating this disposable lab.

If a session is still open, recover in place:

```bash
sudo ufw allow OpenSSH
sudo ufw status verbose
```
