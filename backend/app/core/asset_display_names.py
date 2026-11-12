"""Formatação e resolução canônica de nomes comerciais de ativos para exibição."""

from __future__ import annotations

import re

_CLASS_LABELS = frozenset({
    "Ações",
    "FIIs",
    "ETFs Nacionais",
    "ETFs Internacionais",
    "Stocks",
    "BDRs",
    "Criptomoedas",
    "Renda Fixa",
    "Tesouro Direto",
    "Outros",
})

_KNOWN_ACAO_NAMES: dict[str, str] = {
    "ALOS3": "Allos",
    "ALUP11": "Alupar",
    "AMOB3": "Automob",
    "AUAU3": "União Pet",
    "BBAS3": "Banco do Brasil",
    "BBDC3": "Bradesco",
    "BBDC4": "Bradesco",
    "BBSE3": "BB Seguridade",
    "BMGB4": "Banco BMG",
    "BPAC11": "BTG Pactual",
    "BRBI11": "BR Partners",
    "CEBR6": "CEB",
    "CMIG4": "Cemig",
    "CSMG3": "Copasa",
    "CXSE3": "Caixa Seguridade",
    "EGIE3": "Engie Brasil",
    "FIQE3": "Unifique",
    "GOAU4": "Metalúrgica Gerdau",
    "ISAE4": "ISA Energia",
    "ITSA4": "Itaúsa",
    "ITUB3": "Itaú Unibanco",
    "ITUB4": "Itaú Unibanco",
    "JHSF3": "JHSF",
    "KLBN11": "Klabin",
    "KLBN3": "Klabin",
    "KLBN4": "Klabin",
    "MELK3": "Melnick",
    "MTRE3": "Mitre Realty",
    "PETR3": "Petrobras",
    "PETR4": "Petrobras",
    "POMO3": "Marcopolo",
    "POMO4": "Marcopolo",
    "RANI3": "Irani",
    "SANB11": "Santander Brasil",
    "SAPR4": "Sanepar",
    "SAPR11": "Sanepar",
    "SOJA3": "Boa Safra",
    "TAEE11": "Taesa",
    "TEND3": "Tenda",
    "VALE3": "Vale",
    "VULC3": "Vulcabras",
    "WEGE3": "WEG",
}

_KNOWN_FII_NAMES: dict[str, str] = {
    "AAZQ11": "AZ Quest Sole Fiagro",
    "ALZC11": "Alianza Crédito Imobiliário FII",
    "ALZR11": "Alianza Trust Renda Imobiliária FII",
    "ARXD11": "ARX Dover Recebíveis FII",
    "BCFF11": "BTG Pactual Fundo de Fundos FII",
    "BRCO11": "Bresco Logística FII",
    "BTCI11": "BTG Pactual Crédito Imobiliário FII",
    "BTLG11": "BTG Pactual Logística FII",
    "CPTS11": "Capitânia Securities II FII",
    "DEVA11": "Devant Recebíveis Imobiliários FII",
    "FGAA11": "FG Agro Fiagro",
    "GARE11": "Guardian Real Estate FII",
    "GGRC11": "GGR Covepi Renda FII",
    "HABT11": "Habitat II FII",
    "HCTR11": "Hectare CE FII",
    "HGBS11": "Hedge Brasil Shopping FII",
    "HGLG11": "CSHG Logística FII",
    "HGRU11": "CSHG Renda Urbana FII",
    "HSML11": "HSI Malls FII",
    "IRDM11": "Iridium Recebíveis Imobiliários FII",
    "JSRE11": "JS Real Estate Multigestão FII",
    "KFOF11": "Kinea FOF Imobiliário FII",
    "KNCA11": "Kinea Crédito Agro Fiagro",
    "KNCR11": "Kinea Rendimentos Imobiliários FII",
    "KNIP11": "Kinea Índices de Preços FII",
    "KNRI11": "Kinea Renda Imobiliária FII",
    "KNSC11": "Kinea Securities FII",
    "LVBI11": "VBI Logística FII",
    "MALL11": "Patria Malls FII",
    "MXRF11": "Maxi Renda FII",
    "PVBI11": "VBI Prime Properties FII",
    "RBRF11": "RBR Alpha Multiestratégia FII",
    "RBRR11": "RBR Rendimento High Grade FII",
    "RBRX11": "RBR Plus Multiestratégia FII",
    "RBRY11": "RBR Crédito Imobiliário Estruturado FII",
    "RECR11": "REC Recebíveis Imobiliários FII",
    "RZTR11": "Riza Terrax Fiagro",
    "SNAG11": "Suno Agro Fiagro",
    "SNEL11": "Suno Energias Limpas FII",
    "TGAR11": "TG Ativo Real FII",
    "TRXF11": "TRX Real Estate FII",
    "VCRA11": "Vectis Datagro Crédito Agronegócio Fiagro",
    "VGHF11": "Valora Hedge Fund FII",
    "VGIA11": "Valora CRA Fiagro",
    "VGIR11": "Valora RE III FII",
    "VILG11": "Vinci Logística FII",
    "VINO11": "Vinci Offices FII",
    "VISC11": "Vinci Shopping Centers FII",
    "VIUR11": "Vinci Imóveis Urbanos FII",
    "VRTA11": "Fator Verità FII",
    "XPCA11": "XP Crédito Agrícola Fiagro",
    "XPCI11": "XP Crédito Imobiliário FII",
    "XPLG11": "XP Log FII",
    "XPML11": "XP Malls FII",
    "XPSF11": "XP Selection FII",
}

