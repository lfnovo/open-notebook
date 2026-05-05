import { SourceListResponse } from '@/lib/types/api'

export function canDeleteSource(
  source: SourceListResponse,
  currentUserId?: string | null
) {
  if (!currentUserId || source.owner_id !== currentUserId) return false
  if (source.visibility === 'public' && source.reference_count > 0) return false
  return true
}

export function deletableSourceIds(
  sources: SourceListResponse[],
  currentUserId?: string | null
) {
  return sources
    .filter((source) => canDeleteSource(source, currentUserId))
    .map((source) => source.id)
}
