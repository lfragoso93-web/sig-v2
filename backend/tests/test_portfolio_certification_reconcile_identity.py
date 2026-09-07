from pathlib import Path


def test_shared_certification_identity_requires_active_owned_user_and_portfolio():
    source = Path(
        "app/certification/portfolio_certification_identity.py"
    ).read_text(encoding="utf-8")

    for token in (
        "User.email == identity.user_email",
        "User.name == identity.user_name",
        "User.role == UserRole.user",
        "User.is_active.is_(True)",
        "Portfolio.name == identity.portfolio_name",
        "Portfolio.description == identity.ownership_marker",
        "Portfolio.is_active.is_(True)",
    ):
        assert token in source


def test_reconciliation_cli_reuses_shared_certification_identity():
    source = Path("app/cli/portfolio_certification_reconcile.py").read_text(encoding="utf-8")

    assert "load_certification_portfolio_identity" in source
    assert "select(Portfolio.id, User.id)" not in source
