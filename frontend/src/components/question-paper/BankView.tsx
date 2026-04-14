'use client'

import { useRef, useState } from 'react'
import { useTranslation } from '@/lib/hooks/use-translation'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Trash2, Loader2, Search } from 'lucide-react'
import { useQuestionBank, useDeleteBankQuestion } from '@/lib/hooks/use-question-paper'

export function BankView() {
  const { t } = useTranslation()
  const [query, setQuery] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const searchTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const { data: questions = [], isLoading } = useQuestionBank(debouncedQuery)
  const { mutate: deleteQuestion } = useDeleteBankQuestion()

  const handleSearch = (value: string) => {
    setQuery(value)
    // Simple debounce: update after a short delay
    if (searchTimerRef.current) clearTimeout(searchTimerRef.current)
    searchTimerRef.current = setTimeout(() => setDebouncedQuery(value), 400)
  }

  const handleDelete = (id: string) => {
    setDeletingId(id)
    deleteQuestion(id, { onSettled: () => setDeletingId(null) })
  }

  return (
    <div className="space-y-4">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder={t.questionPaper.bankSearchPlaceholder}
          value={query}
          onChange={(e) => handleSearch(e.target.value)}
          className="pl-9"
        />
      </div>

      {isLoading ? (
        <div className="flex justify-center py-8">
          <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
        </div>
      ) : questions.length === 0 ? (
        <p className="text-sm text-muted-foreground text-center py-8">
          {debouncedQuery ? t.questionPaper.bankNoResults : t.questionPaper.bankEmpty}
        </p>
      ) : (
        <div className="space-y-2">
          <p className="text-xs text-muted-foreground">
            {questions.length} {t.questionPaper.bankQuestionCount}
          </p>
          {questions.map((q) => (
            <div
              key={q.id}
              className="flex items-start gap-3 rounded-md border p-3 group"
            >
              <div className="flex-1 min-w-0">
                <p className="text-sm">{q.question}</p>
                <div className="flex items-center gap-2 mt-1">
                  <Badge variant="outline" className="text-xs capitalize">
                    {q.type}
                  </Badge>
                  <Badge
                    variant={
                      q.difficulty === 'easy'
                        ? 'secondary'
                        : q.difficulty === 'hard'
                          ? 'destructive'
                          : 'default'
                    }
                    className="text-xs capitalize"
                  >
                    {q.difficulty}
                  </Badge>
                  <span className="text-xs text-muted-foreground truncate">{q.topic}</span>
                </div>
                <p className="text-xs text-muted-foreground mt-1 line-clamp-1">
                  <span className="font-medium">{t.questionPaper.answer}:</span> {q.answer}
                </p>
              </div>
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity"
                onClick={() => handleDelete(q.id)}
                disabled={deletingId === q.id}
              >
                {deletingId === q.id ? (
                  <Loader2 className="h-3 w-3 animate-spin" />
                ) : (
                  <Trash2 className="h-3 w-3" />
                )}
              </Button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
