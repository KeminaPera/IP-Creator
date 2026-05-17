/**
 * useAsyncData - Universal async data fetching composable
 * 
 * Replaces repetitive loading/data/error patterns across views.
 * Reduces ~150 lines of duplicate code.
 * 
 * @example
 * // Basic usage
 * const { loading, data, execute: loadModels } = useAsyncData(
 *   () => getLoraList(),
 *   { errorMessage: 'lora.load_failed' }
 * )
 * 
 * // With pagination
 * const { loading, data, execute: loadContents } = useAsyncData(
 *   (params) => getContents(params),
 *   { 
 *     errorMessage: 'content.load_failed',
 *     autoLoad: true 
 *   }
 * )
 * 
 * // With callbacks
 * const { loading, data, execute } = useAsyncData(
 *   () => fetchSomething(),
 *   {
 *     onSuccess: (result) => console.log('Success:', result),
 *     onError: (error) => console.error('Error:', error)
 *   }
 * )
 */
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'

export function useAsyncData(fetchFn, options = {}) {
  const {
    errorMessage = 'common.load_failed',
    autoLoad = false,
    onSuccess = null,
    onError = null,
    transformData = null
  } = options

  const { t } = useI18n()
  
  const loading = ref(false)
  const data = ref(null)
  const error = ref(null)

  /**
   * Execute the async fetch function
   * @param  {...any} args - Arguments to pass to fetchFn
   * @returns {Promise<any>} - The fetched data
   */
  async function execute(...args) {
    loading.value = true
    error.value = null
    
    try {
      const result = await fetchFn(...args)
      
      // Transform data if transformer provided
      data.value = transformData ? transformData(result) : result
      
      // Call success callback
      onSuccess?.(result)
      
      return result
    } catch (err) {
      error.value = err
      
      // Show error message
      const message = typeof errorMessage === 'function' 
        ? errorMessage(err) 
        : t(errorMessage)
      
      ElMessage.error(message)
      
      // Call error callback
      onError?.(err)
      
      throw err
    } finally {
      loading.value = false
    }
  }

  // Auto load if enabled
  if (autoLoad) {
    execute()
  }

  return { 
    loading, 
    data, 
    error, 
    execute,
    // Alias for convenience
    reload: execute
  }
}

/**
 * useAsyncList - Specialized composable for list data with pagination
 * 
 * @example
 * const { 
 *   loading, 
 *   list, 
 *   total, 
 *   execute: loadItems,
 *   pagination 
 * } = useAsyncList(
 *   (params) => getItems(params),
 *   { errorMessage: 'common.load_failed' }
 * )
 */
export function useAsyncList(fetchFn, options = {}) {
  const {
    errorMessage = 'common.load_failed',
    autoLoad = true,
    initialPage = 1,
    initialPageSize = 20
  } = options

  const { t } = useI18n()
  
  const loading = ref(false)
  const list = ref([])
  const total = ref(0)
  const error = ref(null)
  const pagination = ref({
    page: initialPage,
    pageSize: initialPageSize
  })

  async function execute(params = {}) {
    loading.value = true
    error.value = null
    
    try {
      const requestParams = {
        skip: (pagination.value.page - 1) * pagination.value.pageSize,
        limit: pagination.value.pageSize,
        ...params
      }
      
      const result = await fetchFn(requestParams)
      
      // Support different response structures
      if (result.data?.data && Array.isArray(result.data.data)) {
        // Response: {data: {data: [...]}}
        list.value = result.data.data
      } else if (result.data?.items && Array.isArray(result.data.items)) {
        // Response: {data: {items: [...]}}
        list.value = result.data.items
      } else if (Array.isArray(result.data)) {
        // Response: {data: [...]} (list_response format)
        list.value = result.data
      } else {
        list.value = []
      }
      
      // Extract total
      if (result.data?.pagination?.total !== undefined) {
        total.value = result.data.pagination.total
      } else if (result.data?.total !== undefined) {
        total.value = result.data.total
      } else {
        total.value = list.value.length
      }
      
      return result
    } catch (err) {
      error.value = err
      ElMessage.error(t(errorMessage))
      throw err
    } finally {
      loading.value = false
    }
  }

  function setPage(page) {
    pagination.value.page = page
    return execute()
  }

  function setPageSize(pageSize) {
    pagination.value.pageSize = pageSize
    pagination.value.page = 1
    return execute()
  }

  function reset() {
    pagination.value.page = initialPage
    pagination.value.pageSize = initialPageSize
    list.value = []
    total.value = 0
  }

  if (autoLoad) {
    execute()
  }

  return {
    loading,
    list,
    total,
    error,
    pagination,
    execute,
    setPage,
    setPageSize,
    reset
  }
}
