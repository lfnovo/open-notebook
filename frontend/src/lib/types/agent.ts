/**
 * Agent API Types
 */

// Tool call information
export interface ToolCallInfo {
  tool: string
  input: Record<string, unknown>
  output?: string
}

// Agent message
export interface AgentMessage {
  role: 'user' | 'assistant' | 'tool'
  content: string
  tool_calls?: ToolCallInfo[]
}

// Agent execute request
export interface AgentExecuteRequest {
  message: string
  thread_id: string
  notebook_id?: string
  model_override?: string
  api_key?: string
  stream?: boolean
}

// Agent execute response
export interface AgentExecuteResponse {
  thread_id: string
  messages: AgentMessage[]
  final_response?: string
}

// Stream event types
export interface AgentStreamEvent {
  type: 'thinking' | 'tool_call' | 'tool_result' | 'response' | 'done' | 'error'
  content?: string
  tool?: string
  input?: Record<string, unknown>
  output?: string
}

// Supported model info
export interface AgentModelInfo {
  id: string
  name: string
  provider: string
  provider_type: string
  description: string
}

// Tool info
export interface AgentToolInfo {
  name: string
  description: string
  parameters?: Record<string, unknown>
  required?: string[]
}

// Agent models response
export interface AgentModelsResponse {
  models: AgentModelInfo[]
  providers: Record<string, {
    provider: string
    models: string[]
    description: string
  }>
}

// Agent tools response
export interface AgentToolsResponse {
  tools: AgentToolInfo[]
}
