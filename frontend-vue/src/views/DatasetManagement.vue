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
            <el-select v-model="filterIpId" placeholder="选择IP资产" clearable @change="loadDatasets">
              <el-option label="全部" :value="null" />
              <el-option v-for="ip in ipList" :key="ip.id" :label="ip.name" :value="ip.id" />
            </el-select>
          </el-col>
          <el-col :span="6">
            <el-select v-model="filterStatus" placeholder="状态" clearable @change="loadDatasets">
              <el-option label="全部" :value="null" />
              <el-option label="待处理" value="pending" />
              <el-option label="验证中" value="validating" />
              <el-option label="就绪" value="ready" />
              <el-option label="训练中" value="training" />
              <el-option label="已归档" value="archived" />
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
        <el-table-column prop="name" label="数据集名称" min-width="180" />
        <el-table-column label="IP资产" width="150">
          <template #default="{ row }">
            {{ getIpName(row.ip_asset_id) }}
          </template>
        </el-table-column>
        <el-table-column label="图片数量" width="120" align="center">
          <template #default="{ row }">
            <el-tag size="small">{{ row.image_count }} 张</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="增强数量" width="120" align="center">
          <template #default="{ row }">
            <el-tag size="small" type="info">{{ row.augmented_count }} 张</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="质量评分" width="120" align="center">
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
        <el-table-column prop="status" label="状态" width="120" align="center">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">
              {{ getStatusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="version" label="版本" width="80" align="center" />
      </template>

      <template #actions="{ row }">
        <el-button size="small" type="primary" @click="openDetailDialog(row)">详情</el-button>
        <el-dropdown trigger="click" style="margin-left: 8px;">
          <el-button size="small">
            更多<el-icon class="el-icon--right"><arrow-down /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item @click="handleValidate(row)">
                <el-icon><Check /></el-icon> 验证数据集
              </el-dropdown-item>
              <el-dropdown-item @click="handleAugment(row)">
                <el-icon><MagicStick /></el-icon> 数据增强
              </el-dropdown-item>
              <el-dropdown-item @click="handleCreateVersion(row)">
                <el-icon><DocumentCopy /></el-icon> 创建版本
              </el-dropdown-item>
              <el-dropdown-item divided @click="handleDelete(row)" class="text-danger">
                <el-icon><Delete /></el-icon> 删除
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </template>
    </DataTable>

    <!-- Create Dataset Dialog -->
    <el-dialog v-model="createDialogVisible" title="创建训练数据集" width="700px">
      <el-alert
        title="数据集创建流程"
        type="info"
        :closable="false"
        style="margin-bottom: 20px;"
      >
        <template #default>
          <div style="font-size: 13px; line-height: 1.6;">
            <strong>步骤 1:</strong> 填写数据集基本信息<br/>
            <strong>步骤 2:</strong> 上传 15-30 张训练图片<br/>
            <strong>步骤 3:</strong> 标注图片（角度、表情、姿势）<br/>
            <strong>步骤 4:</strong> 验证数据集质量
          </div>
        </template>
      </el-alert>

      <el-form ref="createFormRef" :model="createForm" :rules="createRules" label-width="120px">
        <el-form-item label="IP资产" prop="ip_asset_id">
          <el-select v-model="createForm.ip_asset_id" placeholder="选择IP资产" style="width:100%">
            <el-option v-for="ip in ipList" :key="ip.id" :label="ip.name" :value="ip.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="数据集名称" prop="name">
          <el-input v-model="createForm.name" placeholder="例如：我的角色数据集 v1" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="createForm.description"
            type="textarea"
            :rows="3"
            placeholder="数据集描述（可选）"
          />
        </el-form-item>

        <el-divider>图片上传</el-divider>

        <el-form-item label="训练图片">
          <el-upload
            ref="uploadRef"
            :auto-upload="false"
            :multiple="true"
            :limit="50"
            accept="image/jpeg,image/png,image/webp"
            list-type="picture-card"
            v-model:file-list="uploadFileList"
            :on-change="handleFileChange"
            :on-remove="handleFileRemove"
          >
            <el-icon><Plus /></el-icon>
            <template #tip>
              <div class="el-upload__tip">
                支持 JPG/PNG/WEBP 格式，最多上传 50 张图片<br/>
                建议：15-30 张高质量图片，包含不同角度、表情和姿势
              </div>
            </template>
          </el-upload>
          
          <div v-if="uploadFileList.length > 0" style="margin-top: 12px; padding: 12px; background: #f0f9ff; border-radius: 4px;">
            <el-icon style="color: #409eff; vertical-align: middle;"><InfoFilled /></el-icon>
            <span style="margin-left: 8px; color: #606266;">
              已选择 <strong style="color: #409eff;">{{ uploadFileList.length }}</strong> 张图片
              <span v-if="uploadFileList.length < 15" style="color: #E6A23C; margin-left: 8px;">
                （建议至少 15 张）
              </span>
              <span v-else-if="uploadFileList.length >= 15 && uploadFileList.length <= 30" style="color: #67C23A; margin-left: 8px;">
                ✓ 数量合适
              </span>
              <span v-else style="color: #F56C6C; margin-left: 8px;">
                （超过 30 张，可能训练较慢）
              </span>
            </span>
          </div>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleCreate" :loading="creating">
          创建并上传图片
        </el-button>
      </template>
    </el-dialog>

    <!-- Dataset Detail Dialog -->
    <el-dialog v-model="detailDialogVisible" title="数据集详情" width="900px">
      <div v-if="currentDataset" class="dataset-detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="数据集名称">{{ currentDataset.name }}</el-descriptions-item>
          <el-descriptions-item label="IP资产">{{ getIpName(currentDataset.ip_asset_id) }}</el-descriptions-item>
          <el-descriptions-item label="图片数量">{{ currentDataset.image_count }} 张</el-descriptions-item>
          <el-descriptions-item label="增强数量">{{ currentDataset.augmented_count }} 张</el-descriptions-item>
          <el-descriptions-item label="质量评分">{{ currentDataset.quality_score || '-' }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusType(currentDataset.status)">
              {{ getStatusLabel(currentDataset.status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="版本">v{{ currentDataset.version }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ currentDataset.created_at }}</el-descriptions-item>
        </el-descriptions>

        <el-divider>角度覆盖</el-divider>
        <div v-if="currentDataset.angle_coverage" class="angle-coverage">
          <el-tag
            v-for="(count, angle) in currentDataset.angle_coverage"
            :key="angle"
            style="margin: 4px;"
          >
            {{ angle }}: {{ count }} 张
          </el-tag>
        </div>
        <el-empty v-else description="暂无角度数据" :image-size="80" />
      </div>
    </el-dialog>

    <!-- Augment Dialog -->
    <el-dialog v-model="augmentDialogVisible" title="数据增强" width="600px">
      <el-form :model="augmentForm" label-width="150px">
        <el-form-item label="增强倍数">
          <el-slider v-model="augmentForm.factor" :min="1" :max="5" :step="1" show-input />
        </el-form-item>
        <el-form-item label="增强策略">
          <el-checkbox-group v-model="augmentForm.strategies">
            <el-checkbox label="horizontal_flip">水平翻转</el-checkbox>
            <el-checkbox label="rotation">旋转</el-checkbox>
            <el-checkbox label="brightness">亮度调整</el-checkbox>
            <el-checkbox label="contrast">对比度调整</el-checkbox>
            <el-checkbox label="color_jitter">颜色抖动</el-checkbox>
          </el-checkbox-group>
          <div style="color: #909399; font-size: 12px; margin-top: 8px;">
            留空将随机选择1-2种策略
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="augmentDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleAugmentConfirm" :loading="augmenting">开始增强</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, ArrowDown, Check, MagicStick, DocumentCopy, Delete, InfoFilled } from '@element-plus/icons-vue'
import DataTable from '@/components/common/DataTable.vue'
import {
  getDatasetList,
  createDataset,
  deleteDataset,
  validateDataset,
  augmentDataset,
  createDatasetVersion,
  getDatasetDetail,
  uploadDatasetImages,
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
const createFormRef = ref(null)
const uploadRef = ref(null)
const creating = ref(false)
const uploadFileList = ref([])
const createForm = reactive({
  ip_asset_id: null,
  name: '',
  description: '',
})
const createRules = {
  ip_asset_id: [{ required: true, message: '请选择IP资产', trigger: 'change' }],
  name: [{ required: true, message: '请输入数据集名称', trigger: 'blur' }],
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
const currentAugmentDatasetId = ref(null)

// Load IP list
const loadIpList = async () => {
  try {
    const res = await getIPList({ limit: 100 })
    ipList.value = res.data.data || []
  } catch (error) {
    if (import.meta.env.DEV) {
      console.error('Failed to load IP list:', error)
    }
  }
}

const openCreateDialog = () => {
  createDialogVisible.value = true
  createForm.ip_asset_id = null
  createForm.name = ''
  createForm.description = ''
  uploadFileList.value = []
}

const handleFileChange = (file, fileList) => {
  uploadFileList.value = fileList
}

const handleFileRemove = (file, fileList) => {
  uploadFileList.value = fileList
}

const handleCreate = async () => {
  if (!createFormRef.value) return
  await createFormRef.value.validate(async (valid) => {
    if (!valid) return

    if (uploadFileList.value.length === 0) {
      ElMessage.warning('请至少上传一张图片')
      return
    }

    creating.value = true
    try {
      // Step 1: Create dataset
      const res = await createDataset(createForm)
      const datasetId = res.data.id || res.data.data?.id
      
      ElMessage.success('数据集创建成功，正在上传图片...')
      
      // Step 2: Upload images
      if (uploadFileList.value.length > 0) {
        const files = uploadFileList.value.map(f => f.raw).filter(Boolean)
        await uploadDatasetImages(datasetId, files)
        ElMessage.success(`成功上传 ${files.length} 张图片`)
      }
      
      createDialogVisible.value = false
      loadDatasets()
      
      // Step 3: Redirect to annotation page
      ElMessageBox.confirm(
        '图片上传成功！是否前往标注页面为图片添加标注信息（角度、表情、姿势）？',
        '前往标注',
        {
          confirmButtonText: '去标注',
          cancelButtonText: '稍后标注',
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
      if (import.meta.env.DEV) {
        console.error('Create dataset error:', error)
      }
      ElMessage.error(error.message || t('dataset.create_failed'))
    } finally {
      creating.value = false
    }
  })
}

const openDetailDialog = async (row) => {
  try {
    const res = await getDatasetDetail(row.id, { include_images: false })
    currentDataset.value = res.data
    detailDialogVisible.value = true
  } catch (error) {
    ElMessage.error(t('dataset.detail_load_failed'))
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
    ElMessage.success(t('dataset.validate_success', { score: res.data.quality_score }))
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

const handleCreateVersion = async (row) => {
  try {
    await ElMessageBox.confirm('确定要创建新版本吗？', '创建版本', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'info',
    })

    const res = await createDatasetVersion(row.id)
    ElMessage.success(`版本 v${res.data.version} 创建成功`)
    loadDatasets()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('创建版本失败')
    }
  }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(`确定要删除数据集 "${row.name}" 吗？此操作不可恢复！`, '删除数据集', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })

    await deleteDataset(row.id)
    ElMessage.success('数据集已删除')
    loadDatasets()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
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
</style>
