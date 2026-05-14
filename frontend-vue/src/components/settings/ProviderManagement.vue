<template>
  <div class="provider-management" v-loading="loading">
    <el-table :data="providers" stripe style="width: 100%">
      <el-table-column prop="code" :label="$t('settings.model_code')" width="120" />
      <el-table-column :label="$t('settings.provider')" min-width="200">
        <template #default="{ row }">
          <div style="display: flex; align-items: center; gap: 8px;">
            <img v-if="row.icon_url" :src="row.icon_url" :alt="row.name_cn || row.name_en" loading="lazy" style="width: 24px; height: 24px;" />
            <span>{{ row.name_cn || row.name_en }}</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column :label="$t('settings.model_count')" width="100" align="center">
        <template #default="{ row }">
          <el-tooltip 
            v-if="row.models && row.models.length > 0" 
            placement="top"
            :show-after="300"
          >
            <template #content>
              <div style="max-width: 300px;">
                <div v-for="model in row.models" :key="model.id" style="padding: 2px 0;">
                  {{ model.name }}
                </div>
              </div>
            </template>
            <el-tag type="info" style="cursor: pointer;">
              {{ row.models.length }}
            </el-tag>
          </el-tooltip>
          <el-tag v-else type="info">0</el-tag>
        </template>
      </el-table-column>
      <el-table-column :label="$t('settings.last_synced')" width="180">
        <template #default="{ row }">
          <span v-if="row.last_synced_at" style="font-size: 12px;">
            {{ formatTime(row.last_synced_at) }}
          </span>
          <span v-else style="color: #999; font-size: 12px;">{{ $t('settings.never_synced') }}</span>
        </template>
      </el-table-column>
      <el-table-column :label="$t('settings.status')" width="100" align="center">
        <template #default="{ row }">
          <el-switch 
            v-model="row.is_active" 
            @change="toggleProvider(row)"
          />
        </template>
      </el-table-column>
      <el-table-column :label="$t('common.actions')" width="150" align="center">
        <template #default="{ row }">
          <el-button size="small" type="primary" @click="handleSync(row)" :loading="syncing[row.id]">
            {{ $t('settings.provider_sync') }}
          </el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { getProviders, syncProviderModels, updateProvider } from '../../api/settings'

const { t } = useI18n()

const loading = ref(false)
const providers = ref([])
const syncing = ref({})

const loadProviders = async () => {
  loading.value = true
  try {
    // 获取所有供应商（包括禁用的），以便管理状态
    const { data } = await getProviders(true)
    // Unified response format: { success: true, data: [...] }
    providers.value = data.data || []
  } catch (error) {
    ElMessage.error(t('common.load_failed'))
    console.error('Failed to load providers:', error)
  } finally {
    loading.value = false
  }
}

const toggleProvider = async (provider) => {
  try {
    // 调用 API 更新供应商状态
    await updateProvider(provider.id, { is_active: provider.is_active })
    ElMessage.success(provider.is_active ? t('common.enable_success') : t('common.disable_success'))
  } catch (error) {
    // 如果失败，恢复原状态
    provider.is_active = !provider.is_active
    ElMessage.error(t('common.update_failed'))
    console.error('Failed to toggle provider:', error)
  }
}

const handleSync = async (provider) => {
  syncing.value[provider.id] = true
  try {
    await syncProviderModels(provider.code)
    ElMessage.success(t('settings.provider_sync_success'))
    await loadProviders() // Reload
  } catch (error) {
    ElMessage.error(t('settings.provider_sync_failed'))
    console.error('Failed to sync provider:', error)
  } finally {
    syncing.value[provider.id] = false
  }
}

const formatTime = (time) => {
  if (!time) return ''
  const date = new Date(time)
  return date.toLocaleString('zh-CN')
}

onMounted(() => {
  loadProviders()
})
</script>

<style scoped>
.provider-management {
  padding: 10px 0;
}
</style>
