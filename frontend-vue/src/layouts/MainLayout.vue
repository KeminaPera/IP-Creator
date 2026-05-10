<template>
  <el-container class="main-layout">
    <!-- Sidebar -->
    <el-aside :width="appStore.sidebarCollapsed ? '64px' : '220px'" class="sidebar">
      <div class="logo" @click="$router.push('/')">
        <el-icon :size="28"><MagicStick /></el-icon>
        <div v-show="!appStore.sidebarCollapsed" class="logo-content">
          <span class="logo-text">IP Creator</span>
          <span class="logo-version">v1.0.0</span>
        </div>
      </div>
      <el-menu
        :default-active="activeMenu"
        :collapse="appStore.sidebarCollapsed"
        :collapse-transition="false"
        router
        class="sidebar-menu"
        background-color="#1e3a5f"
        text-color="#b0c4de"
        active-text-color="#ffffff"
      >
        <el-menu-item index="/">
          <el-icon><HomeFilled /></el-icon>
          <template #title>{{ $t('nav.home') }}</template>
        </el-menu-item>
        <el-menu-item index="/llm">
          <el-icon><Monitor /></el-icon>
          <template #title>{{ $t('nav.llm_management') }}</template>
        </el-menu-item>
        <el-menu-item index="/ip">
          <el-icon><PictureFilled /></el-icon>
          <template #title>{{ $t('nav.ip_assets') }}</template>
        </el-menu-item>
        <el-menu-item index="/datasets">
          <el-icon><FolderOpened /></el-icon>
          <template #title>{{ $t('nav.datasets') || '训练数据集' }}</template>
        </el-menu-item>
        <el-menu-item index="/lora">
          <el-icon><Coin /></el-icon>
          <template #title>{{ $t('nav.lora_models') }}</template>
        </el-menu-item>
        <el-menu-item index="/generate">
          <el-icon><VideoCameraFilled /></el-icon>
          <template #title>{{ $t('nav.generate') }}</template>
        </el-menu-item>
        <el-menu-item index="/tasks">
          <el-icon><List /></el-icon>
          <template #title>{{ $t('nav.task_monitor') }}</template>
        </el-menu-item>
        <el-menu-item index="/contents">
          <el-icon><Files /></el-icon>
          <template #title>{{ $t('nav.content_library') }}</template>
        </el-menu-item>
        <el-menu-item index="/settings">
          <el-icon><Setting /></el-icon>
          <template #title>{{ $t('nav.settings') }}</template>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <!-- Main content area -->
    <el-container>
      <!-- Header -->
      <el-header class="header">
        <div class="header-left">
          <el-icon class="collapse-btn" @click="appStore.toggleSidebar" :size="20">
            <Fold v-if="!appStore.sidebarCollapsed" />
            <Expand v-else />
          </el-icon>
        </div>
        <div class="header-right">
          <!-- Language Switcher -->
          <el-dropdown @command="handleLanguageChange" trigger="click">
            <span class="lang-switcher">
              <el-icon><Location /></el-icon>
              {{ appStore.language === 'zh-CN' ? $t('common.chinese') : $t('common.english') }}
              <el-icon class="el-icon--right"><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="zh-CN" :class="{ active: appStore.language === 'zh-CN' }">
                  {{ $t('common.chinese') }}
                </el-dropdown-item>
                <el-dropdown-item command="en-US" :class="{ active: appStore.language === 'en-US' }">
                  {{ $t('common.english') }}
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>

          <!-- User Menu -->
          <el-dropdown @command="handleUserCommand" trigger="click">
            <span class="user-menu">
              <el-avatar :size="32" class="user-avatar">
                {{ authStore.username?.charAt(0)?.toUpperCase() || 'U' }}
              </el-avatar>
              <span class="user-name">{{ authStore.username }}</span>
              <el-icon class="el-icon--right"><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item disabled>
                  {{ authStore.role === 'admin' ? $t('user.admin') : $t('user.regular_user') }}
                </el-dropdown-item>
                <el-dropdown-item divided command="logout">
                  <el-icon><SwitchButton /></el-icon>
                  {{ $t('common.logout') }}
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <!-- Page content -->
      <el-main class="main-content">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../stores/auth'
import { useAppStore } from '../stores/app'
import {
  HomeFilled, Monitor, PictureFilled, Coin,
  VideoCameraFilled, List, MagicStick,
  Fold, Expand, Location, ArrowDown, SwitchButton, Files, Setting,
} from '@element-plus/icons-vue'

const route = useRoute()
const { locale } = useI18n()
const authStore = useAuthStore()
const appStore = useAppStore()

const activeMenu = computed(() => route.path)

function handleLanguageChange(lang) {
  appStore.setLanguage(lang)
  locale.value = lang
}

function handleUserCommand(command) {
  if (command === 'logout') {
    authStore.logout()
  }
}
</script>

<style scoped>
.main-layout {
  height: 100vh;
}
.sidebar {
  background: #1e3a5f;
  overflow: hidden;
  transition: width 0.3s;
}
.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #fff;
  font-size: 18px;
  font-weight: 700;
  cursor: pointer;
  border-bottom: 1px solid rgba(255,255,255,0.1);
}
.logo-content {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  line-height: 1;
}
.logo-text {
  white-space: nowrap;
  overflow: hidden;
}
.logo-version {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.6);
  font-weight: 400;
  margin-top: 2px;
}
.sidebar-menu {
  border-right: none;
}
.sidebar-menu:not(.el-menu--collapse) {
  width: 220px;
}
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border-bottom: 1px solid #e6e6e6;
  padding: 0 20px;
  height: 60px;
}
.header-left {
  display: flex;
  align-items: center;
}
.collapse-btn {
  cursor: pointer;
  color: #666;
}
.collapse-btn:hover {
  color: #409eff;
}
.header-right {
  display: flex;
  align-items: center;
  gap: 20px;
}
.lang-switcher {
  display: flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  color: #606266;
  font-size: 14px;
}
.lang-switcher:hover {
  color: #409eff;
}
.user-menu {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}
.user-avatar {
  background: #409eff;
  color: #fff;
  font-size: 14px;
}
.user-name {
  font-size: 14px;
  color: #606266;
}
.main-content {
  background: #f5f7fa;
  overflow-y: auto;
}
</style>
