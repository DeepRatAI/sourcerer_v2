import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { 
  PlusIcon, 
  ServerIcon, 
  DocumentTextIcon, 
  ChatBubbleLeftRightIcon,
  ExclamationTriangleIcon,
  SparklesIcon
} from '@heroicons/react/24/outline'
import LoadingSpinner from './LoadingSpinner'

const Dashboard = ({ config }) => {
  const [stats, setStats] = useState({
    providers: 0,
    sources: 0,
    chats: 0,
    packages: 0
  })
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    // Simulate loading stats
    const timer = setTimeout(() => {
      setStats({
        providers: Object.keys(config?.providers || {}).length,
        sources: 0, // Will be updated when sources are implemented
        chats: 0, // Will be updated when chat is implemented  
        packages: 0 // Will be updated when content generation is implemented
      })
      setIsLoading(false)
    }, 500)

    return () => clearTimeout(timer)
  }, [config])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <LoadingSpinner size="large" />
      </div>
    )
  }

  const hasIssues = !config?.active_provider || Object.keys(config?.providers || {}).length === 0

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Dashboard</h1>
        <p className="text-gray-600">
          Welcome to your Sourcerer content generation system
        </p>
      </div>

      {/* Status Banner */}
      {hasIssues && (
        <div className="mb-8 bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <div className="flex items-center">
            <ExclamationTriangleIcon className="w-5 h-5 text-yellow-600 mr-2" />
            <div className="flex-1">
              <h3 className="text-sm font-medium text-yellow-800">Configuration Needed</h3>
              <p className="text-sm text-yellow-700 mt-1">
                Please configure at least one LLM provider to start using Sourcerer.
              </p>
            </div>
            <a 
              href="/config/providers"
              className="ml-4 px-3 py-1 bg-yellow-600 text-white text-sm rounded hover:bg-yellow-700 transition-colors"
            >
              Configure Now
            </a>
          </div>
        </div>
      )}

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-medium text-gray-500">Providers</h3>
            <ServerIcon className="w-5 h-5 text-blue-500" />
          </div>
          <p className="text-3xl font-bold text-gray-900">{stats.providers}</p>
          <p className="text-sm text-gray-500 mt-1">
            {config?.active_provider ? `Active: ${config.active_provider}` : 'None active'}
          </p>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-medium text-gray-500">Sources</h3>
            <DocumentTextIcon className="w-5 h-5 text-green-500" />
          </div>
          <p className="text-3xl font-bold text-gray-900">{stats.sources}</p>
          <p className="text-sm text-gray-500 mt-1">Content sources</p>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-medium text-gray-500">Conversations</h3>
            <ChatBubbleLeftRightIcon className="w-5 h-5 text-purple-500" />
          </div>
          <p className="text-3xl font-bold text-gray-900">{stats.chats}</p>
          <p className="text-sm text-gray-500 mt-1">Chat sessions</p>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-medium text-gray-500">Content Packages</h3>
            <DocumentTextIcon className="w-5 h-5 text-orange-500" />
          </div>
          <p className="text-3xl font-bold text-gray-900">{stats.packages}</p>
          <p className="text-sm text-gray-500 mt-1">Generated content</p>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="bg-white rounded-lg shadow p-6 mb-8">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Link to="/sources" className="flex items-center justify-center px-4 py-6 border-2 border-dashed border-gray-300 rounded-lg hover:border-gray-400 hover:bg-gray-50 transition-colors">
            <div className="text-center">
              <PlusIcon className="w-8 h-8 text-gray-400 mx-auto mb-2" />
              <span className="text-sm font-medium text-gray-600">Add Source</span>
              <p className="text-xs text-gray-500 mt-1">Configure a new content source</p>
            </div>
          </Link>

          <Link to="/chat" className="flex items-center justify-center px-4 py-6 border-2 border-dashed border-gray-300 rounded-lg hover:border-gray-400 hover:bg-gray-50 transition-colors">
            <div className="text-center">
              <ChatBubbleLeftRightIcon className="w-8 h-8 text-gray-400 mx-auto mb-2" />
              <span className="text-sm font-medium text-gray-600">Start Chat</span>
              <p className="text-xs text-gray-500 mt-1">Begin a new conversation</p>
            </div>
          </Link>

          <Link to="/content" className="flex items-center justify-center px-4 py-6 border-2 border-dashed border-gray-300 rounded-lg hover:border-gray-400 hover:bg-gray-50 transition-colors">
            <div className="text-center">
              <SparklesIcon className="w-8 h-8 text-gray-400 mx-auto mb-2" />
              <span className="text-sm font-medium text-gray-600">Generate Content</span>
              <p className="text-xs text-gray-500 mt-1">Create new content package</p>
            </div>
          </Link>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Recent Activity</h2>
        <div className="text-center py-8 text-gray-500">
          <DocumentTextIcon className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <p>No recent activity</p>
          <p className="text-sm mt-1">Your activity will appear here once you start using Sourcerer</p>
        </div>
      </div>
    </div>
  )
}

export default Dashboard