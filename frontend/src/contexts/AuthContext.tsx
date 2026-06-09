import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '@/services/api'
import { useTheme } from './ThemeContext'

interface User {
  id: number
  name: string
  email: string
  role: string
}

interface AuthContextData {
  user: User | null
  isLoading: boolean
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextData>({} as AuthContextData)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const navigate = useNavigate()
  const { setTheme } = useTheme()

  useEffect(() => {
    const token = localStorage.getItem('sig_token')
    if (token) {
      api.defaults.headers.common['Authorization'] = `Bearer ${token}`
      api.get('/users/me')
        .then(({ data }) => {
          setUser(data)
          setTheme(data.theme_preference ?? 'dark')
        })
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
    // Backend espera JSON com campos { email, password }
    const { data } = await api.post('/auth/login', { email, password })
    localStorage.setItem('sig_token', data.access_token)
    localStorage.setItem('sig_refresh', data.refresh_token)
    api.defaults.headers.common['Authorization'] = `Bearer ${data.access_token}`
    const me = await api.get('/users/me')
    setUser(me.data)
    setTheme(me.data.theme_preference ?? 'dark')
    navigate('/app/dashboard')
  }

  const logout = () => {
    localStorage.removeItem('sig_token')
    localStorage.removeItem('sig_refresh')
    delete api.defaults.headers.common['Authorization']
    setUser(null)
    navigate('/')
  }

  return (
    <AuthContext.Provider value={{ user, isLoading, isAuthenticated: !!user, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
