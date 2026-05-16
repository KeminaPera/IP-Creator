/**
 * WebSocket实时进度推送Composable
 * 
 * 提供WebSocket连接管理、进度监听、自动重连等功能
 */
import { ref, onUnmounted } from 'vue'

/**
 * 使用WebSocket监听训练进度
 * 
 * @param {number} loraId - LoRA模型ID
 * @param {Object} options - 配置选项
 * @param {boolean} options.autoConnect - 是否自动连接，默认true
 * @param {number} options.reconnectInterval - 重连间隔（毫秒），默认3000
 * @param {number} options.maxReconnectAttempts - 最大重连次数，默认5
 * @returns {Object} 响应式数据和控制方法
 */
export function useTrainingWebSocket(loraId, options = {}) {
  const {
    autoConnect = true,
    reconnectInterval = 3000,
    maxReconnectAttempts = 5
  } = options

  // 响应式状态
  const isConnected = ref(false)
  const progress = ref(0)
  const currentEpoch = ref(0)
  const currentLoss = ref(null)
  const logs = ref([])
  const error = ref(null)
  const reconnectAttempts = ref(0)

  // 内部状态
  let ws = null
  let reconnectTimer = null

  // 日志数量限制
  const MAX_LOGS = 1000

  // 获取WebSocket URL
  const getWsUrl = () => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    return `${protocol}//${host}/ws/training/${loraId}`
  }

  /**
   * 连接WebSocket
   */
  const connect = () => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      console.log('[TrainingWS] Already connected')
      return
    }

    try {
      const wsUrl = getWsUrl()
      console.log(`[TrainingWS] Connecting to ${wsUrl}`)
      
      ws = new WebSocket(wsUrl)

      ws.onopen = () => {
        console.log('[TrainingWS] Connected')
        isConnected.value = true
        reconnectAttempts.value = 0
        error.value = null
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          handleMessage(data)
        } catch (err) {
          console.error('[TrainingWS] Failed to parse message:', err)
        }
      }

      ws.onerror = (err) => {
        console.error('[TrainingWS] Error:', err)
        error.value = 'WebSocket connection error'
      }

      ws.onclose = (event) => {
        console.log(`[TrainingWS] Disconnected (code: ${event.code})`)
        isConnected.value = false
        
        // 尝试重连
        if (reconnectAttempts.value < maxReconnectAttempts) {
          scheduleReconnect()
        } else {
          error.value = 'Max reconnection attempts reached'
          console.warn('[TrainingWS] Max reconnection attempts reached')
        }
      }
    } catch (err) {
      console.error('[TrainingWS] Connection failed:', err)
      error.value = err.message
    }
  }

  /**
   * 处理接收到的消息
   */
  const handleMessage = (data) => {
    // 处理进度更新（来自Redis Pub/Sub）
    if (data.type === 'progress_update') {
      const progressData = data.data
      progress.value = progressData.progress || 0
      currentEpoch.value = progressData.current_epoch || 0
      currentLoss.value = progressData.current_loss
      
      // 添加到日志
      logs.value.push({
        type: 'progress',
        timestamp: new Date().toISOString(),
        data: progressData
      })

      // 限制日志数量
      if (logs.value.length > MAX_LOGS) {
        logs.value = logs.value.slice(-MAX_LOGS)
      }

      console.log(`[TrainingWS] Progress: ${progress.value.toFixed(1)}%, Epoch: ${currentEpoch.value}`)
    }
    
    // 处理训练完成
    else if (data.type === 'training_complete') {
      progress.value = 100
      logs.value.push({
        type: 'complete',
        timestamp: new Date().toISOString(),
        data: data.data
      })
      console.log('[TrainingWS] Training completed')
    }
    
    // 处理训练失败
    else if (data.type === 'training_failed') {
      error.value = data.data.error
      logs.value.push({
        type: 'error',
        timestamp: new Date().toISOString(),
        data: data.data
      })
      console.error('[TrainingWS] Training failed:', data.data.error)
    }
    
    // 处理历史日志
    else if (data.type === 'log' || data.message) {
      logs.value.push({
        type: 'log',
        timestamp: data.timestamp || new Date().toISOString(),
        message: data.message || data,
        data: data
      })
    }
    
    // 处理pong响应
    else if (data.type === 'pong') {
      // Heartbeat response, no action needed
    }
    
    // 处理指标数据
    else if (data.type === 'metrics') {
      logs.value.push({
        type: 'metrics',
        timestamp: new Date().toISOString(),
        data: data.data
      })
    }
  }

  /**
   * 安排重连
   */
  const scheduleReconnect = () => {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
    }

    reconnectAttempts.value++
    console.log(`[TrainingWS] Scheduling reconnect attempt ${reconnectAttempts.value}/${maxReconnectAttempts}`)

    reconnectTimer = setTimeout(() => {
      connect()
    }, reconnectInterval)
  }

  /**
   * 断开连接
   */
  const disconnect = () => {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }

    if (ws) {
      ws.close()
      ws = null
    }

    isConnected.value = false
    console.log('[TrainingWS] Disconnected by user')
  }

  /**
   * 发送消息到服务器
   */
  const sendMessage = (message) => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      if (typeof message === 'string') {
        ws.send(message)
      } else {
        ws.send(JSON.stringify(message))
      }
    } else {
      console.warn('[TrainingWS] Not connected, cannot send message')
    }
  }

  /**
   * 发送ping心跳
   */
  const sendPing = () => {
    sendMessage('ping')
  }

  /**
   * 请求指标数据
   */
  const requestMetrics = () => {
    sendMessage('get_metrics')
  }

  /**
   * 清空日志
   */
  const clearLogs = () => {
    logs.value = []
  }

  /**
   * 重置状态
   */
  const reset = () => {
    disconnect()
    progress.value = 0
    currentEpoch.value = 0
    currentLoss.value = null
    error.value = null
    reconnectAttempts.value = 0
    clearLogs()
  }

  // 自动连接
  if (autoConnect) {
    connect()
  }

  // 组件卸载时自动断开
  onUnmounted(() => {
    disconnect()
  })

  return {
    // 响应式状态
    isConnected,
    progress,
    currentEpoch,
    currentLoss,
    logs,
    error,
    reconnectAttempts,
    
    // 控制方法
    connect,
    disconnect,
    sendMessage,
    sendPing,
    requestMetrics,
    clearLogs,
    reset
  }
}

export default useTrainingWebSocket
