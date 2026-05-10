/**
 * Enhanced Frontend Logger
 * 
 * Features:
 * - Environment-aware logging (dev vs prod)
 * - Performance timing utilities
 * - User action tracking
 * - Structured logging with timestamps
 * 
 * Usage:
 * import { logger } from '@/utils/logger'
 * 
 * logger.debug('Component loaded', data)      // Dev only
 * logger.info('User action', action)          // Dev only
 * logger.warn('Deprecated API', api)          // Dev only
 * logger.error('Failed to load', error)       // Always logged
 * 
 * // Performance timing
 * logger.time('API Call')
 * // ... do something
 * logger.timeEnd('API Call')  // Logs duration
 * 
 * // User action logging
 * logger.action('login', { username: 'admin' })
 */

const isDevelopment = import.meta.env.DEV

// Performance timing storage
const timings = {}

export const logger = {
  /**
   * Debug log - only in development
   * Use for detailed debugging information
   */
  debug: (...args) => {
    if (isDevelopment) {
      console.log('[DEBUG]', new Date().toISOString(), ...args)
    }
  },

  /**
   * Info log - user actions and important events
   * Use for general information in development
   */
  info: (...args) => {
    if (isDevelopment) {
      console.log('[INFO]', new Date().toISOString(), ...args)
    }
  },

  /**
   * Warning log - potential issues
   * Use for warnings that don't break functionality
   */
  warn: (...args) => {
    if (isDevelopment) {
      console.warn('[WARN]', new Date().toISOString(), ...args)
    }
  },

  /**
   * Error log - ALWAYS logged
   * Use for errors and exceptions
   */
  error: (...args) => {
    console.error('[ERROR]', new Date().toISOString(), ...args)
    
    // TODO: Integrate with error tracking service (e.g., Sentry)
    // if (typeof window !== 'undefined' && window.Sentry) {
    //   window.Sentry.captureException(args[0])
    // }
  },

  /**
   * Performance timing start
   * Use to measure operation duration
   * 
   * @param {string} label - Timer label
   */
  time: (label) => {
    timings[label] = performance.now()
    if (isDevelopment) {
      console.log(`[TIMER] Started: ${label}`)
    }
  },

  /**
   * Performance timing end
   * Logs the duration since time() was called
   * 
   * @param {string} label - Timer label
   * @returns {number} Duration in milliseconds
   */
  timeEnd: (label) => {
    if (timings[label]) {
      const duration = performance.now() - timings[label]
      if (isDevelopment) {
        console.log(`[TIMER] ${label}: ${duration.toFixed(2)}ms`)
      }
      delete timings[label]
      return duration
    } else {
      console.warn(`[TIMER] No timer found for label: ${label}`)
      return null
    }
  },

  /**
   * Log user action
   * Use for tracking user interactions
   * 
   * @param {string} action - Action name
   * @param {Object} details - Action details
   */
  action: (action, details = {}) => {
    if (isDevelopment) {
      console.log('[ACTION]', new Date().toISOString(), action, details)
    }
    
    // TODO: Send to analytics service
    // if (typeof window !== 'undefined' && window.analytics) {
    //   window.analytics.track(action, details)
    // }
  },

  /**
   * Group log - only in development
   * Use for grouping related logs
   */
  group: (label) => {
    if (isDevelopment) {
      console.group(`[DEBUG] ${label}`)
    }
  },

  /**
   * Group end - only in development
   */
  groupEnd: () => {
    if (isDevelopment) {
      console.groupEnd()
    }
  },
}

/**
 * Legacy console wrapper for gradual migration
 * Maps old console.log calls to logger.debug
 * 
 * @deprecated Use logger.debug() instead
 */
export const debugLog = logger.debug
