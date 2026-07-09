import axios from 'axios'
import { ElMessage } from 'element-plus'

const request = axios.create({
  baseURL: '/api',
  timeout: 120000
})

request.interceptors.request.use(config => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

request.interceptors.response.use(
  response => {
    const data = response.data
    if (data.code !== 200) {
      ElMessage.error(data.message || '请求失败')
      return Promise.reject(new Error(data.message))
    }
    return data.data
  },
  error => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      window.location.href = '/login'
    }
    const errorMsg = error.response?.data?.detail
      || error.response?.data?.message
      || error.message
      || '网络错误，请稍后重试'
    ElMessage.error(errorMsg)
    return Promise.reject(error)
  }
)

export default request
