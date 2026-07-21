'use client'

import { useState, useCallback, useRef, useEffect } from 'react'
import { toast } from 'sonner'
import { useTranslation } from '@/lib/hooks/use-translation'
import { getApiErrorMessage } from '@/lib/utils/error-handler'
import { searchApi } from '@/lib/api/search'
import { API_TIMEOUT_MS } from '@/lib/api/client'
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

// Idle watchdog for the SSE stream: if no bytes arrive for this long, treat the
// connection as dangling (e.g. a Docker/standalone proxy that doesn't propagate
// the "done" signal), abort the socket and end the loading state.
//
// This is an *idle* timeout — it is re-armed on every received chunk — not a
// wall-clock cap, so a slow-but-healthy stream never trips it. The window is
// aligned to the same budget as the API client (NEXT_PUBLIC_API_TIMEOUT_MS,
// default 10 min; 0 disables the timeout) so slow local models (Ollama, LM
// Studio) that legitimately take a while between events aren't cut off mid-stream.
const STREAM_IDLE_TIMEOUT_MS = API_TIMEOUT_MS

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

  // (Re)arm the idle watchdog. Called at stream start and on every received
  // chunk, so the timer only fires when the connection goes genuinely silent.
  // On fire it aborts the in-flight request (freeing the socket/reader — the
  // `catch` swallows the resulting AbortError) and clears the loading state.
  const armStreamTimeout = useCallback(() => {
    clearStreamTimeout()
    if (STREAM_IDLE_TIMEOUT_MS <= 0) return // 0 = watchdog disabled
    streamTimeoutRef.current = setTimeout(() => {
      abortControllerRef.current?.abort()
      if (mountedRef.current) {
        setState(prev => (prev.isStreaming ? { ...prev, isStreaming: false } : prev))
      }
    }, STREAM_IDLE_TIMEOUT_MS)
  }, [clearStreamTimeout])

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

    // Arm the idle watchdog; it is re-armed on every received chunk below.
    armStreamTimeout()

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

        // Activity on the connection — reset the idle watchdog.
        armStreamTimeout()

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
  }, [t, stopStreaming, armStreamTimeout])

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
