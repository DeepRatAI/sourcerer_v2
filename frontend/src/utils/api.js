import axios from 'axios'

// Create axios instance with base configuration
export const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  }
})

// Request interceptor
api.interceptors.request.use(
  (config) => {
    // Add request timestamp for debugging
    config.metadata = { startTime: new Date() }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor
api.interceptors.response.use(
  (response) => {
    // Calculate request duration
    const duration = new Date() - response.config.metadata.startTime
    console.log(`API ${response.config.method?.toUpperCase()} ${response.config.url} - ${duration}ms`)
    return response
  },
  (error) => {
    // Handle common error cases
    if (error.response) {
      // Server responded with error status
      const { status, data } = error.response
      
      // Log API errors
      console.error(`API Error ${status}:`, data)
      
      // Handle specific error cases
      if (status === 401) {
        console.error('Authentication failed')
        // Could dispatch logout action here
      } else if (status === 403) {
        console.error('Access forbidden')
      } else if (status >= 500) {
        console.error('Server error occurred')
      }
    } else if (error.request) {
      // Network error
      console.error('Network error:', error.message)
    } else {
      // Request setup error
      console.error('Request error:', error.message)
    }
    
    return Promise.reject(error)
  }
)

// API helper functions
export const apiHelpers = {
  // Configuration
  getConfig: () => api.get('/config'),
  checkFirstRun: () => api.get('/config/first-run'),
  validateConfig: () => api.get('/config/validation'),
  setActiveProvider: (providerId, modelId = null) => 
    api.put('/config/active-provider', null, { 
      params: { provider_id: providerId, model_id: modelId }
    }),
  updateInferenceDefaults: (updates) => api.put('/config/inference-defaults', updates),
  toggleImageGeneration: (enabled) => api.put('/config/image-generation', null, {
    params: { enabled }
  }),

  // Providers
  listProviders: () => api.get('/providers'),
  getAvailableProviders: () => api.get('/providers/available'),
  createProvider: (providerData) => api.post('/providers', providerData),
  getProvider: (providerId) => api.get(`/providers/${providerId}`),
  updateProvider: (providerId, updates) => api.put(`/providers/${providerId}`, updates),
  deleteProvider: (providerId) => api.delete(`/providers/${providerId}`),
  refreshProviderModels: (providerId) => api.post(`/providers/${providerId}/refresh-models`),
  getProviderModels: (providerId) => api.get(`/providers/${providerId}/models`),
  testInference: (testData) => api.post('/providers/test-inference', testData),

  // Sources
  listSources: () => api.get('/sources'),
  createSource: (sourceData) => api.post('/sources', sourceData),
  getSource: (sourceId) => api.get(`/sources/${sourceId}`),
  updateSource: (sourceId, updates) => api.put(`/sources/${sourceId}`, updates),
  deleteSource: (sourceId) => api.delete(`/sources/${sourceId}`),
  refreshSource: (sourceId) => api.post(`/sources/${sourceId}/refresh`),

  // Chat
  listChatSessions: () => api.get('/chat/sessions'),
  createChatSession: () => api.post('/chat/sessions'),
  getChatSession: (sessionId) => api.get(`/chat/sessions/${sessionId}`),
  sendMessage: (sessionId, messageData) => api.post(`/chat/sessions/${sessionId}/messages`, messageData),
  deleteChatSession: (sessionId) => api.delete(`/chat/sessions/${sessionId}`),

  // Content Generation
  generateContent: (contentData) => api.post('/content/generate', contentData),
  listContentPackages: () => api.get('/content/packages'),
  getContentPackage: (packageId) => api.get(`/content/packages/${packageId}`),
  deleteContentPackage: (packageId) => api.delete(`/content/packages/${packageId}`),

  // Export/Import
  exportConfig: (exportData) => api.post('/export', exportData),
  importConfig: (importData) => api.post('/export/import', importData),
}

export default api