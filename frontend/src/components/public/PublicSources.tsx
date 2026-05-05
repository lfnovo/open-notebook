'use client'

import { useQuery } from '@tanstack/react-query'
import { sourcesApi } from '@/lib/api/sources'
import { QUERY_KEYS } from '@/lib/api/query-client'
import { SourceListResponse } from '@/lib/types/api'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { EmptyState } from '@/components/common/EmptyState'
import { FileText, Globe, ExternalLink, Upload } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { useTranslation } from '@/lib/hooks/use-translation'
import { getDateLocale } from '@/lib/utils/date-locale'

interface PublicSourcesProps {
  searchQuery?: string
}

export function PublicSources({ searchQuery }: PublicSourcesProps) {
  const { t } = useTranslation()

  const { data: sources, isLoading } = useQuery({
    queryKey: QUERY_KEYS.publicSources,
    queryFn: () => sourcesApi.listPublic({ order_by: 'updated desc' }),
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
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <h2 className="text-lg font-semibold">{t.public.sources}</h2>
        <span className="text-sm text-muted-foreground">({filtered.length})</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
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

  return (
    <Card
      className="group card-hover cursor-pointer transition-all duration-200 hover:shadow-md"
      onClick={() => window.location.href = `/sources/${encodeURIComponent(source.id)}`}
    >
      <CardContent className="px-3 py-3">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            {/* Source type + time */}
            <div className="flex items-center gap-2 mb-2">
              <Badge variant="secondary" className="text-xs flex items-center gap-1">
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
              className="text-sm font-medium leading-tight line-clamp-2 break-all mb-2 group-hover:text-primary transition-colors"
              title={title}
            >
              {title}
            </h4>

            {/* Metadata */}
            <div className="flex items-center gap-2 flex-wrap">
              {source.insights_count > 0 && (
                <Badge variant="outline" className="text-xs">
                  {source.insights_count} {t.sources.insights}
                </Badge>
              )}
              {source.topics && source.topics.length > 0 && (
                <>
                  {source.topics.slice(0, 2).map((topic, index) => (
                    <Badge key={index} variant="outline" className="text-xs">
                      {topic}
                    </Badge>
                  ))}
                  {source.topics.length > 2 && (
                    <Badge variant="outline" className="text-xs">
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
