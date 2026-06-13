<template>
  <div class="quick-generate">
    <div class="workflow-toolbar">
      <div class="toolbar-left">
        <el-select v-model="selectedIPId" :placeholder="$t('workflow.select_ip_placeholder')" size="default" style="width: 180px" @change="onIPChange">
          <el-option v-for="ip in ipAssets" :key="ip.id" :label="ip.name" :value="ip.id" />
        </el-select>
        <el-select v-model="selectedTemplateKey" :placeholder="$t('workflow.template_select')" size="default" style="width: 200px" @change="onTemplateChange">
          <el-option v-for="tpl in templates" :key="tpl.metadata?.template_key" :label="tpl.name" :value="tpl.metadata?.template_key">
            <el-icon style="margin-right:4px"><component :is="templateIcon(tpl.metadata?.template_key)" /></el-icon>
            {{ tpl.name }}
          </el-option>
        </el-select>
        <el-select v-if="currentContentType === 'image' && selectedTemplateKey === 'three_view'" v-model="viewType" size="default" style="width:120px">
          <el-option label="Front" value="front" /><el-option label="Side" value="side" /><el-option label="Back" value="back" />
        </el-select>
      </div>
      <div class="toolbar-right">
        <el-button type="primary" @click="handleQuickExecute" :loading="quickExecuting" :disabled="!canQuickExecute" size="default">
          <el-icon><VideoPlay /></el-icon> {{ $t('workflow.execute') }}
        </el-button>
      </div>
    </div>

    <div v-if="!selectedIPId && ipAssets.length === 0" class="empty-state">
      <el-empty :description="$t('workflow.no_ip_assets')">
        <el-button type="primary" @click="$router.push('/ip')">{{ $t('ip.create_asset') }}</el-button>
      </el-empty>
    </div>

    <div v-else-if="!selectedIPId && ipAssets.length > 0" class="empty-state">
      <el-empty :description="$t('workflow.no_ip_hint')" />
    </div>

    <div v-else class="workflow-content">
      <div class="param-panel">
        <h4 class="panel-title">{{ $t('workflow.parameters') }}</h4>
        <el-descriptions :column="1" size="small" border style="margin-bottom:16px">
          <el-descriptions-item :label="$t('workflow.template_label')">{{ currentTemplate?.name || '-' }}</el-descriptions-item>
          <el-descriptions-item :label="$t('workflow.content_type')">
            <el-tag size="small" :type="contentTypeTagType">{{ contentTypeLabel }}</el-tag>
          </el-descriptions-item>
        </el-descriptions>

        <template v-if="selectedTemplateKey === 'three_view'">
          <h5 class="section-label">{{ $t('workflow.ref_image') }}</h5>
          <div v-if="refImages.length > 0" class="ref-gallery">
            <div v-for="(ref, idx) in refImages" :key="idx" class="ref-item" :class="{selected: selectedRefIdx === idx}" @click="selectedRefIdx = idx">
              <el-image :src="getRefImageUrl(ref)" fit="contain" class="ref-img" />
              <span class="ref-angle">{{ ref.angle || 'img' }}</span>
            </div>
          </div>
          <el-alert v-else type="warning" :closable="false" style="margin-bottom:12px">{{ $t('workflow.no_ref_images') }}</el-alert>
          <el-image v-if="selectedRef" :src="getRefImageUrl(selectedRef)" fit="contain" style="max-height:180px;max-width:100%;border-radius:6px;margin-bottom:12px" />
        </template>

        <h5 class="section-label">{{ $t('workflow.node_params') }}</h5>
        <el-form label-position="top" size="small">
          <el-form-item v-for="param in visibleParams" :key="param.name" :label="paramLabel(param.name)">
            <el-input v-if="param.fieldType==='textarea'" v-model="nodeParams[param.name]" type="textarea" :rows="3" :placeholder="paramPlaceholder(param.name)" />
            <el-input-number v-else-if="param.fieldType==='number'" v-model="nodeParams[param.name]" :min="param.min" :max="param.max" :step="param.step||1" style="width:100%" />
            <el-slider v-else-if="param.fieldType==='slider'" v-model="nodeParams[param.name]" :min="param.min" :max="param.max" :step="param.step||0.1" show-input />
            <el-select v-else-if="param.fieldType==='select'" v-model="nodeParams[param.name]" style="width:100%">
              <el-option v-for="opt in param.options" :key="opt.value" :label="opt.label" :value="opt.value" />
            </el-select>
            <el-input v-else v-model="nodeParams[param.name]" />
          </el-form-item>
        </el-form>
      </div>

      <div class="result-panel">
        <h4 class="panel-title">{{ $t('workflow.results') }}</h4>
        <el-empty v-if="!lastTaskId && !isTaskPolling" :description="$t('workflow.no_results')" />

        <!-- Polling / Running -->
        <div v-if="isTaskPolling" class="executing-state">
          <el-progress :percentage="taskProgress" :status="progressStatus" :stroke-width="12" style="width:80%;max-width:300px" />
          <p>{{ statusText }}</p>
          <p style="font-size:12px;color:#909399;margin-top:4px">Task: {{ currentTaskId }}</p>
        </div>

        <!-- Failed -->
        <div v-if="isTaskFailed" class="failed-state">
          <el-result icon="error" :title="$t('workflow.task_failed')" :sub-title="taskErrorMessage">
            <template #extra>
              <el-button size="small" @click="$router.push('/tasks')"><el-icon><List /></el-icon>{{ $t('workflow.view_tasks') }}</el-button>
            </template>
          </el-result>
        </div>

        <!-- Inline Result -->
        <div v-if="hasTaskResult" class="inline-result">
          <!-- Image thumbnails -->
          <div v-if="imageThumbs.length > 0" class="thumb-grid">
            <div v-for="(img, idx) in imageThumbs" :key="idx" class="thumb-item">
              <el-image :src="getFileUrl(img.thumbnail_path || img.file_path)" fit="cover" class="thumb-img" />
            </div>
          </div>
          <!-- Story summary -->
          <div v-if="storySummary" class="story-summary">
            <el-icon color="#67c23a"><Document /></el-icon>
            <span class="summary-title">{{ storySummary.title }}</span>
            <p class="summary-text">{{ (storySummary.description || '').slice(0, 200) }}{{ (storySummary.description || '').length > 200 ? '...' : '' }}</p>
          </div>
          <!-- Video summary -->
          <div v-if="videoSummary" class="video-summary">
            <el-icon color="#e6a23c"><VideoCameraFilled /></el-icon>
            <span class="summary-title">{{ videoSummary.title }}</span>
            <video v-if="videoSummary.file_path" :src="getFileUrl(videoSummary.file_path)" controls class="inline-video" />
          </div>
          <!-- Action buttons -->
          <div class="result-actions">
            <el-button type="primary" size="small" @click="openResultDialog(currentTaskId)"><el-icon><View /></el-icon>{{ $t('workflow.view_full_result') }}</el-button>
            <el-button size="small" @click="$router.push('/tasks')"><el-icon><List /></el-icon>{{ $t('workflow.view_tasks') }}</el-button>
            <el-button size="small" @click="$router.push('/contents')"><el-icon><Files /></el-icon>{{ $t('workflow.view_contents') }}</el-button>
          </div>
        </div>

        <!-- Task History -->
        <div v-if="taskHistory.length > 0" class="task-history">
          <el-divider content-position="left" style="margin:16px 0 8px">History</el-divider>
          <div v-for="(item, idx) in taskHistory" :key="idx" class="history-item" @click="viewHistoryResult(item)">
            <el-icon :color="item.status === 'completed' ? '#67c23a' : '#f56c6c'">
              <CircleCheck v-if="item.status === 'completed'" />
              <CircleClose v-else />
            </el-icon>
            <span class="history-id">{{ item.taskId.slice(0, 8) }}...</span>
            <el-tag size="small" :type="item.status === 'completed' ? 'success' : 'danger'">{{ item.status }}</el-tag>
          </div>
        </div>

        <!-- TaskResultDialog -->
        <TaskResultDialog v-model="showResultDialog" :task-id="activeResultTaskId" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useI18n } from 'vue-i18n'
