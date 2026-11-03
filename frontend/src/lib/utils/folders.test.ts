import { describe, expect, it } from 'vitest'
import type { FolderResponse, NotebookResponse, SectionResponse } from '@/lib/types/api'
import {
  foldersInSection,
  groupNotebooksByFolder,
  notebooksHref,
  notebooksInFolder,
  unsectionedFolders,
  validateFolderName,
} from './folders'

const folder = (id: string, name: string): FolderResponse => ({
  id,
  name,
  created: '2026-01-01T00:00:00Z',
  updated: '2026-01-01T00:00:00Z',
  notebook_count: 0,
})

const notebook = (id: string, folder_id?: string | null): NotebookResponse => ({
  id,
  name: id,
  description: '',
  archived: false,
  created: '2026-01-01T00:00:00Z',
  updated: '2026-01-01T00:00:00Z',
  source_count: 0,
  note_count: 0,
  folder_id,
})

describe('groupNotebooksByFolder', () => {
  const folders = [folder('folder:a', 'A'), folder('folder:b', 'B'), folder('folder:c', 'C')]

  it('counts notebooks per folder and keeps folder order', () => {
    const result = groupNotebooksByFolder(folders, [
      notebook('n1', 'folder:b'),
      notebook('n2', 'folder:a'),
      notebook('n3', 'folder:b'),
    ])
    expect(result.folderCards.map((c) => [c.folder.id, c.notebookCount])).toEqual([
      ['folder:a', 1],
      ['folder:b', 2],
      ['folder:c', 0],
    ])
    expect(result.ungrouped).toEqual([])
  })

  it('puts notebooks without a folder, with null, or with an unknown folder in ungrouped', () => {
    const result = groupNotebooksByFolder(folders, [
      notebook('n1'),
      notebook('n2', null),
      notebook('n3', 'folder:gone'),
      notebook('n4', 'folder:a'),
    ])
    expect(result.ungrouped.map((n) => n.id)).toEqual(['n1', 'n2', 'n3'])
    expect(result.folderCards[0].notebookCount).toBe(1)
  })

  it('handles empty inputs', () => {
    expect(groupNotebooksByFolder([], [])).toEqual({ folderCards: [], ungrouped: [] })
    expect(groupNotebooksByFolder([], [notebook('n1', 'folder:a')]).ungrouped).toHaveLength(1)
  })
})

describe('notebooksInFolder', () => {
  it('returns only notebooks of that folder', () => {
    const list = [notebook('n1', 'folder:a'), notebook('n2'), notebook('n3', 'folder:b')]
    expect(notebooksInFolder(list, 'folder:a').map((n) => n.id)).toEqual(['n1'])
  })
})

describe('validateFolderName', () => {
  it('rejects empty and whitespace-only names', () => {
    expect(validateFolderName('')).toBe('required')
    expect(validateFolderName('   ')).toBe('required')
  })
  it('accepts 1 to 80 characters (trimmed)', () => {
    expect(validateFolderName('a')).toBeNull()
    expect(validateFolderName('a'.repeat(80))).toBeNull()
    expect(validateFolderName(`  ${'a'.repeat(80)}  `)).toBeNull()
  })
  it('rejects more than 80 characters', () => {
    expect(validateFolderName('a'.repeat(81))).toBe('tooLong')
  })
})

describe('sections', () => {
  const section = (id: string): SectionResponse => ({
    id,
    name: id,
    created: '',
    updated: '',
    folder_count: 0,
  })
  const inSection = (id: string, section_id?: string | null): FolderResponse => ({
    ...folder(id, id),
    section_id,
  })
  const folders = [
    inSection('folder:a', 'section:1'),
    inSection('folder:b'),
    inSection('folder:c', null),
    inSection('folder:d', 'section:gone'),
  ]

  it('foldersInSection returns only that section\'s folders', () => {
    expect(foldersInSection(folders, 'section:1').map((f) => f.id)).toEqual(['folder:a'])
  })

  it('unsectionedFolders keeps folders with no or a deleted section', () => {
    expect(unsectionedFolders(folders, [section('section:1')]).map((f) => f.id)).toEqual([
      'folder:b',
      'folder:c',
      'folder:d',
    ])
  })

  it('notebooksHref builds top-level, section and folder URLs', () => {
    expect(notebooksHref()).toBe('/notebooks')
    expect(notebooksHref({ sectionId: 'section:1' })).toBe('/notebooks?section=section%3A1')
    expect(notebooksHref({ sectionId: 'section:1', folderId: 'folder:a' })).toBe(
      '/notebooks?folder=folder%3Aa'
    )
    expect(notebooksHref({ folderId: null, sectionId: null })).toBe('/notebooks')
  })
})
