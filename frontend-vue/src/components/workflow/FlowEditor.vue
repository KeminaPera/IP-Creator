<template>
  <div class="flow-editor">
    <div class="workflow-toolbar editor-toolbar">
      <div class="toolbar-left">
        <el-select v-model="editorWorkflowId" :placeholder="$t('workflow.select_workflow')" size="small" style="width:220px" @change="onEditorWorkflowSelect">
          <el-option v-for="wf in savedWorkflows" :key="wf.id" :label="wf.name" :value="wf.id">
            <span>{{ wf.name }}</span>
            <span style="color:#888;font-size:11px;float:right;line-height:24px">{{ wf.updated_at?.slice(0,16) }}</span>
          </el-option>
        </el-select>
        <el-button size="small" @click="handleNewWorkflow"><el-icon><Plus /></el-icon>{{ $t('workflow.new_workflow') }}</el-button>
        <el-button size="small" type="danger" @click="handleDeleteWorkflow" :disabled="!editorWorkflowId"><el-icon><Delete /></el-icon>{{ $t('common.delete') }}</el-button>
      </div>
      <div class="toolbar-right">
        <el-button-group>
          <el-button size="small" @click="loadDefault" :loading="loadingDefault"><el-icon><Refresh /></el-icon>{{ $t('workflow.load_default') }}</el-button>
          <el-button size="small" type="success" @click="handleValidate" :loading="validating"><el-icon><CircleCheck /></el-icon>{{ $t('workflow.validate') }}</el-button>
          <el-button size="small" type="primary" @click="handleSave" :loading="saving"><el-icon><Check /></el-icon>{{ $t('common.save') }}</el-button>
          <el-button size="small" type="warning" @click="handleEditorExecute" :loading="editorExecuting"><el-icon><VideoPlay /></el-icon>{{ $t('workflow.execute') }}</el-button>
        </el-button-group>
      </div>
    </div>

    <div class="workflow-content editor-content">
      <NodePanel :nodes="availableNodes" @add-node="addNodeFromSchema" />
      <div class="canvas-container" @drop="onDrop" @dragover.prevent @dragenter.prevent>
        <VueFlow v-model:nodes="flowNodes" v-model:edges="flowEdges" :node-types="flowNodeTypes"
          :default-viewport="{x:0,y:0,zoom:0.8}" :snap-to-grid="true" :snap-grid="[16,16]"
          :connection-mode="ConnectionMode.Loose" @node-click="onNodeClick" @pane-click="onPaneClick"
          @connect="onConnect" fit-view-on-init class="vue-flow-canvas">
          <Background pattern-color="#2a2a4a" :gap="20" />
          <Controls /><MiniMap />
        </VueFlow>
      </div>
      <PropertyPanel :node="editorSelectedNode" :node-schema="editorSelectedNodeSchema" @update-param="onUpdateParam" @delete-node="deleteNode" />
    </div>

    <!-- Save Dialog -->
    <el-dialog v-model="showSaveDialog" :title="$t('workflow.save_workflow')" width="400px">
      <el-form :model="saveForm" label-width="80px">
        <el-form-item :label="$t('workflow.name')"><el-input v-model="saveForm.name" :placeholder="$t('workflow.name_placeholder')" /></el-form-item>
        <el-form-item :label="$t('common.description')"><el-input v-model="saveForm.description" type="textarea" :rows="3" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showSaveDialog = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" @click="doSave" :loading="saving">{{ $t('common.save') }}</el-button>
      </template>
    </el-dialog>

    <!-- Execute Dialog -->
    <el-dialog v-model="showExecDialog" :title="$t('workflow.execute_workflow')" width="520px">
      <div v-if="ipAssets.length === 0" class="no-ip-warning">
        <el-empty :description="$t('workflow.no_ip_assets')" :image-size="80">
          <el-button type="primary" @click="$router.push('/ip')">{{ $t('ip.create_asset') }}</el-button>
        </el-empty>
      </div>
      <el-form v-else label-width="90px">
        <el-form-item :label="$t('workflow.select_ip')">
          <el-select v-model="execForm.ipId" :placeholder="$t('workflow.select_ip_placeholder')" style="width:100%" @change="onExecIPChange">
            <el-option v-for="ip in ipAssets" :key="ip.id" :label="ip.name" :value="ip.id" />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('workflow.ref_image')" v-if="execRefImages.length > 0">
          <div class="ref-gallery">
            <div v-for="(ref,idx) in execRefImages" :key="idx" class="ref-item" :class="{selected: execForm.selectedRefIdx===idx}" @click="execForm.selectedRefIdx = idx">
              <el-image :src="getRefImageUrl(ref)" fit="contain" class="ref-img" />
              <span class="ref-angle">{{ ref.angle || 'img' }}</span>
            </div>
          </div>
        </el-form-item>
        <el-alert v-else-if="execForm.ipId" type="warning" :closable="false" style="margin-bottom:12px">{{ $t('workflow.no_ref_images') }}</el-alert>
        <el-form-item :label="$t('workflow.preview')" v-if="selectedExecRef">
          <el-image :src="getRefImageUrl(selectedExecRef)" fit="contain" style="max-height:200px;max-width:100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showExecDialog = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="warning" @click="doEditorExecute" :loading="editorExecuting" :disabled="!selectedExecRef || ipAssets.length === 0">{{ $t('workflow.execute') }}</el-button>
      </template>
    </el-dialog>

    <!-- Result Drawer -->
    <div class="result-drawer" :class="{ expanded: showResultDrawer }" v-if="flowTaskId || showResultDrawer">
      <div class="drawer-header" @click="showResultDrawer = !showResultDrawer">
        <span>
          <el-icon v-if="isTaskPolling" class="is-loading" style="margin-right:4px"><Loading /></el-icon>
          <el-icon v-else-if="hasTaskResult" color="#67c23a" style="margin-right:4px"><CircleCheck /></el-icon>
          <el-icon v-else-if="isTaskFailed" color="#f56c6c" style="margin-right:4px"><CircleClose /></el-icon>
          {{ drawerTitle }}
        </span>
        <el-icon><ArrowUp v-if="showResultDrawer" /><ArrowDown v-else /></el-icon>
      </div>
      <div v-if="showResultDrawer" class="drawer-body">
        <!-- Polling -->
        <div v-if="isTaskPolling" class="drawer-progress">
          <el-progress :percentage="taskProgress" :stroke-width="10" />
          <p>{{ $t('workflow.task_running') }}...</p>
        </div>
        <!-- Failed -->
        <div v-if="isTaskFailed" class="drawer-failed">
          <el-alert type="error" :title="$t('workflow.task_failed')" :description="taskErrorMessage" :closable="false" />
        </div>
        <!-- Result summary -->
        <div v-if="hasTaskResult" class="drawer-result">
          <div v-if="flowImageThumbs.length > 0" class="thumb-grid">
            <div v-for="(img, idx) in flowImageThumbs" :key="idx" class="thumb-item">
              <el-image :src="getFileUrl(img.thumbnail_path || img.file_path)" fit="cover" class="thumb-img" />
            </div>
          </div>
          <div v-if="flowStorySummary" class="story-summary">
            <el-icon color="#67c23a"><Document /></el-icon>
            <span>{{ flowStorySummary.title }}</span>
          </div>
          <div v-if="flowVideoSummary" class="video-summary">
            <el-icon color="#e6a23c"><VideoCameraFilled /></el-icon>
            <span>{{ flowVideoSummary.title }}</span>
          </div>
          <div class="result-actions">
            <el-button type="primary" size="small" @click="showFlowResultDialog = true"><el-icon><View /></el-icon>{{ $t('workflow.view_full_result') }}</el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- TaskResultDialog -->
    <TaskResultDialog v-model="showFlowResultDialog" :task-id="flowTaskId" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, markRaw } from 'vue'
