import axios from 'axios'
import { useAuthStore } from '@/store/authStore'

// Em producao: VITE_API_URL pode ser:
//   https://sgi-s4u9.onrender.com         (correto)
//   https://sgi-s4u9.onrender.com/api/v1  (legado — normalizado abaixo)
// Em desenvolvimento: http://localhost:8000
const _raw = (import.meta.env.VITE_API_URL ?? 'http://localhost:8000').replace(/\/$/, '')

// Remove sufixo /api/v1 caso a variavel de ambiente ja o inclua
const BASE_URL = _raw.endsWith('/api/v1') ? _raw.slice(0, -7) : _raw

const api = axios.create({
  baseURL: `${BASE_URL}/api/v1`,
  headers: { 'Content-Type': 'application/json' },
})

// Injeta token em toda requisicao
api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Logout automatico em 401
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      useAuthStore.getState().logout()
      window.location.href = '/'
    }
    return Promise.reject(err)
  }
)

export { api }
export default api
