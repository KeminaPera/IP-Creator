<template>
  <div class="settings-page">
    <h1 class="page-title">{{ $t('settings.title') }}</h1>
    
    <el-tabs v-model="activeTab" type="border-card">
      <!-- Tab 1: LLM 供应商管理 -->
      <el-tab-pane :label="$t('settings.tab_providers')" name="providers">
        <ProviderManagement v-if="activeTab === 'providers'" />
      </el-tab-pane>
      
      <!-- Tab 2: LLM 模型管理 -->
      <el-tab-pane :label="$t('settings.tab_models')" name="models">
        <ModelManagement v-if="activeTab === 'models'" />
      </el-tab-pane>
      
      <!-- Tab 3: LLM 默认参数 -->
      <el-tab-pane :label="$t('settings.tab_llm_default')" name="llm_default">
        <SettingsGroup 
          v-if="activeTab === 'llm_default'"
          category="llm_default"
          @save="handleSave"
          @reset="handleReset"
        />
      </el-tab-pane>
      
      <!-- Tab 4: 资源限制 -->
      <el-tab-pane :label="$t('settings.tab_resource_limit')" name="resource_limit">
        <SettingsGroup 
          v-if="activeTab === 'resource_limit'"
          category="resource_limit"
          @save="handleSave"
          @reset="handleReset"
        />
      </el-tab-pane>
      
      <!-- Tab 5: 存储路径 -->
      <el-tab-pane :label="$t('settings.tab_storage_path')" name="storage_path">
        <SettingsGroup 
          v-if="activeTab === 'storage_path'"
          category="storage_path"
          @save="handleSave"
          @reset="handleReset"
        />
      </el-tab-pane>
      
      <!-- Tab 6: 系统功能 -->
      <el-tab-pane :label="$t('settings.tab_system_feature')" name="system_feature">
        <SettingsGroup 
          v-if="activeTab === 'system_feature'"
          category="system_feature"
          @save="handleSave"
          @reset="handleReset"
        />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import SettingsGroup from '../components/settings/SettingsGroup.vue'
import ProviderManagement from '../components/settings/ProviderManagement.vue'
import ModelManagement from '../components/settings/ModelManagement.vue'
import { logger } from '../utils/logger'

const { t } = useI18n()

const activeTab = ref('providers')

const handleSave = (result) => {
  ElMessage.success(t('settings.save_success'))
  logger.debug('Settings saved:', result)
}

const handleReset = (result) => {
  ElMessage.success(t('settings.reset_success'))
  logger.debug('Settings reset:', result)
}
</script>

<style scoped>
.settings-page {
  padding: 20px;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  color: #303133;
  margin: 0 0 20px;
}

:deep(.el-tabs__content) {
  padding: 20px;
}
</style>
