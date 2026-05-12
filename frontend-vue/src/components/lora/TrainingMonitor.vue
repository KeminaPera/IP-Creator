<template>
  <el-dialog
    v-model="visible"
    :title="$t('lora.training_monitor.title')"
    width="1000px"
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <!-- Training Status -->
    <el-card shadow="never" style="margin-bottom: 20px;">
      <div class="status-header">
        <h3>{{ $t('lora.training_monitor.training_status') }}</h3>
        <StatusBadge :status="status" size="large" />
      </div>

      <el-progress
        :percentage="Math.round(progress)"
        :status="status === 'completed' ? 'success' : status === 'failed' ? 'exception' : ''"
        :stroke-width="20"
        style="margin: 20px 0;"
      />

      <el-descriptions :column="3" border size="small">
        <el-descriptions-item :label="$t('lora.training_monitor.epoch')">
          {{ currentEpoch }} / {{ totalEpochs }}
        </el-descriptions-item>
        <el-descriptions-item :label="$t('lora.training_monitor.current_loss')">
          {{ currentLoss?.toFixed(6) || '-' }}
        </el-descriptions-item>
        <el-descriptions-item :label="$t('lora.training_monitor.learning_rate')">
          {{ learningRate?.toExponential(2) || '-' }}
        </el-descriptions-item>
        <el-descriptions-item :label="$t('lora.training_monitor.elapsed_time')">
          {{ formatDuration(elapsedTime) }}
        </el-descriptions-item>
        <el-descriptions-item :label="$t('lora.training_monitor.estimated_remaining')">
          {{ formatDuration(estimatedRemaining) }}
        </el-descriptions-item>
        <el-descriptions-item :label="$t('lora.training_monitor.steps')">
          {{ currentStep }} / {{ totalSteps }}
        </el-descriptions-item>
      </el-descriptions>
    </el-card>

    <!-- Tabs: Charts & Logs -->
    <el-tabs v-model="activeTab" type="border-card">
      <el-tab-pane :label="$t('lora.training_monitor.loss_curve')" name="loss">
        <div ref="lossChartRef" style="height: 400px;"></div>
      </el-tab-pane>

      <el-tab-pane :label="$t('lora.training_monitor.lr_curve')" name="lr">
        <div ref="lrChartRef" style="height: 400px;"></div>
      </el-tab-pane>

      <el-tab-pane :label="$t('lora.training_monitor.logs')" name="logs">
        <div class="log-container">
          <div class="log-toolbar">
            <el-button size="small" @click="loadLogs">
              <el-icon><Refresh /></el-icon>
              {{ $t('lora.training_monitor.refresh') }}
            </el-button>
            <el-button size="small" @click="autoScroll = !autoScroll">
              {{ autoScroll ? $t('lora.training_monitor.stop_scroll') : $t('lora.training_monitor.auto_scroll') }}
            </el-button>
          </div>
          <div ref="logContainerRef" class="log-content">
            <div v-for="(log, index) in logs" :key="index" class="log-line">
              <span class="log-timestamp">{{ formatLogTime(log.timestamp) }}</span>
              <el-tag :type="getLogLevel(log.level)" size="small" style="margin: 0 8px;">
                {{ log.level }}
              </el-tag>
              <span class="log-message">{{ log.message }}</span>
            </div>
            <div v-if="logs.length === 0" class="log-empty">
              {{ $t('lora.training_monitor.no_logs') }}
            </div>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>

    <template #footer>
      <el-button @click="handleClose">{{ $t('common.close') }}</el-button>
      <el-button
        v-if="status === 'training'"
        type="danger"
        @click="handleCancel"
        :loading="cancelling"
      >
        {{ $t('lora.training_monitor.cancel') }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { getTrainingLogs, getTrainingMetrics, cancelTraining } from '../api/lora'
import StatusBadge from '../common/StatusBadge.vue'
import { formatTimeOnly } from '../../utils/time'

const { t } = useI18n()

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  loraId: {
    type: Number,
    required: true
  }
})

const emit = defineEmits(['update:modelValue', 'cancelled'])

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const status = ref('training')
const progress = ref(0)
const currentEpoch = ref(0)
const totalEpochs = ref(10)
const currentLoss = ref(null)
const learningRate = ref(null)
const elapsedTime = ref(0)
const estimatedRemaining = ref(0)
const currentStep = ref(0)
const totalSteps = ref(0)
const logs = ref([])
const activeTab = ref('loss')
const autoScroll = ref(true)
const cancelling = ref(false)

const lossChartRef = ref(null)
const lrChartRef = ref(null)
const logContainerRef = ref(null)

let lossChart = null
let lrChart = null
let refreshTimer = null

watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    loadTrainingData()
    startPolling()
  } else {
    stopPolling()
  }
})

async function loadTrainingData() {
  await Promise.all([
    loadLogs(),
    loadMetrics()
  ])
}

async function loadLogs() {
  try {
    const { data } = await getTrainingLogs(props.loraId, { limit: 100 })
    logs.value = data.data || []
    
    if (autoScroll.value) {
      await nextTick()
      scrollToBottom()
    }
  } catch (err) {
    ElMessage.error(t('lora.training_monitor.load_logs_error'))
  }
}

