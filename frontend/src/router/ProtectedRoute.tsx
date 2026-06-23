import { Navigate, Outlet } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import { useAuth } from '@/contexts/AuthContext'

export default function ProtectedRoute({ children }: { children?: React.ReactNode }) {
  const { isAuthenticated, token } = useAuthStore()
  const { user, isLoading } = useAuth()

  // Aguarda hidratação do contexto de auth
  const hasToken = token || localStorage.getItem('sig_token')

  if (!isAuthenticated && !hasToken) {
    return <Navigate to="/auth/login" replace />
  }

  // Enquanto carrega o usuário, não redireciona ainda
  if (isLoading) return null

  // Usuário autenticado mas onboarding não concluído → welcome
  if (user && !user.onboarding_completed) {
    // Evita loop: se já estiver em /welcome, não redireciona de novo
    if (typeof window !== 'undefined' && window.location.pathname === '/welcome') {
      return children ? <>{children}</> : <Outlet />
    }
    return <Navigate to="/welcome" replace />
  }

  return children ? <>{children}</> : <Outlet />
}
