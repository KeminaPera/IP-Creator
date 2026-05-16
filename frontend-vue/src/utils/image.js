/**
 * 图片 URL 处理工具
 * 
 * 统一处理图片路径转换，支持：
 * - 完整 URL（http/https）直接返回
 * - 相对路径（/api/...）直接返回
 * - 绝对路径（/Users/.../data/...）转换为相对路径
 * - 各种存储路径（ip_assets, test_images, images, videos等）
 */

// 基础路径映射 - 支持多种格式
// 格式: [匹配路径] -> [API前缀]
// 注意：匹配路径会完全被替换为API前缀，后续路径保持不变
const BASE_PATHS = [
  // 完整 URL
  { match: /^https?:\/\//, handler: (path) => path },
  
  // API 路径直接返回
  { match: /^\/api\//, handler: (path) => path },
  
  // 绝对路径中的各种存储路径
  { match: /\/ip_assets\//, handler: (path) => `/api/v1/generate/files${path.match(/(\/ip_assets\/.*)/)[1]}` },
  { match: /\/test_images\//, handler: (path) => `/api/v1/generate/files${path.match(/(\/test_images\/.*)/)[1]}` },
  { match: /\/datasets\//, handler: (path) => `/api/v1/generate/files${path.match(/(\/datasets\/.*)/)[1]}` },
  { match: /\/images\//, handler: (path) => `/api/v1/generate/files${path.match(/(\/images\/.*)/)[1]}` },
  { match: /\/videos\//, handler: (path) => `/api/v1/generate/files${path.match(/(\/videos\/.*)/)[1]}` },
  { match: /\/lora_models\//, handler: (path) => `/api/v1/generate/files${path.match(/(\/lora_models\/.*)/)[1]}` },
  
  // data/xxx 格式的相对路径
  { match: /^data\/ip_assets\//, handler: (path) => `/api/v1/generate/files/${path.substring(5)}` },
  { match: /^data\/test_images\//, handler: (path) => `/api/v1/generate/files/${path.substring(5)}` },
  { match: /^data\/datasets\//, handler: (path) => `/api/v1/generate/files/${path.substring(5)}` },
  { match: /^data\/images\//, handler: (path) => `/api/v1/generate/files/${path.substring(5)}` },
  { match: /^data\/videos\//, handler: (path) => `/api/v1/generate/files/${path.substring(5)}` },
  { match: /^data\/lora_models\//, handler: (path) => `/api/v1/generate/files/${path.substring(5)}` },
  
  // 纯相对路径 (如 images/ip_1/xxx.png)
  { match: /^ip_assets\//, handler: (path) => `/api/v1/generate/files/${path}` },
  { match: /^test_images\//, handler: (path) => `/api/v1/generate/files/${path}` },
  { match: /^datasets\//, handler: (path) => `/api/v1/generate/files/${path}` },
  { match: /^images\//, handler: (path) => `/api/v1/generate/files/${path}` },
  { match: /^videos\//, handler: (path) => `/api/v1/generate/files/${path}` },
  { match: /^lora_models\//, handler: (path) => `/api/v1/generate/files/${path}` },
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
 * getImageUrl('/api/v1/generate/files/xxx.jpg')
 * 
 * @example
 * // 转换绝对路径为相对路径
 * getImageUrl('/Users/yanglin/Codes/IP-Creator/data/test_images/test_1.png')
 * // 返回: /api/v1/generate/files/test_images/test_1.png
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
