<template>
  <div class="dashboard">
    <h1 class="page-title">{{ $t('dashboard.title') }}</h1>

    <!-- Stats Row -->
    <el-row :gutter="20" class="stats-row">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card stat-blue">
          <div class="stat-content">
            <div class="stat-info">
              <p class="stat-label">{{ $t('dashboard.llm_models') }}</p>
              <p class="stat-value">{{ stats.llm_count }}</p>
              <p class="stat-sub">{{ $t('dashboard.active') }}: {{ stats.active_llm_count }}</p>
            </div>
            <el-icon :size="48" class="stat-icon"><Monitor /></el-icon>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card stat-green">
          <div class="stat-content">
            <div class="stat-info">
              <p class="stat-label">{{ $t('dashboard.ip_assets') }}</p>
              <p class="stat-value">{{ stats.ip_count }}</p>
            </div>
            <el-icon :size="48" class="stat-icon"><PictureFilled /></el-icon>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card stat-orange">
          <div class="stat-content">
            <div class="stat-info">
              <p class="stat-label">{{ $t('dashboard.total_tasks') }}</p>
              <p class="stat-value">{{ stats.task_count }}</p>
            </div>
            <el-icon :size="48" class="stat-icon"><List /></el-icon>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card stat-purple">
          <div class="stat-content">
            <div class="stat-info">
              <p class="stat-label">{{ $t('dashboard.lora_models') }}</p>
              <p class="stat-value">{{ stats.lora_count }}</p>
            </div>
            <el-icon :size="48" class="stat-icon"><Coin /></el-icon>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Quick Actions -->
    <el-card style="margin-top: 20px;">
      <template #header>
        <span>{{ $t('dashboard.quick_actions') }}</span>
      </template>
      <el-row :gutter="16">
        <el-col :span="8">
          <el-button type="primary" size="large" class="action-btn" @click="$router.push('/generate')">
            <el-icon><VideoCameraFilled /></el-icon>
            {{ $t('dashboard.start_generation') }}
          </el-button>
        </el-col>
        <el-col :span="8">
          <el-button type="success" size="large" class="action-btn" @click="$router.push('/ip')">
            <el-icon><Plus /></el-icon>
            {{ $t('dashboard.create_ip') }}
          </el-button>
        </el-col>
        <el-col :span="8">
          <el-button type="warning" size="large" class="action-btn" @click="$router.push('/llm')">
            <el-icon><Setting /></el-icon>
            {{ $t('dashboard.configure_llm') }}
          </el-button>
        </el-col>
      </el-row>
    </el-card>

    <!-- System Health Check -->
    <el-card style="margin-top: 20px;" v-loading="healthLoading">
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <div style="display: flex; align-items: center; gap: 12px;">
            <span>{{ $t('dashboard.system_health') }}</span>
            <!-- Status indicators (only show when there are warnings/errors) -->
            <template v-if="healthData && healthData.overall_status !== 'healthy'">
              <el-tag v-if="errorCount > 0" type="danger" size="small" effect="plain">
                {{ errorCount }} {{ $t('dashboard.status_error') }}
              </el-tag>
              <el-tag v-if="warningCount > 0" type="warning" size="small" effect="plain">
                {{ warningCount }} {{ $t('dashboard.status_warning') }}
              </el-tag>
            </template>
          </div>
          <el-button size="small" @click="loadHealth" :loading="healthLoading">
            <el-icon><Refresh /></el-icon>
            {{ $t('dashboard.refresh_health') }}
          </el-button>
        </div>
      </template>

      <!-- Health Check Items -->
      <el-row :gutter="16">
        <el-col :span="8" v-for="item in healthItems" :key="item.key">
          <el-popover
            placement="top"
            :width="400"
            trigger="hover"
            :show-after="200"
          >
            <template #reference>
              <el-card shadow="hover" style="margin-bottom: 16px; cursor: pointer;">
                <div style="display: flex; align-items: center; gap: 12px;">
                  <el-icon :size="32" :color="item.color">
                    <component :is="item.icon" />
                  </el-icon>
                  <div style="flex: 1;">
                    <div style="font-weight: 600; margin-bottom: 4px;">{{ item.name }}</div>
                    <el-tag :type="item.statusType" size="small">{{ item.statusText }}</el-tag>
                    <div style="font-size: 12px; color: #909399; margin-top: 4px;">{{ item.shortMessage }}</div>
                  </div>
                </div>
              </el-card>
            </template>
            
            <!-- Popover Content with scrollable area -->
            <div class="health-detail">
              <div class="health-detail-header">
                <h4 style="margin: 0 0 8px 0;">{{ item.name }}</h4>
                <el-tag :type="item.statusType" size="small">{{ item.statusText }}</el-tag>
              </div>
              
              <el-divider style="margin: 12px 0;" />
              
              <!-- Scrollable content area -->
              <div class="health-detail-scrollable">
                <div class="health-detail-content">
                <div class="detail-row">
                  <span class="detail-label">{{ $t('dashboard.health_check_item') }}:</span>
                  <span class="detail-value">{{ item.checkDescription }}</span>
                </div>
                
                <!-- Show URL for Redis and Database connections -->
                <div v-if="(item.key === 'redis' || item.key === 'database') && item.url" class="detail-row">
                  <span class="detail-label">{{ $t('dashboard.health_connection_url') }}:</span>
                  <span class="detail-value detail-url">{{ item.url }}</span>
                </div>
                
                <!-- Show storage path for Diffusion Models -->
                <div v-if="item.key === 'diffusion_models' && item.modelsPath" class="detail-row">
                  <span class="detail-label">{{ $t('dashboard.models_storage_path') }}:</span>
                  <span class="detail-value detail-path">{{ item.modelsPath }}</span>
                </div>
                
                <!-- Enhanced diffusion models list with download buttons -->
                <div v-if="item.key === 'diffusion_models' && item.requiredModels" class="detail-diffusion-models">
                  <el-divider style="margin: 12px 0;">
                    <span style="color: #909399; font-size: 12px;">{{ $t('dashboard.models_list') }}</span>
                  </el-divider>
                  
                  <!-- Model list -->
                  <div v-for="model in item.requiredModels" :key="model.repo" class="model-download-item">
                    <div class="model-info-header">
                      <span class="model-name">{{ model.name }}</span>
                      <el-tag 
                        :type="getModelStatusType(model.status)" 
                        size="small"
                      >
                        {{ getModelStatusText(model.status) }}
                      </el-tag>
                    </div>
                    
                    <div class="model-meta">
                      <span class="model-purpose">{{ model.purpose_en }}</span>
                      <span class="model-size">{{ model.size_gb }} GB</span>
                    </div>
                    
                    <!-- Show integrity info for incomplete models -->
                    <div v-if="model.status === 'incomplete'" class="model-integrity-warning">
                      <el-icon :size="14" class="warning-icon"><Warning /></el-icon>
                      <span class="integrity-text">
                        {{ $t('dashboard.model_incomplete') }}
                      </span>
                    </div>
                    
                    <!-- Download button (for missing or incomplete models) -->
                    <el-button
                      v-if="model.status === 'missing' || model.status === 'incomplete'"
                      type="primary"
                      size="small"
                      :loading="downloadingModels.includes(model.model_id)"
                      @click="downloadModel(model)"
                    >
                      <el-icon><Download /></el-icon>
                      {{ model.status === 'incomplete' ? $t('dashboard.redownload') : $t('dashboard.model_download') }}
                    </el-button>
                    
                    <!-- Downloading indicator -->
                    <div v-if="model.status === 'downloading'" class="model-downloading-indicator">
                      <el-icon class="is-loading" :size="16"><Refresh /></el-icon>
                      <span>{{ $t('dashboard.download_in_progress') }}</span>
                    </div>
                  </div>
                  
                  <!-- Download progress section -->
                  <div v-if="activeDownloads.length > 0" class="download-progress-section">
                    <el-divider class="detail-divider">
                      <span class="text-muted">{{ $t('dashboard.download_progress') }}</span>
                    </el-divider>
                    
                    <div v-for="download in activeDownloads" :key="download.taskId" class="download-progress-item">
                      <div class="download-header">
                        <span class="download-model-name">{{ download.modelName }}</span>
                        <span class="download-percentage">{{ download.progress }}%</span>
                      </div>
                      <el-progress 
                        :percentage="download.progress" 
                        :status="download.progress === 100 ? 'success' : ''"
                        :stroke-width="8"
                      />
                      <div class="download-meta">
                        <span>{{ download.downloadedMB }} / {{ download.totalMB }} MB</span>
                        <span v-if="download.speed">{{ download.speed }} MB/s</span>
                        <span v-if="download.eta">{{ $t('dashboard.download_eta', { seconds: download.eta }) }}</span>
                        <span v-if="download.statusMsg" class="download-status-msg">{{ download.statusMsg }}</span>
                      </div>
                    </div>
                  </div>
                </div>
                
                <!-- Show directory list with details -->
                <div v-if="item.key === 'directories' && item.directoryList" class="detail-directory-list">
                  <el-divider class="detail-divider">
                    <span class="text-muted">{{ $t('dashboard.directories_detail') }}</span>
                  </el-divider>
                  <div v-for="dir in item.directoryList" :key="dir.name" class="directory-item">
                    <div class="directory-header">
                      <el-icon :size="16"><FolderOpened /></el-icon>
                      <span class="directory-name">{{ dir.name.replace('_PATH', '') }}</span>
                      <el-tag :type="dir.exists ? 'success' : 'danger'" size="small">
                        {{ dir.exists ? $t('dashboard.exists') : $t('dashboard.missing') }}
                      </el-tag>
                    </div>
                    <div class="directory-path">{{ dir.path }}</div>
                    <div class="directory-desc">{{ dir.description_zh }}</div>
                  </div>
                </div>
                
                <!-- Show GPU detailed information -->
                <div v-if="item.key === 'gpu' && item.gpuInfo" class="detail-gpu-info">
                  <el-divider class="detail-divider">
                    <span class="text-muted">{{ $t('dashboard.gpu_info') }}</span>
                  </el-divider>
                  <div class="gpu-info-row">
                    <span class="gpu-label">{{ $t('dashboard.device') }}:</span>
                    <span class="gpu-value">{{ item.gpuInfo.name || $t('common.none') }}</span>
                  </div>
                  <div class="gpu-info-row">
                    <span class="gpu-label">{{ $t('dashboard.count') }}:</span>
                    <span class="gpu-value">{{ item.gpuInfo.count || 0 }}</span>
                  </div>
                  <div class="gpu-info-row">
                    <span class="gpu-label">{{ $t('dashboard.memory') }}:</span>
                    <span class="gpu-value">{{ item.gpuInfo.memory_gb || 0 }} GB</span>
                  </div>
                  <div class="gpu-info-row">
                    <span class="gpu-label">{{ $t('dashboard.status_label') }}:</span>
                    <el-tag :type="item.gpuInfo.available ? 'success' : 'warning'" size="small">
                      {{ item.gpuInfo.available ? $t('dashboard.available') : $t('dashboard.using_cpu') }}
                    </el-tag>
                  </div>
                  <div v-if="!item.gpuInfo.available" class="gpu-warning">
                    <el-icon><Warning /></el-icon>
                    <span>{{ $t('dashboard.gpu_warning') }}</span>
                  </div>
                </div>

                <!-- Show Celery Worker detailed information -->
                <div v-if="item.key === 'celery_worker' && item.celeryInfo" class="detail-celery-info">
                  <el-divider class="detail-divider">
                    <span class="text-muted">{{ $t('dashboard.celery_worker_info') }}</span>
                  </el-divider>
                  <div class="gpu-info-row">
                    <span class="gpu-label">{{ $t('dashboard.status_label') }}:</span>
                    <el-tag :type="item.celeryInfo.active ? 'success' : 'warning'" size="small">
                      {{ item.celeryInfo.active ? $t('dashboard.online') : $t('dashboard.not_detected') }}
                    </el-tag>
                  </div>
                  <div class="gpu-info-row">
                    <span class="gpu-label">{{ $t('dashboard.worker_count') }}:</span>
                    <span class="gpu-value">{{ item.celeryInfo.workers.length }}</span>
                  </div>
                  <div v-if="item.celeryInfo.workers.length > 0" class="gpu-info-row gpu-info-row--align-top">
                    <span class="gpu-label">{{ $t('dashboard.node_name') }}:</span>
                    <div class="gpu-value gpu-value--column">
                      <el-tag
                        v-for="w in item.celeryInfo.workers"
                        :key="w"
                        size="small"
                        type="info"
                        class="node-tag"
                      >{{ w }}</el-tag>
                    </div>
                  </div>
                  <div v-if="item.celeryInfo.method" class="gpu-info-row">
                    <span class="gpu-label">探测方式:</span>
                    <el-tag
                      size="small"
                      :type="item.celeryInfo.method === 'control.ping' ? 'success' : 'warning'"
                    >
                      {{ item.celeryInfo.method === 'control.ping' ? 'Ping (即时响应)' : 'Broker 绑定回退 (忙碌中)' }}
                    </el-tag>
                  </div>
                  <div v-if="item.celeryInfo.method === 'broker-binding-fallback'" class="gpu-warning">
                    <el-icon><Warning /></el-icon>
                    <span>Worker 未响应 ping，可能正在执行长任务 (solo pool 会阻塞控制信号)</span>
                  </div>
                  <div v-if="!item.celeryInfo.active" class="gpu-warning">
                    <el-icon><Warning /></el-icon>
                    <span>异步任务无人消费，请执行 <code>./start_celery.sh</code> 启动 Worker</span>
                  </div>
                </div>
                
                <!-- Show LLM models list with status grouping -->
                <div v-if="item.key === 'llm_configs' && (item.activeReady || item.activePending || item.inactive)" class="detail-llm-list">
                  <el-divider style="margin: 12px 0;">
                    <span style="color: #909399; font-size: 12px;">模型详情</span>
                  </el-divider>
                  
                  <!-- Active - Ready -->
                  <div v-if="item.activeReady && item.activeReady.length > 0" class="model-group">
                    <div class="model-group-header model-group-ready">
                      <el-icon :size="16"><Check /></el-icon>
                      <span class="model-group-title">{{ $t('dashboard.llm_active_ready') }} ({{ item.activeReady.length }})</span>
                    </div>
                    <div v-for="model in item.activeReady" :key="model.id" class="model-item model-ready">
                      <div class="model-header">
                        <div class="model-title-row">
                          <span class="model-name">{{ model.name }}</span>
                          <el-tag 
                            :type="model.model_type === 'cloud' ? 'primary' : 'success'" 
                            size="small"
                            style="font-size:11px;padding:0 6px;height:18px;line-height:18px;"
                          >
                            {{ model.model_type === 'cloud' ? $t('llm.model_type_cloud') : $t('llm.model_type_local') }}
                          </el-tag>
                          <StatusBadge :status="model.health_status" />
                        </div>
                      </div>
                      <div class="model-health-metrics">
                        <span v-if="model.response_time_ms" class="metric-item">
                          <el-icon :size="12"><Timer /></el-icon>
                          {{ formatResponseTime(model.response_time_ms) }}
                        </span>
                        <span v-if="model.success_rate != null" class="metric-item">
                          <el-icon :size="12"><SuccessFilled /></el-icon>
                          {{ model.success_rate.toFixed(1) }}%
                        </span>
                        <span v-if="model.last_health_check" class="metric-item">
                          <el-icon :size="12"><Clock /></el-icon>
                          {{ formatLastCheck(model.last_health_check) }}
                        </span>
                      </div>
                    </div>
                  </div>
                  
                  <!-- Active - Pending -->
                  <div v-if="item.activePending && item.activePending.length > 0" class="model-group">
                    <div class="model-group-header model-group-pending">
                      <el-icon :size="16"><Warning /></el-icon>
                      <span class="model-group-title">{{ $t('dashboard.llm_active_pending') }} ({{ item.activePending.length }})</span>
                    </div>
                    <div v-for="model in item.activePending" :key="model.id" class="model-item model-pending">
                      <div class="model-header">
                        <div class="model-title-row">
                          <span class="model-name">{{ model.name }}</span>
                          <el-tag 
                            :type="model.model_type === 'cloud' ? 'primary' : 'success'" 
                            size="small"
                            style="font-size:11px;padding:0 6px;height:18px;line-height:18px;"
                          >
                            {{ model.model_type === 'cloud' ? $t('llm.model_type_cloud') : $t('llm.model_type_local') }}
                          </el-tag>
                          <el-tag type="warning" size="small">未配置</el-tag>
                        </div>
                      </div>
                      <div class="model-warning">
                        <el-icon :size="14"><Warning /></el-icon>
                        <span>{{ $t('dashboard.llm_need_api_key') }}</span>
                      </div>
                    </div>
                  </div>
                  
                  <!-- Inactive -->
                  <div v-if="item.inactive && item.inactive.length > 0" class="model-group">
                    <div class="model-group-header model-group-inactive">
                      <el-icon :size="16"><CircleClose /></el-icon>
                      <span class="model-group-title">{{ $t('dashboard.llm_inactive') }} ({{ item.inactive.length }})</span>
                    </div>
                    <div v-for="model in item.inactive" :key="model.id" class="model-item model-inactive">
                      <div class="model-header">
                        <div class="model-title-row">
                          <span class="model-name">{{ model.name }}</span>
                          <el-tag 
                            :type="model.model_type === 'cloud' ? 'primary' : 'success'" 
                            size="small"
                            style="font-size:11px;padding:0 6px;height:18px;line-height:18px;"
                          >
                            {{ model.model_type === 'cloud' ? $t('llm.model_type_cloud') : $t('llm.model_type_local') }}
                          </el-tag>
                          <el-tag type="info" size="small">已禁用</el-tag>
                        </div>
                      </div>
                      <div class="model-inactive-hint">
                        <el-icon :size="14"><InfoFilled /></el-icon>
                        <span>{{ $t('dashboard.llm_channel_disabled') }}</span>
                      </div>
                    </div>
                  </div>
                </div>
                
                <div v-if="item.status === 'warning' || item.status === 'error'" class="detail-row detail-alert" :class="'detail-' + item.statusType">
                  <span class="detail-label">
                    {{ item.status === 'warning' ? $t('dashboard.health_warning_info') : $t('dashboard.health_error_info') }}:
                  </span>
                  <span class="detail-value">{{ item.detailMessage }}</span>
                </div>
                
                <div v-if="item.impact" class="detail-row detail-impact">
                  <span class="detail-label">{{ $t('dashboard.health_impact') }}:</span>
                  <span class="detail-value">{{ item.impact }}</span>
                </div>
                </div>
              </div>
            </div>
          </el-popover>
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import request from '@/api/request'
import { getSystemHealth } from '@/api/system'
import { logger } from '../utils/logger'
import StatusBadge from '../components/common/StatusBadge.vue'
import { 
  Check, Warning, CircleClose, Refresh, 
  Monitor, Connection, FolderOpened, Cpu, 
  Coin, Document, Files, Timer, Clock, SuccessFilled, InfoFilled, Download
} from '@element-plus/icons-vue'

