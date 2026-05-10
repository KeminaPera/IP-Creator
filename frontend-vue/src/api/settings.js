import request from './request'

// ========== System Settings API ==========

// 获取所有设置
export function getAllSettings() {
  return request.get('/settings')
}

// 按分类获取设置
export function getSettingsByCategory(category) {
  return request.get(`/settings/${category}`)
}

// 获取设置详情
export function getSettingDetail(category, key) {
  return request.get(`/settings/${category}/${key}`)
}

// 更新设置
export function updateSetting(category, key, value) {
  return request.put(`/settings/${category}/${key}`, { value })
}

// 恢复默认设置
export function resetSettings(category) {
  return request.post(`/settings/${category}/reset`)
}

// 获取所有分类
export function getCategories() {
  return request.get('/settings/categories')
}

// ========== Provider & Model Management API ==========

// 获取供应商列表（含模型）
export function getProviders(includeInactive = false) {
  return request.get('/providers', { 
    params: { include_inactive: includeInactive } 
  })
}

// 获取所有模型
export function getModels(providerId = null, capability = null, includeInactive = false) {
  const params = {}
  if (providerId) params.provider_id = providerId
  if (capability) params.capability = capability
  if (includeInactive) params.include_inactive = includeInactive
  
  return request.get('/providers/models', { params })
}

// 同步供应商模型
export function syncProviderModels(providerId) {
  return request.post(`/providers/${providerId}/sync-models`)
}

// 更新供应商状态
export function updateProvider(id, data) {
  return request.put(`/providers/${id}`, data)
}

// 更新模型状态
export function updateModel(id, data) {
  return request.put(`/providers/models/${id}`, data)
}