_KNOWN_ETF_NACIONAL_NAMES: dict[str, str] = {
    "ACWI11": "Trend MSCI ACWI ETF",
    "AREA11": "Investo US Real Estate ETF",
    "AURO11": "Buena Vista Gold High Income ETF",
    "B5P211": "It Now IMA-B5 P2 ETF",
    "BBOV11": "BB ETF Ibovespa",
    "BOVA11": "iShares Ibovespa ETF",
    "BRAX11": "iShares IBrX-100 Brasil ETF",
    "CHIP11": "Trend Semicondutores ETF",
    "COIN11": "Buena Vista Bitcoin High Income ETF",
    "DIVD11": "It Now IDIV Renda Dividendos ETF",
    "DIVO11": "It Now IDIV ETF",
    "GOLD11": "Trend Ouro ETF",
    "HASH11": "Hashdex Nasdaq Crypto ETF",
    "IMAB11": "It Now IMA-B ETF",
    "IVVB11": "iShares S&P 500 B3 ETF",
    "LFTS11": "Investo Teva Tesouro Selic ETF",
    "NASD11": "Trend Nasdaq-100 ETF",
    "NDIV11": "Nu Renda Ibov Smart Dividendos ETF",
    "NSDV11": "Nu Ibov Smart Dividendos ETF",
    "QQQI11": "Buena Vista Nasdaq-100 High Income ETF",
    "SMAL11": "iShares Small Cap ETF",
    "SPXI11": "It Now S&P 500 ETF",
    "WRLD11": "Investo FTSE Global ETF",
    "XINA11": "Trend MSCI China ETF",
}

_KNOWN_ETF_INTERNACIONAL_NAMES: dict[str, str] = {
    "DGRO": "iShares Core Dividend Growth ETF",
    "IVV": "iShares Core S&P 500 ETF",
    "JEPI": "JPMorgan Equity Premium Income ETF",
    "JEPQ": "JPMorgan Nasdaq Equity Premium Income ETF",
    "NOBL": "ProShares S&P 500 Dividend Aristocrats ETF",
    "QQQ": "Invesco QQQ Trust ETF",
    "SCHD": "Schwab U.S. Dividend Equity ETF",
    "SGOV": "iShares 0-3 Month Treasury Bond ETF",
    "SHV": "iShares Short Treasury Bond ETF",
    "SPY": "SPDR S&P 500 ETF Trust",
    "TFLO": "iShares Treasury Floating Rate Bond ETF",
    "TLT": "iShares 20+ Year Treasury Bond ETF",
    "VNQ": "Vanguard Real Estate ETF",
    "VOO": "Vanguard S&P 500 ETF",
    "VT": "Vanguard Total World Stock ETF",
    "VTI": "Vanguard Total Stock Market ETF",
    "VXUS": "Vanguard Total International Stock ETF",
    "VYM": "Vanguard High Dividend Yield ETF",
}

