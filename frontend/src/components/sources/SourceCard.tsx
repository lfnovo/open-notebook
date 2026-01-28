'use client'

import React, { useState, useEffect } from 'react'
import { SourceListResponse } from '@/lib/types/api'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator
} from '@/components/ui/dropdown-menu'
import {
  FileText,
  ExternalLink,
  Upload,
  MoreVertical,
  Trash2,
  RefreshCw,
  Clock,
  CheckCircle,
  AlertTriangle,
  Loader2,
  Unlink
} from 'lucide-react'
import { useSourceStatus } from '@/lib/hooks/use-sources'
import { useTranslation } from '@/lib/hooks/use-translation'
import { TranslationKeys } from '@/lib/locales'
import { cn } from '@/lib/utils'
import { ContextToggle } from '@/components/common/ContextToggle'
import { ContextMode } from '@/app/(dashboard)/modules/[id]/page'
import { useQueryClient } from '@tanstack/react-query'
import { QUERY_KEYS } from '@/lib/api/query-client'

interface SourceCardProps {
  source: SourceListResponse
  onDelete?: (sourceId: string) => void
  onRetry?: (sourceId: string) => void
  onRemoveFromModule?: (sourceId: string) => void
  onClick?: (sourceId: string) => void
  onRefresh?: () => void
  className?: string
  showRemoveFromModule?: boolean
  contextMode?: ContextMode
  onContextModeChange?: (mode: ContextMode) => void
}

const SOURCE_TYPE_ICONS = {
  link: ExternalLink,
  upload: Upload,
  text: FileText,
} as const

const getStatusConfig = (t: TranslationKeys) => ({
  new: {
    icon: Clock,
    color: 'text-blue-600',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200',
    label: t.sources.statusProcessing,
    description: t.sources.statusPreparingDesc
  },
  queued: {
    icon: Clock,
    color: 'text-blue-600',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200',
    label: t.sources.statusQueued,
    description: t.sources.statusQueuedDesc
  },
  running: {
    icon: Loader2,
    color: 'text-blue-600',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200',
    label: t.sources.statusProcessing,
    description: t.sources.statusProcessingDesc
  },
  completed: {
    icon: CheckCircle,
    color: 'text-green-600',
    bgColor: 'bg-green-50',
    borderColor: 'border-green-200',
    label: t.sources.statusCompleted,
    description: t.sources.statusCompletedDesc
  },
  failed: {
    icon: AlertTriangle,
    color: 'text-red-600',
    bgColor: 'bg-red-50',
    borderColor: 'border-red-200',
    label: t.sources.statusFailed,
    description: t.sources.statusFailedDesc
  }
} as const)

type SourceStatus = 'new' | 'queued' | 'running' | 'completed' | 'failed'

function isSourceStatus(status: unknown): status is SourceStatus {
  return typeof status === 'string' && ['new', 'queued', 'running', 'completed', 'failed'].includes(status)
}

function getSourceType(source: SourceListResponse): 'link' | 'upload' | 'text' {
  // Determine type based on asset information
  if (source.asset?.url) return 'link'
  if (source.asset?.file_path) return 'upload'
  return 'text'
}

