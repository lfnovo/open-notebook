'use client'

import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Badge } from '@/components/ui/badge'
import ReactMarkdown from 'react-markdown'
import { useInsight } from '@/lib/hooks/use-insights'

interface SourceInsightDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  insight?: {
    id: string
    insight_type?: string
    content?: string
    created?: string
  }
}

export function SourceInsightDialog({ open, onOpenChange, insight }: SourceInsightDialogProps) {
  // Ensure insight ID has 'source_insight:' prefix for API calls
  const insightIdWithPrefix = insight?.id
    ? (insight.id.includes(':') ? insight.id : `source_insight:${insight.id}`)
    : ''

  const { data: fetchedInsight, isLoading } = useInsight(insightIdWithPrefix, { enabled: open && !!insight?.id })

  // Use fetched data if available, otherwise fall back to passed-in insight
  const displayInsight = fetchedInsight ?? insight

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-3xl max-h-[90vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center justify-between gap-2">
            <span>Source Insight</span>
            {displayInsight?.insight_type && (
              <Badge variant="outline" className="text-xs uppercase">
                {displayInsight.insight_type}
              </Badge>
            )}
          </DialogTitle>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto min-h-0">
          {isLoading ? (
            <div className="flex items-center justify-center py-10">
              <span className="text-sm text-muted-foreground">Loading insight…</span>
            </div>
          ) : displayInsight ? (
            <div className="prose prose-sm prose-neutral dark:prose-invert max-w-none">
              <ReactMarkdown>{displayInsight.content}</ReactMarkdown>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No insight selected.</p>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
