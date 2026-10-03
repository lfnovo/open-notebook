import fs from 'fs'
import path from 'path'
import { describe, expect, it } from 'vitest'

// The RTL layout ADR (docs/7-DEVELOPMENT/decisions/ADR-0YY-rtl-layout-mirroring.md)
// mandates logical (start/end) Tailwind utilities so layouts mirror in RTL. A
// previous physical→logical sweep mangled border utilities into non-existent
// classes (`bs`, `be`), silently deleting borders. These scans keep both
// failure modes from coming back.

// Physical utilities that must not be reintroduced (v4 supports the logical
// equivalents ms/me/ps/pe, border-s/border-e, text-start/text-end).
const BANNED_TOKENS = [
  /^-?m[lr]-(\d|\[)/,      // ml-*, mr-*, -ml-* (numeric/arbitrary spacing)
  /^-?p[lr]-(\d|\[)/,      // pl-*, pr-*
  /^p[lr]-px$/,            // pl-px, pr-px
  /^m[lr]-auto$/,          // ml-auto, mr-auto
  /^border-[lr](-|$)/,     // border-l, border-r, border-l-2, border-l-fern
  /^text-(left|right)$/,   // text-left, text-right
  /^space-x-\d/,           // standardized on gap-* instead
  /^rounded-[lr]-/,        // rounded-l-*, rounded-r-*
]

// Artifacts of the buggy sweep: `border-l` → `bs`, `border-r` → `be`.
const INVALID_TOKENS = /^(be|bs)(-\d+)?$/

function sourceClassStrings(): { file: string; line: number; text: string }[] {
  const srcDir = path.resolve(__dirname, '..')
  const localesDir = path.resolve(__dirname, 'locales')

  const files = fs.readdirSync(srcDir, { recursive: true }) as string[]
  const sourceFiles = files.filter(f => {
    const full = path.join(srcDir, f)
    if (full.startsWith(localesDir)) return false // prose strings, not classes
    if (f.endsWith('.test.ts') || f.endsWith('.test.tsx')) return false
    return f.endsWith('.ts') || f.endsWith('.tsx')
  })

  const out: { file: string; line: number; text: string }[] = []
  for (const f of sourceFiles) {
    const content = fs.readFileSync(path.join(srcDir, f), 'utf-8')
    content.split('\n').forEach((text, i) => {
      if (/className|cn\(/.test(text)) out.push({ file: f, line: i + 1, text })
    })
  }
  return out
}

function quotedTokens(line: string): string[] {
  const tokens: string[] = []
  for (const match of line.matchAll(/["'`]([^"'`]*)["'`]/g)) {
    tokens.push(...match[1].split(/\s+/).filter(Boolean))
  }
  return tokens
}

describe('logical Tailwind classes (RTL layout ADR)', () => {
  it('no physical directional utility classes', () => {
    const violations: string[] = []
    for (const entry of sourceClassStrings()) {
      for (const token of quotedTokens(entry.text)) {
        if (BANNED_TOKENS.some(re => re.test(token))) {
          violations.push(`${entry.file}:${entry.line} — ${token}`)
        }
      }
    }
    expect(violations).toEqual([])
  })

  it('no invalid bs/be border tokens', () => {
    const violations: string[] = []
    for (const entry of sourceClassStrings()) {
      for (const token of quotedTokens(entry.text)) {
        if (INVALID_TOKENS.test(token)) {
          violations.push(`${entry.file}:${entry.line} — ${token}`)
        }
      }
    }
    expect(violations).toEqual([])
  })
})
