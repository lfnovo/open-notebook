import type { FolderResponse, NotebookResponse } from '@/lib/types/api'

export const FOLDER_NAME_MAX_LENGTH = 80

export type FolderNameError = 'required' | 'tooLong' | null

export function validateFolderName(name: string): FolderNameError {
  const trimmed = name.trim()
  if (trimmed.length < 1) return 'required'
  if (trimmed.length > FOLDER_NAME_MAX_LENGTH) return 'tooLong'
  return null
}

export interface FolderCardData {
  folder: FolderResponse
  notebookCount: number
}

export interface GroupedNotebooks {
  folderCards: FolderCardData[]
  ungrouped: NotebookResponse[]
}

/**
 * Groups notebooks by folder. Folder cards keep the order of `folders` and
 * carry the number of the given notebooks that live in them. Notebooks without
 * a folder (or pointing at a folder that no longer exists) are ungrouped.
 */
export function groupNotebooksByFolder(
  folders: FolderResponse[],
  notebooks: NotebookResponse[]
): GroupedNotebooks {
  const counts = new Map<string, number>()
  const ungrouped: NotebookResponse[] = []
  const known = new Set(folders.map((folder) => folder.id))

  for (const notebook of notebooks) {
    const folderId = notebook.folder_id
    if (folderId && known.has(folderId)) {
      counts.set(folderId, (counts.get(folderId) ?? 0) + 1)
    } else {
      ungrouped.push(notebook)
    }
  }

  return {
    folderCards: folders.map((folder) => ({
      folder,
      notebookCount: counts.get(folder.id) ?? 0,
    })),
    ungrouped,
  }
}

export function notebooksInFolder(
  notebooks: NotebookResponse[],
  folderId: string
): NotebookResponse[] {
  return notebooks.filter((notebook) => notebook.folder_id === folderId)
}

export const NOTEBOOK_DRAG_MIME = 'application/x-open-notebook-id'
