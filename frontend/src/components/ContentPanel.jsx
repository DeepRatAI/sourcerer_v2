import React, { useState, useEffect } from 'react'
import {
  PlusIcon,
  DocumentTextIcon,
  PhotoIcon,
  PlayIcon,
  TrashIcon,
  EyeIcon,
  ArrowDownTrayIcon,
  SparklesIcon,
  ClockIcon,
  CheckCircleIcon
} from '@heroicons/react/24/outline'
import LoadingSpinner from './LoadingSpinner'

const ContentPanel = () => {
  const [packages, setPackages] = useState([])
  const [sources, setSources] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [showGenerateForm, setShowGenerateForm] = useState(false)
  const [selectedPackage, setSelectedPackage] = useState(null)
  const [generateRequest, setGenerateRequest] = useState({
    source_item_id: '',
    content_types: ['summary'],
    platforms: [],
    include_research: false,
    image_count: 0,
    custom_instructions: ''
  })

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    try {
      const [packagesResponse, sourcesResponse] = await Promise.all([
        fetch('/api/content/packages'),
        fetch('/api/sources/')
      ])
      
      const packagesData = await packagesResponse.json()
      const sourcesData = await sourcesResponse.json()
      
      setPackages(packagesData.data?.packages || [])
      setSources(sourcesData.data || [])
    } catch (error) {
      console.error('Failed to fetch data:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleGenerateContent = async (e) => {
    e.preventDefault()
    
    try {
      const response = await fetch('/api/content/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(generateRequest)
      })
      
      if (response.ok) {
        setShowGenerateForm(false)
        setGenerateRequest({
          source_item_id: '',
          content_types: ['summary'],
          platforms: [],
          include_research: false,
          image_count: 0,
          custom_instructions: ''
        })
        await fetchData()
      }
    } catch (error) {
      console.error('Failed to generate content:', error)
    }
  }

  const handleDeletePackage = async (packageId) => {
    if (!confirm('Are you sure you want to delete this content package?')) {
      return
    }

    try {
      const response = await fetch(`/api/content/packages/${packageId}`, {
        method: 'DELETE'
      })
      
      if (response.ok) {
        await fetchData()
      }
    } catch (error) {
      console.error('Failed to delete package:', error)
    }
  }

  const getContentTypeIcon = (type) => {
    switch (type) {
      case 'summary':
        return <DocumentTextIcon className="w-4 h-4 text-blue-500" />
      case 'scripts':
        return <PlayIcon className="w-4 h-4 text-green-500" />
      case 'images':
        return <PhotoIcon className="w-4 h-4 text-purple-500" />
      default:
        return <DocumentTextIcon className="w-4 h-4 text-gray-500" />
    }
  }

  const getAvailableItems = () => {
    return sources.flatMap(source => 
      (source.items || []).map(item => ({ ...item, sourceName: source.name }))
    )
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <LoadingSpinner size="large" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Content Generation</h1>
          <p className="text-gray-600 mt-1">
            Generate and manage content packages from your sources
          </p>
        </div>
        <button
          onClick={() => setShowGenerateForm(true)}
          className="flex items-center px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
        >
          <SparklesIcon className="w-4 h-4 mr-2" />
          Generate Content
        </button>
      </div>

      {/* Stats Overview */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-500">Total Packages</span>
          </div>
          <p className="text-3xl font-bold text-gray-900">{packages.length}</p>
        </div>
        
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-500">With Research</span>
          </div>
          <p className="text-3xl font-bold text-blue-600">
            {packages.filter(p => p.has_research).length}
          </p>
        </div>
        
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-500">Generated Files</span>
          </div>
          <p className="text-3xl font-bold text-green-600">
            {packages.reduce((sum, p) => sum + (p.file_count || 0), 0)}
          </p>
        </div>
        
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-500">Available Items</span>
          </div>
          <p className="text-3xl font-bold text-orange-600">
            {getAvailableItems().length}
          </p>
        </div>
      </div>

      {/* Generate Content Form */}
      {showGenerateForm && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Generate New Content Package</h2>
          
          <form onSubmit={handleGenerateContent} className="space-y-6">
            {/* Source Item Selection */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Select Source Item
              </label>
              <select
                value={generateRequest.source_item_id}
                onChange={(e) => setGenerateRequest({ ...generateRequest, source_item_id: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              >
                <option value="">Choose an item to generate content from...</option>
                {getAvailableItems().map((item) => (
                  <option key={item.id} value={item.id}>
                    [{item.sourceName}] {item.title}
                  </option>
                ))}
              </select>
            </div>

            {/* Content Types */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-3">
                Content Types
              </label>
              <div className="space-y-2">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={generateRequest.content_types.includes('summary')}
                    onChange={(e) => {
                      const types = generateRequest.content_types
                      if (e.target.checked) {
                        setGenerateRequest({ ...generateRequest, content_types: [...types, 'summary'] })
                      } else {
                        setGenerateRequest({ ...generateRequest, content_types: types.filter(t => t !== 'summary') })
                      }
                    }}
                    className="mr-2"
                  />
                  <DocumentTextIcon className="w-4 h-4 mr-2 text-blue-500" />
                  Summary
                </label>
                
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={generateRequest.content_types.includes('scripts')}
                    onChange={(e) => {
                      const types = generateRequest.content_types
                      if (e.target.checked) {
                        setGenerateRequest({ ...generateRequest, content_types: [...types, 'scripts'] })
                      } else {
                        setGenerateRequest({ ...generateRequest, content_types: types.filter(t => t !== 'scripts') })
                      }
                    }}
                    className="mr-2"
                  />
                  <PlayIcon className="w-4 h-4 mr-2 text-green-500" />
                  Scripts
                </label>
                
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={generateRequest.content_types.includes('images')}
                    onChange={(e) => {
                      const types = generateRequest.content_types
                      if (e.target.checked) {
                        setGenerateRequest({ ...generateRequest, content_types: [...types, 'images'] })
                      } else {
                        setGenerateRequest({ ...generateRequest, content_types: types.filter(t => t !== 'images') })
                      }
                    }}
                    className="mr-2"
                  />
                  <PhotoIcon className="w-4 h-4 mr-2 text-purple-500" />
                  Images
                </label>
              </div>
            </div>

            {/* Image Count */}
            {generateRequest.content_types.includes('images') && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Number of Images
                </label>
                <input
                  type="number"
                  value={generateRequest.image_count}
                  onChange={(e) => setGenerateRequest({ ...generateRequest, image_count: parseInt(e.target.value) || 0 })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  min="0"
                  max="5"
                />
              </div>
            )}

            {/* Research Option */}
            <div>
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={generateRequest.include_research}
                  onChange={(e) => setGenerateRequest({ ...generateRequest, include_research: e.target.checked })}
                  className="mr-2"
                />
                Include additional research context
              </label>
            </div>

            {/* Custom Instructions */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Custom Instructions (Optional)
              </label>
              <textarea
                value={generateRequest.custom_instructions}
                onChange={(e) => setGenerateRequest({ ...generateRequest, custom_instructions: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                rows={3}
                placeholder="Any specific requirements or style preferences..."
              />
            </div>
            
            <div className="flex justify-end space-x-3">
              <button
                type="button"
                onClick={() => setShowGenerateForm(false)}
                className="px-4 py-2 text-gray-700 border border-gray-300 rounded-md hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700"
              >
                Generate Content
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Content Packages List */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Generated Content Packages</h2>
        </div>
        
        {packages.length === 0 ? (
          <div className="text-center py-12">
            <SparklesIcon className="w-12 h-12 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No content packages yet</h3>
            <p className="text-gray-600 mb-6">Generate your first content package from a source item</p>
            <button
              onClick={() => setShowGenerateForm(true)}
              className="inline-flex items-center px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
            >
              <SparklesIcon className="w-4 h-4 mr-2" />
              Generate Content
            </button>
          </div>
        ) : (
          <div className="divide-y divide-gray-200">
            {packages.map((pkg) => (
              <div key={pkg.id} className="px-6 py-4">
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <div className="flex items-center space-x-3 mb-2">
                      <DocumentTextIcon className="w-5 h-5 text-green-500" />
                      <h3 className="text-lg font-medium text-gray-900">
                        Package {pkg.id}
                      </h3>
                      {pkg.has_research && (
                        <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                          <CheckCircleIcon className="w-3 h-3 mr-1" />
                          Research
                        </span>
                      )}
                    </div>
                    
                    <div className="flex items-center space-x-6 text-sm text-gray-600">
                      <div className="flex items-center space-x-1">
                        <ClockIcon className="w-4 h-4" />
                        <span>{new Date(pkg.created_at).toLocaleString()}</span>
                      </div>
                      <div className="flex items-center space-x-1">
                        <DocumentTextIcon className="w-4 h-4" />
                        <span>{pkg.content_count} content pieces</span>
                      </div>
                      <div className="flex items-center space-x-1">
                        <ArrowDownTrayIcon className="w-4 h-4" />
                        <span>{pkg.file_count} files</span>
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => setSelectedPackage(pkg)}
                      className="p-2 text-gray-600 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                      title="View details"
                    >
                      <EyeIcon className="w-4 h-4" />
                    </button>
                    
                    <button
                      onClick={() => handleDeletePackage(pkg.id)}
                      className="p-2 text-gray-600 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                      title="Delete package"
                    >
                      <TrashIcon className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Package Details Modal */}
      {selectedPackage && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg max-w-4xl w-full mx-4 max-h-[90vh] overflow-y-auto">
            <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
              <h2 className="text-xl font-semibold text-gray-900">
                Package {selectedPackage.id}
              </h2>
              <button
                onClick={() => setSelectedPackage(null)}
                className="text-gray-600 hover:text-gray-900"
              >
                ×
              </button>
            </div>
            
            <div className="px-6 py-4">
              <div className="space-y-6">
                <div>
                  <h3 className="text-lg font-medium text-gray-900 mb-2">Package Information</h3>
                  <div className="bg-gray-50 rounded-lg p-4 space-y-2 text-sm">
                    <div><strong>Created:</strong> {new Date(selectedPackage.created_at).toLocaleString()}</div>
                    <div><strong>Source Item ID:</strong> {selectedPackage.source_item_id}</div>
                    <div><strong>Content Count:</strong> {selectedPackage.content_count}</div>
                    <div><strong>File Count:</strong> {selectedPackage.file_count}</div>
                  </div>
                </div>
                
                {selectedPackage.has_research && (
                  <div>
                    <h3 className="text-lg font-medium text-gray-900 mb-2">Research Summary</h3>
                    <div className="bg-blue-50 rounded-lg p-4 text-sm text-blue-900">
                      Research context was included in this package generation.
                    </div>
                  </div>
                )}
                
                <div className="text-center py-4">
                  <p className="text-gray-600">
                    Full package details and content viewer will be available in the complete implementation.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default ContentPanel