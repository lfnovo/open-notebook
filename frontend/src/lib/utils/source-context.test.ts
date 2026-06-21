import { describe, it, expect } from 'vitest'
import {
  applyBulkNoteContext,
  applyBulkSourceContext,
  bulkModeForSource,
  computeNoteSelections,
  computeSourceSelections,
  includedMode,
} from './source-context'

const src = (id: string, insights_count = 0) => ({ id, insights_count })
const note = (id: string) => ({ id })

describe('includedMode', () => {
  it('prefers insights when available, else full', () => {
    expect(includedMode(0)).toBe('full')
    expect(includedMode(3)).toBe('insights')
  })
})

describe('bulkModeForSource', () => {
  it('insights-only leaves sources without insights excluded', () => {
    expect(bulkModeForSource('insights', 0)).toBe('off')
    expect(bulkModeForSource('insights', 2)).toBe('insights')
  })

  it('full forces full content regardless of insights', () => {
    expect(bulkModeForSource('full', 0)).toBe('full')
    expect(bulkModeForSource('full', 5)).toBe('full')
  })

  it('exclude turns everything off', () => {
    expect(bulkModeForSource('exclude', 5)).toBe('off')
  })
})

describe('computeSourceSelections', () => {
  it('defaults new sources to included (insights/full)', () => {
    const result = computeSourceSelections({}, [src('s:1', 2), src('s:2', 0)], 'include')
    expect(result).toEqual({ 's:1': 'insights', 's:2': 'full' })
  })

  it('defaults new sources to off when the default mode is exclude', () => {
    const result = computeSourceSelections({}, [src('s:1', 2), src('s:2', 0)], 'exclude')
    expect(result).toEqual({ 's:1': 'off', 's:2': 'off' })
  })

  it('applies an insights-only default to later-loaded sources', () => {
    const result = computeSourceSelections({}, [src('s:1', 2), src('s:2', 0)], 'insights')
    expect(result).toEqual({ 's:1': 'insights', 's:2': 'off' })
  })

  it('applies a full default to later-loaded sources', () => {
    const result = computeSourceSelections({}, [src('s:1', 2), src('s:2', 0)], 'full')
    expect(result).toEqual({ 's:1': 'full', 's:2': 'full' })
  })

  it('preserves existing explicit selections', () => {
    const existing = { 's:1': 'off' as const }
    const result = computeSourceSelections(existing, [src('s:1', 2), src('s:2', 0)], 'include')
    expect(result['s:1']).toBe('off') // untouched
    expect(result['s:2']).toBe('full')
  })

  it('upgrades a full source to insights once it has insights (implicit default only)', () => {
    expect(computeSourceSelections({ 's:1': 'full' }, [src('s:1', 5)], 'include')['s:1']).toBe('insights')
  })

  it('does not auto-upgrade an explicit full bulk choice', () => {
    expect(computeSourceSelections({ 's:1': 'full' }, [src('s:1', 5)], 'full')['s:1']).toBe('full')
  })

  it('keeps later-loaded sources excluded after an exclude-all (regression for #915)', () => {
    let selections = applyBulkSourceContext({}, [src('s:1', 0), src('s:2', 1)], 'exclude')
    expect(selections).toEqual({ 's:1': 'off', 's:2': 'off' })

    selections = computeSourceSelections(
      selections,
      [src('s:1', 0), src('s:2', 1), src('s:3', 4), src('s:4', 0)],
      'exclude',
    )
    expect(selections).toEqual({ 's:1': 'off', 's:2': 'off', 's:3': 'off', 's:4': 'off' })
  })
})

describe('applyBulkSourceContext', () => {
  it('excludes all sources', () => {
    const result = applyBulkSourceContext(
      { 's:1': 'full', 's:2': 'insights' },
      [src('s:1', 0), src('s:2', 3)],
      'exclude',
    )
    expect(result).toEqual({ 's:1': 'off', 's:2': 'off' })
  })

  it('includes all sources using their sensible mode', () => {
    const result = applyBulkSourceContext(
      { 's:1': 'off', 's:2': 'off' },
      [src('s:1', 0), src('s:2', 3)],
      'include',
    )
    expect(result).toEqual({ 's:1': 'full', 's:2': 'insights' })
  })

  it('insights-only includes sources with insights and excludes the rest', () => {
    const result = applyBulkSourceContext(
      { 's:1': 'full', 's:2': 'off' },
      [src('s:1', 0), src('s:2', 3)],
      'insights',
    )
    expect(result).toEqual({ 's:1': 'off', 's:2': 'insights' })
  })

  it('full forces full content on every source', () => {
    const result = applyBulkSourceContext(
      { 's:1': 'off', 's:2': 'insights' },
      [src('s:1', 0), src('s:2', 3)],
      'full',
    )
    expect(result).toEqual({ 's:1': 'full', 's:2': 'full' })
  })
})

describe('note context', () => {
  it('defaults new notes to full (included)', () => {
    expect(computeNoteSelections({}, [note('n:1'), note('n:2')], 'include')).toEqual({
      'n:1': 'full',
      'n:2': 'full',
    })
  })

  it('defaults new notes to off when excluded', () => {
    expect(computeNoteSelections({}, [note('n:1')], 'exclude')).toEqual({ 'n:1': 'off' })
  })

  it('preserves existing note selections', () => {
    expect(computeNoteSelections({ 'n:1': 'off' }, [note('n:1'), note('n:2')], 'include')).toEqual({
      'n:1': 'off',
      'n:2': 'full',
    })
  })

  it('bulk includes/excludes all notes', () => {
    expect(applyBulkNoteContext({ 'n:1': 'off' }, [note('n:1'), note('n:2')], 'include')).toEqual({
      'n:1': 'full',
      'n:2': 'full',
    })
    expect(applyBulkNoteContext({ 'n:1': 'full' }, [note('n:1')], 'exclude')).toEqual({
      'n:1': 'off',
    })
  })
})
