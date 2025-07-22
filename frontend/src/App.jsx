import React, { useState, useEffect } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { CheckCircleIcon, ExclamationCircleIcon } from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'

import Layout from './components/Layout'
import OnboardingFlow from './components/OnboardingFlow'
import Dashboard from './components/Dashboard'
import ConfigPanel from './components/ConfigPanel'
import SourcesPanel from './components/SourcesPanel'
import ContentPanel from './components/ContentPanel'
import ChatPanel from './components/ChatPanel'
import LoadingSpinner from './components/LoadingSpinner'
import { api } from './utils/api'

function App() {
  const [isFirstRun, setIsFirstRun] = useState(null) // null = loading, true/false = determined
  const [config, setConfig] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    checkInitialState()
  }, [])

  const checkInitialState = async () => {
    try {
      // Check if this is first run
      const firstRunResponse = await api.get('/config/first-run')
      const isFirst = firstRunResponse.data.data.first_run
      setIsFirstRun(isFirst)

      if (!isFirst) {
        // Load existing configuration
        const configResponse = await api.get('/config')
        setConfig(configResponse.data.data)
        
        // Validate configuration
        const validationResponse = await api.get('/config/validation')
        const validation = validationResponse.data.data
        
        if (!validation.valid) {
          console.warn('Configuration validation warnings:', validation.errors)
          validation.errors.forEach(error => {
            toast.error(error, { duration: 6000 })
          })
        }
      }
    } catch (error) {
      console.error('Failed to check initial state:', error)
      setError(error.response?.data?.error?.message || 'Failed to initialize application')
    }
  }

  const handleOnboardingComplete = async (newConfig) => {
    setConfig(newConfig)
    setIsFirstRun(false)
    toast.success('Configuration completed successfully!', {
      icon: <CheckCircleIcon className="w-5 h-5" />
    })
  }

  const handleConfigUpdate = (updatedConfig) => {
    setConfig(updatedConfig)
  }

  // Loading state
  if (isFirstRun === null) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <LoadingSpinner size="large" />
          <p className="mt-4 text-gray-600">Initializing Sourcerer...</p>
        </div>
      </div>
    )
  }

  // Error state
  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center max-w-md">
          <ExclamationCircleIcon className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Initialization Error</h2>
          <p className="text-gray-600 mb-4">{error}</p>
          <button 
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  // First run - show onboarding
  if (isFirstRun) {
    return <OnboardingFlow onComplete={handleOnboardingComplete} />
  }

  // Normal application flow
  return (
    <Layout config={config} onConfigUpdate={handleConfigUpdate}>
      <Routes>
        <Route path="/" element={<Dashboard config={config} />} />
        <Route path="/sources" element={<SourcesPanel />} />
        <Route path="/content" element={<ContentPanel />} />
        <Route path="/chat" element={<ChatPanel />} />
        <Route 
          path="/config/*" 
          element={<ConfigPanel config={config} onConfigUpdate={handleConfigUpdate} />} 
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  )
}

export default App