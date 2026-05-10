import request from './request'

export function getChannels() {
  return request.get('/llm/list')
}

export function registerChannel(data) {
  return request.post('/llm/register', data)
}

export function updateChannel(id, data) {
  return request.put(`/llm/${id}`, data)
}

export function deleteChannel(id) {
  return request.delete(`/llm/${id}`)
}

export function switchChannel(id) {
  return request.post('/llm/switch', { channel_id: id })
}

export function getChannelsByCapability(capability) {
  return request.get('/llm/channels/by-capability', { params: { capability } })
}

export function syncProviderModels(providerCode) {
  return request.post(`/providers/${providerCode}/sync-models`)
}
