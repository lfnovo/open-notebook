'use client'

import dynamic from 'next/dynamic'
import { forwardRef } from 'react'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'

const MDEditor = dynamic(
  () => import('@uiw/react-md-editor').then((mod) => mod.default),
  { ssr: false }
)

// Render `$...$` / `$$...$$` math in the live preview. @uiw/react-md-editor
// concatenates these with its defaults (gfm, prism, raw), so syntax
// highlighting and GFM are preserved. KaTeX CSS is loaded globally in
// app/layout.tsx.
const PREVIEW_OPTIONS = {
  remarkPlugins: [remarkMath],
  rehypePlugins: [rehypeKatex],
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