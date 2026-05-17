import request from './request'

export function getLoraList(params) {
  return request.get('/lora/list', { params })
}

export function getLoRADetail(id) {
  return request.get(`/lora/${id}`)
}

export function createLora(data) {
  return request.post('/lora/create', data)
}

export function updateLora(id, data) {
  return request.put(`/lora/update/${id}`, data)
}

export function trainLora(id) {
  return request.post(`/lora/${id}/train`)
}

export function deleteLora(id) {
  return request.delete(`/lora/${id}`)
}

// Training presets
export function getTrainingPresets() {
  return request.get('/lora/presets')
}

// Validate training config
export function validateTrainingConfig(config) {
  return request.post('/lora/validate-config', config)
}

// Get training logs
export function getTrainingLogs(id, params) {
  return request.get(`/lora/${id}/logs`, { params })
}

// Get training metrics
export function getTrainingMetrics(id) {
  return request.get(`/lora/${id}/metrics`)
}

// Start training with config
export function startTraining(id, data) {
  return request.post(`/lora/${id}/train`, data)
}

// Cancel training
export function cancelTraining(id) {
  return request.post(`/lora/${id}/cancel`)
}

// Quality assessment
export function assessQuality(id, data) {
  return request.post(`/lora/${id}/assess-quality`, data)
}

export function getQualityReport(id) {
  return request.get(`/lora/${id}/quality-report`)
}

// Kohya environment check
export function checkKohyaEnvironment() {
  return request.get('/lora/check-kohya')
}