_KNOWN_BDR_NAMES: dict[str, str] = {
    "AAPL34": "Apple",
    "AMZO34": "Amazon",
    "ASML34": "ASML Holding",
    "BABA34": "Alibaba",
    "BERK34": "Berkshire Hathaway",
    "CHVX34": "Chevron",
    "COCA34": "Coca-Cola",
    "COST34": "Costco",
    "DISB34": "Walt Disney",
    "E1CO34": "Ecopetrol",
    "EXXO34": "ExxonMobil",
    "GOGL34": "Alphabet (Google)",
    "INBR32": "Inter & Co",
    "JNJB34": "Johnson & Johnson",
    "JPMC34": "JPMorgan Chase",
    "M1TA34": "Meta Platforms",
    "MCDC34": "McDonald's",
    "MELI34": "Mercado Libre",
    "MSFT34": "Microsoft",
    "NFLX34": "Netflix",
    "NIKE34": "Nike",
    "NUBR33": "Nu Holdings (Nubank)",
    "NVDC34": "NVIDIA",
    "ORCL34": "Oracle",
    "PEPB34": "PepsiCo",
    "PFIZ34": "Pfizer",
    "PGCO34": "Procter & Gamble",
    "ROXO34": "Nu Holdings (Nubank)",
    "SBUB34": "Starbucks",
    "SSFO34": "Salesforce",
    "TSLA34": "Tesla",
    "TSMC34": "TSMC",
    "VISA34": "Visa",
    "WALM34": "Walmart",
    "XPBR31": "XP Inc.",
}

_KNOWN_STOCK_NAMES: dict[str, str] = {
    "AAPL": "Apple",
    "ABBV": "AbbVie",
    "ADBE": "Adobe",
    "AMD": "AMD",
    "AMT": "American Tower",
    "AMZN": "Amazon",
    "ASML": "ASML Holding",
    "AVGO": "Broadcom",
    "BRK.B": "Berkshire Hathaway",
    "BRK-B": "Berkshire Hathaway",
    "COST": "Costco",
    "CRM": "Salesforce",
    "CVX": "Chevron",
    "DIS": "Walt Disney",
    "GOOG": "Alphabet (Google)",
    "GOOGL": "Alphabet (Google)",
    "HD": "Home Depot",
    "INTC": "Intel",
    "INTR": "Inter & Co",
    "JNJ": "Johnson & Johnson",
    "JPM": "JPMorgan Chase",
    "KO": "Coca-Cola",
    "LLY": "Eli Lilly",
    "MA": "Mastercard",
    "MCD": "McDonald's",
    "MELI": "Mercado Libre",
    "META": "Meta Platforms",
    "MRK": "Merck",
    "MSFT": "Microsoft",
    "NFLX": "Netflix",
    "NKE": "Nike",
    "NU": "Nu Holdings (Nubank)",
    "NVDA": "NVIDIA",
    "O": "Realty Income",
    "ORCL": "Oracle",
    "PAGS": "PagSeguro Digital",
    "PBR": "Petrobras ADR",
    "PEP": "PepsiCo",
    "PFE": "Pfizer",
    "PG": "Procter & Gamble",
    "PLD": "Prologis",
    "STNE": "StoneCo",
    "TSLA": "Tesla",
    "TSM": "TSMC",
    "UNH": "UnitedHealth",
    "V": "Visa",
    "VALE": "Vale ADR",
    "WMT": "Walmart",
    "XOM": "ExxonMobil",
    "XP": "XP Inc.",
}

