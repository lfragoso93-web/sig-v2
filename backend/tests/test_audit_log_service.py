"""Testes para audit_log_service — rastreamento de operacoes de usuarios."""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.audit_log_service import AuditLogService
from app.models.audit_log import AuditLog


class TestCalculateChanges:

    def test_no_changes(self):
        old = {"name": "John", "age": 30}
        new = {"name": "John", "age": 30}
        changes = AuditLogService._calculate_changes(old, new)
        assert changes is None

    def test_single_field_changed(self):
        old = {"name": "John", "age": 30}
        new = {"name": "Jane", "age": 30}
        changes = AuditLogService._calculate_changes(old, new)
        assert changes["name"]["old"] == "John"
        assert changes["name"]["new"] == "Jane"
        assert "age" not in changes

    def test_multiple_fields_changed(self):
        old = {"name": "John", "age": 30, "email": "john@example.com"}
        new = {"name": "Jane", "age": 31, "email": "jane@example.com"}
        changes = AuditLogService._calculate_changes(old, new)
        assert "name" in changes
        assert "age" in changes
        assert "email" in changes

    def test_field_added(self):
        old = {"name": "John"}
        new = {"name": "John", "age": 30}
        changes = AuditLogService._calculate_changes(old, new)
        assert changes["age"]["old"] is None
        assert changes["age"]["new"] == 30

    def test_field_removed(self):
        old = {"name": "John", "age": 30}
        new = {"name": "John"}
        changes = AuditLogService._calculate_changes(old, new)
        assert changes["age"]["old"] == 30
        assert changes["age"]["new"] is None

    def test_empty_dicts(self):
        changes = AuditLogService._calculate_changes({}, {})
        assert changes is None


@pytest.mark.asyncio
class TestLogAction:

    async def test_log_action_basic(self):
        db = AsyncMock(spec=AsyncSession)
        db.flush = AsyncMock()

        log = await AuditLogService.log_action(
            db=db,
            user_id=1,
            action="CREATE",
            resource_type="TRANSACTION",
            resource_id=100,
        )

        assert log.user_id == 1
        assert log.action == "CREATE"
        assert log.resource_type == "TRANSACTION"
        assert log.resource_id == 100
        assert log.status == "SUCCESS"
        db.add.assert_called_once()
        db.flush.assert_called_once()

    async def test_log_action_with_values(self):
        db = AsyncMock(spec=AsyncSession)
        db.flush = AsyncMock()

        old_values = {"price": 100.0}
        new_values = {"price": 110.0}

        log = await AuditLogService.log_action(
            db=db,
            user_id=1,
            action="UPDATE",
            resource_type="ASSET",
            old_values=old_values,
            new_values=new_values,
        )

        assert log.old_values == old_values
        assert log.new_values == new_values
        assert log.changes is not None
        assert log.changes["price"]["old"] == 100.0
        assert log.changes["price"]["new"] == 110.0

    async def test_log_action_with_ip_and_user_agent(self):
        db = AsyncMock(spec=AsyncSession)
        db.flush = AsyncMock()

        log = await AuditLogService.log_action(
            db=db,
            user_id=1,
            action="LOGIN",
            resource_type="USER",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )

        assert log.ip_address == "192.168.1.1"
        assert log.user_agent == "Mozilla/5.0"

    async def test_log_action_failure(self):
        db = AsyncMock(spec=AsyncSession)
        db.flush = AsyncMock()

        log = await AuditLogService.log_action(
            db=db,
            user_id=1,
            action="DELETE",
            resource_type="TRANSACTION",
            status="FAILED",
            error_message="Transaction not found",
        )

        assert log.status == "FAILED"
        assert log.error_message == "Transaction not found"

    async def test_log_action_db_error(self):
        db = AsyncMock(spec=AsyncSession)
        db.flush = AsyncMock(side_effect=Exception("DB Error"))

        with pytest.raises(Exception):
            await AuditLogService.log_action(
                db=db,
                user_id=1,
                action="CREATE",
                resource_type="TRANSACTION",
            )