async function loadMetrics() {
  try {
    const { data } = await getTrainingMetrics(props.loraId)
    const metrics = data.data || {}
    
    status.value = metrics.status || 'training'
    progress.value = metrics.progress || 0
    currentEpoch.value = metrics.current_epoch || 0
    totalEpochs.value = metrics.total_epochs || 10
    currentLoss.value = metrics.current_loss
    learningRate.value = metrics.learning_rate
    elapsedTime.value = metrics.elapsed_time || 0
    estimatedRemaining.value = metrics.estimated_remaining || 0
    currentStep.value = metrics.current_step || 0
    totalSteps.value = metrics.total_steps || 0
    
    updateCharts(metrics)
  } catch (err) {
    ElMessage.error(t('lora.training_monitor.load_metrics_error'))
  }
}

function updateCharts(metrics) {
  try {
    // Update loss chart
    if (lossChart && metrics.loss_history?.length) {
      lossChart.setOption({
        xAxis: {
          data: metrics.loss_history.map((_, i) => i + 1)
        },
        series: [{
          data: metrics.loss_history
        }]
      }, { replaceMerge: ['series'] })
    }

    // Update learning rate chart
    if (lrChart && metrics.lr_history?.length) {
      lrChart.setOption({
        xAxis: {
          data: metrics.lr_history.map((_, i) => i + 1)
        },
        series: [{
          data: metrics.lr_history
        }]
      }, { replaceMerge: ['series'] })
    }
  } catch (err) {
    console.error('Failed to update charts:', err)
  }
}

function initCharts() {
  if (lossChartRef.value && !lossChart) {
    lossChart = echarts.init(lossChartRef.value)
    lossChart.setOption({
      title: {
        text: t('lora.training_monitor.loss_curve'),
        left: 'center'
      },
      tooltip: {
        trigger: 'axis'
      },
      xAxis: {
        type: 'category',
        name: t('lora.training_monitor.y_axis.step'),
        data: []
      },
      yAxis: {
        type: 'value',
        name: t('lora.training_monitor.y_axis.loss')
      },
      series: [{
        type: 'line',
        data: [],
        smooth: true,
        lineStyle: {
          color: '#409EFF'
        },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(64, 158, 255, 0.3)' },
              { offset: 1, color: 'rgba(64, 158, 255, 0.05)' }
            ]
          }
        }
      }]
    })
  }

  if (lrChartRef.value && !lrChart) {
    lrChart = echarts.init(lrChartRef.value)
    lrChart.setOption({
      title: {
        text: t('lora.training_monitor.lr_curve'),
        left: 'center'
      },
      tooltip: {
        trigger: 'axis'
      },
      xAxis: {
        type: 'category',
        name: t('lora.training_monitor.y_axis.step'),
        data: []
      },
      yAxis: {
        type: 'value',
        name: t('lora.training_monitor.y_axis.learning_rate')
      },
      series: [{
        type: 'line',
        data: [],
        smooth: true,
        lineStyle: {
          color: '#67C23A'
        },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(103, 194, 58, 0.3)' },
              { offset: 1, color: 'rgba(103, 194, 58, 0.05)' }
            ]
          }
        }
      }]
    })
  }
}

function startPolling() {
  refreshTimer = setInterval(() => {
    loadTrainingData()
  }, 3000)
}

function stopPolling() {
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
}

function getLogLevel(level) {
  const types = {
    INFO: 'info',
    WARNING: 'warning',
    ERROR: 'danger',
    DEBUG: ''
  }
  return types[level] || 'info'
}

function formatDuration(seconds) {
  if (!seconds || seconds === 0) return '-'
  
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const secs = Math.floor(seconds % 60)
  
  if (hours > 0) {
    return `${hours}h ${minutes}m ${secs}s`
  }
  if (minutes > 0) {
    return `${minutes}m ${secs}s`
  }
  return `${secs}s`
}

function formatLogTime(timestamp) {
  return formatTimeOnly(timestamp)
}

function scrollToBottom() {
  if (logContainerRef.value) {
    logContainerRef.value.scrollTop = logContainerRef.value.scrollHeight
  }
}

async function handleCancel() {
  try {
    await ElMessageBox.confirm(
      t('lora.training_monitor.cancel_confirm'),
      t('common.warning'),
      {
        confirmButtonText: t('common.confirm'),
        cancelButtonText: t('common.cancel'),
        type: 'warning'
      }
    )
    
    cancelling.value = true
    await cancelTraining(props.loraId)
    ElMessage.success(t('lora.training_monitor.cancelled'))
    emit('cancelled')
    handleClose()
  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error(t('common.error'))
    }
  } finally {
    cancelling.value = false
  }
}

function handleClose() {
  visible.value = false
  stopPolling()
}

onMounted(() => {
  if (props.modelValue) {
    initCharts()
    loadTrainingData()
    startPolling()
  }
})

onUnmounted(() => {
  stopPolling()
  if (lossChart) {
    lossChart.dispose()
  }
  if (lrChart) {
    lrChart.dispose()
  }
})
</script>

<style scoped>
.status-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.log-container {
  height: 500px;
  display: flex;
  flex-direction: column;
}

.log-toolbar {
  padding: 10px;
  background: #f5f7fa;
  border-bottom: 1px solid #e4e7ed;
}

.log-content {
  flex: 1;
  overflow-y: auto;
  padding: 10px;
  background: #1e1e1e;
  font-family: 'Courier New', monospace;
  font-size: 13px;
}

.log-line {
  display: flex;
  align-items: center;
  padding: 4px 0;
  color: #d4d4d4;
}

.log-timestamp {
  color: #808080;
  margin-right: 8px;
}

.log-message {
  flex: 1;
}

.log-empty {
  text-align: center;
  color: #909399;
  padding: 40px 0;
}
</style>
