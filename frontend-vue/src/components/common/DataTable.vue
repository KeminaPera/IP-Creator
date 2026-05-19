<template>
  <div class="data-table-container">
    <!-- Optional Toolbar Slot -->
    <div v-if="$slots.toolbar" class="data-table-toolbar">
      <slot name="toolbar" />
    </div>

    <!-- Batch Actions Toolbar -->
    <div v-if="$slots['batch-actions'] && selectedRows.length > 0" class="data-table-batch-toolbar">
      <div class="batch-info">
        <el-icon><Check /></el-icon>
        <span>已选择 <strong>{{ selectedRows.length }}</strong> 项</span>
      </div>
      <div class="batch-actions">
        <slot name="batch-actions" :selected="selectedRows" />
      </div>
    </div>

    <!-- Data Table -->
    <el-table
      :data="paginatedData"
      :stripe="stripe"
      :border="border"
      v-loading="loading"
      :row-key="rowKey"
      @selection-change="handleSelectionChange"
      @sort-change="handleSortChange"
      class="data-table"
    >
      <!-- Selection Column -->
      <el-table-column
        v-if="selectable"
        type="selection"
        :width="selectionWidth"
        :reserve-selection="reserveSelection"
        fixed="left"
      />

      <!-- Index Column -->
      <el-table-column
        v-if="showIndex"
        type="index"
        :label="$t('common.no')"
        :width="indexWidth"
        fixed="left"
        align="center"
      />

      <!-- Custom Columns via Slot -->
      <slot :data="paginatedData" />

      <!-- Actions Column -->
      <el-table-column
        v-if="$slots.actions"
        :label="$t('common.actions')"
        min-width="200"
        fixed="right"
        align="center"
      >
        <template #default="{ row }">
          <slot name="actions" :row="row" />
        </template>
      </el-table-column>
    </el-table>

    <!-- Pagination -->
    <div v-if="showPagination" class="data-table-pagination">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :total="computedTotal"
        :page-sizes="pageSizes"
        :layout="paginationLayout"
        :background="paginationBackground"
        @size-change="handlePageChange"
        @current-change="handlePageChange"
      />
    </div>

    <!-- Empty State -->
    <div v-if="!loading && paginatedData.length === 0" class="data-table-empty">
      <slot name="empty">
        <el-empty :description="$t('common.no_data')" />
      </slot>
    </div>
  </div>
</template>

<script setup>
/**
 * DataTable - Reusable data table with pagination
 * 
 * Centralizes table + pagination pattern used across 7+ files.
 * Provides consistent UX, built-in loading, selection, and sorting.
 * 
 * @example
 * <DataTable
 *   :data="channels"
 *   :loading="loading"
 *   :total="total"
 *   @page-change="loadChannels"
 * >
 *   <template #toolbar>
 *     <el-button @click="openCreate">Add</el-button>
 *   </template>
 *   
 *   <template #default="{ data }">
 *     <el-table-column prop="name" label="Name" />
 *   </template>
 *   
 *   <template #actions="{ row }">
 *     <el-button @click="edit(row)">Edit</el-button>
 *   </template>
 * </DataTable>
 */
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Check } from '@element-plus/icons-vue'

useI18n() // Ensure i18n is available

