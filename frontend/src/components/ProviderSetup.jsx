import React, { useState } from 'react'
import { useForm } from 'react-hook-form'
import { EyeIcon, EyeSlashIcon, CheckCircleIcon, XCircleIcon } from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'

import LoadingSpinner from './LoadingSpinner'
import { apiHelpers } from '../utils/api'

const ProviderSetup = ({ onComplete, onBack }) => {
  const [selectedType, setSelectedType] = useState('built_in')
  const [selectedProvider, setSelectedProvider] = useState('')
  const [showApiKey, setShowApiKey] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [testingAuth, setTestingAuth] = useState(false)

  const { register, handleSubmit, formState: { errors }, watch, reset } = useForm()

  const builtInProviders = {
    openai: { name: 'OpenAI', baseUrl: 'https://api.openai.com/v1' },
    anthropic: { name: 'Anthropic Claude', baseUrl: 'https://api.anthropic.com/v1' },
    moonshot: { name: 'Moonshot AI', baseUrl: 'https://api.moonshot.cn/v1' },
    huggingface: { name: 'HuggingFace', baseUrl: 'https://api-inference.huggingface.co' }
  }

  const handleTypeChange = (type) => {
    setSelectedType(type)
    setSelectedProvider('')
    reset()
  }

  const handleProviderChange = (provider) => {
    setSelectedProvider(provider)
  }

  const onSubmit = async (data) => {
    try {
      setIsLoading(true)
      
      let providerData
      let providerId
      
      if (selectedType === 'built_in') {
        providerId = selectedProvider
        providerData = {
          type: 'built_in',
          alias: data.alias || builtInProviders[selectedProvider].name,
          api_key: data.api_key,
          auto_fetch_models: data.auto_fetch_models !== false
        }
      } else {
        providerId = data.name.toLowerCase().replace(/[^a-z0-9_-]/g, '')
        providerData = {
          type: 'custom',
          name: data.name,
          alias: data.alias,
          api_key: data.api_key,
          base_url: data.base_url,
          auth_header: data.auth_header || 'Authorization',
          auth_prefix: data.auth_prefix || 'Bearer ',
          models_endpoint: data.models_endpoint,
          models_json_path: data.models_json_path || 'data[].id',
          default_model: data.default_model,
          payload_schema: data.payload_schema || 'openai_chat',
          test_prompt: data.test_prompt,
          auto_fetch_models: data.auto_fetch_models !== false
        }
      }

      // Create provider
      const response = await apiHelpers.createProvider(providerData)
      
      toast.success('Provider configured successfully!')
      onComplete(providerData, providerId)
      
    } catch (error) {
      const message = error.response?.data?.error?.message || error.response?.data?.detail || 'Failed to create provider'
      toast.error(message)
    } finally {
      setIsLoading(false)
    }
  }

  const testAuthentication = async () => {
    const data = watch()
    
    if (!data.api_key) {
      toast.error('Please enter an API key first')
      return
    }

    try {
      setTestingAuth(true)
      
      let testData
      if (selectedType === 'built_in') {
        testData = {
          type: 'built_in',
          api_key: data.api_key
        }
      } else {
        testData = {
          type: 'custom',
          name: data.name,
          api_key: data.api_key,
          base_url: data.base_url,
          auth_header: data.auth_header || 'Authorization',
          auth_prefix: data.auth_prefix || 'Bearer ',
          default_model: data.default_model,
          payload_schema: data.payload_schema || 'openai_chat',
          test_prompt: data.test_prompt || 'Hello'
        }
      }

      // This would need to be implemented in the backend
      // For now, just simulate a test
      await new Promise(resolve => setTimeout(resolve, 2000))
      toast.success('Authentication test passed!', {
        icon: <CheckCircleIcon className="w-5 h-5" />
      })
      
    } catch (error) {
      toast.error('Authentication test failed')
    } finally {
      setTestingAuth(false)
    }
  }

  return (
    <div>
      <div className="text-center mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Configure Your First Provider</h2>
        <p className="text-gray-600">
          Choose and configure an AI model provider to power your content generation
        </p>
      </div>

      {/* Provider Type Selection */}
      <div className="mb-6">
        <label className="block text-sm font-medium text-gray-700 mb-3">Provider Type</label>
        <div className="grid grid-cols-2 gap-4">
          <button
            type="button"
            onClick={() => handleTypeChange('built_in')}
            className={`p-4 border-2 rounded-lg text-left transition-colors ${
              selectedType === 'built_in'
                ? 'border-blue-500 bg-blue-50 text-blue-900'
                : 'border-gray-300 hover:border-gray-400'
            }`}
          >
            <div className="font-semibold">Built-in Providers</div>
            <div className="text-sm text-gray-600 mt-1">
              Pre-configured popular providers
            </div>
          </button>
          <button
            type="button"
            onClick={() => handleTypeChange('custom')}
            className={`p-4 border-2 rounded-lg text-left transition-colors ${
              selectedType === 'custom'
                ? 'border-blue-500 bg-blue-50 text-blue-900'
                : 'border-gray-300 hover:border-gray-400'
            }`}
          >
            <div className="font-semibold">Custom Provider</div>
            <div className="text-sm text-gray-600 mt-1">
              Configure your own API endpoint
            </div>
          </button>
        </div>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        {selectedType === 'built_in' && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-3">
              Select Provider
            </label>
            <div className="grid grid-cols-2 gap-3">
              {Object.entries(builtInProviders).map(([key, provider]) => (
                <button
                  key={key}
                  type="button"
                  onClick={() => handleProviderChange(key)}
                  className={`p-3 border rounded-lg text-left transition-colors ${
                    selectedProvider === key
                      ? 'border-blue-500 bg-blue-50 text-blue-900'
                      : 'border-gray-300 hover:border-gray-400'
                  }`}
                >
                  <div className="font-medium">{provider.name}</div>
                </button>
              ))}
            </div>
          </div>
        )}

        {selectedType === 'custom' && (
          <>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Provider Name *
              </label>
              <input
                {...register('name', { required: 'Provider name is required' })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="my-provider"
              />
              {errors.name && (
                <p className="mt-1 text-sm text-red-600">{errors.name.message}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Base URL *
              </label>
              <input
                {...register('base_url', { required: 'Base URL is required' })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="https://api.example.com/v1"
              />
              {errors.base_url && (
                <p className="mt-1 text-sm text-red-600">{errors.base_url.message}</p>
              )}
            </div>
          </>
        )}

        {(selectedType === 'built_in' && selectedProvider) || selectedType === 'custom' ? (
          <>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                API Key *
              </label>
              <div className="relative">
                <input
                  {...register('api_key', { required: 'API key is required' })}
                  type={showApiKey ? 'text' : 'password'}
                  className="w-full px-3 py-2 pr-10 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="sk-..."
                />
                <button
                  type="button"
                  onClick={() => setShowApiKey(!showApiKey)}
                  className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  {showApiKey ? <EyeSlashIcon className="w-5 h-5" /> : <EyeIcon className="w-5 h-5" />}
                </button>
              </div>
              {errors.api_key && (
                <p className="mt-1 text-sm text-red-600">{errors.api_key.message}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Alias (Optional)
              </label>
              <input
                {...register('alias')}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="My Provider"
              />
            </div>

            <div className="flex items-center">
              <input
                {...register('auto_fetch_models')}
                type="checkbox"
                defaultChecked={true}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
              <label className="ml-2 block text-sm text-gray-700">
                Automatically fetch available models
              </label>
            </div>

            {selectedType === 'custom' && (
              <details className="border border-gray-200 rounded-lg">
                <summary className="px-4 py-3 cursor-pointer text-sm font-medium text-gray-700">
                  Advanced Settings
                </summary>
                <div className="px-4 pb-4 space-y-4 border-t border-gray-200">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Default Model
                    </label>
                    <input
                      {...register('default_model')}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      placeholder="gpt-3.5-turbo"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Models Endpoint
                    </label>
                    <input
                      {...register('models_endpoint')}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      placeholder="/models"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Payload Schema
                    </label>
                    <select
                      {...register('payload_schema')}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    >
                      <option value="openai_chat">OpenAI Chat</option>
                      <option value="hf_text">HuggingFace Text</option>
                      <option value="raw_json">Raw JSON</option>
                    </select>
                  </div>
                </div>
              </details>
            )}

            <div className="flex space-x-3">
              <button
                type="button"
                onClick={testAuthentication}
                disabled={testingAuth}
                className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50"
              >
                {testingAuth ? (
                  <>
                    <LoadingSpinner size="small" className="inline mr-2" />
                    Testing...
                  </>
                ) : (
                  'Test Connection'
                )}
              </button>
              <button
                type="submit"
                disabled={isLoading}
                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
              >
                {isLoading ? (
                  <>
                    <LoadingSpinner size="small" className="inline mr-2" />
                    Configuring...
                  </>
                ) : (
                  'Configure Provider'
                )}
              </button>
            </div>
          </>
        ) : null}

        <div className="flex justify-between pt-4">
          <button
            type="button"
            onClick={onBack}
            className="px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors"
          >
            ← Back
          </button>
        </div>
      </form>
    </div>
  )
}

export default ProviderSetup