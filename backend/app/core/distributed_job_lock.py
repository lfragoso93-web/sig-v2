"""Redis-backed lease for scheduler jobs running across multiple processes."""

from __future__ import annotations

import logging
import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
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
    try:
        yield True
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
