<template>
  <div class="image-uploader-wrapper" :class="{ 'upload-limit-reached': modelValue.length >= limit }">
    <el-upload
      ref="uploadRef"
      :file-list="fileList"
      :auto-upload="true"
      :action="uploadAction"
      :headers="uploadHeaders"
      :on-success="handleSuccess"
      :on-remove="handleRemove"
      :on-error="handleError"
      :on-preview="handlePreview"
      :before-upload="beforeUpload"
      :multiple="multiple"
      :limit="limit"
      :accept="accept"
      :list-type="listType"
      :show-file-list="true"
    >
      <el-button v-if="listType !== 'picture-card'" type="primary">
        <el-icon><Upload /></el-icon>
        {{ buttonText }}
      </el-button>
      
      <!-- picture-card模式下显示➕号用于上传新图片 -->
      <template v-if="listType === 'picture-card'" #default>
        <div>
          <el-icon><Plus /></el-icon>
        </div>
      </template>
    </el-upload>
    
    <!-- 达到限制时的提示 -->
    <div v-if="modelValue.length >= limit" class="upload-limit-tip">
      {{ t('common.upload_limit_reached', { limit: limit }) }}
    </div>

    <!-- 图片预览对话框 -->
    <el-dialog v-model="previewDialogVisible" title="图片预览" width="800px">
      <img w-full :src="previewImageUrl" alt="Preview" class="preview-image" />
    </el-dialog>
  </div>
</template>

<script setup>
/**
 * 图片上传组件
 * 
 * 统一使用即时上传模式 - 选择文件后立即上传到服务器
 * 返回资源路径数组供父组件使用
 * 
 * @example
 * <ImageUploader
 *   v-model="imagePaths"
 *   :limit="4"
 *   accept="image/*"
 * />
 */

import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, Upload } from '@element-plus/icons-vue'
import { deleteResource, getResourceUrl, extractResourceName } from '@/api/resource'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const props = defineProps({
  // 数据模型（v-model）
  // 资源路径数组 ["data/resources/...", ...]
  modelValue: {
    type: Array,
    default: () => []
  },
  
  // 操作模式：create-创建模式（立即删除）| edit-编辑模式（延迟删除）
  mode: {
    type: String,
    default: 'create',
    validator: (value) => ['create', 'edit'].includes(value)
  },
  
  // 是否支持多选
  multiple: {
    type: Boolean,
    default: true
  },
  
  // 最大文件数量
  limit: {
    type: Number,
    default: 9
  },
  
  // 接受的文件类型
  accept: {
    type: String,
    default: 'image/*'
  },
  
  // 列表类型
  listType: {
    type: String,
    default: 'picture-card',
    validator: (value) => ['text', 'picture', 'picture-card'].includes(value)
  },
  
  // 按钮文本
  buttonText: {
    type: String,
    default: '上传'
  },
})

const emit = defineEmits(['update:modelValue', 'upload-success'])

// 延迟删除状态管理（仅edit模式使用）
const pendingDeletePaths = ref([])  // 标记为待删除的路径

const fileList = ref([])
const previewDialogVisible = ref(false)
const previewImageUrl = ref('')

const uploadAction = computed(() => {
  // 使用完整URL，确保在Nginx环境下也能正确上传
  return `${window.location.origin}/api/v1/resources/upload`
})

// 上传请求头
const uploadHeaders = computed(() => {
  const token = localStorage.getItem('access_token')
  return token ? { 'Authorization': `Bearer ${token}` } : {}
})

// 监听modelValue变化，初始化fileList
watch(() => props.modelValue, (value) => {
  if (!value || value.length === 0) {
    fileList.value = []
    // 如果是edit模式且modelValue被清空，也应该清空pendingDeletePaths
    if (props.mode === 'edit') {
      pendingDeletePaths.value = []
    }
    return
  }
  
  // 将路径数组转换为fileList格式
  fileList.value = value.map((path, index) => {
    const fileName = extractResourceName(path)
    return {
      uid: Date.now() + index,
      name: fileName,
      url: getResourceUrl(path),
      path: path,  // 保存原始路径
      status: 'success',
    }
  })
}, { immediate: true })

