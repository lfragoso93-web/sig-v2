"""Destructive admin backup/restore rehearsal against two disposable databases.

Run only from an isolated backend container with DATABASE_URL pointing at the
disposable API/source database. The restore endpoint is directed to a separate
empty disposable target to exercise the HTTP flow without overwriting its own
API/audit database or any operational volume.
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.database import AsyncSessionLocal, get_db
from app.core.security import create_access_token, hash_password
from app.models.user import User, UserRole
from app.routers import admin
from app.services import backup_service

SUPERADMIN_PASSWORD = "Issue83-Disposable-Only-9x!"
PROBE_KEY = f"issue83_http_restore_probe_{uuid4().hex}"
PROBE_VALUE = "restored-from-disposable-source"


def _async_url(url: str) -> str:
    if url.startswith("postgresql+psycopg2://"):
        return url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


async def _seed_source() -> int:
    async with AsyncSessionLocal() as session:
        user = User(
            name="Issue 83 Disposable Superadmin",
            email=f"issue83-superadmin-{uuid4().hex}@disposable.invalid",
            hashed_password=hash_password(SUPERADMIN_PASSWORD),
            role=UserRole.superadmin,
            is_active=True,
        )
        session.add(user)
        await session.flush()
        user_id = user.id
        await session.execute(
            text(
                "CREATE TABLE IF NOT EXISTS issue83_restore_probe "
                "(probe_key text PRIMARY KEY, probe_value text NOT NULL)"
            )
        )
        await session.execute(
            text(
                "INSERT INTO issue83_restore_probe VALUES (:key, :value) "
                "ON CONFLICT (probe_key) DO UPDATE SET probe_value = EXCLUDED.probe_value"
            ),
            {"key": PROBE_KEY, "value": PROBE_VALUE},
        )
        await session.commit()
        return user_id


async def _probe(url: str) -> str | None:
    engine = create_async_engine(_async_url(url))
    try:
        async with engine.connect() as connection:
            value = await connection.scalar(
                text(
                    "SELECT probe_value FROM issue83_restore_probe "
                    "WHERE probe_key = :key"
                ),
                {"key": PROBE_KEY},
            )
            return str(value) if value is not None else None
    finally:
        await engine.dispose()


async def _audit_actions() -> list[str]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text(
                "SELECT action FROM audit_logs "
                "WHERE resource_type = 'DatabaseBackup' ORDER BY id"
            )
        )
        return [str(value) for value in result.scalars().all()]


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(admin.router, prefix="/api/v1/admin")

    async def source_db_dependency():
        async with AsyncSessionLocal() as session:
            yield session
            await session.commit()

    app.dependency_overrides[get_db] = source_db_dependency
    return app


def run() -> dict[str, Any]:
    source_url = os.environ["DATABASE_URL"]
    target_url = os.environ["ISSUE83_EMPTY_TARGET_DATABASE_URL"]
    backup_dir = Path("/tmp/issue83-http-backups")
    shutil.rmtree(backup_dir, ignore_errors=True)
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_service.BACKUPS_DIR = backup_dir

    app = _build_app()
    with TestClient(app) as client:
        # Use TestClient's ASGI loop for all async database access so the engine
        # pool is never moved across event loops.
        user_id = client.portal.call(_seed_source)
        token = create_access_token(str(user_id))
        headers = {
            "Authorization": f"Bearer {token}",
            "user-agent": "issue83-e2e",
        }

        # Real SuperAdmin authentication, request auditing, pg_dump, and
        # persisted operation status run against the disposable source database.
        backup_response = client.post(
            "/api/v1/admin/database/backup", headers=headers
        )
        assert backup_response.status_code == 202, backup_response.text
        backup_payload = backup_response.json()
        backup_operation_id = backup_payload["operation_id"]
        operations = client.get(
            "/api/v1/admin/database/operations", headers=headers
        )
        assert operations.status_code == 200, operations.text
        backup_operation = next(
            row for row in operations.json()["operations"]
            if row["id"] == backup_operation_id
        )
        assert backup_operation["status"] == "succeeded", backup_operation
        backup_filename = client.get(
            "/api/v1/admin/database/backups", headers=headers
        ).json()["backups"][0]["filename"]
        download = client.get(
            f"/api/v1/admin/database/backups/{backup_filename}", headers=headers
        )
        assert download.status_code == 200, download.text
        assert download.content[:2] == b"\x1f\x8b", "backup response is not gzip"

        # The API still authenticates, writes its audit/status records to the
        # source, and calls the real restore service; only the destructive
        # target URL is isolated to the separate empty disposable database.
        original_getenv = os.getenv

        def restore_target_getenv(
            name: str, default: str | None = None
        ) -> str | None:
            if name == "DATABASE_URL":
                return target_url
            return original_getenv(name, default)

        os.getenv = restore_target_getenv  # type: ignore[assignment]
        try:
            restore_response = client.post(
                "/api/v1/admin/database/restore",
                headers=headers,
                json={
                    "backup_filename": backup_filename,
                    "current_password": SUPERADMIN_PASSWORD,
                },
            )
        finally:
            os.getenv = original_getenv  # type: ignore[assignment]
        assert restore_response.status_code == 202, restore_response.text
        restore_operation_id = restore_response.json()["operation_id"]

        operations_after = client.get(
            "/api/v1/admin/database/operations", headers=headers
        )
        assert operations_after.status_code == 200, operations_after.text
        operation_by_id = {
            row["id"]: row for row in operations_after.json()["operations"]
        }
        assert operation_by_id[restore_operation_id]["status"] == "succeeded"
        source_probe = client.portal.call(_probe, source_url)
        target_probe = client.portal.call(_probe, target_url)
        assert source_probe == PROBE_VALUE
        assert target_probe == PROBE_VALUE

        audits = client.portal.call(_audit_actions)
        assert audits.count("BACKUP") == 1
        assert audits.count("RESTORE") == 1

        result = {
            "schema_version": "admin-backup-restore-http-rehearsal.v1",
            "result": "PASS",
            "database_writes": "two disposable PostgreSQL databases only",
            "real_superadmin_bearer_auth": "passed",
            "backup_http_status": backup_response.status_code,
            "backup_operation_status": backup_operation["status"],
            "authenticated_download_http_status": download.status_code,
            "restore_http_status": restore_response.status_code,
            "restore_operation_status": operation_by_id[restore_operation_id]["status"],
            "audit_actions": audits,
            "source_integrity_probe_unchanged": source_probe == PROBE_VALUE,
            "empty_target_integrity_probe_restored": target_probe == PROBE_VALUE,
            "source_database": "disposable API/auth/audit/status database",
            "restore_target": "separate empty disposable PostgreSQL database",
            "limitation": (
                "restore target is deliberately separated from the API database "
                "so the route-level destructive operation cannot replace its own "
                "auth, audit, or status store; production same-database status "
                "loss remains an acknowledged feature limitation"
            ),
        }
        evidence_path = os.environ.get("ISSUE83_EVIDENCE_PATH")
        if evidence_path:
            Path(evidence_path).write_text(
                json.dumps(result, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        return result


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
