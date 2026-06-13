<template>
  <el-dialog
    v-model="visible"
    :title="dialogTitle"
    width="800px"
    :before-close="handleClose"
  >
    <div v-if="loading" class="loading-container">
      <el-icon class="is-loading"><Loading /></el-icon>
      <p>{{ $t('tasks.loading_content') }}</p>
    </div>

    <div v-else-if="!hasContent" class="empty-state">
      <el-empty :description="$t('tasks.no_content_result')" />
    </div>

    <div v-else class="content-list">
      <!-- Story Content -->
      <div v-if="storyContents.length > 0" class="content-section">
        <div v-for="(content, index) in storyContents" :key="'story-' + index" class="content-item">
        <div class="content-header">
          <el-icon class="content-icon"><Document /></el-icon>
          <h3>{{ content.title }}</h3>
          <el-tag type="success">{{ $t('content.story') }}</el-tag>
        </div>
        
        <div class="content-body">
          <el-descriptions :column="2" border>
            <el-descriptions-item :label="$t('content.file_path')">
              {{ content.file_path || '-' }}
            </el-descriptions-item>
            <el-descriptions-item :label="$t('common.status')">
              <el-tag :type="content.status === 'completed' ? 'success' : 'danger'">
                {{ getStatusLabel(content.status) }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item v-if="content.word_count" :label="$t('content.word_count')">
              {{ content.word_count }} {{ $t('content.words') }}
            </el-descriptions-item>
            <el-descriptions-item v-if="content.created_at" :label="$t('content.created_at')">
              {{ formatTime(content.created_at) }}
            </el-descriptions-item>
          </el-descriptions>
          
          <div class="content-actions">
            <el-button size="small" @click="viewStoryDetail(content)">
              <el-icon><View /></el-icon>
              {{ $t('tasks.view_detail') }}
            </el-button>
            <el-button size="small" @click="copyStoryContent(content)">
              <el-icon><CopyDocument /></el-icon>
              {{ $t('tasks.copy_text') }}
            </el-button>
            <el-button size="small" type="primary" @click="navigateToContent(content.content_id)">
              <el-icon><FolderOpened /></el-icon>
              {{ $t('tasks.view_in_library') }}
            </el-button>
          </div>
        </div>
      </div>
      </div>

      <!-- Image Content -->
      <div v-if="imageContents.length > 0" class="content-item">
        <div class="content-header">
          <el-icon class="content-icon"><Picture /></el-icon>
          <h3>{{ $t('content.image') }} ({{ imageContents.length }})</h3>
          <el-tag type="primary">{{ $t('content.image') }}</el-tag>
        </div>
        
        <div class="content-body">
          <div class="image-grid">
            <div v-for="(img, idx) in imageContents" :key="'img-' + idx" class="image-card">
              <el-image
                v-if="img.thumbnail_path || img.file_path"
                :src="getFileUrl(img.thumbnail_path || img.file_path)"
                fit="cover"
                class="image-preview"
                @click="openImagePreview(img)"
              >
                <template #error>
                  <div class="image-error">
                    <el-icon><Picture /></el-icon>
                  </div>
                </template>
              </el-image>
              <div v-else class="image-placeholder">
                <el-icon><Picture /></el-icon>
              </div>
              
              <div class="image-info">
                <p class="image-title">{{ img.title }}</p>
                <p v-if="img.resolution" class="image-meta">{{ img.resolution }}</p>
              </div>
              
              <div class="image-actions">
                <el-button size="small" @click="openImagePreview(img)">
                  {{ $t('tasks.preview') }}
                </el-button>
                <el-button size="small" type="primary" @click="navigateToContent(img.content_id)">
                  {{ $t('tasks.view_in_library') }}
                </el-button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Video Content -->
      <div v-if="videoContents.length > 0" class="content-section">
        <div v-for="(content, index) in videoContents" :key="'video-' + index" class="content-item">
        <div class="content-header">
          <el-icon class="content-icon"><VideoCamera /></el-icon>
          <h3>{{ content.title }}</h3>
          <el-tag type="warning">{{ $t('content.video') }}</el-tag>
        </div>
        
        <div class="content-body">
          <div class="video-preview">
            <video
              v-if="content.file_path && !videoError[content.content_id]"
              :src="getFileUrl(content.file_path)"
              controls
              class="video-player"
              @error="handleVideoError(content.content_id)"
            >
              {{ $t('tasks.video_not_supported') }}
            </video>
            <div v-else class="video-placeholder">
              <el-icon><VideoCamera /></el-icon>
              <p>{{ videoError[content.content_id] ? $t('tasks.video_load_failed') : $t('tasks.video_preview') }}</p>
            </div>
          </div>
          
          <el-descriptions :column="2" border class="mt-10">
            <el-descriptions-item v-if="content.duration_seconds" :label="$t('content.duration')">
              {{ content.duration_seconds }}s
            </el-descriptions-item>
            <el-descriptions-item v-if="content.resolution" :label="$t('content.resolution')">
              {{ content.resolution }}
            </el-descriptions-item>
            <el-descriptions-item v-if="content.file_size" :label="$t('content.file_size')">
              {{ formatFileSize(content.file_size) }}
            </el-descriptions-item>
            <el-descriptions-item :label="$t('common.status')">
              <el-tag :type="content.status === 'completed' ? 'success' : 'danger'">
                {{ getStatusLabel(content.status) }}
              </el-tag>
            </el-descriptions-item>
          </el-descriptions>
          
          <div class="content-actions mt-10">
            <el-button size="small" type="primary" @click="navigateToContent(content.content_id)">
              <el-icon><FolderOpened /></el-icon>
              {{ $t('tasks.view_in_library') }}
            </el-button>
          </div>
        </div>
      </div>
      </div>
    </div>

    <template #footer>
      <el-button @click="handleClose">{{ $t('common.close') }}</el-button>
      <el-button v-if="hasContent" type="primary" @click="navigateToContentLibrary">
        <el-icon><FolderOpened /></el-icon>
        {{ $t('tasks.view_all_in_library') }}
      </el-button>
    </template>
  </el-dialog>

  <!-- Image Preview Dialog -->
  <el-dialog v-model="imagePreviewVisible" width="900px" append-to-body>
    <template #header>
      <span>{{ currentImage?.title || $t('tasks.image_preview') }}</span>
    </template>
    <el-image
      v-if="currentImage"
      :src="getFileUrl(currentImage.file_path)"
      fit="contain"
      style="width: 100%"
    />
  </el-dialog>

  <!-- Story Detail Dialog -->
  <el-dialog v-model="storyDetailVisible" :title="$t('tasks.story_detail')" width="700px" append-to-body>
    <div v-if="currentStory" class="story-detail">
      <h2>{{ currentStory.title }}</h2>
      <el-divider />
      <!-- Fixed: Use safe text rendering instead of v-html to prevent XSS -->
      <div class="story-content">{{ formatStoryContent(currentStory) }}</div>
    </div>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { 
  Loading, 
  Document, 
  Picture, 
  VideoCamera, 
  View, 
  CopyDocument, 
  FolderOpened 
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { getTaskContentResult } from '@/api/task'

const { t, locale } = useI18n()

const props = defineProps({
  taskId: {
    type: String,
    required: true,
  },
  modelValue: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['update:modelValue', 'navigate'])

const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
})

const loading = ref(false)
const hasContent = ref(false)
const contents = ref([])
const taskType = ref('')

// Image preview
const imagePreviewVisible = ref(false)
const currentImage = ref(null)

// Story detail
const storyDetailVisible = ref(false)
const currentStory = ref(null)

// Video error tracking
const videoError = ref({})

// Computed properties for different content types
const storyContents = computed(() => 
  contents.value.filter(c => c.content_type === 'story')
)

const imageContents = computed(() => 
  contents.value.filter(c => c.content_type === 'image')
)

const videoContents = computed(() => 
  contents.value.filter(c => c.content_type === 'video')
)

const dialogTitle = computed(() => {
  return t('tasks.task_result')
})

watch(() => props.modelValue, (newVal) => {
  // Fixed: Reload content every time dialog opens to ensure fresh data
  if (newVal && props.taskId) {
    loadContent()
  }
})

async function loadContent() {
  loading.value = true
  try {
    const response = await getTaskContentResult(props.taskId)
    
    // Fixed: Check response success before accessing data
    if (!response.data.success) {
      ElMessage.error(response.data.error?.message || t('common.load_failed'))
      hasContent.value = false
      contents.value = []
      return
    }
    
    const resultData = response.data.data
    
    hasContent.value = resultData.has_content
    taskType.value = resultData.task_type || ''
    
    if (resultData.has_content && resultData.contents) {
      contents.value = resultData.contents
    } else {
      contents.value = []
    }
  } catch (err) {
    if (import.meta.env.DEV) {
      console.error('[TaskResultDialog] Error loading content:', err)
    }
    ElMessage.error(t('common.error'))
    hasContent.value = false
    contents.value = []
  } finally {
    loading.value = false
  }
}

function handleClose() {
  visible.value = false
}

function formatTime(timeStr) {
  if (!timeStr) return '-'
  const date = new Date(timeStr)
  // Use current locale from i18n
  const localeStr = locale.value === 'en-US' ? 'en-US' : 'zh-CN'
  return date.toLocaleString(localeStr)
}

function formatFileSize(bytes) {
  if (!bytes) return '-'
  const kb = bytes / 1024
  if (kb < 1024) return `${kb.toFixed(2)} KB`
  const mb = kb / 1024
  if (mb < 1024) return `${mb.toFixed(2)} MB`
  const gb = mb / 1024
  return `${gb.toFixed(2)} GB`
}

function getStatusLabel(status) {
  const statusMap = {
    'completed': t('tasks.completed'),
    'failed': t('tasks.failed'),
    'deleted': t('common.delete'),
  }
  return statusMap[status] || status
}

// Fixed: Merged duplicate URL conversion functions
function getFileUrl(filePath) {
  if (!filePath) return ''
  // Convert backend path to URL and normalize path separators
  const normalizedPath = filePath.replace(/\\/g, '/')
  return `/api/v1/contents/files/${normalizedPath}`
}

function openImagePreview(image) {
  currentImage.value = image
  imagePreviewVisible.value = true
}

function handleVideoError(contentId) {
  videoError.value[contentId] = true
  if (import.meta.env.DEV) {
    console.error(`[TaskResultDialog] Video load failed for content ${contentId}`)
  }
}

function viewStoryDetail(content) {
  currentStory.value = content
  storyDetailVisible.value = true
}

function formatStoryContent(content) {
  // Fixed: Return plain text instead of HTML to prevent XSS
  if (content.description) {
    return content.description
  }
  return content.title || ''
}

async function copyStoryContent(content) {
  try {
    const textToCopy = content.description || content.title
    await navigator.clipboard.writeText(textToCopy)
    ElMessage.success(t('tasks.copy_success'))
  } catch (err) {
    if (import.meta.env.DEV) {
      console.error('Failed to copy:', err)
    }
    ElMessage.error(t('tasks.copy_failed'))
  }
}

function navigateToContent(contentId) {
  emit('navigate', contentId)
  visible.value = false
}

function navigateToContentLibrary() {
  // Navigate with task_id filter
  emit('navigate', null, props.taskId)
  visible.value = false
}
</script>

<style scoped>
.loading-container {
  text-align: center;
  padding: 40px;
}

.loading-container .el-icon {
  font-size: 40px;
  margin-bottom: 10px;
}

.empty-state {
  padding: 40px;
}

.content-list {
  max-height: 600px;
  overflow-y: auto;
}

.content-item {
  margin-bottom: 24px;
  padding: 16px;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  background: #fafafa;
}

.content-item:last-child {
  margin-bottom: 0;
}

.content-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
}

