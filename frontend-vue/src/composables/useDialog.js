import { ref } from 'vue'

/**
 * Composable for managing dialog state
 * 
 * Replaces duplicated dialog management code across multiple files.
 * Provides create, edit, and view modes with consistent state management.
 * 
 * @param {Object} options - Configuration options
 * @param {*} options.initialData - Initial data for the dialog (default: null)
 * 
 * @returns {Object} Dialog state and methods
 * 
 * @example
 * const {
 *   visible,
 *   isEdit,
 *   currentData,
 *   openCreate,
 *   openEdit,
 *   openView,
 *   close
 * } = useDialog()
 * 
 * // Usage
 * function handleCreate() {
 *   openCreate()
 * }
 * 
 * function handleEdit(row) {
 *   openEdit(row)
 * }
 */
export function useDialog(options = {}) {
  const { initialData = null } = options
  
  // Dialog visibility
  const visible = ref(false)
  
  // Mode: true if editing, false if creating or viewing
  const isEdit = ref(false)
  
  // Current data being edited/viewed
  const currentData = ref(initialData)
  
  /**
   * Open dialog in create mode
   */
  function openCreate() {
    isEdit.value = false
    currentData.value = null
    visible.value = true
  }
  
  /**
   * Open dialog in edit mode with existing data
   * 
   * @param {*} data - The data to edit
   */
  function openEdit(data) {
    isEdit.value = true
    currentData.value = data
    visible.value = true
  }
  
  /**
   * Open dialog in view-only mode
   * 
   * @param {*} data - The data to view
   */
  function openView(data) {
    isEdit.value = false
    currentData.value = data
    visible.value = true
  }
  
  /**
   * Close dialog and reset state
   */
  function close() {
    visible.value = false
    currentData.value = null
  }
  
  return {
    visible,
    isEdit,
    currentData,
    openCreate,
    openEdit,
    openView,
    close
  }
}
