from __future__ import annotations

import base64
import json
from datetime import date
from decimal import Decimal

import httpx
import pytest
from app.integrations.b3_listed_companies import (
    B3ListedCompaniesClient,
    B3ListedCompaniesError,
    b3_service_path,
    issuer_code_from_ticker,
    parse_b3_date,
)
from app.services.corporate_action_engine import (
    CorporateActionKind,
    CorporateActionNormalizationError,
    normalize_b3_corporate_actions,
)
from app.services.pre_prod_dividends_seed_providers import StrictB3DividendProvider


def test_b3_service_path_encodes_compact_json_as_base64() -> None:
    path = b3_service_path("GetListedSupplementBDR", {"issuingCompany": "NIKE", "language": "en-US"})
    encoded = path.rsplit("/", 1)[1]
    assert json.loads(base64.b64decode(encoded)) == {
        "issuingCompany": "NIKE", "language": "en-US"
    }


def test_issuer_code_and_b3_date_parsing() -> None:
    assert issuer_code_from_ticker("NIKE34") == "NIKE"
    assert issuer_code_from_ticker("PETR4") == "PETR"
    assert parse_b3_date("10/09/2026") == date(2026, 10, 9)
    assert parse_b3_date("2026-10-09") == date(2026, 10, 9)
    with pytest.raises(B3ListedCompaniesError):
        issuer_code_from_ticker("BTC")


@pytest.mark.asyncio
async def test_b3_bdr_cash_rows_normalize_dates_without_changing_rate() -> None:
    payload = [{
        "code": "NIKE", "tradingName": "NIKE", "cashDividends": [{
            "label": "DIVIDENDO", "rate": "0.14077750410",
            "approvedOn": "06/08/2026", "lastDatePrior": "09/01/2026",
            "paymentDate": "10/08/2026", "isinCode": "BRNIKEBDR006",
        }], "stockDividends": [], "subscriptions": [],
    }]

    async def handler(request: httpx.Request) -> httpx.Response:
        assert "/GetListedSupplementBDR/" in request.url.path
        return httpx.Response(200, json=payload)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        provider = StrictB3DividendProvider(client=B3ListedCompaniesClient(client=http))
        result = await provider("NIKE34", "BDR")

    assert result.source == "b3"
    assert result.rows[0]["rate"] == "0.14077750410"
    assert result.rows[0]["lastDatePrior"] == "2026-09-01"
    assert result.rows[0]["paymentDate"] == "2026-10-08"
    assert Decimal(result.rows[0]["rate"]) == Decimal("0.14077750410")


@pytest.mark.asyncio
async def test_b3_adapter_decodes_portal_double_encoded_json() -> None:
    payload = [{
        "code": "NIKE", "tradingName": "NIKE", "cashDividends": [],
        "stockDividends": [], "subscriptions": [],
    }]

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=json.dumps(payload))

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        result = await B3ListedCompaniesClient(client=http).company_supplement(
            ticker="NIKE34", is_bdr=True
        )
    assert result == payload[0]


@pytest.mark.asyncio
async def test_b3_native_cash_dividends_paginates_all_pages() -> None:
    supplement = [{
        "code": "PETR", "tradingName": "PETROBRAS", "cashDividends": [],
        "stockDividends": [], "subscriptions": [],
    }]
    requested_pages: list[int] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        if "/GetListedSupplementCompany/" in request.url.path:
            return httpx.Response(200, json=supplement)
        if "/GetListedCashDividends/" in request.url.path:
            encoded = request.url.path.rsplit("/", 1)[1]
            params = json.loads(base64.b64decode(encoded))
            page_number = params["pageNumber"]
            requested_pages.append(page_number)
            return httpx.Response(200, json={
                "page": {"pageNumber": page_number, "pageSize": 120, "totalPages": 2},
                "results": [{"id": page_number}],
            })
        return httpx.Response(404)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        supplement_result, rows, error = await B3ListedCompaniesClient(client=http).cash_dividends(
            ticker="PETR4", asset_type="ACAO"
        )
    assert supplement_result is not None and error is None
    assert requested_pages == [1, 2]
    assert rows == ({"id": 1}, {"id": 2})


@pytest.mark.asyncio
async def test_b3_native_provider_maps_share_class_and_canonical_fields() -> None:
    supplement = [{
        "code": "ALOS", "tradingName": "ALLOS", "cashDividends": [{
            "label": "DIVIDENDO", "rate": "0.29191863800",
            "lastDatePrior": "09/22/2026", "paymentDate": "10/02/2026",
            "approvedOn": "09/15/2026", "isinCode": "BRALOSACNOR5",
            "assetIssued": "BRALOSACNOR5",
        }], "stockDividends": [], "subscriptions": [],
    }]

    async def handler(request: httpx.Request) -> httpx.Response:
        if "/GetListedSupplementCompany/" in request.url.path:
            return httpx.Response(200, json=supplement)
        params = json.loads(base64.b64decode(request.url.path.rsplit("/", 1)[1]))
        return httpx.Response(200, json={
            "page": {"pageNumber": params["pageNumber"], "pageSize": 120, "totalPages": 1},
            "results": [
                {"typeStock": "PN", "dateApproval": "09/15/2026", "valueCash": "0.5",
                 "corporateAction": "DIVIDENDO", "lastDatePriorEx": "09/22/2026"},
                {"typeStock": "ON", "dateApproval": "09/15/2026", "valueCash": "0.291918638",
                 "corporateAction": "DIVIDENDO", "lastDatePriorEx": "09/22/2026"},
            ],
        })

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        provider = StrictB3DividendProvider(client=B3ListedCompaniesClient(client=http))
        result = await provider("ALOS3", "ACAO")

    assert len(result.rows) == 1
    assert result.rows[0]["rate"] == "0.291918638"
    assert result.rows[0]["lastDatePrior"] == "2026-09-22"
    assert result.rows[0]["paymentDate"] == "2026-10-02"
    assert result.rows[0]["isinCode"] == "BRALOSACNOR5"
    assert result.rows[0]["typeStock"] == "ON"