_KNOWN_CRIPTO_NAMES: dict[str, str] = {
    "AAVE": "Aave",
    "ADA": "Cardano",
    "ALGO": "Algorand",
    "APT": "Aptos",
    "ARB": "Arbitrum",
    "ATOM": "Cosmos",
    "AVAX": "Avalanche",
    "BCH": "Bitcoin Cash",
    "BNB": "BNB",
    "BTC": "Bitcoin",
    "DOGE": "Dogecoin",
    "DOT": "Polkadot",
    "ETH": "Ethereum",
    "FET": "Artificial Superintelligence",
    "INJ": "Injective",
    "LDO": "Lido DAO",
    "LINK": "Chainlink",
    "LTC": "Litecoin",
    "MATIC": "Polygon",
    "MKR": "Maker",
    "NEAR": "NEAR Protocol",
    "OP": "Optimism",
    "POL": "Polygon",
    "RENDER": "Render",
    "RNDR": "Render",
    "SHIB": "Shiba Inu",
    "SOL": "Solana",
    "SUI": "Sui",
    "TON": "Toncoin",
    "TRX": "TRON",
    "UNI": "Uniswap",
    "USDC": "USD Coin",
    "USDT": "Tether USDt",
    "XLM": "Stellar",
    "XMR": "Monero",
    "XRP": "XRP (Ripple)",
}

_KNOWN_NAMES_BY_TYPE: dict[str, dict[str, str]] = {
    "ACAO": _KNOWN_ACAO_NAMES,
    "ACOES": _KNOWN_ACAO_NAMES,
    "ACAO_NACIONAL": _KNOWN_ACAO_NAMES,
    "FII": _KNOWN_FII_NAMES,
    "ETF_NACIONAL": _KNOWN_ETF_NACIONAL_NAMES,
    "ETF": _KNOWN_ETF_NACIONAL_NAMES,
    "ETF_INTERNACIONAL": _KNOWN_ETF_INTERNACIONAL_NAMES,
    "ETF_INT": _KNOWN_ETF_INTERNACIONAL_NAMES,
    "BDR": _KNOWN_BDR_NAMES,
    "STOCK": _KNOWN_STOCK_NAMES,
    "STOCKS": _KNOWN_STOCK_NAMES,
    "CRIPTO": _KNOWN_CRIPTO_NAMES,
    "CRIPTOMOEDA": _KNOWN_CRIPTO_NAMES,
}

_KNOWN_TICKER_NAMES: dict[str, str] = {
    **_KNOWN_ACAO_NAMES,
    **_KNOWN_FII_NAMES,
    **_KNOWN_ETF_NACIONAL_NAMES,
    **_KNOWN_ETF_INTERNACIONAL_NAMES,
    **_KNOWN_BDR_NAMES,
    **_KNOWN_STOCK_NAMES,
    **_KNOWN_CRIPTO_NAMES,
}

