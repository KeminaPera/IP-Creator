<template>
  <div class="multi-view-manager">
    <div class="section-header">
      <h3>{{ $t('multi_view.title') }}</h3>
      <el-button type="primary" @click="showUploadDialog = true">
        <el-icon><Upload /></el-icon>
        {{ $t('multi_view.upload_view') }}
      </el-button>
    </div>

    <!-- 多视图展示 -->
    <div class="views-grid" v-loading="loading">
      <div 
        v-for="view in views" 
        :key="view.id" 
        class="view-card"
        :class="{ 'is-primary': view.is_primary }"
      >
        <div class="view-image">
          <el-image 
            :src="getViewImageUrl(view.image_path)" 
            fit="cover"
            :preview-src-list="[getViewImageUrl(view.image_path)]"
          >
            <template #error>
              <div class="image-error">
                <el-icon><Picture /></el-icon>
                <span>{{ $t('common.load_failed') }}</span>
              </div>
            </template>
          </el-image>
          <div v-if="view.is_primary" class="primary-badge">{{ $t('multi_view.primary_view') }}</div>
        </div>
        <div class="view-info">
          <div class="view-type">{{ getViewTypeLabel(view.view_type) }}</div>
          <div class="view-meta">
            <el-tag size="small" :type="getSourceType(view.source)">
              {{ getSourceLabel(view.source) }}
            </el-tag>
            <span v-if="view.quality_score" class="quality-score">
              {{ $t('multi_view.quality_score') }}: {{ view.quality_score }}
            </span>
          </div>
        </div>
        <div class="view-actions">
          <el-button 
            size="small" 
            @click="setAsPrimary(view)"
            :disabled="view.is_primary"
          >
            {{ $t('multi_view.set_as_primary') }}
          </el-button>
          <el-button 
            size="small" 
            type="danger" 
            @click="handleDelete(view)"
          >
            {{ $t('common.delete') }}
          </el-button>
        </div>
      </div>

      <!-- 空状态 -->
      <el-empty 
        v-if="!loading && views.length === 0" 
        :description="$t('multi_view.empty')"
      >
        <el-button type="primary" @click="showUploadDialog = true">
          {{ $t('multi_view.upload_multi_view') }}
        </el-button>
      </el-empty>
    </div>

    <!-- 上传对话框 -->
    <el-dialog 
      v-model="showUploadDialog" 
      :title="$t('multi_view.upload_dialog_title')"
      width="600px"
    >
      <el-form :model="uploadForm" label-width="100px">
        <el-form-item :label="$t('multi_view.view_type')" required>
          <el-select v-model="uploadForm.view_type" :placeholder="$t('multi_view.select_view_type')">
            <el-option 
              v-for="type in viewTypes" 
              :key="type.value" 
              :label="type.label" 
              :value="type.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('multi_view.image_source')">
          <el-radio-group v-model="uploadForm.source">
            <el-radio label="uploaded">{{ $t('multi_view.source_uploaded') }}</el-radio>
            <el-radio label="generated">{{ $t('multi_view.source_generated') }}</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item :label="$t('multi_view.upload_image')" required>
          <ImageUploader
            v-model="imagePaths"
            :limit="1"
            accept="image/*"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showUploadDialog = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" @click="handleUpload" :loading="uploading">
          {{ $t('multi_view.upload') }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Upload, Picture } from '@element-plus/icons-vue'
import ImageUploader from '@/components/common/ImageUploader.vue'
import { 
  getMultiViews, 
  createMultiView, 
  deleteMultiView 
} from '@/api/ip-features'
import { logger } from '@/utils/logger'

const { t } = useI18n()

const props = defineProps({
  ipId: {
    type: Number,
    required: true
  }
})

const emit = defineEmits(['update'])

const loading = ref(false)
const uploading = ref(false)
const views = ref([])
const showUploadDialog = ref(false)
const imagePaths = ref([])  // 存储资源路径

const uploadForm = ref({
  view_type: 'front',
  source: 'uploaded',
  image_path: ''
})

const viewTypes = computed(() => [
  { value: 'front', label: t('multi_view.view_type_front') },
  { value: 'side', label: t('multi_view.view_type_side') },
  { value: 'back', label: t('multi_view.view_type_back') },
  { value: 'three_quarter_front', label: t('multi_view.view_type_three_quarter_front') },
  { value: 'three_quarter_back', label: t('multi_view.view_type_three_quarter_back') }
])

// 加载多视图
const loadViews = async () => {
  loading.value = true
  try {
    const response = await getMultiViews(props.ipId)
    views.value = response.data.data || []
  } catch (error) {
    logger.error('[MultiViewManager] Failed to load views:', error)
    ElMessage.error(t('multi_view.load_failed'))
  } finally {
    loading.value = false
  }
}

