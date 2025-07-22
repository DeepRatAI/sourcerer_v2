import React, { useState } from 'react'
import { CheckIcon, CogIcon, ServerIcon } from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'

import ProviderSetup from './ProviderSetup'
import ImageGenerationSetup from './ImageGenerationSetup'
import LoadingSpinner from './LoadingSpinner'
import { apiHelpers } from '../utils/api'

const OnboardingFlow = ({ onComplete }) => {
  const [currentStep, setCurrentStep] = useState(0)
  const [isLoading, setIsLoading] = useState(false)
  const [providers, setProviders] = useState({})
  const [activeProvider, setActiveProvider] = useState(null)
  const [imageGenerationEnabled, setImageGenerationEnabled] = useState(false)

  const steps = [
    {
      id: 'welcome',
      title: 'Welcome to Sourcerer',
      description: 'Let\'s set up your AI content generation system',
      icon: <ServerIcon className="w-8 h-8" />
    },
    {
      id: 'provider',
      title: 'Configure LLM Provider',
      description: 'Set up at least one AI model provider to get started',
      icon: <CogIcon className="w-8 h-8" />
    },
    {
      id: 'image-generation',
      title: 'Image Generation (Optional)',
      description: 'Enable image generation with OpenAI for visual content',
      icon: <CheckIcon className="w-8 h-8" />
    },
    {
      id: 'complete',
      title: 'Setup Complete',
      description: 'You\'re ready to start using Sourcerer!',
      icon: <CheckIcon className="w-8 h-8" />
    }
  ]

  const handleProviderSetupComplete = async (providerData, providerId) => {
    try {
      setProviders(prev => ({ ...prev, [providerId]: providerData }))
      setActiveProvider(providerId)
      
      // Move to next step
      setCurrentStep(2)
      
      toast.success(`Provider ${providerId} configured successfully!`)
    } catch (error) {
      toast.error('Failed to configure provider')
    }
  }

  const handleImageGenerationSetup = async (enabled) => {
    try {
      setImageGenerationEnabled(enabled)
      
      if (enabled) {
        await apiHelpers.toggleImageGeneration(true)
        toast.success('Image generation enabled!')
      } else {
        toast.success('Skipped image generation setup')
      }
      
      setCurrentStep(3)
    } catch (error) {
      toast.error('Failed to configure image generation')
    }
  }

  const handleCompleteSetup = async () => {
    try {
      setIsLoading(true)
      
      // Final configuration steps
      if (activeProvider) {
        // Set active provider
        await apiHelpers.setActiveProvider(activeProvider)
      }
      
      // Get final configuration
      const configResponse = await apiHelpers.getConfig()
      
      onComplete(configResponse.data.data)
    } catch (error) {
      toast.error('Failed to complete setup')
      console.error('Setup completion error:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const renderStepContent = () => {
    switch (currentStep) {
      case 0:
        return (
          <div className="text-center">
            <div className="mb-8">
              <div className="mx-auto w-24 h-24 bg-blue-100 rounded-full flex items-center justify-center">
                <ServerIcon className="w-12 h-12 text-blue-600" />
              </div>
            </div>
            <h2 className="text-3xl font-bold text-gray-900 mb-4">
              Welcome to Sourcerer
            </h2>
            <p className="text-lg text-gray-600 mb-8 max-w-md mx-auto">
              Your AI-powered content aggregation and generation system. 
              Let's get you set up in just a few steps.
            </p>
            <div className="space-y-4 text-left max-w-md mx-auto mb-8">
              <div className="flex items-center space-x-3">
                <CheckIcon className="w-5 h-5 text-green-500" />
                <span className="text-gray-700">Configure AI model providers</span>
              </div>
              <div className="flex items-center space-x-3">
                <CheckIcon className="w-5 h-5 text-green-500" />
                <span className="text-gray-700">Set up content sources</span>
              </div>
              <div className="flex items-center space-x-3">
                <CheckIcon className="w-5 h-5 text-green-500" />
                <span className="text-gray-700">Generate multi-platform content</span>
              </div>
            </div>
            <button
              onClick={() => setCurrentStep(1)}
              className="px-8 py-3 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 transition-colors"
            >
              Get Started
            </button>
          </div>
        )

      case 1:
        return (
          <ProviderSetup 
            onComplete={handleProviderSetupComplete}
            onBack={() => setCurrentStep(0)}
          />
        )

      case 2:
        return (
          <ImageGenerationSetup
            onComplete={handleImageGenerationSetup}
            onSkip={() => handleImageGenerationSetup(false)}
            onBack={() => setCurrentStep(1)}
            hasOpenAI={!!providers.openai}
          />
        )

      case 3:
        return (
          <div className="text-center">
            <div className="mb-8">
              <div className="mx-auto w-24 h-24 bg-green-100 rounded-full flex items-center justify-center">
                <CheckIcon className="w-12 h-12 text-green-600" />
              </div>
            </div>
            <h2 className="text-3xl font-bold text-gray-900 mb-4">
              Setup Complete!
            </h2>
            <p className="text-lg text-gray-600 mb-8 max-w-md mx-auto">
              Your Sourcerer system is now configured and ready to use.
            </p>
            
            <div className="bg-gray-50 rounded-lg p-6 mb-8 text-left max-w-md mx-auto">
              <h3 className="font-semibold text-gray-900 mb-3">Configuration Summary:</h3>
              <ul className="space-y-2 text-sm text-gray-600">
                <li>✓ {Object.keys(providers).length} provider(s) configured</li>
                <li>✓ Active provider: {activeProvider}</li>
                <li>✓ Image generation: {imageGenerationEnabled ? 'Enabled' : 'Disabled'}</li>
              </ul>
            </div>
            
            <button
              onClick={handleCompleteSetup}
              disabled={isLoading}
              className="px-8 py-3 bg-green-600 text-white rounded-lg font-semibold hover:bg-green-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <>
                  <LoadingSpinner size="small" className="inline mr-2" />
                  Finalizing...
                </>
              ) : (
                'Start Using Sourcerer'
              )}
            </button>
          </div>
        )

      default:
        return null
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-8">
        {/* Progress Steps */}
        <div className="max-w-4xl mx-auto mb-8">
          <div className="flex items-center justify-between">
            {steps.map((step, index) => (
              <div key={step.id} className="flex items-center">
                <div className={`
                  flex items-center justify-center w-12 h-12 rounded-full border-2 
                  ${index <= currentStep 
                    ? 'bg-blue-600 border-blue-600 text-white' 
                    : 'bg-white border-gray-300 text-gray-400'
                  }
                `}>
                  {index < currentStep ? (
                    <CheckIcon className="w-6 h-6" />
                  ) : (
                    <span className="text-sm font-semibold">{index + 1}</span>
                  )}
                </div>
                {index < steps.length - 1 && (
                  <div className={`
                    w-24 h-0.5 mx-4 
                    ${index < currentStep ? 'bg-blue-600' : 'bg-gray-300'}
                  `} />
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Step Content */}
        <div className="max-w-2xl mx-auto">
          <div className="bg-white rounded-2xl shadow-xl p-8">
            {renderStepContent()}
          </div>
        </div>
      </div>
    </div>
  )
}

export default OnboardingFlow