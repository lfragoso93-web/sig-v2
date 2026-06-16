import axios from 'axios'
import { useAuthStore } from '@/store/authStore'

// Se VITE_API_URL estiver definido (ex: produção no Render), usa ele.
// Caso contrário, usa URL relativa — o nginx faz o proxy /api/ -> backend:8000
const _raw = import.meta.env.VITE_API_URL
  ? import.meta.env.VITE_API_URL.replace(/\/$/, '')
  : ''

// Remove sufixo /api/v1 caso a variável de ambiente já o inclua
const BASE_URL = _raw.endsWith('/api/v1') ? _raw.slice(0, -7) : _raw

const api = axios.create({
  baseURL: `${BASE_URL}/api/v1`,
  headers: { 'Content-Type': 'application/json' },
})

// Injeta token em toda requisição
// Usa store primeiro; fallback para localStorage para cobrir hidratação tardia do Zustand
api.interceptors.request.use((config) => {
  const token =
    useAuthStore.getState().token ?? localStorage.getItem('sig_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Logout automático em 401 — redireciona para /login (rota correta no App.tsx)
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      useAuthStore.getState().logout()
      window.location.replace('/login')
    }
    return Promise.reject(err)
  }
)

export { api }
export default api