// 上传
const handleUpload = async () => {
  if (!uploadForm.value.view_type) {
    ElMessage.warning(t('multi_view.select_view_type_warning'))
    return
  }
  
  if (imagePaths.value.length === 0) {
    ElMessage.warning(t('multi_view.select_image_warning'))
    return
  }

  uploading.value = true
  try {
    const data = {
      view_type: uploadForm.value.view_type,
      source: 'uploaded',
      image_path: imagePaths.value[0],  // resource_path
      is_primary: views.value.length === 0
    }

    await createMultiView(props.ipId, data)
    ElMessage.success(t('multi_view.upload_success'))
    showUploadDialog.value = false
    imagePaths.value = []  // 清空选择
    loadViews()
    emit('update')
  } catch (error) {
    logger.error('[MultiViewManager] Upload failed:', error)
    ElMessage.error(t('multi_view.upload_failed'))
  } finally {
    uploading.value = false
  }
}

// 设置为主视图
const setAsPrimary = async (view) => {
  try {
    // TODO: 实现设置主视图的 API
    ElMessage.success(t('multi_view.set_primary_success'))
    loadViews()
  } catch (error) {
    logger.error('[MultiViewManager] Set primary failed:', error)
    ElMessage.error(t('multi_view.set_primary_failed'))
  }
}

// 删除
const handleDelete = async (view) => {
  try {
    await ElMessageBox.confirm(t('multi_view.delete_confirm'), t('common.warning'), {
      type: 'warning'
    })
    
    await deleteMultiView(props.ipId, view.id)
    ElMessage.success(t('multi_view.delete_success'))
    loadViews()
    emit('update')
  } catch (error) {
    if (error !== 'cancel') {
      logger.error('[MultiViewManager] Delete failed:', error)
      ElMessage.error(t('multi_view.delete_failed'))
    }
  }
}

// 工具函数
import { getImageUrl } from '@/utils/image'

// 获取多视图图片URL
const getViewImageUrl = (imagePath) => {
  if (!imagePath) return ''
  
  // 如果是完整URL，直接返回
  if (imagePath.startsWith('http://') || imagePath.startsWith('https://')) {
    return imagePath
  }
  
  // 如果是/api/开头的相对路径，直接返回
  if (imagePath.startsWith('/api/')) {
    return imagePath
  }
  
  // 如果是data/resources/开头的路径，拼接完整URL
  // 统一转换反斜杠为正斜杠（跨平台兼容）
  const normalizedPath = imagePath.replace(/\\/g, '/')
  if (normalizedPath.startsWith('data/resources/')) {
    // URL编码路径
    const encodedPath = encodeURIComponent(normalizedPath)
    return `/api/v1/resources/${encodedPath}`
  }
  
  // 其他情况使用getImageUrl
  return getImageUrl(imagePath)
}

// 工具函数已移至 utils/image.js

const getViewTypeLabel = (type) => {
  const found = viewTypes.value.find(t => t.value === type)
  return found ? found.label : type
}

const getSourceLabel = (source) => {
  return source === 'generated' ? t('multi_view.source_generated') : t('multi_view.source_uploaded')
}

const getSourceType = (source) => {
  return source === 'generated' ? 'success' : 'info'
}

// 监听 IP ID 变化
watch(() => props.ipId, () => {
  loadViews()
}, { immediate: true })

onMounted(() => {
  loadViews()
})
</script>

<style scoped>
.multi-view-manager {
  padding: 20px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.section-header h3 {
  margin: 0;
  font-size: 18px;
}

.views-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
  min-height: 200px;
}

.view-card {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  overflow: hidden;
  transition: all 0.3s;
}

.view-card:hover {
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.view-card.is-primary {
  border-color: #409eff;
  border-width: 2px;
}

.view-image {
  position: relative;
  height: 200px;
  background: #f5f7fa;
}

.view-image .el-image {
  width: 100%;
  height: 100%;
}

.image-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #909399;
}

.primary-badge {
  position: absolute;
  top: 10px;
  right: 10px;
  background: #409eff;
  color: white;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
}

.view-info {
  padding: 12px;
}

.view-type {
  font-weight: 600;
  font-size: 16px;
  margin-bottom: 8px;
}

.view-meta {
  display: flex;
  gap: 8px;
  align-items: center;
  font-size: 12px;
  color: #909399;
}

.quality-score {
  margin-left: auto;
}

.view-actions {
  padding: 12px;
  border-top: 1px solid #e4e7ed;
  display: flex;
  gap: 8px;
}

.view-actions .el-button {
  flex: 1;
}
</style>
