import { useState } from 'react'
import { Landmark, Bitcoin, TrendingUp, BarChart2 } from 'lucide-react'

interface Props {
  ticker: string
  assetType: string
  size?: number
  logoUrl?: string | null   // URL do logo persistido pelo onboarding (prioridade maxima)
}

/**
 * Renderiza o logo do ativo em cascata:
 *   1. logoUrl (do banco, coletado pelo onboarding) — maior fidelidade
 *   2. BRAPI favicon ({ticker}.png) — funciona bem para ativos BR
 *   3. Icone SVG por tipo — fallback final sem rede
 *
 * Tipos sem suporte BRAPI (CRIPTO, STOCK, ETF_INT, TESOURO) vao direto
 * para o fallback de icone quando logoUrl nao estiver disponivel.
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

export default function AssetLogo({ ticker, assetType, size = 24, logoUrl }: Props) {
  const norm = assetType.toUpperCase()
  const canUseBrapi = BRAPI_SUPPORTED_TYPES.has(norm) && norm !== 'TESOURO_DIRETO' && norm !== 'TESOURO'

  // Determina a URL inicial a usar: logoUrl do banco tem prioridade
  const initialSrc = logoUrl || (canUseBrapi
    ? `https://brapi.dev/favicon/${ticker.replace(/[^A-Z0-9]/gi, '').toUpperCase()}.png`
    : null
  )

  const [src, setSrc] = useState<string | null>(initialSrc)

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

  if (!src) {
    return (
      <div style={containerStyle}>
        <FallbackIcon assetType={assetType} size={Math.round(size * 0.55)} />
      </div>
    )
  }

  // Se estava usando logoUrl e falhou, tenta BRAPI como segundo passo
  const handleError = () => {
    if (src === logoUrl && canUseBrapi) {
      // Falhou no logo do banco: tenta BRAPI favicon
      setSrc(`https://brapi.dev/favicon/${ticker.replace(/[^A-Z0-9]/gi, '').toUpperCase()}.png`)
    } else {
      // Falhou em tudo: icone SVG
      setSrc(null)
    }
  }

  return (
    <div style={containerStyle}>
      <img
        src={src}
        alt={ticker}
        width={size}
        height={size}
        loading="lazy"
        onError={handleError}
        style={{ width: size, height: size, objectFit: 'contain', display: 'block' }}
      />
    </div>
  )
}
