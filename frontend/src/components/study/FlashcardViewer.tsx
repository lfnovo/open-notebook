'use client'

import { useState } from 'react'
import { ChevronLeft, ChevronRight, RotateCcw } from 'lucide-react'

import { FlashcardItem } from '@/lib/types/study'
import { useTranslation } from '@/lib/hooks/use-translation'
import { Button } from '@/components/ui/button'

interface FlashcardViewerProps {
  items: FlashcardItem[]
}

export function FlashcardViewer({ items }: FlashcardViewerProps) {
  const { t } = useTranslation()
  const [index, setIndex] = useState(0)
  const [flipped, setFlipped] = useState(false)

  if (items.length === 0) {
    return null
  }

  const card = items[index]

  const goTo = (nextIndex: number) => {
    setIndex(Math.max(0, Math.min(items.length - 1, nextIndex)))
    setFlipped(false)
  }

  return (
    <div className="flex flex-col items-center gap-4">
      <p className="text-sm text-muted-foreground">
        {t('study.cardProgress', { current: index + 1, total: items.length })}
      </p>

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
        <Button variant="outline" size="sm" onClick={() => goTo(index - 1)} disabled={index === 0}>
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
          onClick={() => goTo(index + 1)}
          disabled={index === items.length - 1}
        >
          {t('common.next')}
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  )
}