const { t } = useI18n()

const stats = ref({
  llm_count: 0,
  active_llm_count: 0,
  ip_count: 0,
  task_count: 0,
  lora_count: 0,
})

// Health check data
const healthLoading = ref(false)
const healthData = ref(null)

// Computed properties for health display
const healthTitle = computed(() => {
  if (!healthData.value) return t('dashboard.checking_health')
  const status = healthData.value.overall_status
  return t(`dashboard.health_${status}`)
})

const healthAlertType = computed(() => {
  if (!healthData.value) return 'info'
  const status = healthData.value.overall_status
  const typeMap = {
    'healthy': 'success',
    'warning': 'warning',
    'error': 'error'
  }
  return typeMap[status] || 'info'
})

const healthDescription = computed(() => {
  if (!healthData.value) return t('dashboard.health_check_loading')
  const summary = healthData.value.summary
  return t('dashboard.health_summary_text', {
    total: summary.total_checks,
    healthy: summary.healthy,
    warnings: summary.warnings,
    errors: summary.errors
  })
})

// Error and warning counts for header display
const errorCount = computed(() => {
  return healthData.value?.summary?.errors || 0
})

const warningCount = computed(() => {
  return healthData.value?.summary?.warnings || 0
})

const healthItems = computed(() => {
  if (!healthData.value || !healthData.value.checks) return []
  
  const checks = healthData.value.checks
  const statusConfig = {
    'ok': { type: 'success', icon: Check, color: '#67C23A' },
    'healthy': { type: 'success', icon: Check, color: '#67C23A' },
    'warning': { type: 'warning', icon: Warning, color: '#E6A23C' },
    'error': { type: 'danger', icon: CircleClose, color: '#F56C6C' },
    'info': { type: 'info', icon: Monitor, color: '#909399' }
  }
  
  // Check descriptions for each item
  const checkDescriptions = {
    'redis': '检查Redis数据库连接状态',
    'database': '检查主数据库连接和可访问性',
    'llm_configs': '检查LLM模型配置和API密钥',
    'directories': '检查必需的目录结构是否存在',
    'disk_space': '检查磁盘剩余空间是否充足',
    'gpu': '检查GPU可用性和显存大小',
    'celery_worker': '检查Celery异步任务Worker状态',
    'diffusion_models': '检查扩散模型文件是否存在',
    'training_mode': '检查LoRA训练模式配置'
  }
  
  const itemConfig = [
    { key: 'redis', name: t('dashboard.health_redis'), icon: Connection },
    { key: 'database', name: t('dashboard.health_database'), icon: Files },
    { key: 'llm_configs', name: t('dashboard.health_llm'), icon: Document },
    { key: 'directories', name: t('dashboard.health_directories'), icon: FolderOpened },
    { key: 'disk_space', name: t('dashboard.health_disk'), icon: Monitor },
    { key: 'gpu', name: t('dashboard.health_gpu'), icon: Cpu },
    { key: 'celery_worker', name: t('dashboard.health_celery'), icon: Connection },
    { key: 'diffusion_models', name: t('dashboard.health_models'), icon: Coin },
    { key: 'training_mode', name: t('dashboard.health_training'), icon: Monitor }
  ]
  
  return itemConfig.map(config => {
    const check = checks[config.key] || {}
    const status = check.status || 'info'
    const cfg = statusConfig[status] || statusConfig['info']
    
    // Short message for card display (truncate if too long)
    const shortMessage = check.message || ''
    const displayShort = shortMessage.length > 30 ? shortMessage.substring(0, 30) + '...' : shortMessage
    
    return {
      key: config.key,
      name: config.name,
      icon: config.icon,
      status,
      statusText: t(`dashboard.status_${status}`),
      statusType: cfg.type,
      color: cfg.color,
      message: check.message || '',
      shortMessage: displayShort,
      checkDescription: checkDescriptions[config.key] || '',
      detailMessage: check.message || '',
      url: check.url || null,
      modelsPath: check.models_path || null,
      impact: check.impact || null,
      modelDetails: config.key === 'diffusion_models' ? check : null,
      requiredModels: config.key === 'diffusion_models' ? Object.values(check.required_models || {}) : null,
      
      // Directory list with detailed information
      directoryList: config.key === 'directories' ? (check.directories || check.existing || []) : null,
      
      // GPU detailed information
      gpuInfo: config.key === 'gpu' ? {
        available: check.available,
        name: check.name,
        count: check.count,
        memory_gb: check.memory_gb
      } : null,

      // Celery worker detailed information
      celeryInfo: config.key === 'celery_worker' ? {
        active: check.active,
        workers: check.workers || [],
        method: check.method || null
      } : null,
      
      // LLM models grouped by status
      activeReady: config.key === 'llm_configs' ? check.active_ready : null,
      activePending: config.key === 'llm_configs' ? check.active_pending : null,
      inactive: config.key === 'llm_configs' ? check.inactive : null
    }
  })
})

