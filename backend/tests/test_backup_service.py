"""Testes para backup_service — backup e restore de banco de dados."""
import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
import gzip

from app.services.backup_service import (
    create_database_backup,
    restore_database_backup,
    list_backups,
    delete_backup,
    _parse_db_url,
)


class TestParseDBUrl:

    def test_parse_valid_postgresql_url(self):
        url = "postgresql://user:password@localhost:5432/mydb"
        parsed = _parse_db_url(url)
        
        assert parsed["user"] == "user"
        assert parsed["password"] == "password"
        assert parsed["host"] == "localhost"
        assert parsed["port"] == 5432
        assert parsed["database"] == "mydb"

    def test_parse_postgresql_url_default_port(self):
        url = "postgresql://user:password@localhost/mydb"
        parsed = _parse_db_url(url)
        
        assert parsed["port"] == 5432

    def test_parse_postgresql_url_no_password(self):
        url = "postgresql://user@localhost:5432/mydb"
        parsed = _parse_db_url(url)
        
        assert parsed["user"] == "user"
        assert parsed["password"] == ""

    def test_parse_invalid_url_missing_host(self):
        url = "postgresql://user:password@/mydb"
        
        with pytest.raises(ValueError):
            _parse_db_url(url)

    def test_parse_invalid_url_missing_database(self):
        url = "postgresql://user:password@localhost:5432/"
        
        with pytest.raises(ValueError):
            _parse_db_url(url)


@pytest.mark.asyncio
class TestCreateDatabaseBackup:

    @patch('app.services.backup_service.Path.mkdir')
    @patch('app.services.backup_service.asyncio.create_subprocess_exec')
    @patch('builtins.open', new_callable=mock_open)
    async def test_create_backup_success(self, mock_file, mock_subprocess, mock_mkdir):
        db_url = "postgresql://user:password@localhost/testdb"
        
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"backup data", b""))
        mock_subprocess.return_value = mock_process
        
        with patch('app.services.backup_service.Path.stat') as mock_stat:
            mock_stat_obj = MagicMock()
            mock_stat_obj.st_size = 1024 * 1024
            mock_stat.return_value = mock_stat_obj
            
            with patch('app.services.backup_service.gzip.open', mock_open()):
                result = await create_database_backup(db_url)
        
        assert result["success"] is True
        assert result["backup_id"] is not None
        assert result["filename"] is not None
        assert "size_mb" in result
        assert result["error"] is None

    @patch('app.services.backup_service.Path.mkdir')
    @patch('app.services.backup_service.asyncio.create_subprocess_exec')
    async def test_create_backup_pg_dump_fails(self, mock_subprocess, mock_mkdir):
        db_url = "postgresql://user:password@localhost/testdb"
        
        mock_process = AsyncMock()
        mock_process.returncode = 1
        mock_process.communicate = AsyncMock(return_value=(b"", b"error message"))
        mock_subprocess.return_value = mock_process
        
        result = await create_database_backup(db_url)
        
        assert result["success"] is False
        assert "error" in result
        assert result["error"] is not None

    @patch('app.services.backup_service.Path.mkdir')
    @patch('app.services.backup_service.asyncio.create_subprocess_exec')
    async def test_create_backup_with_custom_name(self, mock_subprocess, mock_mkdir):
        db_url = "postgresql://user:password@localhost/testdb"
        
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"backup data", b""))
        mock_subprocess.return_value = mock_process
        
        with patch('app.services.backup_service.Path.stat') as mock_stat:
            mock_stat_obj = MagicMock()
            mock_stat_obj.st_size = 512 * 1024
            mock_stat.return_value = mock_stat_obj
            
            with patch('app.services.backup_service.gzip.open', mock_open()):
                result = await create_database_backup(db_url, backup_name="my_backup")
        
        assert result["success"] is True
        assert "my_backup" in result["backup_id"]


