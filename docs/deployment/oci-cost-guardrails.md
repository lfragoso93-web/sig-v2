# SGI v2 OCI Cost Guardrails

Status: active for every OCI retry.

Goal: keep the migration inside the intended Always Free posture.

## Approved Resources

Allowed:

- One `VM.Standard.A1.Flex` instance.
- Initial size `1 OCPU / 6 GB`.
- Later size up to `2 OCPU / 12 GB`, only if still inside A1 free limits.
- No `VM.Standard.E2.1.Micro` production placeholder for later A1 conversion.
- Optional disposable `VM.Standard.E2.1.Micro` lab host only if marked Always Free eligible and kept non-production.
- Boot volume `80 GB`.
- Existing VCN `sgi-vcn-public`.
- Existing subnet `sgi-subnet-public`.
- Internet Gateway `sgi-prod-ig`.
- NSG `sgi-prod-vm-nsg`.
- Ephemeral public IPv4 on the VM VNIC.
- Cloudflare Tunnel running inside Docker.
- Docker volumes on the VM boot volume.

## Forbidden Resources

Do not create:

- Non-A1 compute shape for production SGI.
- NAT Gateway.
- Load Balancer.
- Reserved public IP.
- Managed PostgreSQL.
- Managed Redis.
- Kubernetes or OKE.
- Object Storage bucket unless a separate free-tier review approves it.
- Extra block volume unless a separate storage review approves it.
- Public ingress to PostgreSQL, Redis, backend, frontend, SSH, HTTP, or HTTPS.

Exception:

- Temporary E2 Micro lab SSH `22` may remain open to `0.0.0.0/0` for VS Code Remote access while the host has no production data, no production `.env`, and no production hostname.
- This exception does not apply to the production A1 VM.

## Retry Checklist

Before applying the saved OCI Stack:

- Shape is `VM.Standard.A1.Flex`.
- Production VM is not temporarily switched to `VM.Standard.E2.1.Micro`.
- OCPUs are `1`.
- Memory is `6 GB`.
- Boot volume is `80 GB`.
- Public IP is ephemeral, not reserved.
- VNIC attaches `sgi-prod-vm-nsg`.
- No paid marketplace image.
- No NAT Gateway, Load Balancer, managed DB, Redis, Kubernetes, or reserved IP appears in the plan.

After a successful apply:

- Instance is `RUNNING`.
- Shape remains `VM.Standard.A1.Flex`.
- OCPUs and memory match the approved retry size.
- Boot volume remains `80 GB`.
- VNIC has `sgi-prod-vm-nsg`.
- NSG has no ingress rules.
- Default Security List was not broadened.
- No unexpected new OCI resource appears.

## Billing Watch

After the VM exists, check daily for the first week:

- Cost Analysis shows no unexpected cost.
- Compute shows only the approved A1 instance.
- Networking shows no NAT Gateway and no Load Balancer.
- Public IPs show no reserved public IP.
- Block volumes remain within the planned storage envelope.

NO-GO:

- Any estimated monthly cost appears for a proposed resource.
- OCI suggests replacing A1 with a paid shape.
- A successful apply creates resources outside this document.