export function SourceCard({
  source,
  onClick,
  onDelete,
  onRetry,
  onRemoveFromModule,
  onRefresh,
  className,
  showRemoveFromModule = false,
  contextMode,
  onContextModeChange
}: SourceCardProps) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const statusConfigMap = getStatusConfig(t)
  
  // Only fetch status for sources that might have async processing
  const sourceWithStatus = source as SourceListResponse & { command_id?: string; status?: string }

  // Track processing state to continue polling until we detect completion
  const [wasProcessing, setWasProcessing] = useState(false)

  // Always fetch status if:
  // 1. Source has a command_id (might be processing)
  // 2. Source status indicates processing (from list)
  // 3. We were previously processing (to catch completion)
  // 4. Status is unknown/null but command_id exists (need to check actual status)
  const shouldFetchStatus = !!sourceWithStatus.command_id ||
    sourceWithStatus.status === 'new' ||
    sourceWithStatus.status === 'queued' ||
    sourceWithStatus.status === 'running' ||
    wasProcessing || // Keep polling if we were processing to catch the completion
    (sourceWithStatus.command_id && !sourceWithStatus.status) // Command exists but no status - need to check

  const { data: statusData, isLoading: statusLoading } = useSourceStatus(
    source.id,
    shouldFetchStatus
  )

  // Determine current status
  // Priority: statusData (from status API) > source.status (from list) > inferred from command_id/embedded state
  // If status API returns null/undefined but we have statusData.message, check if it's a legacy source
  let rawStatus: string | undefined = undefined
  
  if (statusData?.status) {
    // Status API returned a status - use it (most reliable)
    rawStatus = statusData.status
  } else if (statusData?.message && statusData.message.includes('Legacy source')) {
    // Status API explicitly says it's a legacy source (completed)
    rawStatus = 'completed'
  } else if (statusData && !statusData.status && source.embedded_chunks > 0) {
    // Status API returned but status is null/undefined, but source has embeddings - likely completed
    rawStatus = 'completed'
  } else if (sourceWithStatus.status) {
    // Fall back to status from source list
    rawStatus = sourceWithStatus.status
  } else if (sourceWithStatus.command_id && !statusData) {
    // Has command_id but status API hasn't responded yet - likely just created, treat as 'new'
    rawStatus = 'new'
  } else if (source.embedded_chunks > 0 || source.embedded) {
    // Source has embeddings - definitely completed
    rawStatus = 'completed'
  } else if (sourceWithStatus.command_id) {
    // Has command_id but no embeddings - might be processing
    rawStatus = 'new'
  } else {
    // No command_id and no status - assume completed (legacy source)
    rawStatus = 'completed'
  }

  const currentStatus: SourceStatus = isSourceStatus(rawStatus)
    ? rawStatus
    : 'completed'

  // Track processing state and detect completion
  useEffect(() => {
    const currentStatusFromData = statusData?.status || sourceWithStatus.status || rawStatus

    // If we're currently processing, mark that we were processing
    if (currentStatusFromData === 'new' || currentStatusFromData === 'running' || currentStatusFromData === 'queued') {
      setWasProcessing(true)
    }

    // If we were processing and now completed/failed, trigger refresh and stop polling
    if (wasProcessing &&
        (currentStatusFromData === 'completed' || currentStatusFromData === 'failed')) {
      setWasProcessing(false) // Stop polling

      // Invalidate sources queries to refresh the list with updated status
      queryClient.invalidateQueries({ queryKey: ['sources'] })
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.sources() })
      
      if (onRefresh) {
        // Also call the manual refresh callback if provided
        setTimeout(() => {
          onRefresh()
        }, 500) // Small delay to ensure API is updated
      }
    }
  }, [statusData, sourceWithStatus.status, wasProcessing, onRefresh, source.id, rawStatus, queryClient])
  
  const statusConfig = statusConfigMap[currentStatus] || statusConfigMap.completed
  const StatusIcon = statusConfig.icon
  const sourceType = getSourceType(source)
  const SourceTypeIcon = SOURCE_TYPE_ICONS[sourceType]
  
   const title = source.title || t.sources.untitledSource

  const handleRetry = () => {
    if (onRetry) {
      onRetry(source.id)
    }
  }

  const handleDelete = () => {
    if (onDelete) {
      onDelete(source.id)
    }
  }

  const handleRemoveFromModule = () => {
    if (onRemoveFromModule) {
      onRemoveFromModule(source.id)
    }
  }

  const handleCardClick = () => {
    if (onClick) {
      onClick(source.id)
    }
  }

  const isProcessing: boolean = currentStatus === 'new' || currentStatus === 'running' || currentStatus === 'queued'
  const isFailed: boolean = currentStatus === 'failed'
  const isCompleted: boolean = currentStatus === 'completed'

  return (
    <Card
      className={cn(
        'transition-all duration-200 hover:shadow-md group relative cursor-pointer border border-border/60 dark:border-border/40',
        className
      )}
      onClick={handleCardClick}
    >
      <CardContent className="px-3 py-1">
        {/* Header with status indicator */}
        <div className="flex items-start justify-between gap-3 mb-1">
          <div className="flex-1 min-w-0">
            {/* Status badge - only show if not completed */}
            {!isCompleted && (
              <div className="flex items-center gap-2 mb-2">
                <div className={cn(
                  'flex items-center gap-1.5 px-2 py-1 rounded-md text-xs font-medium',
                  statusConfig.bgColor,
                  statusConfig.color
                )}>
                  <StatusIcon className={cn(
                    'h-3 w-3',
                    isProcessing && 'animate-spin'
                  )} />
                  {statusLoading && shouldFetchStatus ? t.sources.checking : statusConfig.label}
                </div>

                {/* Source type indicator */}
                <div className="flex items-center gap-1 text-gray-500">
                  <SourceTypeIcon className="h-3 w-3" />
                  <span className="text-xs capitalize">{t.common.source}</span>
                </div>
              </div>
            )}

            {/* Title */}
            <div className={cn('mb-1.5', !isCompleted && 'mb-1')}>
              <h4
                className="text-sm font-medium leading-tight line-clamp-2"
                title={title}
              >
                {title}
              </h4>
            </div>

            {/* Processing message for active statuses */}
            {statusData?.message && (isProcessing || isFailed) && (
              <p className="text-xs text-gray-600 mb-2 italic">
                {statusData.message}
              </p>
            )}
            
            {/* Debug info - show actual status being used (can be removed in production) */}
            {process.env.NODE_ENV === 'development' && (
              <p className="text-xs text-gray-400 mt-1">
                Status: {currentStatus} | API: {statusData?.status || 'none'} | Source: {sourceWithStatus.status || 'none'} | Command: {sourceWithStatus.command_id || 'none'}
              </p>
            )}

            {/* Metadata badges */}
            <div className="flex items-center gap-2 flex-wrap">
              {/* Source type badge */}
              <Badge variant="secondary" className="text-xs flex items-center gap-1">
                <SourceTypeIcon className="h-3 w-3" />
                {sourceType === 'link' ? t.sources.addUrl : sourceType === 'upload' ? t.sources.uploadFile : t.sources.enterText}
              </Badge>

              {isCompleted && source.insights_count > 0 && (
                <Badge variant="outline" className="text-xs">
                  {t.sources.insightsCount.replace('{count}', source.insights_count.toString())}
                </Badge>
              )}
              {source.topics && source.topics.length > 0 && isCompleted && (
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

          {/* Context toggle and actions */}
          <div className="flex items-center gap-1">
            {/* Context toggle - only show if handler provided */}
            {onContextModeChange && contextMode && (
              <ContextToggle
                mode={contextMode}
                hasInsights={source.insights_count > 0}
                onChange={onContextModeChange}
              />
            )}

            {/* Actions dropdown */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-8 w-8 p-0 opacity-0 group-hover:opacity-100 transition-opacity"
                  onClick={(e) => e.stopPropagation()}
                >
                  <MoreVertical className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-48">
              {showRemoveFromModule && (
                <>
                  <DropdownMenuItem
                    onClick={(e) => {
                      e.stopPropagation()
                      handleRemoveFromModule()
                    }}
                    disabled={!onRemoveFromModule}
                  >
                    <Unlink className="h-4 w-4 mr-2" />
                    {t.sources.removeFromModule}
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                </>
              )}

              {isFailed && (
                <>
                  <DropdownMenuItem
                    onClick={(e) => {
                      e.stopPropagation()
                      handleRetry()
                    }}
                    disabled={!onRetry}
                  >
                    <RefreshCw className="h-4 w-4 mr-2" />
                    {t.sources.retryProcessing}
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                </>
              )}

              <DropdownMenuItem
                onClick={(e) => {
                  e.stopPropagation()
                  handleDelete()
                }}
                disabled={!onDelete}
                className="text-red-600 focus:text-red-600"
              >
                <Trash2 className="h-4 w-4 mr-2" />
                {t.sources.deleteSource}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
          </div>
        </div>
        {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
        {(isFailed as any) && (
          <div className="flex gap-2 pt-2 border-t">
            <Button
              variant="outline"
              size="sm"
              onClick={handleRetry}
              disabled={!onRetry}
              className="h-7 text-xs"
            >
              <RefreshCw className="h-3 w-3 mr-1" />
              {t.sources.retry}
            </Button>
          </div>
        )}

        {/* Processing progress indicator */}
        {isProcessing && statusData?.processing_info?.progress && (
          <div className="mt-3 pt-2 border-t">
            <div className="flex justify-between items-center mb-1">
            <span className="text-xs text-gray-600">{t.common.progress}</span>
              <span className="text-xs text-gray-600">
                {Math.round(statusData.processing_info.progress as number)}%
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-1.5">
              <div
                className="bg-blue-600 h-1.5 rounded-full transition-all duration-300"
                style={{ width: `${statusData.processing_info.progress as number}%` }}
              />
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}