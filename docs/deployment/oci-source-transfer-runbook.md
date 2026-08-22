# SGI v2 OCI Source Transfer Runbook

Status: prepared before the VM exists.

Goal: provide a fallback deployment source path if the VM cannot clone the repository directly.

## 1. Preferred Path

Use Git on the VM when possible:

```bash
cd /opt
git clone --branch stable-15jun <repo-url> sgi-v2
cd /opt/sgi-v2
git rev-parse HEAD
```

Expected:

- Branch is `stable-15jun`.
- Commit SHA is recorded in VM-local `.env` as `APP_COMMIT_SHA`.

## 2. Fallback Package From Operator Machine

Create an archive from Git so ignored files stay out of the package:

```powershell
.\scripts\oci_source_package.ps1
```

The script requires a clean `stable-15jun` working tree and writes a `.tar` plus manifest under `artifacts\oci-source-package`.

Expected:

- Package does not include `.env`.
- Package does not include `node_modules`.
- Package does not include `.git`.
- Package does not include backup artifacts.
- Manifest records branch, commit, tracked file count, and SHA-256.

NO-GO:

- Packaging the working tree with untracked secrets.
- Packaging `.env`.
- Packaging OCI Terraform exports with OCIDs.
- Packaging database backup artifacts into the source package.

## 3. Transfer To VM

Transfer target:

```text
/tmp/sgi-v2-source.tar
```

or:

```text
/tmp/sgi-v2-source.tar.gz
```

Use only an approved operator transfer path, such as Cloud Shell file transfer or restricted SSH if explicitly enabled.

Do not open OCI web ingress for source transfer.

## 4. Extract On VM

```bash
sudo rm -rf /opt/sgi-v2
sudo install -d -o ubuntu -g ubuntu -m 0755 /opt/sgi-v2
cd /opt/sgi-v2
tar -xf /tmp/sgi-v2-source.tar
```

If using gzip:

```bash
tar -xzf /tmp/sgi-v2-source.tar.gz -C /opt/sgi-v2
```

Then verify:

```bash
test -f docker-compose.yml
test -f docker-compose.oci.yml
test -f .env.oci.example
test ! -f .env
```

Or run the bundled source tree check:

```bash
cd /opt/sgi-v2
sh scripts/oci_source_tree_check.sh
```

On the E2 Micro lab host, this is the preferred next validation after Docker baseline. It checks the extracted source package without restoring data or publishing the app.

## 5. Continue Deploy

Continue with:

- `docs/deployment/oci-first-deploy-runbook.md`
- `docs/deployment/oci-backup-restore-runbook.md`
- `docs/deployment/oci-cloudflare-tunnel-runbook.md`
