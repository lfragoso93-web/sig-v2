import subprocess
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import gzip
import shutil
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

BACKUPS_DIR = Path("/tmp/db_backups")


def _ensure_backups_dir():
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)


class BackupError(Exception):
    pass


class RestoreError(Exception):
    pass


async def create_database_backup(
    db_url: str,
    backup_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Creates a PostgreSQL database backup using pg_dump.
    
    Args:
        db_url: Database connection URL (e.g., postgresql://user:pass@host:port/dbname)
        backup_name: Optional custom backup name (defaults to timestamp)
    
    Returns:
        Dict with backup metadata:
        - success: bool
        - backup_id: str (filename without extension)
        - filename: str (full filename with extension)
        - path: str (full path to backup file)
        - size_mb: float
        - timestamp: str (ISO format)
        - error: Optional[str]
    """
    _ensure_backups_dir()
    
    result = {
        "success": False,
        "backup_id": None,
        "filename": None,
        "path": None,
        "size_mb": 0.0,
        "timestamp": None,
        "error": None,
    }
    
    try:
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_id = backup_name or f"backup_{timestamp}"
        backup_file_gz = BACKUPS_DIR / f"{backup_id}.sql.gz"
        
        parsed_url = _parse_db_url(db_url)
        
        env = os.environ.copy()
        env["PGPASSWORD"] = parsed_url["password"]
        
        pg_dump_cmd = [
            "pg_dump",
            "-h", parsed_url["host"],
            "-p", str(parsed_url["port"]),
            "-U", parsed_url["user"],
            "-d", parsed_url["database"],
            "--format=plain",
            "--verbose",
        ]
        
        logger.info(f"[backup] Starting backup: {backup_id}")
        logger.info(f"[backup] Command: {' '.join(pg_dump_cmd)}")
        
        result_dump = await asyncio.create_subprocess_exec(
            *pg_dump_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        
        stdout, stderr = await result_dump.communicate()
        
        if result_dump.returncode != 0:
            error_msg = stderr.decode('utf-8', errors='ignore')
            logger.error(f"[backup] pg_dump failed: {error_msg}")
            result["error"] = f"pg_dump failed: {error_msg}"
            return result
        
        with gzip.open(backup_file_gz, "wb") as f_out:
            f_out.write(stdout)
        
        size_bytes = backup_file_gz.stat().st_size
        size_mb = size_bytes / (1024 * 1024)
        
        result["success"] = True
        result["backup_id"] = backup_id
        result["filename"] = backup_file_gz.name
        result["path"] = str(backup_file_gz)
        result["size_mb"] = round(size_mb, 2)
        result["timestamp"] = datetime.utcnow().isoformat()
        
        logger.info(f"[backup] Backup completed: {backup_id} ({size_mb:.2f} MB)")
        
    except Exception as e:
        logger.error(f"[backup] Backup failed: {e}", exc_info=True)
        result["error"] = str(e)
    
    return result


async def restore_database_backup(
    db_url: str,
    backup_filename: str,
) -> Dict[str, Any]:
    """
    Restores a PostgreSQL database from a backup file.
    
    Args:
        db_url: Database connection URL
        backup_filename: Filename of the backup (e.g., 'backup_20240101_120000.sql.gz')
    
    Returns:
        Dict with restore results:
        - success: bool
        - backup_id: str (filename without extension)
        - timestamp: str (restore timestamp)
        - error: Optional[str]
    """
    result = {
        "success": False,
        "backup_id": None,
        "timestamp": None,
        "error": None,
        "warning": None,
    }
    
    try:
        _ensure_backups_dir()
        
        backup_path = BACKUPS_DIR / backup_filename
        
        if not backup_path.exists():
            result["error"] = f"Backup file not found: {backup_filename}"
            logger.error(f"[restore] Backup file not found: {backup_path}")
            return result
        
        temp_sql_file = BACKUPS_DIR / f"restore_temp_{datetime.utcnow().timestamp()}.sql"
        
        try:
            with gzip.open(backup_path, "rb") as f_in:
                with open(temp_sql_file, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)
        except Exception as e:
            result["error"] = f"Failed to decompress backup: {str(e)}"
            logger.error(f"[restore] Decompression failed: {e}")
            return result
        
        parsed_url = _parse_db_url(db_url)
        
        env = os.environ.copy()
        env["PGPASSWORD"] = parsed_url["password"]
        
        psql_cmd = [
            "psql",
            "-h", parsed_url["host"],
            "-p", str(parsed_url["port"]),
            "-U", parsed_url["user"],
            "-d", parsed_url["database"],
            "-f", str(temp_sql_file),
        ]
        
        logger.info(f"[restore] Starting restore from: {backup_filename}")
        logger.info(f"[restore] Command: {' '.join(psql_cmd)}")
        
        result_restore = await asyncio.create_subprocess_exec(
            *psql_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        
        stdout, stderr = await result_restore.communicate()
        
        try:
            temp_sql_file.unlink()
        except FileNotFoundError:
            pass
        
        if result_restore.returncode != 0:
            error_msg = stderr.decode('utf-8', errors='ignore')
            logger.error(f"[restore] psql failed: {error_msg}")
            result["error"] = f"psql failed: {error_msg}"
            return result
        
        result["success"] = True
        result["backup_id"] = backup_filename.replace(".sql.gz", "").replace(".sql", "")
        result["timestamp"] = datetime.utcnow().isoformat()
        
        logger.info(f"[restore] Restore completed successfully")
        
    except Exception as e:
        logger.error(f"[restore] Restore failed: {e}", exc_info=True)
        result["error"] = str(e)
    
    return result


async def list_backups() -> Dict[str, Any]:
    """
    Lists all available backups.
    
    Returns:
        Dict with:
        - success: bool
        - backups: list of backup info dicts
        - total_size_mb: float
        - count: int
    """
    result = {
        "success": False,
        "backups": [],
        "total_size_mb": 0.0,
        "count": 0,
        "error": None,
    }
    
    try:
        _ensure_backups_dir()
        
        backup_files = sorted(
            BACKUPS_DIR.glob("backup_*.sql.gz"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        
        total_size = 0
        
        for backup_file in backup_files:
            stat = backup_file.stat()
            size_bytes = stat.st_size
            size_mb = size_bytes / (1024 * 1024)
            total_size += size_bytes
            
            result["backups"].append({
                "filename": backup_file.name,
                "backup_id": backup_file.stem.replace(".sql", ""),
                "size_mb": round(size_mb, 2),
                "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            })
        
        result["count"] = len(backup_files)
        result["total_size_mb"] = round(total_size / (1024 * 1024), 2)
        result["success"] = True
        
    except Exception as e:
        logger.error(f"[backups_list] Error listing backups: {e}", exc_info=True)
        result["error"] = str(e)
    
    return result


async def delete_backup(backup_filename: str) -> Dict[str, Any]:
    """
    Deletes a backup file.
    
    Args:
        backup_filename: Filename of the backup to delete
    
    Returns:
        Dict with deletion results
    """
    result = {
        "success": False,
        "backup_id": None,
        "error": None,
    }
    
    try:
        _ensure_backups_dir()
        
        backup_path = BACKUPS_DIR / backup_filename
        
        if not backup_path.exists():
            result["error"] = f"Backup file not found: {backup_filename}"
            logger.warning(f"[backup_delete] File not found: {backup_path}")
            return result
        
        backup_path.unlink()
        
        result["success"] = True
        result["backup_id"] = backup_filename.replace(".sql.gz", "").replace(".sql", "")
        
        logger.info(f"[backup_delete] Backup deleted: {backup_filename}")
        
    except Exception as e:
        logger.error(f"[backup_delete] Error deleting backup: {e}", exc_info=True)
        result["error"] = str(e)
    
    return result


def _parse_db_url(db_url: str) -> Dict[str, Any]:
    """
    Parses a PostgreSQL connection URL.
    
    Expected format: postgresql://user:password@host:port/database
    """
    from urllib.parse import urlparse
    
    parsed = urlparse(db_url)
    
    database = parsed.path.lstrip("/")

    if not all([parsed.hostname, parsed.username, database]):
        raise ValueError(f"Invalid database URL: {db_url}")
    
    return {
        "user": parsed.username,
        "password": parsed.password or "",
        "host": parsed.hostname,
        "port": parsed.port or 5432,
        "database": database,
    }
