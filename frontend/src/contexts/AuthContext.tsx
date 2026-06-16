import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '@/services/api'
import { useTheme } from './ThemeContext'
import { useAuthStore } from '@/store/authStore'

export interface User {
  id: number
  name: string
  email: string
  role: string
  avatar_url?: string | null
  theme_preference?: 'dark' | 'light'
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

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const navigate = useNavigate()
  const { setTheme } = useTheme()
  const authStore = useAuthStore()

  const loadMe = async (): Promise<User> => {
    const { data } = await api.get<User>('/users/me')
    setUser(data)
    setTheme(data.theme_preference ?? 'dark')
    return data
  }

  // Hidratação inicial: se já tem token no store/localStorage, carrega o usuário
  useEffect(() => {
    const token = authStore.token ?? localStorage.getItem('sig_token')
    if (token) {
      api.defaults.headers.common['Authorization'] = `Bearer ${token}`
      loadMe()
        .catch(() => {
          authStore.logout()
          localStorage.removeItem('sig_token')
          localStorage.removeItem('sig_refresh')
        })
        .finally(() => setIsLoading(false))
    } else {
      setIsLoading(false)
    }
  }, [])

  const login = async (email: string, password: string) => {
    // 1. Autentica e obtém tokens
    const { data: tokens } = await api.post<{
      access_token: string
      refresh_token: string
    }>('/auth/login', { email, password })

    // 2. Persiste tokens
    localStorage.setItem('sig_token', tokens.access_token)
    localStorage.setItem('sig_refresh', tokens.refresh_token)
    api.defaults.headers.common['Authorization'] = `Bearer ${tokens.access_token}`

    // 3. Carrega dados do usuário
    const me = await loadMe()

    // 4. Sincroniza com Zustand (usado pelo interceptor do axios)
    authStore.login(tokens.access_token, {
      id: me.id,
      email: me.email,
      name: me.name,
      role: me.role,
      theme_preference: me.theme_preference,
    })

    navigate('/carteira')
  }

  const logout = () => {
    localStorage.removeItem('sig_token')
    localStorage.removeItem('sig_refresh')
    delete api.defaults.headers.common['Authorization']
    authStore.logout()
    setUser(null)
    navigate('/login')
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
