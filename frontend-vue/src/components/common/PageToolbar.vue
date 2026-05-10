<template>
  <el-row :gutter="16" class="page-toolbar">
    <el-col :span="searchSpan">
      <el-input
        v-if="showSearch"
        v-model="searchText"
        :prefix-icon="searchIcon"
        :placeholder="searchPlaceholder"
        clearable
        @input="handleSearch"
        @keyup.enter="handleSearch"
      />
    </el-col>
    <el-col :span="actionsSpan" class="toolbar-actions">
      <slot name="actions">
        <el-button v-if="showCreate" type="primary" @click="$emit('create')">
          <el-icon><Plus /></el-icon> {{ createText }}
        </el-button>
      </slot>
    </el-col>
  </el-row>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  showSearch: {
    type: Boolean,
    default: true,
  },
  searchPlaceholder: {
    type: String,
    default: '搜索',
  },
  searchIcon: {
    type: String,
    default: 'Search',
  },
  searchSpan: {
    type: Number,
    default: 8,
  },
  showCreate: {
    type: Boolean,
    default: true,
  },
  createText: {
    type: String,
    default: '创建',
  },
})

const emit = defineEmits(['search', 'create'])

const searchText = ref('')

const actionsSpan = computed(() => 24 - props.searchSpan)

function handleSearch(value) {
  emit('search', value)
}
</script>

<style scoped>
.page-toolbar {
  margin-bottom: 16px;
}

.toolbar-actions {
  text-align: right;
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 8px;
}
</style>
