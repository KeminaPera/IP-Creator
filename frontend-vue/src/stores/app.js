import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAppStore = defineStore('app', () => {
  const language = ref(localStorage.getItem('app_language') || 'zh-CN')
  const sidebarCollapsed = ref(false)

  function setLanguage(lang) {
    language.value = lang
    localStorage.setItem('app_language', lang)
  }

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  return { language, sidebarCollapsed, setLanguage, toggleSidebar }
})
