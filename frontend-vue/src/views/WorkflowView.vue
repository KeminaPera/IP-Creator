<template>
  <div class="workflow-view">
    <!-- Toolbar -->
    <div class="workflow-toolbar">
      <div class="toolbar-left">
        <h3 class="view-title">
          <el-icon><Connection /></el-icon>
          {{ $t('workflow.title') || '工作流编辑器' }}
        </h3>
        <el-tag v-if="workflowName" type="info" size="small">{{ workflowName }}</el-tag>
      </div>
      <div class="toolbar-right">
        <el-button-group>
          <el-button size="small" @click="loadDefault" :loading="loadingDefault">
            <el-icon><Refresh /></el-icon>
            {{ $t('workflow.load_default') || '加载默认' }}
          </el-button>
          <el-button size="small" type="success" @click="handleValidate" :loading="validating">
            <el-icon><CircleCheck /></el-icon>
            {{ $t('workflow.validate') || '校验' }}
          </el-button>
          <el-button size="small" type="primary" @click="handleSave" :loading="saving">
            <el-icon><Check /></el-icon>
            {{ $t('common.save') || '保存' }}
          </el-button>
          <el-button size="small" type="warning" @click="handleExecute" :loading="executing">
            <el-icon><VideoPlay /></el-icon>
            {{ $t('workflow.execute') || '执行' }}
          </el-button>
        </el-button-group>
      </div>
    </div>

    <!-- Main content: 3-column layout -->
    <div class="workflow-content">
      <!-- Left: Node Panel -->
      <NodePanel :nodes="availableNodes" @add-node="addNodeFromSchema" />

      <!-- Center: vue-flow Canvas -->
      <div class="canvas-container" @drop="onDrop" @dragover.prevent @dragenter.prevent>
        <VueFlow
          v-model:nodes="flowNodes"
          v-model:edges="flowEdges"
          :node-types="nodeTypes"
          :default-viewport="{ x: 0, y: 0, zoom: 0.8 }"
          :snap-to-grid="true"
          :snap-grid="[16, 16]"
          :connection-mode="ConnectionMode.Loose"
          @node-click="onNodeClick"
          @pane-click="onPaneClick"
          @connect="onConnect"
          fit-view-on-init
          class="vue-flow-canvas"
        >
          <Background pattern-color="#2a2a4a" :gap="20" />
          <Controls />
          <MiniMap />
        </VueFlow>
      </div>

      <!-- Right: Property Panel -->
      <PropertyPanel
        :node="selectedNode"
        :node-schema="selectedNodeSchema"
        @update-param="onUpdateParam"
        @delete-node="deleteNode"
      />
    </div>

    <!-- Save Dialog -->
    <el-dialog v-model="showSaveDialog" :title="$t('workflow.save_workflow') || '保存工作流'" width="400px">
      <el-form :model="saveForm" label-width="80px">
        <el-form-item :label="$t('workflow.name') || '名称'">
          <el-input v-model="saveForm.name" :placeholder="$t('workflow.name_placeholder') || '工作流名称'" />
        </el-form-item>
        <el-form-item :label="$t('common.description') || '描述'">
          <el-input v-model="saveForm.description" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showSaveDialog = false">{{ $t('common.cancel') || '取消' }}</el-button>
        <el-button type="primary" @click="doSave" :loading="saving">{{ $t('common.save') || '保存' }}</el-button>
      </template>
    </el-dialog>

    <!-- Execute Dialog -->
    <el-dialog v-model="showExecDialog" :title="$t('workflow.execute_workflow') || '执行工作流'" width="520px">
      <el-form label-width="90px">
        <el-form-item :label="$t('workflow.select_ip') || 'IP 资产'">
          <el-select v-model="execForm.ipId" :placeholder="$t('workflow.select_ip_placeholder') || '选择 IP 资产'" style="width: 100%" @change="onExecIPChange">
            <el-option v-for="ip in ipAssets" :key="ip.id" :label="ip.name" :value="ip.id" />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('workflow.ref_image') || '参考图'" v-if="execRefImages.length > 0">
          <div class="exec-ref-gallery">
            <div
              v-for="(ref, idx) in execRefImages"
              :key="idx"
              class="exec-ref-item"
              :class="{ selected: execForm.selectedRefIdx === idx }"
              @click="execForm.selectedRefIdx = idx"
            >
              <el-image :src="getRefImageUrl(ref)" fit="contain" class="exec-ref-img" />
              <span class="exec-ref-angle">{{ ref.angle || 'img' }}</span>
            </div>
          </div>
        </el-form-item>
        <el-alert v-else-if="execForm.ipId" type="warning" :closable="false" style="margin-bottom: 12px;">
          {{ $t('workflow.no_ref_images') || '该 IP 资产没有参考图' }}
        </el-alert>
        <el-form-item :label="$t('workflow.preview') || '选中图'" v-if="selectedExecRef">
          <el-image :src="getRefImageUrl(selectedExecRef)" fit="contain" style="max-height: 200px; max-width: 100%;" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showExecDialog = false">{{ $t('common.cancel') || '取消' }}</el-button>
        <el-button type="warning" @click="doExecute" :loading="executing" :disabled="!selectedExecRef">
          {{ $t('workflow.execute') || '执行' }}
        </el-button>
      </template>
    </el-dialog>
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

