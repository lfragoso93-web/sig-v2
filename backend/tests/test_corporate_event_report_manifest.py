import hashlib
import json

import pytest

from app.services.corporate_event_report_manifest import (
    verify_corporate_event_report_manifest,
)


def _write_artifacts(tmp_path, *, report_payload=None):
    report_payload = report_payload or {
        "schema_version": "corporate-event-reconciliation-dry-run.v2",
        "dry_run": True,
        "database_writes_executed": 0,
    }
    report_file = tmp_path / "report.json"
    report_bytes = (
        json.dumps(report_payload, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n"
    ).encode("utf-8")
    report_file.write_bytes(report_bytes)
    manifest_file = tmp_path / "manifest.json"
    manifest_file.write_text(
        json.dumps(
            {
                "schema_version": "corporate-event-reconciliation-manifest.v1",
                "report_file": str(report_file),
                "report_sha256": hashlib.sha256(report_bytes).hexdigest(),
                "report_schema_version": report_payload["schema_version"],
                "dry_run": report_payload["dry_run"],
                "database_writes_executed": report_payload[
                    "database_writes_executed"
                ],
                "dataset_id": "fixture-amob3-2025",
                "window_start": None,
                "window_end": None,
                "source_commit_sha": None,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return report_file, manifest_file


def test_manifest_verification_accepts_untampered_dry_run(tmp_path) -> None:
    report_file, manifest_file = _write_artifacts(tmp_path)

    result = verify_corporate_event_report_manifest(report_file, manifest_file)

    assert result["valid"] is True
    assert result["database_writes_executed"] == 0


def test_manifest_verification_rejects_tampered_report(tmp_path) -> None:
    report_file, manifest_file = _write_artifacts(tmp_path)
    report_file.write_text(
        report_file.read_text(encoding="utf-8").replace('"dry_run": true', '"dry_run": false'),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="SHA-256"):
        verify_corporate_event_report_manifest(report_file, manifest_file)


def test_manifest_verification_rejects_non_read_only_report(tmp_path) -> None:
    report_file, manifest_file = _write_artifacts(
        tmp_path,
        report_payload={
            "schema_version": "corporate-event-reconciliation-dry-run.v2",
            "dry_run": True,
            "database_writes_executed": 1,
        },
    )

    with pytest.raises(ValueError, match="escritas no banco"):
        verify_corporate_event_report_manifest(report_file, manifest_file)


def test_manifest_verification_rejects_inverted_window(tmp_path) -> None:
    report_file, manifest_file = _write_artifacts(tmp_path)
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    manifest["window_start"] = "2025-02-01"
    manifest["window_end"] = "2025-01-01"
    manifest_file.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="janela do manifesto esta invertida"):
        verify_corporate_event_report_manifest(report_file, manifest_file)


def test_manifest_verification_rejects_invalid_source_sha(tmp_path) -> None:
    report_file, manifest_file = _write_artifacts(tmp_path)
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    manifest["source_commit_sha"] = "short"
    manifest_file.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="source_commit_sha invalido"):
        verify_corporate_event_report_manifest(report_file, manifest_file)