@pytest.mark.asyncio
class TestRestoreDatabaseBackup:

    @patch('app.services.backup_service.Path.mkdir')
    @patch('app.services.backup_service.Path.exists')
    @patch('app.services.backup_service.asyncio.create_subprocess_exec')
    @patch('builtins.open', new_callable=mock_open)
    async def test_restore_backup_success(self, mock_file, mock_subprocess, mock_exists, mock_mkdir):
        db_url = "postgresql://user:password@localhost/testdb"
        backup_filename = "backup_20240101_120000.sql.gz"
        
        mock_exists.return_value = True
        
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"", b""))
        mock_subprocess.return_value = mock_process
        
        with patch('app.services.backup_service.gzip.open', mock_open()):
            result = await restore_database_backup(db_url, backup_filename)
        
        assert result["success"] is True
        assert "backup_20240101_120000" in result["backup_id"]

    @patch('app.services.backup_service.Path.mkdir')
    @patch('app.services.backup_service.Path.exists')
    async def test_restore_backup_file_not_found(self, mock_exists, mock_mkdir):
        db_url = "postgresql://user:password@localhost/testdb"
        backup_filename = "nonexistent.sql.gz"
        
        mock_exists.return_value = False
        
        result = await restore_database_backup(db_url, backup_filename)
        
        assert result["success"] is False
        assert "not found" in result["error"].lower()

    @patch('app.services.backup_service.Path.mkdir')
    @patch('app.services.backup_service.Path.exists')
    @patch('app.services.backup_service.asyncio.create_subprocess_exec')
    @patch('builtins.open', new_callable=mock_open)
    async def test_restore_backup_psql_fails(self, mock_file, mock_subprocess, mock_exists, mock_mkdir):
        db_url = "postgresql://user:password@localhost/testdb"
        backup_filename = "backup_20240101_120000.sql.gz"
        
        mock_exists.return_value = True
        
        mock_process = AsyncMock()
        mock_process.returncode = 1
        mock_process.communicate = AsyncMock(return_value=(b"", b"restore error"))
        mock_subprocess.return_value = mock_process
        
        with patch('app.services.backup_service.gzip.open', mock_open()):
            result = await restore_database_backup(db_url, backup_filename)
        
        assert result["success"] is False
        assert "psql failed" in result["error"]


@pytest.mark.asyncio
class TestListBackups:

    @patch('app.services.backup_service.Path.mkdir')
    @patch('app.services.backup_service.Path.glob')
    async def test_list_backups_empty(self, mock_glob, mock_mkdir):
        mock_glob.return_value = []
        
        result = await list_backups()
        
        assert result["success"] is True
        assert result["count"] == 0
        assert len(result["backups"]) == 0

    @patch('app.services.backup_service.Path.mkdir')
    @patch('app.services.backup_service.Path.glob')
    async def test_list_backups_with_files(self, mock_glob, mock_mkdir):
        mock_file1 = MagicMock()
        mock_file1.name = "backup_20240101_120000.sql.gz"
        mock_file1.stem = "backup_20240101_120000.sql"
        mock_stat1 = MagicMock()
        mock_stat1.st_size = 1024 * 1024
        mock_stat1.st_mtime = 1704110400
        mock_file1.stat.return_value = mock_stat1
        
        mock_file2 = MagicMock()
        mock_file2.name = "backup_20240102_120000.sql.gz"
        mock_file2.stem = "backup_20240102_120000.sql"
        mock_stat2 = MagicMock()
        mock_stat2.st_size = 2048 * 1024
        mock_stat2.st_mtime = 1704196800
        mock_file2.stat.return_value = mock_stat2
        
        mock_glob.return_value = [mock_file2, mock_file1]
        
        result = await list_backups()
        
        assert result["success"] is True
        assert result["count"] == 2
        assert len(result["backups"]) == 2
        assert result["total_size_mb"] > 0

    @patch('app.services.backup_service.Path.mkdir')
    @patch('app.services.backup_service.Path.glob')
    async def test_list_backups_error(self, mock_glob, mock_mkdir):
        mock_glob.side_effect = Exception("Permission denied")
        
        result = await list_backups()
        
        assert result["success"] is False
        assert result["error"] is not None


@pytest.mark.asyncio
class TestDeleteBackup:

    @patch('app.services.backup_service.Path.mkdir')
    @patch('app.services.backup_service.Path.exists')
    @patch('app.services.backup_service.Path.unlink')
    async def test_delete_backup_success(self, mock_unlink, mock_exists, mock_mkdir):
        backup_filename = "backup_20240101_120000.sql.gz"
        
        mock_exists.return_value = True
        
        result = await delete_backup(backup_filename)
        
        assert result["success"] is True
        assert result["backup_id"] == "backup_20240101_120000"

    @patch('app.services.backup_service.Path.mkdir')
    @patch('app.services.backup_service.Path.exists')
    async def test_delete_backup_file_not_found(self, mock_exists, mock_mkdir):
        backup_filename = "nonexistent.sql.gz"
        
        mock_exists.return_value = False
        
        result = await delete_backup(backup_filename)
        
        assert result["success"] is False
        assert "not found" in result["error"].lower()

    @patch('app.services.backup_service.Path.mkdir')
    @patch('app.services.backup_service.Path.exists')
    @patch('app.services.backup_service.Path.unlink')
    async def test_delete_backup_error(self, mock_unlink, mock_exists, mock_mkdir):
        backup_filename = "backup_20240101_120000.sql.gz"
        
        mock_exists.return_value = True
        mock_unlink.side_effect = Exception("Permission denied")
        
        result = await delete_backup(backup_filename)
        
        assert result["success"] is False
        assert result["error"] is not None
