import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login as loginApi } from '../api/auth'
import router from '../router'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('access_token') || '')
  const username = ref(localStorage.getItem('username') || '')
  const role = ref(localStorage.getItem('user_role') || '')

  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => role.value === 'admin')

  async function login(credentials) {
    const { data } = await loginApi(credentials)
    // Unified response format: { success: true, data: {...}, message: "..." }
    const loginData = data.data || data
    token.value = loginData.access_token
    username.value = loginData.user.username
    role.value = loginData.user.role
    localStorage.setItem('access_token', loginData.access_token)
    localStorage.setItem('username', loginData.user.username)
    localStorage.setItem('user_role', loginData.user.role)
    return loginData
  }

  function logout() {
    token.value = ''
    username.value = ''
    role.value = ''
    localStorage.removeItem('access_token')
    localStorage.removeItem('username')
    localStorage.removeItem('user_role')
    router.push('/login')
  }

  return { token, username, role, isLoggedIn, isAdmin, login, logout }
})
