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
        <el-button size="small" type="warning" @click="openEditDialog(row)">{{ $t('common.edit') }}</el-button>
        <el-dropdown trigger="click" style="margin-left: 8px;">
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
    <el-dialog v-model="dialogVisible" :title="isEdit ? $t('ip.edit_asset') : $t('ip.create_asset')" width="650px" destroy-on-close>
      <el-form ref="ipFormRef" :model="ipForm" :rules="ipRules" label-width="100px">
        <el-form-item :label="$t('ip.name')" prop="name">
          <el-input v-model="ipForm.name" />
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item :label="$t('ip.category')" prop="category">
              <el-select v-model="ipForm.category" :placeholder="$t('ip.select_category')" style="width:100%">
                <el-option :label="$t('ip.category_pet')" value="pet" />
                <el-option :label="$t('ip.category_human')" value="human" />
                <el-option :label="$t('ip.category_fantasy')" value="fantasy" />
                <el-option :label="$t('ip.category_other')" value="other" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item :label="$t('ip.style_template')">
              <el-select v-model="ipForm.style_template" style="width:100%">
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
          <el-input v-model="ipForm.trigger_word" :placeholder="$t('ip.trigger_word_placeholder')" />
        </el-form-item>
        <el-form-item :label="$t('ip.description')">
          <el-input v-model="ipForm.description" type="textarea" :rows="3" :placeholder="$t('ip.description_placeholder')" />
        </el-form-item>
        <el-form-item :label="$t('ip.reference_images')">
          <el-upload
            :file-list="fileList"
            :auto-upload="false"
            list-type="picture-card"
            :limit="4"
            accept="image/*"
            :on-change="handleFileChange"
            :on-remove="handleFileRemove"
          >
            <el-icon><Plus /></el-icon>
          </el-upload>
        </el-form-item>
        <el-form-item :label="$t('ip.positive_tags')">
          <el-input v-model="ipForm.positive_tags" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item :label="$t('ip.negative_tags')">
          <el-input v-model="ipForm.negative_tags" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">
          {{ isEdit ? $t('common.save') : $t('ip.create') }}
        </el-button>
      </template>
    </el-dialog>

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
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { Picture, ArrowDown, Delete } from '@element-plus/icons-vue'
import { getIPList, createIP, updateIP, deleteIP, uploadFile } from '../api/ip'
import request from '../api/request'
import { useDeleteConfirm } from '../composables/useDeleteConfirm'
import { useDebounce } from '../composables/useDebounce'
import { logger } from '../utils/logger'
import DataTable from '../components/common/DataTable.vue'

const { t } = useI18n()

const loading = ref(false)
const submitting = ref(false)
const ipAssets = ref([])
const searchText = ref('')
const debouncedSearchText = ref('')
const dialogVisible = ref(false)
const isEdit = ref(false)
const ipFormRef = ref(null)
const fileList = ref([])
const pendingFiles = ref([])

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
    // Handle both relative paths and full URLs
    let cleanPath = imgPath;

    // If it's a full URL, extract the path part
    if (imgPath.startsWith('http://') || imgPath.startsWith('https://')) {
      try {
        const url = new URL(imgPath);
        cleanPath = url.pathname;
      } catch (e) {
        // If URL parsing fails, use original path
      }
    }

    // Replace Windows backslashes with forward slashes
    cleanPath = cleanPath.replace(/\\/g, '/');

    // Remove leading slash if present
    if (cleanPath.startsWith('/')) {
      cleanPath = cleanPath.substring(1);
    }

    // Extract the last two segments for files
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

async function loadIPs() {
  loading.value = true
  try {
    const { data } = await getIPList({ skip: 0, limit: 100 })
    // Unified response format
    ipAssets.value = data.data || []
  } catch (err) {
    logger.error('[IPAssets] Load error:', err)
    ElMessage.error('Failed to load IP assets')
  } finally {
    loading.value = false
  }
}

function handleFileChange(file, uploadFileList) {
  pendingFiles.value = uploadFileList
}

function handleFileRemove(file, uploadFileList) {
  pendingFiles.value = uploadFileList
}

function openAddDialog() {
  isEdit.value = false
  ipForm.value = {
    name: '', category: '', trigger_word: '', description: '',
    style_template: '', positive_tags: '', negative_tags: '', reference_images: [],
  }
  fileList.value = []
  pendingFiles.value = []
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
  isEdit.value = true
  ipForm.value = {
    id: row.id,
    name: row.name || '',
    category: row.category || '',
    trigger_word: row.trigger_word || '',
    description: row.description || '',
    style_template: row.style_template || '',
    positive_tags: row.positive_tags || '',
    negative_tags: row.negative_tags || '',
    reference_images: row.reference_images || [],
  }
  
  // Convert reference images to fileList format for el-upload
  // Handle both string paths and object format {angle, path}
  const refImages = row.reference_images || []
  
  fileList.value = refImages.map((img, i) => {
    let imgPath = img
    
    // If it's an object, extract the path
    if (typeof img === 'object' && img !== null && img.path) {
      imgPath = img.path
    }
    
    const imageUrl = getRefImageUrl(imgPath)
    
    return {
      name: `image-${i}`,
      url: imageUrl,
      status: 'success',
    }
  })
  
  pendingFiles.value = []
  dialogVisible.value = true
}

