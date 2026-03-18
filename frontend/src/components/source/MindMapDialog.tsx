'use client'

import { useState } from 'react'
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

interface MindMapNodeProps {
  node: MindMapNode
  depth?: number
}

function MindMapNodeView({ node, depth = 0 }: MindMapNodeProps) {
  const [expanded, setExpanded] = useState(true)
  const hasChildren = node.children && node.children.length > 0

  return (
    <div className={`${depth > 0 ? 'ml-5 border-l border-border pl-3' : ''} mt-2`}>
      <div
        className={`flex items-center gap-1 rounded px-2 py-1 text-sm cursor-pointer hover:bg-muted/50 ${
          depth === 0 ? 'font-bold text-base' : depth === 1 ? 'font-semibold text-primary' : ''
        }`}
        onClick={() => hasChildren && setExpanded(!expanded)}
      >
        {hasChildren ? (
          expanded ? (
            <ChevronDown className="h-3 w-3 shrink-0 text-muted-foreground" />
          ) : (
            <ChevronRight className="h-3 w-3 shrink-0 text-muted-foreground" />
          )
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

interface MindMapDialogProps {
  sourceId: string
  sourceTitle?: string | null
}

export function MindMapDialog({ sourceId, sourceTitle }: MindMapDialogProps) {
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [mindMap, setMindMap] = useState<MindMapNode | null>(null)

  const handleGenerate = async () => {
    try {
      setLoading(true)
      setOpen(true)
      const result = await mindmapApi.generate(sourceId)
      setMindMap(result.mind_map)
    } catch (err) {
      console.error('Mind map generation failed:', err)
      toast.error('Failed to generate mind map')
      setOpen(false)
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <Button variant="outline" size="sm" onClick={handleGenerate} disabled={loading}>
        <GitBranch className="mr-2 h-4 w-4" />
        {loading ? 'Generating...' : 'Mind Map'}
      </Button>

      <Dialog open={open} onOpenChange={setOpen}>
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
    </>
  )
}
