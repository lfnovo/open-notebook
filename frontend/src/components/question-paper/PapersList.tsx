'use client'

import { useMemo, useState } from 'react'
import { useTranslation } from '@/lib/hooks/use-translation'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Loader2, Trash2 } from 'lucide-react'
import type { PaperStatus, PaperSummary } from '@/lib/types/question-paper'
import { useQuestionBooks } from '@/lib/hooks/use-question-paper'
import {
  formatCreatedDate,
  formatPaperStatus,
  formatQuestionProgress,
  formatDifficultyMixLabel,
  paperDisplayStatus,
} from '@/lib/question-paper-labels'

interface PapersListProps {
  papers: PaperSummary[]
  onSelect: (paperId: string) => void
  onDelete: (paperId: string) => void
  selectedId: string | null
  deletingId: string | null
}

const ALL = '__all__'

function uniqueSorted(values: Array<string | null | undefined>): string[] {
  return Array.from(new Set(values.map((value) => (value || '').trim()).filter(Boolean))).sort()
}

function paperMatchesDate(created: string, preset: string): boolean {
  if (!preset) return true
  const createdAt = new Date(created)
  if (Number.isNaN(createdAt.getTime())) return false
  const now = new Date()
  const start = new Date(now)
  if (preset === 'today') {
    start.setHours(0, 0, 0, 0)
  } else if (preset === '7d') {
    start.setDate(start.getDate() - 7)
  } else if (preset === '30d') {
    start.setDate(start.getDate() - 30)
  } else {
    return true
  }
  return createdAt >= start
}

function statusClass(status: PaperStatus | string): string {
  if (status === 'completed') return 'text-green-700'
  if (status === 'partial' || status === 'completed_partial' || status === 'needs_manual_review') {
    return 'text-amber-700'
  }
  if (status === 'failed') return 'text-destructive'
  if (status === 'running' || status === 'pending') return 'text-blue-700'
  return 'text-muted-foreground'
}

