/**
 * Format timestamp to unified format: YYYY-M-D HH:mm:ss
 * Example: 2026-5-5 10:50:28
 * 
 * IMPORTANT: Database stores local time (no timezone), this function
 * directly displays the time without any conversion.
 * 
 * @param {string|Date|number} time - Time string, Date object, or timestamp
 * @returns {string} Formatted time string or '-' if invalid
 */
export function formatTime(time) {
  if (!time) return '-'
  
  try {
    // If it's already a formatted string, return as-is
    if (typeof time === 'string' && /^\d{4}-\d{1,2}-\d{1,2} \d{2}:\d{2}:\d{2}$/.test(time)) {
      return time
    }
    
    // Parse the time string
    let date
    
    if (typeof time === 'string') {
      // Database time format: "2026-05-06 14:22:16" (local time, no timezone)
      // Replace space with 'T' for ISO format parsing
      date = new Date(time.replace(' ', 'T'))
    } else {
      date = new Date(time)
    }
    
    // Check if date is valid
    if (isNaN(date.getTime())) {
      return time // Return original if can't parse
    }
    
    const year = date.getFullYear()
    const month = date.getMonth() + 1
    const day = date.getDate()
    const hours = date.getHours()
    const minutes = date.getMinutes()
    const seconds = date.getSeconds()
    
    // Format: YYYY-M-D HH:mm:ss (no leading zeros for month/day)
    return `${year}-${month}-${day} ${padZero(hours)}:${padZero(minutes)}:${padZero(seconds)}`
  } catch (error) {
    console.error('Time formatting error:', error)
    return time // Return original on error
  }
}

/**
 * Pad number with leading zero if less than 10
 * @param {number} num - Number to pad
 * @returns {string} Padded string
 */
function padZero(num) {
  return num < 10 ? `0${num}` : `${num}`
}

/**
 * Format time with custom separator
 * @param {string|Date|number} time - Time string, Date object, or timestamp
 * @param {string} dateSeparator - Date separator (default: '-')
 * @param {string} timeSeparator - Time separator (default: ':')
 * @returns {string} Formatted time string
 */
export function formatTimeCustom(time, dateSeparator = '-', timeSeparator = ':') {
  if (!time) return '-'
  
  try {
    const date = new Date(time)
    
    if (isNaN(date.getTime())) {
      return time
    }
    
    const year = date.getFullYear()
    const month = date.getMonth() + 1
    const day = date.getDate()
    const hours = date.getHours()
    const minutes = date.getMinutes()
    const seconds = date.getSeconds()
    
    return `${year}${dateSeparator}${month}${dateSeparator}${day} ${padZero(hours)}${timeSeparator}${padZero(minutes)}${timeSeparator}${padZero(seconds)}`
  } catch (error) {
    return time
  }
}

/**
 * Format date only (without time)
 * @param {string|Date|number} time - Time string, Date object, or timestamp
 * @returns {string} Formatted date string (YYYY-M-D)
 */
export function formatDate(time) {
  if (!time) return '-'
  
  try {
    const date = new Date(time)
    
    if (isNaN(date.getTime())) {
      return time
    }
    
    const year = date.getFullYear()
    const month = date.getMonth() + 1
    const day = date.getDate()
    
    return `${year}-${month}-${day}`
  } catch (error) {
    return time
  }
}

/**
 * Format time only (without date)
 * @param {string|Date|number} time - Time string, Date object, or timestamp
 * @returns {string} Formatted time string (HH:mm:ss)
 */
export function formatTimeOnly(time) {
  if (!time) return '-'
  
  try {
    const date = new Date(time)
    
    if (isNaN(date.getTime())) {
      return time
    }
    
    const hours = date.getHours()
    const minutes = date.getMinutes()
    const seconds = date.getSeconds()
    
    return `${padZero(hours)}:${padZero(minutes)}:${padZero(seconds)}`
  } catch (error) {
    return time
  }
}
