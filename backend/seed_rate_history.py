#!/usr/bin/env python
"""
seed_rate_history.py

Popula a tabela rate_history com 20 anos de historico de indicadores
macroeconomicos obtidos diretamente da API do Banco Central do Brasil (BCB).

Series utilizadas (BACEN SGS - Sistema Gerenciador de Series Temporais):
  CDI  diario  : serie 12   (taxa % a.d. - ex: 0.040830)
  SELIC diario : serie 11   (taxa % a.d.)
  IPCA mensal  : serie 433  (variacao % a.m. - ex: 0.44)

Uso:
  cd backend
  python seed_rate_history.py
  python seed_rate_history.py --start 2020-01-01   # seed parcial
  python seed_rate_history.py --dry-run            # sem gravar no banco
"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import date, datetime, timedelta
from decimal import Decimal
from math import prod
from typing import Optional

import httpx
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("seed_rate_history")

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
BCB_SGS_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{serie}/dados"
SERIES = {
    "CDI":   {"serie": 12,  "granularity": "daily"},
    "SELIC": {"serie": 11,  "granularity": "daily"},
    "IPCA":  {"serie": 433, "granularity": "monthly"},
}
DEFAULT_START = date(2006, 1, 1)  # 20 anos atras


# ---------------------------------------------------------------------------
# Busca BCB
# ---------------------------------------------------------------------------

def _fetch_bcb_series(
    serie: int,
    start: date,
    end: date,
) -> list[dict]:
    """
    Busca serie temporal do BCB SGS.
    Retorna lista de {data: 'DD/MM/YYYY', valor: '0.04083'}.
    """
    url = BCB_SGS_URL.format(serie=serie)
    params = {
        "formato": "json",
        "dataInicial": start.strftime("%d/%m/%Y"),
        "dataFinal": end.strftime("%d/%m/%Y"),
    }
    log.info("  Buscando serie %d de %s ate %s ...", serie, start, end)
    with httpx.Client(timeout=60.0) as client:
        resp = client.get(url, params=params)
        resp.raise_for_status()
    data = resp.json()
    log.info("  -> %d registros recebidos", len(data))
    return data


# ---------------------------------------------------------------------------
# Conversoes de taxa
# ---------------------------------------------------------------------------

def _daily_to_monthly(daily_pct: float) -> float:
    """Converte taxa diaria (% a.d.) para mensal (% a.m.) assumindo 21 d.u."""
    # formula: (1 + d/100)^21 - 1
    return ((1 + daily_pct / 100) ** 21 - 1) * 100


def _daily_to_annual(daily_pct: float) -> float:
    """Converte taxa diaria (% a.d.) para anual (% a.a.) assumindo 252 d.u."""
    return ((1 + daily_pct / 100) ** 252 - 1) * 100


def _monthly_to_daily(monthly_pct: float) -> float:
    """Converte taxa mensal (% a.m.) para diaria (% a.d.) assumindo 21 d.u."""
    return ((1 + monthly_pct / 100) ** (1 / 21) - 1) * 100


def _monthly_to_annual(monthly_pct: float) -> float:
    """Converte taxa mensal (% a.m.) para anual (% a.a.)."""
    return ((1 + monthly_pct / 100) ** 12 - 1) * 100


# ---------------------------------------------------------------------------
# Processamento por indicador
# ---------------------------------------------------------------------------

def _process_daily_series(
    raw: list[dict],
    indicator: str,
) -> list[dict]:
    """
    Processa serie de granularidade diaria do BCB.
    Cada item raw: {data: 'DD/MM/YYYY', valor: '0.04083'}
    Retorna lista de dicts prontos para upsert.
    """
    rows = []
    for item in raw:
        try:
            ref_date = datetime.strptime(item["data"], "%d/%m/%Y").date()
            daily = float(item["valor"].replace(",", "."))
        except (KeyError, ValueError) as e:
            log.warning("  [%s] item invalido: %s -> %s", indicator, item, e)
            continue

        rows.append({
            "indicator": indicator,
            "date": ref_date,
            "rate_daily": Decimal(str(round(daily, 8))),
            "rate_monthly": Decimal(str(round(_daily_to_monthly(daily), 8))),
            "rate_annual": Decimal(str(round(_daily_to_annual(daily), 4))),
            "source": "BCB",
        })
    return rows


def _process_monthly_series(
    raw: list[dict],
    indicator: str,
) -> list[dict]:
    """
    Processa serie de granularidade mensal do BCB (ex: IPCA).
    Cada item raw: {data: 'DD/MM/YYYY', valor: '0.44'}
    date sempre e o 1o dia do mes de referencia.
    Retorna lista de dicts prontos para upsert.
    """
    rows = []
    for item in raw:
        try:
            ref_date = datetime.strptime(item["data"], "%d/%m/%Y").date()
            # Normaliza para o primeiro dia do mes
            ref_date = ref_date.replace(day=1)
            monthly = float(item["valor"].replace(",", "."))
        except (KeyError, ValueError) as e:
            log.warning("  [%s] item invalido: %s -> %s", indicator, item, e)
            continue

        rows.append({
            "indicator": indicator,
            "date": ref_date,
            "rate_daily": Decimal(str(round(_monthly_to_daily(monthly), 8))),
            "rate_monthly": Decimal(str(round(monthly, 8))),
            "rate_annual": Decimal(str(round(_monthly_to_annual(monthly), 4))),
            "source": "BCB",
        })
    return rows


# ---------------------------------------------------------------------------
# Upsert no banco
# ---------------------------------------------------------------------------

UPSERT_SQL = text("""
    INSERT INTO rate_history (indicator, date, rate_daily, rate_monthly, rate_annual, source)
    VALUES (:indicator, :date, :rate_daily, :rate_monthly, :rate_annual, :source)
    ON CONFLICT (indicator, date)
    DO UPDATE SET
        rate_daily   = EXCLUDED.rate_daily,
        rate_monthly = EXCLUDED.rate_monthly,
        rate_annual  = EXCLUDED.rate_annual,
        source       = EXCLUDED.source
