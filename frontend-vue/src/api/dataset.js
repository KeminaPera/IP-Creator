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

export function evaluateDatasetQuality(id) {
  return request.post(`/datasets/${id}/evaluate-quality`)
}

export function getDatasetStats(id) {
  return request.get(`/datasets/${id}/stats`)
}

export function getQualityDistribution(id) {
  return request.get(`/datasets/${id}/quality-distribution`)
}

// Augmentation & Versioning
export function augmentDataset(id, data = {}) {
  return request.post(`/datasets/${id}/augment`, data)
}

export function createDatasetVersion(id, params = {}) {
  return request.post(`/datasets/${id}/versions`, null, { params })
}

// Batch Annotation & Caption Generation
export function batchAnnotateImages(datasetId, annotations) {
  return request.post(`/datasets/${datasetId}/batch-annotate`, annotations)
}

export function filterLowQualityImages(datasetId, data) {
  return request.post(`/datasets/${datasetId}/filter-quality`, data)
}

export function generateCaptions(datasetId, triggerWord, useAi = false) {
  const formData = new FormData()
  formData.append('trigger_word', triggerWord)
  formData.append('use_ai', useAi)
  return request.post(`/datasets/${datasetId}/generate-captions`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}
