import logging
from datetime import date, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.transaction import Transaction, OperationType
from app.models.asset import Asset
from app.models.asset_dividend import AssetDividend
from app.models.dividend import Dividend, DividendStatus, DividendType

logger = logging.getLogger(__name__)

# Tipos que nao possuem proventos via API
SKIP_TYPES = {"CRIPTO", "TESOURO_DIRETO", "RENDA_FIXA"}

# Tipos internacionais (yfinance)
INTL_TYPES = {"STOCK", "ETF_INTERNACIONAL"}


def _next_business_day(d: date) -> date:
    """Retorna o proximo dia util simples (sab/dom)."""
    nxt = d + timedelta(days=1)
    while nxt.weekday() >= 5:
        nxt += timedelta(days=1)
    return nxt


def _calc_net_qty(txs: list[tuple], ref_date: date) -> float:
    """
    Calcula posicao liquida a partir de lista pre-carregada de (date, operation, quantity).
    Substitui _net_qty_on_date() que fazia SELECT por cada (portfolio, ex_date).
    """
    qty = 0.0
    for tx_date, op, q in txs:
        if tx_date > ref_date:
            continue
        op_str = op.value if isinstance(op, OperationType) else str(op).lower()
        if op_str == "buy":
            qty += float(q)
        elif op_str == "sell":
            qty -= float(q)
    return max(qty, 0.0)


async def _fetch_dividends_brapi(ticker: str) -> list[dict]:
    """Busca proventos do ticker via BRAPI."""
    try:
        from app.integrations.brapi import fetch_asset_info
        info = await fetch_asset_info(ticker)
        if not info:
            return []
        dividends_raw = info.get("dividendsData", {}) or {}
        cash_dividends = dividends_raw.get("cashDividends") or []
        return cash_dividends
    except Exception as e:
        logger.warning(f"[Backfill] BRAPI erro para {ticker}: {e}")
        return []


async def _fetch_dividends_yf(ticker: str) -> list[dict]:
    """Busca proventos do ticker via yfinance."""
    try:
        import asyncio
        from concurrent.futures import ThreadPoolExecutor

        def _sync():
            import yfinance as yf
            t = yf.Ticker(ticker)
            divs = t.dividends
            if divs.empty:
                return []
            return [
                {
                    "paymentDate": str(dt.date()),
                    "rate": float(val),
                    "type": "DIVIDENDO",
                }
                for dt, val in divs.items()
            ]

        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=1) as pool:
            return await loop.run_in_executor(pool, _sync)
    except Exception as e:
        logger.warning(f"[Backfill] yfinance erro para {ticker}: {e}")
        return []


def _parse_raw_dividend(raw: dict) -> Optional[tuple[Optional[date], date, Optional[date], float, str]]:
    """
    Parseia um item raw de provento.

    BRAPI cashDividends costuma trazer:
      - lastDatePrior: data com / ultimo dia negociado com direito
      - paymentDate: data de pagamento
      - rate/value: valor por unidade
      - type/dividendType: tipo de provento

    Algumas respostas tambem podem trazer exDate/ex_date. Quando nao houver data ex
    explicita, derivamos a data ex como o proximo dia util apos a data com.

    Retorna (record_date, ex_date, pay_date, value, div_type) ou None se invalido.
    """
    try:
        record_str = (
            raw.get("lastDatePrior")
            or raw.get("recordDate")
            or raw.get("dateCom")
            or raw.get("date_with")
            or ""
        )
        ex_str = (
            raw.get("exDate")
            or raw.get("ex_date")
            or raw.get("dateEx")
            or raw.get("date_ex")
            or ""
        )
        pay_str = raw.get("paymentDate") or raw.get("paidAt") or raw.get("payment_date") or ""

        record_date = date.fromisoformat(str(record_str)[:10]) if record_str else None
        if ex_str:
            ex_date = date.fromisoformat(str(ex_str)[:10])
        elif record_date:
            ex_date = _next_business_day(record_date)
        elif pay_str:
            # Fallback para provedores que so entregam uma data no evento.
            ex_date = date.fromisoformat(str(pay_str)[:10])
        else:
            return None

        pay_date = date.fromisoformat(str(pay_str)[:10]) if pay_str else None
        value = float(raw.get("rate") or raw.get("value") or raw.get("amount") or 0)
        if value <= 0:
            return None
        div_type = str(raw.get("type") or raw.get("dividendType") or "DIVIDENDO").upper()
        return record_date, ex_date, pay_date, value, div_type
    except Exception:
        return None


