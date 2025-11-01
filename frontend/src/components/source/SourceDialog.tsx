'use client'

import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog'
import { SourceDetailContent } from './SourceDetailContent'

interface SourceDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  sourceId: string | null
}

/**
 * Source Dialog Component
 *
 * Displays source details in a modal dialog.
 * Includes a "Chat with source" button that opens the full source page in a new tab.
 */
export function SourceDialog({ open, onOpenChange, sourceId }: SourceDialogProps) {
  // Ensure source ID has 'source:' prefix for API calls and routing
  const sourceIdWithPrefix = sourceId
    ? (sourceId.includes(':') ? sourceId : `source:${sourceId}`)
    : null

  const handleChatClick = () => {
    if (sourceIdWithPrefix) {
      window.open(`/sources/${sourceIdWithPrefix}`, '_blank')
      // Modal stays open after opening chat
    }
  }

  const handleClose = () => {
    onOpenChange(false)
  }

  if (!sourceIdWithPrefix) {
    return null
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-5xl max-h-[90vh] flex flex-col p-0">
        {/* Accessibility title (hidden visually but read by screen readers) */}
        <DialogTitle className="sr-only">Source Details</DialogTitle>

        {/* Source detail content */}
        <div className="flex-1 overflow-y-auto min-h-0">
          <SourceDetailContent
            sourceId={sourceIdWithPrefix}
            showChatButton={true}
            onChatClick={handleChatClick}
            onClose={handleClose}
          />
        </div>
      </DialogContent>
    </Dialog>
  )
}
