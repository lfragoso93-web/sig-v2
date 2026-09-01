# OCI certification security gate

Last updated: 2026-08-27

CERT-01B is the local/OCI security certification companion to CERT-01A. It does not authorize real seeds, real portfolio data, or `ready_for_real_data=true`.

## Scope

The gate validates one exact clean `stable-15jun` checkout and runs:

- Gitleaks against the full Git history;
- Trivy filesystem vulnerability, secret and misconfiguration scan, blocking fixed HIGH/CRITICAL findings;
- Hadolint for backend and frontend Dockerfiles with the same explicit ignores used by CI;
- fresh backend and frontend runtime image builds;
- Trivy HIGH/CRITICAL runtime image gates for both images;
- final clean-working-tree check.

The scanner versions are pinned in `scripts/oci_certification_security.sh` so repeated certification does not silently change tools.

## External GitHub inventory

Local CERT-01B does not replace GitHub Advanced Security inventories. Before TEST-GO, reconcile separately:

- CodeQL / Code Scanning open alerts;
- Dependabot Security Alerts;
- Secret Scanning alerts.

The ChatGPT GitHub integration may not have access to those alert endpoints. When unavailable, use authenticated `gh api` on the OCI host or another authorized environment and attach the output to Issue #269.

Recommended inventory commands:

```bash
gh api /repos/lfragoso93-web/sig-v2/code-scanning/alerts?state=open --paginate
gh api /repos/lfragoso93-web/sig-v2/dependabot/alerts?state=open --paginate
gh api /repos/lfragoso93-web/sig-v2/secret-scanning/alerts?state=open --paginate
```

Do not print secret values. Secret-scanning output must be reviewed/redacted before sharing.

## Execution

```bash
cd /opt/sgi-v2
git fetch origin
git switch stable-15jun
git pull --ff-only origin stable-15jun

export SGI_CERT_EXPECTED_SHA="$(git rev-parse HEAD)"
sh scripts/oci_certification_security.sh 2>&1 | tee /tmp/sgi-cert-01b.log
```

Successful local completion ends with:

```text
[oci-cert-security] CERT-01B local security gate passed for <sha>
[oci-cert-security] Reconcile GitHub CodeQL/Code Scanning, Dependabot Security Alerts and Secret Scanning separately before TEST-GO
```

Any Critical/High finding is a blocker until classified for exploitability and either fixed or explicitly justified. Medium/Low findings must be recorded and prioritized, but are not automatically equivalent to an exploitable production blocker.
