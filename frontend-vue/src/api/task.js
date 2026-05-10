import request from './request'

export function getTasks(params) {
  return request.get('/tasks/list', { params })
}

export function getTask(id) {
  return request.get(`/tasks/${id}`)
}

export function retryTask(id) {
  return request.post(`/tasks/${id}/retry`)
}

export function deleteTask(id) {
  return request.delete(`/tasks/${id}`)
}

export function getTaskContentResult(id) {
  return request.get(`/tasks/${id}/content-result`)
}
