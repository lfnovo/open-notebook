'use client'

import { useQuery } from '@tanstack/react-query'
import { sourcesApi } from '@/lib/api/sources'
import { QUERY_KEYS } from '@/lib/api/query-client'
import { SourceListResponse } from '@/lib/types/api'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { EmptyState } from '@/components/common/EmptyState'
import { Eye, FileText, Globe, ExternalLink, Link2, Upload, User } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { useTranslation } from '@/lib/hooks/use-translation'
import { getDateLocale } from '@/lib/utils/date-locale'

interface PublicSourcesProps {
  searchQuery?: string
  rankingMode?: 'most_visited' | 'most_referenced'
}

export function PublicSources({ searchQuery, rankingMode = 'most_visited' }: PublicSourcesProps) {
  const { t } = useTranslation()
  const sortBy = rankingMode === 'most_referenced' ? 'reference_count' : 'view_count'
  const rankingLabel = rankingMode === 'most_referenced'
    ? t.public?.mostReferenced || '引用最多'
    : t.public?.mostVisited || '最热访问'

  const { data: sources, isLoading } = useQuery({
    queryKey: [...QUERY_KEYS.publicSources, rankingMode],
    queryFn: () => sourcesApi.listPublic({
      sort_by: sortBy,
      sort_order: 'desc',
      limit: 20,
      offset: 0,
    }),
  })

  const normalizedQuery = searchQuery?.trim().toLowerCase()
  const filtered = normalizedQuery && sources
    ? sources.filter(s =>
        `${s.title || ''} ${(s.topics || []).join(' ')}`.toLowerCase().includes(normalizedQuery)
      )
    : sources

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
        title={normalizedQuery ? t.common.noMatches : t.public.noPublicSources}
        description={normalizedQuery ? t.common.tryDifferentSearch : t.public.noPublicSourcesDesc}
      />
    )
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-base font-semibold text-stone-950">{t.public.sources}</h2>
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
        {filtered.map((source) => (
          <PublicSourceCard key={source.id} source={source} />
        ))}
      </div>
    </div>
  )
}

function PublicSourceCard({ source }: { source: SourceListResponse }) {
  const { t, language } = useTranslation()

  const title = source.title || t.sources.untitledSource

  // Determine source type
  const isLink = !!source.asset?.url
  const isUpload = !!source.asset?.file_path
  const SourceIcon = isLink ? ExternalLink : isUpload ? Upload : FileText
  const creatorLabel = source.creator_username

  return (
    <Card
      className="group cursor-pointer rounded-lg border-stone-200/80 bg-white transition-all duration-200 hover:border-primary/30 hover:shadow-sm"
      onClick={() => window.location.href = `/sources/${encodeURIComponent(source.id)}`}
    >
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            {/* Source type + time */}
            <div className="mb-2 flex items-center gap-2">
              <Badge variant="secondary" className="flex items-center gap-1 rounded-md text-xs">
                <SourceIcon className="h-3 w-3" />
                {isLink ? t.sources.addUrl : isUpload ? t.sources.uploadFile : t.sources.enterText}
              </Badge>
              <span className="text-xs text-muted-foreground">
                {formatDistanceToNow(new Date(source.updated), {
                  addSuffix: true,
                  locale: getDateLocale(language),
                })}
              </span>
            </div>

            {/* Title */}
            <h4
              className="mb-3 line-clamp-2 break-all text-sm font-semibold leading-5 text-stone-950 group-hover:text-primary"
              title={title}
            >
              {title}
            </h4>

            {creatorLabel && (
              <div className="mb-3 inline-flex max-w-full items-center gap-1.5 truncate text-xs text-stone-500">
                <User className="h-3 w-3 shrink-0" />
                <span className="truncate font-medium text-stone-700">
                  {t.notebooks?.createdBy || 'Created by'} {creatorLabel}
                </span>
              </div>
            )}

            {/* Metadata */}
            <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-stone-500">
              <span className="inline-flex items-center gap-1.5">
                <Eye className="h-3 w-3" />
                {source.view_count || 0} {t.public?.views || '访问'}
              </span>
              <span className="inline-flex items-center gap-1.5">
                <Link2 className="h-3 w-3" />
                {source.reference_count || 0} {t.public?.references || '引用'}
              </span>
              {source.insights_count > 0 && (
                <span className="inline-flex items-center gap-1.5">
                  {source.insights_count} {t.sources.insights}
                </span>
              )}
              {source.topics && source.topics.length > 0 && (
                <>
                  {source.topics.slice(0, 2).map((topic, index) => (
                    <Badge key={index} variant="outline" className="rounded-md border-stone-200 bg-stone-50 text-xs">
                      {topic}
                    </Badge>
                  ))}
                  {source.topics.length > 2 && (
                    <Badge variant="outline" className="rounded-md border-stone-200 bg-stone-50 text-xs">
                      +{source.topics.length - 2}
                    </Badge>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
