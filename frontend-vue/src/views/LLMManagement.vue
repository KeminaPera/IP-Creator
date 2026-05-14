<template>
  <div class="llm-page">
    <h1 class="page-title">{{ $t('llm.title') }}</h1>

    <!-- Stats Row -->
    <el-row :gutter="16" class="stats-row">
      <el-col :span="6">
        <el-statistic :title="$t('llm.total_channels')" :value="channels.length" />
      </el-col>
      <el-col :span="6">
        <el-statistic :title="$t('llm.active')" :value="channels.filter(c => c.is_active).length" />
      </el-col>
      <el-col :span="6">
        <el-statistic :title="$t('llm.healthy')" :value="channels.filter(c => c.health_status === 'healthy').length" />
      </el-col>
      <el-col :span="6">
        <el-statistic :title="$t('llm.current_active')" :value="channels.filter(c => c.is_active).length" />
      </el-col>
    </el-row>

    <!-- Toolbar -->
    <DataTable
      :data="paginatedChannels"
      :loading="loading"
      :total="filteredChannels.length"
      :page-size="pagination.pageSize"
      @page-change="handlePageChange"
    >
      <template #toolbar>
        <el-row :gutter="16" style="width: 100%;">
          <el-col :span="8">
            <el-input v-model="searchText" :placeholder="$t('llm.search_placeholder')" prefix-icon="Search" clearable />
          </el-col>
          <el-col :span="16" style="text-align: right;">
            <el-button type="primary" @click="openAddDialog">
              <el-icon><Plus /></el-icon> {{ $t('llm.add_channel') }}
            </el-button>
          </el-col>
        </el-row>
      </template>

      <template #default>
        <el-table-column prop="name" :label="$t('llm.channel')" min-width="280">
          <template #default="{ row }">
            <div style="display:flex;align-items:center;gap:8px;position:relative;">
              <img v-if="row.provider_icon_url" :src="row.provider_icon_url" :alt="row.provider" loading="lazy" style="width:20px;height:20px;" />
              <div style="flex:1;">
                <div style="display:flex;align-items:center;gap:8px;">
                  <span style="font-weight:500;">{{ row.name }}</span>
                  <el-tag 
                    :type="row.model_type === 'cloud' ? 'primary' : 'success'" 
                    size="small"
                    style="font-size:11px;padding:0 6px;height:18px;line-height:18px;"
                  >
                    {{ row.model_type === 'cloud' ? $t('llm.model_type_cloud') : $t('llm.model_type_local') }}
                  </el-tag>
                </div>
                <div style="font-size:12px;color:#909399;margin-top:2px;">
                  {{ row.provider }} - {{ row.model_name }}
                </div>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column :label="$t('llm.capabilities')" width="180" align="center">
          <template #default="{ row }">
            <div style="display:flex;gap:4px;flex-wrap:wrap;justify-content:center;">
              <el-tag v-for="cap in getCapabilityTags(row)" :key="cap.key" :type="cap.type" size="small">
                {{ cap.label }}
              </el-tag>
              <span v-if="!row.capabilities || row.capabilities.length === 0" style="color:#999;font-size:12px;">-</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column :label="$t('llm.status')" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row)" size="small">{{ statusLabel(row) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('llm.success_rate_label')" width="100" align="center">
          <template #default="{ row }">
            <span :style="{ color: getSuccessRateColor(row.success_rate) }">
              {{ row.success_rate != null ? row.success_rate.toFixed(1) + '%' : '-' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column :label="$t('llm.response_time_label')" width="110" align="center">
          <template #default="{ row }">
            <el-tooltip 
              v-if="row.response_time_ms" 
              :content="$t('llm.avg_response_time_hint')" 
              placement="top"
            >
              <span style="cursor: help;">
                {{ formatResponseTime(row.response_time_ms) }}
              </span>
            </el-tooltip>
            <span v-else style="color:#999;">-</span>
          </template>
        </el-table-column>
        <el-table-column :label="$t('llm.last_called')" width="180">
          <template #default="{ row }">
            <span v-if="row.last_health_check" style="font-size:12px;">
              {{ formatTime(row.last_health_check) }}
            </span>
            <span v-else style="color:#999;font-size:12px;">{{ $t('llm.never_called') }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="is_active" :label="$t('common.active')" width="80" align="center">
          <template #default="{ row }">
            <el-switch v-model="row.is_active" @change="toggleActive(row)" />
          </template>
        </el-table-column>
      </template>

      <template #actions="{ row }">
        <el-button size="small" type="warning" @click="openEditDialog(row)">{{ $t('common.edit') }}</el-button>
        <el-dropdown trigger="click" style="margin-left: 8px;">
          <el-button size="small">
            {{ $t('common.more') }}<el-icon class="el-icon--right"><arrow-down /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item 
                @click="testConnection(row)" 
                :disabled="!row.is_active"
                :title="!row.is_active ? $t('llm.test_connection_disabled_hint') : ''"
                class="text-info"
              >
                <el-icon><Connection /></el-icon> {{ $t('llm.test_connection') }}
              </el-dropdown-item>
              <el-dropdown-item divided @click="handleDelete(row, deleteChannel)" class="text-danger">
                <el-icon><Delete /></el-icon> {{ $t('common.delete') }}
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </template>
    </DataTable>

    <!-- Add/Edit Dialog -->
    <el-dialog v-model="dialogVisible" :title="isEdit ? $t('llm.edit_channel') : $t('llm.add_channel')" width="600px" destroy-on-close>
      <el-form ref="channelFormRef" :model="channelForm" :rules="channelRules" label-width="120px">
        <el-form-item :label="$t('llm.provider')" prop="provider">
          <el-select v-model="channelForm.provider" :placeholder="$t('llm.select_provider')" @change="onProviderChange" :disabled="isEdit" style="width:100%">
            <el-option v-for="p in providers" :key="p.code" :label="p.name || p.name_cn || p.name_en || p.code" :value="p.code">
              <div style="display:flex;align-items:center;gap:8px;">
                <img v-if="p.icon_url" :src="p.icon_url" :alt="p.name || p.name_cn || p.name_en || p.code" loading="lazy" style="width:18px;height:18px;" />
                <span>{{ p.name || p.name_cn || p.name_en || p.code }}</span>
              </div>
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('llm.model')" prop="model_name">
          <el-select v-model="channelForm.model_name" :placeholder="$t('llm.select_model')" :disabled="!channelForm.provider || isEdit" @change="onModelChange" style="width:100%">
            <el-option v-for="m in availableModels" :key="m.code" :label="m.name" :value="m.code" />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('llm.channel_name')" prop="name">
          <el-input v-model="channelForm.name" :placeholder="$t('llm.channel_name_placeholder')" :disabled="isEdit" />
        </el-form-item>
        <el-form-item :label="$t('llm.api_endpoint')">
          <el-input v-model="channelForm.api_endpoint" :placeholder="$t('llm.api_endpoint_hint')" />
        </el-form-item>
        <el-form-item :label="isEdit ? $t('llm.api_key_edit') : $t('llm.api_key')" prop="api_key">
          <el-input v-model="channelForm.api_key" type="password" show-password
            :placeholder="isEdit ? $t('llm.api_key_update_placeholder') : $t('llm.api_key_placeholder')" />
        </el-form-item>
        <!-- Advanced Settings -->
        <el-collapse>
          <el-collapse-item :title="$t('llm.advanced_settings')">
            <el-form-item :label="$t('llm.temperature')">
              <el-slider v-model="channelForm.temperature" :min="0" :max="2" :step="0.1" show-input />
            </el-form-item>
            <el-form-item :label="$t('llm.max_tokens')">
              <el-input-number v-model="channelForm.max_tokens" :min="1" :max="128000" />
            </el-form-item>
            <el-form-item :label="$t('llm.timeout')">
              <el-input-number v-model="channelForm.timeout" :min="5" :max="300" />
            </el-form-item>
          </el-collapse-item>
        </el-collapse>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">
          {{ isEdit ? $t('llm.update_channel_btn') : $t('llm.add_channel_btn') }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { Connection, ArrowDown, Delete } from '@element-plus/icons-vue'
import { getChannels, registerChannel, updateChannel, deleteChannel } from '@/api/llm'
import { getProviders } from '@/api/settings'
import { formatTime } from '../utils/time'
import request from '@/api/request'
import { useDeleteConfirm } from '../composables/useDeleteConfirm'
import { useDebounce } from '../composables/useDebounce'
import { useAsyncData } from '@/composables/useAsyncData'
import DataTable from '../components/common/DataTable.vue'

const { t } = useI18n()

// Keep as ref for template reactivity
const channels = ref([])

// Use useAsyncData for automatic data fetching
const { loading, execute: loadChannels } = useAsyncData(
  () => getChannels(),
  { 
    errorMessage: 'common.load_failed', 
    autoLoad: true,
    onSuccess: (result) => {
      // Extract data from nested response: result.data.data
      channels.value = result?.data?.data || result?.data || []
    }
  }
)

const submitting = ref(false)
const testing = ref({})
const providers = ref([])
const searchText = ref('')
const debouncedSearchText = ref('')
const dialogVisible = ref(false)
const isEdit = ref(false)
const channelFormRef = ref(null)

// Pagination
const pagination = ref({
  page: 1,
  pageSize: (() => {
    try {
      return parseInt(localStorage.getItem('llmManagement_pageSize')) || 20
    } catch {
      return 20
    }
  })(),
})
const total = ref(0)

const channelForm = ref({
  provider: '',
  model_name: '',
  name: '',
  model_type: 'cloud',  // Default to cloud, will be auto-detected
  api_endpoint: '',
  api_key: '',
  temperature: 0.7,
  max_tokens: 2048,
  timeout: 120,
})

const channelRules = {
  provider: [{ required: true, message: () => t('llm.select_provider'), trigger: 'change' }],
  model_name: [{ required: true, message: () => t('llm.select_model'), trigger: 'change' }],
  name: [{ required: true, message: () => t('llm.channel_name'), trigger: 'blur' }],
}

const availableModels = computed(() => {
  const p = providers.value.find(p => p.code === channelForm.value.provider)
  return p?.models || []
})

const filteredChannels = computed(() => {
  if (!debouncedSearchText.value) return channels.value
  const s = debouncedSearchText.value.toLowerCase()
  return channels.value.filter(c =>
    c.name?.toLowerCase().includes(s) ||
    c.provider?.toLowerCase().includes(s) ||
    c.model_name?.toLowerCase().includes(s)
  )
})

// Paginated channels
const paginatedChannels = computed(() => {
  const start = (pagination.value.page - 1) * pagination.value.pageSize
  const end = start + pagination.value.pageSize
  const result = filteredChannels.value.slice(start, end)
  
  // Debug
  if (import.meta.env.DEV) {
    console.log('[LLMManagement] Pagination:', {
      total: filteredChannels.value.length,
      page: pagination.value.page,
      pageSize: pagination.value.pageSize,
      start,
      end,
      slicedLength: result.length
    })
  }
  
  return result
})

function statusTagType(row) {
  if (!row.is_active) return 'info'
  return row.health_status === 'healthy' ? 'success' : row.health_status === 'unhealthy' ? 'danger' : 'warning'
}

function statusLabel(row) {
  if (!row.is_active) return t('common.inactive')
  
  const healthStatusMap = {
    'healthy': t('llm.health_healthy'),
    'unhealthy': t('llm.health_unhealthy'),
    'unknown': t('llm.health_unknown')
  }
  
  return healthStatusMap[row.health_status] || t('llm.health_unknown')
}

function getSuccessRateColor(rate) {
  if (rate == null) return '#999'
  if (rate >= 90) return '#67C23A'  // green
  if (rate >= 70) return '#E6A23C'  // orange
  return '#F56C6C'  // red
}

function formatResponseTime(ms) {
  if (ms == null || ms < 0) return '-'
  
  // Less than 1 second: show in milliseconds
  if (ms < 1000) {
    return `${Math.round(ms)}ms`
  }
  
  // Less than 1 minute: show in seconds
  if (ms < 60000) {
    const seconds = Math.round(ms / 1000)
    return `${seconds}s`
  }
  
  // Less than 1 hour: show in minutes and seconds
  if (ms < 3600000) {
    const minutes = Math.floor(ms / 60000)
    const seconds = Math.round((ms % 60000) / 1000)
    return `${minutes}m${seconds}s`
  }
  
  // Less than 1 day: show in hours and minutes
  if (ms < 86400000) {
    const hours = Math.floor(ms / 3600000)
    const minutes = Math.round((ms % 3600000) / 60000)
    return `${hours}h${minutes}m`
  }
  
  // More than 1 day: show in days and hours
  const days = Math.floor(ms / 86400000)
  const hours = Math.round((ms % 86400000) / 3600000)
  return `${days}d${hours}h`
}

function getCapabilityTags(row) {
  if (!row.capabilities || row.capabilities.length === 0) return []
  
  const capabilityMap = {
    text_generation: { label: t('settings.cap_text_generation'), type: 'primary' },
    chat: { label: t('settings.cap_chat'), type: 'primary' },
    text_to_image: { label: t('settings.cap_image'), type: 'success' },
    image_generation: { label: t('settings.cap_image'), type: 'success' },
    text_to_video: { label: t('settings.cap_video'), type: 'warning' },
    video_generation: { label: t('settings.cap_video'), type: 'warning' },
    vision: { label: t('settings.cap_vision'), type: 'info' },
    code: { label: t('settings.cap_code'), type: 'info' },
  }
  
  // Map capabilities to tags
  const tags = row.capabilities
    .filter(cap => capabilityMap[cap])
    .map(cap => ({ key: cap, ...capabilityMap[cap] }))
  
  // Deduplicate by label (keep first occurrence)
  const seen = new Set()
  return tags.filter(tag => {
    if (seen.has(tag.label)) {
      return false
    }
    seen.add(tag.label)
    return true
  })
}

// loadChannels is now provided by useAsyncData

async function loadProviders() {
  try {
    const { data } = await getProviders()
    // Unified response format
    providers.value = data.data || []
  } catch (err) {
    console.error('Failed to load providers:', err)
  }
}

function onProviderChange(code) {
  channelForm.value.model_name = ''
  const p = providers.value.find(p => p.code === code)
  if (p) {
    channelForm.value.api_endpoint = p.default_endpoint || ''
    // Auto-detect model type: ollama and lmstudio are local, others are cloud
    const localProviders = ['ollama', 'lmstudio']
    channelForm.value.model_type = localProviders.includes(code) ? 'local' : 'cloud'
    // Auto-fill channel name (will be completed when model is selected)
    if (!isEdit.value) {
      const providerName = p.name || p.name_cn || p.name_en || p.code
      channelForm.value.name = `${providerName} - `
    }
  }
}

function onModelChange(modelCode) {
  // Auto-generate channel name when model is selected
  if (!isEdit.value && channelForm.value.provider && modelCode) {
    const p = providers.value.find(p => p.code === channelForm.value.provider)
    const m = availableModels.value.find(m => m.code === modelCode)
    if (p && m) {
      const providerName = p.name || p.name_cn || p.name_en || p.code
      channelForm.value.name = `${providerName} - ${m.name}`
    }
  }
}

function openAddDialog() {
  isEdit.value = false
  channelForm.value = {
    provider: '', model_name: '', name: '', model_type: 'cloud',
    api_endpoint: '', api_key: '',
    temperature: 0.7, max_tokens: 2048, timeout: 120,
  }
  dialogVisible.value = true
}

function openEditDialog(row) {
  isEdit.value = true
  channelForm.value = {
    id: row.id,
    provider: row.provider,
    model_name: row.model_name,
    name: row.name,
    model_type: row.model_type || 'cloud',
    api_endpoint: row.api_endpoint || '',
    api_key: '',
    temperature: row.temperature || 0.7,
    max_tokens: row.max_tokens || 2048,
    timeout: row.timeout || 120,
  }
  dialogVisible.value = true
}

async function handleSubmit() {
  const valid = await channelFormRef.value?.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    if (isEdit.value) {
      const { id, ...data } = channelForm.value
      if (!data.api_key) delete data.api_key
      await updateChannel(id, data)
      ElMessage.success(t('llm.update_success'))
    } else {
      await registerChannel(channelForm.value)
      ElMessage.success(t('llm.add_success'))
    }
    dialogVisible.value = false
    loadChannels()
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || 'Operation failed')
  } finally {
    submitting.value = false
  }
}

async function toggleActive(row) {
  try {
    await updateChannel(row.id, { is_active: row.is_active })
    ElMessage.success(row.is_active ? t('llm.enable_success') : t('llm.disable_success'))
  } catch (err) {
    row.is_active = !row.is_active
    ElMessage.error('Operation failed')
  }
}

async function testConnection(row) {
  testing.value[row.id] = true
  try {
    const { data } = await request.get(`/llm/health/${row.id}`)
    const health = data.data
    
    if (health.health_status === 'healthy') {
      ElMessage.success({
        message: `${t('llm.connection_success')} - ${t('llm.response_time_label')}: ${health.response_time_ms?.toFixed(0) || 0}ms`,
        duration: 3000
      })
    } else {
      ElMessage.error({
        message: `${t('llm.connection_failed')}: ${health.error_message || t('common.unknown')}`,
        duration: 5000
      })
    }
    
    // Refresh list to update health status
    await loadChannels()
  } catch (error) {
    ElMessage.error(`${t('llm.connection_failed')}: ${error.message || error}`)
  } finally {
    testing.value[row.id] = false
  }
}

// Delete channel with confirmation
const handleDelete = useDeleteConfirm(loadChannels, 'llm.delete_success')

// Handle page change
function handlePageChange({ page, size }) {
  pagination.value.page = page
  pagination.value.pageSize = size
  try {
    localStorage.setItem('llmManagement_pageSize', size.toString())
  } catch {
    // Ignore storage errors (private mode, etc.)
  }
}

// Load providers on mount (useAsyncData auto-loads channels)
loadProviders()

// Debounce search to reduce filtering computations
const { debouncedFn: updateSearch } = useDebounce(() => {
  debouncedSearchText.value = searchText.value
  // Reset to first page when search changes
  pagination.value.page = 1
}, 300)

// Watch searchText and apply debounce
watch(searchText, () => {
  updateSearch()
})

</script>

<style scoped>
.llm-page { padding: 0; }
.page-title { font-size: 24px; font-weight: 700; color: #303133; margin: 0 0 20px; }
.stats-row { margin-bottom: 20px; }
.stats-row .el-col { padding: 12px; background: #fff; border-radius: 8px; }
</style>
