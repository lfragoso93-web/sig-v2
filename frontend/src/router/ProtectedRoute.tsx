import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import { useAuth } from '@/contexts/AuthContext'

function LoadingSpinner() {
  return (
    <div style={{
      minHeight: '100dvh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'var(--color-bg)',
    }}>
      <div style={{
        width: 32, height: 32, borderRadius: '50%',
        border: '3px solid var(--color-primary)',
        borderTopColor: 'transparent',
        animation: 'spin 0.7s linear infinite',
      }} />
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  )
}

/**
 * ProtectedRoute — rota protegida do app principal.
 * Redireciona para /welcome se onboarding não concluído.
 */
export default function ProtectedRoute({ children }: { children?: React.ReactNode }) {
  const { token } = useAuthStore()
  const { user, isLoading } = useAuth()
  const location = useLocation()

  const hasToken = token || localStorage.getItem('sig_token')

  if (!hasToken) return <Navigate to="/auth/login" replace />
  if (isLoading) return <LoadingSpinner />

  // Onboarding incompleto → /welcome (nunca redireciona se já estiver lá)
  if (user && !user.onboarding_completed && location.pathname !== '/welcome') {
    return <Navigate to="/welcome" replace />
  }

  return children ? <>{children}</> : <Outlet />
}

/**
 * OnboardingRoute — usada exclusivamente para /welcome.
 * Só garante que o usuário está autenticado; NÃO checa onboarding
 * (evita loop infinito de redirect).
 */
export function OnboardingRoute({ children }: { children: React.ReactNode }) {
  const { token } = useAuthStore()
  const { isLoading } = useAuth()

  const hasToken = token || localStorage.getItem('sig_token')

  if (!hasToken) return <Navigate to="/auth/login" replace />
  if (isLoading) return <LoadingSpinner />

  return <>{children}</>
}
