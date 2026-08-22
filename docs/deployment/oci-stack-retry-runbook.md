# OCI Stack Retry Runbook

Use this when retrying the saved OCI Stack while `VM.Standard.A1.Flex` capacity is unavailable.

## Current Stack

- Stack name: `sgi-prod-a1-01`.
- Region: `sa-saopaulo-1`.
- Purpose: create the first SGI production A1 VM from the safe Console configuration.
- Expected cost posture: `R$ 0.00`.

## Retry Window

OCI A1 capacity is opportunistic on free accounts. Retry manually at different times of day, especially early morning or late evening local time.

Do not make multiple conflicting stacks. Keep using the saved Stack so the configuration remains auditable.

## Allowed Retry Changes

You may retry with:

- Shape still `VM.Standard.A1.Flex`.
- Initial size `1 OCPU / 6 GB`.
- Boot volume `80 GB`.
- Same VCN `sgi-vcn-public`.
- Same subnet `sgi-subnet-public`.
- Same NSG `sgi-prod-vm-nsg`.
- Ephemeral public IPv4 enabled.
- No explicit fault domain selection if OCI suggests that capacity may improve.

If OCI later allows it, scale only after the first deployment is stable and still inside the Always Free A1 envelope.

## Forbidden Changes

Do not approve:

- Non-A1 compute shape.
- More than the Always Free A1 envelope.
- Reserved public IP.
- NAT Gateway.
- Load Balancer.
- Managed database.
- Managed Redis.
- Kubernetes/OKE.
- Public ingress for `22`, `80`, `443`, `5432`, `6379`, or `8000`.
- Any estimated monthly cost above `R$ 0.00`.

## Before Clicking Apply

Confirm:

- Estimated cost is `R$ 0.00`.
- Shape is `VM.Standard.A1.Flex`.
- OCPU/memory are `1 / 6 GB`.
- Boot volume is `80 GB`.
- VNIC uses `sgi-prod-vm-nsg`.
- Cloud-init is still the baseline from `docs/deployment/oci-cloud-init.yaml`.
- No ingress rules are being added.

## After A Successful Apply

Record:

- Instance name.
- Public IPv4.
- Private IPv4.
- Shape.
- OCPU and memory.
- Boot volume size.
- Whether cloud-init completed.

Then continue with `docs/deployment/oci-execution-index.md` Phase 2.

## If Apply Fails Again

If the error is still insufficient A1 capacity:

- Keep the Stack saved.
- Do not change to a paid shape.
- Retry later.
- Continue preparing source, environment, backup, and Cloudflare artifacts locally.