import {
  PictureFilled, VideoCameraFilled, Document, Connection,
  VideoPlay, CircleCheck, CircleClose, Loading, List, Files, View,
} from '@element-plus/icons-vue'
import { getWorkflowTemplates, executeWorkflow } from '../../api/workflow'
import { useTaskResult } from '../../composables/useTaskResult'
import TaskResultDialog from '../TaskResultDialog.vue'

const props = defineProps({
  ipAssets: { type: Array, default: () => [] },
})

const router = useRouter()
const { t } = useI18n()

// ================ STATE ================
const selectedIPId = ref(null)
const templates = ref([])
const selectedTemplateKey = ref('three_view')
const viewType = ref('front')
const quickExecuting = ref(false)
const lastTaskId = ref('')
const refImages = ref([])
const selectedRefIdx = ref(0)
const nodeParams = ref({})
const showResultDialog = ref(false)
const taskHistory = ref([])
const currentTaskId = ref('')

// Task result polling
const { taskStatus, taskProgress, resultContents, isPolling: isTaskPolling, hasResult: hasTaskResult, errorMessage: taskErrorMessage, startPolling, stopPolling } = useTaskResult()
const isTaskFailed = computed(() => taskStatus.value === 'failed' && !isTaskPolling.value)
const progressStatus = computed(() => taskStatus.value === 'completed' ? 'success' : taskStatus.value === 'failed' ? 'exception' : '')
const statusText = computed(() => {
  if (taskStatus.value === 'pending') return t('workflow.task_running') + '...'
  if (taskStatus.value === 'running') return t('workflow.task_running') + '...'
  if (taskStatus.value === 'completed') return t('workflow.task_completed')
  return t('workflow.generating')
})
const imageThumbs = computed(() => resultContents.value.filter(c => c.content_type === 'image').slice(0, 6))
const storySummary = computed(() => resultContents.value.find(c => c.content_type === 'story'))
const videoSummary = computed(() => resultContents.value.find(c => c.content_type === 'video'))
const activeResultTaskId = ref('')

