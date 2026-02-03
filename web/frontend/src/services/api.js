import axios from 'axios'

const API_BASE = '/api'

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Dashboard
export const getDashboardOverview = () => api.get('/dashboard/overview')
export const getExecutionTrends = (days = 30, granularity = 'day') =>
  api.get('/dashboard/trends', { params: { days, granularity } })
export const getEfficiencyReport = () => api.get('/dashboard/efficiency')
export const getBottlenecks = () => api.get('/dashboard/bottlenecks')
export const getFunctionPerformance = () => api.get('/dashboard/functions')

// Functions
export const listFunctions = () => api.get('/functions')
export const createFunction = (data) => api.post('/functions', data)

// Roles
export const listRoles = () => api.get('/roles')
export const createRole = (data) => api.post('/roles', data)

// SOPs
export const listSOPs = (params = {}) => api.get('/sops', { params })
export const getSOPmain = (id) => api.get(`/sops/${id}`)
export const createSOP = (data) => api.post('/sops', data)
export const updateSOP = (id, data) => api.put(`/sops/${id}`, data)
export const getSOPSteps = (id) => api.get(`/sops/${id}/steps`)
export const addSOPStep = (id, data) => api.post(`/sops/${id}/steps`, data)
export const getSOPPerformance = (id, days = 30) =>
  api.get(`/sops/${id}/performance`, { params: { days } })
export const getSOPROI = (id) => api.get(`/sops/${id}/roi`)

// Execution
export const startExecution = (data) => api.post('/executions/start', data)
export const completeStep = (execId, stepNumber, data) =>
  api.post(`/executions/${execId}/step/${stepNumber}`, data)
export const completeExecution = (execId, data) =>
  api.post(`/executions/${execId}/complete`, data)

// Automation
export const getAutomationStatus = () => api.get('/automation/status')
export const executeAutomated = (data) => api.post('/automation/execute', data)

// Process Mining
export const identifyBottlenecks = (sopId) => api.get(`/mining/bottlenecks/${sopId}`)
export const getOptimizations = (sopId) => api.get(`/mining/optimizations/${sopId}`)
export const calculateEfficiency = (sopId) => api.get(`/mining/efficiency/${sopId}`)

// Workflows
export const listWorkflows = () => api.get('/workflows')
export const getWorkflow = (id) => api.get(`/workflows/${id}`)
export const createWorkflow = (data) => api.post('/workflows', data)
export const executeWorkflow = (id, data) => api.post(`/workflows/${id}/execute`, data)
export const getWorkflowStatus = (execId) => api.get(`/workflows/executions/${execId}`)

// Search
export const search = (query) => api.get('/search', { params: { q: query } })

export default api
