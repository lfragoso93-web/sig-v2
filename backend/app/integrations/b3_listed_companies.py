"""Read-only client for B3 Listed Companies structured public endpoints."""

from __future__ import annotations

import base64
import json
import re
from datetime import date
from typing import Any

import httpx

B3_LISTED_COMPANIES_BASE = (
    "https://sistemaswebb3-listados.b3.com.br/"
    "listedCompaniesProxy/CompanyCall"
)
B3_LISTED_COMPANIES_SOURCE = (
    "https://sistemaswebb3-listados.b3.com.br/listedCompaniesPage"
)
B3_LISTED_PAGE_SIZE = 120


class B3ListedCompaniesError(RuntimeError):
    """B3 returned an unavailable or invalid listed-company response."""


def b3_service_path(
    endpoint: str,
    parameters: dict[str, Any],
) -> str:
    encoded = base64.b64encode(
        json.dumps(
            parameters,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
    ).decode("ascii")
    return f"{endpoint}/{encoded}"


def issuer_code_from_ticker(ticker: str) -> str:
    code = re.sub(r"\d+$", "", ticker.strip().upper())
    if not code or code == ticker.strip().upper():
        raise B3ListedCompaniesError(
            f"ticker B3 sem codigo de emissor resolvivel: {ticker}"
        )
    return code


def parse_b3_date(value: Any) -> date:
    """Parse an ISO date or the B3 portal's en-US MM/DD/YYYY date."""
    text = str(value or "").strip()
    if not text:
        raise B3ListedCompaniesError("data B3 ausente")
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
            return date.fromisoformat(text)
        month, day, year = (int(part) for part in text.split("/"))
        return date(year, month, day)
    except ValueError as exc:
        raise B3ListedCompaniesError("data B3 invalida") from exc


class B3ListedCompaniesClient:
    """Client for the same structured routes used by B3's public portal."""

    def __init__(
        self,
        *,
        client: httpx.AsyncClient,
        base_url: str = B3_LISTED_COMPANIES_BASE,
        language: str = "en-US",
    ) -> None:
        self._client = client
        self._base_url = base_url.rstrip("/")
        self._language = language

    async def _get_json(self, endpoint: str, parameters: dict[str, Any]) -> Any:
        try:
            response = await self._client.get(
                f"{self._base_url}/{b3_service_path(endpoint, parameters)}",
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
            payload: Any = response.json()
            # The portal currently wraps some JSON responses as a JSON string
            # whose contents are the actual serialized array/object.
            for _ in range(2):
                if not isinstance(payload, str):
                    break
                payload = json.loads(payload)
            if isinstance(payload, str):
                raise B3ListedCompaniesError(
                    f"B3 endpoint {endpoint} retornou JSON encapsulado demais"
                )
            return payload
        except httpx.HTTPError as exc:
            raise B3ListedCompaniesError(
                f"B3 endpoint {endpoint} indisponÃ­vel"
            ) from exc
        except ValueError as exc:
            raise B3ListedCompaniesError(
                f"B3 endpoint {endpoint} retornou JSON invalido"
            ) from exc

    async def company_supplement(
        self,
        *,
        ticker: str,
        is_bdr: bool,
    ) -> dict[str, Any] | None:
        issuer_code = issuer_code_from_ticker(ticker)
        endpoint = (
            "GetListedSupplementBDR"
            if is_bdr
            else "GetListedSupplementCompany"
        )
        payload = await self._get_json(
            endpoint,
            {
                "issuingCompany": issuer_code,
                "language": self._language,
            },
        )
        if not isinstance(payload, list):
            raise B3ListedCompaniesError(
                f"B3 endpoint {endpoint} retornou formato nao suportado"
            )
        matches = [
            item
            for item in payload
            if isinstance(item, dict)
            and str(item.get("code") or "").strip().upper() == issuer_code
        ]
        if len(matches) > 1:
            raise B3ListedCompaniesError(
                f"B3 endpoint {endpoint} retornou emissor duplicado"
            )
        return matches[0] if matches else None

    async def cash_dividends(
        self,
        *,
        ticker: str,
        asset_type: str,
    ) -> tuple[dict[str, Any] | None, tuple[dict[str, Any], ...], str | None]:
        is_bdr = asset_type.strip().upper() == "BDR"
        supplement = await self.company_supplement(
            ticker=ticker,
            is_bdr=is_bdr,
        )
        if supplement is None:
            return None, (), "provider_no_coverage_issuer"

        if is_bdr:
            bdr_rows = supplement.get("cashDividends")
            if not isinstance(bdr_rows, list):
                raise B3ListedCompaniesError(
                    "suplemento B3 BDR sem lista cashDividends valida"
                )
            return supplement, tuple(
                row for row in bdr_rows if isinstance(row, dict)
            ), None

        trading_name = str(supplement.get("tradingName") or "").strip()
        trading_name = re.sub(r"[\s\-_/]+", "", trading_name).upper()
        if not trading_name:
            raise B3ListedCompaniesError(
                f"{ticker}: tradingName ausente no suplemento B3"
            )

        rows: list[dict[str, Any]] = []
        page_number = 1
        total_pages = 1
        while page_number <= total_pages:
            payload = await self._get_json(
                "GetListedCashDividends",
                {
                    "language": self._language,
                    "pageNumber": page_number,
                    "pageSize": B3_LISTED_PAGE_SIZE,
                    "tradingName": trading_name,
                },
            )
            if not isinstance(payload, dict):
                raise B3ListedCompaniesError(
                    "GetListedCashDividends retornou formato invÃ¡lido"
                )
            page = payload.get("page")
            page_rows = payload.get("results")
            if not isinstance(page, dict) or not isinstance(page_rows, list):
                raise B3ListedCompaniesError(
                    "GetListedCashDividends sem paginacao ou results"
                )
            current_page = int(page.get("pageNumber") or page_number)
            returned_size = int(page.get("pageSize") or B3_LISTED_PAGE_SIZE)
            if current_page != page_number or returned_size <= 0:
                raise B3ListedCompaniesError(
                    "GetListedCashDividends paginacao inconsistente"
                )
            total_pages = max(1, int(page.get("totalPages") or 1))
            rows.extend(row for row in page_rows if isinstance(row, dict))
            page_number += 1

        return supplement, tuple(rows), None

    async def corporate_actions(
        self,
        *,
        ticker: str,
        asset_type: str,
        expected_isin: str | None = None,
    ) -> tuple[dict[str, Any] | None, str | None]:
        is_bdr = asset_type.strip().upper() == "BDR"
        supplement = await self.company_supplement(
            ticker=ticker,
            is_bdr=is_bdr,
        )
        if supplement is None:
            return None, "provider_no_coverage_issuer"
        if expected_isin:
            official_isins = {
                str(row.get("isinCode") or "").strip().upper()
                for field in ("stockDividends", "subscriptions")
                for row in supplement.get(field, [])
                if isinstance(row, dict) and row.get("isinCode")
            }
            if official_isins and expected_isin.strip().upper() not in official_isins:
                raise B3ListedCompaniesError(
                    f"{ticker}: ISIN B3 nao corresponde ao ativo do catÃ¡logo"
                )
        for field in ("stockDividends", "subscriptions"):
            value = supplement.get(field)
            if not isinstance(value, list):
                raise B3ListedCompaniesError(
                    f"suplemento B3 sem lista {field} vÃ¡lida"
                )
        return supplement, None