function getFileUrl(filePath) {
  if (!filePath) return ''
  return `/api/v1/contents/files/${filePath.replace(/\\/g, '/')}`
}
function openResultDialog(taskId) {
  activeResultTaskId.value = taskId
  showResultDialog.value = true
}
function viewHistoryResult(item) {
  openResultDialog(item.taskId)
}

// ================ COMPUTED ================
const currentTemplate = computed(() =>
  templates.value.find(tpl => tpl.metadata?.template_key === selectedTemplateKey.value) || null
)
const currentContentType = computed(() => currentTemplate.value?.metadata?.content_type || '')
const contentTypeLabel = computed(() => ({ image: 'Image', video: 'Video', story: 'Story' })[currentContentType.value] || currentContentType.value)
const contentTypeTagType = computed(() => ({ image: 'danger', video: 'warning', story: '' })[currentContentType.value] || 'info')
const selectedRef = computed(() => refImages.value.length === 0 ? null : (refImages.value[selectedRefIdx.value] || refImages.value[0] || null))
const canQuickExecute = computed(() => {
  if (!selectedIPId.value || !currentTemplate.value) return false
  if (selectedTemplateKey.value === 'three_view' && !selectedRef.value) return false
  return true
})

// ================ PARAM DEFS ================
const PARAM_DEFS = {
  three_view: [],
  story: [
    { name: 'prompt', fieldType: 'textarea' },
    { name: 'style', fieldType: 'select', options: [
      { label: 'Healing', value: 'healing' }, { label: 'Comedy', value: 'comedy' },
      { label: 'Adventure', value: 'adventure' }, { label: 'Romance', value: 'romance' },
      { label: 'Slice of Life', value: 'slice_of_life' },
    ]},
    { name: 'temperature', fieldType: 'slider', min: 0, max: 2, step: 0.1 },
    { name: 'max_tokens', fieldType: 'number', min: 100, max: 4096, step: 100 },
  ],
  cloud_image: [
    { name: 'prompt', fieldType: 'textarea' }, { name: 'negative_prompt', fieldType: 'textarea' },
    { name: 'width', fieldType: 'number', min: 256, max: 2048, step: 64 },
    { name: 'height', fieldType: 'number', min: 256, max: 2048, step: 64 },
  ],
  cloud_video: [
    { name: 'prompt', fieldType: 'textarea' },
    { name: 'duration_seconds', fieldType: 'number', min: 2, max: 15 },
    { name: 'fps', fieldType: 'number', min: 4, max: 30 },
    { name: 'width', fieldType: 'number', min: 256, max: 1024, step: 64 },
    { name: 'height', fieldType: 'number', min: 256, max: 1024, step: 64 },
  ],
}
const HIDDEN_PARAMS = new Set(['channel_id', 'ip_asset_id', 'view_type', 'image_path', 'ip_name'])

