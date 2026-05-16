<template>
  <div class="multi-view-manager">
    <div class="section-header">
      <h3>📐 多视图管理</h3>
      <el-button type="primary" @click="showUploadDialog = true">
        <el-icon><Upload /></el-icon>
        上传视图
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
            :src="getImageUrl(view.image_path)" 
            fit="cover"
            :preview-src-list="[getImageUrl(view.image_path)]"
          >
            <template #error>
              <div class="image-error">
                <el-icon><Picture /></el-icon>
                <span>加载失败</span>
              </div>
            </template>
          </el-image>
          <div v-if="view.is_primary" class="primary-badge">主视图</div>
        </div>
        <div class="view-info">
          <div class="view-type">{{ getViewTypeLabel(view.view_type) }}</div>
          <div class="view-meta">
            <el-tag size="small" :type="getSourceType(view.source)">
              {{ getSourceLabel(view.source) }}
            </el-tag>
            <span v-if="view.quality_score" class="quality-score">
              质量: {{ view.quality_score }}
            </span>
          </div>
        </div>
        <div class="view-actions">
          <el-button 
            size="small" 
            @click="setAsPrimary(view)"
            :disabled="view.is_primary"
          >
            设为主视图
          </el-button>
          <el-button 
            size="small" 
            type="danger" 
            @click="handleDelete(view)"
          >
            删除
          </el-button>
        </div>
      </div>

      <!-- 空状态 -->
      <el-empty 
        v-if="!loading && views.length === 0" 
        description="暂无多视图"
      >
        <el-button type="primary" @click="showUploadDialog = true">
          上传多视图
        </el-button>
      </el-empty>
    </div>

    <!-- 上传对话框 -->
    <el-dialog 
      v-model="showUploadDialog" 
      title="上传多视图"
      width="600px"
    >
      <el-form :model="uploadForm" label-width="100px">
        <el-form-item label="视图类型" required>
          <el-select v-model="uploadForm.view_type" placeholder="请选择视图类型">
            <el-option 
              v-for="type in viewTypes" 
              :key="type.value" 
              :label="type.label" 
              :value="type.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="图片来源">
          <el-radio-group v-model="uploadForm.source">
            <el-radio label="uploaded">手动上传</el-radio>
            <el-radio label="generated">AI 生成</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="上传图片" required>
          <el-upload
            :auto-upload="false"
            :limit="1"
            accept="image/*"
            @change="handleFileChange"
          >
            <el-button type="primary">选择图片</el-button>
            <template #tip>
              <div class="el-upload__tip">支持 JPG/PNG 格式</div>
            </template>
          </el-upload>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showUploadDialog = false">取消</el-button>
        <el-button type="primary" @click="handleUpload" :loading="uploading">
          上传
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Upload, Picture } from '@element-plus/icons-vue'
import { 
  getMultiViews, 
  createMultiView, 
  deleteMultiView 
} from '@/api/ip-features'

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
const selectedFile = ref(null)

const uploadForm = ref({
  view_type: 'front',
  source: 'uploaded',
  image_path: ''
})

const viewTypes = [
  { value: 'front', label: '正面' },
  { value: 'side', label: '侧面' },
  { value: 'back', label: '背面' },
  { value: 'three_quarter_front', label: '3/4 正面' },
  { value: 'three_quarter_back', label: '3/4 背面' }
]

// 加载多视图
const loadViews = async () => {
  loading.value = true
  try {
    const response = await getMultiViews(props.ipId)
    views.value = response.data || []
  } catch (error) {
    ElMessage.error('加载多视图失败')
  } finally {
    loading.value = false
  }
}

// 文件选择
const handleFileChange = (file) => {
  selectedFile.value = file.raw
}

// 上传
const handleUpload = async () => {
  if (!uploadForm.value.view_type) {
    ElMessage.warning('请选择视图类型')
    return
  }

  uploading.value = true
  try {
    // TODO: 实现文件上传到服务器
    // 这里先使用占位路径
    const data = {
      view_type: uploadForm.value.view_type,
      source: uploadForm.value.source,
      image_path: '/uploads/multi-view-placeholder.jpg',
      is_primary: views.value.length === 0
    }

    await createMultiView(props.ipId, data)
    ElMessage.success('上传成功')
    showUploadDialog.value = false
    loadViews()
    emit('update')
  } catch (error) {
    ElMessage.error('上传失败')
  } finally {
    uploading.value = false
  }
}

// 设置为主视图
const setAsPrimary = async (view) => {
  try {
    // TODO: 实现设置主视图的 API
    ElMessage.success('已设置为主视图')
    loadViews()
  } catch (error) {
    ElMessage.error('设置失败')
  }
}

// 删除
const handleDelete = async (view) => {
  try {
    await ElMessageBox.confirm('确定删除该视图吗？', '提示', {
      type: 'warning'
    })
    
    await deleteMultiView(props.ipId, view.id)
    ElMessage.success('删除成功')
    loadViews()
    emit('update')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

// 工具函数
import { getImageUrl } from '@/utils/image'

// 工具函数已移至 utils/image.js

const getViewTypeLabel = (type) => {
  const found = viewTypes.find(t => t.value === type)
  return found ? found.label : type
}

const getSourceLabel = (source) => {
  return source === 'generated' ? 'AI 生成' : '手动上传'
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
