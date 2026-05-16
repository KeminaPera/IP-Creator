<template>
  <div class="lora-page">
    <!-- Toolbar -->
    <DataTable
      :data="loraModels"
      :loading="loading"
      :show-pagination="false"
    >
      <template #toolbar>
        <div style="display: flex; justify-content: space-between; align-items: center; width: 100%;">
          <h1 class="page-title" style="margin: 0;">{{ $t('lora.title') }}</h1>
          <el-button type="primary" @click="showCreateDialog">
            <el-icon><Plus /></el-icon>
            <span>{{ $t('lora.create_lora') }}</span>
          </el-button>
        </div>
      </template>

      <template #default>
        <el-table-column prop="name" :label="$t('lora.name')" min-width="180" />
        <el-table-column prop="base_model" :label="$t('lora.base_model')" width="150" />
        <el-table-column :label="$t('lora.status')" width="120" align="center">
          <template #default="{ row }">
            <StatusBadge :status="row.status" />
          </template>
        </el-table-column>
        <el-table-column :label="$t('lora.training_progress')" width="200">
          <template #default="{ row }">
            <div v-if="row.status === 'training'">
              <el-progress 
                :percentage="Math.round(row.progress || 0)" 
                :status="row.progress < 100 ? '' : 'success'"
                :stroke-width="8"
              />
              <div style="font-size: 12px; color: #909399; margin-top: 4px;">
                <span>Epoch {{ row.current_epoch || 0 }}/{{ row.total_epochs || 10 }}</span>
                <span style="margin-left: 8px;">Loss: {{ row.current_loss?.toFixed(4) || '-' }}</span>
              </div>
            </div>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column :label="$t('lora.associated_ip')" width="140">
          <template #default="{ row }">
            <span>{{ row.ip_name || $t('lora.no_ip') }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="final_loss" :label="$t('lora.final_loss')" width="100" align="center">
          <template #default="{ row }">
            <span>{{ row.final_loss != null ? row.final_loss.toFixed(4) : '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="training_steps" :label="$t('lora.training_steps')" width="120" align="center" />
        <el-table-column :label="$t('lora.quality_score')" width="120" align="center">
          <template #default="{ row }">
            <el-tag
              v-if="row.quality_grade"
              :type="getGradeType(row.quality_grade)"
              size="small"
              effect="dark"
            >
              {{ row.quality_grade }} ({{ row.quality_score?.toFixed(0) }})
            </el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
      </template>

      <template #actions="{ row }">
        <el-button
          v-if="row.status === 'failed' && row.error_message"
          size="small"
          type="warning"
          plain
          @click="showErrorReason(row)"
        >
          <el-icon><WarningFilled /></el-icon>
          {{ $t('lora.view_error') }}
        </el-button>
        <el-button
          v-if="row.status === 'pending' || row.status === 'failed'"
          size="small"
          type="primary"
          @click="showTrainingWizard(row)"
        >
          {{ $t('lora.train') }}
        </el-button>
        <el-button
          v-if="row.status === 'training'"
          size="small"
          type="success"
          @click="showTrainingMonitor(row)"
        >
          {{ $t('lora.monitor') }}
        </el-button>
        <el-button
          v-if="row.status === 'completed' || row.status === 'trained'"
          size="small"
          type="warning"
          @click="showQualityReport(row)"
        >
          {{ $t('lora.quality_report') }}
        </el-button>
        <el-button
          size="small"
          type="danger"
          @click="handleDelete(row)"
        >
          {{ $t('lora.delete') }}
        </el-button>
      </template>
    </DataTable>

    <!-- Create LoRA Dialog -->
    <el-dialog v-model="createDialogVisible" :title="$t('lora.create_lora')" width="500px">
      <el-form :model="createForm" label-width="120px">
        <el-form-item :label="$t('lora.name')" required>
          <el-input v-model="createForm.name" :placeholder="$t('lora.name_placeholder')" />
        </el-form-item>
        <el-form-item :label="$t('lora.base_model')" required>
          <el-select v-model="createForm.base_model" style="width: 100%">
            <el-option label="Stable Diffusion 1.5" value="sd1.5" />
            <el-option label="Stable Diffusion XL" value="sdxl" />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('lora.description')">
          <el-input v-model="createForm.description" type="textarea" :rows="3" :placeholder="$t('lora.description_placeholder')" />
        </el-form-item>
        <el-form-item :label="$t('lora.training_epochs')">
          <el-input-number v-model="createForm.epochs" :min="1" :max="100" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" @click="handleCreate" :loading="creating">{{ $t('common.confirm') }}</el-button>
      </template>
    </el-dialog>

    <!-- Training Wizard Dialog -->
    <TrainingWizard
      v-model="wizardVisible"
      :lora-id="selectedLoraId"
      @training-started="handleTrainingStarted"
    />

    <!-- Training Monitor Dialog -->
    <TrainingMonitor
      v-model="monitorVisible"
      :lora-id="selectedLoraId"
      @cancelled="handleTrainingCancelled"
    />

    <!-- Quality Report Dialog -->
    <QualityReport
      ref="qualityReportRef"
      :lora-id="selectedLoraId"
      @update="loadModels"
    />
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, WarningFilled } from '@element-plus/icons-vue'
import { getLoraList, deleteLora, createLora } from '@/api/lora'
import { useAsyncData, useAsyncList } from '@/composables/useAsyncData'
import { usePolling } from '@/composables/usePolling'
import { getGradeType } from '@/utils/grade'
import StatusBadge from '../components/common/StatusBadge.vue'
import DataTable from '../components/common/DataTable.vue'
import TrainingWizard from '../components/lora/TrainingWizard.vue'
import TrainingMonitor from '../components/lora/TrainingMonitor.vue'
import QualityReport from '../components/lora/QualityReport.vue'

const { t } = useI18n()

// Use useAsyncList for automatic data fetching with pagination
const { 
  loading, 
  list: loraModels, 
  execute: loadModels 
} = useAsyncList(
  (params) => getLoraList({ skip: params.skip, limit: params.limit }),
  { 
    errorMessage: 'lora.load_failed',
    autoLoad: true
  }
)

// Use usePolling for automatic refresh during training
const { start: startPolling, stop: stopPolling, isRunning: isPolling } = usePolling(
  () => loadModelsWithPolling(),
  3000, // 3 seconds
  { autoStart: false }
)

// Create dialog
const createDialogVisible = ref(false)
const creating = ref(false)
const createForm = ref({
  name: '',
  base_model: 'sd1.5',
  description: '',
  epochs: 10,
})

// Training wizard
const wizardVisible = ref(false)
const selectedLoraId = ref(null)

// Training monitor
const monitorVisible = ref(false)

// Quality report
const qualityReportRef = ref(null)

// Watch for training status to auto-start polling
function checkAndTogglePolling() {
  const hasTraining = loraModels.value.some(m => m.status === 'training')
  
  if (hasTraining && !isPolling.value) {
    startPolling()
  } else if (!hasTraining && isPolling.value) {
    stopPolling()
  }
}

// Wrapped loadModels with polling check
async function loadModelsWithPolling() {
  await loadModels()
  checkAndTogglePolling()
}

async function handleTrain(row) {
  try {
    await ElMessageBox.confirm(
      t('lora.train_confirm'),
      t('common.confirm'),
      {
        confirmButtonText: t('common.confirm'),
        cancelButtonText: t('common.cancel'),
        type: 'warning',
      }
    )
    await trainLora(row.id)
    ElMessage.success(t('common.success'))
    loadModelsWithPolling()
  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error(t('common.error'))
    }
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(
      t('lora.delete_confirm'),
      t('common.warning'),
      {
        confirmButtonText: t('common.confirm'),
        cancelButtonText: t('common.cancel'),
        type: 'warning',
      }
    )
    await deleteLora(row.id)
    ElMessage.success(t('common.success'))
    loadModelsWithPolling()
  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error(t('common.error'))
    }
  }
}