const issues = computed(() => {
  if (!healthData.value || !healthData.value.checks) return []
  
  const checks = healthData.value.checks
  const issuesList = []
  
  Object.entries(checks).forEach(([key, check]) => {
    if (check.status === 'error' || check.status === 'warning') {
      issuesList.push({
        title: t(`dashboard.health_${key}`),
        description: check.impact || check.message,
        type: check.status === 'error' ? 'error' : 'warning'
      })
    }
  })
  
  return issuesList
})

async function loadHealth() {
  healthLoading.value = true
  try {
    const { data } = await getSystemHealth()
    healthData.value = data.data
  } catch (err) {
    logger.error('Failed to load health data:', err)
    ElMessage.error(t('dashboard.health_check_failed'))
  } finally {
    healthLoading.value = false
  }
}

// Download tracking state
const downloadingModels = ref([])  // List of model repos being downloaded
const activeDownloads = ref([])    // Active download progress
const downloadPollingIntervals = ref({})  // Polling intervals per task

// Poll download progress
async function pollDownloadStatus(taskId, modelRepo) {
  const pollInterval = setInterval(async () => {
    try {
      const { data } = await request.get(`/system/models/download/${taskId}/status`)
      const downloadData = data.data
      
      // Update progress
      const downloadIndex = activeDownloads.value.findIndex(d => d.taskId === taskId)
      if (downloadIndex >= 0) {
        const existing = activeDownloads.value[downloadIndex]
        activeDownloads.value[downloadIndex] = {
          ...existing,
          // ✅ 修复：只在后端有值时才更新，保留前端初始值
          progress: downloadData.progress !== undefined ? Math.round(downloadData.progress) : existing.progress,
          downloadedMB: downloadData.downloaded_mb !== undefined ? Math.round(downloadData.downloaded_mb) : existing.downloadedMB,
          totalMB: existing.totalMB,  // ✅ 保持初始值，不被后端覆盖
          speed: downloadData.speed_mbps !== undefined ? downloadData.speed_mbps.toFixed(1) : existing.speed,
          eta: downloadData.eta_seconds !== undefined ? Math.round(downloadData.eta_seconds) : existing.eta,
          statusMsg: downloadData.status_msg || existing.statusMsg || ''
        }
      }
      
      // Check if completed
      if (downloadData.status === 'completed' || downloadData.status === 'failed') {
        clearInterval(pollInterval)
        delete downloadPollingIntervals.value[taskId]
        
        // ✅ 修复：使用 modelId 而不是 model.modelId（model未定义）
        downloadingModels.value = downloadingModels.value.filter(id => id !== activeDownloads.value[downloadIndex]?.modelId)
        activeDownloads.value = activeDownloads.value.filter(d => d.taskId !== taskId)
        
        // Refresh health check to show new status
        if (downloadData.status === 'completed') {
          ElMessage.success(t('dashboard.download_completed'))
          await loadHealth()
        } else {
          ElMessage.error(t('dashboard.download_failed', { error: downloadData.error }))
        }
      }
    } catch (err) {
      logger.error('Failed to poll download status:', err)
    }
  }, 2000)  // Poll every 2 seconds
  
  downloadPollingIntervals.value[taskId] = pollInterval
}

