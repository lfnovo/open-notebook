import { describe, it, expect } from 'vitest'
import fs from 'fs'
import path from 'path'
import { resources } from './index'
import { enUS } from './en-US'

const getKeys = (obj: Record<string, unknown>, prefix = ''): string[] => {
  return Object.keys(obj).reduce((res: string[], el) => {
    const val = obj[el]
    if (typeof val === 'object' && val !== null && !Array.isArray(val)) {
      return [...res, ...getKeys(val as Record<string, unknown>, prefix + el + '.')]
    }
    return [...res, prefix + el]
  }, [])
}

// Flatten to a map of dotted-key -> string leaf value (skips non-string leaves).
const getLeafStrings = (
  obj: Record<string, unknown>,
  prefix = '',
  acc: Record<string, string> = {},
): Record<string, string> => {
  for (const el of Object.keys(obj)) {
    const val = obj[el]
    if (typeof val === 'object' && val !== null && !Array.isArray(val)) {
      getLeafStrings(val as Record<string, unknown>, prefix + el + '.', acc)
    } else if (typeof val === 'string') {
      acc[prefix + el] = val
    }
  }
  return acc
}

// Collect the set of i18next `{{name}}` placeholder names in a string.
const doubleBracePlaceholders = (value: string): Set<string> => {
  const set = new Set<string>()
  for (const m of value.matchAll(/\{\{\s*(\w+)\s*\}\}/g)) {
    set.add(m[1])
  }
  return set
}

// Find stray single-brace `{name}` tokens (the exact #998 drift). We strip the
// valid `{{...}}` pairs first, so only lone single-brace tokens remain.
const straySingleBraceTokens = (value: string): string[] => {
  const withoutDouble = value.replace(/\{\{\s*\w+\s*\}\}/g, '')
  return [...withoutDouble.matchAll(/\{\s*\w+\s*\}/g)].map(m => m[0])
}

describe('Locale Parity', () => {
  const enKeys = getKeys(enUS)

  const locales = Object.entries(resources).filter(([code]) => code !== 'en-US')

  it.each(locales.map(([code, resource]) => [code, resource] as const))(
    '%s should have the same keys as en-US',
    (code, resource) => {
      const localeKeys = getKeys(resource.translation as Record<string, unknown>)

      const missing = enKeys.filter(key => !localeKeys.includes(key))
      const extra = localeKeys.filter(key => !enKeys.includes(key))

      expect(missing, `Missing keys in ${code}: ${missing.join(', ')}`).toEqual([])
      expect(extra, `Extra keys in ${code}: ${extra.join(', ')}`).toEqual([])
    },
  )
})

describe('Placeholder Parity', () => {
  const enLeaves = getLeafStrings(enUS)

  const locales = Object.entries(resources).filter(([code]) => code !== 'en-US')

  it.each(locales.map(([code, resource]) => [code, resource] as const))(
    '%s interpolation placeholders should match en-US',
    (code, resource) => {
      const localeLeaves = getLeafStrings(
        resource.translation as Record<string, unknown>,
      )

      const mismatches: string[] = []
      const strays: string[] = []

      for (const [key, enValue] of Object.entries(enLeaves)) {
        const localeValue = localeLeaves[key]
        // Missing keys are covered by the parity test; skip here.
        if (localeValue === undefined) continue

        const enSet = doubleBracePlaceholders(enValue)
        const localeSet = doubleBracePlaceholders(localeValue)

        const missing = [...enSet].filter(p => !localeSet.has(p))
        const extra = [...localeSet].filter(p => !enSet.has(p))
        if (missing.length || extra.length) {
          mismatches.push(
            `${key}: missing [${missing.join(', ')}] extra [${extra.join(', ')}]`,
          )
        }

        // A stray single-brace token is only drift if en-US expects a
        // placeholder there (i.e. the token name is a real placeholder).
        const stray = straySingleBraceTokens(localeValue).filter(tok => {
          const name = tok.replace(/[{}\s]/g, '')
          return enSet.has(name)
        })
        if (stray.length) {
          strays.push(`${key}: ${stray.join(', ')}`)
        }
      }

      expect(
        mismatches,
        `Placeholder mismatches in ${code}:\n${mismatches.join('\n')}`,
      ).toEqual([])
      expect(
        strays,
        `Single-brace placeholder(s) in ${code} that should be {{...}}:\n${strays.join('\n')}`,
      ).toEqual([])
    },
  )
})

describe('Unused Key Detection', () => {
  it(
    'all en-US leaf keys should be referenced in source files',
    () => {
      const srcDir = path.resolve(__dirname, '../../..')
      const localesDir = path.resolve(__dirname)

      const files = fs.readdirSync(srcDir, { recursive: true }) as string[]
      const sourceFiles = files.filter(f => {
        const full = path.join(srcDir, f)
        if (full.startsWith(localesDir)) return false
        if (f.endsWith('.test.ts') || f.endsWith('.test.tsx')) return false
        return f.endsWith('.ts') || f.endsWith('.tsx')
      })

      // Normalize optional chaining (t?.common?.key → t.common.key)
      // so that keys like "common.errorDetails" match "common?.errorDetails"
      const corpus = sourceFiles
        .map(f => fs.readFileSync(path.join(srcDir, f), 'utf-8'))
        .join('\n')
        .replace(/\?\./g, '.')

      // Plural forms (key_one, key_other, …) are resolved by i18next from the
      // base key passed to t(), so check the base key instead.
      const pluralSuffix = /_(zero|one|two|few|many|other)$/
      const leafKeys = getKeys(enUS)
      const unused = leafKeys.filter(
        key => !corpus.includes(key.replace(pluralSuffix, '')),
      )

      expect(
        unused,
        `Found ${unused.length} unused i18n key(s):\n${unused.join('\n')}`,
      ).toEqual([])
    },
    30_000,
  )
})
