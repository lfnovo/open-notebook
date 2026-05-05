import fs from 'node:fs'
import path from 'node:path'
import { describe, expect, it } from 'vitest'

const SRC_DIR = path.resolve(__dirname, '../..')
const DIALOG_CONTENT_RE = /<(?:DialogContent|AlertDialogContent)[^>]*className="([^"]*)"/g
const RAW_WIDTH_RE = /(?:^|\s)(?:sm:)?(?:w|max-w)-\[/ 
const UNSCOPED_MAX_WIDTH_RE = /(?:^|\s)max-w-(?:md|lg|2xl|3xl|4xl|5xl)(?:\s|$)/

function collectTsxFiles(dir: string): string[] {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const fullPath = path.join(dir, entry.name)
    if (entry.isDirectory()) {
      return collectTsxFiles(fullPath)
    }
    return entry.isFile() && entry.name.endsWith('.tsx') ? [fullPath] : []
  })
}

describe('dialog width classes', () => {
  it('uses standard responsive width tiers for dialog content', () => {
    const violations = collectTsxFiles(SRC_DIR).flatMap((file) => {
      const source = fs.readFileSync(file, 'utf8')
      return Array.from(source.matchAll(DIALOG_CONTENT_RE)).flatMap((match) => {
        const className = match[1]
        const hasRawWidth = RAW_WIDTH_RE.test(className)
        const hasUnscopedMaxWidth = UNSCOPED_MAX_WIDTH_RE.test(className)
        if (!hasRawWidth && !hasUnscopedMaxWidth) {
          return []
        }
        return [`${path.relative(SRC_DIR, file)}: ${className}`]
      })
    })

    expect(violations).toEqual([])
  })
})