// Start model download
async function downloadModel(model) {
  try {
    // Start async download
    const { data } = await request.post('/system/models/download', {
      model_id: model.model_id || model.repo,  // 优先用 model_id，fallback 用 repo
      mirror: 'modelscope'  // Use China mirror by default
    })
    
    const taskId = data.data.task_id
    
    // Add to downloading list
    downloadingModels.value.push(model.model_id)
    activeDownloads.value.push({
      taskId,
      modelId: model.model_id,
      modelName: model.name,
      progress: 0,
      downloadedMB: 0,
      totalMB: Math.round(model.size_gb * 1024),
      speed: null,
      eta: null
    })
    
    ElMessage.info(t('dashboard.download_started', { name: model.name }))
    
    // Start polling for progress
    pollDownloadStatus(taskId, model.repo)
    
  } catch (err) {
    const errorMsg = err.response?.data?.data?.error || err.response?.data?.error || err.message
    ElMessage.error(t('dashboard.download_start_failed', { error: errorMsg }))
  }
}

function openModelDownload(model) {
  // Open model download link in new tab
  window.open(model.download_url, '_blank')
}

// Helper function to get status tag type
function getModelStatusType(status) {
  const typeMap = {
    'installed': 'success',
    'downloading': 'warning',
    'incomplete': 'danger',
    'missing': 'info'
  }
  return typeMap[status] || 'info'
}

