"""Smoke HTTP descartável para o gate intermediário test_ready (#268).

Executa contra o backend real em http://127.0.0.1:8000, usando PostgreSQL e
migrations do ambiente local. Cria usuário/carteira fictícios exclusivos e
remove a conta ao final, inclusive quando um assert falha após autenticação.

Este smoke não autoriza dados reais e não executa seeds bloqueados.
"""
from __future__ import annotations

import asyncio
import secrets
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Awaitable, Callable

import httpx
from sqlalchemy import delete, select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import AsyncSessionLocal
from app.models.fx_rate import FxRate

BASE_URL = "http://127.0.0.1:8000"
SYNTHETIC_USD_BRL_RATE = Decimal("5.00000000")


def _require_status(response: httpx.Response, expected: int, step: str) -> None:
    if response.status_code != expected:
        raise AssertionError(
            f"{step}: HTTP {response.status_code}, esperado {expected}: "
            f"{response.text[:1000]}"
        )


def _require_ok(response: httpx.Response, step: str) -> None:
    if response.status_code < 200 or response.status_code >= 300:
        raise AssertionError(
            f"{step}: HTTP {response.status_code}: {response.text[:1000]}"
        )


async def _retry(
    action: Callable[[], Awaitable[httpx.Response]],
    *,
    expected: int,
    step: str,
    attempts: int = 60,
    delay_seconds: float = 2.0,
) -> httpx.Response:
    last_error: Exception | None = None
    last_response: httpx.Response | None = None
    for attempt in range(1, attempts + 1):
        try:
            response = await action()
            if response.status_code == expected:
                return response
            last_response = response
        except httpx.HTTPError as exc:
            last_error = exc
        if attempt < attempts:
            await asyncio.sleep(delay_seconds)
    if last_response is not None:
        _require_status(last_response, expected, step)
    assert last_error is not None
    raise AssertionError(f"{step}: backend indisponível após {attempts} tentativas") from last_error


async def _create_transaction(
    client: httpx.AsyncClient,
    *,
    headers: dict[str, str],
    portfolio_id: int,
    ticker: str,
    asset_type: str,
    quantity: float,
    price: float,
    tx_date: str,
    operation: str = "buy",
    notes: str | None = None,
) -> int:
    response = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/transactions",
        headers=headers,
        json={
            "ticker": ticker,
            "asset_type": asset_type,
            "operation": operation,
            "quantity": quantity,
            "price": price,
            "fees": 0.0,
            "date": tx_date,
            "currency": "BRL",
            "notes": notes,
        },
    )
    _require_status(response, 201, f"transaction {operation} {asset_type}/{ticker}")
    return int(response.json()["id"])


async def _ensure_synthetic_fx_rate() -> int | None:
    today = datetime.now(timezone.utc).date()
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(FxRate.id).where(
                FxRate.pair == "USD-BRL",
                FxRate.rate_date == today,
            )
        )
        if result.scalar_one_or_none() is not None:
            return None

        row = FxRate(
            pair="USD-BRL",
            rate_date=today,
            rate=SYNTHETIC_USD_BRL_RATE,
        )
        db.add(row)
        await db.commit()
        await db.refresh(row)
        return int(row.id)


async def _cleanup_synthetic_fx_rate(row_id: int | None) -> None:
    if row_id is None:
        return
    async with AsyncSessionLocal() as db:
        await db.execute(
            delete(FxRate).where(
                FxRate.id == row_id,
                FxRate.pair == "USD-BRL",
                FxRate.rate == SYNTHETIC_USD_BRL_RATE,
            )
        )
        await db.commit()
        print("TEST-READY-HTTP-SMOKE-FX-CLEANUP:PASS")


