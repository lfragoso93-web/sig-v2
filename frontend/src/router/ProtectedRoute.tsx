import { Navigate, Outlet } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'

export default function ProtectedRoute({ children }: { children?: React.ReactNode }) {
  const { isAuthenticated, token } = useAuthStore()

  // Verifica tambem o token no localStorage como fallback (hidratacao do zustand persist)
  const hasToken = token || localStorage.getItem('sig_token')

  if (!isAuthenticated && !hasToken) {
    return <Navigate to="/auth/login" replace />
  }

  return children ? <>{children}</> : <Outlet />
}
