import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '../router'
import i18n from '../i18n'

const request = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
})

// Request interceptor - attach JWT token
request.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor - handle auth errors
request.interceptors.response.use(
  (response) => {
    // All backend responses now follow unified format:
    // { success: true, data: {...}, message?: string, pagination?: {...}, meta?: {...} }
    // No transformation needed - frontend accesses response.data directly
    return response
  },
  (error) => {
    const errorResponse = error.response?.data
    
    // Handle new unified error format: { success: false, error: { error, message, code, details } }
    if (errorResponse && errorResponse.error) {
      const errorMsg = errorResponse.error.message || errorResponse.error.error || 'Unknown error'
      
      if (error.response?.status === 401 || error.response?.status === 403) {
        localStorage.removeItem('access_token')
        localStorage.removeItem('user_role')
        localStorage.removeItem('username')
        router.push('/login')
        
        const i18nGlobal = i18n.global
        ElMessage.error(i18nGlobal.t('common.session_expired') || errorMsg)
      } else {
        // Show error message from unified format
        ElMessage.error(errorMsg)
      }
    } else if (error.response?.status === 401 || error.response?.status === 403) {
      // Fallback for old format
      localStorage.removeItem('access_token')
      localStorage.removeItem('user_role')
      localStorage.removeItem('username')
      router.push('/login')
      
      const i18nGlobal = i18n.global
      ElMessage.error(i18nGlobal.t('common.session_expired'))
    } else {
      // Fallback for old error format
      const i18nGlobal = i18n.global
      const errorMsg = error.response?.data?.detail || error.message || i18nGlobal.t('common.request_failed')
      ElMessage.error(errorMsg)
    }
    
    return Promise.reject(error)
  }
)

export default request