// Helper function to get status text
function getModelStatusText(status) {
  const textMap = {
    'installed': t('dashboard.model_installed'),
    'downloading': '下载中',
    'incomplete': '不完整',
    'missing': t('dashboard.model_missing')
  }
  return textMap[status] || status
}

onMounted(async () => {
  // Load dashboard stats
  try {
    const { data } = await request.get('/dashboard/stats')
    // Unified response format: { success: true, data: {...} }
    const statsData = data.data || {}
    stats.value.llm_count = statsData.llm_count || 0
    stats.value.active_llm_count = statsData.active_llm_count || 0
    stats.value.ip_count = statsData.ip_count || 0
    stats.value.task_count = statsData.task_count || 0
    stats.value.lora_count = statsData.lora_count || 0
  } catch (err) {
    logger.error('Failed to load dashboard stats:', err)
  }
  
  // Load detailed health check
  await loadHealth()
})

onUnmounted(() => {
  // Clean up all download polling intervals to prevent memory leaks
  Object.values(downloadPollingIntervals.value).forEach(interval => {
    clearInterval(interval)
  })
  downloadPollingIntervals.value = {}
})

function formatResponseTime(ms) {
  if (ms == null || ms < 0) return '-'
  if (ms < 1000) return `${Math.round(ms)}ms`
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
  return `${Math.floor(ms / 60000)}m${Math.round((ms % 60000) / 1000)}s`
}

