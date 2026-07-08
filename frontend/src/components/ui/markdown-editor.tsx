'use client'

import dynamic from 'next/dynamic'
import { forwardRef } from 'react'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import rehypeSanitize from 'rehype-sanitize'

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
export const PREVIEW_OPTIONS = {
  remarkPlugins: [remarkMath],
  rehypePlugins: [rehypeSanitize, rehypeKatex],
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