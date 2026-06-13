import request from './request'

/**
 * FlowPipe Workflow API
 */

// --- Node discovery ---

export function listNodes() {
  return request.get('/workflow/nodes')
}

export function getNodeSchema(name) {
  return request.get(`/workflow/nodes/${name}`)
}

// --- Workflow CRUD ---

export function listWorkflows() {
  return request.get('/workflow/')
}

export function getDefaultWorkflow() {
  return request.get('/workflow/default')
}

export function createWorkflow(data) {
  return request.post('/workflow', data)
}

export function getWorkflow(id) {
  return request.get(`/workflow/${id}`)
}

export function updateWorkflow(id, data) {
  return request.put(`/workflow/${id}`, data)
}

export function deleteWorkflow(id) {
  return request.delete(`/workflow/${id}`)
}

// --- Templates ---

export function getWorkflowTemplates() {
  return request.get('/workflow/templates')
}

// --- Validation & Execution ---

export function validateWorkflow(workflowJson) {
  return request.post('/workflow/validate', { workflow_json: workflowJson })
}

export function executeWorkflow(data) {
  return request.post('/workflow/execute', data, { timeout: 120000 })
}