@pytest.mark.asyncio
class TestGetAuditLogs:

    async def test_get_all_logs(self):
        db = AsyncMock(spec=AsyncSession)
        
        mock_log = MagicMock(spec=AuditLog)
        mock_log.user_id = 1
        
        execute_result = MagicMock()
        execute_result.scalar_one = MagicMock(return_value=1)
        execute_result.unique = MagicMock(return_value=execute_result)
        execute_result.scalars = MagicMock(return_value=execute_result)
        execute_result.all = MagicMock(return_value=[mock_log])
        
        db.execute = AsyncMock(return_value=execute_result)

        logs, count = await AuditLogService.get_audit_logs(db)

        assert len(logs) == 1
        assert count == 1

    async def test_get_logs_filter_by_user(self):
        db = AsyncMock(spec=AsyncSession)
        
        execute_result = MagicMock()
        execute_result.scalar_one = MagicMock(return_value=1)
        execute_result.unique = MagicMock(return_value=execute_result)
        execute_result.scalars = MagicMock(return_value=execute_result)
        execute_result.all = MagicMock(return_value=[])
        
        db.execute = AsyncMock(return_value=execute_result)

        logs, count = await AuditLogService.get_audit_logs(db, user_id=42)

        assert count == 1

    async def test_get_logs_filter_by_resource_type(self):
        db = AsyncMock(spec=AsyncSession)
        
        execute_result = MagicMock()
        execute_result.scalar_one = MagicMock(return_value=5)
        execute_result.unique = MagicMock(return_value=execute_result)
        execute_result.scalars = MagicMock(return_value=execute_result)
        execute_result.all = MagicMock(return_value=[])
        
        db.execute = AsyncMock(return_value=execute_result)

        logs, count = await AuditLogService.get_audit_logs(db, resource_type="TRANSACTION")

        assert count == 5

    async def test_get_logs_filter_by_action(self):
        db = AsyncMock(spec=AsyncSession)
        
        execute_result = MagicMock()
        execute_result.scalar_one = MagicMock(return_value=3)
        execute_result.unique = MagicMock(return_value=execute_result)
        execute_result.scalars = MagicMock(return_value=execute_result)
        execute_result.all = MagicMock(return_value=[])
        
        db.execute = AsyncMock(return_value=execute_result)

        logs, count = await AuditLogService.get_audit_logs(db, action="CREATE")

        assert count == 3

    async def test_get_logs_filter_by_portfolio(self):
        db = AsyncMock(spec=AsyncSession)
        
        execute_result = MagicMock()
        execute_result.scalar_one = MagicMock(return_value=2)
        execute_result.unique = MagicMock(return_value=execute_result)
        execute_result.scalars = MagicMock(return_value=execute_result)
        execute_result.all = MagicMock(return_value=[])
        
        db.execute = AsyncMock(return_value=execute_result)

        logs, count = await AuditLogService.get_audit_logs(db, portfolio_id=99)

        assert count == 2

    async def test_get_logs_filter_by_status(self):
        db = AsyncMock(spec=AsyncSession)
        
        execute_result = MagicMock()
        execute_result.scalar_one = MagicMock(return_value=1)
        execute_result.unique = MagicMock(return_value=execute_result)
        execute_result.scalars = MagicMock(return_value=execute_result)
        execute_result.all = MagicMock(return_value=[])
        
        db.execute = AsyncMock(return_value=execute_result)

        logs, count = await AuditLogService.get_audit_logs(db, status="FAILED")

        assert count == 1

    async def test_get_logs_pagination(self):
        db = AsyncMock(spec=AsyncSession)
        
        execute_result = MagicMock()
        execute_result.scalar_one = MagicMock(return_value=100)
        execute_result.unique = MagicMock(return_value=execute_result)
        execute_result.scalars = MagicMock(return_value=execute_result)
        execute_result.all = MagicMock(return_value=[])
        
        db.execute = AsyncMock(return_value=execute_result)

        logs, count = await AuditLogService.get_audit_logs(db, page=2, page_size=20)

        assert count == 100


