import React, { useState, useEffect, useRef } from 'react'
import {
  PlusIcon,
  PaperAirplaneIcon,
  TrashIcon,
  ArchiveBoxIcon,
  ChatBubbleLeftRightIcon,
  UserIcon,
  CpuChipIcon,
  ClockIcon
} from '@heroicons/react/24/outline'
import LoadingSpinner from './LoadingSpinner'

const ChatPanel = () => {
  const [sessions, setSessions] = useState([])
  const [currentSession, setCurrentSession] = useState(null)
  const [messages, setMessages] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [isSending, setIsSending] = useState(false)
  const [newMessage, setNewMessage] = useState('')
  const [includeContext, setIncludeContext] = useState(true)
  const messagesEndRef = useRef(null)

  useEffect(() => {
    fetchSessions()
  }, [])

  useEffect(() => {
    if (currentSession) {
      fetchMessages(currentSession.id)
    }
  }, [currentSession])

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const fetchSessions = async () => {
    try {
      const response = await fetch('/api/chat/sessions')
      const data = await response.json()
      setSessions(data.data?.sessions || [])
    } catch (error) {
      console.error('Failed to fetch sessions:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const fetchMessages = async (sessionId) => {
    try {
      const response = await fetch(`/api/chat/sessions/${sessionId}/messages`)
      const data = await response.json()
      setMessages(data.data?.messages || [])
    } catch (error) {
      console.error('Failed to fetch messages:', error)
    }
  }

  const handleCreateSession = async (title) => {
    try {
      const response = await fetch('/api/chat/sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title })
      })
      
      const data = await response.json()
      if (response.ok) {
        const newSession = data.data
        setSessions([newSession, ...sessions])
        setCurrentSession(newSession)
        setMessages([])
      }
    } catch (error) {
      console.error('Failed to create session:', error)
    }
  }

  const handleSendMessage = async (e) => {
    e.preventDefault()
    
    if (!newMessage.trim()) return
    
    setIsSending(true)
    
    try {
      const request = {
        content: newMessage,
        session_id: currentSession?.id || null,
        include_sources: includeContext,
        max_context_items: 3
      }
      
      const response = await fetch('/api/chat/messages', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request)
      })
      
      const data = await response.json()
      if (response.ok) {
        const responseData = data.data
        
        // If no current session, this creates a new one
        if (!currentSession && responseData.session_id) {
          await fetchSessions()
          const newSession = sessions.find(s => s.id === responseData.session_id) ||
            { id: responseData.session_id, title: `Chat ${responseData.session_id}` }
          setCurrentSession(newSession)
        }
        
        // Refresh messages
        if (responseData.session_id) {
          await fetchMessages(responseData.session_id)
        }
        
        setNewMessage('')
      }
    } catch (error) {
      console.error('Failed to send message:', error)
    } finally {
      setIsSending(false)
    }
  }

  const handleDeleteSession = async (sessionId) => {
    if (!confirm('Are you sure you want to delete this conversation?')) {
      return
    }

    try {
      const response = await fetch(`/api/chat/sessions/${sessionId}`, {
        method: 'DELETE'
      })
      
      if (response.ok) {
        setSessions(sessions.filter(s => s.id !== sessionId))
        if (currentSession?.id === sessionId) {
          setCurrentSession(null)
          setMessages([])
        }
      }
    } catch (error) {
      console.error('Failed to delete session:', error)
    }
  }

  const handleArchiveSession = async (sessionId) => {
    try {
      const response = await fetch(`/api/chat/sessions/${sessionId}/archive`, {
        method: 'POST'
      })
      
      if (response.ok) {
        setSessions(sessions.filter(s => s.id !== sessionId))
        if (currentSession?.id === sessionId) {
          setCurrentSession(null)
          setMessages([])
        }
      }
    } catch (error) {
      console.error('Failed to archive session:', error)
    }
  }

  const formatTimestamp = (timestamp) => {
    return new Date(timestamp).toLocaleString()
  }

  const getMessageIcon = (role) => {
    switch (role) {
      case 'user':
        return <UserIcon className="w-6 h-6 text-blue-600" />
      case 'assistant':
        return <CpuChipIcon className="w-6 h-6 text-green-600" />
      default:
        return <ClockIcon className="w-6 h-6 text-gray-500" />
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
    <div className="flex h-[calc(100vh-200px)]">
      {/* Sessions Sidebar */}
      <div className="w-1/3 border-r border-gray-200 bg-white">
        <div className="px-4 py-4 border-b border-gray-200">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">Conversations</h2>
            <button
              onClick={() => handleCreateSession()}
              className="p-2 text-gray-600 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
              title="New conversation"
            >
              <PlusIcon className="w-5 h-5" />
            </button>
          </div>
        </div>
        
        <div className="overflow-y-auto flex-1">
          {sessions.length === 0 ? (
            <div className="text-center py-8 px-4">
              <ChatBubbleLeftRightIcon className="w-8 h-8 text-gray-300 mx-auto mb-3" />
              <p className="text-gray-600 text-sm">No conversations yet</p>
              <button
                onClick={() => handleCreateSession('New Chat')}
                className="mt-3 text-blue-600 text-sm hover:text-blue-700"
              >
                Start your first chat
              </button>
            </div>
          ) : (
            <div className="divide-y divide-gray-100">
              {sessions.map((session) => (
                <div
                  key={session.id}
                  className={`p-4 cursor-pointer hover:bg-gray-50 transition-colors ${
                    currentSession?.id === session.id ? 'bg-blue-50 border-r-2 border-blue-500' : ''
                  }`}
                  onClick={() => setCurrentSession(session)}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <h3 className="text-sm font-medium text-gray-900 truncate">
                        {session.title}
                      </h3>
                      <div className="flex items-center space-x-2 mt-1 text-xs text-gray-500">
                        <span>{session.message_count || 0} messages</span>
                        <span>•</span>
                        <span>{formatTimestamp(session.updated_at)}</span>
                      </div>
                    </div>
                    
                    <div className="flex items-center space-x-1 ml-2">
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          handleArchiveSession(session.id)
                        }}
                        className="p-1 text-gray-400 hover:text-orange-600 transition-colors"
                        title="Archive"
                      >
                        <ArchiveBoxIcon className="w-4 h-4" />
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          handleDeleteSession(session.id)
                        }}
                        className="p-1 text-gray-400 hover:text-red-600 transition-colors"
                        title="Delete"
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
      </div>

      {/* Chat Area */}
      <div className="flex-1 flex flex-col bg-gray-50">
        {currentSession ? (
          <>
            {/* Chat Header */}
            <div className="px-6 py-4 bg-white border-b border-gray-200">
              <h1 className="text-xl font-semibold text-gray-900">
                {currentSession.title}
              </h1>
              <p className="text-sm text-gray-600 mt-1">
                {messages.length} messages • Last updated {formatTimestamp(currentSession.updated_at)}
              </p>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
              {messages.length === 0 ? (
                <div className="text-center py-12">
                  <ChatBubbleLeftRightIcon className="w-12 h-12 text-gray-300 mx-auto mb-4" />
                  <p className="text-gray-600">Start the conversation by sending a message</p>
                </div>
              ) : (
                messages.map((message) => (
                  <div
                    key={message.id}
                    className={`flex items-start space-x-3 ${
                      message.role === 'user' ? 'justify-end' : 'justify-start'
                    }`}
                  >
                    {message.role === 'assistant' && (
                      <div className="flex-shrink-0 mt-1">
                        {getMessageIcon(message.role)}
                      </div>
                    )}
                    
                    <div
                      className={`max-w-3xl px-4 py-3 rounded-lg ${
                        message.role === 'user'
                          ? 'bg-blue-600 text-white'
                          : 'bg-white border border-gray-200 text-gray-900'
                      }`}
                    >
                      <div className="whitespace-pre-wrap">{message.content}</div>
                      <div
                        className={`text-xs mt-2 ${
                          message.role === 'user' ? 'text-blue-100' : 'text-gray-500'
                        }`}
                      >
                        {formatTimestamp(message.timestamp)}
                        {message.provider && (
                          <span className="ml-2">via {message.provider}</span>
                        )}
                      </div>
                    </div>
                    
                    {message.role === 'user' && (
                      <div className="flex-shrink-0 mt-1">
                        {getMessageIcon(message.role)}
                      </div>
                    )}
                  </div>
                ))
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Message Input */}
            <div className="px-6 py-4 bg-white border-t border-gray-200">
              <form onSubmit={handleSendMessage} className="space-y-3">
                <div className="flex items-center space-x-3">
                  <label className="flex items-center text-sm text-gray-600">
                    <input
                      type="checkbox"
                      checked={includeContext}
                      onChange={(e) => setIncludeContext(e.target.checked)}
                      className="mr-2"
                    />
                    Include context from sources
                  </label>
                </div>
                
                <div className="flex space-x-3">
                  <textarea
                    value={newMessage}
                    onChange={(e) => setNewMessage(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault()
                        handleSendMessage(e)
                      }
                    }}
                    className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                    rows={3}
                    placeholder="Type your message... (Press Enter to send, Shift+Enter for new line)"
                    disabled={isSending}
                  />
                  <button
                    type="submit"
                    disabled={!newMessage.trim() || isSending}
                    className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {isSending ? (
                      <LoadingSpinner size="small" />
                    ) : (
                      <PaperAirplaneIcon className="w-5 h-5" />
                    )}
                  </button>
                </div>
              </form>
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <ChatBubbleLeftRightIcon className="w-16 h-16 text-gray-300 mx-auto mb-4" />
              <h2 className="text-xl font-semibold text-gray-900 mb-2">
                Welcome to Sourcerer Chat
              </h2>
              <p className="text-gray-600 mb-6">
                Select a conversation from the sidebar or start a new one
              </p>
              <button
                onClick={() => handleCreateSession('New Chat')}
                className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                <PlusIcon className="w-4 h-4 mr-2" />
                Start New Conversation
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default ChatPanel