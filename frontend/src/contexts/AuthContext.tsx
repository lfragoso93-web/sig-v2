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

  const login = async (email: string, password: string) => {
    const { data: tokens } = await api.post<{
      access_token: string
      refresh_token: string
    }>('/auth/login', { email, password })

    localStorage.setItem('sig_token', tokens.access_token)
    localStorage.setItem('sig_refresh', tokens.refresh_token)
    api.defaults.headers.common['Authorization'] = `Bearer ${tokens.access_token}`

    const me = await loadMe()

    authStore.login(tokens.access_token, {
      id: me.id,
      email: me.email,
      name: me.name,
      role: me.role,
      theme_preference: me.theme_preference,
    })

    // Redireciona para o tour de onboarding se ainda nao foi concluido
    if (!me.onboarding_completed) {
      navigate('/welcome')
    } else {
      navigate('/carteira')
    }
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
      logout,
      refreshUser,
      setUser,
    }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
