/**
 * LogoSGI — marca do Sistema de Gestão de Investimentos
 * Compatível com qualquer tamanho: 16px até 200px.
 * Usa currentColor para funcionar em light/dark mode.
 */
interface Props {
  /** Altura do componente (width é proporcional). Default: 28 */
  size?: number
  /** Se true, exibe apenas o ícone sem o wordmark */
  iconOnly?: boolean
  className?: string
}

export default function LogoSGI({ size = 28, iconOnly = false, className }: Props) {
  const iconSize = size
  const ratio    = iconSize / 28

  return (
    <span
      className={`inline-flex items-center gap-[${Math.round(6 * ratio)}px] select-none ${className ?? ''}`}
      style={{ gap: Math.round(7 * ratio) }}
      aria-label="SGI — Sistema de Gestão de Investimentos"
    >
      {/* ── Ícone: mini sparkline estilizado dentro de quadrado arredondado ── */}
      <svg
        width={iconSize}
        height={iconSize}
        viewBox="0 0 28 28"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden="true"
      >
        {/* Fundo arredondado — teal semitransparente */}
        <rect
          x="0" y="0" width="28" height="28" rx="7"
          fill="var(--color-primary)"
          opacity="1"
        />
        {/* Sparkline ascendente — 3 barras de alturas diferentes */}
        <rect x="5"  y="17" width="4" height="6"  rx="1.5" fill="white" opacity="0.55" />
        <rect x="12" y="12" width="4" height="11" rx="1.5" fill="white" opacity="0.78" />
        <rect x="19" y="6"  width="4" height="17" rx="1.5" fill="white" opacity="1"    />
        {/* Linha de tendência diagonal */}
        <path
          d="M7 18 L14 13 L21 7"
          stroke="white"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          opacity="0.9"
        />
      </svg>

      {/* ── Wordmark ── */}
      {!iconOnly && (
        <span
          style={{
            fontSize:      Math.round(13 * ratio),
            fontWeight:    700,
            letterSpacing: '-0.02em',
            lineHeight:    1,
            color:         'var(--color-text)',
          }}
        >
          SGI
          <span
            style={{
              marginLeft:  Math.round(3 * ratio),
              fontSize:    Math.round(10 * ratio),
              fontWeight:  500,
              color:       'var(--color-text-muted)',
              letterSpacing: '0',
            }}
          >
            Investimentos
          </span>
        </span>
      )}
    </span>
  )
}
