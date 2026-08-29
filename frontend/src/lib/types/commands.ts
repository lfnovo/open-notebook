/**
 * Types for the generic async-command layer (POST /api/commands/jobs,
 * GET /api/commands/jobs/{job_id} - api/routers/commands.py). Any
 * surreal_commands-backed command can be submitted/polled through this
 * same generic shape; command-specific result payloads are typed per call
 * site (see AskAcrossSourcesResult below).
 */
export interface CommandJobResponse {
  job_id: string
  status: string
  message: string
}

export interface CommandJobStatusResponse<TResult = Record<string, unknown>> {
  job_id: string
  status: string
  result?: TResult | null
  error_message?: string | null
  created?: string | null
  updated?: string | null
  progress?: unknown
}

/** Result payload for the "ask_across_sources" command - mirrors
 * AskAcrossSourcesOutput in commands/ask_sources_command.py. */
export interface AskAcrossSourcesResult {
  success: boolean
  note_id?: string | null
  model_used?: string | null
  estimated_cost_usd?: number | null
  error_message?: string | null
}
