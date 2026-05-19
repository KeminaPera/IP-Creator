/**
 * 图片 URL 处理工具
 * 
 * 统一处理图片路径转换，支持：
 * - 完整 URL（http/https）直接返回
 * - 相对路径（/api/...）直接返回
 * - 绝对路径（/Users/.../data/...）转换为相对路径
 * - 各种存储路径（resources, ip_assets, images, videos等）
 */

// 基础路径映射 - 支持多种格式
// 格式: [匹配路径] -> [API前缀]
// 注意：匹配路径会完全被替换为API前缀，后续路径保持不变
const BASE_PATHS = [
  // 完整 URL
  { match: /^https?:\/\//, handler: (path) => path },
  
  // API 路径直接返回
  { match: /^\/api\//, handler: (path) => path },
  
  // data/xxx 格式的相对路径（优先匹配，更精确）
  // 兼容 Windows 反斜杠和 Unix 正斜杠
  { match: /^data[\/\\]resources[\/\\]/, handler: (path) => {
    // 统一转换为正斜杠
    const normalizedPath = path.replace(/\\/g, '/')
    return `/api/v1/resources/${normalizedPath}`
  }},
  { match: /^data[\/\\]ip_assets[\/\\]/, handler: (path) => {
    const normalizedPath = path.replace(/\\/g, '/')
    return `/api/v1/generate/files/${normalizedPath.substring(5)}`
  }},
  { match: /^data[\/\\]images[\/\\]/, handler: (path) => {
    const normalizedPath = path.replace(/\\/g, '/')
    return `/api/v1/generate/files/${normalizedPath.substring(5)}`
  }},
  { match: /^data[\/\\]videos[\/\\]/, handler: (path) => {
    const normalizedPath = path.replace(/\\/g, '/')
    return `/api/v1/generate/files/${normalizedPath.substring(5)}`
  }},
  { match: /^data[\/\\]lora_models[\/\\]/, handler: (path) => {
    const normalizedPath = path.replace(/\\/g, '/')
    return `/api/v1/generate/files/${normalizedPath.substring(5)}`
  }},
  
  // 绝对路径中的各种存储路径
  { match: /[\/]resources[\/]/, handler: (path) => {
    // 提取resources及后续路径
    const match = path.match(/[/\\](resources[/\\].*)/)
    if (match) {
      const normalizedPath = match[1].replace(/\\/g, '/')
      return `/api/v1/resources/${normalizedPath}`
    }
    return path
  }},
  { match: /[\/]ip_assets[\/]/, handler: (path) => {
    const match = path.match(/[/\\](ip_assets[/\\].*)/)
    if (match) {
      const normalizedPath = match[1].replace(/\\/g, '/')
      return `/api/v1/generate/files/${normalizedPath}`
    }
    return path
  }},
  { match: /[\/]images[\/]/, handler: (path) => {
    const match = path.match(/[/\\](images[/\\].*)/)
    if (match) {
      const normalizedPath = match[1].replace(/\\/g, '/')
      return `/api/v1/generate/files/${normalizedPath}`
    }
    return path
  }},
  { match: /[\/]videos[\/]/, handler: (path) => {
    const match = path.match(/[/\\](videos[/\\].*)/)
    if (match) {
      const normalizedPath = match[1].replace(/\\/g, '/')
      return `/api/v1/generate/files/${normalizedPath}`
    }
    return path
  }},
  { match: /[\/]lora_models[\/]/, handler: (path) => {
    const match = path.match(/[/\\](lora_models[/\\].*)/)
    if (match) {
      const normalizedPath = match[1].replace(/\\/g, '/')
      return `/api/v1/generate/files/${normalizedPath}`
    }
    return path
  }},
  
  // 纯相对路径 (如 images/ip_1/xxx.png)
  { match: /^ip_assets[\/\\]/, handler: (path) => {
    const normalizedPath = path.replace(/\\/g, '/')
    return `/api/v1/generate/files/${normalizedPath}`
  }},
  { match: /^images[\/\\]/, handler: (path) => {
    const normalizedPath = path.replace(/\\/g, '/')
    return `/api/v1/generate/files/${normalizedPath}`
  }},
  { match: /^videos[\/\\]/, handler: (path) => {
    const normalizedPath = path.replace(/\\/g, '/')
    return `/api/v1/generate/files/${normalizedPath}`
  }},
  { match: /^lora_models[\/\\]/, handler: (path) => {
    const normalizedPath = path.replace(/\\/g, '/')
    return `/api/v1/generate/files/${normalizedPath}`
  }},
]

/**
 * 将文件路径转换为可访问的 URL
 * 
 * @param {string} path - 文件路径或 URL
 * @returns {string} 可访问的图片 URL
 * 
 * @example
 * // 返回完整 URL
 * getImageUrl('https://example.com/image.jpg')
 * 
 * @example
 * // 返回相对路径
 * getImageUrl('/api/v1/resources/data/resources/2026/05/18/xxx.jpg')
 * 
 * @example
 * // 转换绝对路径为相对路径
 * getImageUrl('/Users/yanglin/Codes/IP-Creator/data/resources/2026/05/18/xxx.jpg')
 * // 返回: /api/v1/resources/data/resources/2026/05/18/xxx.jpg
 */
export function getImageUrl(path) {
  if (!path) return ''
  
  // 依次尝试每个匹配规则
  for (const rule of BASE_PATHS) {
    if (rule.match.test(path)) {
      return rule.handler(path)
    }
  }
  
  // 都不匹配，直接返回
  return path
}

/**
 * 批量转换图片 URL
 * 
 * @param {string[]} paths - 图片路径数组
 * @returns {string[]} 图片 URL 数组
 */
export function getImageUrls(paths) {
  if (!Array.isArray(paths)) return []
  return paths.map(path => getImageUrl(path))
}

/**
 * 验证图片 URL 是否有效
 * 
 * @param {string} url - 图片 URL
 * @returns {Promise<boolean>} 是否有效
 */
export async function validateImageUrl(url) {
  if (!url) return false
  
  try {
    const response = await fetch(url, { method: 'HEAD' })
    return response.ok
  } catch {
    return false
  }
}
