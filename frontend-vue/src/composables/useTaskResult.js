import { ref, onBeforeUnmount } from 'vue'
import { getTask, getTaskContentResult } from '@/api/task'

/**
 * Composable for polling task status and fetching content results.
 * Usage:
 *   const { taskStatus, taskProgress, resultContents, isPolling, hasResult, errorMessage, startPolling, stopPolling } = useTaskResult()
 *   startPolling('some-task-id')
 */
export function useTaskResult() {
  const taskStatus = ref('')       // pending | running | completed | failed
  const taskProgress = ref(0)      // 0-100
  const resultContents = ref([])   // content list after completion
  const isPolling = ref(false)
  const hasResult = ref(false)
  const errorMessage = ref('')

  let pollTimer = null
  let currentTaskId = null

  function stopPolling() {
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
    isPolling.value = false
  }

  async function fetchContent(taskId, retries = 3) {
    for (let attempt = 0; attempt < retries; attempt++) {
      if (attempt > 0) {
        // Wait 2s before retry to handle race condition (task completed but content not yet saved)
        await new Promise(r => setTimeout(r, 2000))
      }
      try {
        const resp = await getTaskContentResult(taskId)
        const data = resp.data?.data
        if (data?.has_content && data.contents?.length > 0) {
          resultContents.value = data.contents
          hasResult.value = true
          return
        }
      } catch (err) {
        console.error(`[useTaskResult] Failed to fetch content (attempt ${attempt + 1}/${retries}):`, err)
      }
    }
    // All retries exhausted
    resultContents.value = []
    hasResult.value = false
  }

  async function pollOnce(taskId) {
    try {
      const resp = await getTask(taskId)
      const task = resp.data?.data
      if (!task) return

      const status = task.status || 'pending'
      taskStatus.value = status

      // Progress is stored as 0-100 in the database
      if (typeof task.progress === 'number') {
        taskProgress.value = Math.round(task.progress)
      } else if (status === 'completed') {
        taskProgress.value = 100
      } else if (status === 'running') {
        taskProgress.value = Math.max(taskProgress.value, 10)
      }

      if (status === 'completed') {
        stopPolling()
        taskProgress.value = 100
        await fetchContent(taskId)
      } else if (status === 'failed') {
        stopPolling()
        errorMessage.value = task.error_message || task.result || 'Task failed'
      }
    } catch (err) {
      console.error('[useTaskResult] Poll error:', err)
    }
  }

  function startPolling(taskId) {
    if (!taskId) return
    // Reset state
    stopPolling()
    currentTaskId = taskId
    taskStatus.value = 'pending'
    taskProgress.value = 0
    resultContents.value = []
    hasResult.value = false
    errorMessage.value = ''
    isPolling.value = true

    // Immediate first poll
    pollOnce(taskId)

    // Poll every 3 seconds
    pollTimer = setInterval(() => {
      if (isPolling.value) {
        pollOnce(currentTaskId)
      }
    }, 3000)
  }

  // Cleanup on component unmount
  onBeforeUnmount(() => {
    stopPolling()
  })

  return {
    taskStatus,
    taskProgress,
    resultContents,
    isPolling,
    hasResult,
    errorMessage,
    startPolling,
    stopPolling,
  }
}
