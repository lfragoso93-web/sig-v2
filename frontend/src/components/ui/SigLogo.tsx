/**
 * SigLogo — Marca visual do SIG v2
 *
 * Uso:
 *   <SigLogo size={32} />           → só ícone
 *   <SigLogo size={32} showName />   → ícone + texto "SIG"
 *   <SigLogo size={48} variant="auth" /> → versão grande para login
 */

interface SigLogoProps {
  /** Tamanho do ícone SVG em px (padrão: 32) */
  size?: number
  /** Exibir o nome "SIG" ao lado do ícone (padrão: false) */
  showName?: boolean
  /** Variante visual */
  variant?: 'default' | 'auth' | 'sidebar'
  className?: string
}

export default function SigLogo({
  size = 32,
  showName = false,
  variant = 'default',
  className = '',
}: SigLogoProps) {
  const isAuth    = variant === 'auth'
  const isSidebar = variant === 'sidebar'

  return (
    <div
      className={`flex items-center gap-2.5 ${className}`}
      style={{ userSelect: 'none' }}
    >
      {/* ── Ícone SVG ─────────────────────────────────────── */}
      <svg
        width={size}
        height={size}
        viewBox="0 0 48 48"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-label="SIG v2"
        role="img"
        style={{ flexShrink: 0 }}
      >
        {/* Fundo arredondado */}
        <rect width="48" height="48" rx="12" fill="var(--color-primary)" />

        {/* Linha de gráfico ascendente */}
        <polyline
          points="8,34 17,22 24,27 37,13"
          stroke="white"
          strokeWidth="3"
          strokeLinecap="round"
          strokeLinejoin="round"
          fill="none"
          opacity="0.95"
        />

        {/* Ponto de destaque no pico */}
        <circle cx="37" cy="13" r="2.8" fill="white" />

        {/* Linha de base sutil */}
        <line
          x1="8" y1="37" x2="40" y2="37"
          stroke="white"
          strokeWidth="1.5"
          strokeLinecap="round"
          opacity="0.28"
        />
      </svg>

      {/* ── Texto ─────────────────────────────────────────── */}
      {(showName || isAuth || isSidebar) && (
        <div className="flex flex-col leading-none">
          <span
            style={{
              fontFamily:  'var(--font-body)',
              fontWeight:  700,
              letterSpacing: '-0.02em',
              fontSize: isAuth
                ? 'var(--text-xl, 1.5rem)'
                : isSidebar
                ? 'var(--text-base, 1rem)'
                : 'var(--text-lg, 1.25rem)',
              color: 'var(--color-text)',
              lineHeight: 1,
            }}
          >
            SIG
            <span
              style={{
                fontSize:   '0.6em',
                fontWeight: 500,
                marginLeft: '0.2em',
                color:      'var(--color-text-muted)',
                letterSpacing: '0',
              }}
            >
              v2
            </span>
          </span>
          {isAuth && (
            <span
              style={{
                fontFamily: 'var(--font-body)',
                fontSize:   'var(--text-sm, 0.875rem)',
                fontWeight: 400,
                color:      'var(--color-text-muted)',
                marginTop:  '0.25rem',
                letterSpacing: '0',
              }}
            >
              Sistema de Gestão de Investimentos
            </span>
          )}
        </div>
      )}
    </div>
  )
}