import NodePanel from '../components/workflow/NodePanel.vue'
import PropertyPanel from '../components/workflow/PropertyPanel.vue'
import WorkflowNode from '../components/workflow/WorkflowNode.vue'

import {
  listNodes, getDefaultWorkflow, createWorkflow,
  validateWorkflow, executeWorkflow,
} from '../api/workflow'
import { getIPList } from '../api/ip'

const { t } = useI18n()

// ---- State ----
const availableNodes = ref([])
const flowNodes = ref([])
const flowEdges = ref([])
const selectedNode = ref(null)
const selectedNodeSchema = ref(null)
const workflowName = ref('')
const workflowId = ref(null)
const loadingDefault = ref(false)
const validating = ref(false)
const saving = ref(false)
const executing = ref(false)
const showSaveDialog = ref(false)
const saveForm = ref({ name: '', description: '' })
let nodeCounter = 0

// Execute dialog state
const showExecDialog = ref(false)
const ipAssets = ref([])
const execForm = ref({ ipId: null, selectedRefIdx: 0 })
const execRefImages = ref([])

const selectedExecRef = computed(() => {
  if (execRefImages.value.length === 0) return null
  return execRefImages.value[execForm.value.selectedRefIdx] || execRefImages.value[0] || null
})

// Register custom node type
const nodeTypes = { workflowNode: markRaw(WorkflowNode) }

// ---- Vue Flow instance ----
const { addNodes, addEdges, removeNodes, project } = useVueFlow()

// ---- Helpers ----

function getSchemaForType(typeName) {
  return availableNodes.value.find(n => n.name === typeName) || null
}

function buildFlowNode(id, type, position, parameters = {}) {
  const schema = getSchemaForType(type)
  return {
    id,
    type: 'workflowNode',
    position: position || { x: 100 + Math.random() * 200, y: 100 + Math.random() * 200 },
    data: {
      type,
      displayName: schema?.display_name || type,
      category: schema?.category || '',
      description: schema?.description || '',
      inputTypes: schema?.input_types || {},
      returnTypes: schema?.return_types || {},
      outputNode: schema?.output_node || false,
      parameters: parameters || {},
    },
  }
}

function workflowToJson() {
  const nodes = flowNodes.value.map(fn => ({
    id: fn.id,
    type: fn.data.type,
    position: fn.position,
    parameters: fn.data.parameters || {},
  }))
  const edges = flowEdges.value.map(e => ({
    source: e.source,
    source_output: e.sourceHandle || '',
    target: e.target,
    target_input: e.targetHandle || '',
  }))
  return {
    name: workflowName.value || 'Untitled Workflow',
    version: '1.0',
    nodes,
    edges,
    metadata: {},
  }
}

function loadWorkflowFromJson(wfJson) {
  workflowName.value = wfJson.name || ''
  flowNodes.value = (wfJson.nodes || []).map(n =>
    buildFlowNode(n.id, n.type, n.position, n.parameters)
  )
  flowEdges.value = (wfJson.edges || []).map((e, i) => ({
    id: `e-${i}`,
    source: e.source,
    sourceHandle: e.source_output,
    target: e.target,
    targetHandle: e.target_input,
    animated: true,
    style: { stroke: '#667eea', strokeWidth: 2 },
  }))
  // Reset counter based on existing nodes
  nodeCounter = flowNodes.value.length
}

// ---- Events ----

function onNodeClick({ node }) {
  selectedNode.value = {
    id: node.id,
    type: node.data.type,
    parameters: { ...node.data.parameters },
  }
  selectedNodeSchema.value = getSchemaForType(node.data.type)
}

function onPaneClick() {
  selectedNode.value = null
  selectedNodeSchema.value = null
}

function onConnect(params) {
  addEdges([{
    ...params,
    id: `e-${Date.now()}`,
    animated: true,
    style: { stroke: '#667eea', strokeWidth: 2 },
  }])
}

function onDrop(event) {
  const data = event.dataTransfer.getData('application/flowpipe-node')
  if (!data) return

  const nodeSchema = JSON.parse(data)
  const position = project({
    x: event.clientX - event.currentTarget.getBoundingClientRect().left,
    y: event.clientY - event.currentTarget.getBoundingClientRect().top,
  })

  addNodeFromSchema(nodeSchema, position)
}

