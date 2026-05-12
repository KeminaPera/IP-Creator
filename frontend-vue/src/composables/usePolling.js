/**
 * usePolling - Universal polling/timer composable
 * 
 * Replaces repetitive setInterval/clearInterval patterns.
 * Automatically cleans up on component unmount.
 * 
 * @example
 * // Basic polling
 * const { start, stop, restart } = usePolling(
 *   () => loadModels(),
 *   5000 // 5 seconds
 * )
 * 
 * // With auto-start
 * const { start, stop } = usePolling(
 *   () => refreshData(),
 *   10000,
 *   { autoStart: true }
 * )
 * 
 * // Conditional polling
 * const { start, stop, isRunning } = usePolling(
 *   () => checkStatus(),
 *   3000,
 *   { 
 *     autoStart: false,
 *     maxRetries: 100 
 *   }
 * )
 */
import { ref, onUnmounted } from 'vue'

export function usePolling(callback, intervalMs = 5000, options = {}) {
  const {
    autoStart = false,
    maxRetries = Infinity,
    onError = null,
    immediate = false
  } = options

  const timer = ref(null)
  const isRunning = ref(false)
  const retryCount = ref(0)

  /**
   * Start polling
   */
  function start() {
    // Clear existing timer
    stop()
    
    isRunning.value = true
    retryCount.value = 0
    
    // Execute immediately if requested
    if (immediate) {
      executeCallback()
    }
    
    // Set up interval
    timer.value = setInterval(executeCallback, intervalMs)
  }

  /**
   * Execute the callback with error handling
   */
  async function executeCallback() {
    try {
      await callback()
      retryCount.value = 0 // Reset on success
    } catch (error) {
      retryCount.value++
      
      // Call error callback
      onError?.(error, retryCount.value)
      
      // Stop if max retries reached
      if (retryCount.value >= maxRetries) {
        console.warn(`[usePolling] Max retries (${maxRetries}) reached, stopping polling`)
        stop()
      }
    }
  }

  /**
   * Stop polling
   */
  function stop() {
    if (timer.value) {
      clearInterval(timer.value)
      timer.value = null
    }
    isRunning.value = false
  }

  /**
   * Restart polling (stop then start)
   */
  function restart() {
    stop()
    start()
  }

  /**
   * Check if polling is active
   */
  function isActive() {
    return isRunning.value && timer.value !== null
  }

  // Auto cleanup on component unmount
  onUnmounted(stop)

  // Auto start if enabled
  if (autoStart) {
    start()
  }

  return {
    start,
    stop,
    restart,
    isActive,
    isRunning,
    retryCount
  }
}

/**
 * useAutoRefresh - Specialized polling for auto-refresh scenarios
 * 
 * @example
 * const { start, stop } = useAutoRefresh(
 *   () => loadTasks(),
 *   { interval: 30000 } // 30 seconds
 * )
 */
export function useAutoRefresh(refreshFn, options = {}) {
  const {
    interval = 30000,
    autoStart = true,
    pauseOnHidden = true
  } = options

  const { start, stop, isRunning } = usePolling(refreshFn, interval, {
    autoStart: false, // We'll handle auto-start manually
    onError: (error) => {
      console.error('[useAutoRefresh] Refresh failed:', error)
    }
  })

  // Handle page visibility (pause when tab is hidden)
  if (pauseOnHidden && typeof document !== 'undefined') {
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) {
        stop()
      } else if (isRunning.value) {
        start()
      }
    })
  }

  if (autoStart) {
    start()
  }

  return { start, stop, isRunning }
}
