<template>
  <div class="dataset-page">
    <h1 class="page-title">{{ $t('dataset.title') }}</h1>

    <!-- Toolbar -->
    <DataTable
      :data="datasets"
      :loading="loading"
      :total="total"
      :page="currentPage"
      :page-size="pageSize"
      @update:page="handlePageChange"
      @update:page-size="handlePageSizeChange"
    >
      <template #toolbar>
        <el-row :gutter="16" style="width: 100%;">
          <el-col :span="6">
            <el-select v-model="filterIpId" :placeholder="$t('dataset.select_ip_placeholder')" clearable @change="loadDatasets">
              <el-option :label="$t('dataset.all')" :value="null" />
              <el-option v-for="ip in ipList" :key="ip.id" :label="ip.name" :value="ip.id" />
            </el-select>
          </el-col>
          <el-col :span="6">
            <el-select v-model="filterStatus" :placeholder="$t('dataset.status')" clearable @change="loadDatasets">
              <el-option :label="$t('dataset.all')" :value="null" />
              <el-option :label="$t('dataset.pending')" value="pending" />
              <el-option :label="$t('dataset.validating')" value="validating" />
              <el-option :label="$t('dataset.ready')" value="ready" />
              <el-option :label="$t('dataset.training')" value="training" />
              <el-option :label="$t('dataset.archived')" value="archived" />
            </el-select>
          </el-col>
          <el-col :span="12" style="text-align:right;">
            <el-button type="primary" @click="openCreateDialog">
              <el-icon><Plus /></el-icon> {{ $t('dataset.create_dataset') }}
            </el-button>
          </el-col>
        </el-row>
      </template>

      <template #default>
        <el-table-column prop="name" :label="$t('dataset.dataset_name')" min-width="180" />
        <el-table-column :label="$t('dataset.ip_asset')" width="150">
          <template #default="{ row }">
            {{ getIpName(row.ip_asset_id) }}
          </template>
        </el-table-column>
        <el-table-column :label="$t('dataset.image_count')" width="120" align="center">
          <template #default="{ row }">
            <el-tag size="small">{{ row.image_count }} 张</el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('dataset.augmented_count')" width="120" align="center">
          <template #default="{ row }">
            <el-tag size="small" type="info">{{ row.augmented_count }} 张</el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('dataset.quality_score')" width="120" align="center">
          <template #default="{ row }">
            <el-progress
              v-if="row.quality_score"
              :percentage="row.quality_score"
              :color="getQualityColor(row.quality_score)"
              :stroke-width="12"
            />
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" :label="$t('dataset.status')" width="120" align="center">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">
              {{ getStatusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="version" :label="$t('dataset.version')" width="80" align="center" />
      </template>

      <template #actions="{ row }">
        <el-button size="small" type="primary" @click="openDetailDialog(row)">{{ $t('dataset.detail') }}</el-button>
        <el-button size="small" type="success" @click="openAnnotationPage(row)">
          <el-icon><Edit /></el-icon> {{ $t('dataset.annotate') }}
        </el-button>
        <el-dropdown trigger="click" style="margin-left: 8px;">
          <el-button size="small">
            {{ $t('dataset.more') }}<el-icon class="el-icon--right"><arrow-down /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item @click="handleFilterQuality(row)">
                <el-icon><Filter /></el-icon> 质量过滤
              </el-dropdown-item>
              <el-dropdown-item @click="handleEvaluateQuality(row)">
                <el-icon><Star /></el-icon> {{ $t('dataset.evaluate_quality') }}
              </el-dropdown-item>
              <el-dropdown-item @click="handleValidate(row)">
                <el-icon><Check /></el-icon> {{ $t('dataset.validate') }}
              </el-dropdown-item>
              <el-dropdown-item @click="handleAugment(row)">
                <el-icon><MagicStick /></el-icon> {{ $t('dataset.augment') }}
              </el-dropdown-item>
              <el-dropdown-item @click="handleCreateVersion(row)">
                <el-icon><DocumentCopy /></el-icon> {{ $t('dataset.create_version') }}
              </el-dropdown-item>
              <el-dropdown-item divided @click="handleDelete(row)" class="text-danger">
                <el-icon><Delete /></el-icon> {{ $t('dataset.delete') }}
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </template>
    </DataTable>

    <!-- Create Dataset Dialog -->
    <CRUDDialog
      v-model="createDialogVisible"
      :title="$t('dataset.create_dialog_title')"
      width="700px"
      :form-data="createForm"
      :rules="createRules"
      label-width="120px"
      :loading="creating"
      :confirm-text="$t('dataset.confirm_btn')"
      @submit="handleCreate"
    >
      <template #default="{ formData }">
        <el-alert
          :title="$t('dataset.create_flow_title')"
          type="info"
          :closable="false"
          style="margin-bottom: 20px;"
        >
          <template #default>
            <div style="font-size: 13px; line-height: 1.6;">
              <strong>{{ $t('dataset.step1') }}</strong><br/>
              <strong>{{ $t('dataset.step2') }}</strong><br/>
              <strong>{{ $t('dataset.step3') }}</strong><br/>
              <strong>{{ $t('dataset.step4') }}</strong>
            </div>
          </template>
        </el-alert>

        <el-form-item :label="$t('dataset.ip_asset')" prop="ip_asset_id">
          <el-select v-model="formData.ip_asset_id" :placeholder="$t('dataset.select_ip_placeholder')" style="width:100%">
            <el-option v-for="ip in ipList" :key="ip.id" :label="ip.name" :value="ip.id" />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('dataset.dataset_name')" prop="name">
          <el-input v-model="formData.name" :placeholder="$t('dataset.name_placeholder')" />
        </el-form-item>
        <el-form-item :label="$t('dataset.description')">
          <el-input
            v-model="formData.description"
            type="textarea"
            :rows="3"
            :placeholder="$t('dataset.description_placeholder')"
          />
        </el-form-item>

        <el-divider>{{ $t('dataset.image_upload') }}</el-divider>

        <el-form-item :label="$t('dataset.training_images')">
          <ImageUploader
            v-model="formData.image_paths"
            :limit="50"
            accept="image/jpeg,image/png,image/webp"
          />
          
          <div v-if="formData.image_paths.length > 0" style="margin-top: 12px; padding: 12px; background: #f0f9ff; border-radius: 4px;">
            <el-icon style="color: #409eff; vertical-align: middle;"><InfoFilled /></el-icon>
            <span style="margin-left: 8px; color: #606266;">
              {{ $t('dataset.selected_images', { count: formData.image_paths.length }) }}
              <span v-if="formData.image_paths.length < 15" style="color: #E6A23C; margin-left: 8px;">
                {{ $t('dataset.suggest_min') }}
              </span>
              <span v-else-if="formData.image_paths.length >= 15 && formData.image_paths.length <= 30" style="color: #67C23A; margin-left: 8px;">
                {{ $t('dataset.count_ok') }}
              </span>
              <span v-else style="color: #F56C6C; margin-left: 8px;">
                {{ $t('dataset.suggest_max') }}
              </span>
            </span>
          </div>
        </el-form-item>
      </template>
    </CRUDDialog>

    <!-- Dataset Detail Dialog -->
    <el-dialog v-model="detailDialogVisible" :title="$t('dataset.detail_title')" width="900px">
      <div v-if="currentDataset" class="dataset-detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item :label="$t('dataset.dataset_name')">{{ currentDataset.name }}</el-descriptions-item>
          <el-descriptions-item :label="$t('dataset.ip_asset')">{{ getIpName(currentDataset.ip_asset_id) }}</el-descriptions-item>
          <el-descriptions-item :label="$t('dataset.image_count')">{{ currentDataset.image_count }} 张</el-descriptions-item>
          <el-descriptions-item :label="$t('dataset.augmented_count')">{{ currentDataset.augmented_count }} 张</el-descriptions-item>
          <el-descriptions-item :label="$t('dataset.quality_score')">{{ currentDataset.quality_score || '-' }}</el-descriptions-item>
          <el-descriptions-item :label="$t('dataset.status')">
            <el-tag :type="getStatusType(currentDataset.status)">
              {{ getStatusLabel(currentDataset.status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item :label="$t('dataset.version')">v{{ currentDataset.version }}</el-descriptions-item>
          <el-descriptions-item :label="$t('common.created_at')">{{ currentDataset.created_at }}</el-descriptions-item>
        </el-descriptions>

        <el-divider>{{ $t('dataset.angle_coverage') }}</el-divider>
        <div v-if="currentDataset.angle_coverage" class="angle-coverage">
          <el-tag
            v-for="(count, angle) in currentDataset.angle_coverage"
            :key="angle"
            style="margin: 4px;"
          >
            {{ angle }}: {{ count }} 张
          </el-tag>
        </div>
        <el-empty v-else :description="$t('dataset.no_angle_data')" :image-size="80" />
      </div>
    </el-dialog>

    <!-- Augment Dialog -->
    <el-dialog v-model="augmentDialogVisible" :title="$t('dataset.augment_dialog_title')" width="600px">
      <el-form :model="augmentForm" label-width="150px">
        <el-form-item :label="$t('dataset.augment_factor')">
          <el-slider v-model="augmentForm.factor" :min="1" :max="5" :step="1" show-input />
        </el-form-item>
        <el-form-item :label="$t('dataset.augment_strategies')">
          <el-checkbox-group v-model="augmentForm.strategies">
            <el-checkbox label="horizontal_flip">{{ $t('dataset.horizontal_flip') }}</el-checkbox>
            <el-checkbox label="rotation">{{ $t('dataset.rotation') }}</el-checkbox>
            <el-checkbox label="brightness">{{ $t('dataset.brightness') }}</el-checkbox>
            <el-checkbox label="contrast">{{ $t('dataset.contrast') }}</el-checkbox>
            <el-checkbox label="color_jitter">{{ $t('dataset.color_jitter') }}</el-checkbox>
          </el-checkbox-group>
          <div style="color: #909399; font-size: 12px; margin-top: 8px;">
            {{ $t('dataset.strategy_hint') }}
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="augmentDialogVisible = false">{{ $t('dataset.cancel') }}</el-button>
        <el-button type="primary" @click="handleAugmentConfirm" :loading="augmenting">{{ $t('dataset.start_augment') }}</el-button>
      </template>
    </el-dialog>

    <!-- Quality Filter Dialog -->
    <el-dialog v-model="filterDialogVisible" :title="$t('dataset.quality_filter')" width="500px">
      <el-form :model="filterForm" label-width="120px">
        <el-alert
          :title="$t('dataset.filter_low_quality')"
          type="warning"
          :closable="false"
          style="margin-bottom: 20px;"
        >
          <template #default>
            <div style="font-size: 13px; line-height: 1.6;">
              {{ $t('dataset.filter_description') }}
            </div>
          </template>
        </el-alert>
        
        <el-form-item :label="$t('dataset.quality_threshold')">
          <el-slider v-model="filterForm.threshold" :min="0" :max="100" :step="5" show-input />
          <div style="color: #909399; font-size: 12px; margin-top: 8px;">
            {{ $t('dataset.threshold_hint') }}
          </div>
        </el-form-item>
        
        <el-form-item :label="$t('dataset.filter_action')">
          <el-radio-group v-model="filterForm.action">
            <el-radio label="mark">{{ $t('dataset.action_mark') }}</el-radio>
            <el-radio label="delete">{{ $t('dataset.action_delete') }}</el-radio>
          </el-radio-group>
          <div style="color: #909399; font-size: 12px; margin-top: 8px;">
            {{ filterForm.action === 'mark' ? $t('dataset.mark_hint') : $t('dataset.delete_hint') }}
          </div>
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="filterDialogVisible = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="warning" @click="handleFilterConfirm" :loading="filtering">{{ $t('dataset.start_filter') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, ArrowDown, Check, MagicStick, DocumentCopy, Delete, InfoFilled, Edit, Star, Filter } from '@element-plus/icons-vue'
import DataTable from '@/components/common/DataTable.vue'
import CRUDDialog from '@/components/common/CRUDDialog.vue'
import ImageUploader from '@/components/common/ImageUploader.vue'
import { logger } from '@/utils/logger'
import {
  getDatasetList,
  createDataset,
  deleteDataset,
  validateDataset,
  evaluateDatasetQuality,
  filterLowQualityImages,
  augmentDataset,
  createDatasetVersion,
  getDatasetDetail,
} from '@/api/dataset'
import { getIPList } from '@/api/ip'
import { useAsyncList } from '@/composables/useAsyncData'
import { useI18n } from 'vue-i18n'

const router = useRouter()
const { t } = useI18n()

// State - Must be declared before useAsyncList (autoLoad references these)
const filterIpId = ref(null)
const filterStatus = ref(null)
const ipList = ref([])

// Use useAsyncList for automatic data fetching with pagination
const { 
  loading, 
  list: datasets, 
  total, 
  pagination,
  execute: loadDatasets,
  setPage: handlePageChange,
  setPageSize: handlePageSizeChange
} = useAsyncList(
  (params) => {
    const requestParams = { ...params }
    if (filterIpId.value) requestParams.ip_asset_id = filterIpId.value
    if (filterStatus.value) requestParams.status = filterStatus.value
    return getDatasetList(requestParams)
  },
  { 
    errorMessage: 'dataset.load_failed',
    autoLoad: true
  }
)

// Create Dialog
const createDialogVisible = ref(false)
const creating = ref(false)
const createForm = reactive({
  ip_asset_id: null,
  name: '',
  description: '',
  image_paths: [],
})
const createRules = {
  ip_asset_id: [{ required: true, message: t('dataset.ip_asset_required'), trigger: 'change' }],
  name: [{ required: true, message: t('dataset.name_required'), trigger: 'blur' }],
}

// Detail Dialog
const detailDialogVisible = ref(false)
const currentDataset = ref(null)

// Augment Dialog
const augmentDialogVisible = ref(false)
const augmenting = ref(false)
const augmentForm = reactive({
  factor: 2,
  strategies: [],
})

// Quality filter state
const filterDialogVisible = ref(false)
const filtering = ref(false)
const currentFilterDatasetId = ref(null)
const filterForm = reactive({
  threshold: 30,
  action: 'mark',
})
const currentAugmentDatasetId = ref(null)

// Load IP list
const loadIpList = async () => {
  try {
    const res = await getIPList({ limit: 100 })
    ipList.value = res.data.data || []
  } catch (error) {
    logger.error('Failed to load IP list:', error)
    ipList.value = []
  }
}

const openCreateDialog = () => {
  createDialogVisible.value = true
  createForm.ip_asset_id = null
  createForm.name = ''
  createForm.description = ''
  createForm.image_paths = []
}

const handleCreate = async (formData) => {
  if (!formData.image_paths || formData.image_paths.length === 0) {
    ElMessage.warning(t('dataset.upload_images_first'))
    return
  }

  creating.value = true
  try {
    // Step 1: Create dataset with image paths
    const res = await createDataset(formData)
    const datasetId = res.data.id || res.data.data?.id
    
    ElMessage.success(t('dataset.creating_success'))
    createDialogVisible.value = false
    
    // Step 2: Redirect to annotation page
    ElMessageBox.confirm(
      t('dataset.go_annotate_message'),
      t('dataset.go_annotate_title'),
      {
        confirmButtonText: t('dataset.go_annotate_confirm'),
        cancelButtonText: t('dataset.go_annotate_cancel'),
        type: 'success',
      }
    ).then(() => {
      router.push({
        path: '/datasets/annotate',
        query: { dataset_id: datasetId }
      })
    }).catch(() => {
      // User chose to annotate later
    })
    
  } catch (error) {
    logger.error('Create dataset error:', error)
    ElMessage.error(error.message || t('common.request_failed'))
  } finally {
    creating.value = false
  }
}

const openDetailDialog = async (row) => {
  try {
    const res = await getDatasetDetail(row.id, { include_images: false })
    currentDataset.value = res.data.data
    detailDialogVisible.value = true
  } catch (error) {
    ElMessage.error(t('dataset.detail_load_failed'))
  }
}

const openAnnotationPage = (row) => {
  router.push({
    path: '/datasets/annotate',
    query: { dataset_id: row.id }
  })
}

const handleEvaluateQuality = async (row) => {
  try {
    const loading = ElMessage({
      message: t('dataset.evaluating_quality'),
      type: 'info',
      duration: 0,
    })
    
    const res = await evaluateDatasetQuality(row.id)
    loading.close()
    
    ElMessage.success(res.message)
    loadDatasets()
  } catch (error) {
    ElMessage.error(t('dataset.evaluate_quality_failed'))
  }
}

const handleValidate = async (row) => {
  try {
    await ElMessageBox.confirm(t('dataset.confirm_validate'), t('dataset.validate'), {
      confirmButtonText: t('common.confirm'),
      cancelButtonText: t('common.cancel'),
      type: 'info',
    })

    const res = await validateDataset(row.id)
    const report = res.data  // res.data already contains the response object
    
    // 获取评分颜色
    const getScoreColor = (score) => {
      if (score >= 80) return '#67c23a'
      if (score >= 60) return '#e6a23c'
      if (score >= 40) return '#f56c6c'
      return '#ff4949'
    }
    
    const scoreColor = getScoreColor(report.quality_score)
    
    // 构建详细报告HTML
    let reportHtml = `<div class="validation-report">
      <!-- 质量评分 -->
      <div class="report-section">
        <p class="report-section-title">质量评分</p>
        <div class="quality-score-bar">
          <div class="quality-score-fill" style="width: ${report.quality_score}%; background: ${scoreColor};"></div>
          <span class="quality-score-text">${report.quality_score}分</span>
        </div>
      </div>
      
      <!-- 基本信息 -->
      <div class="report-section">
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
          <div style="background: #ecf5ff; padding: 10px; border-radius: 5px;">
            <p style="margin: 0; color: #409eff;"><strong>图片总数:</strong> ${report.total_images} 张</p>
          </div>
          <div style="background: #f0f9ff; padding: 10px; border-radius: 5px;">
            <p style="margin: 0; color: #67c23a;"><strong>已选图片:</strong> ${report.selected_images} 张</p>
          </div>
        </div>
      </div>
      
      <!-- 角度覆盖 -->
      <div class="report-section">
        <p class="report-section-title">角度覆盖</p>
        <div style="background: #fafafa; padding: 10px; border-radius: 5px;">`
    
    // 角度覆盖
    if (report.angle_coverage && Object.keys(report.angle_coverage).length > 0) {
      const angleNames = {
        'front': '正面',
        'side': '侧面',
        'back': '背面',
        'full_body': '全身',
        'half_body': '半身'
      }
      
      for (const [angle, count] of Object.entries(report.angle_coverage)) {
        const angleName = angleNames[angle] || angle
        const percentage = Math.min(100, (count / 10) * 100) // 10张为满分
        const status = count >= 3 ? '✓' : '⚠️'
        const barColor = count >= 3 ? '#67c23a' : '#e6a23c'
        
        reportHtml += `
          <div class="angle-item" style="margin-bottom: 8px;">
            <div class="angle-header">
              <span>${status} ${angleName}</span>
              <span style="color: ${barColor}; font-weight: bold;">${count}张</span>
            </div>
            <div class="angle-bar">
              <div class="angle-bar-fill" style="width: ${percentage}%; background: ${barColor};"></div>
            </div>
          </div>
        `
      }
    } else {
      reportHtml += '<p style="color: #909399; text-align: center;">⚠️ 暂无角度数据</p>'
    }
    
    reportHtml += `</div></div>`
    
    // 问题列表
    if (report.issues && report.issues.length > 0) {
      reportHtml += `
        <div class="report-section">
          <p class="report-section-title" style="color: #f56c6c;">⚠️ 发现的问题 (${report.issues.length})</p>
          <div class="issues-list">`
      
      report.issues.forEach((issue, index) => {
        reportHtml += `<div>• ${issue}</div>`
      })
      
      reportHtml += `</div></div>`
    }
    
    // 建议列表
    if (report.recommendations && report.recommendations.length > 0) {
      reportHtml += `
        <div class="report-section">
          <p class="report-section-title" style="color: #67c23a;">💡 改进建议 (${report.recommendations.length})</p>
          <div class="recommendations-list">`
      
      report.recommendations.forEach((rec, index) => {
        reportHtml += `<div>• ${rec}</div>`
      })
      
      reportHtml += `</div></div>`
    }
    
    reportHtml += `</div>`
    
    // 显示详细报告对话框
    await ElMessageBox.alert(reportHtml, t('dataset.validate'), {
      dangerouslyUseHTMLString: true,
      confirmButtonText: t('common.confirm'),
      type: report.quality_score >= 60 ? 'success' : 'warning',
    })
    
    loadDatasets()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(t('dataset.validate_failed'))
    }
  }
}

const handleAugment = (row) => {
  currentAugmentDatasetId.value = row.id
  augmentForm.factor = 2
  augmentForm.strategies = []
  augmentDialogVisible.value = true
}

const handleAugmentConfirm = async () => {
  augmenting.value = true
  try {
    const res = await augmentDataset(currentAugmentDatasetId.value, {
      augmentation_factor: augmentForm.factor,
      strategies: augmentForm.strategies.length > 0 ? augmentForm.strategies : null,
    })
    ElMessage.success(res.message)
    augmentDialogVisible.value = false
    loadDatasets()
  } catch (error) {
    ElMessage.error(t('dataset.augment_failed'))
  } finally {
    augmenting.value = false
  }
}

// Quality filter handlers
const handleFilterQuality = (row) => {
  currentFilterDatasetId.value = row.id
  filterForm.threshold = 30
  filterForm.action = 'mark'
  filterDialogVisible.value = true
}

const handleFilterConfirm = async () => {
  try {
    const actionText = filterForm.action === 'delete' ? t('dataset.action_delete') : t('dataset.action_mark')
    await ElMessageBox.confirm(
      t('dataset.confirm_filter', { action: actionText, threshold: filterForm.threshold }),
      t('common.confirm'),
      {
        confirmButtonText: t('common.confirm'),
        cancelButtonText: t('common.cancel'),
        type: 'warning',
      }
    )
    
    filtering.value = true
    const res = await filterLowQualityImages(currentFilterDatasetId.value, {
      threshold: filterForm.threshold,
      action: filterForm.action,
    })
    
    ElMessage.success(t('dataset.filter_success', { count: res.data.affected_count || 0 }))
    filterDialogVisible.value = false
    loadDatasets()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(t('dataset.evaluate_quality_failed'))
    }
  } finally {
    filtering.value = false
  }
}

const handleCreateVersion = async (row) => {
  try {
    await ElMessageBox.confirm(t('dataset.confirm_create_version'), t('dataset.create_version'), {
      confirmButtonText: t('common.confirm'),
      cancelButtonText: t('common.cancel'),
      type: 'info',
    })

    const res = await createDatasetVersion(row.id)
    ElMessage.success(t('dataset.version_created', { version: res.data.version }))
    loadDatasets()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(t('dataset.create_version_failed'))
    }
  }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(
      t('common.confirm_delete'),
      t('dataset.delete'),
      {
        confirmButtonText: t('common.confirm'),
        cancelButtonText: t('common.cancel'),
        type: 'warning',
      }
    )

    await deleteDataset(row.id)
    ElMessage.success(t('common.delete_success'))
    loadDatasets()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(t('common.delete_failed'))
    }
  }
}

