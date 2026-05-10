<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-header">
        <el-icon :size="48" color="#409eff"><MagicStick /></el-icon>
        <h1>IP Creator</h1>
        <p>{{ $t('auth.login_subtitle') }}</p>
      </div>
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        @submit.prevent="handleLogin"
      >
        <el-form-item :label="$t('auth.username')" prop="username">
          <el-input
            v-model="form.username"
            :placeholder="$t('auth.username_placeholder')"
            prefix-icon="User"
            size="large"
          />
        </el-form-item>
        <el-form-item :label="$t('auth.password')" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            :placeholder="$t('auth.password_placeholder')"
            prefix-icon="Lock"
            size="large"
            show-password
            @keyup.enter="handleLogin"
          />
        </el-form-item>
        <el-form-item>
          <el-button
            type="primary"
            size="large"
            :loading="loading"
            style="width: 100%"
            @click="handleLogin"
          >
            {{ $t('auth.login_button') }}
          </el-button>
        </el-form-item>
      </el-form>
      <!-- Language switcher on login page -->
      <div class="login-footer">
        <el-dropdown @command="handleLanguageChange" trigger="click">
          <span class="lang-switcher">
            <el-icon><Location /></el-icon>
            {{ appStore.language === 'zh-CN' ? $t('common.chinese') : $t('common.english') }}
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="zh-CN">{{ $t('common.chinese') }}</el-dropdown-item>
              <el-dropdown-item command="en-US">{{ $t('common.english') }}</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../stores/auth'
import { useAppStore } from '../stores/app'

const router = useRouter()
const { t, locale } = useI18n()
const authStore = useAuthStore()
const appStore = useAppStore()

const formRef = ref(null)
const loading = ref(false)

const form = reactive({
  username: '',
  password: '',
})

const rules = {
  username: [{ required: true, message: () => t('auth.username_placeholder'), trigger: 'blur' }],
  password: [{ required: true, message: () => t('auth.password_placeholder'), trigger: 'blur' }],
}

async function handleLogin() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    await authStore.login(form)
    ElMessage.success(t('auth.login_success'))
    router.push('/')
  } catch (err) {
    ElMessage.error(t('auth.login_failed'))
  } finally {
    loading.value = false
  }
}

function handleLanguageChange(lang) {
  appStore.setLanguage(lang)
  locale.value = lang
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1e3a5f 0%, #2d5a8e 50%, #3b7dd8 100%);
}
.login-card {
  width: 420px;
  padding: 40px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}
.login-header {
  text-align: center;
  margin-bottom: 32px;
}
.login-header h1 {
  margin: 12px 0 8px;
  font-size: 28px;
  color: #303133;
}
.login-header p {
  margin: 0;
  color: #909399;
  font-size: 14px;
}
.login-footer {
  text-align: center;
  margin-top: 16px;
}
.lang-switcher {
  cursor: pointer;
  color: #909399;
  font-size: 13px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.lang-switcher:hover {
  color: #409eff;
}
</style>
