<template>
  <el-dialog
    v-model="visible"
    :title="title"
    :width="width"
    :close-on-click-modal="false"
    :destroy-on-close="destroyOnClose"
    @close="handleClose"
  >
    <el-form
      ref="formRef"
      :model="formData"
      :rules="rules"
      :label-width="labelWidth"
      :size="size"
    >
      <slot :form-data="formData" :form-ref="formRef" />
    </el-form>
    
    <template #footer>
      <div class="dialog-actions">
        <el-button @click="handleCancel">
          {{ cancelText }}
        </el-button>
        <el-button
          type="primary"
          :loading="loading"
          @click="handleSubmit"
        >
          {{ confirmText }}
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
/**
 * CRUD 对话框组件
 * 
 * 封装通用的新增/编辑对话框，统一表单验证和提交逻辑
 * 
 * @example
 * <CRUDDialog
 *   v-model="dialogVisible"
 *   :title="isEdit ? '编辑' : '新增'"
 *   :form-data="formData"
 *   :rules="rules"
 *   :loading="submitting"
 *   @submit="handleSubmit"
 * >
 *   <template #default="{ formData, formRef }">
 *     <el-form-item label="名称" prop="name">
 *       <el-input v-model="formData.name" />
 *     </el-form-item>
 *   </template>
 * </CRUDDialog>
 */

import { ref, computed } from 'vue'

const props = defineProps({
  // 对话框显示状态（v-model）
  modelValue: {
    type: Boolean,
    required: true
  },
  
  // 对话框标题
  title: {
    type: String,
    required: true
  },
  
  // 表单数据
  formData: {
    type: Object,
    required: true
  },
  
  // 表单验证规则
  rules: {
    type: Object,
    default: () => ({})
  },
  
  // 对话框宽度
  width: {
    type: String,
    default: '600px'
  },
  
  // 标签宽度
  labelWidth: {
    type: String,
    default: '120px'
  },
  
  // 表单尺寸
  size: {
    type: String,
    default: 'default'
  },
  
  // 关闭时销毁
  destroyOnClose: {
    type: Boolean,
    default: true
  },
  
  // 提交加载状态
  loading: {
    type: Boolean,
    default: false
  },
  
  // 取消按钮文本
  cancelText: {
    type: String,
    default: '取消'
  },
  
  // 确认按钮文本
  confirmText: {
    type: String,
    default: '确定'
  }
})

const emit = defineEmits(['update:modelValue', 'submit', 'cancel', 'close'])

const formRef = ref(null)

// 双向绑定
const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

// 提交表单
async function handleSubmit() {
  if (!formRef.value) return
  
  try {
    // 验证表单
    await formRef.value.validate()
    
    // 触发表单提交事件
    emit('submit', props.formData)
  } catch (error) {
    // 验证失败，静默处理（Element Plus 会显示错误提示）
  }
}

// 取消操作
function handleCancel() {
  emit('cancel')
  visible.value = false
}

// 关闭对话框
function handleClose() {
  // 重置表单
  if (formRef.value) {
    formRef.value.resetFields()
  }
  emit('close')
}

// 暴露方法供外部调用
defineExpose({
  /**
   * 重置表单
   */
  resetForm() {
    formRef.value?.resetFields()
  },
  
  /**
   * 验证表单
   */
  async validate() {
    return await formRef.value?.validate()
  },
  
  /**
   * 获取表单引用
   */
  getFormRef() {
    return formRef.value
  }
})
</script>

<style scoped>
.dialog-actions {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #ebeef5;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
</style>
