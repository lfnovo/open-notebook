import { notesApi } from '@/lib/api/notes'

/** Files that can be dropped on the notes pane (mirrors the backend allow-list). */
export const NOTE_FILE_EXTENSIONS = ['.pdf', '.html', '.htm', '.docx', '.txt', '.md', '.markdown']

export type NoteFileKind = 'pdf' | 'html' | 'text'

export function isSupportedNoteFile(file: { name: string }): boolean {
  const name = file.name.toLowerCase()
  return NOTE_FILE_EXTENSIONS.some((ext) => name.endsWith(ext))
}

/** How the viewer shows a file: PDF and HTML as the original, everything else as extracted text. */
export function noteFileKind(mime: string): NoteFileKind {
  if (mime === 'application/pdf') return 'pdf'
  if (mime === 'text/html') return 'html'
  return 'text'
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(bytes < 10 * 1024 ? 1 : 0)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

/** True while the user is dragging files (not text or an in-app item) over the page. */
export function isDraggingFiles(event: { dataTransfer: DataTransfer | null }): boolean {
  return Array.from(event.dataTransfer?.types ?? []).includes('Files')
}

/** Fetch the original file (with auth) and save it under its own name. */
export async function saveNoteFile(noteId: string, name: string, mime: string): Promise<void> {
  const data = await notesApi.fetchFile(noteId)
  const url = URL.createObjectURL(new Blob([data], { type: mime }))
  const link = document.createElement('a')
  link.href = url
  link.download = name
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}
