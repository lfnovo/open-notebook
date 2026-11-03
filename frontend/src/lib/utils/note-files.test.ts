import { describe, expect, it } from 'vitest'
import {
  formatFileSize,
  isDraggingFiles,
  isSupportedNoteFile,
  noteFileKind,
} from './note-files'

describe('isSupportedNoteFile', () => {
  it.each(['a.pdf', 'A.PDF', 'page.html', 'page.htm', 'doc.docx', 'n.txt', 'n.md', 'n.markdown'])(
    'accepts %s',
    (name) => expect(isSupportedNoteFile({ name })).toBe(true)
  )

  it.each(['a.exe', 'a.doc', 'a.pdf.exe', 'pdf', 'a.png', 'a.xlsx'])('rejects %s', (name) =>
    expect(isSupportedNoteFile({ name })).toBe(false)
  )
})

describe('noteFileKind', () => {
  it('shows PDF and HTML as the original and everything else as text', () => {
    expect(noteFileKind('application/pdf')).toBe('pdf')
    expect(noteFileKind('text/html')).toBe('html')
    expect(
      noteFileKind('application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    ).toBe('text')
    expect(noteFileKind('text/markdown')).toBe('text')
    expect(noteFileKind('text/plain')).toBe('text')
  })
})

describe('formatFileSize', () => {
  it('formats bytes, KB and MB', () => {
    expect(formatFileSize(512)).toBe('512 B')
    expect(formatFileSize(2048)).toBe('2.0 KB')
    expect(formatFileSize(20 * 1024)).toBe('20 KB')
    expect(formatFileSize(3 * 1024 * 1024)).toBe('3.0 MB')
  })
})

describe('isDraggingFiles', () => {
  it('is true only for file drags', () => {
    expect(isDraggingFiles({ dataTransfer: { types: ['Files'] } as unknown as DataTransfer })).toBe(true)
    expect(isDraggingFiles({ dataTransfer: { types: ['text/plain'] } as unknown as DataTransfer })).toBe(false)
    expect(isDraggingFiles({ dataTransfer: null })).toBe(false)
  })
})
