"""Redis-backed lease for scheduler jobs running across multiple processes."""

from __future__ import annotations

import logging
import json
import re
import time
from contextlib import contextmanager
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from uuid import uuid4

from app.core.cache import get_redis
from app.core.log_safety import sanitize_log_value


logger = logging.getLogger(__name__)
_SCHEDULER_TRIGGER_SOURCE: ContextVar[str] = ContextVar(
    "scheduler_trigger_source", default="scheduled"
)
_SCHEDULER_TRIGGER_ACTOR: ContextVar[str] = ContextVar(
    "scheduler_trigger_actor", default=""
)


@contextmanager
def scheduler_execution_source(source: str, actor_user_id: int | None = None):
    if source not in {"scheduled", "manual"}:
        raise ValueError("unsupported scheduler trigger source")
    token = _SCHEDULER_TRIGGER_SOURCE.set(source)
    actor_token = _SCHEDULER_TRIGGER_ACTOR.set(
        str(actor_user_id) if actor_user_id is not None else ""
    )
    try:
        yield
    finally:
        _SCHEDULER_TRIGGER_ACTOR.reset(actor_token)
        _SCHEDULER_TRIGGER_SOURCE.reset(token)


_LOCK_SEGMENT = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}")
_RELEASE_IF_OWNER = """
if redis.call('get', KEYS[1]) == ARGV[1] then
    return redis.call('del', KEYS[1])
end
return 0
"""
_RECORD_STATUS_IF_OWNER = """
if redis.call('get', KEYS[1]) ~= ARGV[1] then
    return 0
end
if ARGV[2] == 'terminal'
    and redis.call('hget', KEYS[2], 'run_token') ~= ARGV[1] then
    return 0
end
for i = 3, #ARGV - 1, 2 do
    redis.call('hset', KEYS[2], ARGV[i], ARGV[i + 1])
end
redis.call('expire', KEYS[2], tonumber(ARGV[#ARGV]))
return 1
"""
_JOB_STATUS_RETENTION_SECONDS = 90 * 24 * 60 * 60
_JOB_HISTORY_LIMIT = 100


class ScheduledJobFailed(RuntimeError):
    """Sanitized exception surfaced to APScheduler after a failed job."""

    def __init__(self, original_error_type: str) -> None:
        self.original_error_type = original_error_type
        super().__init__(f"scheduled job failed ({original_error_type})")


def scheduler_job_status_key(job_name: str) -> str:
    if not _LOCK_SEGMENT.fullmatch(job_name):
        raise ValueError("job_name must be a safe lowercase lock segment")
    return f"sgi:job:status:{job_name}"


def scheduler_job_history_key(job_name: str) -> str:
    if not _LOCK_SEGMENT.fullmatch(job_name):
        raise ValueError("job_name must be a safe lowercase lock segment")
    return f"sgi:job:history:{job_name}"


async def _record_job_status(
    client,
    lock_key: str,
    status_key: str,
    owner_token: str,
    values: dict[str, str],
    *,
    terminal: bool,
) -> bool:
    """Persist status only while this execution still owns the current lease."""
    try:
        arguments = [owner_token, "terminal" if terminal else "start"]
        for name, value in values.items():
            arguments.extend((name, value))
        arguments.append(str(_JOB_STATUS_RETENTION_SECONDS))
        recorded = bool(
            await client.eval(
                _RECORD_STATUS_IF_OWNER,
                2,
                lock_key,
                status_key,
                *arguments,
            )
        )
        if not recorded:
            logger.warning(
                "scheduler_status_write_ignored reason=lease_owner_changed"
            )
        return recorded
    except Exception as exc:
        logger.warning(
            "scheduler_status_write_failed error_type=%s",
            type(exc).__name__,
        )
        return False


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