# Prefixos B3 de 4 letras para ações (cobre classes ON/PN/UNT como POMO3/POMO4, PETR3/PETR4)
_KNOWN_B3_EQUITY_PREFIX_NAMES: dict[str, str] = {
    "ABEV": "Ambev",
    "AGRO": "BrasilAgro",
    "ALOS": "Allos",
    "ALPA": "Alpargatas",
    "ALUP": "Alupar",
    "AMOB": "Automob",
    "ANIM": "Ânima Educação",
    "ASAI": "Assaí",
    "AUAU": "União Pet",
    "AURE": "Auren Energia",
    "AZUL": "Azul",
    "AZZA": "Azzas 2154",
    "B3SA": "B3",
    "BBAS": "Banco do Brasil",
    "BBDC": "Bradesco",
    "BBSE": "BB Seguridade",
    "BEEF": "Minerva Foods",
    "BLAU": "Blau Farmacêutica",
    "BMGB": "Banco BMG",
    "BPAC": "BTG Pactual",
    "BRAV": "Brava Energia",
    "BRBI": "BR Partners",
    "BRFS": "BRF",
    "CAML": "Camil",
    "CEBR": "CEB",
    "CMIG": "Cemig",
    "CMIN": "CSN Mineração",
    "COGN": "Cogna",
    "CPFE": "CPFL Energia",
    "CPLE": "Copel",
    "CRFB": "Carrefour Brasil",
    "CSAN": "Cosan",
    "CSMG": "Copasa",
    "CSNA": "CSN",
    "CURY": "Cury",
    "CVCB": "CVC",
    "CXSE": "Caixa Seguridade",
    "CYRE": "Cyrela",
    "DIRR": "Direcional",
    "ECOR": "EcoRodovias",
    "EGIE": "Engie Brasil",
    "ELET": "Eletrobras",
    "EMBR": "Embraer",
    "ENGI": "Energisa",
    "EQTL": "Equatorial",
    "EVEN": "Even",
    "EZTC": "EZTEC",
    "FIQE": "Unifique",
    "FLRY": "Fleury",
    "FRAS": "Fras-le",
    "GGBR": "Gerdau",
    "GMAT": "Grupo Mateus",
    "GOAU": "Metalúrgica Gerdau",
    "GOLL": "Gol",
    "GRND": "Grendene",
    "HAPV": "Hapvida",
    "HBSA": "Hidrovias do Brasil",
    "HYPE": "Hypera",
    "IGTI": "Iguatemi",
    "INTB": "Intelbras",
    "IRBR": "IRB Re",
    "ISAE": "ISA Energia",
    "ITSA": "Itaúsa",
    "ITUB": "Itaú Unibanco",
    "JBSS": "JBS",
    "JHSF": "JHSF",
    "KEPL": "Kepler Weber",
    "KLBN": "Klabin",
    "LAVV": "Lavvi",
    "LEVE": "Mahle Metal Leve",
    "LOGG": "LOG Commercial",
    "LREN": "Lojas Renner",
    "LWSA": "LWSA",
    "MDIA": "M. Dias Branco",
    "MELK": "Melnick",
    "MGLU": "Magazine Luiza",
    "MOTV": "Motiva",
    "MOVI": "Movida",
    "MRFG": "Marfrig",
    "MRVE": "MRV",
    "MTRE": "Mitre Realty",
    "MULT": "Multiplan",
    "MYPK": "Iochpe-Maxion",
    "NEOE": "Neoenergia",
    "ODPV": "OdontoPrev",
    "PETR": "Petrobras",
    "PLPL": "Plano & Plano",
    "POMO": "Marcopolo",
    "POSI": "Positivo",
    "PRIO": "PRIO",
    "PSSA": "Porto Seguro",
    "RADL": "Raia Drogasil",
    "RAIL": "Rumo",
    "RANI": "Irani",
    "RAPT": "Randoncorp",
    "RDOR": "Rede D'Or",
    "RECV": "PetroRecôncavo",
    "RENT": "Localiza",
    "ROMI": "Romi",
    "SANB": "Santander Brasil",
    "SAPR": "Sanepar",
    "SBSP": "Sabesp",
    "SEER": "Ser Educacional",
    "SIMH": "Simpar",
    "SLCE": "SLC Agrícola",
    "SMFT": "Smart Fit",
    "SMTO": "São Martinho",
    "SOJA": "Boa Safra",
    "STBP": "Santos Brasil",
    "SUZB": "Suzano",
    "TAEE": "Taesa",
    "TEND": "Tenda",
    "TIMS": "TIM",
    "TOTS": "TOTVS",
    "TRPL": "ISA Energia",
    "TTEN": "3tentos",
    "TUPY": "Tupy",
    "UGPA": "Ultrapar",
    "VALE": "Vale",
    "VAMO": "Vamos",
    "VBBR": "Vibra Energia",
    "VIVT": "Telefônica Vivo",
    "VULC": "Vulcabras",
    "WEGE": "WEG",
    "YDUQ": "Yduqs",
}

_B3_EQUITY_SHARES_RE = re.compile(r"^([A-Z]{4})(?:3|4|5|6|11)$")
_CORP_SUFFIX_RE = re.compile(
    r"\s*(?:-\s*EM\s+RECUPERACAO\s+JUDICIAL)?\s*"
    r"\b(?:S\.?A\.?|S/A|LTDA\.?|INC\.?|CORP\.?|PLC|LIMITED|LTD\.?)\s*$",
    re.IGNORECASE,
)
_LOWERCASE_CONNECTORS = frozenset({"de", "da", "do", "dos", "das", "e", "em", "para", "com"})
_UPPERCASE_ACRONYMS = frozenset({
    "FII", "FIAGRO", "ETF", "BDR", "BB", "BMG", "BR", "WEG", "JHSF", "CSN",
    "PRIO", "B3", "TIM", "TOTVS", "MRV", "CVC", "II", "III", "IV", "S&P",
    "EUA", "US", "USA", "TI", "MG", "SP", "RJ", "PR", "CEB", "ADR",
})


