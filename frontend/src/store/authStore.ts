import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'

interface User {
  id: number
  email: string
  name: string
  role: string
  theme_preference?: 'dark' | 'light'
}

interface AuthState {
  token: string | null
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (token: string, user: User) => void
  logout: () => void
  setLoading: (v: boolean) => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      isAuthenticated: false,
      isLoading: false,
      login: (token: string, user: User) => {
        localStorage.setItem('sig_token', token)
        set({ token, user, isAuthenticated: true })
      },
      logout: () => {
        localStorage.removeItem('sig_token')
        localStorage.removeItem('sig_refresh')
        // Limpa o storage persistido pelo zustand/persist para evitar
        // re-hidratação automática após logout (bug de "login em cache")
        localStorage.removeItem('sig-auth')
        set({ token: null, user: null, isAuthenticated: false })
      },
      setLoading: (v: boolean) => set({ isLoading: v }),
    }),
    {
      name: 'sig-auth',
      storage: createJSONStorage(() => localStorage),
      // IMPORTANTE: NÃO persistir isAuthenticated.
      // Se persistido, o Zustand rehidrata como "autenticado" mesmo após logout,
      // fazendo o ProtectedRoute deixar passar sem validar o token real.
      partialize: (state) => ({ token: state.token, user: state.user }),
    }
  )
)
