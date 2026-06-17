import axios from 'axios'
import { useAuthStore } from '@/store/authStore'

const _raw = import.meta.env.VITE_API_URL
  ? import.meta.env.VITE_API_URL.replace(/\/$/, '')
  : ''

const BASE_URL = _raw.endsWith('/api/v1') ? _raw.slice(0, -7) : _raw

const api = axios.create({
  baseURL: `${BASE_URL}/api/v1`,
  headers: { 'Content-Type': 'application/json' },
})

// Injeta token em toda requisição
api.interceptors.request.use((config) => {
  const token =
    useAuthStore.getState().token ?? localStorage.getItem('sig_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Logout automático em 401 — exceto na rota de login (credenciais erradas)
api.interceptors.response.use(
  (res) => res,
  (err) => {
    const isLoginRoute = err.config?.url?.includes('/auth/login')
    if (err.response?.status === 401 && !isLoginRoute) {
      useAuthStore.getState().logout()
      localStorage.removeItem('sig-auth')
      window.location.replace('/login')
    }
    return Promise.reject(err)
  }
)

export { api }
export default api
