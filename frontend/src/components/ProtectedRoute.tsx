import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'

export default function ProtectedRoute() {
  const { isAuthenticated, isLoading, user } = useAuth()
  const location = useLocation()

  if (isLoading) {
    return (
      <div style={{
        minHeight: '100dvh', display: 'flex', alignItems: 'center',
        justifyContent: 'center', background: 'var(--color-bg)',
        flexDirection: 'column', gap: '0.75rem',
      }}>
        <div style={{
          width: 32, height: 32,
          border: '2px solid var(--color-primary)',
          borderTopColor: 'transparent',
          borderRadius: '50%',
          animation: 'spin 0.7s linear infinite',
        }} />
        <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>Carregando...</span>
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  // Redireciona para onboarding se nao concluido e nao esta la ainda
  if (user && !user.onboarding_completed && location.pathname !== '/welcome') {
    return <Navigate to="/welcome" replace />
  }

  // Ja concluiu onboarding mas tentou acessar /welcome diretamente
  if (user?.onboarding_completed && location.pathname === '/welcome') {
    return <Navigate to="/carteira" replace />
  }

  return <Outlet />
}
