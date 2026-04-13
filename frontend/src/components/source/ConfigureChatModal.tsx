'use client'
import { useState } from 'react'

export function ConfigureChatModal({ currentConfig, onSave, onClose }: any) {
  const [goal, setGoal] = useState(currentConfig.goal)
  const [length, setLength] = useState(currentConfig.length)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-2xl p-6 w-full max-w-lg shadow-xl">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold">Configure chat</h2>
          <button onClick={onClose} className="text-gray-500 hover:text-black text-2xl">×</button>
        </div>
        
        <p className="text-gray-600 text-sm mb-6">Notebooks can be customised to help you achieve different goals.</p>

        <div className="space-y-6">
          {/* Goal Selection */}
          <div>
            <label className="block text-sm font-medium mb-2">Define your conversational goal</label>
            <div className="flex gap-2">
              {['Default', 'Learning guide', 'Custom'].map((opt) => (
                <button
                  key={opt}
                  onClick={() => setGoal(opt)}
                  className={`px-4 py-2 rounded-full border text-sm ${goal === opt ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-gray-700'}`}
                >
                  {opt}
                </button>
              ))}
            </div>
          </div>

          {/* Length Selection */}
          <div>
            <label className="block text-sm font-medium mb-2">Choose your response length</label>
            <div className="flex gap-2">
              {['Default', 'Longer', 'Shorter'].map((opt) => (
                <button
                  key={opt}
                  onClick={() => setLength(opt)}
                  className={`px-4 py-2 rounded-full border text-sm ${length === opt ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-gray-700'}`}
                >
                  {opt}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="flex justify-end mt-8">
          <button 
            onClick={() => onSave({ goal, length })}
            className="bg-blue-600 text-white px-6 py-2 rounded-full font-medium hover:bg-blue-700"
          >
            Save
          </button>
        </div>
      </div>
    </div>
  )
}
