"""Prepare the isolated OCI pre-deploy backup directory for the app user."""

from __future__ import annotations

import os
from pathlib import Path

BACKUP_DIRECTORY_NAME = "oci-predeploy-backups"
ARTIFACT_PARENT = Path("/app/artifacts")
APP_UID = 1000
APP_GID = 1000


def ensure_predeploy_backup_root(parent: Path = ARTIFACT_PARENT) -> Path:
    """Create and grant the app user access to only the dedicated backup root."""

    if (
        not parent.is_absolute()
        or parent.is_symlink()
        or not parent.is_dir()
        or parent.resolve(strict=True) != parent
    ):
        raise RuntimeError("artifact mount is not the expected directory")

    root = parent / BACKUP_DIRECTORY_NAME
    if root.is_symlink() or (root.exists() and not root.is_dir()):
        raise RuntimeError("pre-deploy backup path is not a regular directory")

    root.mkdir(mode=0o700, exist_ok=True)
    if root.is_symlink() or root.resolve(strict=True) != root:
        raise RuntimeError(
            "pre-deploy backup path resolves outside its dedicated root"
        )

    os.chown(root, APP_UID, APP_GID)
    root.chmod(root.stat().st_mode | 0o700)
    return root


def main() -> None:
    try:
        root = ensure_predeploy_backup_root()
    except (OSError, RuntimeError) as exc:
        raise SystemExit(str(exc)) from exc
    print(f"Prepared dedicated pre-deploy backup directory: {root}")


if __name__ == "__main__":
    main()
