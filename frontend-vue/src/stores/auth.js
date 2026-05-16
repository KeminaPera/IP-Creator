import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login as loginApi } from '../api/auth'
import router from '../router'
import { logger } from '../utils/logger'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('access_token') || '')
  const refreshToken = ref(localStorage.getItem('refresh_token') || '')
  const username = ref(localStorage.getItem('username') || '')
  const role = ref(localStorage.getItem('user_role') || '')

  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => role.value === 'admin')

  async function login(credentials) {
    const { data } = await loginApi(credentials)
    // Unified response format: { success: true, data: {...}, message: "..." }
    const loginData = data.data || data
    token.value = loginData.access_token
    refreshToken.value = loginData.refresh_token
    username.value = loginData.user.username
    role.value = loginData.user.role
    localStorage.setItem('access_token', loginData.access_token)
    localStorage.setItem('refresh_token', loginData.refresh_token)
    localStorage.setItem('username', loginData.user.username)
    localStorage.setItem('user_role', loginData.user.role)
    return loginData
  }

  async function refreshAccessToken() {
    if (!refreshToken.value) {
      throw new Error('No refresh token available')
    }
    
    try {
      const response = await fetch('/api/v1/auth/refresh', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          refresh_token: refreshToken.value
        })
      })
      
      const result = await response.json()
      
      if (result.success && result.data) {
        const newToken = result.data.access_token
        token.value = newToken
        localStorage.setItem('access_token', newToken)
        logger.info('Token refreshed successfully')
        return newToken
      } else {
        throw new Error(result.message || 'Token refresh failed')
      }
    } catch (error) {
      logger.error('Token refresh error:', error)
      // Refresh failed, force logout
      logout()
      throw error
    }
  }

  function logout() {
    token.value = ''
    refreshToken.value = ''
    username.value = ''
    role.value = ''
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('username')
    localStorage.removeItem('user_role')
    
    // Use window.location for reliable navigation
    if (window.location.pathname !== '/login') {
      window.location.href = '/login'
    }
  }

  return { 
    token, 
    refreshToken, 
    username, 
    role, 
    isLoggedIn, 
    isAdmin, 
    login, 
    logout,
    refreshAccessToken
  }
})
