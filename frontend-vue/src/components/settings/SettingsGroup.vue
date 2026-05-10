<template>
  <div class="settings-group" v-loading="loading">
    <el-alert
      v-for="setting in settingsList"
      :key="setting.setting_key"
      :title="setting.display_name_cn"
      :closable="false"
      show-icon
      style="margin-bottom: 20px;"
      :type="setting.is_system ? 'warning' : 'info'"
    >
      <template #default>
        <div class="setting-content">
          <p class="setting-description">{{ setting.description_cn }}</p>
          
          <div class="setting-input">
            <!-- Float/Integer 类型：滑块 -->
            <el-slider 
              v-if="setting.value_type === 'float' || setting.value_type === 'integer'"
              v-model="localSettings[setting.setting_key]"
              :min="setting.validation_rule?.min || 0"
              :max="setting.validation_rule?.max || 100"
              :step="setting.value_type === 'float' ? 0.1 : 1"
              show-input
              style="width: 100%; max-width: 500px;"
            />
            
            <!-- String 类型：输入框 -->
            <el-input 
              v-else-if="setting.value_type === 'string'"
              v-model="localSettings[setting.setting_key]"
              :placeholder="setting.default_value"
              style="width: 100%; max-width: 500px;"
            />
            
            <!-- Boolean 类型：开关 -->
            <el-switch 
              v-else-if="setting.value_type === 'boolean'"
              v-model="localSettings[setting.setting_key]"
            />
            
            <!-- JSON 类型：代码编辑器 -->
            <el-input 
              v-else-if="setting.value_type === 'json'"
              v-model="localSettings[setting.setting_key]"
              type="textarea"
              :rows="5"
              style="width: 100%; max-width: 500px;"
            />
          </div>
          
          <div class="setting-meta">
            <span class="setting-type">{{ setting.value_type }}</span>
            <span v-if="setting.is_system" class="system-badge">系统配置</span>
            <span class="setting-default">默认值: {{ setting.default_value }}</span>
          </div>
        </div>
      </template>
    </el-alert>
    
    <div class="settings-actions">
      <el-button @click="handleReset" :disabled="loading">
        {{ $t('settings.reset_default') }}
      </el-button>
      <el-button type="primary" @click="handleSave" :loading="saving" :disabled="loading">
        {{ $t('settings.save') }}
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getSettingsByCategory, updateSetting, resetSettings } from '../../api/settings'

const { t } = useI18n()

const props = defineProps({
  category: {
    type: String,
    required: true
  }
})

const emit = defineEmits(['save', 'reset'])

const loading = ref(false)
const saving = ref(false)
const settingsList = ref([])
const localSettings = ref({})

// 加载设置
const loadSettings = async () => {
  loading.value = true
  try {
    const { data } = await getSettingsByCategory(props.category)
    // Unified response format: { success: true, data: { key1: value1, ... } }
    const settingsData = data.data || {}
    
    // Convert object to array
    const settingsArray = []
    for (const [key, value] of Object.entries(settingsData)) {
      settingsArray.push({
        setting_key: key,
        setting_value: value,
        value_type: getTypeFromValue(value),
        display_name_cn: getDisplayName(key),
        description_cn: getDescription(key),
        validation_rule: getValidationRule(key),
        default_value: value,
        is_system: isSystemSetting(key)
      })
    }
    settingsList.value = settingsArray
    
    // Initialize local settings
    localSettings.value = { ...settingsData }
  } catch (error) {
    ElMessage.error(t('common.load_failed'))
    console.error('Failed to load settings:', error)
  } finally {
    loading.value = false
  }
}

// 保存设置
const handleSave = async () => {
  saving.value = true
  try {
    const promises = []
    
    for (const setting of settingsList.value) {
      const key = setting.setting_key
      const newValue = localSettings.value[key]
      
      if (newValue !== setting.setting_value) {
        promises.push(updateSetting(props.category, key, newValue))
      }
    }
    
    await Promise.all(promises)
    emit('save', { category: props.category })
    await loadSettings() // Reload
  } catch (error) {
    ElMessage.error(t('settings.save_failed'))
    console.error('Failed to save settings:', error)
  } finally {
    saving.value = false
  }
}

