'use client'

import { FileText, Lightbulb, StickyNote } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

interface ContextIndicatorProps {
  sourcesInsights: number
  sourcesFull: number
  notesCount: number
  tokenCount?: number
  charCount?: number
  className?: string
}

// Helper function to format large numbers with K/M suffixes
function formatNumber(num: number): string {
  if (num >= 1000000) {
    return `${(num / 1000000).toFixed(1)}M`
  }
  if (num >= 1000) {
    return `${(num / 1000).toFixed(1)}K`
  }
  return num.toString()
}

export function ContextIndicator({
  sourcesInsights,
  sourcesFull,
  notesCount,
  tokenCount,
  charCount,
  className
}: ContextIndicatorProps) {
  const totalSources = sourcesInsights + sourcesFull
  const hasContext = totalSources > 0 || notesCount > 0

  if (!hasContext) {
    return (
      <div className={cn('flex-shrink-0 text-xs text-muted-foreground py-2 px-3 border-t', className)}>
        No sources or notes included in context. Toggle icons on cards to include them.
      </div>
    )
  }

  return (
    <div className={cn('flex-shrink-0 flex items-center justify-between gap-2 py-2 px-3 border-t bg-muted/30', className)}>
      <div className="flex items-center gap-2">
        <span className="text-xs font-medium text-muted-foreground">Context:</span>

        {totalSources > 0 && (
          <div className="flex items-center gap-1.5">
            <Badge variant="secondary" className="text-xs flex items-center gap-1 px-1.5 py-0.5">
              <FileText className="h-3 w-3" />
              <span>{totalSources}</span>
            </Badge>

            {sourcesInsights > 0 && (
              <Badge variant="outline" className="text-xs flex items-center gap-1 px-1.5 py-0.5 text-amber-600 border-amber-600/50">
                <Lightbulb className="h-3 w-3" />
                <span>{sourcesInsights}</span>
              </Badge>
            )}

            {sourcesFull > 0 && (
              <Badge variant="outline" className="text-xs flex items-center gap-1 px-1.5 py-0.5 text-primary border-primary/50">
                <FileText className="h-3 w-3" />
                <span>{sourcesFull}</span>
              </Badge>
            )}
          </div>
        )}

        {notesCount > 0 && (
          <>
            {totalSources > 0 && (
              <span className="text-muted-foreground">•</span>
            )}
            <Badge variant="secondary" className="text-xs flex items-center gap-1 px-1.5 py-0.5">
              <StickyNote className="h-3 w-3" />
              <span>{notesCount}</span>
            </Badge>
          </>
        )}
      </div>

      {(tokenCount !== undefined || charCount !== undefined) && (
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          {tokenCount !== undefined && tokenCount > 0 && (
            <span>{formatNumber(tokenCount)} tokens</span>
          )}
          {tokenCount !== undefined && charCount !== undefined && tokenCount > 0 && charCount > 0 && (
            <span>/</span>
          )}
          {charCount !== undefined && charCount > 0 && (
            <span>{formatNumber(charCount)} chars</span>
          )}
        </div>
      )}
    </div>
  )
}
