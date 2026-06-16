import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '@/services/api'
import { useTheme } from './ThemeContext'

export interface User {
  id: number
  name: string
  email: string
  role: string
  avatar_url?: string | null
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

  const loadMe = async () => {
    const { data } = await api.get('/users/me')
    setUser(data)
    setTheme(data.theme_preference ?? 'dark')
    return data
  }

  useEffect(() => {
    const token = localStorage.getItem('sig_token')
    if (token) {
      api.defaults.headers.common['Authorization'] = `Bearer ${token}`
      loadMe()
        .catch(() => {
          localStorage.removeItem('sig_token')
          localStorage.removeItem('sig_refresh')
        })
        .finally(() => setIsLoading(false))
    } else {
      setIsLoading(false)
    }
  }, [])

  const login = async (email: string, password: string) => {
    const { data } = await api.post('/auth/login', { email, password })
    localStorage.setItem('sig_token', data.access_token)
    localStorage.setItem('sig_refresh', data.refresh_token)
    api.defaults.headers.common['Authorization'] = `Bearer ${data.access_token}`
    await loadMe()
    navigate('/carteira')
  }

  const logout = () => {
    localStorage.removeItem('sig_token')
    localStorage.removeItem('sig_refresh')
    delete api.defaults.headers.common['Authorization']
    setUser(null)
    navigate('/login')
  }

  const refreshUser = async () => { await loadMe() }

  return (
    <AuthContext.Provider value={{ user, isLoading, isAuthenticated: !!user, login, logout, refreshUser, setUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
