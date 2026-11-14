import type { ReactNode } from 'react'

/**
 * Ícones vetoriais próprios do SGI para classes de ativos e criptomoedas.
 * Usados quando não há logo real da empresa/ativo (ou quando o provider
 * devolve apenas um placeholder genérico).
 */

export type IconRenderer = (size: number) => ReactNode

const svgProps = (size: number) => ({
  width: size,
  height: size,
  viewBox: '0 0 24 24',
  fill: 'none',
  'aria-hidden': true as const,
})

const stroke = {
  stroke: 'currentColor',
  strokeWidth: 1.8,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
}

/* ------------------------------------------------------------------ */
/* Ícones de classe                                                    */
/* ------------------------------------------------------------------ */

/** Tesouro Direto: edifício público com frontão, colunas e emblema. */
export const TreasuryIcon: IconRenderer = (s) => (
  <svg {...svgProps(s)}>
    <path d="M3.5 9.2 12 4l8.5 5.2H3.5Z" {...stroke} fill="currentColor" fillOpacity="0.18" />
    <circle cx="12" cy="7.3" r="0.9" fill="currentColor" />
    <path d="M5.5 10.8v6.4M9.2 10.8v6.4M14.8 10.8v6.4M18.5 10.8v6.4" {...stroke} />
    <path d="M4 17.6h16M3 20h18" {...stroke} />
  </svg>
)

/** Renda Fixa: escudo de proteção com símbolo de percentual. */
export const FixedIncomeIcon: IconRenderer = (s) => (
  <svg {...svgProps(s)}>
    <path
      d="M12 3.5 19 6v5.6c0 4.2-2.9 7.6-7 8.9-4.1-1.3-7-4.7-7-8.9V6l7-2.5Z"
      {...stroke}
      fill="currentColor"
      fillOpacity="0.14"
    />
    <path d="m9.2 14.6 5.6-5.6" {...stroke} />
    <circle cx="9.6" cy="9.6" r="1.2" fill="currentColor" />
    <circle cx="14.4" cy="14.2" r="1.2" fill="currentColor" />
  </svg>
)

/** Ações: gráfico de candlesticks. */
export const StockBrIcon: IconRenderer = (s) => (
  <svg {...svgProps(s)}>
    <path d="M6 4.5v15M12 3v14M18 6.5v13" {...stroke} strokeWidth={1.4} />
    <rect x="4.3" y="9" width="3.4" height="6.5" rx="0.8" fill="currentColor" fillOpacity="0.35" stroke="currentColor" strokeWidth="1.4" />
    <rect x="10.3" y="5.5" width="3.4" height="7.5" rx="0.8" fill="currentColor" stroke="currentColor" strokeWidth="1.4" />
    <rect x="16.3" y="10" width="3.4" height="6" rx="0.8" fill="currentColor" fillOpacity="0.35" stroke="currentColor" strokeWidth="1.4" />
  </svg>
)

/** FIIs: prédio comercial com janelas e porta. */
export const RealEstateIcon: IconRenderer = (s) => (
  <svg {...svgProps(s)}>
    <path d="M4.5 20V8.5L12 4l7.5 4.5V20" {...stroke} fill="currentColor" fillOpacity="0.14" />
    <path d="M3 20h18" {...stroke} />
    <path d="M8.5 10h1.5M14 10h1.5M8.5 13.5h1.5M14 13.5h1.5" {...stroke} strokeWidth={2} />
    <path d="M10.5 20v-3.2h3V20" {...stroke} />
  </svg>
)

/** ETF Nacional: cesta diversificada (gráfico de pizza segmentado). */
export const EtfBrIcon: IconRenderer = (s) => (
  <svg {...svgProps(s)}>
    <circle cx="12" cy="12" r="8" {...stroke} />
    <path d="M12 4v8l6.9 4" {...stroke} />
    <path d="M12 12 5.1 16" {...stroke} />
    <path d="M12 4a8 8 0 0 1 6.9 12L12 12V4Z" fill="currentColor" fillOpacity="0.3" />
  </svg>
)

/** ETF Internacional: globo com cesta de ativos. */
export const EtfIntlIcon: IconRenderer = (s) => (
  <svg {...svgProps(s)}>
    <circle cx="11" cy="11" r="7.5" {...stroke} />
    <path d="M3.5 11h15M11 3.5c2 2.1 3 4.6 3 7.5s-1 5.4-3 7.5c-2-2.1-3-4.6-3-7.5s1-5.4 3-7.5Z" {...stroke} strokeWidth={1.4} />
    <circle cx="18" cy="18" r="3.6" fill="currentColor" stroke="var(--color-surface, #fff)" strokeWidth="1.2" />
    <path d="M18 14.4V18h3.6" stroke="var(--color-surface, #fff)" strokeWidth="1.2" />
  </svg>
)

