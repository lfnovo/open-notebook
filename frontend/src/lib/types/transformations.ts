export interface Transformation {
  id: string
  name: string
  title: string
  description: string
  prompt: string
  apply_default: boolean
  model_id: string | null
  created: string
  updated: string
}

export interface CreateTransformationRequest {
  name: string
  title: string
  description: string
  prompt: string
  apply_default?: boolean
  model_id?: string | null
}

export interface UpdateTransformationRequest {
  name?: string
  title?: string
  description?: string
  prompt?: string
  apply_default?: boolean
  model_id?: string | null
}

export interface ExecuteTransformationRequest {
  transformation_id: string
  input_text: string
  model_id?: string | null
}

export interface ExecuteTransformationResponse {
  output: string
  transformation_id: string
  model_id: string | null
}

export interface DefaultPrompt {
  transformation_instructions: string
}
