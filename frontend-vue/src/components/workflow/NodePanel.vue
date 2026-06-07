<template>
  <div class="node-panel">
    <div class="panel-header">
      <el-icon><Operation /></el-icon>
      <span>{{ $t('workflow.node_panel') || '节点面板' }}</span>
    </div>

    <el-input
      v-model="searchQuery"
      :placeholder="$t('workflow.search_nodes') || '搜索节点...'"
      size="small"
      clearable
      class="search-input"
    >
      <template #prefix><el-icon><Search /></el-icon></template>
    </el-input>

    <div class="category-list">
      <el-collapse v-model="expandedCategories">
        <el-collapse-item
          v-for="[category, nodes] in filteredCategories"
          :key="category"
          :name="category"
        >
          <template #title>
            <span class="category-title">
              <span class="category-icon">{{ getCategoryIcon(category) }}</span>
              {{ category }}
              <el-badge :value="nodes.length" type="info" class="category-badge" />
            </span>
          </template>

          <div
            v-for="node in nodes"
            :key="node.name"
            class="node-item"
            draggable="true"
            @dragstart="onDragStart($event, node)"
          >
            <div class="node-item-header">
              <span class="node-name">{{ node.display_name }}</span>
            </div>
            <div class="node-item-desc">{{ node.description }}</div>
            <div class="node-item-ports">
              <span class="port-count">
                IN: {{ getInputCount(node) }}
              </span>
              <span class="port-count">
                OUT: {{ Object.keys(node.return_types || {}).length }}
              </span>
            </div>
          </div>
        </el-collapse-item>
      </el-collapse>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  nodes: { type: Array, default: () => [] },
})

const emit = defineEmits(['add-node'])

const searchQuery = ref('')
const expandedCategories = ref([])

const PORT_COLORS = {
  MODEL: '#e74c3c', IMAGE: '#2ecc71', EMBEDDINGS: '#9b59b6',
  FACES: '#f39c12', STRING: '#3498db', INT: '#1abc9c',
}

const categories = computed(() => {
  const map = {}
  for (const node of props.nodes) {
    const cat = (node.category || '未分类').split('/')[0]
    if (!map[cat]) map[cat] = []
    map[cat].push(node)
  }
  // Expand all by default
  if (expandedCategories.value.length === 0) {
    expandedCategories.value = Object.keys(map)
  }
  return map
})

const filteredCategories = computed(() => {
  const q = searchQuery.value.toLowerCase().trim()
  if (!q) return Object.entries(categories.value)

  const result = {}
  for (const [cat, nodes] of Object.entries(categories.value)) {
    const filtered = nodes.filter(n =>
      n.display_name.toLowerCase().includes(q) ||
      n.name.toLowerCase().includes(q) ||
      (n.description || '').toLowerCase().includes(q)
    )
    if (filtered.length > 0) result[cat] = filtered
  }
  return Object.entries(result)
})

function getCategoryIcon(cat) {
  const icons = { '模型': '🧠', '预处理': '🔧', '文本': '📝', '嵌入': '🔗', '采样': '🎨', '输出': '💾' }
  return icons[cat] || '⚙️'
}

function getInputCount(node) {
  const it = node.input_types || {}
  return Object.keys(it.required || {}).length + Object.keys(it.optional || {}).length
}

function onDragStart(event, node) {
  event.dataTransfer.setData('application/flowpipe-node', JSON.stringify(node))
  event.dataTransfer.effectAllowed = 'move'
}
</script>

<style scoped>
.node-panel {
  width: 240px;
  background: #1a1a2e;
  border-right: 1px solid #2a2a4a;
  display: flex;
  flex-direction: column;
  overflow: hidden;
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
.search-input {
  margin: 8px 12px;
}
.search-input :deep(.el-input__wrapper) {
  background: #252540;
  border-color: #3a3a5c;
}
.search-input :deep(input) {
  color: #e0e0e0;
}

.category-list {
  flex: 1;
  overflow-y: auto;
  padding: 0 8px;
}
.category-list :deep(.el-collapse) {
  border: none;
}
.category-list :deep(.el-collapse-item__header) {
  background: transparent;
  color: #b0b0cc;
  border-bottom-color: #2a2a4a;
  height: 36px;
}
.category-list :deep(.el-collapse-item__wrap) {
  background: transparent;
  border-bottom-color: #2a2a4a;
}
.category-list :deep(.el-collapse-item__content) {
  padding-bottom: 8px;
}

.category-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
}
.category-icon { font-size: 14px; }
.category-badge { margin-left: auto; }

.node-item {
  background: #252540;
  border: 1px solid #3a3a5c;
  border-radius: 6px;
  padding: 8px 10px;
  margin-bottom: 6px;
  cursor: grab;
  transition: all 0.2s;
}
.node-item:hover {
  border-color: #667eea;
  background: #2a2a50;
}
.node-item:active { cursor: grabbing; }

.node-name {
  font-size: 12px;
  font-weight: 600;
  color: #e0e0e0;
}
.node-item-desc {
  font-size: 10px;
  color: #888;
  margin-top: 3px;
  line-height: 1.3;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.node-item-ports {
  display: flex;
  gap: 8px;
  margin-top: 4px;
}
.port-count {
  font-size: 9px;
  color: #666;
  background: rgba(255,255,255,0.05);
  padding: 1px 6px;
  border-radius: 3px;
}
</style>
