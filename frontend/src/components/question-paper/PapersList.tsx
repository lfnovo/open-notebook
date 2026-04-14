'use client'

import { useTranslation } from '@/lib/hooks/use-translation'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Trash2, Loader2, CheckCircle2, XCircle, Clock } from 'lucide-react'
import type { PaperSummary, PaperStatus } from '@/lib/types/question-paper'

interface PapersListProps {
  papers: PaperSummary[]
  onSelect: (paperId: string) => void
  onDelete: (paperId: string) => void
  selectedId: string | null
  deletingId: string | null
}

function StatusIcon({ status }: { status: PaperStatus }) {
  switch (status) {
    case 'completed':
      return <CheckCircle2 className="h-4 w-4 text-green-500" />
    case 'failed':
      return <XCircle className="h-4 w-4 text-destructive" />
    case 'running':
      return <Loader2 className="h-4 w-4 animate-spin text-blue-500" />
    default:
      return <Clock className="h-4 w-4 text-muted-foreground" />
  }
}

function DifficultyBadge({ difficulty }: { difficulty: string }) {
  const variant =
    difficulty === 'easy' ? 'secondary' : difficulty === 'hard' ? 'destructive' : 'default'
  return (
    <Badge variant={variant} className="capitalize text-xs">
      {difficulty}
    </Badge>
  )
}

export function PapersList({
  papers,
  onSelect,
  onDelete,
  selectedId,
  deletingId,
}: PapersListProps) {
  const { t } = useTranslation()

  if (papers.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        <p className="text-sm">{t.questionPaper.noPapers}</p>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {papers.map((paper) => (
        <div
          key={paper.paper_id}
          className={`flex items-start gap-3 rounded-lg border p-3 cursor-pointer transition-colors hover:bg-accent/50 ${
            selectedId === paper.paper_id ? 'border-primary bg-accent/30' : ''
          }`}
          onClick={() => paper.status === 'completed' && onSelect(paper.paper_id)}
        >
          <div className="mt-0.5">
            <StatusIcon status={paper.status} />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate">{paper.topic}</p>
            <div className="flex items-center gap-2 mt-1">
              <DifficultyBadge difficulty={paper.difficulty} />
              <span className="text-xs text-muted-foreground">
                {paper.target_marks} {t.questionPaper.marks}
              </span>
              {paper.status === 'failed' && paper.error_message && (
                <span className="text-xs text-destructive truncate max-w-32">
                  {paper.error_message}
                </span>
              )}
            </div>
          </div>
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 shrink-0"
            onClick={(e) => {
              e.stopPropagation()
              onDelete(paper.paper_id)
            }}
            disabled={deletingId === paper.paper_id}
          >
            {deletingId === paper.paper_id ? (
              <Loader2 className="h-3 w-3 animate-spin" />
            ) : (
              <Trash2 className="h-3 w-3" />
            )}
          </Button>
        </div>
      ))}
    </div>
  )
}
