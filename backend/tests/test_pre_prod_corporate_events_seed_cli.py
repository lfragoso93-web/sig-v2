from app.cli import pre_prod_corporate_events_seed as cli


def test_seed_cli_defaults_to_dry_run() -> None:
    arguments = cli._parser().parse_args(["--portfolio-id", "7"])

    assert arguments.execute is False


def test_seed_cli_requires_explicit_execute_for_persistence() -> None:
    arguments = cli._parser().parse_args(["--portfolio-id", "7", "--execute"])

    assert arguments.execute is True
