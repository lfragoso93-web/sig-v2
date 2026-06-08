import { create } from 'zustand'

interface User {
  id: number
  name: string
  email: string
}

interface AuthState {
  token: string | null
  user: User | null
  setAuth: (token: string, user: User) => void
  logout: () => void
}

// Persiste token em memória (sem localStorage por limitação de sandbox)
// Em produção real, trocar para localStorage ou cookie httpOnly
let _persistedToken: string | null = null

export const useAuthStore = create<AuthState>((set) => ({
  token: _persistedToken,
  user: null,

  setAuth: (token, user) => {
    _persistedToken = token
    document.documentElement.setAttribute('data-auth', 'true')
    set({ token, user })
  },

  logout: () => {
    _persistedToken = null
    document.documentElement.removeAttribute('data-auth')
    set({ token: null, user: null })
  },
}))
