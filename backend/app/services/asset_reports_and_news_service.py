"""Serviço de Relatórios Gerenciais (FNet CVM/B3 e ITR/DFP B3) e Notícias Externas por Ativo.

Fontes oficiais utilizadas:
1. FIIs (Relatórios Gerenciais, Informes Mensais, Avisos aos Cotistas):
   - Sistema Fundos.NET (B3 / CVM):
     `https://fnet.bmfbovespa.com.br/fnet/publico/pesquisarGerenciadorDocumentosDados`
   - Download/Visualização direta de PDF:
     `https://fnet.bmfbovespa.com.br/fnet/publico/exibirDocumento?id={doc_id}&cvm=true`
   - Extração de resumo textual do PDF do último Relatório Gerencial via `pypdf` para
     confronto analítico pela IA.

2. Ações e BDRs (ITR, DFP, FRE, FCA):
   - Portal B3 Empresas Listadas (`GetListedSupplementCompany` + `GetListStructuredReports`):
     `https://sistemaswebb3-listados.b3.com.br/listedCompaniesProxy/CompanyCall/GetListStructuredReports/{base64}`

3. Notícias Externas do Ativo:
   - Ativos Internacionais (`STOCK` / `ETF_INTERNACIONAL`): Finnhub `/company-news` + Google News RSS fallback.
   - Ativos Brasileiros e Gerais (`ACAO`, `FII`, `BDR`, `ETF_NACIONAL`, `CRIPTO`):
     Google News RSS (`https://news.google.com/rss/search`) filtrado por ticker e nome da companhia/fundo.
"""
from __future__ import annotations

import asyncio
import io
import json
import logging
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Optional
from urllib.parse import quote_plus

import httpx

from app.core.cache import get_redis
from app.core.log_safety import sanitize_log_value
from app.core.provider_registry import ProviderId, get_runtime_provider_key
from app.integrations.b3_listed_companies import (
    B3ListedCompaniesClient,
    b3_service_path,
    B3_LISTED_COMPANIES_BASE,
)

logger = logging.getLogger(__name__)

FNET_BASE_URL = "https://fnet.bmfbovespa.com.br/fnet/publico"
GOOGLE_NEWS_RSS_URL = "https://news.google.com/rss/search"
FINNHUB_NEWS_URL = "https://finnhub.io/api/v1/company-news"

TTL_REPORTS_SECONDS = 21600      # 6 horas para relatórios CVM/B3/FNet
TTL_REPORT_TEXT_SECONDS = 86400  # 24 horas para texto extraído de PDF
TTL_NEWS_SECONDS = 3600          # 1 hora para notícias externas
TTL_EMPTY_SECONDS = 900          # 15 minutos de cooldown para resultados vazios

# Mapa curado de CNPJs dos principais FIIs da B3 para resolução instantânea mesmo sem cache prévio
CURATED_FII_CNPJS: dict[str, str] = {
    "MXRF11": "97521225000125",
    "HGLG11": "11728688000147",
    "KNRI11": "12005956000165",
    "XPLG11": "26502794000185",
    "XPML11": "28757546000100",
    "VISC11": "17554274000185",
    "KNIP11": "24960430000113",
    "KNCR11": "16706958000132",
    "BTLG11": "11839593000109",
    "HGRU11": "29641226000153",
    "BCFF11": "11026627000138",
    "BRCO11": "20748515000181",
    "IRDM11": "28830325000110",
    "CPTS11": "18979895000113",
    "HGBS11": "08431747000106",
    "VILG11": "24853044000122",
    "LVBI11": "30629603000118",
    "PVBI11": "35652102000176",
    "TGAR11": "25032881000153",
    "RECR11": "28152272000107",
    "VRTA11": "11664201000100",
    "HGCR11": "11160521000122",
    "RZTR11": "36501128000186",
    "KNSC11": "35864448000138",
    "GARE11": "37295919000160",
    "TRXF11": "28548288000152",
    "ALZR11": "28737771000185",
    "MALL11": "26499833000188",
    "HSML11": "32892018000131",
    "JSRE11": "13125917000192",
}


