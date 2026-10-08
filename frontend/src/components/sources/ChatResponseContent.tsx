'use client'

import { Fragment } from 'react'
import type { ChatImage } from '@/lib/types/api'
import { ChatImages } from './ChatImages'
import { InlineChatQuiz } from './InlineChatQuiz'
import { MarkdownRenderer } from '@/components/ui/markdown-renderer'
import { useTranslation } from '@/lib/hooks/use-translation'
import { convertReferencesToCompactMarkdown, createCompactReferenceLinkComponent } from '@/lib/utils/source-references'

export function ChatResponseContent({ content, images = [], quizzes = [], onReferenceClick }: {
  content: string
  images?: ChatImage[]
  quizzes?: string[]
  onReferenceClick: (type: string, id: string) => void
}) {
  const { t } = useTranslation()
  const markdown = convertReferencesToCompactMarkdown(content, t('common.references'))
  const LinkComponent = createCompactReferenceLinkComponent(onReferenceClick)
  const pieces = markdown.split(/(\[\[(?:image:\d+|quiz:[^\]]+|quiz-unavailable)\]\])/g)
  const renderedImages = new Set<number>()
  const renderedQuizzes = new Set<string>()
  let warningShown = false
  return <div className="space-y-3">
    {pieces.map((piece, index) => {
      if (piece === '[[quiz-unavailable]]') {
        if (warningShown) return null
        warningShown = true
        return <p key={index} role="status" className="rounded-md border p-3 text-sm text-muted-foreground">{t('chat.quizPreparationFailed')}</p>
      }
      const imageMatch = piece.match(/^\[\[image:(\d+)\]\]$/)
      if (imageMatch) {
        const position = Number(imageMatch[1]) - 1
        if (!images[position] || renderedImages.has(position)) return null
        renderedImages.add(position)
        return <ChatImages key={index} images={[images[position]]} large />
      }
      const quizMatch = piece.match(/^\[\[quiz:([^\]]+)\]\]$/)
      if (quizMatch) {
        const id = quizMatch[1]
        if (!quizzes.includes(id) || renderedQuizzes.has(id)) return null
        renderedQuizzes.add(id)
        return <InlineChatQuiz key={id} id={id} />
      }
      return piece.trim() ? <MarkdownRenderer key={index} components={{ a: LinkComponent }}>{piece}</MarkdownRenderer> : null
    })}
    {/* Histories saved before positioned widgets still display their attachments. */}
    {images.map((image, index) => renderedImages.has(index) ? null : <ChatImages key={`legacy-image-${index}`} images={[image]} large />)}
    {quizzes.map(id => renderedQuizzes.has(id) ? null : <Fragment key={id}><InlineChatQuiz id={id} /></Fragment>)}
  </div>
}
