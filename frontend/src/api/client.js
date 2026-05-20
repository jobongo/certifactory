import axios from 'axios'

const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api/v1',
})

client.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

let refreshPromise = null

client.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config
    if (error.response?.status === 401 && !original._retry) {
      const refreshToken = localStorage.getItem('refresh_token')
      if (!refreshToken || original.url === '/auth/refresh') {
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        window.location.href = '/login'
        return Promise.reject(error)
      }

      original._retry = true

      if (!refreshPromise) {
        refreshPromise = axios.post(
          `${client.defaults.baseURL}/auth/refresh`,
          { refresh_token: refreshToken },
        ).then((res) => {
          localStorage.setItem('access_token', res.data.access_token)
          localStorage.setItem('refresh_token', res.data.refresh_token)
          return res.data.access_token
        }).catch(() => {
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
          window.location.href = '/login'
          return null
        }).finally(() => {
          refreshPromise = null
        })
      }

      const newToken = await refreshPromise
      if (!newToken) return Promise.reject(error)
      original.headers.Authorization = `Bearer ${newToken}`
      return client(original)
    }
    return Promise.reject(error)
  }
)

export default client