async def read_scheduler_job_history(
    job_name: str, *, limit: int = 30
) -> list[dict[str, str]]:
    """Read a bounded, sanitized execution history for a known scheduler job."""
    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")
    client = await get_redis()
    if client is None:
        return []
    try:
        rows = await client.lrange(scheduler_job_history_key(job_name), 0, limit - 1)
        result = []
        for row in rows:
            raw = row.decode() if isinstance(row, bytes) else str(row)
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                result.append({str(k): str(v) for k, v in parsed.items()})
        return result
    except Exception as exc:
        logger.warning(
            "scheduler_history_read_failed job=%s error_type=%s",
            job_name,
            type(exc).__name__,
        )
        return []


async def _append_job_history(client, job_name: str, values: dict[str, str]) -> None:
    try:
        key = scheduler_job_history_key(job_name)
        await client.lpush(key, json.dumps(values, separators=(",", ":")))
        await client.ltrim(key, 0, _JOB_HISTORY_LIMIT - 1)
        await client.expire(key, _JOB_STATUS_RETENTION_SECONDS)
    except Exception as exc:
        logger.warning(
            "scheduler_history_write_failed job=%s error_type=%s",
            job_name,
            type(exc).__name__,
        )


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
    status_job_name: str | None = None,
    trigger_source: str | None = None,
) -> AsyncIterator[bool]:
    """Acquire a fail-closed Redis lease and release only the owned token."""
    if ttl_seconds <= 0:
        raise ValueError("ttl_seconds must be positive")
    if attempt <= 0:
        raise ValueError("attempt must be positive")

    key = scheduler_lock_key(job_name, period)
    status_name = status_job_name or job_name
    execution_source = trigger_source or _SCHEDULER_TRIGGER_SOURCE.get()
    execution_actor = _SCHEDULER_TRIGGER_ACTOR.get()
    status_key = scheduler_job_status_key(status_name)
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
    started_at = datetime.now(timezone.utc).isoformat()
    started_clock = time.monotonic()
    await _record_job_status(
        client,
        key,
        status_key,
        owner_token,
        {
            "job_name": status_name,
            "run_token": owner_token,
            "status": "running",
            "last_started_at": started_at,
            "last_finished_at": "",
            "duration_ms": "",
            "last_error_type": "",
            "lease_ttl_seconds": str(ttl_seconds),
            "trigger_source": execution_source,
            "triggered_by_user_id": execution_actor,
        },
        terminal=False,
    )
    try:
        yield True
    except Exception as exc:
        error_type = getattr(exc, "original_error_type", type(exc).__name__)
        finished_at = datetime.now(timezone.utc).isoformat()
        duration_ms = str(round((time.monotonic() - started_clock) * 1000))
        await _record_job_status(
            client,
            key,
            status_key,
            owner_token,
            {
                "status": "failed",
                "last_finished_at": finished_at,
                "duration_ms": duration_ms,
                "last_error_type": error_type,
                "trigger_source": execution_source,
                "triggered_by_user_id": execution_actor,
            },
            terminal=True,
        )
        await _append_job_history(
            client,
            status_name,
            {
                "status": "failed",
                "started_at": started_at,
                "finished_at": finished_at,
                "duration_ms": duration_ms,
                "error_type": error_type,
                "trigger_source": execution_source,
                "triggered_by_user_id": execution_actor,
            },
        )
        logger.error(
            "scheduler_job_failed job=%s error_type=%s",
            job_name,
            error_type,
        )
        raise ScheduledJobFailed(error_type) from None
    else:
        finished_at = datetime.now(timezone.utc).isoformat()
        duration_ms = str(round((time.monotonic() - started_clock) * 1000))
        await _record_job_status(
            client,
            key,
            status_key,
            owner_token,
            {
                "status": "succeeded",
                "last_finished_at": finished_at,
                "duration_ms": duration_ms,
                "last_error_type": "",
                "trigger_source": execution_source,
                "triggered_by_user_id": execution_actor,
            },
            terminal=True,
        )
        await _append_job_history(
            client,
            status_name,
            {
                "status": "succeeded",
                "started_at": started_at,
                "finished_at": finished_at,
                "duration_ms": duration_ms,
                "error_type": "",
                "trigger_source": execution_source,
                "triggered_by_user_id": execution_actor,
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