import { VueFlow, useVueFlow, ConnectionMode } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import { MiniMap } from '@vue-flow/minimap'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useI18n } from 'vue-i18n'
import {
  VideoPlay, CircleCheck, CircleClose, Plus, Delete, Refresh, Check,
  Loading, ArrowUp, ArrowDown, View, Document, VideoCameraFilled,
} from '@element-plus/icons-vue'

import NodePanel from './NodePanel.vue'
import PropertyPanel from './PropertyPanel.vue'
import WorkflowNode from './WorkflowNode.vue'
import TaskResultDialog from '../TaskResultDialog.vue'
import { useTaskResult } from '../../composables/useTaskResult'
import {
  listNodes, getDefaultWorkflow, listWorkflows, getWorkflow,
  createWorkflow, updateWorkflow, deleteWorkflow,
  validateWorkflow, executeWorkflow,
} from '../../api/workflow'

const props = defineProps({
  ipAssets: { type: Array, default: () => [] },
})

const { t } = useI18n()

// ================ STATE ================
const availableNodes = ref([])
const flowNodes = ref([])
const flowEdges = ref([])
const editorSelectedNode = ref(null)
const editorSelectedNodeSchema = ref(null)
const editorWorkflowId = ref(null)
const workflowName = ref('')
const savedWorkflows = ref([])
const loadingDefault = ref(false)
const validating = ref(false)
const saving = ref(false)
const editorExecuting = ref(false)
const showSaveDialog = ref(false)
const showExecDialog = ref(false)
const saveForm = ref({ name: '', description: '' })
const execForm = ref({ ipId: null, selectedRefIdx: 0 })
const execRefImages = ref([])
const showResultDrawer = ref(false)
const showFlowResultDialog = ref(false)
const flowTaskId = ref('')
let nodeCounter = 0
let selectRequestId = 0

