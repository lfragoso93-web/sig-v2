from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.cli.ensure_predeploy_backup_root import ensure_predeploy_backup_root


def test_initializer_assigns_only_the_dedicated_root_to_app_user(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    parent = tmp_path / "artifacts"
    parent.mkdir()
    ownership_changes: list[tuple[Path, int, int]] = []

    def record_chown(path: str | os.PathLike[str], uid: int, gid: int) -> None:
        ownership_changes.append((Path(path), uid, gid))

    monkeypatch.setattr(
        "app.cli.ensure_predeploy_backup_root.os.chown", record_chown
    )

    root = ensure_predeploy_backup_root(parent)

    assert root == parent / "oci-predeploy-backups"
    assert root.is_dir()
    assert root.stat().st_mode & 0o700 == 0o700
    assert ownership_changes == [(root, 1000, 1000)]
    assert list(parent.iterdir()) == [root]


def test_initializer_rejects_symlink_artifact_mount_without_creating_backup_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real_parent = tmp_path / "real-artifacts"
    real_parent.mkdir()
    parent = tmp_path / "artifacts"
    try:
        parent.symlink_to(real_parent, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"symlinks unavailable: {exc}")

    monkeypatch.setattr(
        "app.cli.ensure_predeploy_backup_root.os.chown",
        lambda *_args: pytest.fail("must not change ownership through a symlink"),
    )

    with pytest.raises(RuntimeError, match="artifact mount"):
        ensure_predeploy_backup_root(parent)

    assert not (real_parent / "oci-predeploy-backups").exists()


def test_initializer_rejects_symlink_backup_root_without_chowning_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    parent = tmp_path / "artifacts"
    parent.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "keep.txt").write_text("preserve", encoding="utf-8")
    root = parent / "oci-predeploy-backups"
    try:
        root.symlink_to(outside, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"symlinks unavailable: {exc}")

    monkeypatch.setattr(
        "app.cli.ensure_predeploy_backup_root.os.chown",
        lambda *_args: pytest.fail("must not change ownership through a symlink"),
    )

    with pytest.raises(RuntimeError, match="regular directory"):
        ensure_predeploy_backup_root(parent)

    assert (outside / "keep.txt").read_text(encoding="utf-8") == "preserve"
