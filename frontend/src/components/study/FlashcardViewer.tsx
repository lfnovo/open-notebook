'use client'

import { useMemo, useState } from 'react'
import { ChevronLeft, ChevronRight, RotateCcw } from 'lucide-react'

import { FlashcardItem, SrsRating } from '@/lib/types/study'
import { useTranslation } from '@/lib/hooks/use-translation'
import { useReviewFlashcard } from '@/lib/hooks/use-study'
import { buildQueue, isDue, todayIso } from '@/lib/utils/flashcard-queue'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'

interface FlashcardViewerProps {
  items: FlashcardItem[]
  studySetId: string
  notebookId?: string
}

const RATING_STYLES: Record<SrsRating, string> = {
  again: 'border-destructive/40 text-destructive hover:bg-destructive-tint',
  hard: 'border-gold/40 text-gold hover:bg-gold-tint',
  good: 'border-fern/40 text-fern hover:bg-fern-tint',
  easy: 'border-teal/40 text-teal hover:bg-teal-tint',
}

// Written as literal keys (not a template string) so the i18n unused-key
// checker (src/lib/locales/index.test.ts, plain substring search) can find
// them.
const RATING_LABEL_KEY: Record<SrsRating, string> = {
  again: 'study.rating.again',
  hard: 'study.rating.hard',
  good: 'study.rating.good',
  easy: 'study.rating.easy',
}

export function FlashcardViewer({ items, studySetId, notebookId }: FlashcardViewerProps) {
  const { t } = useTranslation()
  const [position, setPosition] = useState(0)
  const [flipped, setFlipped] = useState(false)
  const reviewFlashcard = useReviewFlashcard(studySetId, notebookId)

  // Built once per study set (not on every `items` update, which would
  // reshuffle the deck under the user mid-session as reviews change due
  // dates - see useReviewFlashcard's optimistic cache patch).
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const queue = useMemo(() => buildQueue(items), [studySetId])

  const dueCount = useMemo(() => {
    const today = todayIso()
    return items.filter((item) => isDue(item, today)).length
  }, [items])

  if (items.length === 0) {
    return null
  }

  const clampedPosition = Math.min(position, queue.length - 1)
  const originalIndex = queue[clampedPosition]
  const card = items[originalIndex]
  const cardDue = isDue(card, todayIso())

  const goTo = (nextPosition: number) => {
    setPosition(Math.max(0, Math.min(queue.length - 1, nextPosition)))
    setFlipped(false)
  }

  const handleRate = (rating: SrsRating) => {
    reviewFlashcard.mutate({ itemIndex: originalIndex, rating })
    if (clampedPosition < queue.length - 1) {
      goTo(clampedPosition + 1)
    } else {
      setFlipped(false)
    }
  }

  return (
    <div className="flex flex-col items-center gap-4">
      <div className="flex flex-wrap items-center justify-center gap-2">
        <p className="text-sm text-muted-foreground">
          {t('study.cardProgress', { current: clampedPosition + 1, total: queue.length })}
        </p>
        {dueCount > 0 ? (
          <Badge variant="outline" className="border-teal/40 text-teal">
            {t('study.dueCount', { count: dueCount })}
          </Badge>
        ) : (
          <Badge variant="outline" className="border-fern/40 text-fern">
            {t('study.allCaughtUp')}
          </Badge>
        )}
      </div>

      <div
        className="w-full max-w-xl [perspective:1200px]"
        role="button"
        tabIndex={0}
        aria-label={t('study.flipCard')}
        onClick={() => setFlipped((prev) => !prev)}
        onKeyDown={(event) => {
          if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault()
            setFlipped((prev) => !prev)
          }
        }}
      >
        <div
          className="relative h-64 w-full cursor-pointer transition-transform duration-500 [transform-style:preserve-3d]"
          style={{ transform: flipped ? 'rotateY(180deg)' : 'rotateY(0deg)' }}
        >
          <div className="absolute inset-0 flex items-center justify-center rounded-xl border bg-card p-6 text-center shadow-sm [backface-visibility:hidden]">
            <p className="text-lg font-medium text-foreground">{card.front}</p>
          </div>
          <div
            className="absolute inset-0 flex items-center justify-center rounded-xl border bg-fern-tint p-6 text-center shadow-sm [backface-visibility:hidden]"
            style={{ transform: 'rotateY(180deg)' }}
          >
            <p className="text-lg text-foreground">{card.back}</p>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => goTo(clampedPosition - 1)}
          disabled={clampedPosition === 0}
        >
          <ChevronLeft className="h-4 w-4" />
          {t('study.previous')}
        </Button>
        <Button variant="outline" size="sm" onClick={() => setFlipped((prev) => !prev)}>
          <RotateCcw className="h-4 w-4" />
          {t('study.flipCard')}
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => goTo(clampedPosition + 1)}
          disabled={clampedPosition === queue.length - 1}
        >
          {t('common.next')}
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>

      {flipped ? (
        <div className="flex flex-col items-center gap-2">
          <p className="text-xs text-muted-foreground">{t('study.reviewPrompt')}</p>
          <div className="flex flex-wrap items-center justify-center gap-2">
            {(['again', 'hard', 'good', 'easy'] as SrsRating[]).map((rating) => (
              <Button
                key={rating}
                variant="outline"
                size="sm"
                disabled={reviewFlashcard.isPending}
                onClick={() => handleRate(rating)}
                className={cn(RATING_STYLES[rating])}
              >
                {t(RATING_LABEL_KEY[rating])}
              </Button>
            ))}
          </div>
          {!cardDue ? (
            <p className="text-xs text-muted-foreground">{t('study.reviewAheadHint')}</p>
          ) : null}
        </div>
      ) : null}
    </div>
  )
}
