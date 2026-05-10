/**
 * Debounce Composable
 * 
 * Provides debounce functionality for search inputs and other user interactions
 * Improves performance by reducing unnecessary API calls and computations
 * 
 * Usage:
 * const { debouncedFn } = useDebounce(() => { ... }, 300)
 */

import { ref } from 'vue'

export function useDebounce(fn, delay = 300) {
  let timer = null
  const isPending = ref(false)

  const debouncedFn = (...args) => {
    // Clear existing timer
    if (timer) {
      clearTimeout(timer)
    }

    // Mark as pending
    isPending.value = true

    // Set new timer
    timer = setTimeout(() => {
      fn(...args)
      isPending.value = false
      timer = null
    }, delay)
  }

  // Cancel pending execution
  const cancel = () => {
    if (timer) {
      clearTimeout(timer)
      timer = null
      isPending.value = false
    }
  }

  // Execute immediately
  const flush = () => {
    if (timer) {
      clearTimeout(timer)
      fn()
      timer = null
      isPending.value = false
    }
  }

  return {
    debouncedFn,
    isPending,
    cancel,
    flush
  }
}

/**
 * Debounced Search Composable
 * 
 * Specialized for search inputs with loading state
 * 
 * Usage:
 * const { searchQuery, isSearching, performSearch } = useDebouncedSearch(
 *   async (query) => { await fetchData(query) },
 *   300
 * )
 */
export function useDebouncedSearch(searchFn, delay = 300) {
  const searchQuery = ref('')
  const isSearching = ref(false)
  let timer = null

  const performSearch = (query = searchQuery.value) => {
    // Clear existing timer
    if (timer) {
      clearTimeout(timer)
    }

    searchQuery.value = query
    isSearching.value = true

    // Set new timer
    timer = setTimeout(async () => {
      try {
        await searchFn(query)
      } catch (error) {
        console.error('Search failed:', error)
      } finally {
        isSearching.value = false
        timer = null
      }
    }, delay)
  }

  const cancel = () => {
    if (timer) {
      clearTimeout(timer)
      timer = null
      isSearching.value = false
    }
  }

  return {
    searchQuery,
    isSearching,
    performSearch,
    cancel
  }
}
