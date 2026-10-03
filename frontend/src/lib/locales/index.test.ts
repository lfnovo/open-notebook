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

// Only these Arabic sentences spell out zero/one/two rather than displaying a
// number. All other keys and locales retain the full placeholder contract.
const arabicWordedCounts = new Set([
  'podcasts.usedByCount_zero',
  'podcasts.usedByCount_one',
  'podcasts.usedByCount_two',
])

const placeholderProblems = (code: string, key: string, enValue: string, localeValue: string) => {
  const enSet = doubleBracePlaceholders(enValue)
  const localeSet = doubleBracePlaceholders(localeValue)
  const mayOmitCount = code === 'ar-SA' && arabicWordedCounts.has(key)

  return {
    missing: [...enSet].filter(p => !localeSet.has(p) && !(p === 'count' && mayOmitCount)),
    extra: [...localeSet].filter(p => !enSet.has(p)),
    // Check against the original English placeholders, including an optional
    // count: spelling out a number never makes a literal {count} valid.
    stray: straySingleBraceTokens(localeValue).filter(tok =>
      enSet.has(tok.replace(/[{}\s]/g, '')),
    ),
  }
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

  it.each(['fr-FR', 'ru-RU'])('rejects a dropped count in %s singular forms', code => {
    expect(placeholderProblems(code, 'podcasts.usedByCount_one', 'Used by {{count}} episode', 'Used by one episode').missing).toEqual(['count'])
  })

  const arLeaves = getLeafStrings(resources['ar-SA'].translation)

  it.each([
    ['podcasts.usedByCount_zero', 'لا تستخدمه أي حلقة'],
    ['podcasts.usedByCount_one', 'تستخدمه حلقة واحدة'],
    ['podcasts.usedByCount_two', 'تستخدمه حلقتان'],
  ])('validates the real Arabic worded count at %s', (key, expected) => {
    const enValue = enLeaves[key]
    const arValue = arLeaves[key]

    // Pin the actual worded forms, not a synthetic example of the exception.
    // Runtime plural selection is covered separately in interpolation.test.ts.
    expect(arValue).toBe(expected)
    expect(doubleBracePlaceholders(enValue)).toContain('count')
    expect(doubleBracePlaceholders(arValue)).not.toContain('count')
    expect(placeholderProblems('ar-SA', key, enValue, arValue)).toEqual({
      missing: [], extra: [], stray: [],
    })
  })

  it.each(['zero', 'one', 'two'])('still rejects an Arabic {count} typo in the %s exception', suffix => {
    expect(placeholderProblems('ar-SA', `podcasts.usedByCount_${suffix}`, 'Used by {{count}} episodes', 'تستخدمه {count} حلقة').stray).toEqual(['{count}'])
  })

  it.each(['podcasts.usedByCount_few', 'podcasts.usedByCount_many', 'podcasts.usedByCount_other', 'unrelated_one'])('requires count in Arabic %s', key => {
    expect(placeholderProblems('ar-SA', key, '{{count}} items', 'عناصر').missing).toEqual(['count'])
  })

  it('keeps other placeholders required in the Arabic exceptions', () => {
    expect(placeholderProblems('ar-SA', 'podcasts.usedByCount_one', '{{name}}: {{count}} episode', 'حلقة واحدة').missing).toEqual(['name'])
    expect(placeholderProblems('ar-SA', 'podcasts.usedByCount_one', '{{count}} episode', '{{unexpected}}').extra).toEqual(['unexpected'])
  })

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

        const { missing, extra, stray } = placeholderProblems(code, key, enValue, localeValue)
        if (missing.length || extra.length) {
          mismatches.push(
            `${key}: missing [${missing.join(', ')}] extra [${extra.join(', ')}]`,
          )
        }

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
