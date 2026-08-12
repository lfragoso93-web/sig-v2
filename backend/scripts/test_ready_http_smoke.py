"""Smoke HTTP descartável para o gate intermediário test_ready (#268).

Executa contra o backend real em http://127.0.0.1:8000, usando PostgreSQL e
migrations do ambiente local. Cria usuário/carteira fictícios exclusivos e
remove a conta ao final, inclusive quando um assert falha após autenticação.

Este smoke não autoriza dados reais e não executa seeds bloqueados.
"""
from __future__ import annotations

import asyncio
import secrets
from datetime import date

import httpx

BASE_URL = "http://127.0.0.1:8000"


def _require_status(response: httpx.Response, expected: int, step: str) -> None:
    if response.status_code != expected:
        raise AssertionError(
            f"{step}: HTTP {response.status_code}, esperado {expected}: "
            f"{response.text[:1000]}"
        )


async def main() -> None:
    suffix = secrets.token_hex(6)
    email = f"test-ready-{suffix}@sig.local"
    password = f"Smoke{suffix}#Aa1"
    headers: dict[str, str] = {}
    portfolio_id: int | None = None

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        try:
            health = await client.get("/health")
            _require_status(health, 200, "health")

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

            tx_date = date.today().isoformat()
            btc = await client.post(
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
            _require_status(btc, 201, "BTC transaction")
            btc_tx_id = int(btc.json()["id"])

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

            patch = await client.patch(
                f"/api/v1/portfolios/{portfolio_id}/transactions/{btc_tx_id}",
                headers=headers,
                json={"notes": "smoke patch parcial"},
            )
            _require_status(patch, 200, "partial PATCH")
            assert patch.json()["ticker"] == "BTC"
            assert patch.json()["notes"] == "smoke patch parcial"

            transactions = await client.get(
                f"/api/v1/portfolios/{portfolio_id}/transactions",
                headers=headers,
            )
            _require_status(transactions, 200, "list transactions")
            assert transactions.json()["total"] == 1

            print(
                "TEST-READY-HTTP-SMOKE-PHASE1:PASS "
                f"portfolio_id={portfolio_id} btc_tx_id={btc_tx_id}"
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


if __name__ == "__main__":
    asyncio.run(main())
