import { describe, expect, it } from 'vitest'
import { convertReferencesToMarkdownLinks, parseSourceReferences } from './source-references'

describe('parseSourceReferences', () => {
  it('reads plain and bracketed references', () => {
    const refs = parseSourceReferences('See [source:abc] and note:xyz.')
    expect(refs.map((r) => `${r.type}:${r.id}`)).toEqual(['source:abc', 'note:xyz'])
  })

  it('skips a repeated prefix', () => {
    const refs = parseSourceReferences('As shown in [source:source:abc] and [note:note:note:xyz]')
    expect(refs.map((r) => `${r.type}:${r.id}`)).toEqual(['source:abc', 'note:xyz'])
  })

  it('keeps the insight alias', () => {
    expect(parseSourceReferences('[insight:insight:q1]')[0]).toMatchObject({ type: 'source_insight', id: 'q1' })
  })
})

describe('convertReferencesToMarkdownLinks', () => {
  it('links a repeated prefix to the real id', () => {
    const out = convertReferencesToMarkdownLinks('As shown in [source:source:abc].')
    expect(out).toContain('#ref-source-abc')
    expect(out).not.toContain('source:source')
  })
})
