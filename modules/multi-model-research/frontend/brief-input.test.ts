import { describe, expect, it } from 'vitest'
import { briefLength, packBrief, readBriefFile, validateBrief } from './brief-input'

describe('Research brief admission', () => {
  it('preserves a 39,982-character document across existing API fields', () => {
    const text = '# GenUI\n\n' + 'ş'.repeat(39_972) + '\n'
    expect(briefLength(text)).toBe(39_982)
    const body = packBrief(text, '')
    expect(body.question.length).toBeLessThanOrEqual(12_000)
    expect(body.scope.length).toBeLessThanOrEqual(30_000)
    expect(body.question + body.scope).toBe(text)
  })
  it('keeps ordinary question and scope fields unchanged', () => {
    expect(packBrief('A question?', '  Scope\n')).toEqual({ question: 'A question?', scope: '  Scope\n' })
  })
  it('retains additional criteria after the complete long document', () => {
    const text = '# Brief\n\n' + 'x'.repeat(35_000)
    const scope = 'Compare sources. Keep uncertainty.'
    const body = packBrief(text, scope)
    expect(body.question + body.scope).toBe(text + '\n\n' + scope)
  })
  it('preserves Unicode code points and exact boundary content', () => {
    const text = '🧭'.repeat(42_000)
    const body = packBrief(text, '')
    expect(briefLength(body.question)).toBe(12_000)
    expect(briefLength(body.scope)).toBe(30_000)
    expect(body.question + body.scope).toBe(text)
  })
  it('rejects overflow without clipping and accounts for the criteria separator', () => {
    expect(validateBrief('x'.repeat(42_001), '')).toBe('briefTooLong')
    expect(validateBrief('x'.repeat(42_000), 'y')).toBe('briefTooLong')
    expect(() => packBrief('x'.repeat(42_001), '')).toThrow('briefTooLong')
    expect(validateBrief('Question', 'x'.repeat(30_001))).toBe('briefScopeTooLong')
    expect(validateBrief('     ', '')).toBe('briefTooShort')
  })
  it('prefers a paragraph boundary when it fits the remaining scope capacity', () => {
    const text = 'a'.repeat(10_500) + '\n\n' + 'b'.repeat(28_000)
    const body = packBrief(text, '')
    expect(body.question).toBe('a'.repeat(10_500))
    expect(body.question + body.scope).toBe(text)
  })
  it('reads UTF-8 Markdown without trimming, normalizing line endings or dropping the BOM', async () => {
    const text = '\ufeff# Başlık\r\n\r\nSon satır.\r\n'
    const bytes = new TextEncoder().encode(text)
    expect(await readBriefFile({name: 'brief.MD', size: bytes.length, arrayBuffer: async () => bytes.buffer as ArrayBuffer})).toBe(text)
  })
  it('rejects unsupported, oversized, binary, empty and invalid UTF-8 files', async () => {
    const file = (name: string, bytes: Uint8Array) => ({name, size: bytes.length, arrayBuffer: async () => bytes.buffer as ArrayBuffer})
    await expect(readBriefFile(file('brief.pdf', new Uint8Array([65])))).rejects.toThrow('briefFileType')
    await expect(readBriefFile({...file('brief.md', new Uint8Array()),size:168_001})).rejects.toThrow('briefFileTooLarge')
    await expect(readBriefFile(file('brief.md', new Uint8Array([0])))).rejects.toThrow('briefFileEncoding')
    await expect(readBriefFile(file('brief.md', new Uint8Array([0xff])))).rejects.toThrow('briefFileEncoding')
    await expect(readBriefFile(file('brief.txt', new Uint8Array([32,10])))).rejects.toThrow('briefFileEmpty')
  })
})
