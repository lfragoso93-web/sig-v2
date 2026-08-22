# OCI Capacity Fallbacks

Use this when `VM.Standard.A1.Flex` returns insufficient host capacity.

## Short Answer

Do not create a different production VM shape as a placeholder for SGI v2.

Keep retrying the saved Stack with `VM.Standard.A1.Flex`.

## Why Not Use Another Shape Temporarily

OCI Always Free compute options include:

- `VM.Standard.A1.Flex`, Arm/Ampere, Always Free within the account limits.
- `VM.Standard.E2.1.Micro`, AMD/x86, Always Free, very small memory profile.

The SGI v2 production plan is built for Docker on A1 ARM64 with enough memory for frontend, backend, PostgreSQL, Redis, and `cloudflared`.

`VM.Standard.E2.1.Micro` is not a safe production placeholder because:

- it has about `1 GB` memory.
- it is AMD/x86, while the target production host is ARM64.
- it is unlikely to run the full SGI Docker stack reliably.
- treating it as temporary production increases migration drift.

## Can We Resize Later?

OCI supports changing instance shape in some cases, but do not rely on changing an AMD/x86 micro instance into the ARM64 A1 production VM.

For this migration, consider shape change safe only within the same intended family:

- from `VM.Standard.A1.Flex 1 OCPU / 6 GB`;
- to `VM.Standard.A1.Flex 2 OCPU / 12 GB`.

Do not plan production around:

- creating an AMD/x86 micro VM now;
- later converting that boot volume into the ARM64 A1 production VM.

## Acceptable Fallbacks While Waiting

Safe options:

- Keep the saved Stack `sgi-prod-a1-01` and retry later.
- Retry with no explicit fault domain selection.
- Keep `VM.Standard.A1.Flex`.
- Keep initial `1 OCPU / 6 GB`.
- Keep boot volume `80 GB`.
- Continue local readiness, backup, package, Cloudflare, and runbook preparation.

Optional non-production use only:

- A `VM.Standard.E2.1.Micro` can be used only for tiny connectivity or OCI Console experiments if it is clearly disposable.
- Do not restore production data onto it.
- Do not publish SGI production through it.
- Do not treat it as the future production host.

## NO-GO

- Non-A1 production shape.
- Paid flexible AMD/Intel shape.
- Larger shape with estimated cost above `R$ 0.00`.
- Any reserved public IP, NAT Gateway, Load Balancer, managed DB, managed Redis, or OKE workaround.
- Restoring production data onto a disposable test host.

