/**
 * LogoSGI — marca visual do SIG v2
 *
 * Variantes:
 *   <LogoSGI size={24} iconOnly />          → só ícone (favicon/sidebar colapsada)
 *   <LogoSGI size={26} />                   → ícone + wordmark (sidebar desktop)
 *   <LogoSGI size={40} variant="auth" />    → ícone grande + nome + subtítulo (login)
 */

interface Props {
  /** Altura do ícone em px. Default: 28 */
  size?: number
  /** Exibe apenas o ícone, sem wordmark */
  iconOnly?: boolean
  /** Variante de contexto: altera proporções do texto */
  variant?: 'default' | 'auth'
  className?: string
}

export default function LogoSGI({
  size = 28,
  iconOnly = false,
  variant = 'default',
  className,
}: Props) {
  const isAuth = variant === 'auth'
  const r      = size / 28   // fator de escala

  return (
    <span
      className={`inline-flex items-center select-none ${className ?? ''}`}
      style={{ gap: Math.round(8 * r) }}
      aria-label="SIG — Sistema de Gestão de Investimentos"
    >
      {/* ── Ícone ────────────────────────────────────────────── */}
      <svg
        width={size}
        height={size}
        viewBox="0 0 32 32"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden="true"
        style={{ flexShrink: 0 }}
      >
        {/* Fundo com cantos arredondados — teal sólido */}
        <rect width="32" height="32" rx="8" fill="var(--color-primary)" />

        {/* Barras de fundo: representam volume / base de dados */}
        <rect x="5"  y="20" width="4" height="7"  rx="1.5" fill="white" opacity="0.22" />
        <rect x="11" y="15" width="4" height="12" rx="1.5" fill="white" opacity="0.22" />
        <rect x="17" y="11" width="4" height="16" rx="1.5" fill="white" opacity="0.22" />
        <rect x="23" y="7"  width="4" height="20" rx="1.5" fill="white" opacity="0.22" />

        {/* Linha de tendência ascendente — destaque principal */}
        <polyline
          points="5,23 11,17 17,13 23,9"
          stroke="white"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          opacity="0.95"
        />

        {/* Ponto de destaque no pico */}
        <circle cx="23" cy="9" r="2.2" fill="white" />

        {/* Ponto inicial da linha */}
        <circle cx="5" cy="23" r="1.4" fill="white" opacity="0.6" />
      </svg>

      {/* ── Wordmark ─────────────────────────────────────────── */}
      {!iconOnly && (
        <span
          style={{
            display:       'flex',
            flexDirection: 'column',
            lineHeight:    1,
            gap:           isAuth ? Math.round(4 * r) : 0,
          }}
        >
          {/* Nome principal */}
          <span
            style={{
              fontSize:      isAuth ? Math.round(20 * r) : Math.round(13 * r),
              fontWeight:    700,
              letterSpacing: '-0.02em',
              color:         'var(--color-text)',
            }}
          >
            SIG
            <span
              style={{
                marginLeft:    Math.round(3 * r),
                fontSize:      isAuth ? Math.round(11 * r) : Math.round(9.5 * r),
                fontWeight:    500,
                color:         'var(--color-text-muted)',
                letterSpacing: '0',
              }}
            >
              v2
            </span>
          </span>

          {/* Subtítulo — apenas na variante auth */}
          {isAuth && (
            <span
              style={{
                fontSize:      Math.round(11 * r),
                fontWeight:    400,
                color:         'var(--color-text-muted)',
                letterSpacing: '0.01em',
              }}
            >
              Sistema de Gestão de Investimentos
            </span>
          )}
        </span>
      )}
    </span>
  )
}
