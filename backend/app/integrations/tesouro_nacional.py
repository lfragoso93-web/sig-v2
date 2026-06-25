"""
tesouro_nacional.py

Integrador com a API publica do Tesouro Nacional (STN).
Usado como FALLBACK quando a BRAPI nao retorna preco para um titulo.

Fontes:
  1. Precos em tempo real (disponivel):
     https://www.tesourodireto.com.br/json/br/com/b3/tesourodireto/model/dto/public/yieldedBonds.json
     Sem autenticacao. Retorna todos os titulos disponiveis com buyPrice/sellPrice.

  2. Historico completo (CSV publico via Tesouro Transparente):
     https://www.tesourotransparente.gov.br/ckan/dataset/taxa-dos-titulos-ofertados-pelo-tesouro-direto
     Planilha com precos e taxas desde 2002 para todos os titulos.

Normalizacao de nomes:
  A STN usa nomes longos como "Tesouro Renda+ Aposentadoria Extra 2065".
  _normalize_tn_name() converte qualquer variacao do usuario para um
  slug comparavel, permitindo match fuzzy com os nomes da API da STN.
"""
import logging
import re
import time
from datetime import date, datetime, timezone
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# URL da API publica da STN - precos em tempo real
_TN_BONDS_URL = (
    "https://www.tesourodireto.com.br/json/br/com/b3/tesourodireto"
    "/model/dto/public/yieldedBonds.json"
)

# URL do CSV historico (Tesouro Transparente)
_TN_HIST_CSV_URL = (
    "https://www.tesourotransparente.gov.br/ckan/dataset/"
    "taxa-dos-titulos-ofertados-pelo-tesouro-direto/resource/"
    "796d2059-14e9-44e3-80a7-2dff9d4d4b5f/download/"
    "PrecoTaxaTesouroDireto.csv"
)

# Cache em memoria do catalogo TN: {slug_norm: {"name": str, "buyPrice": float, ...}}
# Expira a cada 15 minutos (preco muda durante o dia)
_TN_CACHE: dict = {}
_TN_CACHE_EXPIRES: float = 0.0
_TN_CACHE_TTL = 900.0  # 15 minutos


def _slug_tn(s: str) -> str:
    """
    Normaliza um nome de titulo TN para comparacao fuzzy.
    Remove acentos, pontuacao, converte para minusculas e colapsa espacos.

    Ex:
      'Tesouro RendA+ Aposentadoria Extra 2065'  -> 'tesouro renda aposentadoria extra 2065'
      'TESOURO RENDA+ 2065'                      -> 'tesouro renda 2065'
      'tesouro-renda-mais-2065'                  -> 'tesouro renda mais 2065'
    """
    s = s.lower().strip()
    # Remove acentos simples
    for src, dst in [
        ("a+", "a"), ("renda+", "renda"), ("educa+", "educa"), ("ipca+", "ipca"),
        ("a\u0301", "a"), ("e\u0301", "e"), ("i\u0301", "i"), ("o\u0301", "o"), ("u\u0301", "u"),
        ("\xe3", "a"), ("\xe9", "e"), ("\xed", "i"), ("\xf3", "o"), ("\xfa", "u"),
        ("\xe0", "a"), ("\xe2", "a"), ("\xea", "e"), ("\xf4", "o"),
        ("\xc3", "a"), ("\xc9", "e"), ("\xcd", "i"), ("\xd3", "o"), ("\xda", "u"),
    ]:
        s = s.replace(src, dst)
    # Hifens viram espacos
    s = s.replace("-", " ")
    # Remove caracteres especiais exceto espacos e digitos
    s = re.sub(r"[^a-z0-9\s]", "", s)
    # Colapsa multiplos espacos
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _score_match(user_slug: str, tn_slug: str) -> int:
    """
    Pontua a similaridade entre dois slugs normalizados.
    Retorna 0-100. >= 60 e considerado match.

    Criterios:
      - Slug do usuario contido no slug TN: +50
      - Todos os tokens do usuario presentes no slug TN: +40
      - Ano presente nos dois: +10
    """
    score = 0
    if user_slug in tn_slug:
        score += 50
    user_tokens = set(user_slug.split())
    tn_tokens   = set(tn_slug.split())
    common = user_tokens & tn_tokens
    if user_tokens and len(common) / len(user_tokens) >= 0.8:
        score += 40
    # Bonus se o ano bater
    user_year = re.search(r"\b(20\d{2})\b", user_slug)
    tn_year   = re.search(r"\b(20\d{2})\b", tn_slug)
    if user_year and tn_year and user_year.group() == tn_year.group():
        score += 10
    return score


