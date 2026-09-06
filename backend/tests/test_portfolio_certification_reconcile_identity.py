from pathlib import Path


def test_reconciliation_identity_lookup_requires_active_owned_user_and_portfolio():
    source = Path("app/cli/portfolio_certification_reconcile.py").read_text(encoding="utf-8")

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