async function handleSubmit() {
  const valid = await ipFormRef.value?.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    logger.debug('[IPAssets] Submit - ipForm.reference_images:', ipForm.value.reference_images)
    logger.debug('[IPAssets] Submit - pendingFiles:', pendingFiles.value)
    
    // Upload new files first
    const uploadedPaths = [...(ipForm.value.reference_images || [])]
    logger.debug('[IPAssets] Submit - initial uploadedPaths:', uploadedPaths)
    
    for (const file of pendingFiles.value) {
      if (file.raw && file.status !== 'success') {
        const fd = new FormData()
        fd.append('file', file.raw)
        const { data } = await uploadFile(fd)
        // Unified response format
        logger.debug('[IPAssets] Submit - upload response:', data)
        if (data.data?.file_path) {
          uploadedPaths.push(data.data.file_path)
          logger.debug('[IPAssets] Submit - added path:', data.data.file_path)
        }
      }
    }

    logger.debug('[IPAssets] Submit - final uploadedPaths:', uploadedPaths)
    
    const payload = { ...ipForm.value, reference_images: uploadedPaths }
    delete payload.id

    logger.debug('[IPAssets] Submit - payload:', payload)

    // Convert empty strings to null for list fields
    if (payload.positive_tags === '') payload.positive_tags = null
    if (payload.negative_tags === '') payload.negative_tags = null

    if (isEdit.value) {
      await updateIP(ipForm.value.id, payload)
      ElMessage.success(t('ip.update_success'))
    } else {
      await createIP(payload)
      ElMessage.success(t('ip.add_success'))
    }
    dialogVisible.value = false
    loadIPs()
  } catch (err) {
    console.error('[IPAssets] Submit error:', err)
    ElMessage.error(err.response?.data?.detail || 'Operation failed')
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
}

async function generateThreeViews() {
  if (!currentIP.value || !hasReferenceImages.value) {
    ElMessage.warning($t('ip.upload_ref_images_first'))
    return
  }

  generating.value = true
  generationComplete.value = false
  
  try {
    // Call API to generate three views
    const { data } = await request.post(`/ip/${currentIP.value.id}/generate-three-views`)
    
    if (!data.success) {
      throw new Error(data.message || $t('common.generation_failed'))
    }
    
    ElMessage.success($t('ip.three_views_generated'))
    
    // Store task IDs
    viewTaskIds.value = data.data.task_ids
    
    // Start polling for task status
    pollTaskStatus(data.data.task_ids)
    
  } catch (err) {
    ElMessage.error(err.response?.data?.message || err.message || $t('common.generation_failed'))
    generating.value = false
  }
}

async function pollTaskStatus(taskIds) {
  const maxAttempts = 120 // 120 * 3s = 6 minutes max
  let attempts = 0
  
  const poll = async () => {
    if (attempts >= maxAttempts) {
      ElMessage.warning($t('common.generation_failed'))
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
            viewStatus.value[viewName] = { text: $t('status.completed'), type: 'success' }
            viewProgress.value[viewName] = 100
          } else if (task.status === 'failed') {
            viewStatus.value[viewName] = { text: $t('status.failed'), type: 'danger' }
            viewProgress.value[viewName] = 0
          } else if (task.status === 'running') {
            viewStatus.value[viewName] = { text: $t('common.generating'), type: 'warning' }
            viewProgress.value[viewName] = task.progress || 10
          } else {
            viewStatus.value[viewName] = { text: $t('status.pending'), type: 'info' }
            viewProgress.value[viewName] = 0
          }
        }
      } catch (err) {
        // Task not found yet - might be creating, just log and continue polling
        if (err.response?.data?.error?.error === 'NotFoundError') {
          logger.debug(`[ThreeViews] Task ${taskId} not ready yet, will retry...`)
          viewStatus.value[viewName] = { text: $t('status.pending'), type: 'info' }
          viewProgress.value[viewName] = 0
        } else {
          console.error(`[ThreeViews] Failed to poll task ${taskId}:`, err)
        }
      }
    }
    
    // Check if all views are complete
    const completeCount = Object.values(viewImages.value).filter(v => v !== null).length
    if (completeCount === 3) {
      generationComplete.value = true
      generating.value = false
      ElMessage.success($t('ip.three_views_generated'))
      return
    }
    
    // Continue polling
    pollTimeoutId = setTimeout(poll, 3000)
  }
  
  poll()
}

function getImageUrl(filePath) {
  if (!filePath) return ''
  
  try {
    let cleanPath = filePath
    
    if (filePath.startsWith('http://') || filePath.startsWith('https://')) {
      return filePath
    }
    
    if (cleanPath.startsWith('/')) {
      cleanPath = cleanPath.substring(1)
    }
    
    const parts = cleanPath.split('/').filter(p => p.length > 0)
    if (parts.length >= 2) {
      return `/api/v1/generate/files/${parts[parts.length - 2]}/${parts[parts.length - 1]}`
    } else if (parts.length === 1) {
      return `/api/v1/generate/files/${parts[0]}`
    }
    
    return ''
  } catch (error) {
    logger.error('Failed to get image URL:', error)
    return ''
  }
}

onMounted(loadIPs)

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
</style>
