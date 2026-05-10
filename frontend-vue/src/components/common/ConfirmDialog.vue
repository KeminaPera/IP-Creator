<template>
  <el-dialog
    v-model="visible"
    :title="computedTitle"
    :width="width"
    :close-on-click-modal="closeOnClickModal"
    :close-on-press-escape="closeOnPressEscape"
    @close="handleClose"
    class="confirm-dialog"
  >
    <div class="confirm-dialog-content">
      <!-- Icon -->
      <div class="confirm-icon" :style="{ color: iconColor }">
        <el-icon :size="iconSize">
          <Warning v-if="type === 'warning'" />
          <CircleCheck v-else-if="type === 'success'" />
          <CircleClose v-else-if="type === 'error'" />
          <QuestionFilled v-else />
        </el-icon>
      </div>

      <!-- Message -->
      <div class="confirm-message">
        <p class="confirm-text">{{ computedMessage }}</p>
        <p v-if="subMessage" class="confirm-sub-text">{{ subMessage }}</p>
      </div>
    </div>

    <template #footer>
      <div class="confirm-dialog-footer">
        <el-button
          :disabled="confirming"
          @click="handleCancel"
        >
          {{ computedCancelText }}
        </el-button>
        <el-button
          :type="confirmButtonType"
          :loading="confirming"
          :disabled="cancelDisabled"
          @click="handleConfirm"
        >
          {{ computedConfirmText }}
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
/**
 * ConfirmDialog - Reusable confirmation dialog component
 * 
 * Standardizes all confirmation dialogs across the application.
 * Replaces manual ElMessageBox.confirm calls with consistent UX.
 * 
 * @example
 * <ConfirmDialog
 *   ref="deleteDialog"
 *   :message="$t('common.confirm_delete')"
 *   type="warning"
 *   @confirm="handleDeleteConfirmed"
 * />
 * 
 * <script setup>
 * const deleteDialog = ref(null)
 * 
 * function handleDelete(row) {
 *   deleteDialog.value.open()
 * }
 * 
 * async function handleDeleteConfirmed() {
 *   await deleteItem()
 *   ElMessage.success('Deleted')
 * }
 * </script>
 */
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Warning, CircleCheck, CircleClose, QuestionFilled } from '@element-plus/icons-vue'

const { t } = useI18n()

const props = defineProps({
  /**
   * Dialog title (i18n key or plain text)
   * @default 'common.confirm'
   */
  title: {
    type: String,
    default: 'common.confirm'
  },
  
  /**
   * Confirmation message (i18n key or plain text)
   */
  message: {
    type: String,
    required: true
  },
  
  /**
   * Sub message for additional context
   */
  subMessage: {
    type: String,
    default: ''
  },
  
  /**
   * Dialog type (affects icon and color)
   * @default 'warning'
   */
  type: {
    type: String,
    default: 'warning',
    validator: (value) => ['warning', 'success', 'error', 'info'].includes(value)
  },
  
  /**
   * Confirm button text (i18n key or plain text)
   * @default 'common.confirm'
   */
  confirmText: {
    type: String,
    default: 'common.confirm'
  },
  
  /**
   * Cancel button text (i18n key or plain text)
   * @default 'common.cancel'
   */
  cancelText: {
    type: String,
    default: 'common.cancel'
  },
  
  /**
   * Confirm button type
   * @default 'primary'
   */
  confirmButtonType: {
    type: String,
    default: 'primary'
  },
  
  /**
   * Dialog width
   * @default '400px'
   */
  width: {
    type: String,
    default: '400px'
  },
  
  /**
   * Icon size
   * @default 48
   */
  iconSize: {
    type: Number,
    default: 48
  },
  
  /**
   * Close on click modal backdrop
   * @default false
   */
  closeOnClickModal: {
    type: Boolean,
    default: false
  },
  
  /**
   * Close on press escape key
   * @default true
   */
  closeOnPressEscape: {
    type: Boolean,
    default: true
  },
  
  /**
   * Disable cancel button (force confirm)
   * @default false
   */
  cancelDisabled: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['confirm', 'cancel', 'close', 'open'])

// Dialog visibility
const visible = ref(false)

// Confirm loading state
const confirming = ref(false)

// Compute translated title
const computedTitle = computed(() => {
  // Check if it's an i18n key (no spaces and contains dot)
  if (props.title.includes('.') && !props.title.includes(' ')) {
    return t(props.title)
  }
  return props.title
})

// Compute translated message
const computedMessage = computed(() => {
  // Check if it's an i18n key
  if (props.message.includes('.') && !props.message.includes(' ')) {
    return t(props.message)
  }
  return props.message
})

// Compute translated confirm text
const computedConfirmText = computed(() => {
  if (props.confirmText.includes('.') && !props.confirmText.includes(' ')) {
    return t(props.confirmText)
  }
  return props.confirmText
})

// Compute translated cancel text
const computedCancelText = computed(() => {
  if (props.cancelText.includes('.') && !props.cancelText.includes(' ')) {
    return t(props.cancelText)
  }
  return props.cancelText
})

// Compute icon color based on type
const iconColor = computed(() => {
  const colors = {
    warning: '#E6A23C',
    success: '#67C23A',
    error: '#F56C6C',
    info: '#909399'
  }
  return colors[props.type] || colors.warning
})

/**
 * Open the dialog
 */
function open() {
  visible.value = true
  confirming.value = false
  emit('open')
}

/**
 * Handle confirm action
 */
async function handleConfirm() {
  confirming.value = true
  try {
    emit('confirm')
    // Dialog will be closed by parent after async operation completes
  } catch (error) {
    // Keep dialog open on error
    console.error('Confirm action failed:', error)
  } finally {
    confirming.value = false
  }
}

/**
 * Handle cancel action
 */
function handleCancel() {
  emit('cancel')
  visible.value = false
}

/**
 * Handle dialog close
 */
function handleClose() {
  emit('close')
  confirming.value = false
}

// Expose open method
defineExpose({
  open
})
</script>

<style scoped>
.confirm-dialog :deep(.el-dialog__header) {
  padding-bottom: 0;
}

.confirm-dialog-content {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 20px 0;
}

.confirm-icon {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.confirm-message {
  flex: 1;
}

.confirm-text {
  margin: 0 0 8px 0;
  font-size: 14px;
  line-height: 1.5;
  color: #303133;
}

.confirm-sub-text {
  margin: 0;
  font-size: 12px;
  line-height: 1.5;
  color: #909399;
}

.confirm-dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
</style>
