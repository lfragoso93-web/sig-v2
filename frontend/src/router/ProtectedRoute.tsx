import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import { useAuth } from '@/contexts/AuthContext'

export default function ProtectedRoute({ children }: { children?: React.ReactNode }) {
  const { token } = useAuthStore()
  const { user, isLoading } = useAuth()
  const location = useLocation()

  const hasToken = token || localStorage.getItem('sig_token')

  // Sem token algum → manda para login imediatamente
  if (!hasToken) {
    return <Navigate to="/auth/login" replace />
  }

  // Tem token mas ainda está carregando o usuário → aguarda
  if (isLoading) {
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

  // Usuário carregado — checa onboarding
  // Evita loop: não redireciona se já está em /welcome
  if (user && !user.onboarding_completed && location.pathname !== '/welcome') {
    return <Navigate to="/welcome" replace />
  }

  return children ? <>{children}</> : <Outlet />
}
