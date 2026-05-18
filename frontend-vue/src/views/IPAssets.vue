<template>
  <div class="ip-page">
    <h1 class="page-title">{{ $t('ip.title') }}</h1>

    <!-- Toolbar -->
    <DataTable
      :data="filteredIPs"
      :loading="loading"
      :show-pagination="false"
    >
      <template #toolbar>
        <el-row :gutter="16" style="width: 100%;">
          <el-col :span="8">
            <el-input v-model="searchText" prefix-icon="Search" :placeholder="$t('common.search')" clearable />
          </el-col>
          <el-col :span="16" style="text-align:right;">
            <el-button type="primary" @click="openAddDialog">
              <el-icon><Plus /></el-icon> {{ $t('ip.create_asset') }}
            </el-button>
          </el-col>
        </el-row>
      </template>

      <template #default>
        <el-table-column prop="name" :label="$t('ip.name')" min-width="150" />
        <el-table-column prop="category" :label="$t('ip.category')" width="120">
          <template #default="{ row }">
            <el-tag size="small">{{ getCategoryLabel(row.category) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="trigger_word" :label="$t('ip.trigger_word')" width="140" />
        <el-table-column prop="style_template" :label="$t('ip.style_template')" width="120">
          <template #default="{ row }">
            <el-tag type="info" size="small">{{ getStyleLabel(row.style_template) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="description" :label="$t('ip.description')" min-width="200" show-overflow-tooltip />
        <el-table-column :label="$t('ip.reference_images')" width="120" align="center">
          <template #default="{ row }">
            <el-image
              v-if="checkRowHasImages(row)"
              :src="getFirstRefImageUrl(row.reference_images)"
              :preview-src-list="getRefImagePreviewList(row.reference_images)"
              style="width:40px;height:40px;border-radius:4px;"
              fit="cover"
            >
              <template #error>
                <span>{{ $t('common.none') }}</span>
              </template>
            </el-image>
            <span v-else>{{ $t('common.none') }}</span>
          </template>
        </el-table-column>
      </template>

      <template #actions="{ row }">
        <el-button size="small" type="primary" @click="openDetail(row)">
          <el-icon><View /></el-icon> {{ $t('common.view_detail') }}
        </el-button>
        <el-button size="small" type="warning" @click="openEditDialog(row)">
          <el-icon><Edit /></el-icon> {{ $t('common.edit') }}
        </el-button>
        <el-dropdown trigger="click">
          <el-button size="small">
            {{ $t('common.more') }}<el-icon class="el-icon--right"><arrow-down /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item @click="openThreeViewsDialog(row)" class="text-success">
                <el-icon><Picture /></el-icon> {{ $t('ip.generate_three_views') }}
              </el-dropdown-item>
              <el-dropdown-item divided @click="handleDelete(row, deleteIP)" class="text-danger">
                <el-icon><Delete /></el-icon> {{ $t('common.delete') }}
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </template>
    </DataTable>

    <!-- Add/Edit Dialog -->
    <CRUDDialog
      v-model="dialogVisible"
      :title="isEdit ? $t('ip.edit_asset') : $t('ip.create_asset')"
      width="650px"
      :form-data="ipForm"
      :rules="ipRules"
      label-width="100px"
      :loading="submitting"
      :confirm-text="isEdit ? $t('common.save') : $t('ip.create')"
      @submit="handleSubmit"
    >
      <template #default="{ formData }">
        <el-form-item :label="$t('ip.name')" prop="name">
          <el-input v-model="formData.name" />
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item :label="$t('ip.category')" prop="category">
              <el-select v-model="formData.category" :placeholder="$t('ip.select_category')" style="width:100%">
                <el-option :label="$t('ip.category_pet')" value="pet" />
                <el-option :label="$t('ip.category_human')" value="human" />
                <el-option :label="$t('ip.category_fantasy')" value="fantasy" />
                <el-option :label="$t('ip.category_other')" value="other" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item :label="$t('ip.style_template')">
              <el-select v-model="formData.style_template" style="width:100%">
                <el-option :label="$t('ip.style_3d_cartoon')" value="3d_cartoon" />
                <el-option :label="$t('ip.style_blind_box')" value="blind_box" />
                <el-option :label="$t('ip.style_healing')" value="healing" />
                <el-option :label="$t('ip.style_anime')" value="anime" />
                <el-option :label="$t('ip.style_realistic')" value="realistic" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item :label="$t('ip.trigger_word')" prop="trigger_word">
          <el-input v-model="formData.trigger_word" :placeholder="$t('ip.trigger_word_placeholder')" />
        </el-form-item>
        <el-form-item :label="$t('ip.description')">
          <el-input v-model="formData.description" type="textarea" :rows="3" :placeholder="$t('ip.description_placeholder')" />
        </el-form-item>
        <el-form-item :label="$t('ip.reference_images')">
          <ImageUploader
            ref="imageUploaderRef"
            v-model="formData.reference_images"
            :mode="isEdit ? 'edit' : 'create'"
            :limit="4"
            accept="image/*"
          />
        </el-form-item>
        <el-form-item :label="$t('ip.positive_tags')">
          <el-input v-model="formData.positive_tags" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item :label="$t('ip.negative_tags')">
          <el-input v-model="formData.negative_tags" type="textarea" :rows="2" />
        </el-form-item>
      </template>
    </CRUDDialog>

    <!-- Three Views Generation Dialog -->
    <el-dialog 
      v-model="threeViewsDialogVisible" 
      :title="$t('ip.generate_three_views_title')" 
      width="900px" 
      :close-on-click-modal="false"
      destroy-on-close
    >
      <div v-if="currentIP" class="three-views-container">
        <!-- IP Info -->
        <el-alert :closable="false" style="margin-bottom: 20px;">
          <template #title>
            <strong>{{ currentIP.name }}</strong> - {{ currentIP.description || $t('common.no_description') }}
          </template>
        </el-alert>

        <!-- Generation Parameters -->
        <el-card shadow="never" style="margin-bottom: 20px;">
          <template #header>
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <span style="font-weight: 600;">{{ $t('ip.generation_params') }}</span>
              <el-button size="small" text @click="showAdvancedParams = !showAdvancedParams">
                {{ showAdvancedParams ? $t('common.close') : $t('common.more') }}
              </el-button>
            </div>
          </template>
          
          <el-form :model="threeViewParams" label-width="120px" size="default">
            <!-- Key Parameters (always visible) -->
            <el-row :gutter="16">
              <el-col :span="8">
                <el-form-item :label="$t('ip.ip_adapter_scale')">
                  <el-slider v-model="threeViewParams.ip_adapter_scale" :min="0.5" :max="1.0" :step="0.05" show-input />
                  <div class="param-hint">
                    <el-icon><InfoFilled /></el-icon>
                    <span>{{ $t('ip.ip_adapter_scale_hint') }}</span>
                  </div>
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item :label="$t('ip.lora_weight')">
                  <el-slider v-model="threeViewParams.lora_weight" :min="0" :max="1" :step="0.1" show-input />
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item :label="$t('ip.steps')">
                  <el-input-number v-model="threeViewParams.steps" :min="20" :max="50" style="width: 100%" />
                </el-form-item>
              </el-col>
            </el-row>
            
            <!-- Advanced Parameters (collapsible) -->
            <el-collapse v-show="showAdvancedParams" style="margin-top: 12px;">
              <el-collapse-item :title="$t('ip.advanced_params')" name="advanced">
                <el-row :gutter="16">
                  <el-col :span="8">
                    <el-form-item :label="$t('ip.cfg_scale')">
                      <el-input-number v-model="threeViewParams.cfg_scale" :min="5" :max="15" :step="0.5" style="width: 100%" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="8">
                    <el-form-item :label="$t('ip.resolution')">
                      <el-select v-model="threeViewParams.resolution" style="width: 100%">
                        <el-option :label="$t('ip.resolutions.512')" :value="512" />
                        <el-option :label="$t('ip.resolutions.768')" :value="768" />
                      </el-select>
                    </el-form-item>
                  </el-col>
                </el-row>
              </el-collapse-item>
            </el-collapse>
          </el-form>
        </el-card>

        <!-- Generate Button -->
        <div style="text-align: center; margin-bottom: 20px;">
          <el-button 
            type="primary" 
            size="large" 
            @click="generateThreeViews"
            :loading="generating"
            :disabled="!hasReferenceImages"
          >
            {{ generating ? $t('common.generating') : $t('ip.start_generate_three_views') }}
          </el-button>
          <div v-if="!hasReferenceImages" style="color: #f56c6c; font-size: 12px; margin-top: 8px;">
            {{ $t('ip.upload_ref_images_first') }}
          </div>
        </div>

        <!-- Three Views Display -->
        <el-row :gutter="16">
          <el-col :span="8" v-for="view in viewTypes" :key="view.key">
            <el-card shadow="hover" class="view-card">
              <template #header>
                <div class="view-header">
                  <span class="view-title">{{ view.label }}</span>
                  <el-tag 
                    :type="viewStatus[view.key]?.type || 'info'" 
                    size="small"
                  >
                    {{ viewStatus[view.key]?.text || $t('ip.not_generated') }}
                  </el-tag>
                </div>
              </template>
              
              <div class="image-container">
                <el-image
                  v-if="viewImages[view.key]"
                  :src="viewImages[view.key]"
                  fit="contain"
                  :preview-src-list="[viewImages[view.key]]"
                  style="width: 100%; height: 300px;"
                >
                  <template #error>
                    <div class="image-error">
                      <el-icon><Picture /></el-icon>
                      <span>{{ $t('common.load_failed') }}</span>
                    </div>
                  </template>
                </el-image>
                <div v-else class="image-placeholder">
                  <el-icon :size="48"><Picture /></el-icon>
                  <span>{{ $t('ip.waiting_generation') }}</span>
                </div>
              </div>

              <!-- Progress -->
              <div v-if="viewProgress[view.key] !== undefined && viewProgress[view.key] < 100" class="progress-container">
                <el-progress 
                  :percentage="viewProgress[view.key]" 
                  :status="viewProgress[view.key] < 100 ? '' : 'success'"
                />
              </div>
            </el-card>
          </el-col>
        </el-row>

        <!-- Tips -->
        <el-alert 
          v-if="generationComplete" 
          :title="$t('ip.three_views_generated')" 
          type="success" 
          :closable="false"
          style="margin-top: 20px;"
        >
          <template #default>
            <div>{{ $t('ip.three_views_usage_hint') }}</div>
          </template>
        </el-alert>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { View, Picture, ArrowDown, Delete, InfoFilled, Edit } from '@element-plus/icons-vue'
import { getIPList, createIP, updateIP, deleteIP } from '@/api/ip'
import { deleteResource } from '@/api/resource'
import request from '@/api/request'
import { useDeleteConfirm } from '../composables/useDeleteConfirm'
import { useDebounce } from '../composables/useDebounce'
import { useAsyncData } from '@/composables/useAsyncData'
import { logger } from '../utils/logger'
import { getImageUrl } from '../utils/image'
import DataTable from '../components/common/DataTable.vue'
import ImageUploader from '../components/common/ImageUploader.vue'
import CRUDDialog from '../components/common/CRUDDialog.vue'

const router = useRouter()
const { t } = useI18n()

// Keep as ref for template reactivity
const ipAssets = ref([])

// Use useAsyncData for automatic data fetching
const { loading, execute: loadIPs } = useAsyncData(
  () => getIPList({ skip: 0, limit: 100 }),
  { 
    errorMessage: 'common.load_failed', 
    autoLoad: true,
    onSuccess: (result) => {
      // Unified response format: response.data.data
      ipAssets.value = result?.data?.data || []
    }
  }
)

const submitting = ref(false)
const searchText = ref('')
const debouncedSearchText = ref('')
const dialogVisible = ref(false)
const isEdit = ref(false)
const imageUploaderRef = ref(null)  // ImageUploader组件引用

// Timer for three views polling
let pollTimeoutId = null

// Three views state
const threeViewsDialogVisible = ref(false)
const currentIP = ref(null)
const generating = ref(false)
const viewImages = ref({ front: null, side: null, back: null })
const viewStatus = ref({ front: {}, side: {}, back: {} })
const viewProgress = ref({ front: 0, side: 0, back: 0 })
const viewTaskIds = ref({ front: null, side: null, back: null })
const generationComplete = ref(false)

// Three view generation parameters
const showAdvancedParams = ref(false)
const threeViewParams = ref({
  ip_adapter_scale: 0.85,
  lora_weight: 0.7,
  steps: 30,
  cfg_scale: 7.0,
  resolution: 512,
})

const viewTypes = computed(() => [
  { key: 'front', label: t('ip.view_front') },
  { key: 'side', label: t('ip.view_side') },
  { key: 'back', label: t('ip.view_back') }
])

const hasReferenceImages = computed(() => {
  return currentIP.value && 
         Array.isArray(currentIP.value.reference_images) && 
         currentIP.value.reference_images.length > 0
})

// Check if a row has reference images
function checkRowHasImages(row) {
  if (!row || !row.reference_images) return false
  if (Array.isArray(row.reference_images) && row.reference_images.length > 0) return true
  if (typeof row.reference_images === 'object' && row.reference_images.path) return true
  return false
}

// Get first reference image URL for thumbnail
function getFirstRefImageUrl(referenceImages) {
  if (!referenceImages) return ''
  
  // If it's an array, get the first element
  if (Array.isArray(referenceImages) && referenceImages.length > 0) {
    const firstImg = referenceImages[0]
    return getRefImageUrl(firstImg)
  }
  
  // If it's a single object
  if (typeof referenceImages === 'object' && referenceImages.path) {
    return getRefImageUrl(referenceImages.path)
  }
  
  return ''
}

// Get preview list for image gallery
function getRefImagePreviewList(referenceImages) {
  if (!referenceImages || !Array.isArray(referenceImages)) return []
  
  return referenceImages
    .map(img => getRefImageUrl(img))
    .filter(url => url !== '') // Remove empty URLs
}

const ipForm = ref({
  name: '', category: '', trigger_word: '', description: '',
  style_template: '', positive_tags: '', negative_tags: '',
  reference_images: [],
})

const ipRules = {
  name: [{ required: true, message: () => t('ip.name'), trigger: 'blur' }],
  category: [{ required: true, message: () => t('ip.select_category'), trigger: 'change' }],
  trigger_word: [{ required: true, message: () => t('ip.trigger_word'), trigger: 'blur' }],
}

// Debounce search to reduce filtering computations
const { debouncedFn: updateSearch } = useDebounce(() => {
  debouncedSearchText.value = searchText.value
}, 300)

// Watch searchText and apply debounce
watch(searchText, () => {
  updateSearch()
})

const filteredIPs = computed(() => {
  if (!debouncedSearchText.value) return ipAssets.value
  const s = debouncedSearchText.value.toLowerCase()
  return ipAssets.value.filter(ip =>
    ip.name?.toLowerCase().includes(s) || ip.trigger_word?.toLowerCase().includes(s)
  )
})

const categoryMap = { pet: 'ip.category_pet', human: 'ip.category_human', fantasy: 'ip.category_fantasy', other: 'ip.category_other' }
const styleMap = { '3d_cartoon': 'ip.style_3d_cartoon', blind_box: 'ip.style_blind_box', healing: 'ip.style_healing', anime: 'ip.style_anime', realistic: 'ip.style_realistic' }

function getCategoryLabel(cat) { return t(categoryMap[cat] || cat) }
function getStyleLabel(style) { return t(styleMap[style] || style) }

function getRefImageUrl(imgPath) {
  // Handle object format: { angle: 'front', path: '/placeholder.jpg' }
  if (imgPath && typeof imgPath === 'object' && imgPath.path) {
    imgPath = imgPath.path;
  }
  
  if (!imgPath || typeof imgPath !== 'string' || imgPath === '/placeholder.jpg') {
    return ''
  }
  
  try {
    // 新资源路径格式: data/resources/2026/05/17/xxx.jpg
    if (imgPath.startsWith('data/resources/')) {
      const encodedPath = encodeURIComponent(imgPath)
      return `/api/v1/resources/${encodedPath}`
    }
    
    // 旧路径格式: data/ip_assets/xxx.jpg (向后兼容)
    let cleanPath = imgPath;
    
    // 如果是完整URL，提取路径部分
    if (imgPath.startsWith('http://') || imgPath.startsWith('https://')) {
      try {
        const url = new URL(imgPath);
        cleanPath = url.pathname;
      } catch (e) {
        // 如果URL解析失败，使用原始路径
      }
    }
    
    // 替换Windows反斜杠
    cleanPath = cleanPath.replace(/\\/g, '/');
    
    // 移除前导斜杠
    if (cleanPath.startsWith('/')) {
      cleanPath = cleanPath.substring(1);
    }
    
    // 提取最后两个段用于文件
    const parts = cleanPath.split('/').filter(p => p.length > 0);
    if (parts.length >= 2) {
      const result = `/api/v1/generate/files/${parts[parts.length - 2]}/${parts[parts.length - 1]}`;
      return result;
    } else if (parts.length === 1) {
      const result = `/api/v1/generate/files/${parts[0]}`;
      return result;
    } else {
      return '';
    }
  } catch (error) {
    logger.error('[IPAssets] Failed to get reference image URL:', error)
    return ''
  }
}

// loadIPs is now provided by useAsyncData

function openDetail(row) {
  router.push(`/ip/${row.id}`)
}

function openAddDialog() {
  isEdit.value = false
  Object.assign(ipForm.value, {
    id: undefined,
    name: '',
    category: '',
    trigger_word: '',
    description: '',
    style_template: '',
    positive_tags: '',
    negative_tags: '',
    reference_images: [],
  })
  dialogVisible.value = true
}

function openEditDialog(row) {
  if (!row) {
    ElMessage.error('Invalid IP asset selected for editing')
    return
  }
  if (!row.id) {
    ElMessage.error('IP asset ID is missing. Cannot edit.')
    return
  }
  
  // 清空上一个编辑的待删除状态，防止状态残留
  if (imageUploaderRef.value) {
    imageUploaderRef.value.clearPendingDeletePaths()
  }
  
  isEdit.value = true
  Object.assign(ipForm.value, {
    id: row.id,
    name: row.name || '',
    category: row.category || '',
    trigger_word: row.trigger_word || '',
    description: row.description || '',
    style_template: row.style_template || '',
    positive_tags: row.positive_tags || '',
    negative_tags: row.negative_tags || '',
    reference_images: row.reference_images || [],
  })
  dialogVisible.value = true
}

async function handleSubmit(formData) {
  submitting.value = true
  try {
    // 编辑模式：准备延迟删除的路径（但不立即删除）
    let pathsToDelete = []
    if (isEdit.value && imageUploaderRef.value) {
      pathsToDelete = imageUploaderRef.value.getPendingDeletePaths() || []
    }
    
    // formData.reference_images已经是路径数组，直接提交
    const payload = { ...formData }
    delete payload.id
    
    // Convert empty strings to null for list fields
    if (payload.positive_tags === '') payload.positive_tags = null
    if (payload.negative_tags === '') payload.negative_tags = null
    
    // 1. 先更新数据库
    if (isEdit.value) {
      await updateIP(formData.id, payload)
      ElMessage.success(t('ip.update_success'))
    } else {
      await createIP(payload)
      ElMessage.success(t('ip.add_success'))
    }
    
    // 2. 数据库更新成功后，再删除文件
    if (isEdit.value && pathsToDelete.length > 0) {
      for (const path of pathsToDelete) {
        try {
          await deleteResource(path)
        } catch (error) {
          // 文件删除失败不影响数据一致性，仅记录警告
          logger.warn('[IPAssets] Failed to delete resource after update:', path, error)
        }
      }
      
      // 3. 清空待删除列表
      if (imageUploaderRef.value) {
        imageUploaderRef.value.clearPendingDeletePaths()
      }
    }
    
    dialogVisible.value = false
    loadIPs()
  } catch (err) {
    logger.error('[IPAssets] Submit error:', err)
    ElMessage.error(err.response?.data?.detail || err.message || 'Operation failed')
    // 注意：如果失败，pendingDeletePaths保持不变，用户可重新尝试保存
  } finally {
    submitting.value = false
  }
}

// Delete IP with confirmation
const handleDelete = useDeleteConfirm(loadIPs, 'ip.delete_success')

// Three Views Functions
function openThreeViewsDialog(row) {
  currentIP.value = row
  threeViewsDialogVisible.value = true
  // Reset state
  viewImages.value = { front: null, side: null, back: null }
  viewStatus.value = { front: {}, side: {}, back: {} }
  viewProgress.value = { front: 0, side: 0, back: 0 }
  viewTaskIds.value = { front: null, side: null, back: null }
  generationComplete.value = false
  
  // Reset generation parameters to defaults
  threeViewParams.value = {
    ip_adapter_scale: 0.85,
    lora_weight: 0.7,
    steps: 30,
    cfg_scale: 7.0,
    resolution: 512,
  }
  showAdvancedParams.value = false
}

async function generateThreeViews() {
  if (!currentIP.value || !hasReferenceImages.value) {
    ElMessage.warning(t('ip.upload_ref_images_first'))
    return
  }

  generating.value = true
  generationComplete.value = false
  
  try {
    // Call API to generate three views with parameters
    const { data } = await request.post(`/ip/${currentIP.value.id}/generate-three-views`, {
      ip_adapter_scale: threeViewParams.value.ip_adapter_scale,
      lora_weight: threeViewParams.value.lora_weight,
      steps: threeViewParams.value.steps,
      cfg_scale: threeViewParams.value.cfg_scale,
      width: threeViewParams.value.resolution,
      height: threeViewParams.value.resolution,
    })
    
    if (!data.success) {
      throw new Error(data.message || t('common.generation_failed'))
    }
    
    ElMessage.success(t('ip.three_views_generated'))
    
    // Store task IDs
    viewTaskIds.value = data.data.task_ids
    
    // Start polling for task status
    pollTaskStatus(data.data.task_ids)
    
  } catch (err) {
    ElMessage.error(err.response?.data?.message || err.message || t('common.generation_failed'))
    generating.value = false
  }
}

async function pollTaskStatus(taskIds) {
  const maxAttempts = 120 // 120 * 3s = 6 minutes max
  let attempts = 0
  
  const poll = async () => {
    if (attempts >= maxAttempts) {
      ElMessage.warning(t('common.generation_failed'))
      generating.value = false
      return
    }
    
    attempts++
    
    let allComplete = true
    
    for (const [viewName, taskId] of Object.entries(taskIds)) {
      // Skip if already completed
      if (viewImages.value[viewName]) {
        continue
      }
      
      allComplete = false
      
      try {
        const { data } = await request.get(`/tasks/${taskId}`)
        
        if (data.data) {
          const task = data.data
          
          if (task.status === 'completed') {
            // Update image
            viewImages.value[viewName] = getImageUrl(task.result_path)
            viewStatus.value[viewName] = { text: t('status.completed'), type: 'success' }
            viewProgress.value[viewName] = 100
          } else if (task.status === 'failed') {
            viewStatus.value[viewName] = { text: t('status.failed'), type: 'danger' }
            viewProgress.value[viewName] = 0
          } else if (task.status === 'running') {
            viewStatus.value[viewName] = { text: t('common.generating'), type: 'warning' }
            viewProgress.value[viewName] = task.progress || 10
          } else {
            viewStatus.value[viewName] = { text: t('status.pending'), type: 'info' }
            viewProgress.value[viewName] = 0
          }
        }
      } catch (err) {
        // Task not found yet - might be creating, just log and continue polling
        if (err.response?.data?.error?.error === 'NotFoundError') {
          logger.debug(`[ThreeViews] Task ${taskId} not ready yet, will retry...`)
          viewStatus.value[viewName] = { text: t('status.pending'), type: 'info' }
          viewProgress.value[viewName] = 0
        } else {
          if (import.meta.env.DEV) {
            console.error(`[ThreeViews] Failed to poll task ${taskId}:`, err)
          }
        }
      }
    }
    
    // Check if all views are complete
    const completeCount = Object.values(viewImages.value).filter(v => v !== null).length
    if (completeCount === 3) {
      generationComplete.value = true
      generating.value = false
      ElMessage.success(t('ip.three_views_generated'))
      return
    }
    
    // Continue polling
    pollTimeoutId = setTimeout(poll, 3000)
  }
  
  poll()
}

// 使用统一的 getImageUrl 工具函数
// 已移至 utils/image.js

// useAsyncData auto-loads on mount, only clean up polling timer on unmount

onUnmounted(() => {
  // Clean up polling timer when component is destroyed
  if (pollTimeoutId) {
    clearTimeout(pollTimeoutId)
    pollTimeoutId = null
  }
})
</script>

<style scoped>
.ip-page { padding: 0; }
.page-title { font-size: 24px; font-weight: 700; color: #303133; margin: 0 0 20px; }

/* Three Views Dialog Styles */
.three-views-container {
  padding: 10px;
}

.view-card {
  margin-bottom: 16px;
}

.view-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.view-title {
  font-weight: 600;
  font-size: 14px;
}

.image-container {
  width: 100%;
  height: 300px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f7fa;
  border-radius: 4px;
  overflow: hidden;
}

.image-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #909399;
  gap: 8px;
}

.image-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #f56c6c;
  gap: 8px;
}

.progress-container {
  margin-top: 12px;
}

/* Parameter hint style */
.param-hint {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 8px;
  font-size: 12px;
  color: #909399;
  line-height: 1.4;
}
.param-hint .el-icon {
  flex-shrink: 0;
}
</style>