def _clean_corporate_registration_name(raw_name: str) -> str:
    cleaned = raw_name.strip()
    if cleaned.upper().startswith("BCO "):
        cleaned = "BANCO " + cleaned[4:]
    elif cleaned.upper().startswith("CIA "):
        cleaned = "COMPANHIA " + cleaned[4:]

    cleaned = _CORP_SUFFIX_RE.sub("", cleaned).strip(" -/,.")
    if not cleaned:
        return raw_name.strip()

    words = cleaned.split()
    formatted_words: list[str] = []
    for idx, word in enumerate(words):
        upper_word = word.upper().strip("(),.")
        if upper_word in _UPPERCASE_ACRONYMS:
            formatted_words.append(word.upper())
        elif idx > 0 and word.lower() in _LOWERCASE_CONNECTORS:
            formatted_words.append(word.lower())
        else:
            formatted_words.append(word.capitalize())
    return " ".join(formatted_words)


def _format_treasury_slug(slug: str) -> str:
    lower = slug.strip().lower()
    year_match = re.search(r"(\d{4})$", lower)
    year_suffix = f" {year_match.group(1)}" if year_match else ""
    if "renda-mais" in lower or "renda+" in lower:
        return f"Tesouro Renda+{year_suffix}"
    if "educa-mais" in lower or "educa+" in lower:
        return f"Tesouro Educa+{year_suffix}"
    if "selic" in lower:
        return f"Tesouro Selic{year_suffix}"
    if "prefixado" in lower:
        if "juros" in lower:
            return f"Tesouro Prefixado com Juros Semestrais{year_suffix}"
        return f"Tesouro Prefixado{year_suffix}"
    if "ipca" in lower:
        if "juros" in lower:
            return f"Tesouro IPCA+ com Juros Semestrais{year_suffix}"
        return f"Tesouro IPCA+{year_suffix}"
    return slug.strip()


def format_asset_display_name(
    raw_name: object,
    ticker: object,
    asset_type: object = None,
    *,
    fallback_label: str | None = None,
) -> str:
    """Resolve o nome comercial limpo de um ativo para exibição nos cards e tabelas."""
    clean_ticker = str(ticker or "").strip()
    upper_ticker = clean_ticker.upper()
    clean_raw = str(raw_name or "").strip()
    norm_type = str(asset_type or "").strip().upper()

    # 1. Preserva nomes customizados ou já formatados em mixed-case (ex.: testes, Tesouro Direto)
    if (
        clean_raw
        and clean_raw.upper() != upper_ticker
        and clean_raw not in _CLASS_LABELS
        and not clean_raw.isupper()
    ):
        return clean_raw

    if norm_type in {"TESOURO_DIRETO", "TESOURO"} or upper_ticker.startswith("TESOURO-"):
        return _format_treasury_slug(clean_ticker)

    # 2. Mapa canônico por (asset_type, ticker) para evitar colisão entre classes
    if norm_type in _KNOWN_NAMES_BY_TYPE:
        known = _KNOWN_NAMES_BY_TYPE[norm_type].get(upper_ticker)
        if known:
            return known
    elif not norm_type:
        known = _KNOWN_TICKER_NAMES.get(upper_ticker)
        if known:
            return known

    # 3. Mapa por prefixo de 4 letras para ações da B3 (ex.: POMO3/POMO4 -> Marcopolo)
    if norm_type in {"", "ACAO", "ACOES", "ACAO_NACIONAL"}:
        match = _B3_EQUITY_SHARES_RE.fullmatch(upper_ticker)
        if match:
            prefix_name = _KNOWN_B3_EQUITY_PREFIX_NAMES.get(match.group(1))
            if prefix_name:
                return prefix_name

    # 4. Se existir nome de registro em caixa alta no banco (COTAHIST/CVM), formata de forma limpa
    if clean_raw and clean_raw.upper() != upper_ticker and clean_raw not in _CLASS_LABELS:
        return _clean_corporate_registration_name(clean_raw)

    # 5. Fallback para o rótulo fornecido ou ticker
    if fallback_label:
        return fallback_label
    return clean_ticker