.content-header h3 {
  margin: 0;
  flex: 1;
  font-size: 16px;
}

.content-icon {
  font-size: 20px;
  color: #409eff;
}

.content-body {
  padding-left: 30px;
}

.content-actions {
  margin-top: 12px;
  display: flex;
  gap: 8px;
}

.image-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px;
}

.image-card {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  overflow: hidden;
  background: white;
  transition: transform 0.2s;
}

.image-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.image-preview {
  width: 100%;
  height: 150px;
  cursor: pointer;
}

.image-error,
.image-placeholder {
  width: 100%;
  height: 150px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f7fa;
  color: #909399;
}

.image-error .el-icon,
.image-placeholder .el-icon {
  font-size: 40px;
}

.image-info {
  padding: 10px;
}

.image-title {
  margin: 0 0 5px;
  font-size: 14px;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.image-meta {
  margin: 0;
  font-size: 12px;
  color: #909399;
}

.image-actions {
  padding: 8px 10px;
  border-top: 1px solid #e4e7ed;
  display: flex;
  gap: 8px;
}

.video-preview {
  width: 100%;
  background: #000;
  border-radius: 8px;
  overflow: hidden;
}

.video-player {
  width: 100%;
  max-height: 400px;
  display: block;
}

.video-placeholder {
  height: 200px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #909399;
}

.video-placeholder .el-icon {
  font-size: 60px;
  margin-bottom: 10px;
}

.story-detail h2 {
  margin-top: 0;
}

.story-content {
  line-height: 1.8;
  /* Fixed: Use white-space: pre-wrap to preserve line breaks in plain text */
  white-space: pre-wrap;
  word-wrap: break-word;
}

.mt-10 {
  margin-top: 10px;
}
</style>
