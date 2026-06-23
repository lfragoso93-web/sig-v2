import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '@/services/api'
import { useTheme } from './ThemeContext'
import { useAuthStore } from '@/store/authStore'
import { useAppStore } from '@/store/appStore'

export interface User {
  id: number
  name: string
  email: string
  role: string
  avatar_url?: string | null
  theme_preference?: 'dark' | 'light'
  onboarding_completed?: boolean
}

interface AuthContextData {
  user: User | null
  isLoading: boolean
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<void>
  loginWithTokens: (accessToken: string, refreshToken: string) => Promise<void>
  logout: () => void
  refreshUser: () => Promise<void>
  setUser: React.Dispatch<React.SetStateAction<User | null>>
}

const AuthContext = createContext<AuthContextData>({} as AuthContextData)

function clearAllTokens() {
  localStorage.removeItem('sig_token')
  localStorage.removeItem('sig_refresh')
  localStorage.removeItem('sig-auth')
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const navigate = useNavigate()
  const { setTheme } = useTheme()
  const authStore = useAuthStore()
  const clearSelectedPortfolio = useAppStore((s) => s.clearSelectedPortfolio)

  const loadMe = async (): Promise<User> => {
    const { data } = await api.get<User>('/users/me')
    setUser(data)
    setTheme(data.theme_preference ?? 'dark')
    return data
  }

  useEffect(() => {
    const token = authStore.token ?? localStorage.getItem('sig_token')
    if (!token) {
      setIsLoading(false)
      return
    }
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`
    loadMe()
      .catch(() => {
        authStore.logout()
        clearAllTokens()
        delete api.defaults.headers.common['Authorization']
      })
      .finally(() => setIsLoading(false))
  }, [])

  // login via email+senha (usado pelo LoginPage)
  const login = async (email: string, password: string) => {
    const { data: tokens } = await api.post<{
      access_token: string
      refresh_token: string
    }>('/auth/login', { email, password })
    await loginWithTokens(tokens.access_token, tokens.refresh_token)
  }

  // login direto com tokens (usado pelo RegisterPage apos /auth/register)
  const loginWithTokens = async (accessToken: string, refreshToken: string) => {
    localStorage.setItem('sig_token', accessToken)
    localStorage.setItem('sig_refresh', refreshToken)
    api.defaults.headers.common['Authorization'] = `Bearer ${accessToken}`

    const me = await loadMe()

    authStore.login(accessToken, {
      id: me.id,
      email: me.email,
      name: me.name,
      role: me.role,
      theme_preference: me.theme_preference,
    })

    // Redirect reativo: ProtectedRoute cuida do /welcome.
    // Aqui apenas mandamos para a raiz protegida.
    navigate('/carteira')
  }

  const logout = () => {
    clearAllTokens()
    delete api.defaults.headers.common['Authorization']
    authStore.logout()
    clearSelectedPortfolio()
    setUser(null)
    try {
      navigate('/login', { replace: true })
    } catch {
      window.location.replace('/login')
    }
  }

  const refreshUser = async () => { await loadMe() }

  return (
    <AuthContext.Provider value={{
      user,
      isLoading,
      isAuthenticated: !!user,
      login,
      loginWithTokens,
      logout,
      refreshUser,
      setUser,
    }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
