/**
 * Agent Hook
 * Manages agent state and interactions
 */

import { useState, useCallback, useRef } from 'react'
import { agentApi } from '../api/agent'
import type {
  AgentStreamEvent,
  AgentModelInfo,
  ToolCallInfo,
} from '../types/agent'

// Agent execution step for UI display
export interface AgentStep {
  id: string
  type: 'thinking' | 'tool_call' | 'tool_result' | 'response' | 'error'
  content?: string
  tool?: string
  toolInput?: Record<string, unknown>
  toolOutput?: string
  timestamp: Date
}

// Agent conversation message
export interface AgentConversationMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  steps?: AgentStep[]
  timestamp: Date
}

interface UseAgentOptions {
  notebookId?: string
  apiKey?: string
  modelOverride?: string
}

export function useAgent(options: UseAgentOptions = {}) {
  const { notebookId, apiKey, modelOverride } = options

  // State
  const [messages, setMessages] = useState<AgentConversationMessage[]>([])
  const [currentSteps, setCurrentSteps] = useState<AgentStep[]>([])
  const [isRunning, setIsRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [models, setModels] = useState<AgentModelInfo[]>([])
  const [selectedModel, setSelectedModel] = useState<string>(modelOverride || '')

  // Refs
  const threadIdRef = useRef<string>(`agent-${Date.now()}`)
  const abortControllerRef = useRef<AbortController | null>(null)

  // Generate unique ID
  const generateId = () => `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`

  // Load available models
  const loadModels = useCallback(async () => {
    try {
      const response = await agentApi.getModels()
      setModels(response.models)
      if (!selectedModel && response.models.length > 0) {
        setSelectedModel(response.models[0].id)
      }
    } catch (err) {
      console.error('Failed to load models:', err)
    }
  }, [selectedModel])

  // Send message to agent
  const sendMessage = useCallback(async (message: string) => {
    if (!message.trim() || isRunning) return

    setIsRunning(true)
    setError(null)
    setCurrentSteps([])

    // Add user message
    const userMessage: AgentConversationMessage = {
      id: generateId(),
      role: 'user',
      content: message,
      timestamp: new Date(),
    }
    setMessages(prev => [...prev, userMessage])

    // Prepare steps collection for this response
    const steps: AgentStep[] = []

    try {
      // Stream agent response
      for await (const event of agentApi.stream({
        message,
        thread_id: threadIdRef.current,
        notebook_id: notebookId,
        api_key: apiKey,
        model_override: selectedModel || modelOverride,
      })) {
        const step: AgentStep = {
          id: generateId(),
          type: event.type as AgentStep['type'],
          timestamp: new Date(),
        }

        switch (event.type) {
          case 'thinking':
            step.content = event.content || '思考中...'
            break
          case 'tool_call':
            step.tool = event.tool
            step.toolInput = event.input
            step.content = `调用工具: ${event.tool}`
            break
          case 'tool_result':
            step.tool = event.tool
            step.toolOutput = event.output
            step.content = `工具结果: ${event.tool}`
            break
          case 'response':
            step.content = event.content
            break
          case 'error':
            step.content = event.content || '执行出错'
            setError(event.content || '执行出错')
            break
        }

        if (event.type !== 'done') {
          steps.push(step)
          setCurrentSteps([...steps])
        }

        // If we got a final response, add it as assistant message
        if (event.type === 'response' && event.content) {
          const assistantMessage: AgentConversationMessage = {
            id: generateId(),
            role: 'assistant',
            content: event.content,
            steps: [...steps],
            timestamp: new Date(),
          }
          setMessages(prev => [...prev, assistantMessage])
        }
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '执行失败'
      setError(errorMessage)
      
      // Add error as a step
      const errorStep: AgentStep = {
        id: generateId(),
        type: 'error',
        content: errorMessage,
        timestamp: new Date(),
      }
      steps.push(errorStep)
      setCurrentSteps([...steps])
    } finally {
      setIsRunning(false)
    }
  }, [notebookId, apiKey, selectedModel, modelOverride, isRunning])

  // Clear conversation
  const clearConversation = useCallback(() => {
    setMessages([])
    setCurrentSteps([])
    setError(null)
    threadIdRef.current = `agent-${Date.now()}`
  }, [])

  // Stop current execution
  const stop = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
    setIsRunning(false)
  }, [])

  return {
    // State
    messages,
    currentSteps,
    isRunning,
    error,
    models,
    selectedModel,
    
    // Actions
    sendMessage,
    clearConversation,
    stop,
    loadModels,
    setSelectedModel,
  }
}
