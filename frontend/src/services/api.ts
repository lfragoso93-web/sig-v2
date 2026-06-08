import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? 'http://localhost:8000',
  timeout: 15000,
})

// Interceptor: injeta token em todas as requests
api.interceptors.request.use(config => {
  const token = localStorage.getItem('sig_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Interceptor: tenta refresh automático em 401
api.interceptors.response.use(
  res => res,
  async error => {
    const original = error.config
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true
      const refresh = localStorage.getItem('sig_refresh')
      if (refresh) {
        try {
          const { data } = await axios.post(
            `${import.meta.env.VITE_API_URL ?? 'http://localhost:8000'}/api/v1/auth/refresh`,
            { refresh_token: refresh }
          )
          localStorage.setItem('sig_token', data.access_token)
          api.defaults.headers.common['Authorization'] = `Bearer ${data.access_token}`
          original.headers['Authorization'] = `Bearer ${data.access_token}`
          return api(original)
        } catch {
          localStorage.removeItem('sig_token')
          localStorage.removeItem('sig_refresh')
          window.location.href = '/login'
        }
      }
    }
    return Promise.reject(error)
  }
)

export default api
