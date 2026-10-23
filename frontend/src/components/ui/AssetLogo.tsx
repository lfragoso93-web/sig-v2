import { useEffect, useState } from 'react'
import {
  Landmark,
  Bitcoin,
  TrendingUp,
  BarChart2,
  Building2,
  ShieldCheck,
  Layers,
  Globe,
  Briefcase,
} from 'lucide-react'

export interface AssetLogoProps {
  ticker: string
  assetType?: string | null
  size?: number
  logoUrl?: string | null
}

interface CryptoBrand {
  symbol: string
  bg: string
  fg: string
  renderSvg: (iconSize: number) => React.ReactNode
}

function normalizeCryptoSymbol(rawTicker: string): string {
  const clean = rawTicker.trim().toUpperCase()
  const withoutPair = clean
    .replace(/[-/](USD|BRL|USDT|USDC|BUSD|EUR)$/i, '')
    .replace(/[^A-Z0-9]/g, '')
  return withoutPair
}

const KNOWN_CRYPTO_BRANDS: Record<string, CryptoBrand> = {
  BTC: {
    symbol: 'BTC',
    bg: 'oklch(0.68 0.17 55 / 0.16)',
    fg: '#f7931a',
    renderSvg: (s) => (
      <svg width={s} height={s} viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path
          d="M15.4 11.3c.7-.4 1.2-1.1 1.1-2.1-.1-1.5-1.4-2.1-3.1-2.2V5h-1.4v2h-1.1V5H9.5v2H7.5v1.5h1.1c.4 0 .6.2.6.5v6c0 .3-.2.5-.6.5H7.5V17h2v2h1.4v-2h1.1v2h1.4v-2c2.1-.1 3.6-.8 3.8-2.6.1-1.2-.6-2-1.8-2.1ZM10.9 8.4h1.6c1 0 1.7.3 1.7 1.1 0 .8-.7 1.2-1.8 1.2h-1.5V8.4Zm1.9 7.1h-1.9v-2.6h2c1.2 0 2 .4 2 1.3 0 1-.8 1.3-2.1 1.3Z"
          fill="currentColor"
        />
      </svg>
    ),
  },
  ETH: {
    symbol: 'ETH',
    bg: 'oklch(0.58 0.16 265 / 0.16)',
    fg: '#627eea',
    renderSvg: (s) => (
      <svg width={s} height={s} viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path d="M12 3L6.5 12.2 12 15.5l5.5-3.3L12 3Z" fill="currentColor" fillOpacity="0.85" />
        <path d="M12 16.8L6.5 13.5 12 21l5.5-7.5-5.5 3.3Z" fill="currentColor" />
      </svg>
    ),
  },
  SOL: {
    symbol: 'SOL',
    bg: 'oklch(0.62 0.2 295 / 0.16)',
    fg: '#9945ff',
    renderSvg: (s) => (
      <svg width={s} height={s} viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path d="M6.5 7.5h12l-2 2.5h-12l2-2.5Zm-2 4.5h12l2 2.5h-12l-2-2.5Zm4 4.5h12l-2 2.5h-12l2-2.5Z" fill="currentColor" />
      </svg>
    ),
  },
  USDT: {
    symbol: 'USDT',
    bg: 'oklch(0.62 0.14 165 / 0.16)',
    fg: '#26a17b',
    renderSvg: (s) => (
      <svg width={s} height={s} viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path d="M6 6h12v2.4h-4.7v2.1c2.8.2 4.9.8 4.9 1.6s-2.1 1.4-4.9 1.6V19h-2.6v-5.3c-2.8-.2-4.9-.8-4.9-1.6s2.1-1.4 4.9-1.6V8.4H6V6Z" fill="currentColor" />
      </svg>
    ),
  },
  USDC: {
    symbol: 'USDC',
    bg: 'oklch(0.58 0.16 245 / 0.16)',
    fg: '#2775ca',
    renderSvg: (s) => (
      <svg width={s} height={s} viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <circle cx="12" cy="12" r="8.5" stroke="currentColor" strokeWidth="2" />
        <path d="M12 7v10M9.8 9.8c0-1 .9-1.6 2.2-1.6s2.2.6 2.2 1.5c0 2-4.4 1.5-4.4 3.6 0 1 .9 1.6 2.2 1.6s2.2-.6 2.2-1.6" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      </svg>
    ),
  },
  BNB: {
    symbol: 'BNB',
    bg: 'oklch(0.75 0.16 85 / 0.16)',
    fg: '#e0a800',
    renderSvg: (s) => (
      <svg width={s} height={s} viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path d="M12 4.5l3.2 3.2-1.6 1.6L12 7.7l-1.6 1.6-1.6-1.6L12 4.5Zm-5.2 5.2l1.6-1.6 1.6 1.6-1.6 1.6-1.6-1.6Zm10.4 0l1.6 1.6-1.6 1.6-1.6-1.6 1.6-1.6ZM12 10.4l1.6 1.6-1.6 1.6-1.6-1.6 1.6-1.6Zm0 5.9l1.6-1.6 1.6 1.6L12 19.5l-3.2-3.2 1.6-1.6 1.6 1.6Z" fill="currentColor" />
      </svg>
    ),
  },
  XRP: {
    symbol: 'XRP',
    bg: 'oklch(0.55 0.08 240 / 0.16)',
    fg: 'var(--color-blue)',
    renderSvg: (s) => (
      <svg width={s} height={s} viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path d="M6 6l4.2 4.2a2.5 2.5 0 0 0 3.6 0L18 6M6 18l4.2-4.2a2.5 2.5 0 0 1 3.6 0L18 18" stroke="currentColor" strokeWidth="2.1" strokeLinecap="round" />
      </svg>
    ),
  },
  ADA: {
    symbol: 'ADA',
    bg: 'oklch(0.55 0.16 250 / 0.16)',
    fg: '#0033ad',
    renderSvg: (s) => (
      <svg width={s} height={s} viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <circle cx="12" cy="12" r="3" fill="currentColor" />
        <circle cx="12" cy="5.5" r="1.3" fill="currentColor" />
        <circle cx="12" cy="18.5" r="1.3" fill="currentColor" />
        <circle cx="6.4" cy="8.7" r="1.3" fill="currentColor" />
        <circle cx="17.6" cy="15.3" r="1.3" fill="currentColor" />
        <circle cx="6.4" cy="15.3" r="1.3" fill="currentColor" />
        <circle cx="17.6" cy="8.7" r="1.3" fill="currentColor" />
      </svg>
    ),
  },
  LINK: {
    symbol: 'LINK',
    bg: 'oklch(0.55 0.16 255 / 0.16)',
    fg: '#2a5ada',
    renderSvg: (s) => (
      <svg width={s} height={s} viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <polygon points="12,4.5 18.5,8.2 18.5,15.8 12,19.5 5.5,15.8 5.5,8.2" stroke="currentColor" strokeWidth="2.1" fill="none" />
      </svg>
    ),
  },
}

