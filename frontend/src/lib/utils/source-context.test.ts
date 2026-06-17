import { describe, it, expect } from 'vitest'
import {
  applyBulkSourceContext,
  computeSourceSelections,
  includedMode,
} from './source-context'

const src = (id: string, insights_count = 0) => ({ id, insights_count })

describe('includedMode', () => {
  it('prefers insights when available, else full', () => {
    expect(includedMode(0)).toBe('full')
    expect(includedMode(3)).toBe('insights')
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

  it('preserves existing explicit selections', () => {
    const existing = { 's:1': 'off' as const }
    const result = computeSourceSelections(existing, [src('s:1', 2), src('s:2', 0)], 'include')
    expect(result['s:1']).toBe('off') // untouched
    expect(result['s:2']).toBe('full')
  })

  it('upgrades a full source to insights once it has insights', () => {
    const result = computeSourceSelections({ 's:1': 'full' }, [src('s:1', 5)], 'include')
    expect(result['s:1']).toBe('insights')
  })

  it('keeps later-loaded sources excluded after an exclude-all (regression for #915)', () => {
    // exclude-all over the first page
    let selections = applyBulkSourceContext({}, [src('s:1', 0), src('s:2', 1)], 'exclude')
    expect(selections).toEqual({ 's:1': 'off', 's:2': 'off' })

    // a second page loads; with the exclude default the new sources stay excluded
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
})
