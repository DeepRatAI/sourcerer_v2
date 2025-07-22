import React, { useState, useEffect } from 'react'
import {
  PlusIcon,
  RssIcon,
  GlobeAltIcon,
  TrashIcon,
  PlayIcon,
  PauseIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  ClockIcon
} from '@heroicons/react/24/outline'
import LoadingSpinner from './LoadingSpinner'

const SourcesPanel = () => {
  const [sources, setSources] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [showAddForm, setShowAddForm] = useState(false)
  const [newSource, setNewSource] = useState({
    name: '',
    type: 'rss',
    url: '',
    refresh_interval: 3600
  })

  useEffect(() => {
    fetchSources()
  }, [])

  const fetchSources = async () => {
    try {
      const response = await fetch('/api/sources/')
      const data = await response.json()
      setSources(data.data || [])
    } catch (error) {
      console.error('Failed to fetch sources:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleAddSource = async (e) => {
    e.preventDefault()
    
    try {
      const response = await fetch('/api/sources/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newSource)
      })
      
      if (response.ok) {
        setShowAddForm(false)
        setNewSource({ name: '', type: 'rss', url: '', refresh_interval: 3600 })
        await fetchSources()
      }
    } catch (error) {
      console.error('Failed to add source:', error)
    }
  }

  const handleDeleteSource = async (sourceId) => {
    if (!confirm('Are you sure you want to delete this source?')) {
      return
    }

    try {
      const response = await fetch(`/api/sources/${sourceId}`, {
        method: 'DELETE'
      })
      
      if (response.ok) {
        await fetchSources()
      }
    } catch (error) {
      console.error('Failed to delete source:', error)
    }
  }

  const handleToggleSource = async (sourceId, isActive) => {
    try {
      const action = isActive ? 'pause' : 'activate'
      const response = await fetch(`/api/sources/${sourceId}/${action}`, {
        method: 'POST'
      })
      
      if (response.ok) {
        await fetchSources()
      }
    } catch (error) {
      console.error(`Failed to ${action} source:`, error)
    }
  }

  const handleRefreshSource = async (sourceId) => {
    try {
      const response = await fetch(`/api/sources/${sourceId}/refresh`, {
        method: 'POST'
      })
      
      if (response.ok) {
        await fetchSources()
      }
    } catch (error) {
      console.error('Failed to refresh source:', error)
    }
  }

  const getStatusIcon = (status) => {
    switch (status) {
      case 'active':
        return <CheckCircleIcon className="w-5 h-5 text-green-500" />
      case 'paused':
        return <PauseIcon className="w-5 h-5 text-yellow-500" />
      case 'error':
        return <ExclamationTriangleIcon className="w-5 h-5 text-red-500" />
      case 'syncing':
        return <ClockIcon className="w-5 h-5 text-blue-500" />
      default:
        return <ClockIcon className="w-5 h-5 text-gray-500" />
    }
  }

  const getSourceIcon = (type) => {
    switch (type) {
      case 'rss':
        return <RssIcon className="w-5 h-5 text-orange-500" />
      case 'html':
        return <GlobeAltIcon className="w-5 h-5 text-blue-500" />
      default:
        return <GlobeAltIcon className="w-5 h-5 text-gray-500" />
    }
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
          <h1 className="text-3xl font-bold text-gray-900">Content Sources</h1>
          <p className="text-gray-600 mt-1">
            Manage your RSS feeds and web sources for content aggregation
          </p>
        </div>
        <button
          onClick={() => setShowAddForm(true)}
          className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          <PlusIcon className="w-4 h-4 mr-2" />
          Add Source
        </button>
      </div>

      {/* Stats Overview */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-500">Total Sources</span>
          </div>
          <p className="text-3xl font-bold text-gray-900">{sources.length}</p>
        </div>
        
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-500">Active Sources</span>
          </div>
          <p className="text-3xl font-bold text-green-600">
            {sources.filter(s => s.status === 'active').length}
          </p>
        </div>
        
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-500">Total Items</span>
          </div>
          <p className="text-3xl font-bold text-blue-600">
            {sources.reduce((sum, s) => sum + (s.item_count || 0), 0)}
          </p>
        </div>
        
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-500">Errors</span>
          </div>
          <p className="text-3xl font-bold text-red-600">
            {sources.filter(s => s.status === 'error').length}
          </p>
        </div>
      </div>

      {/* Add Source Form */}
      {showAddForm && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Add New Source</h2>
          <form onSubmit={handleAddSource} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Source Name
                </label>
                <input
                  type="text"
                  value={newSource.name}
                  onChange={(e) => setNewSource({ ...newSource, name: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="My RSS Feed"
                  required
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Source Type
                </label>
                <select
                  value={newSource.type}
                  onChange={(e) => setNewSource({ ...newSource, type: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="rss">RSS Feed</option>
                  <option value="html">HTML Page</option>
                </select>
              </div>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                URL
              </label>
              <input
                type="url"
                value={newSource.url}
                onChange={(e) => setNewSource({ ...newSource, url: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="https://example.com/feed.xml"
                required
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Refresh Interval (seconds)
              </label>
              <input
                type="number"
                value={newSource.refresh_interval}
                onChange={(e) => setNewSource({ ...newSource, refresh_interval: parseInt(e.target.value) })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                min="300"
                placeholder="3600"
              />
            </div>
            
            <div className="flex justify-end space-x-3">
              <button
                type="button"
                onClick={() => setShowAddForm(false)}
                className="px-4 py-2 text-gray-700 border border-gray-300 rounded-md hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
              >
                Add Source
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Sources List */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Sources</h2>
        </div>
        
        {sources.length === 0 ? (
          <div className="text-center py-12">
            <RssIcon className="w-12 h-12 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No sources configured</h3>
            <p className="text-gray-600 mb-6">Add your first content source to start aggregating content</p>
            <button
              onClick={() => setShowAddForm(true)}
              className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              <PlusIcon className="w-4 h-4 mr-2" />
              Add Source
            </button>
          </div>
        ) : (
          <div className="divide-y divide-gray-200">
            {sources.map((source) => (
              <div key={source.id} className="px-6 py-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-4">
                    {getSourceIcon(source.type)}
                    <div>
                      <h3 className="text-lg font-medium text-gray-900">{source.name}</h3>
                      <p className="text-sm text-gray-600">{source.url}</p>
                      <div className="flex items-center space-x-4 mt-1">
                        <div className="flex items-center space-x-1">
                          {getStatusIcon(source.status)}
                          <span className="text-sm text-gray-500 capitalize">{source.status}</span>
                        </div>
                        <span className="text-sm text-gray-500">
                          {source.item_count || 0} items
                        </span>
                        {source.last_sync && (
                          <span className="text-sm text-gray-500">
                            Last sync: {new Date(source.last_sync).toLocaleString()}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => handleRefreshSource(source.id)}
                      className="p-2 text-gray-600 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                      title="Refresh now"
                    >
                      <ClockIcon className="w-4 h-4" />
                    </button>
                    
                    <button
                      onClick={() => handleToggleSource(source.id, source.status === 'active')}
                      className={`p-2 rounded-lg transition-colors ${
                        source.status === 'active'
                          ? 'text-yellow-600 hover:text-yellow-700 hover:bg-yellow-50'
                          : 'text-green-600 hover:text-green-700 hover:bg-green-50'
                      }`}
                      title={source.status === 'active' ? 'Pause' : 'Activate'}
                    >
                      {source.status === 'active' ? (
                        <PauseIcon className="w-4 h-4" />
                      ) : (
                        <PlayIcon className="w-4 h-4" />
                      )}
                    </button>
                    
                    <button
                      onClick={() => handleDeleteSource(source.id)}
                      className="p-2 text-gray-600 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                      title="Delete source"
                    >
                      <TrashIcon className="w-4 h-4" />
                    </button>
                  </div>
                </div>
                
                {source.error_message && (
                  <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-md">
                    <p className="text-sm text-red-700">{source.error_message}</p>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default SourcesPanel