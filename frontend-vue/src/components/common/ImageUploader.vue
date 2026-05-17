<template>
  <el-upload
    ref="uploadRef"
    :file-list="fileList"
    :auto-upload="true"
    :action="uploadAction"
    :headers="uploadHeaders"
    :on-success="handleSuccess"
    :on-remove="handleRemove"
    :on-error="handleError"
    :before-upload="beforeUpload"
    :multiple="multiple"
    :limit="limit"
    :accept="accept"
    :list-type="listType"
  >
    <el-button v-if="listType !== 'picture-card'" type="primary">
      <el-icon><Upload /></el-icon>
      {{ buttonText }}
    </el-button>
    
    <template v-if="listType === 'picture-card'" #default>
      <el-icon><Plus /></el-icon>
    </template>
  </el-upload>
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

const props = defineProps({
  // 数据模型（v-model）
  // 资源路径数组 ["data/resources/...", ...]
  modelValue: {
    type: Array,
    default: () => []
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

const fileList = ref([])
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
    ElMessage.error('只能上传图片文件!')
    return false
  }
  if (!isLt50M) {
    ElMessage.error('图片大小不能超过50MB!')
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
  // 调用后端删除
  try {
    if (file.path) {
      await deleteResource(file.path)
    }
    
    // 从modelValue中移除
    const newPaths = props.modelValue.filter(p => p !== file.path)
    emit('update:modelValue', newPaths)
    
    ElMessage.success('删除成功')
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '删除失败')
    
    // 删除失败，重新添加回列表
    if (file.path) {
      fileList.value.push(file)
    }
  }
}

// 上传失败
function handleError(error, file, uploadedFileList) {
  ElMessage.error('上传失败: ' + (error.message || '未知错误'))
}

// 暴露方法
defineExpose({
  clearFiles() {
    fileList.value = []
    emit('update:modelValue', [])
  }
})
</script>

<style scoped>
.el-upload__tip {
  color: #909399;
  font-size: 12px;
  margin-top: 8px;
}
</style>
