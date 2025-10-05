'use client'

import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Badge } from '@/components/ui/badge'
import ReactMarkdown from 'react-markdown'

interface SourceInsightDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  insight?: {
    id: string
    insight_type: string
    content: string
    created?: string
  }
}

export function SourceInsightDialog({ open, onOpenChange, insight }: SourceInsightDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-3xl max-h-[90vh] overflow-hidden">
        <DialogHeader>
          <DialogTitle className="flex items-center justify-between gap-2">
            <span>Source Insight</span>
            {insight?.insight_type && (
              <Badge variant="outline" className="text-xs uppercase">
                {insight.insight_type}
              </Badge>
            )}
          </DialogTitle>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto">
          {insight ? (
            <div className="prose prose-sm prose-neutral dark:prose-invert max-w-none">
              <ReactMarkdown>{insight.content}</ReactMarkdown>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No insight selected.</p>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