const visibleParams = computed(() => {
  const defs = PARAM_DEFS[selectedTemplateKey.value] || []
  if (defs.length > 0) return defs
  if (!currentTemplate.value) return []
  const nodes = currentTemplate.value.nodes || []
  if (nodes.length === 0) return []
  const params = nodes[0].parameters || {}
  return Object.entries(params).filter(([name]) => !HIDDEN_PARAMS.has(name))
    .map(([name, val]) => ({ name, fieldType: typeof val === 'number' ? 'number' : (name.includes('prompt') ? 'textarea' : 'text'), min: 0, max: name.includes('width') || name.includes('height') ? 2048 : 9999, step: 1 }))
})

// ================ HELPERS ================
function templateIcon(key) {
  return ({ three_view: PictureFilled, story: Document, cloud_image: PictureFilled, cloud_video: VideoCameraFilled })[key] || Connection
}
function paramLabel(name) {
  const m = { prompt: t('workflow.param_prompt'), negative_prompt: t('workflow.param_negative_prompt'), width: t('workflow.param_width'), height: t('workflow.param_height'), style: t('workflow.param_style'), temperature: t('workflow.param_temperature'), max_tokens: t('workflow.param_max_tokens'), duration_seconds: t('workflow.param_duration'), fps: t('workflow.param_fps') }
  return m[name] || name
}
function paramPlaceholder(name) {
  if (name === 'prompt') return t('workflow.prompt_placeholder') || 'Describe what to generate...'
  if (name === 'negative_prompt') return t('workflow.negative_prompt_placeholder') || 'What to exclude...'
  return ''
}
function getRefImageUrl(ref) {
  let imgPath = typeof ref === 'string' ? ref : (ref.path || ref.url || '')
  if (!imgPath || imgPath === '/placeholder.jpg') return ''
  const np = imgPath.replace(/\\/g, '/')
  if (np.startsWith('data/resources/')) return `/api/v1/resources/${encodeURIComponent(np)}`
  let cleanPath = np.startsWith('/') ? np.substring(1) : np
  const parts = cleanPath.split('/').filter(p => p.length > 0)
  if (parts.length >= 2) return `/api/v1/generate/files/${parts[parts.length - 2]}/${parts[parts.length - 1]}`
  if (parts.length === 1) return `/api/v1/generate/files/${parts[0]}`
  return ''
}

// ================ LOGIC ================
function initNodeParams() {
  const tpl = currentTemplate.value
  if (!tpl?.nodes?.length) { nodeParams.value = {}; return }
  const params = tpl.nodes[0].parameters || {}
  const filtered = {}
  for (const [key, val] of Object.entries(params)) { if (!HIDDEN_PARAMS.has(key)) filtered[key] = val }
  nodeParams.value = filtered
}
function onIPChange(ipId) {
  selectedRefIdx.value = 0
  const ip = props.ipAssets.find(a => a.id === ipId)
  refImages.value = ip?.reference_images?.filter(r => r && (r.path || r.url || typeof r === 'string')) || []
}
function onTemplateChange() { initNodeParams() }

async function handleQuickExecute() {
  if (!canQuickExecute.value) return
  quickExecuting.value = true; lastTaskId.value = ''; currentTaskId.value = ''
  try {
    const tpl = currentTemplate.value
    const wfJson = JSON.parse(JSON.stringify(tpl))
    if (wfJson.nodes?.length > 0) {
      wfJson.nodes[0].parameters = { ...(wfJson.nodes[0].parameters || {}), ...nodeParams.value }
    }
    const body = { workflow_json: wfJson, runtime_inputs: {} }
    if (selectedIPId.value) body.ip_asset_id = selectedIPId.value
    if (selectedTemplateKey.value === 'three_view') {
      body.view_type = viewType.value
      if (selectedRef.value) {
        body.runtime_inputs.image = typeof selectedRef.value === 'string' ? selectedRef.value : (selectedRef.value.path || selectedRef.value.url || '')
      }
    }
    const resp = await executeWorkflow(body)
    const taskId = resp.data?.data?.task_id || ''
    lastTaskId.value = taskId
    currentTaskId.value = taskId
    ElMessage.success(`${t('workflow.submitted')}: ${taskId}`)
    // Start polling for result
    if (taskId) startPolling(taskId)
    // Watch for completion to add to history
    const unwatch = watch(taskStatus, (status) => {
      if (status === 'completed' || status === 'failed') {
        taskHistory.value.unshift({ taskId, status, templateKey: selectedTemplateKey.value })
        if (taskHistory.value.length > 10) taskHistory.value = taskHistory.value.slice(0, 10)
        quickExecuting.value = false
        unwatch()
      }
    })
  } catch (e) { ElMessage.error(t('workflow.execute_failed')); quickExecuting.value = false }
  finally { /* quickExecuting stays true until polling completes */ }
}

