<template>
  <div class="task-page">
    <h1 class="page-title">{{ $t('tasks.title') }}</h1>

    <!-- Toolbar -->
    <DataTable
      :data="tasks"
      :loading="loading"
      :total="total"
      :client-pagination="false"
      :page-size="pagination.pageSize"
      @page-change="handlePageChange"
    >
      <template #toolbar>
        <el-row :gutter="16" style="width: 100%;">
          <el-col :span="8">
            <el-select v-model="filterIPId" :placeholder="$t('tasks.filter_by_ip')" clearable style="width:100%">
              <el-option :label="$t('tasks.all_ips')" :value="null" />
              <el-option v-for="ip in ipAssets" :key="ip.id" :label="ip.name" :value="ip.id" />
            </el-select>
          </el-col>
          <el-col :span="16" style="text-align:right;">
            <el-button type="primary" @click="loadTasks">
              <el-icon><Refresh /></el-icon> {{ $t('tasks.refresh') }}
            </el-button>
          </el-col>
        </el-row>
      </template>

      <template #default>
        <el-table-column prop="id" :label="$t('tasks.task_id')" width="80" />
        <el-table-column :label="$t('tasks.task_type')" min-width="120">
          <template #default="{ row }">{{ row.task_type || '-' }}</template>
        </el-table-column>
        <el-table-column :label="$t('tasks.ip_name')" min-width="140">
          <template #default="{ row }">{{ row.ip_name || $t('tasks.no_ip') }}</template>
        </el-table-column>
        <el-table-column :label="$t('common.status')" width="100" align="center">
          <template #default="{ row }">
            <StatusBadge :status="row.status" />
          </template>
        </el-table-column>
        <el-table-column :label="$t('tasks.progress')" width="120">
          <template #default="{ row }">
            <el-progress v-if="row.status === 'running'" :percentage="row.progress || 0" :stroke-width="6" />
            <span v-else>{{ row.progress || 0 }}%</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" :label="$t('tasks.created_at')" width="170">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column prop="started_at" :label="$t('tasks.start_time')" width="170">
          <template #default="{ row }">{{ formatTime(row.started_at) }}</template>
        </el-table-column>
      </template>

      <template #actions="{ row }">
        <el-button size="small" type="primary" @click="handleView(row)">
          {{ $t('tasks.view_details') }}
        </el-button>
        <el-dropdown trigger="click" style="margin-left: 8px;">
          <el-button size="small">
            {{ $t('common.more') }}<el-icon class="el-icon--right"><arrow-down /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item v-if="row.status === 'completed'" @click="handleViewResult(row)" class="text-success">
                <el-icon><SuccessFilled /></el-icon> {{ $t('tasks.view_result') }}
              </el-dropdown-item>
              <el-dropdown-item v-if="row.status === 'failed' && row.error_message" @click="showErrorDetail(row)" class="text-danger">
                <el-icon><WarningFilled /></el-icon> {{ $t('tasks.view_error') }}
              </el-dropdown-item>
              <el-dropdown-item v-if="row.status === 'failed'" @click="handleRetry(row)" class="text-warning">
                <el-icon><RefreshRight /></el-icon> {{ $t('tasks.retry') }}
              </el-dropdown-item>
              <el-dropdown-item divided @click="handleDelete(row, deleteTask)" class="text-danger">
                <el-icon><Delete /></el-icon> {{ $t('tasks.delete') }}
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </template>
    </DataTable>

    <!-- Task Details Dialog -->
    <el-dialog v-model="detailsDialogVisible" :title="$t('tasks.task_details')" width="600px">
      <el-descriptions :column="1" border v-if="selectedTask">
        <el-descriptions-item :label="$t('tasks.task_id')">{{ selectedTask.id }}</el-descriptions-item>
        <el-descriptions-item :label="$t('tasks.task_type')">{{ selectedTask.task_type }}</el-descriptions-item>
        <el-descriptions-item :label="$t('tasks.ip_name')">{{ selectedTask.ip_name || $t('tasks.no_ip') }}</el-descriptions-item>
        <el-descriptions-item :label="$t('common.status')">
          <StatusBadge :status="selectedTask.status" />
        </el-descriptions-item>
        <el-descriptions-item :label="$t('tasks.progress')">{{ selectedTask.progress || 0 }}%</el-descriptions-item>
        <el-descriptions-item :label="$t('tasks.created_at')">{{ formatTime(selectedTask.created_at) }}</el-descriptions-item>
        <el-descriptions-item :label="$t('tasks.start_time')">{{ formatTime(selectedTask.started_at) }}</el-descriptions-item>
        <el-descriptions-item :label="$t('tasks.completed_at')">{{ formatTime(selectedTask.completed_at) }}</el-descriptions-item>
        <el-descriptions-item :label="$t('tasks.result')">{{ selectedTask.result || $t('tasks.no_result') }}</el-descriptions-item>
        <el-descriptions-item v-if="selectedTask.error_message" :label="$t('tasks.error_message')">
          <el-alert :title="selectedTask.error_message" type="error" :closable="false" />
        </el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowDown, SuccessFilled, WarningFilled, RefreshRight, Delete } from '@element-plus/icons-vue'
