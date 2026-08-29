export interface Model {
  id: string
  name: string
  provider: string
  type: 'language' | 'embedding' | 'text_to_speech' | 'speech_to_text'
  credential?: string | null
  created: string
  updated: string
}

export interface CreateModelRequest {
  name: string
  provider: string
  type: 'language' | 'embedding' | 'text_to_speech' | 'speech_to_text'
  credential?: string
}

export interface ModelDefaults {
  default_chat_model?: string | null
  default_transformation_model?: string | null
  large_context_model?: string | null
  default_text_to_speech_model?: string | null
  default_speech_to_text_model?: string | null
  default_embedding_model?: string | null
  default_tools_model?: string | null

  // Ordered fallback chains (automatic failover) - one per task type. The
  // primary field above stays the first entry/highest priority; these are
  // additional models tried in order if the primary fails (e.g. a free-tier
  // rate limit). See open_notebook/ai/provision.py::provision_langchain_model().
  chat_fallback_models?: string[]
  transformation_fallback_models?: string[]
  large_context_fallback_models?: string[]
  tools_fallback_models?: string[]
  embedding_fallback_models?: string[]
  text_to_speech_fallback_models?: string[]
  speech_to_text_fallback_models?: string[]
}

/** Maps a ModelDefaults primary-model key to its fallback-chain key. */
export const FALLBACK_KEY_MAP: Record<string, keyof ModelDefaults> = {
  default_chat_model: 'chat_fallback_models',
  default_transformation_model: 'transformation_fallback_models',
  large_context_model: 'large_context_fallback_models',
  default_tools_model: 'tools_fallback_models',
  default_embedding_model: 'embedding_fallback_models',
  default_text_to_speech_model: 'text_to_speech_fallback_models',
  default_speech_to_text_model: 'speech_to_text_fallback_models',
}

export interface ProviderAvailability {
  available: string[]
  unavailable: string[]
  supported_types: Record<string, string[]>
}

// Model Discovery Types
export interface DiscoveredModel {
  name: string
  provider: string
  model_type: 'language' | 'embedding' | 'text_to_speech' | 'speech_to_text'
  description?: string
}

export interface ProviderSyncResult {
  provider: string
  discovered: number
  new: number
  existing: number
}

export interface AllProvidersSyncResult {
  results: Record<string, ProviderSyncResult>
  total_discovered: number
  total_new: number
}

export interface ProviderModelCount {
  provider: string
  counts: Record<string, number>
  total: number
}

export interface AutoAssignResult {
  assigned: Record<string, string>  // slot_name -> model_id
  skipped: string[]  // slots already assigned
  missing: string[]  // slots with no available models
}

export interface ModelTestResult {
  success: boolean
  message: string
  details?: string
}