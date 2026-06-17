import type { ContextMode } from '@/app/(dashboard)/notebooks/[id]/page'

export type SourceContextDefault = 'include' | 'exclude'

interface SourceLike {
  id: string
  insights_count: number
}

/** The "included" context mode for a source: insights when available, else full. */
export function includedMode(insightsCount: number): ContextMode {
  return insightsCount > 0 ? 'insights' : 'full'
}

/**
 * Compute chat-context selections for a batch of sources while preserving
 * existing choices.
 *
 * Newly-seen sources adopt `defaultMode`, so a prior bulk include/exclude also
 * governs sources that load later via pagination — otherwise "exclude all"
 * would silently miss sources loaded after the action (#223/#915).
 */
export function computeSourceSelections(
  existing: Record<string, ContextMode>,
  sources: SourceLike[],
  defaultMode: SourceContextDefault = 'include',
): Record<string, ContextMode> {
  const next = { ...existing }
  for (const source of sources) {
    const current = next[source.id]
    if (current === undefined) {
      next[source.id] =
        defaultMode === 'exclude' ? 'off' : includedMode(source.insights_count)
    } else if (current === 'full' && source.insights_count > 0) {
      // Source gained insights while in 'full' mode — prefer the leaner insights.
      next[source.id] = 'insights'
    }
  }
  return next
}

/** Apply a uniform bulk include/exclude to every given source. */
export function applyBulkSourceContext(
  existing: Record<string, ContextMode>,
  sources: SourceLike[],
  action: SourceContextDefault,
): Record<string, ContextMode> {
  const next = { ...existing }
  for (const source of sources) {
    next[source.id] = action === 'exclude' ? 'off' : includedMode(source.insights_count)
  }
  return next
}