""")


def _upsert_rows(session: Session, rows: list[dict], dry_run: bool) -> int:
    if not rows:
        return 0
    if dry_run:
        log.info("  [dry-run] %d linhas seriam gravadas", len(rows))
        return len(rows)
    # Insere em lotes de 500 para evitar statements gigantes
    batch_size = 500
    total = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        session.execute(UPSERT_SQL, batch)
        total += len(batch)
    session.commit()
    return total


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Seed historico de taxas (CDI, IPCA, SELIC)")
    parser.add_argument(
        "--start",
        type=lambda s: datetime.strptime(s, "%Y-%m-%d").date(),
        default=DEFAULT_START,
        help="Data inicial (YYYY-MM-DD). Padrao: 20 anos atras.",
    )
    parser.add_argument(
        "--end",
        type=lambda s: datetime.strptime(s, "%Y-%m-%d").date(),
        default=date.today(),
        help="Data final (YYYY-MM-DD). Padrao: hoje.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Processa mas nao grava no banco.",
    )
    parser.add_argument(
        "--indicator",
        choices=["CDI", "SELIC", "IPCA", "ALL"],
        default="ALL",
        help="Qual indicador popular. Padrao: ALL.",
    )
    args = parser.parse_args()

    # Carrega DATABASE_URL do .env
    import os
    from dotenv import load_dotenv
    load_dotenv()
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        log.error("DATABASE_URL nao definida. Configure o .env.")
        sys.exit(1)

    # SQLAlchemy sync engine (seed e sincrono)
    engine = create_engine(db_url, echo=False)

    indicators_to_run = (
        list(SERIES.keys()) if args.indicator == "ALL"
        else [args.indicator]
    )

    log.info("=" * 60)
    log.info("seed_rate_history | start=%s end=%s dry_run=%s", args.start, args.end, args.dry_run)
    log.info("Indicadores: %s", indicators_to_run)
    log.info("=" * 60)

    total_inserted = 0

    with Session(engine) as session:
        for indicator in indicators_to_run:
            cfg = SERIES[indicator]
            log.info("\n[%s] serie BCB %d (granularidade: %s)", indicator, cfg["serie"], cfg["granularity"])

            try:
                raw = _fetch_bcb_series(cfg["serie"], args.start, args.end)
            except Exception as e:
                log.error("  ERRO ao buscar %s: %s", indicator, e)
                continue

            if cfg["granularity"] == "daily":
                rows = _process_daily_series(raw, indicator)
            else:
                rows = _process_monthly_series(raw, indicator)

            log.info("  Processados: %d registros", len(rows))

            inserted = _upsert_rows(session, rows, args.dry_run)
            total_inserted += inserted
            log.info("  Gravados/atualizados: %d", inserted)

    log.info("\n" + "=" * 60)
    log.info("Concluido. Total: %d registros", total_inserted)
    log.info("=" * 60)


if __name__ == "__main__":
    main()
