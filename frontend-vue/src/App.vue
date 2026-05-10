<template>
  <el-config-provider :locale="elementLocale">
    <MainLayout v-if="authStore.isLoggedIn" />
    <router-view v-else />
  </el-config-provider>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElConfigProvider } from 'element-plus'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'
import en from 'element-plus/dist/locale/en.mjs'
import { useAuthStore } from './stores/auth'
import MainLayout from './layouts/MainLayout.vue'

const authStore = useAuthStore()
const { locale } = useI18n()

// Element Plus locale mapping
const elementLocales = {
  'zh-CN': zhCn,
  'en-US': en,
}

// Computed to reactively change Element Plus locale
const elementLocale = computed(() => elementLocales[locale.value] || zhCn)
</script>

<style>
body {
  margin: 0;
  padding: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}
</style>
