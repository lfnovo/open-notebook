'use client'

import { useQuery } from '@tanstack/react-query'
import { notebooksApi } from '@/lib/api/notebooks'
import { QUERY_KEYS } from '@/lib/api/query-client'
import type { NotebookResponse } from '@/lib/types/api'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { EmptyState } from '@/components/common/EmptyState'
import { BookOpen, FileText, Globe } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { useTranslation } from '@/lib/hooks/use-translation'
import { getDateLocale } from '@/lib/utils/date-locale'

export function PublicNotebooks({
  searchQuery,
}: {
  searchQuery?: string
}) {
  const { t, language } = useTranslation()
  const { data: notebooks, isLoading } = useQuery({
    queryKey: QUERY_KEYS.publicNotebooks,
    queryFn: () => notebooksApi.listPublic({ order_by: 'updated desc' }),
  })

  const normalizedQuery = searchQuery?.trim().toLowerCase()
  const filtered = normalizedQuery && notebooks
    ? notebooks.filter((n) =>
        `${n.name} ${n.description || ''}`.toLowerCase().includes(normalizedQuery)
      )
    : notebooks

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  if (!filtered || filtered.length === 0) {
    return (
      <EmptyState
        icon={Globe}
        title={normalizedQuery ? t.common.noMatches : t.public.noPublicNotebooks}
        description={normalizedQuery ? t.common.tryDifferentSearch : t.public.noPublicNotebooksDesc}
      />
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <h2 className="text-lg font-semibold">{t.public.notebooks}</h2>
        <span className="text-sm text-muted-foreground">({filtered.length})</span>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filtered.map((notebook) => (
          <PublicNotebookCard key={notebook.id} notebook={notebook} language={language} />
        ))}
      </div>
    </div>
  )
}

function PublicNotebookCard({
  notebook,
  language,
}: {
  notebook: NotebookResponse
  language: string
}) {
  const { t } = useTranslation()

  return (
    <Card
      className="group card-hover cursor-pointer transition-all duration-200 hover:shadow-md"
      onClick={() => window.location.href = `/notebooks/${encodeURIComponent(notebook.id)}`}
    >
      <CardContent className="px-3 py-3">
        <div className="flex items-start gap-3">
          <div className="rounded-lg bg-primary/10 p-2 text-primary">
            <BookOpen className="h-4 w-4" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 mb-1">
              <h3 className="font-medium truncate group-hover:text-primary transition-colors">
                {notebook.name}
              </h3>
            </div>
            {notebook.description && (
              <p className="text-sm text-muted-foreground line-clamp-2 mb-3">
                {notebook.description}
              </p>
            )}
            <div className="flex items-center gap-2 flex-wrap text-xs text-muted-foreground">
              <Badge variant="outline" className="text-xs flex items-center gap-1">
                <FileText className="h-3 w-3" />
                {notebook.source_count} {t.public.sources}
              </Badge>
              <span>
                {formatDistanceToNow(new Date(notebook.updated), {
                  addSuffix: true,
                  locale: getDateLocale(language),
                })}
              </span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