// 恢复默认设置
const handleReset = async () => {
  try {
    await ElMessageBox.confirm(
      t('settings.reset_confirm'),
      t('common.warning'),
      {
        confirmButtonText: t('common.confirm'),
        cancelButtonText: t('common.cancel'),
        type: 'warning'
      }
    )
    
    await resetSettings(props.category)
    emit('reset', { category: props.category })
    await loadSettings() // Reload
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(t('settings.reset_failed'))
      console.error('Failed to reset settings:', error)
    }
  }
}

// 辅助函数：从值推断类型
const getTypeFromValue = (value) => {
  if (typeof value === 'boolean') return 'boolean'
  if (typeof value === 'number') {
    return Number.isInteger(value) ? 'integer' : 'float'
  }
  if (typeof value === 'object') return 'json'
  return 'string'
}

// 辅助函数：获取显示名称（从 API 获取详细信息时可替换）
const getDisplayName = (key) => {
  const names = {
    temperature: 'LLM 温度',
    max_tokens: '最大 Token 数',
    timeout: '超时时间（秒）',
    gpu_memory_limit: 'GPU 内存限制（GB）',
    max_concurrent_tasks: '最大并发任务数',
    storage_path: '主存储路径',
    models_path: '模型存储路径',
    ip_assets_path: 'IP 资产路径',
    lora_models_path: 'LoRA 模型路径',
    videos_path: '视频存储路径',
    lora_training_mode: 'LoRA 训练模式',
    enable_model_preload: '启用模型预下载'
  }
  return names[key] || key
}

// 辅助函数：获取描述
const getDescription = (key) => {
  const descriptions = {
    temperature: '控制生成文本的创造性，值越高越有创造性',
    max_tokens: 'LLM 生成文本的最大 token 数量',
    timeout: 'LLM API 调用超时时间',
    gpu_memory_limit: 'GPU 内存使用上限（GB）',
    max_concurrent_tasks: '同时运行的最大任务数量',
    storage_path: '项目主数据存储路径',
    models_path: 'AI 模型存储路径（Stable Diffusion 等）',
    ip_assets_path: 'IP 资产图片存储路径（角色参考图）',
    lora_models_path: 'LoRA 微调模型存储路径',
    videos_path: '生成的视频文件存储路径',
    lora_training_mode: 'LoRA 训练模式：mock（模拟）或 real（真实训练）',
    enable_model_preload: '是否在应用启动时预加载模型'
  }
  return descriptions[key] || ''
}

// 辅助函数：获取验证规则
const getValidationRule = (key) => {
  const rules = {
    temperature: { min: 0, max: 2 },
    max_tokens: { min: 1, max: 128000 },
    timeout: { min: 5, max: 300 },
    gpu_memory_limit: { min: 2, max: 80 },
    max_concurrent_tasks: { min: 1, max: 10 }
  }
  return rules[key] || null
}

// 辅助函数：判断是否为系统设置
const isSystemSetting = (key) => {
  const systemKeys = ['gpu_memory_limit', 'max_concurrent_tasks', 'storage_path', 'models_path', 'ip_assets_path', 'lora_models_path', 'videos_path', 'lora_training_mode']
  return systemKeys.includes(key)
}

// 监听 category 变化
watch(() => props.category, () => {
  loadSettings()
})

onMounted(() => {
  loadSettings()
})
</script>

<style scoped>
.settings-group {
  max-width: 800px;
}

.setting-content {
  padding: 10px 0;
}

.setting-description {
  margin: 0 0 12px 0;
  color: #606266;
  font-size: 13px;
  line-height: 1.5;
}

.setting-input {
  margin-bottom: 12px;
}

.setting-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 12px;
}

.setting-type {
  color: #909399;
  background: #f5f7fa;
  padding: 2px 8px;
  border-radius: 4px;
}

.system-badge {
  color: #e6a23c;
  background: #fdf6ec;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 600;
}

.setting-default {
  color: #909399;
}

.settings-actions {
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid #ebeef5;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
</style>