// ================ INIT ================
onMounted(async () => {
  try {
    const tplResp = await getWorkflowTemplates()
    templates.value = tplResp.data?.data || []
    if (templates.value.length > 0 && !selectedTemplateKey.value) {
      selectedTemplateKey.value = templates.value[0].metadata?.template_key || 'three_view'
    }
    initNodeParams()
    // Auto-select first IP (for the case where ipAssets is already loaded on mount)
    if (props.ipAssets.length > 0 && !selectedIPId.value) {
      selectedIPId.value = props.ipAssets[0].id
      onIPChange(selectedIPId.value)
    }
  } catch (e) { console.error('[QuickGenerate] Failed to load templates:', e) }
})

// Also watch for async loading from parent (ipAssets arrives after mount)
watch(() => props.ipAssets, (assets) => {
  if (assets.length > 0 && !selectedIPId.value) {
    selectedIPId.value = assets[0].id
    onIPChange(selectedIPId.value)
  }
})
</script>

<style scoped>
.quick-generate { display: flex; flex-direction: column; flex: 1; overflow: hidden; }
.workflow-toolbar { display: flex; align-items: center; justify-content: space-between; padding: 8px 16px; background: #fff; border-bottom: 1px solid #e6e6e6; min-height: 48px; }
.toolbar-left { display: flex; align-items: center; gap: 12px; }
.toolbar-right { display: flex; align-items: center; gap: 8px; }
.empty-state { flex: 1; display: flex; align-items: center; justify-content: center; }
.workflow-content { flex: 1; display: flex; overflow: hidden; }
.param-panel { width: 420px; min-width: 360px; padding: 16px 20px; overflow-y: auto; border-right: 1px solid #e6e6e6; background: #fff; }
.result-panel { flex: 1; padding: 16px 20px; overflow-y: auto; background: #fafafa; }
.panel-title { margin: 0 0 16px; font-size: 15px; color: #303133; }
.section-label { margin: 12px 0 8px; font-size: 13px; color: #606266; font-weight: 600; }
.ref-gallery { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 12px; }
.ref-item { width: 80px; text-align: center; cursor: pointer; border: 2px solid transparent; border-radius: 6px; padding: 4px; transition: border-color 0.2s; }
.ref-item:hover { border-color: #409eff; }
.ref-item.selected { border-color: #e6a23c; }
.ref-img { width: 72px; height: 72px; border-radius: 4px; }
.ref-angle { display: block; font-size: 10px; color: #888; margin-top: 2px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.executing-state { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 60px 0; color: #909399; }
.executing-state p { margin-top: 16px; font-size: 14px; }
.task-result-card { margin-top: 8px; }
.failed-state { padding: 40px 0; }
.inline-result { padding: 12px 0; }
.thumb-grid { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 12px; }
.thumb-item { width: 100px; height: 100px; border-radius: 6px; overflow: hidden; border: 1px solid #e4e7ed; cursor: pointer; }
.thumb-img { width: 100%; height: 100%; }
.story-summary { background: #f0f9eb; border-radius: 8px; padding: 12px; margin-bottom: 12px; }
.story-summary .el-icon { margin-right: 6px; }
.summary-title { font-weight: 600; font-size: 14px; }
.summary-text { margin: 8px 0 0; font-size: 13px; color: #606266; line-height: 1.6; }
.video-summary { background: #fdf6ec; border-radius: 8px; padding: 12px; margin-bottom: 12px; }
.video-summary .el-icon { margin-right: 6px; }
.inline-video { width: 100%; max-height: 200px; margin-top: 8px; border-radius: 6px; }
.result-actions { display: flex; gap: 8px; margin-top: 12px; flex-wrap: wrap; }
.task-history { margin-top: 8px; }
.history-item { display: flex; align-items: center; gap: 8px; padding: 6px 8px; cursor: pointer; border-radius: 4px; font-size: 13px; }
.history-item:hover { background: #f5f7fa; }
.history-id { font-family: monospace; color: #909399; }
</style>
