'use client'

import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'

import { useThemeStore } from '@/lib/stores/theme-store'
import { oneDark as darkTheme } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { oneLight as lightTheme } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'

import type {ExtraProps} from 'react-markdown'
import type {ComponentProps, ElementType} from 'react'

type Components = {
  [Key in Extract<ElementType, string>]?: ElementType<ComponentProps<Key> & ExtraProps>
}

export function MarkdownRenderer({ children, components = {}}: { children: React.ReactNode , components?: Components }) {

  const { getEffectiveTheme } = useThemeStore()
  const isDark = getEffectiveTheme() === 'dark'

  return (
    <div className="prose prose-sm prose-neutral dark:prose-invert max-w-none break-words prose-headings:font-semibold prose-a:text-blue-600 prose-a:break-all prose-code:before:content-none prose-code:after:content-none prose-pre:p-0 prose-pre:bg-transparent prose-p:mb-4 prose-p:leading-7 prose-li:mb-2">
        <ReactMarkdown
          remarkPlugins={[remarkGfm, remarkMath]}
          rehypePlugins={[rehypeKatex]}
          components={{...{
            p: ({ children }) => <p className="mb-4">{children}</p>,
            h1: ({ children }) => <h1 className="mb-4 mt-6">{children}</h1>,
            h2: ({ children }) => <h2 className="mb-3 mt-5">{children}</h2>,
            h3: ({ children }) => <h3 className="mb-3 mt-4">{children}</h3>,
            h4: ({ children }) => <h4 className="mb-2 mt-4">{children}</h4>,
            h5: ({ children }) => <h5 className="mb-2 mt-3">{children}</h5>,
            h6: ({ children }) => <h6 className="mb-2 mt-3">{children}</h6>,
            li: ({ children }) => <li className="mb-1">{children}</li>,
            ul: ({ children }) => <ul className="mb-4 space-y-1">{children}</ul>,
            ol: ({ children }) => <ol className="mb-4 space-y-1">{children}</ol>,
            table: ({ children }) => (
              <div className="my-4 overflow-x-auto">
                <table className="min-w-full border-collapse border border-border">{children}</table>
              </div>
            ),
            thead: ({ children }) => <thead className="bg-muted">{children}</thead>,
            tbody: ({ children }) => <tbody>{children}</tbody>,
            tr: ({ children }) => <tr className="border-b border-border">{children}</tr>,
            th: ({ children }) => <th className="border border-border px-3 py-2 text-left font-semibold">{children}</th>,
            td: ({ children }) => <td className="border border-border px-3 py-2">{children}</td>,
            code: ({ children, className }) => {
              const match = /language-(\w+)/.exec(className || '')
              const isBlock = match || String(children).includes('\n')
              return isBlock ? (
                <SyntaxHighlighter
                  language={match ? match[1] : 'text'}
                  style={isDark ? darkTheme : lightTheme}
                  PreTag="div"
                  className="text-sm border border-border"
                >
                  {String(children)}
                </SyntaxHighlighter>
              ) : (
                <code className="bg-border rounded px-1 py-0.5">{children}</code>
              )
            },
          }, ...components}}
        >
          {String(children)}
        </ReactMarkdown>
      </div>
  )
}
