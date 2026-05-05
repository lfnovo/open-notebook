import { NotebookResponse } from '@/lib/types/api'

export function canManageNotebook(
  notebook: Pick<NotebookResponse, 'owner_id'> | null | undefined,
  userId: string | null | undefined
): boolean {
  if (!notebook) return false
  if (!notebook.owner_id) return true
  return notebook.owner_id === userId
}
