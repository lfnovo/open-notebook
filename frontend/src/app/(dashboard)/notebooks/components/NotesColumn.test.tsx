import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { NoteResponse } from '@/lib/types/api'
import { NotesColumn } from './NotesColumn'

interface MockNoteEditorDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  notebookId: string
  note?: NoteResponse
}

vi.mock('./NoteEditorDialog', () => ({
  NoteEditorDialog: ({
    open,
    onOpenChange,
    notebookId,
    note,
  }: MockNoteEditorDialogProps) => (
    <div
      data-testid="note-editor-dialog"
      data-open={String(open)}
      data-notebook-id={notebookId}
      data-note-id={note?.id ?? ''}
    >
      <button onClick={() => onOpenChange(false)}>close editor</button>
    </div>
  ),
}))

const uploadAsync = vi.fn()
vi.mock('@/lib/hooks/use-notes', () => ({
  useDeleteNote: () => ({ isPending: false, mutateAsync: vi.fn() }),
  useUploadNoteFile: () => ({ isPending: false, mutateAsync: uploadAsync }),
}))

const toast = vi.fn()
vi.mock('@/lib/hooks/use-toast', () => ({
  useToast: () => ({ toast }),
}))

vi.mock('./NoteFileViewer', () => ({
  NoteFileViewer: ({ note, open }: { note: NoteResponse | null; open: boolean }) => (
    <div data-testid="file-viewer" data-open={String(open)} data-note-id={note?.id ?? ''} />
  ),
}))

vi.mock('@/lib/stores/notebook-columns-store', () => ({
  useNotebookColumnsStore: () => ({
    notesCollapsed: false,
    toggleNotes: vi.fn(),
  }),
}))

vi.mock('./NotebookPodcasts', () => ({
  NotebookPodcasts: () => <div data-testid="notebook-podcasts" />,
}))

const notebookId = 'notebook:123'
const existingNote: NoteResponse = {
  id: 'note:456',
  title: 'Existing note',
  content: 'Existing note content',
  note_type: 'human',
  created: '2026-01-01T00:00:00Z',
  updated: '2026-01-01T00:00:00Z',
}

function renderNotes(notes: NoteResponse[]) {
  render(
    <NotesColumn
      notes={notes}
      isLoading={false}
      notebookId={notebookId}
    />
  )
  return screen.getByTestId('note-editor-dialog')
}

describe('NotesColumn', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('opens, closes, and reopens the editor in create mode with loaded notes', () => {
    const editor = renderNotes([existingNote])

    fireEvent.click(screen.getByText('common.writeNote'))

    expect(editor).toHaveAttribute('data-open', 'true')
    expect(editor).toHaveAttribute('data-notebook-id', notebookId)
    expect(editor).toHaveAttribute('data-note-id', '')

    fireEvent.click(screen.getByText('close editor'))
    expect(editor).toHaveAttribute('data-open', 'false')

    fireEvent.click(screen.getByText('common.writeNote'))
    expect(editor).toHaveAttribute('data-open', 'true')
    expect(editor).toHaveAttribute('data-note-id', '')
  })

  it('opens the editor in create mode when the notes list is empty', () => {
    const editor = renderNotes([])

    fireEvent.click(screen.getByText('common.writeNote'))

    expect(editor).toHaveAttribute('data-open', 'true')
    expect(editor).toHaveAttribute('data-notebook-id', notebookId)
    expect(editor).toHaveAttribute('data-note-id', '')
  })

  it('clears the selected note before opening the editor in create mode', () => {
    const editor = renderNotes([existingNote])

    fireEvent.click(screen.getByText(existingNote.title!))
    expect(editor).toHaveAttribute('data-open', 'true')
    expect(editor).toHaveAttribute('data-note-id', existingNote.id)

    fireEvent.click(screen.getByText('close editor'))
    fireEvent.click(screen.getByText('common.writeNote'))

    expect(editor).toHaveAttribute('data-open', 'true')
    expect(editor).toHaveAttribute('data-note-id', '')
  })

  describe('files', () => {
    const fileNote: NoteResponse = {
      id: 'note:file',
      title: 'report.pdf',
      content: 'extracted text',
      note_type: 'human',
      created: '2026-01-01T00:00:00Z',
      updated: '2026-01-01T00:00:00Z',
      attachment: { name: 'report.pdf', type: 'application/pdf', size: 2048 },
    }
    const file = (name: string) => new File(['x'], name)
    const drop = (card: Element, files: File[], types = ['Files']) =>
      fireEvent.drop(card, { dataTransfer: { types, files } })
    const card = () => screen.getByText('common.notes').closest('[class*="flex-col"]') as Element

    beforeEach(() => uploadAsync.mockResolvedValue({}))

    it('uploads dropped supported files into this notebook, one by one', async () => {
      renderNotes([])
      drop(card(), [file('a.pdf'), file('b.docx')])

      await waitFor(() => expect(uploadAsync).toHaveBeenCalledTimes(2))
      expect(uploadAsync).toHaveBeenNthCalledWith(1, { notebookId, file: expect.objectContaining({ name: 'a.pdf' }) })
      expect(uploadAsync).toHaveBeenNthCalledWith(2, { notebookId, file: expect.objectContaining({ name: 'b.docx' }) })
    })

    it('rejects unsupported files with a message and uploads only the rest', async () => {
      renderNotes([])
      drop(card(), [file('malware.exe'), file('ok.md')])

      await waitFor(() => expect(uploadAsync).toHaveBeenCalledTimes(1))
      expect(uploadAsync).toHaveBeenCalledWith({ notebookId, file: expect.objectContaining({ name: 'ok.md' }) })
      expect(toast).toHaveBeenCalledWith(expect.objectContaining({ title: 'noteFiles.unsupportedTitle' }))
    })

    it('ignores drags that are not files', () => {
      renderNotes([])
      drop(card(), [], ['text/plain'])
      expect(uploadAsync).not.toHaveBeenCalled()
    })

    it('shows a drop overlay while files are dragged over and hides it on drop', () => {
      renderNotes([])
      fireEvent.dragOver(card(), { dataTransfer: { types: ['Files'] } })
      expect(screen.getByTestId('notes-drop-overlay')).toBeInTheDocument()

      drop(card(), [])
      expect(screen.queryByTestId('notes-drop-overlay')).toBeNull()
    })

    it('uploads files chosen with the Add file button', async () => {
      renderNotes([])
      fireEvent.change(screen.getByTestId('notes-file-input'), { target: { files: [file('c.html')] } })
      await waitFor(() => expect(uploadAsync).toHaveBeenCalledTimes(1))
    })

    it('opens the viewer, not the editor, when a file card is clicked', () => {
      const editor = renderNotes([fileNote])
      fireEvent.click(screen.getByText('report.pdf'))

      expect(screen.getByTestId('file-viewer')).toHaveAttribute('data-open', 'true')
      expect(screen.getByTestId('file-viewer')).toHaveAttribute('data-note-id', 'note:file')
      expect(editor).toHaveAttribute('data-open', 'false')
    })

    it('still opens the editor for ordinary notes', () => {
      const editor = renderNotes([existingNote])
      fireEvent.click(screen.getByText('Existing note'))

      expect(editor).toHaveAttribute('data-open', 'true')
      expect(screen.getByTestId('file-viewer')).toHaveAttribute('data-open', 'false')
    })
  })
})
