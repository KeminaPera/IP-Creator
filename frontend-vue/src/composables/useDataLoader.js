import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useI18n } from 'vue-i18n'
import { logger } from '@/utils/logger'

/**
 * Composable for standardized data loading with error handling
 * 
 * Replaces duplicated loading patterns across 8+ files.
 * Provides consistent loading states, error handling, and logging.
 * 
 * @param {Function} loadFn - Async function that fetches data
 * @param {Object} options - Configuration options
 * @param {string} options.errorMessage - i18n key for error message (default: 'common.load_failed')
 * @param {Function} options.onSuccess - Callback on successful load
 * @param {Function} options.onError - Callback on load error
 * @param {*} options.initialData - Initial data value (default: [])
 * 
 * @returns {Object} Loading state and reload function
 * 
 * @example
 * const { loading, data, error, reload } = useDataLoader(
 *   () => getChannels(),
 *   { 
 *     onSuccess: (data) => console.log(`Loaded ${data.length} channels`),
 *     onError: (err) => logger.error('Failed to load channels:', err)
 *   }
 * )
 * 
 * // Load on mount
 * onMounted(() => reload())
 * 
 * // Manual reload
 * function refresh() {
 *   reload()
 * }
 */
export function useDataLoader(loadFn, options = {}) {
  const { t } = useI18n()
  
  const {
    errorMessage = 'common.load_failed',
    onSuccess = null,
    onError = null,
    initialData = []
  } = options
  
  // Loading state
  const loading = ref(false)
  
  // Data state
  const data = ref(initialData)
  
  // Error state
  const error = ref(null)
  
  /**
   * Load/reload data from API
   * 
   * @param {Object} params - Optional parameters to pass to loadFn
   * @returns {Promise<Array>} Loaded data
   */
  async function reload(params = {}) {
    loading.value = true
    error.value = null
    
    try {
      // Call the load function with optional params
      const response = await loadFn(params)
      
      // Extract data from response (handle different response formats)
      let loadedData
      if (response?.data?.data !== undefined) {
        // Standard API response: { data: { data: [...] } }
        loadedData = response.data.data
      } else if (response?.data !== undefined) {
        // Simple response: { data: [...] }
        loadedData = response.data
      } else if (Array.isArray(response)) {
        // Direct array response: [...]
        loadedData = response
      } else {
        // Fallback
        loadedData = []
      }
      
      // Update data state
      data.value = loadedData
      
      // Call success callback if provided
      if (onSuccess) {
        onSuccess(loadedData)
      }
      
      logger.debug(`Data loaded successfully: ${loadedData.length} items`)
      
      return loadedData
      
    } catch (err) {
      // Store error
      error.value = err
      
      // Show user-friendly error message
      const userMessage = t(errorMessage)
      ElMessage.error(userMessage)
      
      // Log detailed error
      logger.error(`Data load failed:`, err)
      
      // Call error callback if provided
      if (onError) {
        onError(err)
      }
      
      // Return empty array on error
      return []
      
    } finally {
      // Always set loading to false
      loading.value = false
    }
  }
  
  /**
   * Reset data and error states
   */
  function reset() {
    data.value = initialData
    error.value = null
    loading.value = false
  }
  
  return {
    loading,
    data,
    error,
    reload,
    reset
  }
}
