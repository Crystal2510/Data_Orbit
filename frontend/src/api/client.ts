import axios from 'axios'

const apiClient = axios.create({
  baseURL: '/api/v1',
  timeout: 120000, // 2 min — AI calls can be slow
  headers: { 'Content-Type': 'application/json' },
})

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const detail = error.response?.data?.detail || error.message || 'Unknown error'
    const err = new Error(detail)
    return Promise.reject(err)
  }
)

export default apiClient