import { getTasks, getTask, retryTask, deleteTask, getTaskContentResult } from '@/api/task'
import { getIPList } from '@/api/ip'
import { useAsyncList } from '@/composables/useAsyncData'
import { useAutoRefresh } from '@/composables/usePolling'
import { formatTime } from '../utils/time'
import { useDeleteConfirm } from '../composables/useDeleteConfirm'
import StatusBadge from '../components/common/StatusBadge.vue'
import DataTable from '../components/common/DataTable.vue'

const { t } = useI18n()
const router = useRouter()

const ipAssets = ref([])
const filterIPId = ref(null)
const detailsDialogVisible = ref(false)
const selectedTask = ref(null)

// Use useAsyncList for automatic data fetching with pagination
const { 
  loading, 
  list: tasks, 
  total, 
  pagination,
  execute: loadTasks,
  setPage,
  setPageSize
} = useAsyncList(
  (params) => {
    const requestParams = { ...params }
    if (filterIPId.value) requestParams.ip_asset_id = filterIPId.value
    return getTasks(requestParams)
  },
  { 
    errorMessage: 'common.load_failed',
    autoLoad: true,
    initialPageSize: parseInt(localStorage.getItem('taskMonitor_pageSize')) || 20
  }
)

// Use useAutoRefresh for automatic refresh (30s interval)
const { start: startAutoRefresh, stop: stopAutoRefresh } = useAutoRefresh(
  () => loadTasks(),
  { 
    interval: 30000, // 30 seconds
    autoStart: true,
    pauseOnHidden: true // Pause when tab is hidden
  }
)

// Watch for pageSize changes and save to localStorage
watch(
  () => pagination.value.pageSize,
  (newSize) => {
    localStorage.setItem('taskMonitor_pageSize', newSize.toString())
  }
)

async function loadIPs() {
  try {
    const { data } = await getIPList({ skip: 0, limit: 100 })
    ipAssets.value = data.data || []
  } catch (err) { /* ignore */ }
}

async function handleRetry(row) {
  try {
    await retryTask(row.id)
    ElMessage.success(t('tasks.retry') + ' ' + t('common.success'))
    loadTasks()
  } catch (err) {
    ElMessage.error(t('tasks.retry') + ' ' + t('common.error'))
  }
}

async function handleView(row) {
  try {
    const { data } = await getTask(row.id)
    // Unified response format
    selectedTask.value = data.data
    detailsDialogVisible.value = true
  } catch (err) {
    ElMessage.error(t('tasks.view_details') + ' ' + t('common.error'))
  }
}

async function handleViewResult(row) {
  try {
    const response = await getTaskContentResult(row.id)
    const { data } = response
    
    if (!data.has_content) {
      ElMessage.info(t('tasks.no_content_result'))
      return
    }
    
    // Navigate to Content Library with content ID highlight
    // Clear all filters by using state parameter
    router.push({
      path: '/content-library',
      query: { 
        highlight: data.content_id,
        reset_filters: 'true'  // Signal to reset filters
      }
    })
    
    ElMessage.success(t('tasks.navigating_to_content'))
  } catch (err) {
    console.error('[TaskMonitor] Error in handleViewResult:', err)
    ElMessage.error(t('tasks.view_result') + ' ' + t('common.error'))
  }
}

// Delete task with confirmation
const handleDelete = useDeleteConfirm(loadTasks, 'tasks.delete_success')

function showErrorDetail(row) {
  ElMessageBox.alert(
    `<div style="padding: 10px;">
      <p style="margin-bottom: 10px; font-weight: bold;">${t('tasks.task_id')}: ${row.id}</p>
      <p style="margin-bottom: 10px; font-weight: bold;">${t('tasks.error_detail')}:</p>
      <div style="background: #f5f5f5; padding: 10px; border-radius: 4px; font-family: monospace; word-break: break-all;">
        ${row.error_message}
      </div>
    </div>`,
    t('tasks.error_title'),
    {
      dangerouslyUseHTMLString: true,
      confirmButtonText: t('common.close'),
      type: 'error',
    }
  )
}

function handlePageChange({ page, size }) {
  pagination.value.page = page
  pagination.value.pageSize = size
  if (size !== pagination.value.pageSize) {
    pagination.value.page = 1
  }
  loadTasks()
}

watch(filterIPId, () => {
  pagination.value.page = 1
  loadTasks()
})

// Load IP assets on mount (useAsyncList auto-loads tasks)
loadIPs()

// useAutoRefresh automatically handles page visibility and cleanup
</script>

<style scoped>
.task-page { padding: 0; }
.page-title { font-size: 24px; font-weight: 700; color: #303133; margin: 0 0 20px; }
</style>
