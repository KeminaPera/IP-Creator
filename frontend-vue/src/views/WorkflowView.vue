<template>
  <div class="workflow-view">
    <!-- Header with mode tabs -->
    <div class="workflow-header">
      <h3 class="view-title"><el-icon><MagicStick /></el-icon>{{ $t('workflow.title') }}</h3>
      <el-radio-group v-model="activeMode" size="small">
        <el-radio-button value="quick">
          <el-icon><MagicStick /></el-icon> {{ $t('workflow.mode_quick') || '快捷生成' }}
        </el-radio-button>
        <el-radio-button value="editor">
          <el-icon><Connection /></el-icon> {{ $t('workflow.mode_editor') || '流程编排' }}
        </el-radio-button>
      </el-radio-group>
    </div>

    <!-- Quick Generate Mode -->
    <QuickGenerate v-if="activeMode === 'quick'" :ip-assets="ipAssets" />

    <!-- Flow Editor Mode -->
    <FlowEditor v-if="activeMode === 'editor'" :ip-assets="ipAssets" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { MagicStick, Connection } from '@element-plus/icons-vue'

import QuickGenerate from '../components/workflow/QuickGenerate.vue'
import FlowEditor from '../components/workflow/FlowEditor.vue'
import { getIPList } from '../api/ip'

const activeMode = ref('quick')
const ipAssets = ref([])

onMounted(async () => {
  try {
    const ipResp = await getIPList()
    ipAssets.value = ipResp.data?.data?.items || ipResp.data?.data || []
  } catch (e) { console.error('[WorkflowView] Failed to load IP assets:', e) }
})
</script>

<!-- Vue Flow global styles must NOT be scoped -->
<style>
@import '@vue-flow/core/dist/style.css';
@import '@vue-flow/core/dist/theme-default.css';
@import '@vue-flow/controls/dist/style.css';
@import '@vue-flow/minimap/dist/style.css';
.vue-flow__edge-path { stroke: #667eea !important; stroke-width: 2.5 !important; }
.vue-flow__edge.selected .vue-flow__edge-path { stroke: #a78bfa !important; stroke-width: 3 !important; }
.vue-flow__edge-textbg { fill: #1a1a2e; }
.vue-flow__edge-text { fill: #e0e0e0; }
.vue-flow__connection-line { stroke: #667eea; stroke-width: 2; }
.vue-flow__handle { width: 10px !important; height: 10px !important; border: 2px solid #0f0f23 !important; border-radius: 50% !important; }
.vue-flow__node { border: none !important; border-radius: 8px !important; padding: 0 !important; }
.vue-flow__node.selected { box-shadow: 0 0 0 2px #667eea; }
.vue-flow__minimap { background: #1a1a2e; border: 1px solid #2a2a4a; border-radius: 6px; }
.vue-flow__controls { background: #1a1a2e; border: 1px solid #2a2a4a; border-radius: 6px; box-shadow: 0 2px 8px rgba(0,0,0,0.3); }
.vue-flow__controls-button { background: #252540; border-color: #3a3a5c; color: #e0e0e0; fill: #e0e0e0; }
.vue-flow__controls-button:hover { background: #3a3a5c; }
.vue-flow__background { background: #0f0f23; }
.vue-flow__pane { background: #0f0f23 !important; }
</style>

<style scoped>
.workflow-view { display: flex; flex-direction: column; height: calc(100vh - 60px - 40px); margin: -20px; background: #f5f7fa; overflow: hidden; }
.workflow-header { display: flex; align-items: center; justify-content: space-between; padding: 8px 20px; background: #fff; border-bottom: 1px solid #e6e6e6; }
.view-title { margin: 0; font-size: 16px; display: flex; align-items: center; gap: 6px; }
</style>
