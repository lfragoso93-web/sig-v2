import axios, { type AxiosRequestConfig } from 'axios'
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

interface RetriableRequestConfig extends AxiosRequestConfig {
  _retry?: boolean
}

let refreshPromise: Promise<string | null> | null = null

async function tryRefreshAccessToken(): Promise<string | null> {
  const refreshToken = localStorage.getItem('sig_refresh')
  if (!refreshToken) return null

  if (!refreshPromise) {
    refreshPromise = axios
      .post<{ access_token?: string; refresh_token?: string }>(
        `${BASE_URL}/api/v1/auth/refresh`,
        { refresh_token: refreshToken },
        { headers: { 'Content-Type': 'application/json' } }
      )
      .then((res) => {
        const nextAccess = res.data?.access_token
        const nextRefresh = res.data?.refresh_token
        if (!nextAccess || !nextRefresh) return null

        localStorage.setItem('sig_token', nextAccess)
        localStorage.setItem('sig_refresh', nextRefresh)
        api.defaults.headers.common['Authorization'] = `Bearer ${nextAccess}`
        useAuthStore.setState({ token: nextAccess, isAuthenticated: true })
        return nextAccess
      })
      .catch(() => null)
      .finally(() => {
        refreshPromise = null
      })
  }

  return refreshPromise
}

function forceLogoutRedirect() {
  useAuthStore.getState().logout()
  localStorage.removeItem('sig_token')
  localStorage.removeItem('sig_refresh')
  localStorage.removeItem('sig-auth')
  delete api.defaults.headers.common['Authorization']
  window.location.replace('/login')
}

// Renovação silenciosa em 401 via refresh_token; logout apenas se refresh falhar
api.interceptors.response.use(
  (res) => res,
  async (err) => {
    const originalConfig = err.config as RetriableRequestConfig | undefined
    const url = originalConfig?.url ?? ''
    const isAuthBypassRoute =
      url.includes('/auth/login') ||
      url.includes('/auth/register') ||
      url.includes('/auth/refresh') ||
      url.includes('/auth/mfa/verify')

    if (err.response?.status === 401 && !isAuthBypassRoute && originalConfig) {
      if (!originalConfig._retry) {
        originalConfig._retry = true
        const newAccessToken = await tryRefreshAccessToken()
        if (newAccessToken) {
          originalConfig.headers = {
            ...originalConfig.headers,
            Authorization: `Bearer ${newAccessToken}`,
          }
          return api(originalConfig)
        }
      }
      forceLogoutRedirect()
    }
    return Promise.reject(err)
  }
)

export { api }
export default api
