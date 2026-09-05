import pytest

from app.cli import portfolio_certification_seed as cli


def test_cli_requires_password_env(monkeypatch) -> None:
    monkeypatch.delenv(cli.PASSWORD_ENV, raising=False)

    with pytest.raises(SystemExit, match="SGI_CERT303_PASSWORD is required"):
        cli.main()
