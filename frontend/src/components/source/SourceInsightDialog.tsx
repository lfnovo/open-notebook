'use client'

import { useState, useEffect } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { FileText } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { useInsight } from '@/lib/hooks/use-insights'
import { useModalManager } from '@/lib/hooks/use-modal-manager'

interface SourceInsightDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  insight?: {
    id: string
    insight_type?: string
    content?: string
    created?: string
    source_id?: string
  }
  onDelete?: (insightId: string) => Promise<void>
}

export function SourceInsightDialog({ open, onOpenChange, insight, onDelete }: SourceInsightDialogProps) {
  const { openModal } = useModalManager()
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)

  // Ensure insight ID has 'source_insight:' prefix for API calls
  const insightIdWithPrefix = insight?.id
    ? (insight.id.includes(':') ? insight.id : `source_insight:${insight.id}`)
    : ''

  const { data: fetchedInsight, isLoading } = useInsight(insightIdWithPrefix, { enabled: open && !!insight?.id })

  // Use fetched data if available, otherwise fall back to passed-in insight
  const displayInsight = fetchedInsight ?? insight

  // Get source_id from fetched data (preferred) or passed-in insight
  const sourceId = fetchedInsight?.source_id ?? insight?.source_id

  const handleViewSource = () => {
    if (sourceId) {
      openModal('source', sourceId)
    }
  }

  const handleDelete = async () => {
    if (!insight?.id || !onDelete) return
    setIsDeleting(true)
    try {
      await onDelete(insight.id)
      onOpenChange(false)
    } finally {
      setIsDeleting(false)
      setShowDeleteConfirm(false)
    }
  }

  // Reset delete confirmation when dialog closes
  useEffect(() => {
    if (!open) {
      setShowDeleteConfirm(false)
    }
  }, [open])

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-3xl max-h-[90vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center justify-between gap-2">
            <span>Source Insight</span>
            <div className="flex items-center gap-2">
              {displayInsight?.insight_type && (
                <Badge variant="outline" className="text-xs uppercase">
                  {displayInsight.insight_type}
                </Badge>
              )}
              {sourceId && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleViewSource}
                  className="gap-1"
                >
                  <FileText className="h-3 w-3" />
                  View Source
                </Button>
              )}
            </div>
          </DialogTitle>
        </DialogHeader>

        {showDeleteConfirm ? (
          <div className="flex flex-col items-center justify-center py-8 gap-4">
            <p className="text-center text-muted-foreground">
              Are you sure you want to delete this insight?<br />
              <span className="text-sm">This action cannot be undone.</span>
            </p>
            <div className="flex gap-2">
              <Button
                variant="outline"
                onClick={() => setShowDeleteConfirm(false)}
                disabled={isDeleting}
              >
                Cancel
              </Button>
              <Button
                variant="destructive"
                onClick={handleDelete}
                disabled={isDeleting}
              >
                {isDeleting ? 'Deleting...' : 'Delete'}
              </Button>
            </div>
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto min-h-0">
            {isLoading ? (
              <div className="flex items-center justify-center py-10">
                <span className="text-sm text-muted-foreground">Loading insight…</span>
              </div>
            ) : displayInsight ? (
              <div className="prose prose-sm prose-neutral dark:prose-invert max-w-none">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={{
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
                  }}
                >
                  {displayInsight.content}
                </ReactMarkdown>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No insight selected.</p>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
