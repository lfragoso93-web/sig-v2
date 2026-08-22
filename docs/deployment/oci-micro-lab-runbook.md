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

Expected:

- Cloud-init completes.
- Docker and Compose are installed.
- UFW is active with deny incoming.
- Outbound package/download access works.
- Memory is recognized as constrained.

## Cleanup

Terminate the lab instance after the tests are complete or after the A1 VM is created.

Before termination:

- Confirm no production data exists on the host.
- Confirm no tunnel token or real `.env` remains on the host.
- Confirm no reserved public IP was created.

