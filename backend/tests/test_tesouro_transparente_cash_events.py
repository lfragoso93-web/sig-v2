from app.integrations.tesouro_transparente_cash_events import (
    inspect_coupon_payment_csv,
    select_latest_coupon_resource,
)


def test_selects_latest_official_coupon_resource() -> None:
    payload = {
        "success": True,
        "result": {
            "resources": [
                {
                    "id": "old",
                    "name": "Pagamento de Cupom de Juros do Tesouro Direto",
                    "format": "CSV",
                    "url": "https://official.example/old.csv",
                    "last_modified": "2026-07-02T10:21:03",
                },
                {
                    "id": "new",
                    "name": "Pagamento de Cupom de Juros do Tesouro Direto",
                    "format": "CSV",
                    "url": "https://official.example/new.csv",
                    "last_modified": "2026-07-03T10:39:08",
                },
                {
                    "id": "maturity",
                    "name": "Vencimentos do Tesouro Direto",
                    "format": "CSV",
                    "url": "https://official.example/maturity.csv",
                    "last_modified": "2026-10-08T10:20:06",
                },
            ]
        },
    }

    assert select_latest_coupon_resource(payload) == {
        "resource_id": "new",
        "url": "https://official.example/new.csv",
        "last_modified": "2026-07-03T10:39:08",
    }


def test_coupon_payment_facts_remain_non_promotable_without_eligibility() -> None:
    csv_text = """Tipo Titulo;Vencimento do Titulo;Data Resgate;PU;Quantidade;Valor
Tesouro Prefixado com Juros Semestrais;01/01/2035;01/07/2026;48,808850;2685086,30;131055974,45
"""

    report = inspect_coupon_payment_csv(csv_text)

    assert report["facts_accepted"] == 1
    assert report["facts_rejected"] == 0
    assert report["latest_payment_date"] == "2026-07-01"
    assert report["status"] == "blocked_missing_eligibility"
    assert report["capabilities"]["payment_date"] is True
    assert report["capabilities"]["gross_value_per_unit"] is True
    assert report["capabilities"]["record_date"] is False
    assert report["capabilities"]["portfolio_eligibility"] is False
    assert report["promotable_events"] == 0
    assert report["database_writes_executed"] == 0


def test_invalid_schema_fails_closed() -> None:
    report = inspect_coupon_payment_csv("title;date;value\nTesouro;01/07/2026;48,80\n")

    assert report["status"] == "invalid_source_schema"
    assert report["promotable_events"] == 0
    assert report["database_writes_executed"] == 0
    assert report["blockers"]


def test_inconsistent_aggregate_is_rejected() -> None:
    csv_text = """Tipo Titulo;Vencimento do Titulo;Data Resgate;PU;Quantidade;Valor
Tesouro Prefixado com Juros Semestrais;01/01/2035;01/07/2026;48,808850;2,00;999,00
"""

    report = inspect_coupon_payment_csv(csv_text)

    assert report["facts_accepted"] == 0
    assert report["facts_rejected"] == 1
    assert report["promotable_events"] == 0


def test_business_day_payment_after_maturity_remains_a_valid_official_fact() -> None:
    csv_text = """Tipo Titulo;Vencimento do Titulo;Data Resgate;PU;Quantidade;Valor
Tesouro Prefixado com Juros Semestrais;01/10/2005;03/10/2005;48,808850;2,00;97,62
"""

    report = inspect_coupon_payment_csv(csv_text)

    assert report["facts_accepted"] == 1
    assert report["facts_rejected"] == 0
