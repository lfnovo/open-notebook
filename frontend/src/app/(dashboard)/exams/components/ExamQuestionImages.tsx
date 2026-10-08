'use client'

import type { ChatImage } from '@/lib/types/api'
import type { ExamQuestion } from '@/lib/types/exams'
import { ChatImages } from '@/components/sources/ChatImages'
import { useTranslation } from '@/lib/hooks/use-translation'

export function ExamQuestionImages({ question, images = {}, review = false }: {
  question: ExamQuestion
  images?: Record<string, ChatImage>
  review?: boolean
}) {
  const { t } = useTranslation()
  return <div className="space-y-3">
    {(question.image_ids ?? []).map((id) => {
      const image = images[id]
      if (!image) return null
      const label = t('exams.figure', { n: id.replace(/^figure/, '') })
      return <figure key={id} className="space-y-1">
        <ChatImages images={[{ ...image, name: label }]} large showProvenance={review} />
        <figcaption className="text-sm text-muted-foreground">{label}</figcaption>
      </figure>
    })}
  </div>
}
