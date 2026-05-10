import { ElMessage, ElMessageBox } from 'element-plus'
import { useI18n } from 'vue-i18n'

/**
 * Composable for delete confirmation dialogs
 * 
 * @param {Function} loadFn - Function to reload data after deletion
 * @param {string} successKey - i18n key for success message (default: 'common.success')
 * @returns {Function} handleDelete function
 * 
 * @example
 * const handleDelete = useDeleteConfirm(loadIPs, 'ip.delete_success')
 * // Usage in template: @click="handleDelete(row, deleteIP)"
 */
export function useDeleteConfirm(loadFn, successKey = 'common.success') {
  const { t } = useI18n()
  
  /**
   * Show delete confirmation and execute deletion
   * 
   * @param {Object} row - The row/item to delete
   * @param {Function} deleteFn - API delete function that accepts ID
   */
  const handleDelete = async (row, deleteFn) => {
    try {
      await ElMessageBox.confirm(
        t('common.confirm_delete'),
        t('common.confirm'),
        {
          confirmButtonText: t('common.confirm'),
          cancelButtonText: t('common.cancel'),
          type: 'warning',
        }
      )
      
      await deleteFn(row.id)
      ElMessage.success(t(successKey))
      loadFn()
    } catch (err) {
      if (err !== 'cancel') {
        // Show backend error if available, otherwise generic message
        const errorMsg = err.response?.data?.detail || t('common.error')
        ElMessage.error(errorMsg)
      }
    }
  }
  
  return handleDelete
}
