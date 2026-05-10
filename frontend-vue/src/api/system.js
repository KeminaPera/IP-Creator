import request from './request'

export function getSystemHealth() {
  return request.get('/system/health')
}

export function getHealthSummary() {
  return request.get('/system/health/summary')
}
