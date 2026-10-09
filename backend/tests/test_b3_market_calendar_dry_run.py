import pytest

from app.services.b3_market_calendar_dry_run import (
    extract_b3_annual_calendar_dry_run,
)


SOURCE_REFERENCE = "https://www.b3.com.br/pt_br/noticias/calendario-2026.htm"


def test_extracts_explicit_closures_and_preserves_special_operation_dates():
    report = extract_b3_annual_calendar_dry_run(
        """
        01 de janeiro - Confraternização Universal
        18 de fevereiro - A B3 opera em horário especial.
        09 de julho - Funcionamento normal na B3.
        25 de dezembro - Natal
        """,
        year=2026,
        source_reference=SOURCE_REFERENCE,
    )

    assert report.dry_run is True
    assert report.database_writes_executed == 0
    assert report.explicitly_closed_dates == ("2026-01-01", "2026-12-25")
    assert report.special_operation_dates == ("2026-02-18",)
    assert report.source_dates_found == (
        "2026-01-01",
        "2026-02-18",
        "2026-07-09",
        "2026-12-25",
    )
    assert report.complete_daily_coverage is False


def test_rejects_source_without_dates():
    with pytest.raises(ValueError, match="no recognized Portuguese dates"):
        extract_b3_annual_calendar_dry_run(
            "Calendário sem datas reconhecíveis.",
            year=2026,
            source_reference=SOURCE_REFERENCE,
        )


def test_extracts_both_dates_when_a_month_is_shared():
    report = extract_b3_annual_calendar_dry_run(
        "16 e 17 de fevereiro - Carnaval",
        year=2026,
        source_reference=SOURCE_REFERENCE,
    )

    assert report.explicitly_closed_dates == ("2026-02-16", "2026-02-17")
