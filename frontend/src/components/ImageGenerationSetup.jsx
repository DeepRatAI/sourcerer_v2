import React, { useState } from 'react'
import { PhotoIcon, XMarkIcon } from '@heroicons/react/24/outline'

const ImageGenerationSetup = ({ onComplete, onSkip, onBack, hasOpenAI }) => {
  const [enableGeneration, setEnableGeneration] = useState(hasOpenAI)

  const handleEnable = () => {
    setEnableGeneration(true)
    onComplete(true)
  }

  const handleSkip = () => {
    onSkip()
  }

  return (
    <div className="text-center">
      <div className="mb-8">
        <div className="mx-auto w-24 h-24 bg-purple-100 rounded-full flex items-center justify-center">
          <PhotoIcon className="w-12 h-12 text-purple-600" />
        </div>
      </div>

      <h2 className="text-2xl font-bold text-gray-900 mb-4">
        Image Generation Setup
      </h2>
      <p className="text-gray-600 mb-8 max-w-md mx-auto">
        Enable image generation to create visual content for your posts. 
        This feature uses OpenAI's DALL-E model.
      </p>

      <div className="bg-gray-50 rounded-lg p-6 mb-8 max-w-md mx-auto">
        <h3 className="font-semibold text-gray-900 mb-3">Image Generation Features:</h3>
        <ul className="text-sm text-gray-600 space-y-2 text-left">
          <li>• Generate cover images for content</li>
          <li>• Create visual assets for social media</li>
          <li>• Automatically generate image prompts</li>
          <li>• Support for multiple aspect ratios</li>
        </ul>
      </div>

      {hasOpenAI ? (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-6">
          <p className="text-green-800 text-sm">
            ✓ OpenAI provider detected - Image generation can be enabled
          </p>
        </div>
      ) : (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
          <p className="text-yellow-800 text-sm">
            OpenAI provider not configured. You can enable this later in the configuration panel.
          </p>
        </div>
      )}

      <div className="flex space-x-4 justify-center">
        {hasOpenAI ? (
          <button
            onClick={handleEnable}
            className="px-6 py-3 bg-purple-600 text-white rounded-lg font-semibold hover:bg-purple-700 transition-colors"
          >
            Enable Image Generation
          </button>
        ) : null}
        
        <button
          onClick={handleSkip}
          className="px-6 py-3 border border-gray-300 text-gray-700 rounded-lg font-semibold hover:bg-gray-50 transition-colors"
        >
          Skip for Now
        </button>
      </div>

      <div className="flex justify-between pt-8">
        <button
          onClick={onBack}
          className="px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors"
        >
          ← Back
        </button>
      </div>
    </div>
  )
}

export default ImageGenerationSetup