const props = defineProps({
  /**
   * Table data array
   */
  data: {
    type: Array,
    required: true,
    default: () => []
  },
  
  /**
   * Loading state
   */
  loading: {
    type: Boolean,
    default: false
  },
  
  /**
   * Total count for pagination (if using backend pagination)
   */
  total: {
    type: Number,
    default: null
  },
  
  /**
   * Enable stripe style
   */
  stripe: {
    type: Boolean,
    default: true
  },
  
  /**
   * Enable border
   */
  border: {
    type: Boolean,
    default: false
  },
  
  /**
   * Enable row selection
   */
  selectable: {
    type: Boolean,
    default: false
  },
  
  /**
   * Selection column width
   */
  selectionWidth: {
    type: Number,
    default: 55
  },
  
  /**
   * Reserve selection after data refresh
   */
  reserveSelection: {
    type: Boolean,
    default: false
  },
  
  /**
   * Show index column
   */
  showIndex: {
    type: Boolean,
    default: false
  },
  
  /**
   * Index column width
   */
  indexWidth: {
    type: Number,
    default: 60
  },
  
  /**
   * Row key for selection reserve
   */
  rowKey: {
    type: String,
    default: 'id'
  },
  
  /**
   * Actions column width
   */
  actionsWidth: {
    type: Number,
    default: 280
  },
  
  /**
   * Show pagination
   */
  showPagination: {
    type: Boolean,
    default: true
  },
  
  /**
   * Page size options
   */
  pageSizes: {
    type: Array,
    default: () => [10, 20, 50, 100]
  },
  
  /**
   * Pagination layout
   */
  paginationLayout: {
    type: String,
    default: 'total, sizes, prev, pager, next, jumper'
  },
  
  /**
   * Pagination background
   */
  paginationBackground: {
    type: Boolean,
    default: true
  },
  
  /**
   * Initial page size
   */
  pageSize: {
    type: Number,
    default: 20
  },
  
  /**
   * Enable client-side pagination (if total not provided)
   */
  clientPagination: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits([
  'page-change',
  'selection-change',
  'sort-change'
])

// Pagination state
const currentPage = ref(1)
const pageSize = ref(props.pageSize)

// Compute total for pagination
const computedTotal = computed(() => {
  if (props.total !== null && props.total !== undefined) return props.total
  if (props.clientPagination) return props.data.length
  return 0
})

// Debug: Log pagination changes
if (import.meta.env.DEV) {
  watch(() => ({
    showPagination: props.showPagination,
    total: props.total,
    computedTotal: computedTotal.value,
    dataLength: props.data.length,
    clientPagination: props.clientPagination
  }), (val) => {
    console.log('[DataTable] Pagination debug:', val)
  }, { immediate: true })
}

// Compute paginated data (client-side)
const paginatedData = computed(() => {
  if (!props.clientPagination || props.total !== null) {
    return props.data
  }
  
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return props.data.slice(start, end)
})

// Watch for data changes to reset page if needed
watch(
  () => props.data,
  (newData, oldData) => {
    if (oldData && newData.length !== oldData.length && currentPage.value > 1) {
      const maxPage = Math.ceil(newData.length / pageSize.value)
      if (currentPage.value > maxPage) {
        currentPage.value = Math.max(1, maxPage)
      }
    }
  }
)

// Handle page change
function handlePageChange() {
  emit('page-change', {
    page: currentPage.value,
    size: pageSize.value
  })
}

// Handle selection change
const selectedRows = ref([])

function handleSelectionChange(selection) {
  selectedRows.value = selection
  emit('selection-change', selection)
}

// Handle sort change
function handleSortChange(sortInfo) {
  emit('sort-change', sortInfo)
}
</script>

<style scoped>
.data-table-container {
  width: 100%;
}

.data-table-toolbar {
  margin-bottom: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.data-table-batch-toolbar {
  margin-bottom: 16px;
  padding: 12px 16px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 8px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: white;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
}

.batch-info {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
}

.batch-info .el-icon {
  font-size: 18px;
}

.batch-info strong {
  font-size: 16px;
  margin: 0 4px;
}

.batch-actions {
  display: flex;
  gap: 8px;
}

.batch-actions :deep(.el-button) {
  border-color: rgba(255, 255, 255, 0.5);
  color: white;
}

.batch-actions :deep(.el-button:hover) {
  border-color: white;
  background: rgba(255, 255, 255, 0.2);
}

.data-table {
  width: 100%;
}

.data-table-pagination {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
  width: 100%;
  padding: 12px 0;
}

.data-table-empty {
  margin-top: 16px;
}

/* 操作列按钮容器 - 只针对操作列 */
:deep(.el-table__row td:last-child .cell) {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  flex-wrap: nowrap;
  padding: 0 8px;
}

:deep(.el-table__row td:last-child .cell .el-button) {
  margin: 0;
  white-space: nowrap;
}
</style>
