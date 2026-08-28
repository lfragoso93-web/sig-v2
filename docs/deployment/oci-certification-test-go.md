# OCI CERT-03 — TEST-GO decision

Last updated: 2026-08-27

CERT-03 is the final certification gate for integrated testing with fictitious/disposable data. It does not authorize real data.

## Preconditions

CERT-01A, CERT-01B and CERT-02 must already be approved and recorded in Issue #227.

## What CERT-03 does

The gate intentionally reuses existing canonical wrappers instead of duplicating bootstrap logic:

1. `scripts/oci_seed_contract_validation.sh` — revalidates `system-bootstrap.v4`, admin surface and all seed/bootstrap contracts without executing real seeds;
2. `scripts/oci_lab_disposable_http_smoke.sh` — revalidates the disposable HTTP journey and requires `/ready` to stay closed with `ready_for_real_data=false`;
3. requires `stable-15jun`, exact optional SHA and clean working tree before and after execution;
4. emits an explicit `TEST-GO-DISPOSABLE:PASS` only when both canonical gates pass.

Successful CERT-03 means the SGI v2 is cleared for integrated testing with fictitious/disposable data. It does **not** authorize real users, real portfolios, CSV imports, real market seeds, real snapshots or promotion of `ready_for_real_data`.

## Execution

```bash
cd /opt/sgi-v2
git fetch origin
git switch stable-15jun
git pull --ff-only origin stable-15jun

export SGI_CERT_EXPECTED_SHA="$(git rev-parse HEAD)"
sh scripts/oci_certification_test_go.sh 2>&1 | tee /tmp/sgi-cert-03.log
```

Expected ending:

```text
TEST-GO-DISPOSABLE:PASS sha=<sha>
REAL-DATA-GATE:CLOSED
[oci-cert-test-go] CERT-03 passed: SGI v2 is cleared for integrated testing with fictitious/disposable data only
```

After approval, the next macroblock is the real-data chain governed by #226 -> #216 -> #158. No step in that chain may be inferred from CERT-03 alone.