/** BDR: recibo de ativo estrangeiro negociado no Brasil (globo + seta de conexão). */
export const BdrIcon: IconRenderer = (s) => (
  <svg {...svgProps(s)}>
    <circle cx="8.5" cy="9" r="5" {...stroke} />
    <path d="M3.5 9h10M8.5 4c1.3 1.4 2 3.1 2 5s-.7 3.6-2 5c-1.3-1.4-2-3.1-2-5s.7-3.6 2-5Z" {...stroke} strokeWidth={1.3} />
    <rect x="13" y="13" width="7.5" height="7" rx="1.6" {...stroke} fill="currentColor" fillOpacity="0.2" />
    <path d="M13.8 7.5c2.6.2 4.4 1.9 4.7 4.4m0 0-1.6-1.3m1.6 1.3 1.3-1.6" {...stroke} strokeWidth={1.4} />
  </svg>
)

/** Stocks (EUA): gráfico de barras ascendente com cifrão. */
export const StockUsIcon: IconRenderer = (s) => (
  <svg {...svgProps(s)}>
    <path d="M4 20h16" {...stroke} />
    <rect x="5" y="13" width="3" height="5" rx="0.7" fill="currentColor" fillOpacity="0.35" />
    <rect x="10.5" y="9.5" width="3" height="8.5" rx="0.7" fill="currentColor" fillOpacity="0.6" />
    <rect x="16" y="11" width="3" height="7" rx="0.7" fill="currentColor" fillOpacity="0.35" />
    <path d="M17.5 3.5v5M19 4.6c-.3-.5-.9-.8-1.6-.8-.9 0-1.5.5-1.5 1.1 0 1.5 3.2.8 3.2 2.3 0 .6-.7 1.1-1.6 1.1-.7 0-1.3-.3-1.6-.8" {...stroke} strokeWidth={1.3} />
  </svg>
)

/** Cripto genérica: moeda hexagonal com nós de blockchain. */
export const CryptoGenericIcon: IconRenderer = (s) => (
  <svg {...svgProps(s)}>
    <path d="M12 3 19.8 7.5v9L12 21l-7.8-4.5v-9L12 3Z" {...stroke} fill="currentColor" fillOpacity="0.14" />
    <path d="M12 8v8M8.5 10l3.5 2 3.5-2M8.5 14l3.5-2 3.5 2" {...stroke} strokeWidth={1.4} />
    <circle cx="12" cy="8" r="1.1" fill="currentColor" />
    <circle cx="12" cy="16" r="1.1" fill="currentColor" />
  </svg>
)

/** Fallback neutro. */
export const GenericAssetIcon: IconRenderer = (s) => (
  <svg {...svgProps(s)}>
    <path d="M4 20h16M6.5 16.5v-4M11 16.5V8M15.5 16.5v-6M20 16.5V5.5" {...stroke} />
  </svg>
)

/* ------------------------------------------------------------------ */
/* Ícones de criptomoedas específicas                                  */
/* ------------------------------------------------------------------ */

export interface CryptoBrand {
  symbol: string
  bg: string
  fg: string
  renderSvg: IconRenderer
}

const glyph =
  (text: string, fontSize = 13): IconRenderer =>
  (s) => (
    <svg {...svgProps(s)}>
      <text
        x="12"
        y="12"
        textAnchor="middle"
        dominantBaseline="central"
        fontSize={fontSize}
        fontWeight={800}
        fontFamily="system-ui, -apple-system, Segoe UI, sans-serif"
        fill="currentColor"
      >
        {text}
      </text>
    </svg>
  )

const brand = (symbol: string, fg: string, renderSvg: IconRenderer, alpha = 0.16): CryptoBrand => ({
  symbol,
  fg,
  bg: `color-mix(in oklch, ${fg} ${Math.round(alpha * 100)}%, transparent)`,
  renderSvg,
})

