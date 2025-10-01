'use client'

import { FileText, Lightbulb, StickyNote } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

interface ContextIndicatorProps {
  sourcesInsights: number
  sourcesFull: number
  notesCount: number
  className?: string
}

export function ContextIndicator({
  sourcesInsights,
  sourcesFull,
  notesCount,
  className
}: ContextIndicatorProps) {
  const totalSources = sourcesInsights + sourcesFull
  const hasContext = totalSources > 0 || notesCount > 0

  if (!hasContext) {
    return (
      <div className={cn('text-xs text-muted-foreground py-2 px-3 border-t', className)}>
        No sources or notes included in context. Toggle icons on cards to include them.
      </div>
    )
  }

  return (
    <div className={cn('flex items-center gap-2 py-2 px-3 border-t bg-muted/30', className)}>
      <span className="text-xs font-medium text-muted-foreground">Context:</span>

      {totalSources > 0 && (
        <div className="flex items-center gap-1.5">
          <Badge variant="secondary" className="text-xs flex items-center gap-1">
            <FileText className="h-3 w-3" />
            {totalSources} source{totalSources !== 1 ? 's' : ''}
          </Badge>

          {sourcesInsights > 0 && (
            <Badge variant="outline" className="text-xs flex items-center gap-1 text-amber-600 border-amber-600/50">
              <Lightbulb className="h-3 w-3" />
              {sourcesInsights} insights
            </Badge>
          )}

          {sourcesFull > 0 && (
            <Badge variant="outline" className="text-xs flex items-center gap-1 text-primary border-primary/50">
              <FileText className="h-3 w-3" />
              {sourcesFull} full
            </Badge>
          )}
        </div>
      )}

      {notesCount > 0 && (
        <>
          {totalSources > 0 && (
            <span className="text-muted-foreground">•</span>
          )}
          <Badge variant="secondary" className="text-xs flex items-center gap-1">
            <StickyNote className="h-3 w-3" />
            {notesCount} note{notesCount !== 1 ? 's' : ''}
          </Badge>
        </>
      )}
    </div>
  )
}
