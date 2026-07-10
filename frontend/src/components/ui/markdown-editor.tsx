'use client'

import dynamic from 'next/dynamic'
import { forwardRef } from 'react'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import rehypeSanitize, { defaultSchema } from 'rehype-sanitize'
import type { PluggableList } from 'unified'

const MDEditor = dynamic(
  () => import('@uiw/react-md-editor').then((mod) => mod.default),
  { ssr: false }
)

// Render `$...$` / `$$...$$` math in the live preview. @uiw/react-md-editor
// concatenates these with its defaults (gfm, prism, raw), so syntax
// highlighting and GFM are preserved. KaTeX CSS is loaded globally in
// app/layout.tsx.
//
// The library's own `raw` default lets literal HTML in the markdown source
// (e.g. pasted content, or an AI-generated note echoing an indirect prompt
// injection) render as live elements - notably a real <iframe>, not just
// inert text. rehypeSanitize (default schema) strips that down to safe
// HTML. It must run *before* rehypeKatex: katex's own generated markup
// (katex-html spans, MathML) isn't in the default sanitize schema and gets
// stripped if sanitize runs after it - order here is load-bearing, verified
// against the actual rendered output for math/code/GFM before changing it.
// The library's rehypeRewrite injects a copy button into code blocks
// (div.copied[data-code] + two octicon SVGs) *before* user plugins run, so
// the default schema strips it. Allow exactly that markup back in. The div
// keys must be the literal lowercase 'class'/'data-code' the library sets
// (hast-util-sanitize matches raw property keys); the SVGs are authored in
// camelCase, so camelCase is correct there. Worst case this permits from
// user-authored raw HTML: a decoy div that copies attacker-chosen text on
// click, plus inert static SVGs.
const SANITIZE_SCHEMA = {
  ...defaultSchema,
  tagNames: [...(defaultSchema.tagNames ?? []), 'svg', 'path'],
  attributes: {
    ...defaultSchema.attributes,
    div: [...(defaultSchema.attributes?.div ?? []), ['class', 'copied'], 'data-code'],
    svg: [['className', 'octicon-copy', 'octicon-check'], 'ariaHidden', 'viewBox', 'fill', 'height', 'width'],
    path: ['fillRule', 'd'],
  },
}

export const PREVIEW_OPTIONS = {
  remarkPlugins: [remarkMath] as PluggableList,
  rehypePlugins: [[rehypeSanitize, SANITIZE_SCHEMA], rehypeKatex] as PluggableList,
}

export interface MarkdownEditorProps {
  value?: string
  onChange?: (value?: string) => void
  placeholder?: string
  height?: number
  preview?: 'live' | 'edit' | 'preview'
  hideToolbar?: boolean
  textareaId?: string
  name?: string
  className?: string
}

export const MarkdownEditor = forwardRef<HTMLDivElement, MarkdownEditorProps>(
  ({ value = '', onChange, placeholder, height = 300, preview = 'live', hideToolbar = false, className, textareaId, name }, ref) => {
    return (
      <div className={className} ref={ref}>
        <MDEditor
          value={value}
          onChange={onChange}
          preview={preview}
          height={height}
          hideToolbar={hideToolbar}
          textareaProps={{
            placeholder: placeholder || 'Enter markdown...',
            id: textareaId,
            name: name,
          }}
          previewOptions={PREVIEW_OPTIONS}
          data-color-mode="light"
        />
      </div>
    )
  }
)

MarkdownEditor.displayName = 'MarkdownEditor'