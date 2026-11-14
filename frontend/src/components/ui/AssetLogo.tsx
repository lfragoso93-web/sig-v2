import { useEffect, useState } from 'react'
import type { CSSProperties, ElementType } from 'react'
import {
  BdrIcon,
  CryptoGenericIcon,
  EtfBrIcon,
  EtfIntlIcon,
  FixedIncomeIcon,
  GenericAssetIcon,
  KNOWN_CRYPTO_BRANDS,
  KNOWN_CRYPTO_TICKERS,
  RealEstateIcon,
  StockBrIcon,
  StockUsIcon,
  TreasuryIcon,
  type IconRenderer,
} from './assetIcons'

export interface AssetLogoProps {
  ticker: string
  assetType?: string | null
  size?: number
  logoUrl?: string | null
}

const US_STOCK_LOGO_ALIAS: Record<string, string> = {
  NVDA: 'NVDC34',
  AMZN: 'AMZO34',
  GOOGL: 'GOGL34',
  GOOG: 'GOGL34',
  DIS: 'DISB34',
  KO: 'COCA34',
  MELI: 'MELI34',
  JNJ: 'JNJB34',
  PG: 'PGCO34',
  V: 'VISA34',
  MA: 'MSCD34',
  JPM: 'JPMC34',
  WMT: 'WALM34',
  HD: 'HOME34',
  MCD: 'MCDC34',
  INTC: 'ITLC34',
  AMD: 'A1MD34',
  BABA: 'BABA34',
  NIKE: 'NIKE34',
  NKE: 'NIKE34',
  SBUX: 'SBUB34',
  PYPL: 'PYPL34',
  ADBE: 'ADBE34',
  QCOM: 'QCOM34',
  AVGO: 'AVGO34',
  PFIZ: 'PFIZ34',
  PFE: 'PFIZ34',
  ABBV: 'ABBV34',
  UNH: 'UNHH34',
  CVX: 'CHVX34',
  XOM: 'EXXO34',
  BAC: 'BOAC34',
  WFC: 'WFCO34',
  GS: 'GSGI34',
  ORCL: 'ORCL34',
  CSCO: 'CSCO34',
  IBM: 'IBMB34',
  AIRB: 'AIRB34',
  ABNB: 'AIRB34',
  UBER: 'U1BE34',
}

const KNOWN_US_STOCK_DIRECT = new Set(['AAPL', 'MSFT', 'TSLA', 'META', 'NFLX'])

const B3_TICKER_REGEX = /^[A-Z]{4}(3|4|5|6|11|34|35)$/i

export function deriveCompanyLogoUrl(ticker?: string | null, assetType?: string | null): string | null {
  if (!ticker || !ticker.trim()) return null
  const clean = ticker.trim().toUpperCase()
  const normType = (assetType ?? '').trim().toUpperCase()

  // Tesouro, Renda Fixa e Cripto sempre usam seus icones dedicados
  if (
    normType === 'TESOURO_DIRETO' ||
    normType === 'TESOURO' ||
    normType === 'RENDA_FIXA' ||
    normType === 'CRIPTO' ||
    normType === 'CRIPTOMOEDA'
  ) {
    return null
  }

  // Stock americano
  if (normType === 'STOCK' || normType === 'STOCKS') {
    if (clean in US_STOCK_LOGO_ALIAS) {
      return `https://icons.brapi.dev/icons/${US_STOCK_LOGO_ALIAS[clean]}.svg`
    }
    if (KNOWN_US_STOCK_DIRECT.has(clean)) {
      return `https://icons.brapi.dev/icons/${clean}.svg`
    }
    return null
  }

  // Ativos B3 (Acao, BDR, FII, ETF)
  if (B3_TICKER_REGEX.test(clean)) {
    return `https://icons.brapi.dev/icons/${clean}.svg`
  }

  return null
}

function normalizeCryptoSymbol(rawTicker: string): string {
  const clean = rawTicker.trim().toUpperCase()
  return clean
    .replace(/[-/](USD|BRL|USDT|USDC|BUSD|EUR)$/i, '')
    .replace(/[^A-Z0-9]/g, '')
}

/**
 * Logos que o provider devolve quando não tem a imagem real do ativo
 * (ex.: o ícone genérico da própria BRAPI). Nesses casos usamos o ícone da classe.
 */
const PLACEHOLDER_LOGO_PATTERNS = [/\/BRAPI\.(svg|png)(\?.*)?$/i, /placeholder/i, /default[-_]?logo/i]

export function isPlaceholderLogo(url?: string | null): boolean {
  if (!url || !url.trim()) return true
  return PLACEHOLDER_LOGO_PATTERNS.some((pattern) => pattern.test(url.trim()))
}

type ClassIconProps = { size?: number; strokeWidth?: number; className?: string; style?: CSSProperties }

function asComponent(renderer: IconRenderer): ElementType<ClassIconProps> {
  const Component = ({ size = 16, className, style }: ClassIconProps) => (
    <span className={className} style={{ display: 'inline-flex', lineHeight: 0, ...style }}>
      {renderer(size)}
    </span>
  )
  return Component
}

interface ClassVisual {
  Icon: ElementType<ClassIconProps>
  render: IconRenderer
  color: string
  bg: string
}

const tint = (color: string, alpha = 0.14) => `oklch(from ${color} l c h / ${alpha})`

function visual(render: IconRenderer, color: string): ClassVisual {
  return { Icon: asComponent(render), render, color, bg: tint(color) }
}

