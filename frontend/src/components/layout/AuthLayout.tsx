import { Outlet, Navigate } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import LogoSGI from '@/components/ui/LogoSGI'

export default function AuthLayout() {
  const token = useAuthStore((s) => s.token)
  if (token) return <Navigate to="/carteira" replace />

  return (
    <div
      className="flex flex-col items-center justify-center px-4 py-12"
      style={{
        minHeight: '100dvh',
        background: 'var(--color-bg)',
      }}
    >
      <div className="w-full max-w-sm">

        {/* ── Header com logo ─────────────────────────────── */}
        <div className="flex flex-col items-center gap-5 mb-10">
          <LogoSGI size={44} variant="auth" />
        </div>

        {/* ── Card de conteúdo (login/registro) ───────────── */}
        <div
          style={{
            background:   'var(--color-surface)',
            border:       '1px solid oklch(from var(--color-text) l c h / 0.08)',
            borderRadius: 'var(--radius-xl)',
            boxShadow:    'var(--shadow-md)',
            padding:      'clamp(1.5rem, 5vw, 2rem)',
          }}
        >
          <Outlet />
        </div>

        {/* ── Rodapé discreto ─────────────────────────────── */}
        <p
          className="text-center mt-6"
          style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-faint)' }}
        >
          SIG v2 &mdash; Uso interno
        </p>
      </div>
    </div>
  )
}
