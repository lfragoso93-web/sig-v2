import { useState } from 'react'
import { Landmark, Bitcoin, TrendingUp, BarChart2 } from 'lucide-react'

interface Props {
  ticker: string
  assetType: string
  size?: number
}

/**
 * Tipos que têm logo na BRAPI: ativos nacionais (ações, FIIs, ETFs nacionais, Tesouro).
 * Internacionais e cripto não têm — usam fallback imediato.
 */
const BRAPI_SUPPORTED_TYPES = new Set([
  'ACAO_NACIONAL', 'ACAO', 'ACOES',
  'FII',
  'ETF_NACIONAL', 'ETF',
  'TESOURO_DIRETO', 'TESOURO',
])

function FallbackIcon({ assetType, size }: { assetType: string; size: number }) {
  const norm = assetType.toUpperCase()
  const iconStyle = { color: 'var(--color-text-faint)' }
  if (norm === 'TESOURO_DIRETO' || norm === 'TESOURO')
    return <Landmark size={size} style={iconStyle} />
  if (norm === 'CRIPTO' || norm === 'CRIPTOMOEDA')
    return <Bitcoin size={size} style={iconStyle} />
  if (norm === 'STOCK' || norm === 'STOCKS' || norm === 'ETF_INTERNACIONAL' || norm === 'ETF_INT')
    return <TrendingUp size={size} style={iconStyle} />
  return <BarChart2 size={size} style={iconStyle} />
}

export default function AssetLogo({ ticker, assetType, size = 24 }: Props) {
  const norm = assetType.toUpperCase()
  const canUseBrapi = BRAPI_SUPPORTED_TYPES.has(norm)

  // Para Tesouro e tipos sem suporte BRAPI vai direto ao fallback
  const [imgError, setImgError] = useState(
    !canUseBrapi || norm === 'TESOURO_DIRETO' || norm === 'TESOURO'
  )

  const containerStyle: React.CSSProperties = {
    width: size,
    height: size,
    borderRadius: '50%',
    overflow: 'hidden',
    flexShrink: 0,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: 'var(--color-surface-offset)',
  }

  if (imgError) {
    return (
      <div style={containerStyle}>
        <FallbackIcon assetType={assetType} size={Math.round(size * 0.55)} />
      </div>
    )
  }

  // Remove sufixos como F (PETR4F) e normaliza para uppercase
  const cleanTicker = ticker.replace(/[^A-Z0-9]/gi, '').toUpperCase()

  return (
    <div style={containerStyle}>
      <img
        src={`https://brapi.dev/favicon/${cleanTicker}.png`}
        alt={ticker}
        width={size}
        height={size}
        loading="lazy"
        onError={() => setImgError(true)}
        style={{ width: size, height: size, objectFit: 'contain', display: 'block' }}
      />
    </div>
  )
}
