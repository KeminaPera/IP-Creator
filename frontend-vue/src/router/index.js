import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/',
    name: 'Dashboard',
    component: () => import('../views/Dashboard.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/llm',
    name: 'LLMManagement',
    component: () => import('../views/LLMManagement.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/ip',
    name: 'IPAssets',
    component: () => import('../views/IPAssets.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/generate',
    name: 'Generate',
    component: () => import('../views/Generate.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/lora',
    name: 'LoRAModels',
    component: () => import('../views/LoRAModels.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/tasks',
    name: 'TaskMonitor',
    component: () => import('../views/TaskMonitor.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/contents',
    name: 'ContentLibrary',
    component: () => import('../views/ContentLibrary.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/settings',
    name: 'SettingsManagement',
    component: () => import('../views/SettingsManagement.vue'),
    meta: { requiresAuth: true },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// Auth guard
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('access_token')
  if (to.meta.requiresAuth !== false && !token) {
    next('/login')
  } else if (to.path === '/login' && token) {
    next('/')
  } else {
    next()
  }
})

export default router