async def main() -> None:
    suffix = secrets.token_hex(6)
    email = f"test-ready-{suffix}@sgi.com"
    password = f"Smoke{suffix}#Aa1"
    headers: dict[str, str] = {}
    portfolio_id: int | None = None
    synthetic_fx_id: int | None = None

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=120.0) as client:
        try:
            await _retry(lambda: client.get("/health"), expected=200, step="health")
            synthetic_fx_id = await _ensure_synthetic_fx_rate()

            register = await client.post(
                "/api/v1/auth/register",
                json={
                    "name": "Test Ready Smoke",
                    "email": email,
                    "password": password,
                },
            )
            _require_status(register, 201, "register")
            access_token = register.json()["access_token"]
            headers = {"Authorization": f"Bearer {access_token}"}

            me = await client.get("/api/v1/users/me", headers=headers)
            _require_status(me, 200, "users/me")
            assert me.json()["email"] == email

            admin_bootstrap_status = await client.get(
                "/api/v1/admin/bootstrap/status",
                headers=headers,
            )
            _require_status(
                admin_bootstrap_status,
                403,
                "admin bootstrap status common user gate",
            )

            portfolio = await client.post(
                "/api/v1/portfolios/",
                headers=headers,
                json={
                    "name": f"Smoke {suffix}",
                    "description": "Carteira fictícia descartável do gate test_ready",
                },
            )
            _require_status(portfolio, 201, "create portfolio")
            portfolio_id = int(portfolio.json()["id"])

            get_portfolio = await client.get(
                f"/api/v1/portfolios/{portfolio_id}", headers=headers
            )
            _require_status(get_portfolio, 200, "get portfolio")

            now_utc = datetime.now(timezone.utc)
            tx_date = now_utc.date().isoformat()
            maturity = (now_utc.date() + timedelta(days=365)).isoformat()

            btc_tx_id: int | None = None
            btc_response = await client.post(
                f"/api/v1/portfolios/{portfolio_id}/transactions",
                headers=headers,
                json={
                    "ticker": "BTC",
                    "asset_type": "CRIPTO",
                    "operation": "buy",
                    "quantity": 0.001,
                    "price": 500000.0,
                    "fees": 0.0,
                    "date": tx_date,
                    "currency": "BRL",
                    "notes": "smoke test_ready",
                },
            )
            if btc_response.status_code == 201:
                btc_tx_id = int(btc_response.json()["id"])
            else:
                _require_status(btc_response, 422, "crypto BTC pre-catalog gate")

            for ticker in ("APT", "PUMP", "TAO", "XUSD"):
                blocked = await client.post(
                    f"/api/v1/portfolios/{portfolio_id}/transactions",
                    headers=headers,
                    json={
                        "ticker": ticker,
                        "asset_type": "CRIPTO",
                        "operation": "buy",
                        "quantity": 1.0,
                        "price": 100.0,
                        "fees": 0.0,
                        "date": tx_date,
                        "currency": "BRL",
                    },
                )
                _require_status(blocked, 422, f"blocked CRIPTO {ticker}")

            canonical_transactions = (
                ("SMKACAO3", "ACAO", 2.0, 10.0, None),
                ("SMKFII11", "FII", 1.0, 100.0, None),
                ("SMKETF11", "ETF_NACIONAL", 1.0, 50.0, None),
                ("SMKBDR34", "BDR", 1.0, 25.0, None),
                (
                    "SMKRF",
                    "RENDA_FIXA",
                    1.0,
                    1000.0,
                    (
                        "Indexador: CDI | 110% do CDI | "
                        f"Vencimento: {maturity} | Emissor: Banco Smoke"
                    ),
                ),
                (
                    "TESOURO SMOKE",
                    "TESOURO_DIRETO",
                    1.0,
                    1000.0,
                    (
                        "Indexador: SELIC | Taxa: 0% | "
                        f"Vencimento: {maturity} | Emissor: Tesouro Nacional"
                    ),
                ),
            )

            created_ids: list[int] = []
            for ticker, asset_type, quantity, price, notes in canonical_transactions:
                created_ids.append(
                    await _create_transaction(
                        client,
                        headers=headers,
                        portfolio_id=portfolio_id,
                        ticker=ticker,
                        asset_type=asset_type,
                        quantity=quantity,
                        price=price,
                        tx_date=tx_date,
                        notes=notes,
                    )
                )

            patch_target_id = btc_tx_id or created_ids[0]
            patch = await client.patch(
                f"/api/v1/portfolios/{portfolio_id}/transactions/{patch_target_id}",
                headers=headers,
                json={"notes": "smoke patch parcial"},
            )
            _require_status(patch, 200, "partial PATCH")
            assert patch.json()["notes"] == "smoke patch parcial"

            sell_tx_id = await _create_transaction(
                client,
                headers=headers,
                portfolio_id=portfolio_id,
                ticker="SMKACAO3",
                asset_type="ACAO",
                quantity=1.0,
                price=12.0,
                tx_date=tx_date,
                operation="sell",
                notes="smoke venda parcial",
            )

            disposable_tx_id = await _create_transaction(
                client,
                headers=headers,
                portfolio_id=portfolio_id,
                ticker="SMKDEL3",
                asset_type="ACAO",
                quantity=1.0,
                price=5.0,
                tx_date=tx_date,
                notes="smoke delete isolado",
            )

            transactions = await client.get(
                f"/api/v1/portfolios/{portfolio_id}/transactions",
                headers=headers,
            )
            _require_status(transactions, 200, "list transactions")
            expected_total = 2 + len(canonical_transactions) + int(btc_tx_id is not None)
            assert transactions.json()["total"] == expected_total
            assert any(
                item["id"] == sell_tx_id and item["operation"] == "sell"
                for item in transactions.json()["items"]
            )

            delete_response = await client.delete(
                f"/api/v1/portfolios/{portfolio_id}/transactions/{disposable_tx_id}",
                headers=headers,
            )
            _require_status(delete_response, 204, "delete isolated transaction")

            transactions_after_delete = await client.get(
                f"/api/v1/portfolios/{portfolio_id}/transactions",
                headers=headers,
            )
            _require_status(
                transactions_after_delete,
                200,
                "list transactions after delete",
            )
            assert transactions_after_delete.json()["total"] == expected_total - 1
            assert any(
                item["id"] == sell_tx_id and item["operation"] == "sell"
                for item in transactions_after_delete.json()["items"]
            )

            summary = await client.get(
                f"/api/v1/portfolios/{portfolio_id}/summary",
                headers=headers,
            )
            _require_status(summary, 200, "summary")
            assert summary.json()["summary_version"] == "summary.v2"

            positions = await client.get(
                f"/api/v1/portfolios/{portfolio_id}/positions",
                headers=headers,
            )
            _require_status(positions, 200, "positions")
            assert isinstance(positions.json(), list)

            rentabilidade_paths = (
                "kpis",
                "ativos",
                "classes",
                "reconciliation",
            )
            for suffix_path in rentabilidade_paths:
                response = await client.get(
                    f"/api/v1/portfolios/{portfolio_id}/rentabilidade/{suffix_path}",
                    headers=headers,
                )
                _require_ok(response, f"rentabilidade/{suffix_path}")

            dividends = await client.get(
                f"/api/v1/portfolios/{portfolio_id}/dividends",
                headers=headers,
            )
            _require_status(dividends, 200, "dividends")
            assert isinstance(dividends.json(), list)

            year = now_utc.year
            irpf = await client.get(
                f"/api/v1/irpf/{portfolio_id}/irpf/{year}/canonical",
                headers=headers,
            )
            _require_status(irpf, 200, "IRPF canonical")
            assert irpf.json()["schema_version"].startswith("irpf-")

            ready = await client.get("/ready")
            _require_status(ready, 503, "ready_for_real_data gate")
            assert ready.json()["ready_for_real_data"] is False

            print(
                "TEST-READY-HTTP-SMOKE:PASS "
                f"portfolio_id={portfolio_id} btc_tx_id={btc_tx_id} "
                f"sell_tx_id={sell_tx_id} canonical_transactions={len(canonical_transactions)}"
            )
        finally:
            if headers:
                cleanup = await client.delete("/api/v1/users/me", headers=headers)
                if cleanup.status_code != 200:
                    print(
                        "TEST-READY-HTTP-SMOKE-CLEANUP:WARN "
                        f"status={cleanup.status_code} body={cleanup.text[:500]}"
                    )
                else:
                    print("TEST-READY-HTTP-SMOKE-CLEANUP:PASS")
            await _cleanup_synthetic_fx_rate(synthetic_fx_id)


if __name__ == "__main__":
    asyncio.run(main())
