import { NotebookResponse } from '@/lib/types/api'

export function canManageNotebook(
  notebook: Pick<NotebookResponse, 'owner_id' | 'capabilities'> | null | undefined,
  userId: string | null | undefined
): boolean {
  if (!notebook) return false
  if (notebook.capabilities) {
    return (
      notebook.capabilities.can_manage ||
      notebook.capabilities.can_update ||
      notebook.capabilities.can_delete ||
      notebook.capabilities.can_share
    )
  }
  if (!notebook.owner_id) return true
  return notebook.owner_id === userId
}