// Task result polling
const { taskStatus, taskProgress, resultContents, isPolling: isTaskPolling, hasResult: hasTaskResult, errorMessage: taskErrorMessage, startPolling, stopPolling } = useTaskResult()
const isTaskFailed = computed(() => taskStatus.value === 'failed' && !isTaskPolling.value)
const drawerTitle = computed(() => {
  if (isTaskPolling.value) return t('workflow.task_progress')
  if (hasTaskResult.value) return t('workflow.task_completed')
  if (isTaskFailed.value) return t('workflow.task_failed')
  return t('workflow.result_drawer_title')
})
const flowImageThumbs = computed(() => resultContents.value.filter(c => c.content_type === 'image').slice(0, 8))
const flowStorySummary = computed(() => resultContents.value.find(c => c.content_type === 'story'))
const flowVideoSummary = computed(() => resultContents.value.find(c => c.content_type === 'video'))
function getFileUrl(filePath) {
  if (!filePath) return ''
  return `/api/v1/contents/files/${filePath.replace(/\\/g, '/')}`
}

// ================ VUE FLOW ================
const flowNodeTypes = { workflowNode: markRaw(WorkflowNode) }
const { addNodes, addEdges, removeNodes, project } = useVueFlow()
const selectedExecRef = computed(() => execRefImages.value.length === 0 ? null : (execRefImages.value[execForm.value.selectedRefIdx] || execRefImages.value[0] || null))

// ================ WORKFLOW HELPERS ================
function getSchemaForType(typeName) { return availableNodes.value.find(n => n.name === typeName) || null }

function buildFlowNode(id, type, position, parameters = {}) {
  const schema = getSchemaForType(type)
  return { id, type: 'workflowNode', position: position || { x: 100 + Math.random() * 200, y: 100 + Math.random() * 200 },
    data: { type, displayName: schema?.display_name || type, category: schema?.category || '', description: schema?.description || '',
      inputTypes: schema?.input_types || {}, returnTypes: schema?.return_types || {}, outputNode: schema?.output_node || false, parameters: parameters || {} } }
}

function workflowToJson() {
  const nodes = flowNodes.value.map(fn => ({ id: fn.id, type: fn.data.type, position: fn.position, parameters: fn.data.parameters || {} }))
  const edges = flowEdges.value.map(e => ({ source: e.source, source_output: e.sourceHandle || '', target: e.target, target_input: e.targetHandle || '' }))
  return { name: workflowName.value || 'Untitled Workflow', version: '1.0', nodes, edges, metadata: {} }
}