export const KNOWN_CRYPTO_BRANDS: Record<string, CryptoBrand> = {
  BTC: brand('BTC', '#f7931a', (s) => (
    <svg {...svgProps(s)}>
      <path
        d="M15.4 11.3c.7-.4 1.2-1.1 1.1-2.1-.1-1.5-1.4-2.1-3.1-2.2V5h-1.4v2h-1.1V5H9.5v2H7.5v1.5h1.1c.4 0 .6.2.6.5v6c0 .3-.2.5-.6.5H7.5V17h2v2h1.4v-2h1.1v2h1.4v-2c2.1-.1 3.6-.8 3.8-2.6.1-1.2-.6-2-1.8-2.1ZM10.9 8.4h1.6c1 0 1.7.3 1.7 1.1 0 .8-.7 1.2-1.8 1.2h-1.5V8.4Zm1.9 7.1h-1.9v-2.6h2c1.2 0 2 .4 2 1.3 0 1-.8 1.3-2.1 1.3Z"
        fill="currentColor"
      />
    </svg>
  )),
  ETH: brand('ETH', '#627eea', (s) => (
    <svg {...svgProps(s)}>
      <path d="M12 3L6.5 12.2 12 15.5l5.5-3.3L12 3Z" fill="currentColor" fillOpacity="0.85" />
      <path d="M12 16.8L6.5 13.5 12 21l5.5-7.5-5.5 3.3Z" fill="currentColor" />
    </svg>
  )),
  SOL: brand('SOL', '#9945ff', (s) => (
    <svg {...svgProps(s)}>
      <path d="M6.5 7.5h12l-2 2.5h-12l2-2.5Zm-2 4.5h12l2 2.5h-12l-2-2.5Zm4 4.5h12l-2 2.5h-12l2-2.5Z" fill="currentColor" />
    </svg>
  )),
  USDT: brand('USDT', '#26a17b', (s) => (
    <svg {...svgProps(s)}>
      <path d="M6 6h12v2.4h-4.7v2.1c2.8.2 4.9.8 4.9 1.6s-2.1 1.4-4.9 1.6V19h-2.6v-5.3c-2.8-.2-4.9-.8-4.9-1.6s2.1-1.4 4.9-1.6V8.4H6V6Z" fill="currentColor" />
    </svg>
  )),
  USDC: brand('USDC', '#2775ca', (s) => (
    <svg {...svgProps(s)}>
      <circle cx="12" cy="12" r="8.5" stroke="currentColor" strokeWidth="2" />
      <path d="M12 7v10M9.8 9.8c0-1 .9-1.6 2.2-1.6s2.2.6 2.2 1.5c0 2-4.4 1.5-4.4 3.6 0 1 .9 1.6 2.2 1.6s2.2-.6 2.2-1.6" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  )),
  BNB: brand('BNB', '#e0a800', (s) => (
    <svg {...svgProps(s)}>
      <path d="M12 4.5l3.2 3.2-1.6 1.6L12 7.7l-1.6 1.6-1.6-1.6L12 4.5Zm-5.2 5.2l1.6-1.6 1.6 1.6-1.6 1.6-1.6-1.6Zm10.4 0l1.6 1.6-1.6 1.6-1.6-1.6 1.6-1.6ZM12 10.4l1.6 1.6-1.6 1.6-1.6-1.6 1.6-1.6Zm0 5.9l1.6-1.6 1.6 1.6L12 19.5l-3.2-3.2 1.6-1.6 1.6 1.6Z" fill="currentColor" />
    </svg>
  )),
  XRP: brand('XRP', '#23292f', (s) => (
    <svg {...svgProps(s)}>
      <path d="M6 6l4.2 4.2a2.5 2.5 0 0 0 3.6 0L18 6M6 18l4.2-4.2a2.5 2.5 0 0 1 3.6 0L18 18" stroke="currentColor" strokeWidth="2.1" strokeLinecap="round" />
    </svg>
  ), 0.12),
  ADA: brand('ADA', '#0033ad', (s) => (
    <svg {...svgProps(s)}>
      <circle cx="12" cy="12" r="3" fill="currentColor" />
      <circle cx="12" cy="5.5" r="1.3" fill="currentColor" />
      <circle cx="12" cy="18.5" r="1.3" fill="currentColor" />
      <circle cx="6.4" cy="8.7" r="1.3" fill="currentColor" />
      <circle cx="17.6" cy="15.3" r="1.3" fill="currentColor" />
      <circle cx="6.4" cy="15.3" r="1.3" fill="currentColor" />
      <circle cx="17.6" cy="8.7" r="1.3" fill="currentColor" />
    </svg>
  )),
  LINK: brand('LINK', '#2a5ada', (s) => (
    <svg {...svgProps(s)}>
      <polygon points="12,4.5 18.5,8.2 18.5,15.8 12,19.5 5.5,15.8 5.5,8.2" stroke="currentColor" strokeWidth="2.1" fill="none" />
    </svg>
  )),
  DOGE: brand('DOGE', '#c2a633', glyph('Ð', 15)),
  LTC: brand('LTC', '#345d9d', glyph('Ł', 15)),
  BCH: brand('BCH', '#0ac18e', glyph('₿', 14)),
  DOT: brand('DOT', '#e6007a', (s) => (
    <svg {...svgProps(s)}>
      <ellipse cx="12" cy="5.2" rx="3.4" ry="1.9" fill="currentColor" />
      <ellipse cx="12" cy="18.8" rx="3.4" ry="1.9" fill="currentColor" />
      <ellipse cx="6.1" cy="8.6" rx="3.4" ry="1.9" transform="rotate(-60 6.1 8.6)" fill="currentColor" />
      <ellipse cx="17.9" cy="8.6" rx="3.4" ry="1.9" transform="rotate(60 17.9 8.6)" fill="currentColor" />
      <ellipse cx="6.1" cy="15.4" rx="3.4" ry="1.9" transform="rotate(60 6.1 15.4)" fill="currentColor" />
      <ellipse cx="17.9" cy="15.4" rx="3.4" ry="1.9" transform="rotate(-60 17.9 15.4)" fill="currentColor" />
    </svg>
  )),
  AVAX: brand('AVAX', '#e84142', (s) => (
    <svg {...svgProps(s)}>
      <path d="M10.6 5.3a1.6 1.6 0 0 1 2.8 0l1.3 2.3-4.8 8.4H6.3a1.2 1.2 0 0 1-1-1.8l5.3-8.9Z" fill="currentColor" />
      <path d="M15.7 9.6a1.1 1.1 0 0 1 1.9 0l2.9 5a1.2 1.2 0 0 1-1 1.8h-5.8a1.2 1.2 0 0 1-1-1.8l3-5Z" fill="currentColor" />
    </svg>
  )),
  MATIC: brand('MATIC', '#8247e5', (s) => (
    <svg {...svgProps(s)}>
      <path d="M15.8 9.1 13 7.5l-2.8 1.6v3.2L13 13.9l2.8-1.6V9.1ZM10.2 11.7 7.4 10.1l-2.8 1.6v3.2l2.8 1.6 2.8-1.6M15.8 12.3l2.8 1.6v3.2l-2.8 1.6-2.8-1.6" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round" />
    </svg>
  )),
  UNI: brand('UNI', '#ff007a', glyph('UNI', 8)),
  ATOM: brand('ATOM', '#2e3148', (s) => (
    <svg {...svgProps(s)}>
      <circle cx="12" cy="12" r="1.8" fill="currentColor" />
      <ellipse cx="12" cy="12" rx="8.5" ry="3.2" stroke="currentColor" strokeWidth="1.5" />
      <ellipse cx="12" cy="12" rx="8.5" ry="3.2" transform="rotate(60 12 12)" stroke="currentColor" strokeWidth="1.5" />
      <ellipse cx="12" cy="12" rx="8.5" ry="3.2" transform="rotate(-60 12 12)" stroke="currentColor" strokeWidth="1.5" />
    </svg>
  ), 0.12),
  NEAR: brand('NEAR', '#00c08b', (s) => (
    <svg {...svgProps(s)}>
      <path d="M7 18V6l10 12V6" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )),
  TRX: brand('TRX', '#ff060a', (s) => (
    <svg {...svgProps(s)}>
      <path d="M4.5 5.5 19.5 8.5 11 20 4.5 5.5Zm0 0L11 20m8.5-11.5-8 3.3L4.5 5.5" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
    </svg>
  )),
  XLM: brand('XLM', '#14b6e7', (s) => (
    <svg {...svgProps(s)}>
      <path d="M5 14.5 19 8M5 16.5 19 10M17.6 6.6A7 7 0 0 0 5.4 13M6.4 17.4A7 7 0 0 0 18.6 11" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
    </svg>
  )),
  TON: brand('TON', '#0098ea', (s) => (
    <svg {...svgProps(s)}>
      <path d="M6 6h12l-6 12L6 6Zm6 0v12" stroke="currentColor" strokeWidth="1.9" strokeLinejoin="round" />
    </svg>
  )),
  SUI: brand('SUI', '#4da2ff', (s) => (
    <svg {...svgProps(s)}>
      <path d="M12 3.5c3 3.6 6 6.9 6 10.4a6 6 0 0 1-12 0c0-3.5 3-6.8 6-10.4Z" stroke="currentColor" strokeWidth="1.8" fill="currentColor" fillOpacity="0.25" />
    </svg>
  )),
  SHIB: brand('SHIB', '#ffa409', glyph('SHIB', 7)),
}

// Aliases de rebranding / símbolos equivalentes
KNOWN_CRYPTO_BRANDS.POL = { ...KNOWN_CRYPTO_BRANDS.MATIC, symbol: 'POL' }

/**
 * Tickers reconhecidos como cripto mesmo quando a classe não vem informada.
 * Inclui os que só usam o ícone genérico de cripto.
 */
export const KNOWN_CRYPTO_TICKERS = new Set<string>([
  ...Object.keys(KNOWN_CRYPTO_BRANDS),
  'AAVE',
  'ALGO',
  'APT',
  'ARB',
  'FET',
  'INJ',
  'LDO',
  'MKR',
  'OP',
  'RENDER',
  'RNDR',
  'XMR',
])
