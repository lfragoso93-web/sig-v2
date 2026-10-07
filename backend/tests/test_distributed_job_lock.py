"""Distributed scheduler lease and crash-recovery contracts."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from app.core import distributed_job_lock as lock_module
from app.core.distributed_job_lock import distributed_job_lock, scheduler_lock_key


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


class _FakeRedis:
    def __init__(self) -> None:
        self.now = 0
        self.values: dict[str, tuple[str, int]] = {}

    def advance(self, seconds: int) -> None:
        self.now += seconds

    def _expire(self, key: str) -> None:
        current = self.values.get(key)
        if current is not None and current[1] <= self.now:
            self.values.pop(key)

    async def set(self, key: str, value: str, *, nx: bool, ex: int):
        assert nx is True
        self._expire(key)
        if key in self.values:
            return None
        self.values[key] = (value, self.now + ex)
        return True

    async def eval(self, script: str, key_count: int, key: str, token: str):
        assert "redis.call('get'" in script
        assert key_count == 1
        self._expire(key)
        current = self.values.get(key)
        if current is None or current[0] != token:
            return 0
        self.values.pop(key)
        return 1


async def _return(value):
    return value


def test_lock_key_rejects_unsafe_or_unbounded_segments() -> None:
    assert scheduler_lock_key("persist_daily_close_prices", "daily") == (
        "sgi:job:persist_daily_close_prices:daily"
    )

    for unsafe in ("UPPER", "../escape", "with space", "x" * 65):
        with pytest.raises(ValueError, match="safe lowercase"):
            scheduler_lock_key(unsafe, "daily")


def test_reliable_async_adr_records_inventory_and_no_outbox_decision() -> None:
    adr = (REPOSITORY_ROOT / "docs" / "RELIABLE_ASYNC.md").read_text(
        encoding="utf-8"
    )

    for required in (
        "## Inventário e risco",
        "fechamento diário global de preços",
        "TTL de duas horas",
        "Status: **não adotar agora**",
        "semântica at-least-once",
    ):
        assert required in adr


@pytest.mark.asyncio
async def test_concurrent_process_is_refused_and_owner_releases(
    monkeypatch,
    caplog,
) -> None:
    redis = _FakeRedis()
    monkeypatch.setattr(lock_module, "get_redis", lambda: _return(redis))

    with caplog.at_level(logging.INFO):
        async with distributed_job_lock(
            job_name="persist_daily_close_prices",
            period="daily",
            ttl_seconds=120,
        ) as first_acquired:
            assert first_acquired is True
            async with distributed_job_lock(
                job_name="persist_daily_close_prices",
                period="daily",
                ttl_seconds=120,
            ) as second_acquired:
                assert second_acquired is False

    assert redis.values == {}
    assert "scheduler_lock_acquired" in caplog.text
    assert "reason=already_running" in caplog.text
    assert "scheduler_lock_released" in caplog.text


@pytest.mark.asyncio
async def test_expired_crashed_owner_does_not_create_permanent_deadlock(
    monkeypatch,
) -> None:
    redis = _FakeRedis()
    monkeypatch.setattr(lock_module, "get_redis", lambda: _return(redis))
    crashed = distributed_job_lock(
        job_name="persist_daily_close_prices",
        period="daily",
        ttl_seconds=60,
    )

    assert await crashed.__aenter__() is True
    redis.advance(61)

    recovered = distributed_job_lock(
        job_name="persist_daily_close_prices",
        period="daily",
        ttl_seconds=60,
        attempt=2,
    )
    assert await recovered.__aenter__() is True
    replacement = dict(redis.values)

    await crashed.__aexit__(None, None, None)
    assert redis.values == replacement
    await recovered.__aexit__(None, None, None)
    assert redis.values == {}


@pytest.mark.asyncio
async def test_redis_unavailable_fails_closed_and_logs_refusal(
    monkeypatch,
    caplog,
) -> None:
    monkeypatch.setattr(lock_module, "get_redis", lambda: _return(None))

    with caplog.at_level(logging.INFO):
        async with distributed_job_lock(
            job_name="persist_daily_close_prices",
            period="daily",
            ttl_seconds=120,
            attempt=2,
        ) as acquired:
            assert acquired is False

    assert "scheduler_lock_refused" in caplog.text
    assert "reason=redis_unavailable" in caplog.text
    assert "reprocessing=True" in caplog.text