function addNodeFromSchema(schema, position) {
  nodeCounter++
  const id = `${schema.name}_${nodeCounter}`
  const defaults = {}
  const it = schema.input_types || {}
  for (const [name, typeInfo] of Object.entries(it.required || {})) {
    if (typeInfo[1]?.default !== undefined) defaults[name] = typeInfo[1].default
  }
  for (const [name, typeInfo] of Object.entries(it.optional || {})) {
    if (typeInfo[1]?.default !== undefined) defaults[name] = typeInfo[1].default
  }

  addNodes([buildFlowNode(id, schema.name, position || { x: 200, y: 200 }, defaults)])
}

function deleteNode(nodeId) {
  removeNodes([nodeId])
  selectedNode.value = null
  selectedNodeSchema.value = null
}

function onUpdateParam({ nodeId, param, value }) {
  const fn = flowNodes.value.find(n => n.id === nodeId)
  if (fn) {
    fn.data = { ...fn.data, parameters: { ...fn.data.parameters, [param]: value } }
    if (selectedNode.value?.id === nodeId) {
      selectedNode.value = { ...selectedNode.value, parameters: { ...selectedNode.value.parameters, [param]: value } }
    }
  }
}

// ---- Actions ----

async function loadDefault() {
  loadingDefault.value = true
  try {
    const resp = await getDefaultWorkflow()
    const wf = resp.data?.data
    if (wf) {
      loadWorkflowFromJson(wf)
      ElMessage.success(t('workflow.default_loaded') || '默认工作流已加载')
    }
  } catch (e) {
    ElMessage.error(t('workflow.load_failed') || '加载失败')
  } finally {
    loadingDefault.value = false
  }
}

async function handleValidate() {
  validating.value = true
  try {
    const wfJson = workflowToJson()
    const resp = await validateWorkflow(wfJson)
    const result = resp.data?.data
    if (result?.valid) {
      ElMessage.success(t('workflow.valid') || '工作流校验通过')
    } else {
      ElMessageBox.alert(
        (result?.errors || []).join('\n'),
        t('workflow.validation_errors') || '校验错误',
        { type: 'warning', confirmButtonText: 'OK' }
      )
    }
  } catch (e) {
    ElMessage.error('Validation request failed')
  } finally {
    validating.value = false
  }
}

function handleSave() {
  saveForm.value = { name: workflowName.value || '', description: '' }
  showSaveDialog.value = true
}

async function doSave() {
  if (!saveForm.value.name.trim()) {
    ElMessage.warning(t('workflow.name_required') || '请输入名称')
    return
  }
  saving.value = true
  try {
    const wfJson = workflowToJson()
    wfJson.name = saveForm.value.name
    workflowName.value = saveForm.value.name

    if (workflowId.value) {
      // Update existing
      const { updateWorkflow } = await import('../api/workflow')
      await updateWorkflow(workflowId.value, {
        name: saveForm.value.name,
        description: saveForm.value.description,
        workflow_json: wfJson,
      })
    } else {
      // Create new
      const resp = await createWorkflow({
        name: saveForm.value.name,
        description: saveForm.value.description,
        workflow_json: wfJson,
      })
      workflowId.value = resp.data?.data?.id
    }
    showSaveDialog.value = false
    ElMessage.success(t('workflow.saved') || '保存成功')
  } catch (e) {
    ElMessage.error(t('workflow.save_failed') || '保存失败')
  } finally {
    saving.value = false
  }
}

function handleExecute() {
  // Open execute dialog instead of immediate confirm
  showExecDialog.value = true
}

async function loadIPAssets() {
  try {
    const resp = await getIPList()
    ipAssets.value = resp.data?.data?.items || resp.data?.data || []
  } catch (e) {
    console.error('Failed to load IP assets:', e)
  }
}

function onExecIPChange(ipId) {
  const ip = ipAssets.value.find(a => a.id === ipId)
  execForm.value.selectedRefIdx = 0
  if (ip && ip.reference_images && ip.reference_images.length > 0) {
    execRefImages.value = ip.reference_images.filter(r => r && (r.path || r.url || typeof r === 'string'))
  } else {
    execRefImages.value = []
  }
}

function getRefImageUrl(ref) {
  let imgPath = typeof ref === 'string' ? ref : (ref.path || ref.url || '')
  if (!imgPath || imgPath === '/placeholder.jpg') return ''
  const normalizedPath = imgPath.replace(/\\/g, '/')
  // New format: data/resources/...
  if (normalizedPath.startsWith('data/resources/')) {
    return `/api/v1/resources/${encodeURIComponent(normalizedPath)}`
  }
  // Old format: data/ip_assets/xxx.jpg
  let cleanPath = normalizedPath.startsWith('/') ? normalizedPath.substring(1) : normalizedPath
  const parts = cleanPath.split('/').filter(p => p.length > 0)
  if (parts.length >= 2) {
    return `/api/v1/generate/files/${parts[parts.length - 2]}/${parts[parts.length - 1]}`
  } else if (parts.length === 1) {
    return `/api/v1/generate/files/${parts[0]}`
  }
  return ''
}

