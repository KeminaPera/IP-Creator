<template>
  <div class="property-panel" v-if="node">
    <div class="panel-header">
      <el-icon><Setting /></el-icon>
      <span>{{ $t('workflow.properties') || '属性面板' }}</span>
      <el-button size="small" type="danger" :icon="Delete" circle @click="$emit('delete-node', node.id)" />
    </div>

    <div class="node-info">
      <div class="info-row">
        <span class="info-label">类型</span>
        <el-tag size="small" type="info">{{ node.type }}</el-tag>
      </div>
      <div class="info-row">
        <span class="info-label">ID</span>
        <span class="info-value">{{ node.id }}</span>
      </div>
      <div class="info-row" v-if="nodeSchema">
        <span class="info-label">分类</span>
        <span class="info-value">{{ nodeSchema.category }}</span>
      </div>
    </div>

    <el-divider />

    <div class="params-section" v-if="nodeSchema">
      <h4 class="section-title">参数配置</h4>

      <!-- Required params -->
      <div v-for="[name, typeInfo] of requiredParams" :key="name" class="param-group">
        <label class="param-label">
          {{ typeInfo[1]?.label || name }}
          <span class="required-star">*</span>
        </label>
        <el-select
          v-if="hasOptions(typeInfo)"
          :model-value="getParamValue(name)"
          @update:model-value="setParamValue(name, $event)"
          :placeholder="typeInfo[1]?.label || '选择...'"
          size="small"
          class="param-input"
        >
          <el-option
            v-for="opt in typeInfo[1].options"
            :key="opt"
            :label="opt"
            :value="opt"
          />
        </el-select>
        <el-input-number
          v-else-if="typeInfo[0] === 'INT' || typeInfo[0] === 'FLOAT'"
          :model-value="getParamValue(name)"
          @update:model-value="setParamValue(name, $event)"
          v-bind="getNumericProps(typeInfo)"
          size="small"
          controls-position="right"
          class="param-input"
        />
        <el-input
          v-else
          :model-value="getParamValue(name)"
          @update:model-value="setParamValue(name, $event)"
          :placeholder="typeInfo[1]?.label || typeInfo[0]"
          :type="typeInfo[1]?.multiline ? 'textarea' : undefined"
          :rows="typeInfo[1]?.multiline ? 3 : undefined"
          size="small"
          class="param-input"
        />
        <div class="param-hint" v-if="typeInfo[1]?.description">
          {{ typeInfo[1].description }}
        </div>
      </div>

      <!-- Optional params -->
      <template v-if="optionalParams.length > 0">
        <el-divider />
        <h4 class="section-title">可选参数</h4>
        <div v-for="[name, typeInfo] of optionalParams" :key="name" class="param-group">
          <label class="param-label">{{ typeInfo[1]?.label || name }}</label>
          <el-select
            v-if="hasOptions(typeInfo)"
            :model-value="getParamValue(name)"
            @update:model-value="setParamValue(name, $event)"
            :placeholder="typeInfo[1]?.label || '选择...'"
            size="small"
            class="param-input"
          >
            <el-option
              v-for="opt in typeInfo[1].options"
              :key="opt"
              :label="opt"
              :value="opt"
            />
          </el-select>
          <el-input-number
            v-else-if="typeInfo[0] === 'INT' || typeInfo[0] === 'FLOAT'"
            :model-value="getParamValue(name)"
            @update:model-value="setParamValue(name, $event)"
            v-bind="getNumericProps(typeInfo)"
            size="small"
            controls-position="right"
            class="param-input"
          />
          <el-input
            v-else
            :model-value="getParamValue(name)"
            @update:model-value="setParamValue(name, $event)"
            :placeholder="typeInfo[1]?.label || typeInfo[0]"
            :type="typeInfo[1]?.multiline ? 'textarea' : undefined"
            :rows="typeInfo[1]?.multiline ? 3 : undefined"
            size="small"
            class="param-input"
          />
        </div>
      </template>
    </div>

    <!-- Ports info -->
    <el-divider />
    <div class="ports-section">
      <h4 class="section-title">端口</h4>
      <div class="port-list">
        <div v-for="(type, name) in (nodeSchema?.return_types || {})" :key="name" class="port-info">
          <span class="port-direction">OUT</span>
          <span class="port-name">{{ name }}</span>
          <el-tag size="small" :color="getPortColor(type)" effect="dark">{{ type }}</el-tag>
        </div>
      </div>
    </div>
  </div>

  <div class="property-panel empty" v-else>
    <div class="empty-hint">
      <el-icon :size="48" color="#444"><Mouse /></el-icon>
      <p>{{ $t('workflow.select_node_hint') || '点击节点查看属性' }}</p>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Delete } from '@element-plus/icons-vue'

