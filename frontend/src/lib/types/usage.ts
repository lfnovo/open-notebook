export type UsagePeriod = 'month' | 'year'

/** Matches api/models.py UsageSummaryResponse (GET /api/usage/summary). */
export interface UsageSummary {
  total_cost_usd: number
  /** Configured budget in USD (STUDY_BUDGET_USD, default 10.0) */
  budget_usd: number
  /** Estimated cost in USD grouped by task_type (chat, transformation, ...) */
  by_task_type: Record<string, number>
  input_tokens: number
  output_tokens: number
}
