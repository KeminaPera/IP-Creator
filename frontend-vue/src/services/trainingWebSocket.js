/**
 * WebSocket service for real-time training log streaming.
 * 
 * Provides WebSocket connection management for training monitoring.
 */

class TrainingWebSocket {
  constructor() {
    this.ws = null
    this.reconnectTimer = null
    this.reconnectAttempts = 0
    this.maxReconnectAttempts = 5
    this.reconnectDelay = 3000
    this.listeners = []
    this.isConnected = false
  }

  /**
   * Connect to training WebSocket
   * @param {number} loraId - LoRA model ID
   */
  connect(loraId) {
    if (this.ws) {
      this.disconnect()
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    const url = `${protocol}//${host}/api/v1/ws/training/${loraId}`

    console.log('[TrainingWebSocket] Connecting to:', url)

    this.ws = new WebSocket(url)

    this.ws.onopen = () => {
      console.log('[TrainingWebSocket] Connected')
      this.isConnected = true
      this.reconnectAttempts = 0
      this._notifyListeners({ type: 'connected' })
    }

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        this._notifyListeners(data)
      } catch (err) {
        console.error('[TrainingWebSocket] Failed to parse message:', err)
      }
    }

    this.ws.onerror = (error) => {
      console.error('[TrainingWebSocket] Error:', error)
      this._notifyListeners({ type: 'error', error })
    }

    this.ws.onclose = () => {
      console.log('[TrainingWebSocket] Disconnected')
      this.isConnected = false
      this._notifyListeners({ type: 'disconnected' })
      this._attemptReconnect(loraId)
    }
  }

  /**
   * Disconnect from WebSocket
   */
  disconnect() {
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
    this.isConnected = false
  }

  /**
   * Send message to server
   * @param {string} message - Message to send
   */
  send(message) {
    if (this.ws && this.isConnected) {
      this.ws.send(message)
    }
  }

  /**
   * Send ping to keep connection alive
   */
  ping() {
    this.send('ping')
  }

  /**
   * Request metrics from server
   */
  requestMetrics() {
    this.send('get_metrics')
  }

  /**
   * Add event listener
   * @param {Function} callback - Callback function
   * @returns {Function} Unsubscribe function
   */
  addListener(callback) {
    this.listeners.push(callback)

    // Return unsubscribe function
    return () => {
      this.listeners = this.listeners.filter(l => l !== callback)
    }
  }

  /**
   * Remove event listener
   * @param {Function} callback - Callback function
   */
  removeListener(callback) {
    this.listeners = this.listeners.filter(l => l !== callback)
  }

  /**
   * Notify all listeners
   * @param {Object} data - Message data
   */
  _notifyListeners(data) {
    this.listeners.forEach(listener => {
      try {
        listener(data)
      } catch (err) {
        console.error('[TrainingWebSocket] Listener error:', err)
      }
    })
  }

  /**
   * Attempt to reconnect
   * @param {number} loraId - LoRA model ID
   */
  _attemptReconnect(loraId) {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.log('[TrainingWebSocket] Max reconnection attempts reached')
      return
    }

    this.reconnectAttempts++
    console.log(`[TrainingWebSocket] Reconnecting in ${this.reconnectDelay}ms (attempt ${this.reconnectAttempts})`)

    this.reconnectTimer = setTimeout(() => {
      this.connect(loraId)
    }, this.reconnectDelay)
  }
}

// Create singleton instance
export const trainingWebSocket = new TrainingWebSocket()

/**
 * Hook for using training WebSocket in Vue components
 * @param {number} loraId - LoRA model ID
 * @param {Function} onMessage - Message handler
 * @returns {Object} WebSocket control functions
 */
export function useTrainingWebSocket(loraId, onMessage) {
  let unsubscribe = null

  function connect() {
    trainingWebSocket.connect(loraId)
    if (onMessage) {
      unsubscribe = trainingWebSocket.addListener(onMessage)
    }
  }

  function disconnect() {
    if (unsubscribe) {
      unsubscribe()
    }
    trainingWebSocket.disconnect()
  }

  function ping() {
    trainingWebSocket.ping()
  }

  function requestMetrics() {
    trainingWebSocket.requestMetrics()
  }

  return {
    connect,
    disconnect,
    ping,
    requestMetrics,
    isConnected: () => trainingWebSocket.isConnected
  }
}
