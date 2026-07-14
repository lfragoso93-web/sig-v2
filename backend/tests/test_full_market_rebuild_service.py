import asyncio

from app.services.full_market_rebuild_service import (
    FullMarketRebuildResult,
    _run_step,
)


def test_run_step_records_success() -> None:
    summary = FullMarketRebuildResult(started_at="2026-07-13T00:00:00+00:00")

    async def operation() -> dict:
        return {"inserted": 10}

    asyncio.run(_run_step(summary, "prices", operation))

    assert summary.ok is True
    assert len(summary.steps) == 1
    assert summary.steps[0].name == "prices"
    assert summary.steps[0].ok is True
    assert summary.steps[0].result == {"inserted": 10}
    assert summary.steps[0].error is None


def test_run_step_records_error_and_continues_summary() -> None:
    summary = FullMarketRebuildResult(started_at="2026-07-13T00:00:00+00:00")

    async def operation() -> None:
        raise RuntimeError("provider unavailable")

    asyncio.run(_run_step(summary, "prices", operation))

    assert summary.ok is False
    assert len(summary.steps) == 1
    assert summary.steps[0].ok is False
    assert summary.steps[0].error == "provider unavailable"


def test_summary_to_dict_is_json_ready() -> None:
    summary = FullMarketRebuildResult(
        started_at="2026-07-13T00:00:00+00:00",
        finished_at="2026-07-13T00:01:00+00:00",
        duration_seconds=60.0,
    )

    async def operation() -> list[dict]:
        return [{"ticker": "PETR4", "ok": True}]

    asyncio.run(_run_step(summary, "audit", operation))
    payload = summary.to_dict()

    assert payload["ok"] is True
    assert payload["duration_seconds"] == 60.0
    assert payload["steps"][0]["result"][0]["ticker"] == "PETR4"
