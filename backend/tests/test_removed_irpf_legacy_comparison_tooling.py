from pathlib import Path


_BACKEND = Path(__file__).resolve().parents[1]


def test_irpf_legacy_comparison_tooling_is_absent() -> None:
    removed_paths = (
        "app/cli/irpf_compare_legacy.py",
        "app/cli/irpf_compare_legacy_batch.py",
        "app/cli/irpf_compare_day_trade.py",
        "app/cli/irpf_compare_integrated.py",
        "app/services/irpf_legacy_comparison_service.py",
        "app/services/irpf_comparison_batch_service.py",
        "app/services/irpf_day_trade_comparison_service.py",
        "app/services/irpf_day_trade_legacy_comparison.py",
        "app/services/irpf_integrated_comparison_service.py",
        "app/services/irpf_integrated_legacy_comparison.py",
        "tests/test_irpf_compare_day_trade_cli.py",
        "tests/test_irpf_compare_integrated_cli.py",
        "tests/test_irpf_compare_legacy_batch_cli.py",
        "tests/test_irpf_compare_legacy_cli.py",
        "tests/test_irpf_comparison_batch_service.py",
        "tests/test_irpf_day_trade_comparison_service.py",
        "tests/test_irpf_day_trade_legacy_comparison.py",
        "tests/test_irpf_integrated_comparison_service.py",
        "tests/test_irpf_integrated_legacy_comparison.py",
        "tests/test_irpf_legacy_comparison_service.py",
    )

    unexpected = [path for path in removed_paths if (_BACKEND / path).exists()]
    assert unexpected == [], (
        f"tooling legado de comparação IRPF ainda distribuído: {unexpected}"
    )
