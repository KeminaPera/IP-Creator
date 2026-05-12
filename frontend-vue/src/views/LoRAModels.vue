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
        <el-table-column :label="$t('lora.quality')" width="120" align="center">
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
          v-if="row.status !== 'trained' && row.status !== 'training'"
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
          <el-input v-model="createForm.name" placeholder="e.g., My Character LoRA" />
        </el-form-item>
        <el-form-item :label="$t('lora.base_model')" required>
          <el-select v-model="createForm.base_model" style="width: 100%">
            <el-option label="Stable Diffusion 1.5" value="sd1.5" />
            <el-option label="Stable Diffusion XL" value="sdxl" />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('lora.description')">
          <el-input v-model="createForm.description" type="textarea" :rows="3" placeholder="Optional description" />
        </el-form-item>
        <el-form-item label="Training Epochs">
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
import { ref, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { getLoraList, deleteLora, createLora } from '../api/lora'
import StatusBadge from '../components/common/StatusBadge.vue'
import DataTable from '../components/common/DataTable.vue'
import TrainingWizard from '../components/lora/TrainingWizard.vue'
import TrainingMonitor from '../components/lora/TrainingMonitor.vue'
import QualityReport from '../components/lora/QualityReport.vue'

const { t } = useI18n()

const loading = ref(false)
const loraModels = ref([])
let refreshTimer = null
let isPolling = false  // Track polling state to prevent race conditions

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

async function loadModels() {
  loading.value = true
  try {
    const { data } = await getLoraList({ skip: 0, limit: 50 })
    // Unified response format
    loraModels.value = data.data || []
    
    // Check if any models are training
    const hasTraining = loraModels.value.some(m => m.status === 'training')
    
    if (hasTraining && !isPolling) {
      // Start auto-refresh when training
      startPolling()
    } else if (!hasTraining && isPolling) {
      // Stop auto-refresh when no training
      stopPolling()
    }
  } catch (err) {
    ElMessage.error('Failed to load LoRA models')
    console.error('[LoRAModels] Load error:', err)
  } finally {
    loading.value = false
  }
}

function startPolling() {
  if (isPolling) return  // Prevent multiple intervals
  isPolling = true
  refreshTimer = setInterval(() => {
    loadModels()
  }, 3000)
}

function stopPolling() {
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
  isPolling = false
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
    loadModels()
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
    loadModels()
  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error(t('common.error'))
    }
  }
}

function showTrainingWizard(row) {
  selectedLoraId.value = row.id
  wizardVisible.value = true
}

function showTrainingMonitor(row) {
  selectedLoraId.value = row.id
  monitorVisible.value = true
}

function showQualityReport(row) {
  selectedLoraId.value = row.id
  qualityReportRef.value?.open()
}

function getGradeType(grade) {
  const typeMap = {
    'S': 'success',
    'A': 'success',
    'B': '',
    'C': 'warning',
    'D': 'danger',
    'F': 'danger',
  }
  return typeMap[grade] || 'info'
}

function handleTrainingStarted() {
  loadModels()
}

function handleTrainingCancelled() {
  loadModels()
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
    ElMessage.error('Please enter a name')
    return
  }

  creating.value = true
  try {
    await createLora(createForm.value)
    ElMessage.success('LoRA model created')
    createDialogVisible.value = false
    loadModels()
  } catch (err) {
    ElMessage.error('Failed to create LoRA model')
  } finally {
    creating.value = false
  }
}

onMounted(loadModels)

onUnmounted(() => {
  // Clean up timer when component is destroyed
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
})
</script>

<style scoped>
.lora-page { padding: 0; }
.page-title { font-size: 24px; font-weight: 700; color: #303133; margin: 0 0 20px; }
</style>