async def _load_tn_catalog() -> dict:
    """
    Carrega (e cacheia 15min) o catalogo completo da API da STN.
    Retorna: { slug_norm: { name, buyPrice, sellPrice, maturityDate, annualRate } }
    """
    global _TN_CACHE, _TN_CACHE_EXPIRES

    now = time.monotonic()
    if _TN_CACHE and now < _TN_CACHE_EXPIRES:
        return _TN_CACHE

    catalog: dict = {}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(_TN_BONDS_URL, headers={
                "User-Agent": "Mozilla/5.0 (compatible; SIG-v2/1.0)",
                "Accept": "application/json, text/plain, */*",
                "Referer": "https://www.tesourodireto.com.br/",
            })
            resp.raise_for_status()
            data = resp.json()

        # Estrutura esperada: { "response": { "TrsrBdTradgList": [ { "TrsrBd": {...} } ] } }
        response = data.get("response") or data
        bond_list = (
            response.get("TrsrBdTradgList")
            or response.get("bonds")
            or response.get("treasuries")
            or (data if isinstance(data, list) else [])
        )

        for entry in bond_list:
            bond = entry.get("TrsrBd") or entry
            if not isinstance(bond, dict):
                continue

            # Nome oficial completo da STN
            name = (
                bond.get("nm")
                or bond.get("name")
                or bond.get("bondType")
                or ""
            ).strip()

            buy_price = (
                bond.get("untrInvstmtVal")
                or bond.get("minInvstmtAmt")
                or bond.get("buyPrice")
                or bond.get("BuyPric")
            )
            sell_price = (
                bond.get("SellPric")
                or bond.get("sellPrice")
            )
            maturity = (
                bond.get("mtrtyDt")
                or bond.get("maturityDate")
                or bond.get("MtrtyDt")
            )
            annual_rate = (
                bond.get("anulInvstmtRate")
                or bond.get("annualRate")
                or bond.get("AnulInvstmtRate")
            )

            if not name or buy_price is None:
                continue

            slug = _slug_tn(name)
            catalog[slug] = {
                "name":        name,
                "buyPrice":    float(buy_price),
                "sellPrice":   float(sell_price) if sell_price else None,
                "maturityDate": str(maturity) if maturity else None,
                "annualRate":  float(annual_rate) if annual_rate else None,
            }

        logger.info("[TN] catalogo carregado: %d titulos", len(catalog))

    except Exception as e:
        logger.warning("[TN] _load_tn_catalog erro: %s", e)

    if catalog:
        _TN_CACHE = catalog
        _TN_CACHE_EXPIRES = now + _TN_CACHE_TTL

    return catalog


def _find_best_match(
    ticker: str,
    catalog: dict,
    min_score: int = 60,
) -> Optional[dict]:
    """
    Encontra o melhor match no catalogo TN para um ticker do usuario.
    Retorna o dict do titulo com maior score >= min_score, ou None.
    """
    user_slug = _slug_tn(ticker)
    best_score = 0
    best_item  = None

    for tn_slug, item in catalog.items():
        score = _score_match(user_slug, tn_slug)
        if score > best_score:
            best_score = score
            best_item  = item

    if best_score >= min_score and best_item:
        logger.info(
            "[TN] match: %r -> %r (score=%d)",
            ticker, best_item["name"], best_score,
        )
        return best_item

    logger.warning(
        "[TN] sem match para %r (melhor score=%d, threshold=%d)",
        ticker, best_score, min_score,
    )
    return None


