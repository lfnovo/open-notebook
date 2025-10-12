'use client'

import { useState, useCallback } from 'react'
import { toast } from 'sonner'
import { searchApi } from '@/lib/api/search'
import { AskStreamEvent } from '@/lib/types/search'

interface AskModels {
  strategy: string
  answer: string
  finalAnswer: string
}

interface StrategyData {
  reasoning: string
  searches: Array<{ term: string; instructions: string }>
}

interface AskState {
  isStreaming: boolean
  strategy: StrategyData | null
  answers: string[]
  finalAnswer: string | null
  error: string | null
}

export function useAsk() {
  const [state, setState] = useState<AskState>({
    isStreaming: false,
    strategy: null,
    answers: [],
    finalAnswer: null,
    error: null
  })

  const sendAsk = useCallback(async (question: string, models: AskModels) => {
    // Validate inputs
    if (!question.trim()) {
      toast.error('Please enter a question')
      return
    }

    if (!models.strategy || !models.answer || !models.finalAnswer) {
      toast.error('Please configure all required models')
      return
    }

    // Reset state
    setState({
      isStreaming: true,
      strategy: null,
      answers: [],
      finalAnswer: null,
      error: null
    })

    try {
      const response = await searchApi.askKnowledgeBase({
        question,
        strategy_model: models.strategy,
        answer_model: models.answer,
        final_answer_model: models.finalAnswer
      })

      if (!response) {
        throw new Error('No response body received from server')
      }

      const reader = response.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()

        if (done) {
          break
        }

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')

        // Keep the last incomplete line in buffer
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const jsonStr = line.slice(6).trim()
              if (!jsonStr) continue

              const data: AskStreamEvent = JSON.parse(jsonStr)

              if (data.type === 'strategy') {
                setState(prev => ({
                  ...prev,
                  strategy: {
                    reasoning: data.reasoning || '',
                    searches: data.searches || []
                  }
                }))
              } else if (data.type === 'answer') {
                setState(prev => ({
                  ...prev,
                  answers: [...prev.answers, data.content || '']
                }))
              } else if (data.type === 'final_answer') {
                setState(prev => ({
                  ...prev,
                  finalAnswer: data.content || '',
                  isStreaming: false
                }))
              } else if (data.type === 'complete') {
                setState(prev => ({
                  ...prev,
                  isStreaming: false
                }))
              } else if (data.type === 'error') {
                throw new Error(data.message || 'Stream error occurred')
              }
            } catch (e) {
              console.error('Error parsing SSE data:', e, 'Line:', line)
              // Don't throw - continue processing other lines
            }
          }
        }
      }

      // Ensure streaming is stopped
      setState(prev => ({ ...prev, isStreaming: false }))

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'An unexpected error occurred'
      console.error('Ask error:', error)

      setState(prev => ({
        ...prev,
        isStreaming: false,
        error: errorMessage
      }))

      toast.error('Ask failed', {
        description: errorMessage
      })
    }
  }, [])

  const reset = useCallback(() => {
    setState({
      isStreaming: false,
      strategy: null,
      answers: [],
      finalAnswer: null,
      error: null
    })
  }, [])

  return {
    ...state,
    sendAsk,
    reset
  }
}