const CLASS_VISUALS = {
  TESOURO: visual(TreasuryIcon, 'var(--color-gold)'),
  RENDA_FIXA: visual(FixedIncomeIcon, 'var(--color-success)'),
  FII: visual(RealEstateIcon, 'var(--color-blue)'),
  ACAO: visual(StockBrIcon, 'var(--color-primary)'),
  ETF_NACIONAL: visual(EtfBrIcon, 'var(--color-purple)'),
  ETF_INTERNACIONAL: visual(EtfIntlIcon, 'var(--color-blue)'),
  BDR: visual(BdrIcon, 'var(--color-purple)'),
  STOCK: visual(StockUsIcon, 'var(--color-orange)'),
  CRIPTO: visual(CryptoGenericIcon, 'var(--color-orange)'),
  DEFAULT: {
    Icon: asComponent(GenericAssetIcon),
    render: GenericAssetIcon,
    color: 'var(--color-text-muted)',
    bg: 'var(--color-surface-offset)',
  } as ClassVisual,
}

export function resolveClassVisual(assetType?: string | null): ClassVisual {
  const norm = (assetType ?? '').trim().toUpperCase()
  switch (norm) {
    case 'TESOURO_DIRETO':
    case 'TESOURO':
      return CLASS_VISUALS.TESOURO
    case 'RENDA_FIXA':
      return CLASS_VISUALS.RENDA_FIXA
    case 'FII':
      return CLASS_VISUALS.FII
    case 'ACAO':
    case 'ACAO_NACIONAL':
    case 'ACOES':
      return CLASS_VISUALS.ACAO
    case 'ETF':
    case 'ETF_NACIONAL':
    case 'ETF_BR':
      return CLASS_VISUALS.ETF_NACIONAL
    case 'ETF_INTERNACIONAL':
    case 'ETF_INT':
      return CLASS_VISUALS.ETF_INTERNACIONAL
    case 'BDR':
      return CLASS_VISUALS.BDR
    case 'STOCK':
    case 'STOCKS':
      return CLASS_VISUALS.STOCK
    case 'CRIPTO':
    case 'CRIPTOMOEDA':
      return CLASS_VISUALS.CRIPTO
    default:
      return CLASS_VISUALS.DEFAULT
  }
}

/**
 * Renderiza a representação visual do ativo sem chamadas externas no render:
 *   1. logoUrl persistido (ignorando placeholders genéricos do provider)
 *   2. Ícone próprio da criptomoeda (BTC, ETH, SOL, ADA, DOGE, DOT, AVAX...)
 *   3. Ícone próprio da classe (Tesouro, Renda Fixa, FII, Ação, ETF, BDR, Stock, Cripto)
 *   4. Fallback neutro
 */
export default function AssetLogo({ ticker, assetType, size = 24, logoUrl }: AssetLogoProps) {
  const [imgFailed, setImgFailed] = useState(false)

  useEffect(() => {
    setImgFailed(false)
  }, [logoUrl, ticker])

  const normType = (assetType ?? '').trim().toUpperCase()
  const cryptoSymbol = normalizeCryptoSymbol(ticker ?? '')
  const isCryptoContext =
    normType === 'CRIPTO' ||
    normType === 'CRIPTOMOEDA' ||
    (!normType && KNOWN_CRYPTO_TICKERS.has(cryptoSymbol))
  const cryptoBrand = isCryptoContext ? KNOWN_CRYPTO_BRANDS[cryptoSymbol] : undefined
  const classVisual = resolveClassVisual(normType || (isCryptoContext ? 'CRIPTO' : undefined))

  const iconSize = Math.max(12, Math.round(size * 0.58))

  const baseContainerStyle: CSSProperties = {
    width: size,
    height: size,
    borderRadius: '50%',
    overflow: 'hidden',
    flexShrink: 0,
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
  }

  const isPlaceholder = isPlaceholderLogo(logoUrl)
  const candidateUrl =
    logoUrl && !isPlaceholder
      ? logoUrl
      : logoUrl == null
        ? deriveCompanyLogoUrl(ticker, normType)
        : null

  if (candidateUrl && !imgFailed) {
    return (
      <div
        style={{
          ...baseContainerStyle,
          background: 'var(--color-surface-offset)',
          border: '1px solid oklch(from var(--color-text) l c h / 0.08)',
        }}
      >
        <img
          src={candidateUrl}
          alt={ticker}
          width={size}
          height={size}
          loading="lazy"
          onError={() => setImgFailed(true)}
          style={{ width: size, height: size, objectFit: 'contain', display: 'block' }}
        />
      </div>
    )
  }

  if (cryptoBrand) {
    return (
      <div
        data-testid={`asset-logo-crypto-${cryptoBrand.symbol}`}
        title={ticker}
        style={{
          ...baseContainerStyle,
          background: cryptoBrand.bg,
          color: cryptoBrand.fg,
          border: `1px solid color-mix(in oklch, ${cryptoBrand.fg} 30%, transparent)`,
        }}
      >
        {cryptoBrand.renderSvg(iconSize)}
      </div>
    )
  }

  return (
    <div
      data-testid={`asset-logo-class-${normType || 'FALLBACK'}`}
      title={ticker}
      style={{
        ...baseContainerStyle,
        background: classVisual.bg,
        color: classVisual.color,
        border: '1px solid oklch(from var(--color-text) l c h / 0.07)',
      }}
    >
      {classVisual.render(iconSize)}
    </div>
  )
}
