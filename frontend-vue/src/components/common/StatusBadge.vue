<template>
  <el-tag :type="statusConfig.type" :size="size" effect="plain">
    {{ statusConfig.label }}
  </el-tag>
</template>

<script setup>
/**
 * StatusBadge - Reusable status indicator component
 * 
 * Centralizes status color/type mapping across the application.
 * Replaces duplicated status mapping functions in multiple files.
 * 
 * @example
 * <StatusBadge status="completed" />
 * <StatusBadge status="healthy" size="medium" />
 * <StatusBadge :status="row.status" :custom-map="customMap" />
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const props = defineProps({
  /**
   * Status value to display
   * @example 'completed', 'pending', 'healthy', 'active'
   */
  status: {
    type: String,
    required: true
  },
  
  /**
   * Badge size
   * @default 'small'
   */
  size: {
    type: String,
    default: 'small',
    validator: (value) => ['small', 'default', 'large'].includes(value)
  },
  
  /**
   * Custom status mapping override
   * Use this when you need custom labels/types for specific contexts
   */
  customMap: {
    type: Object,
    default: null
  }
})

// Default comprehensive status mapping
const defaultStatusMap = {
  // Task statuses
  pending: { type: 'info', label: 'status.pending' },
  running: { type: 'warning', label: 'status.running' },
  processing: { type: 'warning', label: 'status.running' },
  completed: { type: 'success', label: 'status.completed' },
  success: { type: 'success', label: 'status.completed' },
  failed: { type: 'danger', label: 'status.failed' },
  error: { type: 'danger', label: 'status.failed' },
  cancelled: { type: 'info', label: 'status.cancelled' },
  
  // Health statuses
  healthy: { type: 'success', label: 'status.healthy' },
  ok: { type: 'success', label: 'status.ok' },
  warning: { type: 'warning', label: 'status.warning' },
  unhealthy: { type: 'danger', label: 'status.unhealthy' },
  unknown: { type: 'info', label: 'status.unknown' },
  
  // Training statuses
  training: { type: 'warning', label: 'status.training' },
  trained: { type: 'success', label: 'status.trained' },
  not_trained: { type: 'info', label: 'status.not_trained' },
  
  // Active/Inactive
  active: { type: 'success', label: 'common.active' },
  inactive: { type: 'info', label: 'common.inactive' },
  enabled: { type: 'success', label: 'common.enable' },
  disabled: { type: 'info', label: 'common.disable' }
}

// Compute the status configuration
const statusConfig = computed(() => {
  // Use custom map if provided, otherwise use default
  const map = props.customMap || defaultStatusMap
  const config = map[props.status]
  
  // If status not found in map, return as-is with info type
  if (!config) {
    return {
      type: 'info',
      label: props.status
    }
  }
  
  // Translate the label if it's an i18n key
  return {
    type: config.type,
    label: t(config.label)
  }
})
</script>

<style scoped>
.el-tag {
  font-weight: 500;
}
</style>
