import { Outlet, Navigate } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import LogoSGI from '@/components/ui/LogoSGI'

export default function AuthLayout() {
  const token = useAuthStore((s) => s.token)
  if (token) return <Navigate to="/carteira" replace />

  return (
    <div className="auth-shell">
      <div className="auth-panel">
        <div className="auth-brand">
          <LogoSGI size={46} variant="auth" />
          <p className="auth-brand-caption" style={{ margin: 0, fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>
            Sistema de Gestão de Investimentos
          </p>
        </div>

        <div className="auth-card">
          <Outlet />
        </div>

        <p className="auth-footer-note">
          SIG v2 &mdash; Uso interno
        </p>
      </div>
    </div>
  )
}
