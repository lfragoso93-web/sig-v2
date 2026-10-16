import asyncio
from types import SimpleNamespace
from unittest.mock import ANY, AsyncMock

import pytest

from app.cli import portfolio_certification_seed as cli


def test_cli_requires_password_env(monkeypatch) -> None:
    monkeypatch.delenv(cli.PASSWORD_ENV, raising=False)

    with pytest.raises(SystemExit, match="SGI_CERT303_PASSWORD is required"):
        cli.main()


class _SessionContext:
    async def __aenter__(self) -> object:
        return object()

    async def __aexit__(self, *args: object) -> None:
        return None


def test_cli_output_does_not_expose_password(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    password = "unique-do-not-log-password"
    monkeypatch.setenv(cli.PASSWORD_ENV, password)
    monkeypatch.setattr(cli, "AsyncSessionLocal", _SessionContext)
    provision = AsyncMock(
        return_value=SimpleNamespace(
            user_id=1,
            portfolio_id=2,
            user_created=True,
            portfolio_created=True,
            password_rotated=True,
        )
    )
    monkeypatch.setattr(cli, "provision_synthetic_user_portfolio", provision)
    transaction_result = SimpleNamespace(
        created=3,
        reused=4,
        crypto_membership_created=True,
        crypto_membership_reused=False,
    )
    count_result = SimpleNamespace(created=1, reused=0)
    benchmark_result = SimpleNamespace(
        rates_created=1,
        rates_reused=0,
        coverages_created=1,
        coverages_reused=0,
    )
    monkeypatch.setattr(
        cli,
        "seed_transactions",
        AsyncMock(return_value=transaction_result),
    )
    monkeypatch.setattr(
        cli,
        "seed_generic_market_prices",
        AsyncMock(return_value=count_result),
    )
    monkeypatch.setattr(
        cli,
        "seed_synthetic_dividends",
        AsyncMock(return_value=count_result),
    )
    monkeypatch.setattr(
        cli,
        "seed_synthetic_treasury_price",
        AsyncMock(return_value=count_result),
    )
    monkeypatch.setattr(
        cli,
        "seed_synthetic_benchmark_rate",
        AsyncMock(return_value=benchmark_result),
    )

    asyncio.run(cli._run())
    output = capsys.readouterr().out

    assert password not in output
    assert cli.PASSWORD_ENV not in output
    assert "password" not in output.lower()
    provision.assert_awaited_once_with(
        ANY,
        password=password,
        rotate_password=False,
    )