def _digits_only(value: Optional[str]) -> str:
    if not value:
        return ""
    return re.sub(r"\D+", "", str(value))


def _parse_br_or_iso_date(value: Any) -> Optional[str]:
    """Normaliza datas DD/MM/YYYY, MM/DD/YYYY ou YYYY-MM-DD para ISO YYYY-MM-DD."""
    raw = str(value or "").strip()
    if not raw:
        return None
    raw_part = raw.split(" ")[0].split("T")[0]
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw_part):
        return raw_part
    if re.fullmatch(r"\d{2}/\d{2}/\d{4}", raw_part):
        p1, p2, year = (int(x) for x in raw_part.split("/"))
        # Se p1 > 12, é DD/MM/YYYY; no FNet é sempre DD/MM/YYYY
        if p1 > 12:
            return f"{year:04d}-{p2:02d}-{p1:02d}"
        return f"{year:04d}-{p2:02d}-{p1:02d}"
    if re.fullmatch(r"\d{2}/\d{4}", raw_part):
        month, year = (int(x) for x in raw_part.split("/"))
        if 1 <= month <= 12:
            return f"{year:04d}-{month:02d}-01"
    return raw_part


class AssetReportsAndNewsService:
    """Busca e mantém em cache relatórios gerenciais/estruturados e notícias de mercado."""

    def __init__(self) -> None:
        self._memory_cache: dict[str, tuple[float, Any]] = {}

    async def _get_cached(self, key: str) -> Optional[Any]:
        now = time.time()
        if key in self._memory_cache:
            expires_at, val = self._memory_cache[key]
            if now < expires_at:
                return val
            del self._memory_cache[key]

        redis_client = await get_redis()
        if redis_client is not None:
            try:
                raw = await redis_client.get(key)
                if raw:
                    parsed = json.loads(raw)
                    self._memory_cache[key] = (now + 300, parsed)
                    return parsed
            except Exception:
                pass
        return None

    async def _set_cached(self, key: str, val: Any, ttl_seconds: int) -> None:
        self._memory_cache[key] = (time.time() + ttl_seconds, val)
        redis_client = await get_redis()
        if redis_client is not None:
            try:
                await redis_client.set(key, json.dumps(val), ex=ttl_seconds)
            except Exception:
                pass

    # -------------------------------------------------------------------------
    # 1. Relatórios Gerenciais de FIIs (FNet B3/CVM)
    # -------------------------------------------------------------------------

    async def _resolve_fii_cnpj(
        self,
        ticker: str,
        enrichment: Optional[dict[str, Any]] = None,
    ) -> str:
        clean_ticker = ticker.strip().upper()
        if enrichment and isinstance(enrichment.get("fii_indicators"), dict):
            raw_cnpj = enrichment["fii_indicators"].get("cnpj")
            digits = _digits_only(raw_cnpj)
            if len(digits) == 14:
                return digits

        if clean_ticker in CURATED_FII_CNPJS:
            return CURATED_FII_CNPJS[clean_ticker]

        # Tenta buscar via asset_enrichment_service (Brapi v2 FII indicators)
        try:
            from app.services.asset_enrichment_service import asset_enrichment_service

            dto = await asset_enrichment_service.get_fii_indicators(clean_ticker)
            if dto and dto.cnpj:
                digits = _digits_only(dto.cnpj)
                if len(digits) == 14:
                    return digits
        except Exception:
            pass
        return ""

    async def fetch_fii_reports(
        self,
        ticker: str,
        enrichment: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, Any]]:
        clean_ticker = ticker.strip().upper()
        cache_key = f"asset_reports:fii:v1:{clean_ticker}"
        cached = await self._get_cached(cache_key)
        if isinstance(cached, list):
            return cached

        cnpj = await self._resolve_fii_cnpj(clean_ticker, enrichment)
        if not cnpj:
            return []

        params = {
            "d": "1",
            "s": "0",
            "l": "25",
            "o[0][dataEntrega]": "desc",
            "cnpjFundo": cnpj,
            "situacao": "A",
        }
        headers = {
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (compatible; SGI/2.0; +https://investimentos.r2ar.com.br)",
        }

        reports: list[dict[str, Any]] = []
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(
                    f"{FNET_BASE_URL}/pesquisarGerenciadorDocumentosDados",
                    params=params,
                    headers=headers,
                )
                if resp.status_code == 200:
                    payload = resp.json()
                    rows = payload.get("data") if isinstance(payload, dict) else []
                    if isinstance(rows, list):
                        for row in rows:
                            if not isinstance(row, dict):
                                continue
                            doc_id = row.get("id")
                            if not doc_id:
                                continue
                            category = str(row.get("categoriaDocumento") or "Documento").strip()
                            tipo_doc = str(row.get("tipoDocumento") or "").strip()
                            especie = str(row.get("especieDocumento") or "").strip()
                            title = tipo_doc or especie or category
                            ref_date = _parse_br_or_iso_date(row.get("dataReferencia"))
                            deliv_date = _parse_br_or_iso_date(row.get("dataEntrega"))
                            is_management = (
                                "gerencial" in title.lower()
                                or "gerencial" in category.lower()
                            )
                            view_url = f"{FNET_BASE_URL}/exibirDocumento?id={doc_id}&cvm=true"
                            download_url = f"{FNET_BASE_URL}/downloadDocumento?id={doc_id}"
                            reports.append({
                                "id": str(doc_id),
                                "title": title,
                                "category": category,
                                "reference_date": ref_date or str(row.get("dataReferencia") or ""),
                                "delivery_date": deliv_date or str(row.get("dataEntrega") or ""),
                                "status": str(row.get("descricaoStatus") or "Ativo"),
                                "version": row.get("versao"),
                                "fund_name": str(row.get("descricaoFundo") or "").strip(),
                                "source": "CVM / B3 Fundos.NET",
                                "url": view_url,
                                "download_url": download_url,
                                "is_management_report": is_management,
                            })
        except Exception as exc:
            logger.warning(
                "Falha ao consultar relatórios FNet para %s: %s",
                sanitize_log_value(clean_ticker),
                sanitize_log_value(exc),
            )

        # Prioriza Relatórios Gerenciais e Informes Mensais no topo, mantendo ordem cronológica
        reports.sort(
            key=lambda r: (
                1 if r.get("is_management_report") else 0,
                str(r.get("delivery_date") or ""),
            ),
            reverse=True,
        )
        final_reports = reports[:15]
        await self._set_cached(
            cache_key,
            final_reports,
            TTL_REPORTS_SECONDS if final_reports else TTL_EMPTY_SECONDS,
        )
        return final_reports

    async def extract_latest_fii_report_excerpt(
        self,
        ticker: str,
        reports: list[dict[str, Any]],
    ) -> Optional[dict[str, Any]]:
        """Baixa e extrai o texto principal do último Relatório Gerencial em PDF via pypdf."""
        clean_ticker = ticker.strip().upper()
        mgmt_reports = [r for r in reports if r.get("is_management_report")]
        target = mgmt_reports[0] if mgmt_reports else (reports[0] if reports else None)
        if not target or not target.get("id"):
            return None

        doc_id = str(target["id"])
        cache_key = f"asset_report_excerpt:v1:{clean_ticker}:{doc_id}"
        cached = await self._get_cached(cache_key)
        if isinstance(cached, dict):
            return cached

        try:
            from pypdf import PdfReader

            async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
                resp = await client.get(
                    f"{FNET_BASE_URL}/exibirDocumento",
                    params={"id": doc_id, "cvm": "true"},
                    headers={"User-Agent": "Mozilla/5.0 (compatible; SGI/2.0)"},
                )
                if resp.status_code != 200 or not resp.content.startswith(b"%PDF"):
                    return None

                def _parse_pdf(pdf_bytes: bytes) -> tuple[int, str]:
                    reader = PdfReader(io.BytesIO(pdf_bytes))
                    num_pages = len(reader.pages)
                    pages_text: list[str] = []
                    for idx in range(min(4, num_pages)):
                        page_txt = reader.pages[idx].extract_text() or ""
                        cleaned = re.sub(r"\s+", " ", page_txt).strip()
                        if cleaned:
                            pages_text.append(cleaned)
                    return num_pages, " ".join(pages_text)[:3200]

                pages_count, extracted_text = await asyncio.to_thread(_parse_pdf, resp.content)
                if not extracted_text:
                    return None

                excerpt_payload = {
                    "document_id": doc_id,
                    "title": target.get("title") or "Relatório Gerencial",
                    "reference_date": target.get("reference_date"),
                    "delivery_date": target.get("delivery_date"),
                    "pages_count": pages_count,
                    "url": target.get("url"),
                    "excerpt": extracted_text,
                }
                await self._set_cached(cache_key, excerpt_payload, TTL_REPORT_TEXT_SECONDS)
                return excerpt_payload
        except Exception as exc:
            logger.debug(
                "Não foi possível extrair texto do PDF FNet %s (%s): %s",
                sanitize_log_value(clean_ticker),
                sanitize_log_value(doc_id),
                sanitize_log_value(exc),
            )
            return None

    # -------------------------------------------------------------------------
    # 2. Relatórios Estruturados de Ações / BDRs (ITR, DFP, FRE, FCA na B3/CVM)
    # -------------------------------------------------------------------------

    async def fetch_company_reports(
        self,
        ticker: str,
        asset_type: str = "ACAO",
    ) -> list[dict[str, Any]]:
        clean_ticker = ticker.strip().upper()
        cache_key = f"asset_reports:company:v1:{clean_ticker}"
        cached = await self._get_cached(cache_key)
        if isinstance(cached, list):
            return cached

        is_bdr = asset_type.strip().upper() == "BDR" or clean_ticker.endswith(("34", "35"))
        reports: list[dict[str, Any]] = []
        try:
            async with httpx.AsyncClient(timeout=8.0) as http_client:
                b3_client = B3ListedCompaniesClient(client=http_client, language="pt-br")
                supplement = await b3_client.company_supplement(
                    ticker=clean_ticker,
                    is_bdr=is_bdr,
                )
                if not supplement:
                    return []

                code_cvm = str(supplement.get("codeCVM") or "").strip()
                company_name = str(supplement.get("companyName") or clean_ticker).strip()
                if not code_cvm:
                    return []

                current_year = datetime.now(timezone.utc).year
                for year in (current_year, current_year - 1):
                    path = b3_service_path(
                        "GetListStructuredReports",
                        {
                            "codeCVM": int(code_cvm) if code_cvm.isdigit() else code_cvm,
                            "language": "pt-br",
                            "status": True,
                            "year": year,
                        },
                    )
                    resp = await http_client.get(
                        f"{B3_LISTED_COMPANIES_BASE}/{path}",
                        headers={"Accept": "application/json"},
                    )
                    if resp.status_code != 200:
                        continue
                    payload: Any = resp.json()
                    for _ in range(2):
                        if isinstance(payload, str) and payload.strip():
                            payload = json.loads(payload)
                    if not isinstance(payload, dict):
                        continue

                    for group_key, category_label in (
                        ("itr", "ITR — Informações Trimestrais"),
                        ("dfp", "DFP — Demonstrações Financeiras Padronizadas"),
                        ("fre", "FRE — Formulário de Referência"),
                        ("fca", "FCA — Formulário Cadastral"),
                        ("ian", "Informe de Governança"),
                    ):
                        items = payload.get(group_key)
                        if not isinstance(items, list):
                            continue
                        for item in items:
                            if not isinstance(item, dict):
                                continue
                            url_search = str(item.get("urlSearch") or "").strip()
                            url_download = str(item.get("urlDownload") or "").strip()
                            if not url_search and not url_download:
                                continue
                            ref_dt = _parse_br_or_iso_date(item.get("dateReference"))
                            deliv_dt = _parse_br_or_iso_date(item.get("deliveryDate"))
                            title = str(item.get("type") or category_label).strip()
                            reports.append({
                                "id": f"{code_cvm}-{group_key}-{ref_dt or year}-{item.get('version', 1)}",
                                "title": title,
                                "category": category_label,
                                "reference_date": ref_dt or str(item.get("dateReference") or ""),
                                "delivery_date": deliv_dt or str(item.get("deliveryDate") or ""),
                                "status": str(item.get("status") or "Ativo"),
                                "version": item.get("version"),
                                "fund_name": company_name,
                                "source": "CVM / B3 Empresas.NET",
                                "url": url_search or url_download,
                                "download_url": url_download or url_search,
                                "is_management_report": group_key in ("itr", "dfp"),
                            })
                    if len(reports) >= 10:
                        break
        except Exception as exc:
            logger.debug(
                "Falha ao buscar relatórios estruturados B3 para %s: %s",
                sanitize_log_value(clean_ticker),
                sanitize_log_value(exc),
            )

        reports.sort(
            key=lambda r: (
                1 if r.get("is_management_report") else 0,
                str(r.get("delivery_date") or r.get("reference_date") or ""),
            ),
            reverse=True,
        )
        final_reports = reports[:15]
        await self._set_cached(
            cache_key,
            final_reports,
            TTL_REPORTS_SECONDS if final_reports else TTL_EMPTY_SECONDS,
        )
        return final_reports

    # -------------------------------------------------------------------------
    # 3. Notícias Externas do Ativo (Finnhub + Google News RSS)
    # -------------------------------------------------------------------------

    async def _fetch_finnhub_company_news(self, ticker: str) -> list[dict[str, Any]]:
        key = get_runtime_provider_key(ProviderId.FINNHUB)
        if not key:
            return []
        clean_ticker = ticker.strip().upper()
        today = datetime.now(timezone.utc).date()
        from_date = (today - timedelta(days=30)).isoformat()
        to_date = today.isoformat()
        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                resp = await client.get(
                    FINNHUB_NEWS_URL,
                    headers={"X-Finnhub-Token": key},
                    params={"symbol": clean_ticker, "from": from_date, "to": to_date},
                )
                if resp.status_code != 200:
                    return []
                data = resp.json()
                if not isinstance(data, list):
                    return []
                items: list[dict[str, Any]] = []
                for row in data[:10]:
                    if not isinstance(row, dict):
                        continue
                    headline = str(row.get("headline") or "").strip()
                    url = str(row.get("url") or "").strip()
                    if not headline or not url:
                        continue
                    ts = row.get("datetime")
                    published_at = (
                        datetime.fromtimestamp(int(ts), tz=timezone.utc).isoformat()
                        if isinstance(ts, (int, float)) and ts > 0
                        else None
                    )
                    items.append({
                        "title": headline,
                        "source": str(row.get("source") or "Finnhub"),
                        "url": url,
                        "published_at": published_at,
                        "summary": str(row.get("summary") or "")[:280].strip() or None,
                    })
                return items
        except Exception:
            return []

    async def _fetch_google_news_rss(
        self,
        ticker: str,
        asset_name: Optional[str] = None,
        asset_type: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        clean_ticker = ticker.strip().upper()
        tipo = (asset_type or "").upper()
        if tipo == "FII":
            query = f'"{clean_ticker}" FII OR "fundo imobiliário" when:60d'
        elif tipo in ("ACAO", "BDR", "ETF_NACIONAL"):
            short_name = ""
            if asset_name:
                words = [w for w in re.split(r"\s+", asset_name.strip()) if len(w) > 2]
                if words:
                    short_name = words[0]
            query = f'"{clean_ticker}" {short_name} ações OR bolsa OR dividendos when:45d'.strip()
        elif tipo == "CRIPTO":
            query = f'"{clean_ticker}" criptomoeda OR mercado cripto when:14d'
        else:
            query = f'"{clean_ticker}" {asset_name or ""} mercado financeiro when:45d'.strip()

        url = f"{GOOGLE_NEWS_RSS_URL}?q={quote_plus(query)}&hl=pt-BR&gl=BR&ceid=BR:pt-419"
        try:
            async with httpx.AsyncClient(timeout=6.0, follow_redirects=True) as client:
                resp = await client.get(
                    url,
                    headers={"User-Agent": "Mozilla/5.0 (compatible; SGI/2.0)"},
                )
                if resp.status_code != 200 or not resp.text:
                    return []

                root = ET.fromstring(resp.text)
                items: list[dict[str, Any]] = []
                for item_el in root.findall("./channel/item")[:10]:
                    raw_title = (item_el.findtext("title") or "").strip()
                    link = (item_el.findtext("link") or "").strip()
                    pub_date_raw = (item_el.findtext("pubDate") or "").strip()
                    source_el = item_el.find("source")
                    source_name = (
                        source_el.text.strip()
                        if source_el is not None and source_el.text
                        else "Google Notícias"
                    )
                    if not raw_title or not link:
                        continue
                    # Remove sufixo " - Fonte" duplicado no título do Google News
                    if f" - {source_name}" in raw_title:
                        raw_title = raw_title.rsplit(f" - {source_name}", 1)[0].strip()

                    published_iso: Optional[str] = None
                    if pub_date_raw:
                        try:
                            published_iso = parsedate_to_datetime(pub_date_raw).astimezone(timezone.utc).isoformat()
                        except Exception:
                            published_iso = pub_date_raw

                    items.append({
                        "title": raw_title,
                        "source": source_name,
                        "url": link,
                        "published_at": published_iso,
                        "summary": None,
                    })
                return items
        except Exception as exc:
            logger.debug(
                "Falha ao consultar Google News RSS para %s: %s",
                sanitize_log_value(clean_ticker),
                sanitize_log_value(exc),
            )
            return []

    async def fetch_asset_news(
        self,
        ticker: str,
        asset_name: Optional[str] = None,
        asset_type: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        clean_ticker = ticker.strip().upper()
        cache_key = f"asset_news:v1:{clean_ticker}"
        cached = await self._get_cached(cache_key)
        if isinstance(cached, list):
            return cached

        tipo = (asset_type or "").upper()
        news: list[dict[str, Any]] = []
        if tipo in ("STOCK", "ETF_INTERNACIONAL"):
            news = await self._fetch_finnhub_company_news(clean_ticker)

        if len(news) < 4:
            rss_news = await self._fetch_google_news_rss(
                clean_ticker,
                asset_name=asset_name,
                asset_type=tipo,
            )
            seen_titles = {n["title"].lower() for n in news}
            for item in rss_news:
                if item["title"].lower() not in seen_titles:
                    news.append(item)
                    seen_titles.add(item["title"].lower())

        final_news = news[:10]
        await self._set_cached(
            cache_key,
            final_news,
            TTL_NEWS_SECONDS if final_news else TTL_EMPTY_SECONDS,
        )
        return final_news

    # -------------------------------------------------------------------------
    # 4. Leitura DB-first / Cache-only e Refresh em Background
    # -------------------------------------------------------------------------

    async def get_cached_reports_and_news(
        self,
        ticker: str,
        asset_type: Optional[str] = None,
        *,
        schedule_refresh_on_miss: bool = True,
        asset_name: Optional[str] = None,
        enrichment: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Lê apenas relatórios e notícias já em cache (sem bloquear o read path com chamadas externas)."""
        clean_ticker = ticker.strip().upper()
        tipo = (asset_type or "").upper()

        if tipo == "FII" or (not tipo and clean_ticker.endswith("11")):
            reports_key = f"asset_reports:fii:v1:{clean_ticker}"
        elif tipo in ("ACAO", "BDR"):
            reports_key = f"asset_reports:company:v1:{clean_ticker}"
        else:
            reports_key = ""

        cached_reports = await self._get_cached(reports_key) if reports_key else []
        cached_news = await self._get_cached(f"asset_news:v1:{clean_ticker}")

        reports_list = cached_reports if isinstance(cached_reports, list) else []
        news_list = cached_news if isinstance(cached_news, list) else []

        report_excerpt: Optional[dict[str, Any]] = None
        if (tipo == "FII" or clean_ticker.endswith("11")) and reports_list:
            mgmt = [r for r in reports_list if isinstance(r, dict) and r.get("is_management_report")]
            target = mgmt[0] if mgmt else reports_list[0]
            if isinstance(target, dict) and target.get("id"):
                excerpt_cached = await self._get_cached(
                    f"asset_report_excerpt:v1:{clean_ticker}:{target['id']}"
                )
                if isinstance(excerpt_cached, dict):
                    report_excerpt = excerpt_cached

        is_miss = (bool(reports_key) and cached_reports is None) or (cached_news is None)
        if is_miss and schedule_refresh_on_miss:
            self.schedule_background_refresh(
                clean_ticker,
                asset_type=tipo,
                asset_name=asset_name,
                enrichment=enrichment,
            )

        inflight_key = f"inflight:{clean_ticker}"
        inflight_active = (
            inflight_key in self._memory_cache
            and time.time() < self._memory_cache[inflight_key][0]
        )

        return {
            "reports": reports_list,
            "latest_report_excerpt": report_excerpt,
            "news": news_list,
            "refresh_pending": bool((is_miss and schedule_refresh_on_miss) or inflight_active),
        }

    def schedule_background_refresh(
        self,
        ticker: str,
        asset_type: Optional[str] = None,
        asset_name: Optional[str] = None,
        enrichment: Optional[dict[str, Any]] = None,
    ) -> None:
        """Agenda atualização assíncrona em background sem bloquear a requisição HTTP."""
        clean_ticker = ticker.strip().upper()
        inflight_key = f"inflight:{clean_ticker}"
        now = time.time()
        if inflight_key in self._memory_cache and now < self._memory_cache[inflight_key][0]:
            return
        self._memory_cache[inflight_key] = (now + 60, True)

        async def _runner() -> None:
            try:
                await self.get_reports_and_news(
                    clean_ticker,
                    asset_type=asset_type,
                    asset_name=asset_name,
                    enrichment=enrichment,
                )
            except Exception:
                pass
            finally:
                self._memory_cache.pop(inflight_key, None)

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_runner())
        except RuntimeError:
            pass

    async def get_reports_and_news(
        self,
        ticker: str,
        asset_type: Optional[str] = None,
        asset_name: Optional[str] = None,
        enrichment: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        clean_ticker = ticker.strip().upper()
        tipo = (asset_type or "").upper()

        reports_task: Any
        if tipo == "FII" or (not tipo and clean_ticker.endswith("11")):
            reports_task = self.fetch_fii_reports(clean_ticker, enrichment=enrichment)
        elif tipo in ("ACAO", "BDR"):
            reports_task = self.fetch_company_reports(clean_ticker, asset_type=tipo)
        else:
            reports_task = asyncio.sleep(0, result=[])

        news_task = self.fetch_asset_news(
            clean_ticker,
            asset_name=asset_name,
            asset_type=tipo,
        )

        reports, news = await asyncio.gather(reports_task, news_task)
        report_excerpt: Optional[dict[str, Any]] = None
        if (tipo == "FII" or clean_ticker.endswith("11")) and reports:
            report_excerpt = await self.extract_latest_fii_report_excerpt(
                clean_ticker,
                reports,
            )

        return {
            "reports": reports,
            "latest_report_excerpt": report_excerpt,
            "news": news,
        }


asset_reports_and_news_service = AssetReportsAndNewsService()
