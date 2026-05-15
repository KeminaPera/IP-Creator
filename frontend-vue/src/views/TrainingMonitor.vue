<template>
  <div class="training-monitor-page">
    <div class="page-header">
      <h1>{{ t('training_monitor.title') }}</h1>
      <el-button @click="$router.push('/lora')">{{ t('training_monitor.back_to_lora') }}</el-button>
    </div>

    <div v-if="loading" class="loading-state">
      <el-icon class="is-loading"><Loading /></el-icon>
      <p>{{ t('training_monitor.loading') }}</p>
    </div>

    <div v-else-if="error" class="error-state">
      <el-alert type="error" :title="error" :closable="false" />
    </div>

    <div v-else class="monitor-content">
      <!-- Training Overview -->
      <el-card class="overview-card">
        <template #header>
          <h2>{{ t('training_monitor.overview') }}</h2>
        </template>
        
        <el-descriptions :column="2" border>
          <el-descriptions-item :label="t('training_monitor.model_name')">
            {{ loraModel.name }}
          </el-descriptions-item>
          <el-descriptions-item :label="t('training_monitor.status')">
            <el-tag :type="statusType">{{ getStatusLabel(loraModel.status) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item :label="t('training_monitor.base_model')">
            {{ loraModel.base_model }}
          </el-descriptions-item>
          <el-descriptions-item :label="t('training_monitor.final_loss')">
            {{ loraModel.final_loss || t('common.none') }}
          </el-descriptions-item>
          <el-descriptions-item :label="t('training_monitor.training_steps')">
            {{ loraModel.training_steps || t('common.none') }}
          </el-descriptions-item>
          <el-descriptions-item :label="t('training_monitor.training_time')">
            {{ loraModel.training_time_minutes ? `${loraModel.training_time_minutes.toFixed(1)} min` : t('common.none') }}
          </el-descriptions-item>
        </el-descriptions>
      </el-card>

      <!-- Training Monitor Component -->
      <TrainingMonitorComponent 
        v-if="loraId"
        :lora-id="loraId"
        :auto-start="true"
      />

      <!-- Quick Actions -->
      <el-card class="actions-card">
        <template #header>
          <h2>{{ t('training_monitor.quick_actions') }}</h2>
        </template>
        
        <el-space wrap>
          <el-button 
            type="primary" 
            @click="viewQualityReport"
            :disabled="loraModel.status !== 'completed'"
          >
            {{ t('training_monitor.view_quality_report') }}
          </el-button>
          
          <el-button 
            type="success"
            @click="viewLogs"
          >
            {{ t('training_monitor.view_logs') }}
          </el-button>
          
          <el-button 
            type="warning"
            @click="viewMetrics"
          >
            {{ t('training_monitor.view_metrics') }}
          </el-button>
          
          <el-button 
            type="danger"
            @click="cancelTraining"
            :disabled="loraModel.status !== 'training'"
          >
            {{ t('training_monitor.cancel_training') }}
          </el-button>
        </el-space>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'
import TrainingMonitorComponent from '@/components/lora/TrainingMonitor.vue'
import { getLoRADetail, cancelTraining as cancelTrainingApi } from '@/api/lora'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()

const loading = ref(false)
const error = ref(null)
const loraModel = ref(null)

const loraId = computed(() => parseInt(route.params.loraId))

const statusType = computed(() => {
  if (!loraModel.value) return 'info'
  const statusMap = {
    'not_trained': 'info',
    'training': 'warning',
    'completed': 'success',
    'failed': 'danger',
    'cancelled': 'info'
  }
  return statusMap[loraModel.value.status] || 'info'
})

const getStatusLabel = (status) => {
  const key = `lora.status.${status}`
  return t(key) || status
}

const loadLoRADetails = async () => {
  loading.value = true
  error.value = null
  
  try {
    const response = await getLoRADetail(loraId.value)
    loraModel.value = response.data
  } catch (err) {
    error.value = err.message || t('training_monitor.load_failed')
    ElMessage.error(error.value)
  } finally {
    loading.value = false
  }
}

const viewQualityReport = () => {
  router.push(`/lora/${loraId.value}/quality-report`)
}

const viewLogs = async () => {
  try {
    router.push(`/lora`)
    ElMessage.info(t('training_monitor.logs_available'))
  } catch (err) {
    ElMessage.error(t('training_monitor.logs_failed'))
  }
}

const viewMetrics = async () => {
  try {
    router.push(`/lora`)
    ElMessage.info(t('training_monitor.metrics_available'))
  } catch (err) {
    ElMessage.error(t('training_monitor.metrics_failed'))
  }
}

const cancelTraining = async () => {
  try {
    await ElMessageBox.confirm(
      t('training_monitor.cancel_confirm_message'),
      t('training_monitor.cancel_title'),
      {
        confirmButtonText: t('training_monitor.cancel_confirm'),
        cancelButtonText: t('training_monitor.cancel_reject'),
        type: 'warning',
      }
    )
    
    await cancelTrainingApi(loraId.value)
    ElMessage.success(t('training_monitor.cancel_success'))
    await loadLoRADetails()
  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error(t('training_monitor.cancel_failed'))
    }
  }
}

onMounted(() => {
  loadLoRADetails()
})
</script>

<style scoped>
.training-monitor-page {
  max-width: 1400px;
  margin: 0 auto;
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.page-header h1 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
}

.loading-state, .error-state {
  text-align: center;
  padding: 60px 20px;
}

.loading-state .el-icon {
  font-size: 48px;
  color: #409eff;
  margin-bottom: 16px;
}

.monitor-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.overview-card, .actions-card {
  margin-bottom: 0;
}

h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}
</style>
