<template>
  <div class="model-management" v-loading="loading">
    <!-- Filters -->
    <el-row :gutter="16" style="margin-bottom: 16px;">
      <el-col :span="6">
        <el-select v-model="filterProvider" :placeholder="$t('settings.select_provider')" clearable @change="handleFilter" style="width: 100%">
          <el-option 
            v-for="provider in providers" 
            :key="provider.id" 
            :label="provider.name_cn || provider.name_en" 
            :value="provider.id"
          >
            <div style="display:flex;align-items:center;gap:8px;">
              <img v-if="provider.icon_url" :src="provider.icon_url" loading="lazy" style="width:18px;height:18px;" />
              <span>{{ provider.name_cn || provider.name_en || provider.code }}</span>
            </div>
          </el-option>
        </el-select>
      </el-col>
      <el-col :span="6">
        <el-select v-model="filterCapability" :placeholder="$t('settings.select_capability')" clearable @change="handleFilter" style="width: 100%">
          <el-option :label="$t('settings.cap_text_generation')" value="text_generation" />
          <el-option :label="$t('settings.cap_vision')" value="vision" />
          <el-option :label="$t('settings.cap_chat')" value="chat" />
          <el-option :label="$t('settings.cap_code')" value="code" />
        </el-select>
      </el-col>
    </el-row>

    <!-- Model List -->
    <el-table :data="filteredModels" stripe style="width: 100%">
      <el-table-column prop="code" :label="$t('settings.model_code')" width="180" />
      <el-table-column prop="name" :label="$t('settings.model_name')" min-width="150" />
      <el-table-column :label="$t('settings.provider')" width="150">
        <template #default="{ row }">
          {{ getProviderName(row.provider_id) }}
        </template>
      </el-table-column>
      <el-table-column :label="$t('settings.capability')" min-width="200">
        <template #default="{ row }">
          <div style="display: flex; flex-wrap: wrap; gap: 4px;">
            <el-tag 
              v-for="cap in row.capabilities" 
              :key="cap" 
              size="small" 
              type="info"
            >
              {{ getCapabilityLabel(cap) }}
            </el-tag>
          </div>
        </template>
      </el-table-column>
      <el-table-column :label="$t('settings.max_context')" width="120" align="center">
        <template #default="{ row }">
          {{ formatTokens(row.max_tokens) }}
        </template>
      </el-table-column>
      <el-table-column :label="$t('settings.max_output')" width="120" align="center">
        <template #default="{ row }">
          {{ formatTokens(row.max_output_tokens) }}
        </template>
      </el-table-column>
      <el-table-column :label="$t('settings.price')" width="180">
        <template #default="{ row }">
          <div v-if="row.input_price_per_million" style="font-size: 12px;">
            <div>{{ $t('settings.input_price') }}: ¥{{ row.input_price_per_million }}/M</div>
            <div>{{ $t('settings.output_price') }}: ¥{{ row.output_price_per_million }}/M</div>
          </div>
          <span v-else style="color: #999;">-</span>
        </template>
      </el-table-column>
      <el-table-column :label="$t('settings.status')" width="100" align="center">
        <template #default="{ row }">
          <el-switch 
            v-model="row.is_active" 
            @change="toggleModel(row)"
          />
        </template>
      </el-table-column>
    </el-table>
    
    <el-empty v-if="filteredModels.length === 0" :description="$t('settings.no_model_data')" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { getProviders, getModels, updateModel } from '../../api/settings'

const { t } = useI18n()

const loading = ref(false)
const providers = ref([])
const models = ref([])
const filterProvider = ref(null)
const filterCapability = ref(null)

const filteredModels = computed(() => {
  let result = models.value
  
  if (filterProvider.value) {
    result = result.filter(m => m.provider_id === filterProvider.value)
  }
  
  if (filterCapability.value) {
    result = result.filter(m => 
      m.capabilities && m.capabilities.includes(filterCapability.value)
    )
  }
  
  return result
})

const loadProviders = async () => {
  try {
    // 获取所有供应商（包括禁用的）
    const { data } = await getProviders(true)
    // Unified response format
    providers.value = data.data || []
  } catch (error) {
    console.error('Failed to load providers:', error)
  }
}

const loadModels = async () => {
  loading.value = true
  try {
    // 获取所有模型（包括禁用的），以便管理状态
    const { data } = await getModels(null, null, true)
    // Unified response format
    models.value = data.data || []
  } catch (error) {
    ElMessage.error(t('common.load_failed'))
    console.error('Failed to load models:', error)
  } finally {
    loading.value = false
  }
}

const handleFilter = () => {
  // 筛选逻辑由 computed 自动处理
}

const formatTokens = (tokens) => {
  if (!tokens) return '-'
  if (tokens >= 1000) {
    return `${(tokens / 1000).toFixed(0)}K`
  }
  return tokens.toString()
}

const getCapabilityLabel = (cap) => {
  const labels = {
    text_generation: t('settings.cap_text_generation'),
    vision: t('settings.cap_vision'),
    chat: t('settings.cap_chat'),
    code: t('settings.cap_code')
  }
  return labels[cap] || cap
}

const getProviderName = (providerId) => {
  const provider = providers.value.find(p => p.id === providerId)
  return provider ? (provider.name_cn || provider.name_en) : '-'
}

const toggleModel = async (model) => {
  try {
    // 调用 API 更新模型状态
    await updateModel(model.id, { is_active: model.is_active })
    ElMessage.success(model.is_active ? t('common.enable_success') : t('common.disable_success'))
  } catch (error) {
    // 如果失败，恢复原状态
    model.is_active = !model.is_active
    ElMessage.error(t('common.update_failed'))
    console.error('Failed to toggle model:', error)
  }
}

onMounted(async () => {
  await Promise.all([
    loadProviders(),
    loadModels()
  ])
})
</script>

<style scoped>
.model-management {
  padding: 10px 0;
}
</style>
