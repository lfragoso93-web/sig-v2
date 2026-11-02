"""Redis-backed lease for scheduler jobs running across multiple processes."""

from __future__ import annotations

import logging
import re
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from uuid import uuid4

from app.core.cache import get_redis
from app.core.log_safety import sanitize_log_value


logger = logging.getLogger(__name__)

_LOCK_SEGMENT = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}")
_RELEASE_IF_OWNER = """
if redis.call('get', KEYS[1]) == ARGV[1] then
    return redis.call('del', KEYS[1])
end
return 0
"""
_JOB_STATUS_RETENTION_SECONDS = 90 * 24 * 60 * 60


class ScheduledJobFailed(RuntimeError):
    """Sanitized exception surfaced to APScheduler after a failed job."""

    def __init__(self, original_error_type: str) -> None:
        self.original_error_type = original_error_type
        super().__init__(f"scheduled job failed ({original_error_type})")


def scheduler_job_status_key(job_name: str) -> str:
    if not _LOCK_SEGMENT.fullmatch(job_name):
        raise ValueError("job_name must be a safe lowercase lock segment")
    return f"sgi:job:status:{job_name}"


async def _record_job_status(client, key: str, values: dict[str, str]) -> None:
    """Persist best-effort operational status without changing job outcome."""
    try:
        await client.hset(key, mapping=values)
        await client.expire(key, _JOB_STATUS_RETENTION_SECONDS)
    except Exception as exc:
        logger.warning(
            "scheduler_status_write_failed error_type=%s",
            type(exc).__name__,
        )


async def read_scheduler_job_statuses(
    job_names: tuple[str, ...],
) -> dict[str, dict[str, str]]:
    """Read the latest run status for a fixed list of known jobs."""
    client = await get_redis()
    if client is None:
        return {}
    result: dict[str, dict[str, str]] = {}
    for job_name in job_names:
        try:
            values = await client.hgetall(scheduler_job_status_key(job_name))
        except Exception as exc:
            logger.warning(
                "scheduler_status_read_failed job=%s error_type=%s",
                job_name,
                type(exc).__name__,
            )
            return {}
        result[job_name] = {
            key.decode() if isinstance(key, bytes) else str(key):
            value.decode() if isinstance(value, bytes) else str(value)
            for key, value in values.items()
        }
    return result


def scheduler_lock_key(job_name: str, period: str) -> str:
    for label, value in (("job_name", job_name), ("period", period)):
        if not _LOCK_SEGMENT.fullmatch(value):
            raise ValueError(f"{label} must be a safe lowercase lock segment")
    return f"sgi:job:{job_name}:{period}"


@asynccontextmanager
async def distributed_job_lock(
    *,
    job_name: str,
    period: str,
    ttl_seconds: int,
    attempt: int = 1,
) -> AsyncIterator[bool]:
    """Acquire a fail-closed Redis lease and release only the owned token."""
    if ttl_seconds <= 0:
        raise ValueError("ttl_seconds must be positive")
    if attempt <= 0:
        raise ValueError("attempt must be positive")

    key = scheduler_lock_key(job_name, period)
    owner_token = uuid4().hex
    client = await get_redis()
    if client is None:
        logger.warning(
            "scheduler_lock_refused job=%s period=%s reason=redis_unavailable "
            "attempt=%s reprocessing=%s",
            job_name,
            period,
            attempt,
            attempt > 1,
        )
        yield False
        return

    try:
        acquired = bool(await client.set(key, owner_token, nx=True, ex=ttl_seconds))
    except Exception as exc:
        logger.warning(
            "scheduler_lock_refused job=%s period=%s reason=redis_error "
            "error_type=%s error=%s attempt=%s reprocessing=%s",
            job_name,
            period,
            type(exc).__name__,
            sanitize_log_value(exc),
            attempt,
            attempt > 1,
        )
        yield False
        return

    if not acquired:
        logger.info(
            "scheduler_lock_refused job=%s period=%s reason=already_running "
            "attempt=%s reprocessing=%s",
            job_name,
            period,
            attempt,
            attempt > 1,
        )
        yield False
        return

    logger.info(
        "scheduler_lock_acquired job=%s period=%s ttl_seconds=%s "
        "attempt=%s reprocessing=%s",
        job_name,
        period,
        ttl_seconds,
        attempt,
        attempt > 1,
    )
    status_key = scheduler_job_status_key(job_name)
    started_at = datetime.now(timezone.utc).isoformat()
    started_clock = time.monotonic()
    await _record_job_status(
        client,
        status_key,
        {
            "job_name": job_name,
            "status": "running",
            "last_started_at": started_at,
            "last_finished_at": "",
            "duration_ms": "",
            "last_error_type": "",
            "lease_ttl_seconds": str(ttl_seconds),
        },
    )
    try:
        yield True
    except Exception as exc:
        error_type = getattr(exc, "original_error_type", type(exc).__name__)
        await _record_job_status(
            client,
            status_key,
            {
                "status": "failed",
                "last_finished_at": datetime.now(timezone.utc).isoformat(),
                "duration_ms": str(round((time.monotonic() - started_clock) * 1000)),
                "last_error_type": error_type,
            },
        )
        logger.error(
            "scheduler_job_failed job=%s error_type=%s",
            job_name,
            error_type,
        )
        raise ScheduledJobFailed(error_type) from None
    else:
        await _record_job_status(
            client,
            status_key,
            {
                "status": "succeeded",
                "last_finished_at": datetime.now(timezone.utc).isoformat(),
                "duration_ms": str(round((time.monotonic() - started_clock) * 1000)),
                "last_error_type": "",
            },
        )
        logger.info("scheduler_job_succeeded job=%s", job_name)
    finally:
        try:
            released = bool(
                await client.eval(_RELEASE_IF_OWNER, 1, key, owner_token)
            )
            if released:
                logger.info(
                    "scheduler_lock_released job=%s period=%s",
                    job_name,
                    period,
                )
            else:
                logger.warning(
                    "scheduler_lock_release_lost job=%s period=%s "
                    "reason=expired_or_reacquired",
                    job_name,
                    period,
                )
        except Exception as exc:
            logger.warning(
                "scheduler_lock_release_failed job=%s period=%s "
                "error_type=%s error=%s",
                job_name,
                period,
                type(exc).__name__,
                sanitize_log_value(exc),
            )