function formatLastCheck(isoTime) {
  if (!isoTime) return '-'
  const date = new Date(isoTime)
  const now = new Date()
  const diffMs = now - date
  
  if (diffMs < 60000) return '刚刚'
  if (diffMs < 3600000) return `${Math.floor(diffMs / 60000)}分钟前`
  if (diffMs < 86400000) return `${Math.floor(diffMs / 3600000)}小时前`
  return date.toLocaleDateString('zh-CN')
}
</script>

<style scoped>
.dashboard {
  padding: 0;
}
.page-title {
  font-size: 24px;
  font-weight: 700;
  color: #303133;
  margin: 0 0 16px;
}
.stat-card {
  border-radius: 12px;
}
.stat-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.stat-info {
  flex: 1;
}
.stat-label {
  font-size: 14px;
  color: #909399;
  margin: 0;
}
.stat-value {
  font-size: 32px;
  font-weight: 700;
  margin: 4px 0;
}
.stat-sub {
  font-size: 12px;
  color: #909399;
  margin: 0;
}
.stat-icon {
  opacity: 0.2;
}
.stat-blue .stat-value { color: #409eff; }
.stat-blue .stat-icon { color: #409eff; }
.stat-green .stat-value { color: #67c23a; }
.stat-green .stat-icon { color: #67c23a; }
.stat-orange .stat-value { color: #e6a23c; }
.stat-orange .stat-icon { color: #e6a23c; }
.stat-purple .stat-value { color: #9b59b6; }
.stat-purple .stat-icon { color: #9b59b6; }
.action-btn {
  width: 100%;
  height: 60px;
  font-size: 15px;
}

/* Model Details Popover Styles */
.health-detail {
  padding: 8px 0;
}

.health-detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

/* Scrollable content area */
.health-detail-scrollable {
  max-height: 400px;
  overflow-y: auto;
  overflow-x: hidden;
  padding-right: 8px;
}

/* Custom scrollbar styling */
.health-detail-scrollable::-webkit-scrollbar {
  width: 6px;
}

.health-detail-scrollable::-webkit-scrollbar-track {
  background: #f5f7fa;
  border-radius: 3px;
}

.health-detail-scrollable::-webkit-scrollbar-thumb {
  background: #c0c4cc;
  border-radius: 3px;
  transition: background 0.3s;
}

.health-detail-scrollable::-webkit-scrollbar-thumb:hover {
  background: #909399;
}

.health-detail-content {
  font-size: 13px;
}

.detail-row {
  margin-bottom: 12px;
  line-height: 1.6;
}

.detail-row:last-child {
  margin-bottom: 0;
}

.detail-label {
  font-weight: 600;
  color: #606266;
  display: block;
  margin-bottom: 4px;
}

.detail-value {
  color: #303133;
  display: block;
}

.detail-alert {
  padding: 10px;
  border-radius: 6px;
  margin: 12px 0;
}

.detail-danger {
  background: #fef0f0;
  border-left: 3px solid #f56c6c;
}

.detail-danger .detail-label,
.detail-danger .detail-value {
  color: #f56c6c;
}

.detail-warning {
  background: #fdf6ec;
  border-left: 3px solid #e6a23c;
}

.detail-warning .detail-label,
.detail-warning .detail-value {
  color: #e6a23c;
}

.detail-impact {
  padding: 10px;
  background: #f5f7fa;
  border-radius: 6px;
  border-left: 3px solid #909399;
}

/* Directory list styles */
.detail-directory-list {
  margin-top: 12px;
}

.directory-item {
  padding: 12px;
  background: #f5f7fa;
  border-radius: 8px;
  margin-bottom: 10px;
  border-left: 3px solid #409eff;
}

.directory-item:last-child {
  margin-bottom: 0;
}

.directory-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.directory-name {
  font-weight: 600;
  font-size: 13px;
  color: #303133;
  flex: 1;
}

.directory-path {
  font-size: 12px;
  color: #606266;
  font-family: 'Courier New', monospace;
  background: #ffffff;
  padding: 4px 8px;
  border-radius: 4px;
  margin-bottom: 6px;
  word-break: break-all;
}

.directory-desc {
  font-size: 12px;
  color: #909399;
  line-height: 1.5;
}

/* GPU info styles */
.detail-gpu-info {
  margin-top: 12px;
}

.gpu-info-row {
  display: flex;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid #f0f0f0;
}

.gpu-info-row:last-child {
  border-bottom: none;
}

.gpu-label {
  font-weight: 600;
  color: #606266;
  min-width: 80px;
  font-size: 13px;
}

.gpu-value {
  color: #303133;
  flex: 1;
  font-size: 13px;
}

.gpu-warning {
  margin-top: 12px;
  padding: 10px;
  background: #fdf6ec;
  border-radius: 6px;
  border-left: 3px solid #e6a23c;
  display: flex;
  align-items: center;
  gap: 8px;
  color: #e6a23c;
  font-size: 12px;
  line-height: 1.5;
}

.model-details {
  padding: 8px 0;
}

.model-item {
  padding: 12px;
  background: #f5f7fa;
  border-radius: 8px;
  margin-bottom: 12px;
}

.model-item:last-of-type {
  margin-bottom: 0;
}

.model-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.model-name {
  font-weight: 600;
  font-size: 14px;
  color: #303133;
}

.model-info {
  font-size: 12px;
  color: #606266;
  line-height: 1.8;
  margin-bottom: 8px;
}

.model-actions {
  display: flex;
  gap: 8px;
}

.summary-info {
  font-size: 13px;
  color: #606266;
  line-height: 1.6;
}

/* Health status tags in header */
:deep(.el-tag--small) {
  font-size: 12px;
  padding: 2px 8px;
}

:deep(.el-tag--plain) {
  background-color: transparent;
}

/* Connection URL style */
.detail-url {
  font-family: 'Courier New', monospace;
  font-size: 12px;
  color: #409eff;
  word-break: break-all;
  background: #f5f7fa;
  padding: 6px 8px;
  border-radius: 4px;
  display: inline-block;
  margin-top: 4px;
}

/* Storage Path style (same as URL) */
.detail-path {
  font-family: 'Courier New', monospace;
  font-size: 12px;
  color: #409eff;
  word-break: break-all;
  background: #f5f7fa;
  padding: 6px 8px;
  border-radius: 4px;
  display: inline-block;
  margin-top: 4px;
}

/* LLM model list styles */
.detail-llm-list {
  margin-top: 12px;
}

.model-group {
  margin-bottom: 16px;
}

.model-group:last-child {
  margin-bottom: 0;
}

/* Group headers with different colors */
.model-group-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  color: white;
  border-radius: 8px 8px 0 0;
  font-weight: 600;
  font-size: 13px;
}

.model-group-ready .model-group-header {
  background: linear-gradient(135deg, #67c23a 0%, #85ce61 100%);
}

.model-group-pending .model-group-header {
  background: linear-gradient(135deg, #e6a23c 0%, #ebb563 100%);
}

.model-group-inactive .model-group-header {
  background: linear-gradient(135deg, #909399 0%, #a6a9ad 100%);
}

.model-group-title {
  flex: 1;
}

/* Model item cards */
.model-item {
  padding: 12px;
  background: #f5f7fa;
  border-radius: 0 0 8px 8px;
  margin-bottom: 10px;
  transition: all 0.3s;
}

.model-ready {
  border-left: 3px solid #67c23a;
}

.model-ready:hover {
  background: #f0f9ff;
  box-shadow: 0 2px 8px rgba(103, 194, 58, 0.15);
}

.model-pending {
  border-left: 3px solid #e6a23c;
  background: #fdf6ec;
}

.model-pending:hover {
  background: #faecd8;
  box-shadow: 0 2px 8px rgba(230, 162, 60, 0.15);
}

.model-inactive {
  border-left: 3px solid #909399;
  background: #f4f4f5;
  opacity: 0.7;
}

.model-item:last-child {
  margin-bottom: 0;
}

.model-header {
  margin-bottom: 8px;
}

.model-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.model-name {
  font-weight: 600;
  font-size: 14px;
  color: #303133;
  flex: 1;
}

/* Health metrics row */
.model-health-metrics {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  font-size: 12px;
  color: #606266;
}

.metric-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.metric-item .el-icon {
  color: #909399;
}

/* Warning and info hints */
.model-warning,
.model-inactive-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  padding: 6px 8px;
  border-radius: 4px;
  margin-top: 8px;
}

.model-warning {
  color: #e6a23c;
  background: rgba(230, 162, 60, 0.1);
}

.model-inactive-hint {
  color: #909399;
  background: rgba(144, 147, 153, 0.1);
}

/* Diffusion model download styles */
.detail-diffusion-models {
  margin-top: 12px;
}

.model-download-item {
  padding: 12px;
  background: #f5f7fa;
  border-radius: 8px;
  margin-bottom: 10px;
  border-left: 3px solid #409eff;
}

.model-download-item:last-child {
  margin-bottom: 0;
}

.model-info-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.model-download-item .model-name {
  font-weight: 600;
  font-size: 13px;
  color: #303133;
}

.model-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12px;
  color: #606266;
  margin-bottom: 8px;
}

.model-purpose {
  flex: 1;
}

.model-size {
  font-weight: 500;
  color: #909399;
}

/* Model integrity warning */
.model-integrity-warning {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 10px;
  background: #fdf6ec;
  border-radius: 6px;
  margin-bottom: 8px;
  font-size: 12px;
}

.integrity-text {
  color: #e6a23c;
  font-weight: 500;
}

/* Model downloading indicator */
.model-downloading-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #ecf5ff;
  border-radius: 6px;
  color: #409eff;
  font-size: 13px;
  font-weight: 500;
}

/* Download progress styles */
.download-progress-section {
  margin-top: 12px;
}

.download-progress-item {
  padding: 12px;
  background: #ecf5ff;
  border-radius: 8px;
  margin-bottom: 10px;
  border-left: 3px solid #409eff;
}

.download-progress-item:last-child {
  margin-bottom: 0;
}

.download-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.download-model-name {
  font-weight: 600;
  font-size: 13px;
  color: #303133;
}

.download-percentage {
  font-weight: 600;
  font-size: 14px;
  color: #409eff;
}

.download-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 12px;
  color: #606266;
  margin-top: 6px;
  flex-wrap: wrap;
}

.download-status-msg {
  color: #409eff;
  font-weight: 500;
  font-style: italic;
}
</style>