export function PapersList({
  papers,
  onSelect,
  onDelete,
  selectedId,
  deletingId,
}: PapersListProps) {
  const { t } = useTranslation()
  const [grade, setGrade] = useState('')
  const [bookId, setBookId] = useState('')
  const [status, setStatus] = useState('')
  const [difficultyMix, setDifficultyMix] = useState('')
  const [datePreset, setDatePreset] = useState('')

  const grades = useMemo(() => uniqueSorted(papers.map((paper) => paper.grade)), [papers])
  const bookIds = useMemo(() => uniqueSorted(papers.map((paper) => paper.book_id)), [papers])
  const bookTitles = useQuestionBooks(bookIds)

  const filtered = useMemo(() => {
    return papers.filter((paper) => {
      if (grade && String(paper.grade || '') !== grade) return false
      if (bookId && String(paper.book_id || '') !== bookId) return false
      if (status === 'running') {
        if (paper.status !== 'running' && paper.status !== 'pending') return false
      } else if (status && paper.status !== status) {
        return false
      }
      if (difficultyMix && paper.difficulty_mix !== difficultyMix) return false
      if (!paperMatchesDate(paper.created, datePreset)) return false
      return true
    })
  }, [papers, grade, bookId, status, difficultyMix, datePreset])

  if (papers.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        <p className="text-sm">{t.questionPaper.noPapers}</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-3">
        <div className="space-y-1.5">
          <Label>{t.questionPaper.grade}</Label>
          <Select value={grade || ALL} onValueChange={(value) => setGrade(value === ALL ? '' : value)}>
            <SelectTrigger><SelectValue placeholder={t.questionPaper.filterAll} /></SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>{t.questionPaper.filterAll}</SelectItem>
              {grades.map((value) => (
                <SelectItem key={value} value={value}>{value}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1.5">
          <Label>{t.questionPaper.bankFilterBook}</Label>
          <Select value={bookId || ALL} onValueChange={(value) => setBookId(value === ALL ? '' : value)}>
            <SelectTrigger><SelectValue placeholder={t.questionPaper.filterAll} /></SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>{t.questionPaper.filterAll}</SelectItem>
              {bookIds.map((id) => (
                <SelectItem key={id} value={id}>{bookTitles[id] || id}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1.5">
          <Label>{t.questionPaper.status}</Label>
          <Select value={status || ALL} onValueChange={(value) => setStatus(value === ALL ? '' : value)}>
            <SelectTrigger><SelectValue placeholder={t.questionPaper.filterAll} /></SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>{t.questionPaper.filterAll}</SelectItem>
              <SelectItem value="completed">{t.questionPaper.statusCompleted}</SelectItem>
              <SelectItem value="needs_manual_review">{t.questionPaper.statusNeedsReview}</SelectItem>
              <SelectItem value="failed">{t.questionPaper.statusFailed}</SelectItem>
              <SelectItem value="running">{t.questionPaper.statusRunning}</SelectItem>
              <SelectItem value="pending">{t.questionPaper.statusRunning}</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1.5">
          <Label>{t.questionPaper.historyFilterDifficulty}</Label>
          <Select value={difficultyMix || ALL} onValueChange={(value) => setDifficultyMix(value === ALL ? '' : value)}>
            <SelectTrigger><SelectValue placeholder={t.questionPaper.filterAll} /></SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>{t.questionPaper.filterAll}</SelectItem>
              <SelectItem value="easy_only">{t.questionPaper.difficultyEasyOnly}</SelectItem>
              <SelectItem value="medium_only">{t.questionPaper.difficultyMediumOnly}</SelectItem>
              <SelectItem value="difficult_only">{t.questionPaper.difficultyDifficultOnly}</SelectItem>
              <SelectItem value="mixed">{t.questionPaper.difficultyMixed}</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1.5">
          <Label>{t.questionPaper.historyFilterDate}</Label>
          <Select value={datePreset || ALL} onValueChange={(value) => setDatePreset(value === ALL ? '' : value)}>
            <SelectTrigger><SelectValue placeholder={t.questionPaper.filterAll} /></SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>{t.questionPaper.filterAll}</SelectItem>
              <SelectItem value="today">{t.questionPaper.historyDateToday}</SelectItem>
              <SelectItem value="7d">{t.questionPaper.historyDate7d}</SelectItem>
              <SelectItem value="30d">{t.questionPaper.historyDate30d}</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="overflow-x-auto rounded-md border">
        <table className="w-full text-sm">
          <thead className="bg-muted/50 text-left">
            <tr className="border-b">
              <th className="px-3 py-2 font-medium">{t.questionPaper.historyColName}</th>
              <th className="px-3 py-2 font-medium">{t.questionPaper.grade}</th>
              <th className="px-3 py-2 font-medium">{t.questionPaper.bankFilterBook}</th>
              <th className="px-3 py-2 font-medium">{t.questionPaper.historyColQuestions}</th>
              <th className="px-3 py-2 font-medium">{t.questionPaper.historyColDifficultyMix}</th>
              <th className="px-3 py-2 font-medium">{t.questionPaper.status}</th>
              <th className="px-3 py-2 font-medium">{t.questionPaper.historyColCreated}</th>
              <th className="px-3 py-2 font-medium text-right">{t.questionPaper.historyColActions}</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((paper) => (
              <tr
                key={paper.paper_id}
                className={`border-b last:border-0 ${selectedId === paper.paper_id ? 'bg-accent/40' : ''}`}
              >
                <td className="px-3 py-2">
                  <p className="font-medium">{paper.topic || paper.paper_id}</p>
                  <p className="text-xs text-muted-foreground">{paper.paper_id}</p>
                </td>
                <td className="px-3 py-2 whitespace-nowrap">{paper.grade || '—'}</td>
                <td className="px-3 py-2 whitespace-nowrap max-w-[12rem] truncate" title={bookTitles[paper.book_id || ''] || paper.book_id || ''}>
                  {paper.book_id ? (bookTitles[paper.book_id] || paper.book_id) : '—'}
                </td>
                <td className="px-3 py-2 whitespace-nowrap">
                  {formatQuestionProgress(
                    paper.generated_questions,
                    paper.requested_questions,
                  )}
                </td>
                <td className="px-3 py-2 whitespace-nowrap">
                  {paper.difficulty_mix_label || formatDifficultyMixLabel(paper.requested_difficulty)}
                </td>
                <td
                  className={`px-3 py-2 whitespace-nowrap font-medium ${statusClass(paperDisplayStatus(paper))}`}
                >
                  {formatPaperStatus(paperDisplayStatus(paper))}
                </td>
                <td className="px-3 py-2 whitespace-nowrap text-muted-foreground">
                  {formatCreatedDate(paper.created)}
                </td>
                <td className="px-3 py-2">
                  <div className="flex justify-end gap-2">
                    <Button variant="outline" size="sm" onClick={() => onSelect(paper.paper_id)}>
                      {t.questionPaper.bankColView}
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8"
                      onClick={() => onDelete(paper.paper_id)}
                      disabled={deletingId === paper.paper_id}
                    >
                      {deletingId === paper.paper_id ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <Trash2 className="h-3.5 w-3.5" />
                      )}
                    </Button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