async def backfill_dividends(
    db: AsyncSession,
    portfolio_id: int,
    ticker: str,
    asset_type: str,
) -> None:
    """
    Ponto de entrada principal do backfill.
    Chamado pelo transactions.py apos cada insercao/edicao/exclusao de transacao
    e pelo seed/onboarding de ativos.

    Estrategia sem N+1:
      1. Busca proventos da API uma unica vez.
      2. Garante Asset e AssetDividend globais mesmo sem carteira com posicao.
      3. Pre-carrega carteiras/transacoes do ticker em memoria.
      4. Materializa Dividends por carteira apenas quando houver quantidade na data com.
    """
    if asset_type.upper() in SKIP_TYPES:
        logger.debug(f"[Backfill] {ticker} ({asset_type}) ignorado (SKIP_TYPES)")
        return

    logger.info(f"[Backfill] iniciando para {ticker} / portfolio {portfolio_id}")
    ticker = ticker.upper()
    asset_type_norm = asset_type.upper()

    # 1. Busca raw dividends da API (uma chamada)
    use_yf = asset_type_norm in INTL_TYPES
    raw_dividends = (
        await _fetch_dividends_yf(ticker)
        if use_yf
        else await _fetch_dividends_brapi(ticker)
    )
    if not raw_dividends:
        logger.info(f"[Backfill] nenhum provento encontrado para {ticker}")
        return

    # 2. Garante Asset global para salvar AssetDividends mesmo sem carteira.
    asset_result = await db.execute(
        select(Asset).where(
            Asset.ticker == ticker,
            Asset.asset_type == asset_type_norm,
        )
    )
    asset = asset_result.scalar_one_or_none()
    if asset is None:
        asset = Asset(
            ticker=ticker,
            name=ticker,
            asset_type=asset_type_norm,
            currency="USD" if asset_type_norm in INTL_TYPES else "BRL",
        )
        db.add(asset)
        await db.flush()

    # 3. Portfolios com o ticker (um SELECT). Pode ser vazio no seed global.
    pid_result = await db.execute(
        select(Transaction.portfolio_id)
        .where(Transaction.ticker == ticker)
        .distinct()
    )
    portfolio_ids = [row[0] for row in pid_result.all()]

    # 4. Pre-carrega transacoes do ticker para todos os portfolios (um SELECT)
    txs_by_portfolio: dict[int, list[tuple]] = {pid: [] for pid in portfolio_ids}
    if portfolio_ids:
        tx_result = await db.execute(
            select(
                Transaction.portfolio_id,
                Transaction.date,
                Transaction.operation,
                Transaction.quantity,
            ).where(
                Transaction.ticker == ticker,
                Transaction.portfolio_id.in_(portfolio_ids),
            )
        )
        for pid, tx_date, op, qty in tx_result.all():
            txs_by_portfolio[pid].append((tx_date, op, qty))

    # 5. Pre-carrega AssetDividends existentes para o ticker (um SELECT)
    ad_result = await db.execute(
        select(AssetDividend).where(AssetDividend.asset_id == asset.id)
    )
    existing_ads: dict[tuple[date, str], AssetDividend] = {
        (ad.ex_date, str(ad.dividend_type.value if hasattr(ad.dividend_type, "value") else ad.dividend_type)): ad
        for ad in ad_result.scalars().all()
    }

    # 6. Pre-carrega Dividends existentes para (portfolio_ids, ticker) (um SELECT)
    if portfolio_ids and existing_ads:
        ad_ids = [ad.id for ad in existing_ads.values()]
        div_result = await db.execute(
            select(Dividend).where(
                Dividend.portfolio_id.in_(portfolio_ids),
                Dividend.asset_dividend_id.in_(ad_ids),
            )
        )
        existing_divs: dict[tuple[int, int], Dividend] = {
            (d.portfolio_id, d.asset_dividend_id): d
            for d in div_result.scalars().all()
        }
    else:
        existing_divs = {}

    source = "yfinance" if use_yf else "brapi"

    # 7. Loop sobre proventos — sem queries adicionais
    for raw in raw_dividends:
        parsed = _parse_raw_dividend(raw)
        if parsed is None:
            continue
        record_date, ex_date, pay_date, value, div_type = parsed

        try:
            try:
                dividend_type = DividendType(div_type)
            except ValueError:
                dividend_type = DividendType.OUTROS

            # Upsert AssetDividend usando cache em memoria
            asset_key = (ex_date, dividend_type.value)
            asset_div = existing_ads.get(asset_key)
            if asset_div is None:
                asset_div = AssetDividend(
                    asset_id=asset.id,
                    record_date=record_date,
                    ex_date=ex_date,
                    payment_date=pay_date,
                    value_per_unit=value,
                    dividend_type=dividend_type,
                    source=source,
                )
                db.add(asset_div)
                await db.flush()  # obtem asset_div.id para usar como FK
                existing_ads[asset_key] = asset_div
            else:
                asset_div.record_date = record_date or asset_div.record_date
                asset_div.payment_date = pay_date
                asset_div.value_per_unit = value
                asset_div.source = source

            # Upsert Dividend por portfolio usando transacoes pre-carregadas
            div_type_str = dividend_type.value
            status = (
                DividendStatus.RECEBIDO
                if pay_date and pay_date <= date.today()
                else DividendStatus.A_RECEBER
            )

            # Para direito ao provento, a quantidade deve ser calculada na data com.
            # Se nao houver data com no provedor, usa data ex como fallback.
            entitlement_date = record_date or ex_date

            for pid in portfolio_ids:
                txs = txs_by_portfolio.get(pid, [])
                qty = _calc_net_qty(txs, entitlement_date)
                if qty <= 0:
                    continue

                total = qty * value
                net = total * 0.85 if "JCP" in div_type_str else total

                div = existing_divs.get((pid, asset_div.id))
                if div is None:
                    div = Dividend(
                        portfolio_id=pid,
                        asset_dividend_id=asset_div.id,
                        quantity=qty,
                        total_value=total,
                        net_value=net,
                        status=status,
                        ticker=ticker,
                        ex_date=ex_date,
                        payment_date=pay_date,
                        value_per_unit=value,
                        total_received=total,
                        dividend_type=div_type_str,
                    )
                    db.add(div)
                    existing_divs[(pid, asset_div.id)] = div
                else:
                    div.quantity = qty
                    div.total_value = total
                    div.net_value = net
                    div.status = status
                    div.ticker = ticker
                    div.ex_date = ex_date
                    div.payment_date = pay_date
                    div.value_per_unit = value
                    div.total_received = total
                    div.dividend_type = div_type_str

        except Exception as e:
            logger.warning(f"[Backfill] erro ao processar provento de {ticker} ex={ex_date}: {e}")
            continue

    await db.commit()
    logger.info(f"[Backfill] concluido para {ticker} / portfolio {portfolio_id}")


async def backfill_all_tickers(
    db: AsyncSession,
    portfolio_id: int,
    tickers: list[tuple[str, str]],
) -> list[str]:
    """
    Dispara backfill para uma lista de (ticker, asset_type).
    Usado pelo endpoint POST /dividends/sync.
    """
    queued = []
    for ticker, asset_type in tickers:
        if asset_type.upper() in SKIP_TYPES:
            continue
        await backfill_dividends(db, portfolio_id, ticker, asset_type)
        queued.append(ticker)
    return queued


async def run_backfill(
    db: AsyncSession,
    ticker: str,
    asset_type,
) -> None:
    """
    Alias usado pelo asset_onboarding_service e pelo seed.
    Chama backfill_dividends sem portfolio_id especifico (usa portfolio_id=0
    pois backfill_dividends busca todos os portfolios do ticker internamente).
    """
    asset_type_str = asset_type.value if hasattr(asset_type, 'value') else str(asset_type)
    await backfill_dividends(db, portfolio_id=0, ticker=ticker, asset_type=asset_type_str)
