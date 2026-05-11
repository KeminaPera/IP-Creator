import request from './request'

export function getIPList(params) {
  return request.get('/ip/list', { params })
}

export function createIP(data) {
  return request.post('/ip/create', data)
}

export function updateIP(id, data) {
  return request.put(`/ip/${id}`, data)
}

export function deleteIP(id) {
  return request.delete(`/ip/${id}`)
}

export function getIPAsset(id) {
  return request.get(`/ip/${id}`)
}

export function uploadFile(formData) {
  return request.post('/generate/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 60000,
  })
}