// 上传前验证
function beforeUpload(file) {
  const isImage = file.type.startsWith('image/')
  const isLt50M = file.size / 1024 / 1024 < 50
  
  if (!isImage) {
    ElMessage.error(t('common.upload_only_images'))
    return false
  }
  if (!isLt50M) {
    ElMessage.error(t('common.upload_file_too_large'))
    return false
  }
  return true
}

// 上传成功
function handleSuccess(response, file, uploadedFileList) {
  if (response.success) {
    const resourcePath = response.data.resource_path
    const resourceUrl = response.data.resource_url
    
    // 更新file对象，保存完整响应数据
    file.path = resourcePath
    // 使用API URL作为显示URL，el-upload会自动通过这个URL显示图片
    file.url = resourceUrl
    file.response = response.data
    file.status = 'success'
    
    // 更新fileList，确保UI显示正确的URL
    const index = fileList.value.findIndex(f => f.uid === file.uid)
    if (index !== -1) {
      fileList.value[index] = file
    }
    
    // 更新modelValue
    const newPaths = [...props.modelValue, resourcePath]
    emit('update:modelValue', newPaths)
    
    // 触发upload-success事件，传递完整响应数据
    emit('upload-success', response.data)
    
    ElMessage.success('上传成功')
  } else {
    ElMessage.error(response.message || '上传失败')
  }
}

// 删除文件
async function handleRemove(file, uploadedFileList) {
  if (!file.path) return
  
  if (props.mode === 'edit') {
    // 编辑模式：延迟删除，只标记不真正删除
    try {
      // 先标记待删除（去重）
      if (!pendingDeletePaths.value.includes(file.path)) {
        pendingDeletePaths.value.push(file.path)
      }
      
      // 从modelValue中移除（更新UI显示）
      const newPaths = props.modelValue.filter(p => p !== file.path)
      emit('update:modelValue', newPaths)
      
      ElMessage.success(t('common.removed_pending_save'))
    } catch (error) {
      // 恢复pendingDeletePaths
      const idx = pendingDeletePaths.value.indexOf(file.path)
      if (idx !== -1) {
        pendingDeletePaths.value.splice(idx, 1)
      }
      ElMessage.error('移除失败')
    }
  } else {
    // 创建模式：立即删除
    try {
      await deleteResource(file.path)
      
      // 从modelValue中移除
      const newPaths = props.modelValue.filter(p => p !== file.path)
      emit('update:modelValue', newPaths)
      
      ElMessage.success('删除成功')
    } catch (error) {
      ElMessage.error(error.response?.data?.message || '删除失败')
      
      // 删除失败，重新添加回列表（去重）
      const exists = fileList.value.some(f => f.uid === file.uid)
      if (!exists) {
        fileList.value.push(file)
      }
    }
  }
}

// 上传失败
function handleError(error, file, uploadedFileList) {
  ElMessage.error('上传失败: ' + (error.message || '未知错误'))
}

// 预览图片
function handlePreview(file) {
  previewImageUrl.value = file.url || getResourceUrl(file.path)
  previewDialogVisible.value = true
}

// 暴露方法
defineExpose({
  // 清空文件
  clearFiles() {
    fileList.value = []
    pendingDeletePaths.value = []
    emit('update:modelValue', [])
  },
  
  // 获取待删除的路径列表（供父组件保存时使用）
  getPendingDeletePaths() {
    return pendingDeletePaths.value
  },
  
  // 清空待删除列表（保存后调用）
  clearPendingDeletePaths() {
    pendingDeletePaths.value = []
  }
})
</script>

<style scoped>
.image-uploader-wrapper {
  width: 100%;
}

.upload-limit-tip {
  margin-top: 8px;
  font-size: 12px;
  color: #f56c6c;
  line-height: 1.5;
}

.el-upload__tip {
  color: #909399;
  font-size: 12px;
  margin-top: 8px;
}

.preview-image {
  width: 100%;
  max-height: 70vh;
  object-fit: contain;
}

/* 达到限制时隐藏上传框 */
.image-uploader-wrapper.upload-limit-reached {
  :deep(.el-upload--picture-card) {
    display: none !important;
  }
}
</style>
