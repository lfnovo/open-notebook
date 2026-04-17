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
  Unlink,
  GitBranch,
  Newspaper,
  Lightbulb,
  Network,
} from 'lucide-react'
import { useSourceStatus } from '@/lib/hooks/use-sources'
import { useTranslation } from '@/lib/hooks/use-translation'
import { TranslationKeys } from '@/lib/locales'
import { cn } from '@/lib/utils'
import { ContextToggle } from '@/components/common/ContextToggle'
import { ContextMode } from '@/app/(dashboard)/notebooks/[id]/page'
import { MindMapDialog } from '@/components/source/MindMapDialog'
import { InfographicDialog } from '@/components/source/InfographicDialog'
import { Checkbox } from '@/components/ui/checkbox'
import { ProfileGraphModal } from '@/components/sources/ProfileGraphModal'

interface SourceCardProps {
  source: SourceListResponse
  onDelete?: (sourceId: string) => void
  onRetry?: (sourceId: string) => void
  onRemoveFromNotebook?: (sourceId: string) => void
  onClick?: (sourceId: string) => void
  onRefresh?: () => void
  className?: string
  showRemoveFromNotebook?: boolean
  contextMode?: ContextMode
  onContextModeChange?: (mode: ContextMode) => void
  selectable?: boolean
  selected?: boolean
  onSelectChange?: (selected: boolean) => void
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
  onRemoveFromNotebook,
  onRefresh,
  className,
  showRemoveFromNotebook = false,
  contextMode,
  onContextModeChange,
  selectable = false,
  selected = false,
  onSelectChange,
}: SourceCardProps) {
  const { t } = useTranslation()
  const statusConfigMap = getStatusConfig(t)
  
  // Only fetch status for sources that might have async processing
  const sourceWithStatus = source as SourceListResponse & { command_id?: string; status?: string }

  // Track processing state to continue polling until we detect completion
  const [wasProcessing, setWasProcessing] = useState(false)
  const [mindMapOpen, setMindMapOpen] = useState(false)
  const [infographicOpen, setInfographicOpen] = useState(false)
  const [profileGraphOpen, setProfileGraphOpen] = useState(false)
  // Once we've seen a terminal status, stop polling entirely
  const [terminalStatus, setTerminalStatus] = useState<string | null>(
    sourceWithStatus.status === 'completed' || sourceWithStatus.status === 'failed'
      ? sourceWithStatus.status
      : null
  )

  const isActiveStatus = (s?: string | null) =>
    s === 'new' || s === 'queued' || s === 'running'

  // Only poll if: actively processing OR we were processing (to catch completion).
  // Never poll if we already know the terminal status.
  const shouldFetchStatus = !terminalStatus && (
    isActiveStatus(sourceWithStatus.status) ||
    wasProcessing
  )

  const { data: statusData, isLoading: statusLoading } = useSourceStatus(
    source.id,
    shouldFetchStatus
  )

  // Determine current status
  // If source has a command_id but no status, treat as "new" (just created)
  const rawStatus = statusData?.status || sourceWithStatus.status
  const currentStatus: SourceStatus = isSourceStatus(rawStatus)
    ? rawStatus
    : (sourceWithStatus.command_id ? 'new' : 'completed')


  // Track processing state and detect completion
  useEffect(() => {
    const currentStatusFromData = statusData?.status || sourceWithStatus.status

    // If we're currently processing, mark that we were processing
    if (isActiveStatus(currentStatusFromData)) {
      setWasProcessing(true)
    }

    // If we were processing and now completed/failed, trigger refresh and stop polling
    if (wasProcessing &&
        (currentStatusFromData === 'completed' || currentStatusFromData === 'failed')) {
      setWasProcessing(false)
      setTerminalStatus(currentStatusFromData) // stop all future polling

      if (onRefresh) {
        setTimeout(() => onRefresh(), 500)
      }
    }

    // If status came back terminal from the very first fetch, lock it in
    if (!wasProcessing &&
        (currentStatusFromData === 'completed' || currentStatusFromData === 'failed') &&
        !terminalStatus) {
      setTerminalStatus(currentStatusFromData)
    }
  }, [statusData, sourceWithStatus.status, wasProcessing, terminalStatus, onRefresh, source.id])
  
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

  const handleRemoveFromNotebook = () => {
    if (onRemoveFromNotebook) {
      onRemoveFromNotebook(source.id)
    }
  }

  const handleCardClick = () => {
    if (onClick) {
      onClick(source.id)
    }
  }

  const handleSelectionChange = (checked: boolean) => {
    if (onSelectChange) {
      onSelectChange(checked)
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
      onClick={(e) => {
        // Don't open source detail if a dialog is already open
        if (mindMapOpen || infographicOpen || profileGraphOpen) return
        handleCardClick()
      }}
    >
      <CardContent className="px-4 py-3 min-h-[80px]">
        {/* Header with status indicator */}
        <div className="flex items-start justify-between gap-3 mb-1">
          <div className="flex items-start gap-3 min-w-0">
            {selectable && (
              <Checkbox
                checked={!!selected}
                onCheckedChange={(value) => handleSelectionChange(value === true)}
                aria-label={`Select source ${title}`}
                onClick={(e) => e.stopPropagation()}
              />
            )}
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
                className="text-sm font-medium leading-tight line-clamp-2 break-all"
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

            {/* Metadata badges */}
            <div className="flex items-center gap-2 flex-wrap">
              {/* Source type badge */}
              <Badge variant="secondary" className="text-xs flex items-center gap-1">
                <SourceTypeIcon className="h-3 w-3" />
                {sourceType === 'link' ? t.sources.addUrl : sourceType === 'upload' ? t.sources.uploadFile : t.sources.enterText}
              </Badge>

              {isCompleted && (
                <Badge
                  variant={source.insights_count > 0 ? 'default' : 'outline'}
                  className="text-xs flex items-center gap-1"
                  title={`${source.insights_count} insight${source.insights_count !== 1 ? 's' : ''}`}
                >
                  <Lightbulb className="h-3 w-3 shrink-0" />
                  <span>{source.insights_count} {source.insights_count === 1 ? 'Insight' : 'Insights'}</span>
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

            {/* Mind Map button */}
            <Button
              variant="ghost"
              size="sm"
              className="h-8 w-8 p-0 text-muted-foreground hover:text-pink-600 hover:bg-pink-50 transition-colors"
              title="Generate Mind Map"
              onClick={(e) => {
                e.stopPropagation()
                setMindMapOpen(true)
              }}
            >
              <GitBranch className="h-4 w-4" />
            </Button>

            {/* Infographic button */}
            <Button
              variant="ghost"
              size="sm"
              className="h-8 w-8 p-0 text-muted-foreground hover:text-purple-600 hover:bg-purple-50 transition-colors"
              title="Generate Infographic"
              onClick={(e) => {
                e.stopPropagation()
                setInfographicOpen(true)
              }}
            >
              <Newspaper className="h-4 w-4" />
            </Button>

            {/* Profile Graph button */}
            <Button
              variant="ghost"
              size="sm"
              className="h-8 w-8 p-0 text-muted-foreground hover:text-blue-600 hover:bg-blue-50 transition-colors"
              title="Profile Graph — Personal, Family & Associates"
              onClick={(e) => {
                e.stopPropagation()
                setProfileGraphOpen(true)
              }}
            >
              <Network className="h-4 w-4" />
            </Button>

            {/* Actions dropdown */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-8 w-8 p-0 text-muted-foreground hover:text-foreground transition-colors"
                  onClick={(e) => e.stopPropagation()}
                >
                  <MoreVertical className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-48">
              {showRemoveFromNotebook && (
                <>
                  <DropdownMenuItem
                    onClick={(e) => {
                      e.stopPropagation()
                      handleRemoveFromNotebook()
                    }}
                    disabled={!onRemoveFromNotebook}
                  >
                    <Unlink className="h-4 w-4 mr-2" />
                    {t.sources.removeFromNotebook}
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

      {/* Mind Map Dialog — rendered outside CardContent to avoid click propagation issues */}
      <div onClick={(e) => e.stopPropagation()}>
        <MindMapDialog
          open={mindMapOpen}
          onOpenChange={setMindMapOpen}
          sourceId={source.id}
          sourceTitle={source.title}
        />

        {/* Infographic Dialog */}
        <InfographicDialog
          open={infographicOpen}
          onOpenChange={setInfographicOpen}
          sourceId={source.id}
          sourceTitle={source.title}
        />

        {/* Profile Graph Dialog */}
        <ProfileGraphModal
          open={profileGraphOpen}
          onOpenChange={setProfileGraphOpen}
          sourceId={source.id}
          sourceTitle={source.title || undefined}
          sourceImageUrl={source.asset?.url || undefined}
        />
      </div>
    </Card>
  )
}