function loadWorkflowFromJson(wfJson) {
  workflowName.value = wfJson.name || ''
  flowNodes.value = (wfJson.nodes || []).map(n => buildFlowNode(n.id, n.type, n.position, n.parameters))
  flowEdges.value = (wfJson.edges || []).map((e, i) => ({ id: `e-${i}`, source: e.source, sourceHandle: e.source_output, target: e.target, targetHandle: e.target_input, animated: true, style: { stroke: '#667eea', strokeWidth: 2 } }))
  nodeCounter = flowNodes.value.length
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

// ================ CANVAS INTERACTIONS ================
function onNodeClick({ node }) {
  editorSelectedNode.value = { id: node.id, type: node.data.type, parameters: { ...node.data.parameters } }
  editorSelectedNodeSchema.value = getSchemaForType(node.data.type)
}
function onPaneClick() { editorSelectedNode.value = null; editorSelectedNodeSchema.value = null }
function onConnect(params) { addEdges([{ ...params, id: `e-${Date.now()}`, animated: true, style: { stroke: '#667eea', strokeWidth: 2 } }]) }
function onDrop(event) {
  const data = event.dataTransfer.getData('application/flowpipe-node')
  if (!data) return
  const nodeSchema = JSON.parse(data)
  const position = project({ x: event.clientX - event.currentTarget.getBoundingClientRect().left, y: event.clientY - event.currentTarget.getBoundingClientRect().top })
  addNodeFromSchema(nodeSchema, position)
}
function addNodeFromSchema(schema, position) {
  nodeCounter++
  const id = `${schema.name}_${nodeCounter}`
  const defaults = {}
  const it = schema.input_types || {}
  for (const [name, typeInfo] of Object.entries(it.required || {})) { if (typeInfo[1]?.default !== undefined) defaults[name] = typeInfo[1].default }
  for (const [name, typeInfo] of Object.entries(it.optional || {})) { if (typeInfo[1]?.default !== undefined) defaults[name] = typeInfo[1].default }
  addNodes([buildFlowNode(id, schema.name, position || { x: 200, y: 200 }, defaults)])
}
function deleteNode(nodeId) { removeNodes([nodeId]); editorSelectedNode.value = null; editorSelectedNodeSchema.value = null }
function onUpdateParam({ nodeId, param, value }) {
  const fn = flowNodes.value.find(n => n.id === nodeId)
  if (fn) {
    fn.data = { ...fn.data, parameters: { ...fn.data.parameters, [param]: value } }
    if (editorSelectedNode.value?.id === nodeId) editorSelectedNode.value = { ...editorSelectedNode.value, parameters: { ...editorSelectedNode.value.parameters, [param]: value } }
  }
}

// ================ WORKFLOW CRUD ================
async function loadSavedWorkflows() {
  try { const resp = await listWorkflows(); savedWorkflows.value = resp.data?.data?.items || [] } catch (e) { console.error('Failed to load saved workflows:', e) }
}
async function onEditorWorkflowSelect(id) {
  if (!id) return
  const currentId = ++selectRequestId
  try {
    const resp = await getWorkflow(id)
    if (currentId !== selectRequestId) return
    const wf = resp.data?.data
    if (wf) { loadWorkflowFromJson(wf.workflow_json); editorWorkflowId.value = wf.id; workflowName.value = wf.name; ElMessage.success(`${t('workflow.loaded')}: ${wf.name}`) }
  } catch (e) { if (currentId !== selectRequestId) return; editorWorkflowId.value = null; ElMessage.error(t('workflow.load_failed')) }
}
async function handleNewWorkflow() {
  editorWorkflowId.value = null; workflowName.value = ''; flowNodes.value = []; flowEdges.value = []; editorSelectedNode.value = null; editorSelectedNodeSchema.value = null; nodeCounter = 0; await loadDefault()
}
async function handleDeleteWorkflow() {
  if (!editorWorkflowId.value) return
  const name = savedWorkflows.value.find(w => w.id === editorWorkflowId.value)?.name || ''
  try {
    await ElMessageBox.confirm(`${t('workflow.delete_confirm')} "${name}" ?`, t('common.confirm_delete'), { type: 'warning' })
    await deleteWorkflow(editorWorkflowId.value)
    ElMessage.success(t('workflow.deleted')); editorWorkflowId.value = null; await loadSavedWorkflows(); await loadDefault()
  } catch (e) { if (e !== 'cancel' && e?.toString() !== 'cancel') ElMessage.error(t('workflow.delete_failed')) }
}
async function loadDefault() {
  loadingDefault.value = true
  try { const resp = await getDefaultWorkflow(); const wf = resp.data?.data; if (wf) { loadWorkflowFromJson(wf); ElMessage.success(t('workflow.default_loaded')) } }
  catch (e) { ElMessage.error(t('workflow.load_failed')) } finally { loadingDefault.value = false }
}
async function handleValidate() {
  validating.value = true
  try {
    const wfJson = workflowToJson(); const resp = await validateWorkflow(wfJson); const result = resp.data?.data
    if (result?.valid) ElMessage.success(t('workflow.valid'))
    else ElMessageBox.alert((result?.errors || []).join('\n'), t('workflow.validation_errors'), { type: 'warning' })
  } catch (e) { ElMessage.error('Validation request failed') } finally { validating.value = false }
}
function handleSave() { saveForm.value = { name: workflowName.value || '', description: '' }; showSaveDialog.value = true }
async function doSave() {
  if (!saveForm.value.name.trim()) { ElMessage.warning(t('workflow.name_required')); return }
  saving.value = true
  try {
    const wfJson = workflowToJson(); wfJson.name = saveForm.value.name; workflowName.value = saveForm.value.name
    if (editorWorkflowId.value) await updateWorkflow(editorWorkflowId.value, { name: saveForm.value.name, description: saveForm.value.description, workflow_json: wfJson })
    else { const resp = await createWorkflow({ name: saveForm.value.name, description: saveForm.value.description, workflow_json: wfJson }); editorWorkflowId.value = resp.data?.data?.id }
    showSaveDialog.value = false; ElMessage.success(t('workflow.saved')); await loadSavedWorkflows()
  } catch (e) { ElMessage.error(t('workflow.save_failed')) } finally { saving.value = false }
}

// ================ EXECUTE ================
function handleEditorExecute() {
  // Auto-select first IP when opening execute dialog
  if (props.ipAssets.length > 0 && !execForm.value.ipId) {
    execForm.value.ipId = props.ipAssets[0].id
    onExecIPChange(execForm.value.ipId)
  }
  showExecDialog.value = true
}
function onExecIPChange(ipId) {
  const ip = props.ipAssets.find(a => a.id === ipId); execForm.value.selectedRefIdx = 0
  execRefImages.value = ip?.reference_images?.filter(r => r && (r.path || r.url || typeof r === 'string')) || []
}
async function doEditorExecute() {
  if (!selectedExecRef.value) { ElMessage.warning(t('workflow.select_ref_image')); return }
  showExecDialog.value = false; editorExecuting.value = true
  try {
    const wfJson = workflowToJson()
    const refPath = typeof selectedExecRef.value === 'string' ? selectedExecRef.value : (selectedExecRef.value.path || selectedExecRef.value.url || '')
    const resp = await executeWorkflow({
      workflow_json: wfJson,
      runtime_inputs: { image: refPath },
      ip_asset_id: execForm.value.ipId || undefined,
    })
    const taskId = resp.data?.data?.task_id || ''
    flowTaskId.value = taskId
    ElMessage.success(`${t('workflow.submitted')}: ${taskId}`)
    if (taskId) {
      showResultDrawer.value = true
      startPolling(taskId)
    }
  } catch (e) { ElMessage.error(t('workflow.execute_failed')) } finally { editorExecuting.value = false }
}

// ================ INIT ================
onMounted(async () => {
  try {
    const [nodeResp] = await Promise.all([listNodes()])
    availableNodes.value = nodeResp.data?.data?.nodes || []
    await loadSavedWorkflows()
    await loadDefault()
  } catch (e) { console.error('[FlowEditor] Failed to load initial data:', e) }
})
</script>

<style scoped>
.flow-editor { display: flex; flex-direction: column; flex: 1; overflow: hidden; }
.workflow-toolbar { display: flex; align-items: center; justify-content: space-between; padding: 8px 16px; background: #1a1a2e; border-bottom: 1px solid #2a2a4a; min-height: 48px; }
.workflow-toolbar .el-button { color: #e0e0e0; }
.toolbar-left { display: flex; align-items: center; gap: 12px; }
.toolbar-right { display: flex; align-items: center; gap: 8px; }
.workflow-content { flex: 1; display: flex; overflow: hidden; background: #0f0f23; }
.canvas-container { flex: 1; position: relative; }
.vue-flow-canvas { width: 100%; height: 100%; background: #0f0f23; }
.ref-gallery { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 12px; }
.ref-item { width: 80px; text-align: center; cursor: pointer; border: 2px solid transparent; border-radius: 6px; padding: 4px; transition: border-color 0.2s; }
.ref-item:hover { border-color: #409eff; }
.ref-item.selected { border-color: #e6a23c; }
.ref-img { width: 72px; height: 72px; border-radius: 4px; }
.ref-angle { display: block; font-size: 10px; color: #888; margin-top: 2px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.no-ip-warning { padding: 20px 0; }
.result-drawer { border-top: 1px solid #2a2a4a; background: #1a1a2e; transition: height 0.3s; }
.drawer-header { display: flex; align-items: center; justify-content: space-between; padding: 8px 16px; cursor: pointer; color: #e0e0e0; font-size: 14px; user-select: none; }
.drawer-header:hover { background: #2a2a4a; }
.drawer-body { padding: 12px 16px; max-height: 200px; overflow-y: auto; }
.drawer-progress { display: flex; flex-direction: column; align-items: center; gap: 8px; color: #909399; }
.drawer-progress p { margin: 0; font-size: 13px; }
.drawer-failed { padding: 4px 0; }
.drawer-result { }
.drawer-result .thumb-grid { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 8px; }
.drawer-result .thumb-item { width: 80px; height: 80px; border-radius: 6px; overflow: hidden; border: 1px solid #3a3a5a; }
.drawer-result .thumb-img { width: 100%; height: 100%; }
.drawer-result .story-summary, .drawer-result .video-summary { display: flex; align-items: center; gap: 8px; padding: 8px; margin-bottom: 8px; background: rgba(255,255,255,0.05); border-radius: 6px; color: #e0e0e0; font-size: 14px; }
.drawer-result .result-actions { margin-top: 8px; }
</style>