const getIpName = (ipId) => {
  const ip = ipList.value.find(i => i.id === ipId)
  return ip ? ip.name : '-'
}

const getStatusType = (status) => {
  const types = {
    pending: '',
    validating: 'warning',
    ready: 'success',
    training: 'primary',
    archived: 'info',
  }
  return types[status] || ''
}

const getStatusLabel = (status) => {
  const labels = {
    pending: '待处理',
    validating: '验证中',
    ready: '就绪',
    training: '训练中',
    archived: '已归档',
  }
  return labels[status] || status
}

const getQualityColor = (score) => {
  if (score >= 85) return '#67C23A'
  if (score >= 70) return '#E6A23C'
  return '#F56C6C'
}

// Load IP list on mount (useAsyncList auto-loads datasets)
loadIpList()
</script>

<style scoped>
.dataset-page {
  padding: 20px;
}

.page-title {
  margin: 0 0 20px 0;
  font-size: 24px;
  font-weight: 600;
  color: #303133;
}

.dataset-detail {
  padding: 10px 0;
}

.angle-coverage {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

:deep(.el-upload-list--picture-card) {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

:deep(.el-upload--picture-card) {
  width: 100px;
  height: 100px;
}

:deep(.el-upload-list__item) {
  width: 100px;
  height: 100px;
}

/* Validation report styles */
.validation-report {
  text-align: left;
  padding: 10px;
}

.report-section {
  margin-bottom: 20px;
}

.report-section-title {
  font-weight: 600;
  color: #303133;
  margin-bottom: 10px;
  font-size: 14px;
}

.quality-score-bar {
  background: #f5f7fa;
  border-radius: 10px;
  padding: 10px;
  position: relative;
  height: 30px;
}

.quality-score-fill {
  height: 100%;
  border-radius: 10px;
  transition: width 0.3s ease;
}

.quality-score-text {
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  font-weight: 600;
  color: #303133;
}

.angle-item {
  flex: 1;
  min-width: 120px;
}

.angle-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 5px;
}

.angle-bar {
  background: #e4e7ed;
  border-radius: 4px;
  height: 8px;
  overflow: hidden;
}

.angle-bar-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.3s ease;
}

.issues-list {
  background: #fef0f0;
  border-left: 3px solid #f56c6c;
  padding: 12px;
  border-radius: 4px;
  margin-bottom: 10px;
}

.issues-list ul {
  margin: 8px 0 0 0;
  padding-left: 20px;
}

.issues-list li {
  margin: 4px 0;
  color: #f56c6c;
}

.recommendations-list {
  background: #f0f9ff;
  border-left: 3px solid #67c23a;
  padding: 12px;
  border-radius: 4px;
}

.recommendations-list ul {
  margin: 8px 0 0 0;
  padding-left: 20px;
}

.recommendations-list li {
  margin: 4px 0;
  color: #67c23a;
}
</style>
