import request from './request'

export function getLoraList(params) {
  return request.get('/lora/list', { params })
}

export function createLora(data) {
  return request.post('/lora/create', data)
}

export function trainLora(id) {
  return request.post(`/lora/${id}/train`)
}

export function deleteLora(id) {
  return request.delete(`/lora/${id}`)
}
