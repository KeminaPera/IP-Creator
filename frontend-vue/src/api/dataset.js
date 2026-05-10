import request from './request'

// Dataset CRUD
export function getDatasetList(params) {
  return request.get('/datasets', { params })
}

export function getDatasetDetail(id, params = {}) {
  return request.get(`/datasets/${id}`, { params })
}

export function createDataset(data) {
  return request.post('/datasets', data)
}

export function updateDataset(id, data) {
  return request.patch(`/datasets/${id}`, data)
}

export function deleteDataset(id) {
  return request.delete(`/datasets/${id}`)
}

// Image Management
export function addDatasetImage(datasetId, data) {
  return request.post(`/datasets/${datasetId}/images`, data)
}

// Validation & Statistics
export function validateDataset(id, data = {}) {
  return request.post(`/datasets/${id}/validate`, data)
}

export function getDatasetStats(id) {
  return request.get(`/datasets/${id}/stats`)
}

// Augmentation & Versioning
export function augmentDataset(id, data = {}) {
  return request.post(`/datasets/${id}/augment`, data)
}

export function createDatasetVersion(id, params = {}) {
  return request.post(`/datasets/${id}/versions`, null, { params })
}
