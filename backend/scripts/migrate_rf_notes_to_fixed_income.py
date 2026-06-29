"""
migrate_rf_notes_to_fixed_income.py

Script de migracao one-shot:
  Percorre TODAS as transacoes de RENDA_FIXA existentes no banco e
  popula a tabela fixed_income_investments com os dados estruturados,
  lendo indexador/taxa dos notes (unica vez justificada — migracao legado).

  Para cada ticker+portfolio_id:
    - Se ja existe registro em fixed_income_investments: SKIP (nao sobrescreve).
    - Se nao existe: cria com base no primeiro buy encontrado para esse ticker.

Uso:
  cd backend
  python -m scripts.migrate_rf_notes_to_fixed_income

  Flags opcionais:
    --dry-run   Apenas imprime o que seria feito, sem gravar no banco.
    --force     Sobrescreve registros existentes (use com cuidado).
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import re
import sys
from datetime import date
from decimal import Decimal
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Parser de notes (uso exclusivo da migracao legado)
# ---------------------------------------------------------------------------

class _RFMeta:
    def __init__(
        self,
        indexer_str: Optional[str] = None,
        rate: float = 0.0,
        maturity: Optional[date] = None,
        issuer: str = "",
        daily_liquidity: bool = False,
    ):
        self.indexer_str = indexer_str
        self.rate = rate
        self.maturity = maturity
        self.issuer = issuer
        self.daily_liquidity = daily_liquidity


def _parse_notes(notes: Optional[str]) -> _RFMeta:
    meta = _RFMeta()
    if not notes:
        return meta
    n = notes.strip()

    # Indexador
    m = re.search(r"Indexador:\s*([^|\-\n]+)", n, re.IGNORECASE)
    if m:
        meta.indexer_str = m.group(1).strip()

    # CDI+
    if re.search(r"CDI\s*\+", n, re.IGNORECASE):
        meta.indexer_str = meta.indexer_str or "CDI+"
        m2 = re.search(r"CDI\s*\+\s*([0-9]+(?:[.,][0-9]+)?)", n, re.IGNORECASE)
        if m2:
            meta.rate = float(m2.group(1).replace(",", "."))
    # % CDI
    elif re.search(r"[0-9]\s*%\s*(?:do\s+)?CDI", n, re.IGNORECASE):
        meta.indexer_str = meta.indexer_str or "CDI"
        m2 = re.search(r"([0-9]+(?:[.,][0-9]+)?)\s*%\s*(?:do\s+)?CDI", n, re.IGNORECASE)
        if m2:
            meta.rate = float(m2.group(1).replace(",", "."))
    # CDI sem percentual explícito
    elif re.search(r"\bCDI\b", n, re.IGNORECASE) and not meta.indexer_str:
        meta.indexer_str = "CDI"
        meta.rate = 100.0
    # IPCA+
    elif re.search(r"IPCA\s*\+", n, re.IGNORECASE):
        meta.indexer_str = meta.indexer_str or "IPCA+"
        m2 = re.search(r"IPCA\s*\+\s*([0-9]+(?:[.,][0-9]+)?)", n, re.IGNORECASE)
        if m2:
            meta.rate = float(m2.group(1).replace(",", "."))
    # IPCA puro
    elif re.search(r"\bIPCA\b", n, re.IGNORECASE) and not meta.indexer_str:
        meta.indexer_str = "IPCA+"
        meta.rate = 0.0
    # Prefixado
    elif re.search(r"prefixado", n, re.IGNORECASE):
        meta.indexer_str = meta.indexer_str or "Prefixado"
        m2 = re.search(r"([0-9]+(?:[.,][0-9]+)?)\s*%(?:\s*a\.?a\.?)?", n, re.IGNORECASE)
        if m2:
            meta.rate = float(m2.group(1).replace(",", "."))
    # Taxa % a.a. simples (Prefixado sem label)
    elif not meta.indexer_str:
        m2 = re.search(r"([0-9]+(?:[.,][0-9]+)?)\s*%\s*a\.?a\.?", n, re.IGNORECASE)
        if m2:
            meta.indexer_str = "Prefixado"
            meta.rate = float(m2.group(1).replace(",", "."))

    # Vencimento
    m = re.search(r"Vencimento:\s*([0-9]{4}-[0-9]{2}-[0-9]{2})", n)
    if m:
        try:
            meta.maturity = date.fromisoformat(m.group(1))
        except ValueError:
            pass

    # Emissor
    m = re.search(r"Emissor:\s*([^|\-\n]+)", n)
    if m:
        meta.issuer = m.group(1).strip()

    # Liquidez diária
    if re.search(r"Liquidez\s*Di", n, re.IGNORECASE):
        meta.daily_liquidity = True
        meta.maturity = None

    return meta


def _map_indexer(indexer_str: Optional[str]):
    """Mapeia string do notes para IndexerType."""
    from app.models.fixed_income import IndexerType
    if not indexer_str:
        return None
    s = indexer_str.strip().upper()
    mapping = {
        "CDI":       IndexerType.CDI,
        "CDI+":      IndexerType.CDI,       # CDI+ tratado como CDI no modelo (spread via rate)
        "IPCA":      IndexerType.IPCA_PLUS,
        "IPCA+":     IndexerType.IPCA_PLUS,
        "SELIC":     IndexerType.SELIC,
        "PREFIXADO": IndexerType.PREFIXADO,
        "IGP-M":     IndexerType.IGPM_PLUS,
        "IGPM":      IndexerType.IGPM_PLUS,
        "OUTRO":     None,
    }
    for key, val in mapping.items():
        if s.startswith(key):
            return val
    return None


# ---------------------------------------------------------------------------
# Logica principal
# ---------------------------------------------------------------------------

async def _run(dry_run: bool, force: bool) -> None:
    # Importacoes lazy para nao quebrar se script for rodado fora do contexto app
    from app.core.database import AsyncSessionLocal
    from app.models.transaction import Transaction, OperationType
    from app.models.fixed_income import (
        FixedIncomeInvestment,
        FixedIncomeType,
        IndexerType,
    )
    from sqlalchemy import select

    log.info("=" * 60)
    log.info("Migracao RF notes -> fixed_income_investments")
    log.info("dry_run=%s | force=%s", dry_run, force)
    log.info("=" * 60)

    async with AsyncSessionLocal() as db:
        # 1. Busca todas as transactions RF de compra ordenadas por data
        result = await db.execute(
            select(Transaction)
            .where(
                Transaction.asset_type.in_(["RENDA_FIXA", "renda_fixa"])
                | Transaction.asset_type.cast(str).ilike("%renda_fixa%")
            )
            .order_by(Transaction.portfolio_id, Transaction.ticker, Transaction.date.asc())
        )
        all_txs = result.scalars().all()

        if not all_txs:
            log.info("Nenhuma transacao RENDA_FIXA encontrada. Nada a migrar.")
            return

        # 2. Agrupa por (portfolio_id, ticker)
        groups: dict[tuple[int, str], list] = {}
        for tx in all_txs:
            op_val = tx.operation.value if hasattr(tx.operation, "value") else str(tx.operation)
            if op_val.lower() not in ("buy", "compra"):
                continue
            key = (tx.portfolio_id, tx.ticker.upper())
            groups.setdefault(key, []).append(tx)

        log.info("Grupos (portfolio_id, ticker) com compras RF: %d", len(groups))

        created = 0
        skipped = 0
        errors = 0

        for (portfolio_id, ticker), txs in groups.items():
            try:
                # 3. Verifica se ja existe registro
                existing = await db.execute(
                    select(FixedIncomeInvestment).where(
                        FixedIncomeInvestment.portfolio_id == portfolio_id,
                        FixedIncomeInvestment.name == ticker,
                    )
                )
                fi = existing.scalar_one_or_none()

                if fi is not None and not force:
                    log.debug("SKIP portfolio=%s ticker=%s (ja existe)", portfolio_id, ticker)
                    skipped += 1
                    continue

                # 4. Usa o primeiro buy com notes para extrair metadados
                meta: Optional[_RFMeta] = None
                first_tx = txs[0]
                for tx in txs:
                    if tx.notes:
                        parsed = _parse_notes(tx.notes)
                        if parsed.indexer_str:
                            meta = parsed
                            first_tx = tx
                            break

                if meta is None:
                    # Sem notes com indexador: tenta parse do primeiro mesmo assim
                    meta = _parse_notes(first_tx.notes)

                indexer = _map_indexer(meta.indexer_str if meta else None)

                if indexer is None:
                    log.warning(
                        "SKIP portfolio=%s ticker=%s — indexador nao identificado "
                        "(notes=%r)",
                        portfolio_id, ticker,
                        first_tx.notes,
                    )
                    skipped += 1
                    continue

                # 5. Calcula invested_amount como soma de todos os aportes
                invested_amount = sum(
                    float(tx.quantity or 0) * float(tx.price or 0) + float(tx.fees or 0)
                    for tx in txs
                )

                log.info(
                    "%s portfolio=%s ticker=%s indexer=%s rate=%s invested=%.2f maturity=%s",
                    "DRY-RUN" if dry_run else "CREATE" if fi is None else "UPDATE",
                    portfolio_id, ticker, indexer,
                    meta.rate if meta else 0,
                    invested_amount,
                    meta.maturity if meta else None,
                )

                if dry_run:
                    created += 1
                    continue

                if fi is None:
                    fi = FixedIncomeInvestment(
                        portfolio_id=portfolio_id,
                        name=ticker,
                        institution=meta.issuer if meta and meta.issuer else "",
                        fixed_income_type=FixedIncomeType.OUTROS,
                        indexer=indexer,
                        rate=Decimal(str(meta.rate if meta else 0)),
                        invested_amount=Decimal(str(round(invested_amount, 2))),
                        date_start=first_tx.date,
                        daily_liquidity=meta.daily_liquidity if meta else False,
                        date_maturity=meta.maturity if meta else None,
                        is_active=True,
                    )
                    db.add(fi)
                else:
                    # force=True: atualiza campos principais
                    fi.indexer = indexer
                    fi.rate = Decimal(str(meta.rate if meta else 0))
                    fi.invested_amount = Decimal(str(round(invested_amount, 2)))
                    fi.daily_liquidity = meta.daily_liquidity if meta else False
                    fi.date_maturity = meta.maturity if meta else None
                    if meta and meta.issuer:
                        fi.institution = meta.issuer

                created += 1

            except Exception as e:
                log.error(
                    "ERRO portfolio=%s ticker=%s: %s", portfolio_id, ticker, e
                )
                errors += 1

        if not dry_run:
            await db.commit()
            log.info("Commit realizado.")

    log.info("=" * 60)
    log.info(
        "Resultado: %s=%d | skipped=%d | errors=%d",
        "simulados" if dry_run else "gravados",
        created, skipped, errors,
    )
    log.info("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Migra dados RF de notes para fixed_income_investments."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Simula sem gravar no banco (padrao: False).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        default=False,
        help="Sobrescreve registros existentes (padrao: False).",
    )
    args = parser.parse_args()

    try:
        asyncio.run(_run(dry_run=args.dry_run, force=args.force))
    except KeyboardInterrupt:
        log.info("Interrompido pelo usuario.")
        sys.exit(0)