const KNOWN_CRYPTO_TICKERS = new Set([
  ...Object.keys(KNOWN_CRYPTO_BRANDS),
  'DOGE',
  'DOT',
  'AVAX',
  'MATIC',
  'POL',
  'LTC',
  'UNI',
  'ATOM',
  'NEAR',
])

export function resolveClassVisual(assetType?: string | null): {
  Icon: React.ElementType
  color: string
  bg: string
} {
  const norm = (assetType ?? '').trim().toUpperCase()
  switch (norm) {
    case 'TESOURO_DIRETO':
    case 'TESOURO':
      return {
        Icon: Landmark,
        color: 'var(--color-gold)',
        bg: 'oklch(from var(--color-gold) l c h / 0.14)',
      }
    case 'RENDA_FIXA':
      return {
        Icon: ShieldCheck,
        color: 'var(--color-success)',
        bg: 'oklch(from var(--color-success) l c h / 0.14)',
      }
    case 'FII':
      return {
        Icon: Building2,
        color: 'var(--color-blue)',
        bg: 'oklch(from var(--color-blue) l c h / 0.14)',
      }
    case 'ACAO':
    case 'ACAO_NACIONAL':
    case 'ACOES':
      return {
        Icon: TrendingUp,
        color: 'var(--color-primary)',
        bg: 'oklch(from var(--color-primary) l c h / 0.14)',
      }
    case 'ETF':
    case 'ETF_NACIONAL':
    case 'ETF_BR':
      return {
        Icon: Layers,
        color: 'var(--color-purple)',
        bg: 'oklch(from var(--color-purple) l c h / 0.14)',
      }
    case 'ETF_INTERNACIONAL':
    case 'ETF_INT':
      return {
        Icon: Globe,
        color: 'var(--color-blue)',
        bg: 'oklch(from var(--color-blue) l c h / 0.14)',
      }
    case 'BDR':
      return {
        Icon: Globe,
        color: 'var(--color-purple)',
        bg: 'oklch(from var(--color-purple) l c h / 0.14)',
      }
    case 'STOCK':
    case 'STOCKS':
      return {
        Icon: Briefcase,
        color: 'var(--color-orange)',
        bg: 'oklch(from var(--color-orange) l c h / 0.14)',
      }
    case 'CRIPTO':
    case 'CRIPTOMOEDA':
      return {
        Icon: Bitcoin,
        color: 'var(--color-orange)',
        bg: 'oklch(from var(--color-orange) l c h / 0.14)',
      }
    default:
      return {
        Icon: BarChart2,
        color: 'var(--color-text-muted)',
        bg: 'var(--color-surface-offset)',
      }
  }
}

/**
 * Renderiza a representação visual canônica do ativo sem chamadas externas de provider no render:
 *   1. logoUrl persistido no banco (se informado e válido)
 *   2. Ícone vetorial canônico de ativo específico (ex.: BTC, ETH, SOL, USDT, USDC, BNB, XRP, ADA, LINK)
 *   3. Ícone semântico da classe do ativo (Tesouro, Renda Fixa, FII, Ação, ETF, BDR, Stock, Cripto)
 *   4. Fallback visual neutro
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
    KNOWN_CRYPTO_TICKERS.has(cryptoSymbol)
  const cryptoBrand = isCryptoContext ? KNOWN_CRYPTO_BRANDS[cryptoSymbol] : undefined
  const classVisual = resolveClassVisual(
    normType || (isCryptoContext ? 'CRIPTO' : undefined),
  )

  const iconSize = Math.max(12, Math.round(size * 0.56))

  const baseContainerStyle: React.CSSProperties = {
    width: size,
    height: size,
    borderRadius: '50%',
    overflow: 'hidden',
    flexShrink: 0,
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
  }

  if (logoUrl && !imgFailed) {
    return (
      <div
        style={{
          ...baseContainerStyle,
          background: 'var(--color-surface-offset)',
          border: '1px solid oklch(from var(--color-text) l c h / 0.08)',
        }}
      >
        <img
          src={logoUrl}
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
          border: '1px solid oklch(from currentColor l c h / 0.2)',
        }}
      >
        {cryptoBrand.renderSvg(iconSize)}
      </div>
    )
  }

  const { Icon } = classVisual
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
      <Icon size={iconSize} strokeWidth={2} aria-hidden="true" />
    </div>
  )
}
