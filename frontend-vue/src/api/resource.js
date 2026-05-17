import request from './request'

/**
 * 统一资源管理API
 * 
 * 提供资源上传、删除、访问功能
 * 所有文件存储在 data/resources/{year}/{month}/{day}/ 目录
 */

/**
 * 上传资源
 * @param {File} file - 文件对象
 * @returns {Promise} 返回资源信息
 */
export function uploadResource(file) {
  const formData = new FormData()
  formData.append('file', file)
  
  return request.post('/resources/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 60000,  // 60秒超时
  })
}

/**
 * 删除资源
 * @param {string} resourcePath - 资源路径
 * @returns {Promise}
 */
export function deleteResource(resourcePath) {
  if (!resourcePath) {
    return Promise.reject(new Error('Resource path is required'))
  }
  
  // URL编码路径
  const encodedPath = encodeURIComponent(resourcePath)
  return request.delete(`/resources/${encodedPath}`)
}

/**
 * 获取资源URL
 * @param {string} resourcePath - 资源路径
 * @returns {string} 完整的访问URL
 */
export function getResourceUrl(resourcePath) {
  if (!resourcePath) return ''
  
  const encodedPath = encodeURIComponent(resourcePath)
  return `/api/v1/resources/${encodedPath}`
}

/**
 * 从资源路径中提取文件名
 * @param {string} resourcePath - 资源路径
 * @returns {string} 原始文件名（去掉UUID前缀）
 */
export function extractResourceName(resourcePath) {
  if (!resourcePath) return 'unknown'
  
  const parts = resourcePath.split('/')
  const fullName = parts[parts.length - 1]
  
  // 去掉UUID前缀 (格式: uuid_originalname)
  const nameWithoutUuid = fullName.split('_').slice(1).join('_')
  
  return nameWithoutUuid || fullName
}
