'use client'

import { useState, useEffect } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { GitBranch, Newspaper, CheckCircle2, FileText as FileTextIcon } from 'lucide-react'
import { sourcesApi } from '@/lib/api/sources'
import { SourceListResponse } from '@/lib/types/api'
import { MindMapDialog } from '@/components/source/MindMapDialog'
import { InfographicDialog } from '@/components/source/InfographicDialog'
import { SummaryDialog, hasSummaryCache } from '@/components/source/SummaryDialog'
import { loadCachedInfographic } from '@/lib/api/infographic'
import { cn } from '@/lib/utils'

function hasMindMapCache(sourceId: string): boolean {
  try { return !!localStorage.getItem('mindmap_cache_' + sourceId) } catch { return false }
}

function hasInfographicCache(sourceId: string): boolean {
  try { return !!loadCachedInfographic(sourceId) } catch { return false }
}

type StudioMode = 'mindmap' | 'infographic' | 'summary'

interface SourcePickerDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  mode: StudioMode
}

export function SourcePickerDialog({ open, onOpenChange, mode }: SourcePickerDialogProps) {
  const [sources, setSources] = useState<SourceListResponse[]>([])
  const [loading, setLoading] = useState(false)

  // selectedSource and resultOpen are NEVER reset to null/false once set
  // so the result dialog stays mounted and visible
  const [selectedSource, setSelectedSource] = useState<SourceListResponse | null>(null)
  const [resultOpen, setResultOpen] = useState(false)

  useEffect(() => {
    if (!open) return
    setLoading(true)
    sourcesApi.list({ sort_by: 'updated', sort_order: 'desc' })
      .then(setSources)
      .catch(() => setSources([]))
      .finally(() => setLoading(false))
  }, [open])

  const handleSelect = (source: SourceListResponse) => {
    // Set the source first, then close picker, then open result
    setSelectedSource(source)
    setResultOpen(false) // reset so useEffect in result dialog fires fresh
    onOpenChange(false)  // close picker
    // Use setTimeout to ensure React has flushed the above state updates
    // before opening the result dialog
    setTimeout(() => {
      setResultOpen(true)
    }, 50)
  }

  const title = mode === 'mindmap' ? 'Mind Map' : mode === 'infographic' ? 'Infographic' : 'Summary'
  const icon = mode === 'mindmap'
    ? <GitBranch className="h-5 w-5 text-pink-500" />
    : mode === 'infographic'
    ? <Newspaper className="h-5 w-5 text-purple-500" />
    : <FileTextIcon className="h-5 w-5 text-blue-500" />

  return (
    <>
      {/* Source picker dialog */}
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-w-md max-h-[80vh] flex flex-col">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {icon}
              {title} — Select a Source
            </DialogTitle>
          </DialogHeader>

          <p className="text-xs text-muted-foreground -mt-1">
            Choose a source to generate the {title.toLowerCase()} for.
            Sources with a cached result are marked with a green badge.
          </p>

          <div className="flex-1 overflow-y-auto space-y-2 mt-2 pr-1">
            {loading && (
              <div className="flex justify-center py-10">
                <LoadingSpinner />
              </div>
            )}

            {!loading && sources.length === 0 && (
              <p className="text-sm text-muted-foreground text-center py-10">
                No sources found. Add a source first.
              </p>
            )}

            {!loading && sources.map((source) => {
              const cached = mode === 'mindmap'
                ? hasMindMapCache(source.id)
                : mode === 'infographic'
                ? hasInfographicCache(source.id)
                : hasSummaryCache(source.id)

              return (
                <button
                  key={source.id}
                  onClick={() => handleSelect(source)}
                  className={cn(
                    'w-full flex items-center gap-3 px-4 py-3 rounded-xl border text-left transition-all',
                    'hover:bg-accent hover:border-accent-foreground/20',
                    'bg-background border-border/60'
                  )}
                >
                  <FileTextIcon className="h-4 w-4 text-muted-foreground shrink-0" />
                  <span className="flex-1 text-sm font-medium truncate">
                    {source.title || 'Untitled Source'}
                  </span>
                  {cached && (
                    <span className="flex items-center gap-1 text-xs text-green-600 shrink-0">
                      <CheckCircle2 className="h-3.5 w-3.5" />
                      Cached
                    </span>
                  )}
                </button>
              )
            })}
          </div>
        </DialogContent>
      </Dialog>

      {/* Result dialogs — always mounted once a source is selected */}
      {selectedSource && mode === 'mindmap' && (
        <MindMapDialog
          open={resultOpen}
          onOpenChange={setResultOpen}
          sourceId={selectedSource.id}
          sourceTitle={selectedSource.title}
        />
      )}
      {selectedSource && mode === 'infographic' && (
        <InfographicDialog
          open={resultOpen}
          onOpenChange={setResultOpen}
          sourceId={selectedSource.id}
          sourceTitle={selectedSource.title}
        />
      )}
      {selectedSource && mode === 'summary' && (
        <SummaryDialog
          open={resultOpen}
          onOpenChange={setResultOpen}
          sourceId={selectedSource.id}
          sourceTitle={selectedSource.title}
        />
      )}
    </>
  )
}