@pytest.mark.asyncio
class TestGetSpecificAuditLogs:

    async def test_get_user_audit_logs(self):
        db = AsyncMock(spec=AsyncSession)
        
        execute_result = MagicMock()
        execute_result.scalar_one = MagicMock(return_value=5)
        execute_result.unique = MagicMock(return_value=execute_result)
        execute_result.scalars = MagicMock(return_value=execute_result)
        execute_result.all = MagicMock(return_value=[])
        
        db.execute = AsyncMock(return_value=execute_result)

        logs, count = await AuditLogService.get_user_audit_logs(db, user_id=42)

        assert count == 5

    async def test_get_portfolio_audit_logs(self):
        db = AsyncMock(spec=AsyncSession)
        
        execute_result = MagicMock()
        execute_result.scalar_one = MagicMock(return_value=3)
        execute_result.unique = MagicMock(return_value=execute_result)
        execute_result.scalars = MagicMock(return_value=execute_result)
        execute_result.all = MagicMock(return_value=[])
        
        db.execute = AsyncMock(return_value=execute_result)

        logs, count = await AuditLogService.get_portfolio_audit_logs(db, portfolio_id=99)

        assert count == 3

    async def test_get_audit_log_by_id(self):
        db = AsyncMock(spec=AsyncSession)
        
        mock_log = MagicMock(spec=AuditLog)
        mock_log.id = 123
        
        execute_result = MagicMock()
        execute_result.scalar_one_or_none = MagicMock(return_value=mock_log)
        
        db.execute = AsyncMock(return_value=execute_result)

        log = await AuditLogService.get_audit_log_by_id(db, 123)

        assert log is not None
        assert log.id == 123


@pytest.mark.asyncio
class TestAuditStats:

    async def test_get_audit_stats(self):
        db = AsyncMock(spec=AsyncSession)
        
        execute_result = MagicMock()
        execute_result.scalar_one = MagicMock(return_value=100)
        execute_result.all = MagicMock(return_value=[("CREATE", 50), ("UPDATE", 30), ("DELETE", 20)])
        
        db.execute = AsyncMock(return_value=execute_result)

        stats = await AuditLogService.get_audit_stats(db)

        assert stats.total_logs == 100
        assert stats.failed_operations == 100

    async def test_get_user_audit_stats(self):
        db = AsyncMock(spec=AsyncSession)
        
        execute_result = MagicMock()
        execute_result.scalar_one = MagicMock(return_value=25)
        execute_result.scalar_one_or_none = MagicMock(return_value=datetime.now(timezone.utc))
        execute_result.all = MagicMock(return_value=[("CREATE", 15), ("UPDATE", 10)])
        
        db.execute = AsyncMock(return_value=execute_result)

        stats = await AuditLogService.get_user_audit_stats(db, user_id=42)

        assert stats.user_id == 42
        assert stats.total_actions == 25


@pytest.mark.asyncio
class TestCleanupAuditLogs:

    async def test_cleanup_dry_run(self):
        db = AsyncMock(spec=AsyncSession)
        
        execute_result = MagicMock()
        execute_result.scalar_one = MagicMock(return_value=50)
        
        db.execute = AsyncMock(return_value=execute_result)

        result = await AuditLogService.cleanup_audit_logs(db, days_to_keep=90, dry_run=True)

        assert result.deleted_count == 50

    async def test_cleanup_actual(self):
        db = AsyncMock(spec=AsyncSession)
        
        execute_result = MagicMock()
        execute_result.scalar_one = MagicMock(return_value=30)
        
        db.execute = AsyncMock(return_value=execute_result)
        db.commit = AsyncMock()

        result = await AuditLogService.cleanup_audit_logs(db, days_to_keep=90, dry_run=False)

        assert result.deleted_count == 30

    async def test_cleanup_no_logs_to_delete(self):
        db = AsyncMock(spec=AsyncSession)
        
        execute_result = MagicMock()
        execute_result.scalar_one = MagicMock(return_value=0)
        
        db.execute = AsyncMock(return_value=execute_result)

        result = await AuditLogService.cleanup_audit_logs(db, dry_run=False)

        assert result.deleted_count == 0
