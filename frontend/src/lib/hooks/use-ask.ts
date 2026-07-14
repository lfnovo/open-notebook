'use client'

import { useState, useCallback, useRef, useEffect } from 'react'
import { toast } from 'sonner'
import { useTranslation } from '@/lib/hooks/use-translation'
import { getApiErrorMessage } from '@/lib/utils/error-handler'
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

// Safety net: if the stream connection hangs without proper termination
// (e.g. Docker/standalone proxy doesn't propagate the "done" signal),
// force the loading state to end after this timeout.
const STREAM_TIMEOUT_MS = 75_000 // 75 seconds — prevents permanent hang on dangling connections

export function useAsk() {
  const { t } = useTranslation()
  const [state, setState] = useState<AskState>({
    isStreaming: false,
    strategy: null,
    answers: [],
    finalAnswer: null,
    error: null
  })
  const streamTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const abortControllerRef = useRef<AbortController | null>(null)
  const mountedRef = useRef(true)

  useEffect(() => {
    return () => {
      mountedRef.current = false
      if (streamTimeoutRef.current) {
        clearTimeout(streamTimeoutRef.current)
      }
      if (abortControllerRef.current) {
        abortControllerRef.current.abort()
      }
    }
  }, [])

  const clearStreamTimeout = useCallback(() => {
    if (streamTimeoutRef.current) {
      clearTimeout(streamTimeoutRef.current)
      streamTimeoutRef.current = null
    }
  }, [])

  const stopStreaming = useCallback((finalAnswer?: string | null) => {
    clearStreamTimeout()
    if (mountedRef.current) {
      setState(prev => ({
        ...prev,
        isStreaming: false,
        ...(finalAnswer !== undefined ? { finalAnswer } : {})
      }))
    }
  }, [clearStreamTimeout])

  const sendAsk = useCallback(async (question: string, models: AskModels) => {
    // Validate inputs
    if (!question.trim()) {
      toast.error(t('apiErrors.pleaseEnterQuestion'))
      return
    }

    if (!models.strategy || !models.answer || !models.finalAnswer) {
      toast.error(t('apiErrors.pleaseConfigureModels'))
      return
    }

    // Abort any previous in-flight request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
    abortControllerRef.current = new AbortController()
    const signal = abortControllerRef.current.signal

    // Reset state
    setState({
      isStreaming: true,
      strategy: null,
      answers: [],
      finalAnswer: null,
      error: null
    })

    // Safety timeout: force loading to end if stream doesn't complete
    streamTimeoutRef.current = setTimeout(() => {
      if (mountedRef.current) {
        setState(prev => {
          if (prev.isStreaming) {
            return { ...prev, isStreaming: false }
          }
          return prev
        })
      }
    }, STREAM_TIMEOUT_MS)

    try {
      const response = await searchApi.askKnowledgeBase({
        question,
        strategy_model: models.strategy,
        answer_model: models.answer,
        final_answer_model: models.finalAnswer
      }, signal)

      if (!response) {
        stopStreaming()
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
                stopStreaming(data.content || '')
              } else if (data.type === 'complete') {
                stopStreaming(data.final_answer ?? undefined)
              } else if (data.type === 'error') {
                stopStreaming()
                throw new Error(data.message || 'Stream error occurred')
              }
            } catch (e) {
              if (e instanceof SyntaxError) {
                console.error('Error parsing SSE data:', e, 'Line:', line)
                // Don't throw - continue processing other lines
              } else {
                stopStreaming()
                throw e
              }
            }
          }
        }
      }

      // Stream ended normally — clear the safety timeout
      stopStreaming()

    } catch (error) {
      // If aborted by the safety timeout, don't show an error toast
      if (error instanceof DOMException && error.name === 'AbortError') {
        return
      }

      const err = error as { message?: string }
      const errorMessage = err.message || 'An unexpected error occurred'
      console.error('Ask error:', error)

      if (mountedRef.current) {
        setState(prev => ({
          ...prev,
          isStreaming: false,
          error: errorMessage
        }))
      }

      toast.error(t('apiErrors.askFailed'), {
        description: getApiErrorMessage(errorMessage, (key) => t(key))
      })
    }
  }, [t, stopStreaming])

  const reset = useCallback(() => {
    clearStreamTimeout()
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }
    setState({
      isStreaming: false,
      strategy: null,
      answers: [],
      finalAnswer: null,
      error: null
    })
  }, [clearStreamTimeout])

  return {
    ...state,
    sendAsk,
    reset
  }
}
