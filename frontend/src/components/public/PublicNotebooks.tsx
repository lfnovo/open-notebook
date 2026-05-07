'use client'

import { useQuery } from '@tanstack/react-query'
import { notebooksApi } from '@/lib/api/notebooks'
import { QUERY_KEYS } from '@/lib/api/query-client'
import type { NotebookResponse } from '@/lib/types/api'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { EmptyState } from '@/components/common/EmptyState'
import { BookOpen, Eye, FileText, Globe, Link2, User } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { useTranslation } from '@/lib/hooks/use-translation'
import { getDateLocale } from '@/lib/utils/date-locale'

export function PublicNotebooks({
  searchQuery,
  rankingMode = 'most_visited',
}: {
  searchQuery?: string
  rankingMode?: 'most_visited' | 'most_referenced'
}) {
  const { t, language } = useTranslation()
  const orderBy = rankingMode === 'most_referenced' ? 'reference_count desc' : 'view_count desc'
  const rankingLabel = rankingMode === 'most_referenced'
    ? t.public?.mostReferenced || '引用最多'
    : t.public?.mostVisited || '最热访问'
  const { data: notebooks, isLoading } = useQuery({
    queryKey: [...QUERY_KEYS.publicNotebooks, rankingMode],
    queryFn: () => notebooksApi.listPublic({
      order_by: orderBy,
      limit: 20,
      offset: 0,
    }),
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
    <div className="space-y-3">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-base font-semibold text-stone-950">{t.public.notebooks}</h2>
            <Badge variant="secondary" className="rounded-md text-xs">
              {rankingLabel}
            </Badge>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            {t.public?.discoverLimitHint || '仅展示前 20 条，更多请使用搜索。'}
          </p>
        </div>
        <span className="text-xs font-medium text-muted-foreground">
          {filtered.length} / 20
        </span>
      </div>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
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
  const creatorLabel = notebook.creator_username || notebook.creator_name

  return (
    <Card
      className="group cursor-pointer rounded-lg border-stone-200/80 bg-white transition-all duration-200 hover:border-primary/30 hover:shadow-sm"
      onClick={() => window.location.href = `/notebooks/${encodeURIComponent(notebook.id)}`}
    >
      <CardContent className="p-4">
        <div className="flex items-start gap-3">
          <div className="shrink-0 rounded-md bg-primary/10 p-2 text-primary">
            <BookOpen className="h-4 w-4" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 mb-1">
              <h3 className="truncate text-sm font-semibold leading-5 text-stone-950 group-hover:text-primary">
                {notebook.name}
              </h3>
            </div>
            {notebook.description && (
              <p className="mb-3 line-clamp-2 text-sm leading-5 text-muted-foreground">
                {notebook.description}
              </p>
            )}
            {creatorLabel && (
              <div className="mb-3 inline-flex max-w-full items-center gap-1.5 truncate text-xs text-stone-500">
                <User className="h-3 w-3 shrink-0" />
                <span className="truncate font-medium text-stone-700">
                  {t.notebooks?.createdBy || 'Created by'} {creatorLabel}
                </span>
              </div>
            )}
            <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-stone-500">
              <span className="inline-flex items-center gap-1.5">
                <FileText className="h-3 w-3" />
                {notebook.source_count} {t.public.sources}
              </span>
              <span className="inline-flex items-center gap-1.5">
                <Eye className="h-3 w-3" />
                {notebook.view_count || 0} {t.public?.views || '访问'}
              </span>
              <span className="inline-flex items-center gap-1.5">
                <Link2 className="h-3 w-3" />
                {notebook.reference_count || 0} {t.public?.references || '引用'}
              </span>
              <span className="ml-auto">
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
