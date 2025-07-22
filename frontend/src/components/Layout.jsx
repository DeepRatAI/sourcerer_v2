import React from 'react'
import { Link, useLocation } from 'react-router-dom'
import { 
  CogIcon, 
  HomeIcon,
  ChatBubbleLeftRightIcon,
  DocumentTextIcon,
  ServerIcon,
  SparklesIcon
} from '@heroicons/react/24/outline'

const Layout = ({ children, config, onConfigUpdate }) => {
  const location = useLocation()
  
  const navigation = [
    { name: 'Dashboard', href: '/', icon: HomeIcon },
    { name: 'Sources', href: '/sources', icon: DocumentTextIcon },
    { name: 'Content', href: '/content', icon: SparklesIcon },
    { name: 'Chat', href: '/chat', icon: ChatBubbleLeftRightIcon },
    { name: 'Configuration', href: '/config', icon: CogIcon }
  ]

  const isActive = (href) => {
    if (href === '/') {
      return location.pathname === '/'
    }
    return location.pathname.startsWith(href)
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Sidebar */}
      <div className="fixed inset-y-0 left-0 w-64 bg-white shadow-lg">
        <div className="flex flex-col h-full">
          {/* Logo */}
          <div className="flex items-center px-6 py-4 border-b border-gray-200">
            <ServerIcon className="w-8 h-8 text-blue-600 mr-3" />
            <h1 className="text-xl font-bold text-gray-900">Sourcerer</h1>
          </div>

          {/* Navigation */}
          <nav className="flex-1 px-4 py-6 space-y-2">
            {navigation.map((item) => {
              const Icon = item.icon
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={`
                    flex items-center px-4 py-3 text-sm font-medium rounded-lg transition-colors
                    ${isActive(item.href)
                      ? 'bg-blue-50 text-blue-700 border-r-2 border-blue-700'
                      : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                    }
                  `}
                >
                  <Icon className="w-5 h-5 mr-3" />
                  {item.name}
                </Link>
              )
            })}
          </nav>

          {/* Status */}
          <div className="px-6 py-4 border-t border-gray-200">
            <div className="text-xs text-gray-500 mb-2">Active Provider</div>
            <div className="text-sm font-medium text-gray-900">
              {config?.active_provider || 'None'}
            </div>
            {config?.active_model && (
              <div className="text-xs text-gray-500 mt-1">
                Model: {config.active_model}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className="ml-64">
        <main className="p-8">
          {children}
        </main>
      </div>
    </div>
  )
}

export default Layout