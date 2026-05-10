import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'
import en from 'element-plus/dist/locale/en.mjs'
import 'element-plus/dist/index.css'
import './styles/common.css'
import './styles/utilities.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import App from './App.vue'
import router from './router'
import i18n from './i18n'

const app = createApp(App)
const pinia = createPinia()

// Element Plus locale mapping
const elementLocales = {
  'zh-CN': zhCn,
  'en-US': en,
}

// Register all Element Plus icons globally
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.use(pinia)
app.use(router)
app.use(i18n)

// Use Element Plus with locale based on current i18n locale
const currentLocale = localStorage.getItem('app_language') || 'zh-CN'
app.use(ElementPlus, {
  locale: elementLocales[currentLocale] || zhCn,
})

app.mount('#app')