function showTrainingWizard(row) {
  if (!row.id) {
    ElMessage.error(t('lora.invalid_model_id'))
    return
  }
  selectedLoraId.value = row.id
  wizardVisible.value = true
}

function showTrainingMonitor(row) {
  if (!row.id) {
    ElMessage.error(t('lora.invalid_model_id'))
    return
  }
  selectedLoraId.value = row.id
  monitorVisible.value = true
}

function showQualityReport(row) {
  if (!row.id) {
    ElMessage.error(t('lora.invalid_model_id'))
    return
  }
  selectedLoraId.value = row.id
  qualityReportRef.value?.open()
}

function showErrorReason(row) {
  if (!row.error_message) {
    ElMessage.warning(t('lora.no_error_message'))
    return
  }
  
  ElMessageBox.alert(
    `<pre style="white-space: pre-wrap; word-break: break-word; max-height: 400px; overflow-y: auto;">${row.error_message}</pre>`,
    t('lora.error_details'),
    {
      dangerouslyUseHTMLString: true,
      confirmButtonText: t('common.close'),
      customClass: 'error-message-dialog'
    }
  )
}

// getGradeType is now imported from @/utils/grade

function handleTrainingStarted() {
  loadModelsWithPolling()
}

function handleTrainingCancelled() {
  loadModelsWithPolling()
}

function showCreateDialog() {
  createForm.value = {
    name: '',
    base_model: 'sd1.5',
    description: '',
    epochs: 10,
  }
  createDialogVisible.value = true
}

async function handleCreate() {
  if (!createForm.value.name) {
    ElMessage.error(t('lora.please_enter_name'))
    return
  }

  creating.value = true
  try {
    await createLora(createForm.value)
    ElMessage.success(t('lora.create_success'))
    createDialogVisible.value = false
    loadModelsWithPolling()
  } catch (err) {
    ElMessage.error(t('lora.create_failed'))
  } finally {
    creating.value = false
  }
}

// useAsyncList auto-loads on mount, usePolling auto-cleans up on unmount
</script>

<style scoped>
.lora-page { padding: 0; }
.page-title { font-size: 24px; font-weight: 700; color: #303133; margin: 0 0 20px; }
</style>