async function doExecute() {
  if (!selectedExecRef.value) {
    ElMessage.warning(t('workflow.select_ref_image') || '请选择参考图')
    return
  }
  showExecDialog.value = false
  executing.value = true
  try {
    const wfJson = workflowToJson()
    const refPath = typeof selectedExecRef.value === 'string'
      ? selectedExecRef.value
      : selectedExecRef.value.path || selectedExecRef.value.url || ''
    const resp = await executeWorkflow({
      workflow_json: wfJson,
      runtime_inputs: { image: refPath },
    })
    const result = resp.data?.data
    ElMessage.success(
      `${t('workflow.submitted') || '已提交'}: ${result?.task_id || ''}`
    )
  } catch (e) {
    ElMessage.error(t('workflow.execute_failed') || '执行失败')
  } finally {
    executing.value = false
  }
}

// ---- Init ----
onMounted(async () => {
  try {
    const resp = await listNodes()
    availableNodes.value = resp.data?.data?.nodes || []
  } catch (e) {
    console.error('Failed to load nodes:', e)
  }
  // Load IP assets for execute dialog
  await loadIPAssets()
  // Load default workflow on mount
  await loadDefault()
})
</script>

<!-- Vue Flow global styles must NOT be scoped -->
<style>
@import '@vue-flow/core/dist/style.css';
@import '@vue-flow/core/dist/theme-default.css';
@import '@vue-flow/controls/dist/style.css';
@import '@vue-flow/minimap/dist/style.css';

/* Dark theme overrides for vue-flow (global) */
.vue-flow__edge-path {
  stroke: #667eea !important;
  stroke-width: 2.5 !important;
}
.vue-flow__edge.selected .vue-flow__edge-path {
  stroke: #a78bfa !important;
  stroke-width: 3 !important;
}
.vue-flow__edge-textbg {
  fill: #1a1a2e;
}
.vue-flow__edge-text {
  fill: #e0e0e0;
}
.vue-flow__connection-line {
  stroke: #667eea;
  stroke-width: 2;
}
.vue-flow__handle {
  width: 10px !important;
  height: 10px !important;
  border: 2px solid #0f0f23 !important;
  border-radius: 50% !important;
}
.vue-flow__node {
  border: none !important;
  border-radius: 8px !important;
  padding: 0 !important;
}
.vue-flow__node.selected {
  box-shadow: 0 0 0 2px #667eea;
}
.vue-flow__minimap {
  background: #1a1a2e;
  border: 1px solid #2a2a4a;
  border-radius: 6px;
}
.vue-flow__controls {
  background: #1a1a2e;
  border: 1px solid #2a2a4a;
  border-radius: 6px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.3);
}
.vue-flow__controls-button {
  background: #252540;
  border-color: #3a3a5c;
  color: #e0e0e0;
  fill: #e0e0e0;
}
.vue-flow__controls-button:hover {
  background: #3a3a5c;
}
.vue-flow__background {
  background: #0f0f23;
}
.vue-flow__pane {
  background: #0f0f23 !important;
}
</style>

<style scoped>
.workflow-view {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 60px - 40px); /* 60px header + 40px el-main padding */
  margin: -20px; /* negate el-main padding */
  background: #0f0f23;
  color: #e0e0e0;
  overflow: hidden;
}

.workflow-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  background: #1a1a2e;
  border-bottom: 1px solid #2a2a4a;
  min-height: 48px;
}
.toolbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
}
.view-title {
  margin: 0;
  font-size: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.workflow-content {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.canvas-container {
  flex: 1;
  position: relative;
}
.vue-flow-canvas {
  width: 100%;
  height: 100%;
  background: #0f0f23;
}

/* Execute dialog ref gallery */
.exec-ref-gallery {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.exec-ref-item {
  width: 80px;
  text-align: center;
  cursor: pointer;
  border: 2px solid transparent;
  border-radius: 6px;
  padding: 4px;
  transition: border-color 0.2s;
}
.exec-ref-item:hover {
  border-color: #667eea;
}
.exec-ref-item.selected {
  border-color: #e6a23c;
}
.exec-ref-img {
  width: 72px;
  height: 72px;
  border-radius: 4px;
}
.exec-ref-angle {
  display: block;
  font-size: 10px;
  color: #888;
  margin-top: 2px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
