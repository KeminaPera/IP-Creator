<template>
  <div class="workflow-node" :class="{ selected: selected, 'output-node': isOutputNode }">
    <!-- Header -->
    <div class="node-header" :style="{ backgroundColor: headerColor }">
      <span class="node-icon">{{ icon }}</span>
      <span class="node-title">{{ label }}</span>
    </div>

    <!-- Input ports (left side) -->
    <div class="node-ports inputs">
      <div v-for="port in inputPorts" :key="port.name" class="port input-port">
        <Handle
          type="target"
          :id="port.name"
          :position="Position.Left"
          :style="{ backgroundColor: getPortColor(port.type) }"
        />
        <span class="port-label" :style="{ color: getPortColor(port.type) }">{{ port.label || port.name }}</span>
        <span class="port-type">{{ port.type }}</span>
      </div>
    </div>

    <!-- Output ports (right side) -->
    <div class="node-ports outputs">
      <div v-for="port in outputPorts" :key="port.name" class="port output-port">
        <span class="port-type">{{ port.type }}</span>
        <span class="port-label" :style="{ color: getPortColor(port.type) }">{{ port.label || port.name }}</span>
        <Handle
          type="source"
          :id="port.name"
          :position="Position.Right"
          :style="{ backgroundColor: getPortColor(port.type) }"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Handle, Position } from '@vue-flow/core'

const props = defineProps({
  data: { type: Object, required: true },
  selected: { type: Boolean, default: false },
})

const PORT_COLORS = {
  MODEL: '#e74c3c',
  IMAGE: '#2ecc71',
  IMAGE_LIST: '#27ae60',
  EMBEDDINGS: '#9b59b6',
  FACES: '#f39c12',
  BBOX: '#e67e22',
  STRING: '#3498db',
  INT: '#1abc9c',
  FLOAT: '#16a085',
  ANY: '#95a5a6',
}

const CATEGORY_COLORS = {
  '模型': '#e74c3c',
  '预处理': '#f39c12',
  '文本': '#3498db',
  '嵌入': '#9b59b6',
  '采样': '#2ecc71',
  '输出': '#e67e22',
}

const CATEGORY_ICONS = {
  '模型': '🧠',
  '预处理': '🔧',
  '文本': '📝',
  '嵌入': '🔗',
  '采样': '🎨',
  '输出': '💾',
}

const label = computed(() => props.data.displayName || props.data.type || 'Node')
const isOutputNode = computed(() => props.data.outputNode || false)
const icon = computed(() => {
  const cat = (props.data.category || '').split('/')[0]
  return CATEGORY_ICONS[cat] || '⚙️'
})

const headerColor = computed(() => {
  const cat = (props.data.category || '').split('/')[0]
  return CATEGORY_COLORS[cat] || '#7f8c8d'
})

const inputPorts = computed(() => {
  const ports = []
  const inputTypes = props.data.inputTypes || {}
  for (const [name, typeInfo] of Object.entries(inputTypes.required || {})) {
    ports.push({ name, type: typeInfo[0] || 'ANY', label: typeInfo[1]?.label || name })
  }
  for (const [name, typeInfo] of Object.entries(inputTypes.optional || {})) {
    ports.push({ name, type: typeInfo[0] || 'ANY', label: typeInfo[1]?.label || name, optional: true })
  }
  return ports
})

const outputPorts = computed(() => {
  const ports = []
  const returnTypes = props.data.returnTypes || {}
  for (const [name, type] of Object.entries(returnTypes)) {
    ports.push({ name, type, label: name })
  }
  return ports
})

function getPortColor(type) {
  return PORT_COLORS[type] || PORT_COLORS.ANY
}
</script>

<style scoped>
.workflow-node {
  background: #1e1e2e;
  border: 2px solid #3a3a5c;
  border-radius: 8px;
  min-width: 180px;
  font-size: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
  transition: border-color 0.2s, box-shadow 0.2s;
}
.workflow-node.selected {
  border-color: #667eea;
  box-shadow: 0 0 12px rgba(102, 126, 234, 0.5);
}
.workflow-node.output-node {
  border-style: dashed;
}

.node-header {
  padding: 6px 10px;
  border-radius: 6px 6px 0 0;
  color: #fff;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
}
.node-icon { font-size: 14px; }

.node-ports {
  padding: 6px 0;
}
.port {
  display: flex;
  align-items: center;
  padding: 3px 10px;
  gap: 4px;
}
.input-port { justify-content: flex-start; }
.output-port { justify-content: flex-end; }

.port-label {
  font-size: 11px;
  font-weight: 500;
}
.port-type {
  font-size: 9px;
  color: #888;
  background: rgba(255,255,255,0.05);
  padding: 1px 4px;
  border-radius: 3px;
}
</style>