async def fetch_tn_prices(tickers: list[str]) -> dict[str, float]:
    """
    Busca precos atuais (buyPrice) para uma lista de tickers de Tesouro Direto
    usando a API publica da STN.

    Retorna { ticker_original: preco_float } para os tickers encontrados.
    Tickers sem match sao omitidos (nao levantam excecao).
    """
    if not tickers:
        return {}

    catalog = await _load_tn_catalog()
    if not catalog:
        logger.warning("[TN] fetch_tn_prices: catalogo vazio, sem fallback disponivel")
        return {}

    results: dict[str, float] = {}
    for ticker in tickers:
        match = _find_best_match(ticker, catalog)
        if match:
            results[ticker] = match["buyPrice"]

    return results


async def fetch_tn_catalog_full() -> list[dict]:
    """
    Retorna a lista completa de titulos disponiveis na STN com metadados.
    Util para popular sugestoes no frontend ao lancar um Tesouro.

    Cada item: { name, buyPrice, sellPrice, maturityDate, annualRate }
    """
    catalog = await _load_tn_catalog()
    return list(catalog.values())


async def fetch_tn_price_by_date(
    ticker: str,
    date_str: str,
) -> Optional[float]:
    """
    Busca o preco historico de um titulo na data especificada via CSV
    do Tesouro Transparente.

    Usa o CSV publico que cobre precos e taxas desde 2002.
    Retorna o preco de compra (Pu Compra Manha) mais proximo da data.
    """
    try:
        import io
        import csv

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(_TN_HIST_CSV_URL)
            resp.raise_for_status()
            # O CSV da STN usa encoding latin-1 e separador ;
            content = resp.content.decode("latin-1", errors="replace")

        user_slug  = _slug_tn(ticker)
        target     = date.fromisoformat(date_str)
        best_price: Optional[float] = None
        best_delta: Optional[int]   = None

        reader = csv.DictReader(
            io.StringIO(content),
            delimiter=";",
        )
        for row in reader:
            # Coluna do nome do titulo (varia entre versoes do CSV)
            bond_name = (
                row.get("Tipo Titulo")
                or row.get("Titulo")
                or row.get("Nome Titulo")
                or ""
            ).strip()
            if not bond_name:
                continue

            tn_slug = _slug_tn(bond_name)
            if _score_match(user_slug, tn_slug) < 60:
                continue

            # Data da linha
            raw_date = (
                row.get("Data Vencimento")
                or row.get("Data Base")
                or row.get("Data")
                or ""
            ).strip()
            if not raw_date:
                continue
            try:
                # Formato do CSV: DD/MM/YYYY
                parts = raw_date.split("/")
                if len(parts) == 3:
                    row_date = date(int(parts[2]), int(parts[1]), int(parts[0]))
                else:
                    row_date = date.fromisoformat(raw_date[:10])
            except ValueError:
                continue

            delta = abs((row_date - target).days)
            if best_delta is None or delta < best_delta:
                # Preco de compra
                raw_price = (
                    row.get("Pu Compra Manha")
                    or row.get("PU Compra")
                    or row.get("Preco")
                    or ""
                ).strip().replace(".", "").replace(",", ".")
                try:
                    p = float(raw_price)
                    if p > 0:
                        best_price = p
                        best_delta = delta
                except ValueError:
                    pass

        if best_price:
            logger.info(
                "[TN] fetch_tn_price_by_date: %r em %s -> %.2f (delta=%d dias)",
                ticker, date_str, best_price, best_delta or 0,
            )
        else:
            logger.warning("[TN] fetch_tn_price_by_date: sem preco para %r em %s", ticker, date_str)

        return best_price

    except Exception as e:
        logger.warning("[TN] fetch_tn_price_by_date erro para %r em %s: %s", ticker, date_str, e)
        return None