def test_b3_grouping_action_keeps_official_record_date_and_isin() -> None:
    payload = {
        "code": "NIKE", "stockDividends": [{
            "label": "GRUPAMENTO", "factor": "0.20000000000",
            "approvedOn": "09/08/2026", "lastDatePrior": "10/09/2026",
            "isinCode": "BRNIKEBDR006",
        }], "subscriptions": [],
    }
    action, = normalize_b3_corporate_actions("NIKE34", payload)
    assert action.source == "b3"
    assert action.kind == CorporateActionKind.REVERSE_SPLIT
    assert action.quantity_factor == Decimal("0.20000000000")
    assert action.event_date == date(2026, 10, 9)
    assert action.raw_payload["isinCode"] == "BRNIKEBDR006"
    assert action.raw_payload["effectiveDateResolution"] == "unresolved_until_b3_trading_calendar"


def test_b3_share_actions_convert_percentages_and_filter_by_isin() -> None:
    payload = {
        "code": "TEST",
        "stockDividends": [
            {
                "label": "BONIFICACAO", "factor": "4", "lastDatePrior": "01/02/2025",
                "isinCode": "BRTESTACNOR0",
            },
            {
                "label": "DESDOBRAMENTO", "factor": "100", "lastDatePrior": "02/03/2025",
                "isinCode": "BRTESTACNPR7",
            },
            {
                "label": "GRUPAMENTO", "factor": "0.02", "lastDatePrior": "03/04/2025",
                "isinCode": "BRTESTACNOR0",
            },
        ],
        "subscriptions": [],
    }

    actions = normalize_b3_corporate_actions(
        "TEST3", payload, expected_isin="brtestacnor0"
    )

    assert [action.quantity_factor for action in actions] == [
        Decimal("1.04"), Decimal("0.02")
    ]
    assert [action.kind for action in actions] == [
        CorporateActionKind.STOCK_BONUS,
        CorporateActionKind.REVERSE_SPLIT,
    ]
    assert all(action.raw_payload["sourceFactorConvention"] in {
        "percentage_increase", "quantity_multiplier"
    } for action in actions)


def test_b3_split_percentage_converts_to_quantity_multiplier() -> None:
    payload = {
        "code": "TEST",
        "stockDividends": [{
            "label": "DESDOBRAMENTO", "factor": "300", "lastDatePrior": "01/02/2025",
            "isinCode": "BRTESTACNOR0",
        }],
        "subscriptions": [],
    }

    action, = normalize_b3_corporate_actions("TEST3", payload)

    assert action.kind == CorporateActionKind.SPLIT
    assert action.quantity_factor == Decimal("4")


def test_b3_multi_class_payload_requires_expected_isin() -> None:
    payload = {
        "code": "TEST",
        "stockDividends": [
            {"label": "BONIFICACAO", "factor": "5", "lastDatePrior": "01/02/2025", "isinCode": "BRTESTACNOR0"},
            {"label": "BONIFICACAO", "factor": "5", "lastDatePrior": "01/02/2025", "isinCode": "BRTESTACNPR7"},
        ],
        "subscriptions": [],
    }

    with pytest.raises(CorporateActionNormalizationError, match="expected_isin"):
        normalize_b3_corporate_actions("TEST3", payload)


def test_b3_unknown_stock_action_label_fails_closed() -> None:
    payload = {
        "code": "TEST",
        "stockDividends": [{
            "label": "ROTULO DESCONHECIDO", "factor": "100", "lastDatePrior": "01/02/2025",
            "isinCode": "BRTESTACNOR0",
        }],
        "subscriptions": [],
    }

    with pytest.raises(CorporateActionNormalizationError, match="label nao suportado"):
        normalize_b3_corporate_actions("TEST3", payload)


def test_b3_complex_action_label_skipped_in_simple_normalizer() -> None:
    payload = {
        "code": "TEST",
        "stockDividends": [
            {
                "label": "BONIFICACAO", "factor": "10", "lastDatePrior": "01/02/2025",
                "isinCode": "BRTESTACNOR0",
            },
            {
                "label": "CIS RED CAP", "factor": "100", "lastDatePrior": "01/02/2020",
                "isinCode": "BRTESTACNOR0",
            },
        ],
        "subscriptions": [],
    }

    actions = normalize_b3_corporate_actions("TEST3", payload)
    assert len(actions) == 1
    assert actions[0].kind == CorporateActionKind.STOCK_BONUS


def test_b3_factor_with_thousands_separator_and_commas() -> None:
    payload = {
        "code": "TEST",
        "stockDividends": [{
            "label": "DESDOBRAMENTO", "factor": "4,900.00000000000", "lastDatePrior": "01/02/2025",
            "isinCode": "BRTESTACNOR0",
        }],
        "subscriptions": [],
    }

    action, = normalize_b3_corporate_actions("TEST3", payload)
    assert action.kind == CorporateActionKind.SPLIT
    assert action.quantity_factor == Decimal("50")
