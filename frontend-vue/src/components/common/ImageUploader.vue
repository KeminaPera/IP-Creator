<template>
  <el-upload
    ref="uploadRef"
    :file-list="fileList"
    :auto-upload="autoUpload"
    :multiple="multiple"
    :limit="limit"
    :accept="accept"
    :list-type="listType"
    :action="action"
    :headers="uploadHeaders"
    :data="uploadData"
    :on-change="handleChange"
    :on-remove="handleRemove"
    :on-success="handleSuccess"
    :on-error="handleError"
    :before-upload="beforeUpload"
  >
    <el-button v-if="listType !== 'picture-card'" type="primary">
      <el-icon><Upload /></el-icon>
      {{ buttonText }}
    </el-button>
    
    <template v-if="listType === 'picture-card'" #default>
      <el-icon><Plus /></el-icon>
    </template>
    
    <template v-if="showTip" #tip>
      <div class="el-upload__tip">
        {{ tipText }}
      </div>
    </template>
  </el-upload>
</template>

<script setup>
/**
 * 图片上传组件
 * 
 * 封装 el-upload，提供统一的图片上传功能
 * 支持预览、删除、数量限制等功能
 * 
 * @example
 * <ImageUploader
 *   v-model="imageFiles"
 *   :limit="4"
 *   accept="image/*"
 *   @change="handleFilesChange"
 * />
 */

import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, Upload } from '@element-plus/icons-vue'

const props = defineProps({
  // 已选文件列表（v-model）
  modelValue: {
    type: Array,
    default: () => []
  },
  
  // 是否自动上传
  autoUpload: {
    type: Boolean,
    default: false
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
  
  // 上传地址（自动上传时使用）
  action: {
    type: String,
    default: ''
  },
  
  // 上传请求头
  headers: {
    type: Object,
    default: () => ({})
  },
  
  // 上传额外数据
  data: {
    type: Object,
    default: () => ({})
  },
  
  // 按钮文本
  buttonText: {
    type: String,
    default: '上传图片'
  },
  
  // 是否显示提示文本
  showTip: {
    type: Boolean,
    default: true
  },
  
  // 提示文本
  tipText: {
    type: String,
    default: '支持 jpg、png 格式，单个文件不超过 5MB'
  },
  
  // 单个文件大小限制（MB）
  maxSize: {
    type: Number,
    default: 5
  }
})

const emit = defineEmits(['update:modelValue', 'change', 'remove', 'success', 'error'])

const uploadRef = ref(null)
const fileList = ref([])

// 监听外部 modelValue 变化
watch(() => props.modelValue, (newVal) => {
  // 同步外部变化（包括清空操作）
  fileList.value = newVal || []
}, { immediate: true })

// 上传请求头
const uploadHeaders = computed(() => {
  const token = localStorage.getItem('token')
  return {
    ...props.headers,
    ...(token ? { 'Authorization': `Bearer ${token}` } : {})
  }
})

// 上传额外数据
const uploadData = computed(() => {
  return { ...props.data }
})

// 文件选择变化
function handleChange(file, list) {
  fileList.value = list
  emit('update:modelValue', list)
  emit('change', list)
}

// 文件删除
function handleRemove(file, list) {
  fileList.value = list
  emit('update:modelValue', list)
  emit('remove', file)
}

// 上传成功
function handleSuccess(response, file, list) {
  emit('success', response, file)
  ElMessage.success('上传成功')
}

// 上传失败
function handleError(error, file, list) {
  emit('error', error, file)
  ElMessage.error('上传失败')
}

// 上传前验证
function beforeUpload(file) {
  // 验证文件类型
  const isImage = file.type.startsWith('image/')
  if (!isImage) {
    ElMessage.error('只能上传图片文件！')
    return false
  }
  
  // 验证文件大小
  const isLtMaxSize = file.size / 1024 / 1024 < props.maxSize
  if (!isLtMaxSize) {
    ElMessage.error(`图片大小不能超过 ${props.maxSize}MB！`)
    return false
  }
  
  return true
}

// 暴露方法供外部调用
defineExpose({
  /**
   * 提交上传（手动上传模式）
   */
  submit() {
    uploadRef.value?.submit()
  },
  
  /**
   * 清空文件列表
   */
  clearFiles() {
    fileList.value = []
    emit('update:modelValue', [])
  },
  
  /**
   * 移除文件
   */
  removeFile(file) {
    const index = fileList.value.findIndex(f => f.uid === file.uid)
    if (index > -1) {
      fileList.value.splice(index, 1)
      emit('update:modelValue', fileList.value)
    }
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
