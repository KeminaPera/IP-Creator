import axios from 'axios'
import { ElMessage } from 'element-plus'
import i18n from '../i18n'
import { useAuthStore } from '../stores/auth'

// 防止并发刷新导致多次请求
let isRefreshing = false
let failedQueue = []

const processQueue = (error, token = null) => {
  failedQueue.forEach(prom => {
    if (error) {
      prom.reject(error)
    } else {
      prom.resolve(token)
    }
  })
  failedQueue = []
}

// 统一的跳转到登录页函数
const redirectToLogin = () => {
  // 防止重复跳转
  if (window.location.pathname === '/login') return
  
  // Clear all auth data
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  localStorage.removeItem('username')
  localStorage.removeItem('user_role')
  
  // Use window.location for reliable navigation
  window.location.href = '/login'
}

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

// Response interceptor - handle auth errors with automatic token refresh
request.interceptors.response.use(
  (response) => {
    // ============================================================
    // 统一响应格式 (所有API都使用 success_response() 包装):
    // response.data = {
    //   success: true,
    //   data: {...},         // 实际业务数据
    //   message: "...",      // 可选
    //   pagination: {...}    // 可选（列表接口）
    // }
    //
    // 前端访问实际数据: response.data.data
    // ============================================================
    return response
  },
  async (error) => {
    const originalRequest = error.config
    const errorResponse = error.response?.data
    
    // Handle 401 - Token expired or invalid
    if (error.response?.status === 401 && !originalRequest._retry) {
      // Mark request to prevent infinite loop
      originalRequest._retry = true
      
      if (isRefreshing) {
        // If already refreshing, queue this request
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject })
        })
          .then(token => {
            originalRequest.headers.Authorization = `Bearer ${token}`
            return request(originalRequest)
          })
          .catch(err => {
            // Queue request failed, redirect to login
            redirectToLogin()
            return Promise.reject(err)
          })
      }
      
      isRefreshing = true
      
      try {
        const authStore = useAuthStore()
        const newToken = await authStore.refreshAccessToken()
        
        // Update original request token
        originalRequest.headers.Authorization = `Bearer ${newToken}`
        
        // Process queued requests
        processQueue(null, newToken)
        
        // Retry original request
        return request(originalRequest)
      } catch (refreshError) {
        // Refresh failed
        processQueue(refreshError, null)
        
        const i18nGlobal = i18n.global
        ElMessage.error(i18nGlobal.t('common.session_expired') || '登录已过期，请重新登录')
        
        // Redirect to login
        redirectToLogin()
        
        return Promise.reject(error)
      } finally {
        isRefreshing = false
      }
    }
    
    // Handle 401 with _retry=true (token refresh failed)
    if (error.response?.status === 401 && originalRequest._retry) {
      redirectToLogin()
      return Promise.reject(error)
    }
    
    // Handle other errors
    if (errorResponse && errorResponse.error) {
      const errorMsg = errorResponse.error.message || errorResponse.error.error || 'Unknown error'
      
      if (error.response?.status === 403) {
        const i18nGlobal = i18n.global
        ElMessage.error(i18nGlobal.t('common.forbidden') || '没有权限访问')
      } else if (error.response?.status !== 401) {
        // Show error message (skip 401 as it's handled above)
        ElMessage.error(errorMsg)
      }
    } else if (error.response?.status === 403) {
      const i18nGlobal = i18n.global
      ElMessage.error(i18nGlobal.t('common.forbidden'))
    } else if (error.response?.status !== 401) {
      // Fallback for old error format
      const i18nGlobal = i18n.global
      const errorMsg = error.response?.data?.detail || error.message || i18nGlobal.t('common.request_failed')
      ElMessage.error(errorMsg)
    }
    
    return Promise.reject(error)
  }
)

export default request
