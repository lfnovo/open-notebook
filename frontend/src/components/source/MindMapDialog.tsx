'use client'

import { useState, useEffect } from 'react'
import { mindmapApi, MindMapNode } from '@/lib/api/mindmap'
import { Button } from '@/components/ui/button'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { toast } from 'sonner'
import { GitBranch, ChevronRight, ChevronDown } from 'lucide-react'

// ── Tree node renderer ────────────────────────────────────────────────────────
function MindMapNodeView({ node, depth = 0 }: { node: MindMapNode; depth?: number }) {
  const [expanded, setExpanded] = useState(true)
  const hasChildren = !!node.children?.length

  return (
    <div className={`${depth > 0 ? 'ml-5 border-l border-border pl-3' : ''} mt-2`}>
      <div
        className={`flex items-center gap-1 rounded px-2 py-1 text-sm cursor-pointer hover:bg-muted/50 ${
          depth === 0 ? 'font-bold text-base' : depth === 1 ? 'font-semibold text-primary' : ''
        }`}
        onClick={() => hasChildren && setExpanded(!expanded)}
      >
        {hasChildren ? (
          expanded
            ? <ChevronDown className="h-3 w-3 shrink-0 text-muted-foreground" />
            : <ChevronRight className="h-3 w-3 shrink-0 text-muted-foreground" />
        ) : (
          <span className="h-3 w-3 shrink-0 inline-block rounded-full bg-muted-foreground/40" />
        )}
        <span>{node.label}</span>
      </div>
      {hasChildren && expanded && (
        <div>
          {node.children!.map((child, i) => (
            <MindMapNodeView key={i} node={child} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  )
}

// ── Controlled dialog (used by StudioSection) ─────────────────────────────────
interface MindMapDialogProps {
  sourceId: string
  sourceTitle?: string | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function MindMapDialog({ sourceId, sourceTitle, open, onOpenChange }: MindMapDialogProps) {
  const [loading, setLoading] = useState(false)
  const [mindMap, setMindMap] = useState<MindMapNode | null>(null)

  // Trigger generation when dialog opens
  useEffect(() => {
    if (!open) return
    setMindMap(null)
    setLoading(true)

    mindmapApi.generate(sourceId)
      .then(result => setMindMap(result.mind_map))
      .catch(err => {
        console.error('Mind map generation failed:', err)
        toast.error('Failed to generate mind map')
        onOpenChange(false)
      })
      .finally(() => setLoading(false))
  }, [open, sourceId, onOpenChange])

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <GitBranch className="h-5 w-5" />
            Mind Map{sourceTitle ? ` — ${sourceTitle}` : ''}
          </DialogTitle>
        </DialogHeader>

        {loading ? (
          <div className="flex flex-col items-center justify-center py-16 gap-3">
            <LoadingSpinner />
            <p className="text-sm text-muted-foreground">
              Analyzing content and building mind map...
            </p>
          </div>
        ) : mindMap ? (
          <div className="rounded-lg border bg-muted/20 p-4">
            <MindMapNodeView node={mindMap} />
          </div>
        ) : null}
      </DialogContent>
    </Dialog>
  )
}

// ── Standalone button variant (used in SourceDetailContent header) ────────────
interface MindMapButtonProps {
  sourceId: string
  sourceTitle?: string | null
}

export function MindMapButton({ sourceId, sourceTitle }: MindMapButtonProps) {
  const [open, setOpen] = useState(false)

  return (
    <>
      <Button variant="outline" size="sm" onClick={() => setOpen(true)}>
        <GitBranch className="mr-2 h-4 w-4" />
        Mind Map
      </Button>
      <MindMapDialog
        open={open}
        onOpenChange={setOpen}
        sourceId={sourceId}
        sourceTitle={sourceTitle}
      />
    </>
  )
}