const props = defineProps({
  node: { type: Object, default: null },
  nodeSchema: { type: Object, default: null },
})

const emit = defineEmits(['update-param', 'delete-node'])

const PORT_COLORS = {
  MODEL: '#e74c3c', IMAGE: '#2ecc71', IMAGE_LIST: '#27ae60',
  EMBEDDINGS: '#9b59b6', FACES: '#f39c12', BBOX: '#e67e22',
  STRING: '#3498db', INT: '#1abc9c', FLOAT: '#16a085', ANY: '#95a5a6',
}

const requiredParams = computed(() => {
  if (!props.nodeSchema) return []
  return Object.entries(props.nodeSchema.input_types?.required || {})
})

const optionalParams = computed(() => {
  if (!props.nodeSchema) return []
  return Object.entries(props.nodeSchema.input_types?.optional || {})
})

function getParamValue(name) {
  return props.node?.parameters?.[name] ?? props.nodeSchema?.input_types?.required?.[name]?.[1]?.default
    ?? props.nodeSchema?.input_types?.optional?.[name]?.[1]?.default ?? ''
}

function setParamValue(name, value) {
  emit('update-param', { nodeId: props.node.id, param: name, value })
}

function hasOptions(typeInfo) {
  const [, config] = typeInfo
  return config?.options && config.options.length > 0
}

function getNumericProps(typeInfo) {
  const [type, config] = typeInfo
  if (type === 'FLOAT') {
    return {
      min: config?.min ?? 0,
      max: config?.max ?? 10,
      step: config?.step ?? 0.1,
      precision: config?.precision ?? 2,
    }
  }
  return {
    min: config?.min ?? 0,
    max: config?.max ?? 9999,
    step: config?.step ?? 1,
  }
}

function getPortColor(type) {
  return PORT_COLORS[type] || PORT_COLORS.ANY
}
</script>

<style scoped>
.property-panel {
  width: 280px;
  background: #1a1a2e;
  border-left: 1px solid #2a2a4a;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}
.property-panel.empty {
  display: flex;
  align-items: center;
  justify-content: center;
}
.empty-hint {
  text-align: center;
  color: #666;
}
.empty-hint p {
  margin-top: 12px;
  font-size: 13px;
}

.panel-header {
  padding: 12px 16px;
  font-weight: 600;
  color: #e0e0e0;
  border-bottom: 1px solid #2a2a4a;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
}
.panel-header .el-button { margin-left: auto; }

.node-info {
  padding: 12px 16px;
}
.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}
.info-label { font-size: 12px; color: #888; }
.info-value { font-size: 12px; color: #e0e0e0; font-family: monospace; }

.params-section, .ports-section {
  padding: 0 16px 12px;
}
.section-title {
  font-size: 12px;
  color: #b0b0cc;
  margin: 0 0 10px 0;
  font-weight: 600;
}

.param-group {
  margin-bottom: 12px;
}
.param-label {
  display: block;
  font-size: 11px;
  color: #aaa;
  margin-bottom: 4px;
  font-weight: 500;
}
.required-star { color: #e74c3c; margin-left: 2px; }
.param-input { width: 100%; }
.param-input :deep(.el-input__wrapper),
.param-input :deep(.el-textarea__inner) {
  background: #252540;
  border-color: #3a3a5c;
  color: #e0e0e0;
}
.param-input :deep(.el-select .el-input__wrapper) {
  background: #252540;
}
.param-hint {
  font-size: 10px;
  color: #666;
  margin-top: 2px;
}

.el-divider {
  border-color: #2a2a4a;
  margin: 8px 0;
}

.port-list { padding: 0; }
.port-info {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}
.port-direction {
  font-size: 9px;
  font-weight: 700;
  color: #2ecc71;
  background: rgba(46, 204, 113, 0.1);
  padding: 2px 6px;
  border-radius: 3px;
}
.port-name {
  font-size: 11px;
  color: #e0e0e0;
  font-family: monospace;
}
</style>
