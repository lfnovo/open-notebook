'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { useTranslation } from '@/lib/hooks/use-translation'
import { useCurrentWorkspace } from '@/lib/hooks/use-workspaces'
import { QUERY_KEYS } from '@/lib/api/query-client'
import {
  useAvailableExternalSources,
  useExternalApiCommand,
  useFetchExternalItem,
  useSearchExternalSource,
  useSnapshotExternalItem,
} from '@/lib/hooks/use-external-api'
import type { ExternalSourceItem } from '@/lib/api/external-api'
import { ExternalLink, Loader2, Plus, Search } from 'lucide-react'

interface ExternalSourcesPanelProps {
  notebookId: string
  canCreateSource: boolean
  onSnapshot?: () => void
}

const TERMINAL_COMMAND_STATUSES = new Set(['completed', 'failed', 'timeout', 'cancelled'])
const WAITING_COMMAND_STATUSES = new Set(['new', 'queued', 'running', 'submitted'])

export function ExternalSourcesPanel({
  notebookId,
  canCreateSource,
  onSnapshot,
}: ExternalSourcesPanelProps) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const { currentWorkspace } = useCurrentWorkspace()
  const teamId = currentWorkspace?.type === 'team' ? currentWorkspace.team_id : null
  const availableSources = useAvailableExternalSources(teamId)
  const searchExternal = useSearchExternalSource()
  const fetchItem = useFetchExternalItem()
  const snapshotItem = useSnapshotExternalItem()

  const [selectedSourceId, setSelectedSourceId] = useState('')
  const [query, setQuery] = useState('')
  const [searchCommandId, setSearchCommandId] = useState<string | null>(null)
  const [fetchCommandId, setFetchCommandId] = useState<string | null>(null)
  const [joiningItem, setJoiningItem] = useState<ExternalSourceItem | null>(null)
  const [joinErrorMessage, setJoinErrorMessage] = useState<string | null>(null)
  const snapshottingItemId = useRef<string | null>(null)

  const searchCommand = useExternalApiCommand(searchCommandId)
  const fetchCommand = useExternalApiCommand(fetchCommandId)
  const sources = useMemo(() => availableSources.data?.items ?? [], [availableSources.data?.items])
  const isLoadingAvailableSources = Boolean(
    teamId && !availableSources.data && (availableSources.isLoading || availableSources.isFetching)
  )

  useEffect(() => {
    if (!selectedSourceId && sources.length > 0) {
      setSelectedSourceId(sources[0].id)
    }
  }, [selectedSourceId, sources])

  useEffect(() => {
    const statuses = [searchCommand.data?.status, fetchCommand.data?.status]
    if (teamId && statuses.some((status) => status && TERMINAL_COMMAND_STATUSES.has(status))) {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.externalApiAvailableSources(teamId) })
    }
  }, [fetchCommand.data?.status, queryClient, searchCommand.data?.status, teamId])

  useEffect(() => {
    if (!joiningItem || fetchCommand.data?.status !== 'completed') {
      return
    }
    if (snapshottingItemId.current === joiningItem.id) {
      return
    }
    snapshottingItemId.current = joiningItem.id

    const snapshotFetchedItem = async () => {
      try {
        const fetchedItems = fetchCommand.data?.result?.items
        const fetchedItem = Array.isArray(fetchedItems) ? (fetchedItems[0] as ExternalSourceItem | undefined) : undefined
        await snapshotItem.mutateAsync({
          itemId: fetchedItem?.id || joiningItem.id,
          notebookId,
        })
        onSnapshot?.()
      } catch (error) {
        setJoinErrorMessage(error instanceof Error ? error.message : t.externalApi.joinFailed)
      } finally {
        snapshottingItemId.current = null
        setJoiningItem(null)
        setFetchCommandId(null)
      }
    }

    void snapshotFetchedItem()
  }, [fetchCommand.data?.result?.items, fetchCommand.data?.status, joiningItem, notebookId, onSnapshot, snapshotItem, t.externalApi.joinFailed])

  const selectedSource = sources.find((source) => source.id === selectedSourceId)
  const commandStatus = searchCommand.data?.status
  const isWaitingForSearchResult = Boolean(
    searchExternal.isPending ||
      (searchCommandId && (!commandStatus || WAITING_COMMAND_STATUSES.has(commandStatus)))
  )
  const fetchCommandStatus = fetchCommand.data?.status
  const isJoining = Boolean(
    joiningItem &&
      (fetchItem.isPending ||
        snapshotItem.isPending ||
        !fetchCommandStatus ||
        WAITING_COMMAND_STATUSES.has(fetchCommandStatus))
  )
  const hasCompletedSearch = commandStatus === 'completed'
  const searchItems = useMemo(() => {
    const items = searchCommand.data?.result?.items
    return hasCompletedSearch && Array.isArray(items) ? (items as ExternalSourceItem[]) : []
  }, [hasCompletedSearch, searchCommand.data?.result?.items])
  const usageText = selectedSource
    ? `${selectedSource.current_month_usage}/${selectedSource.monthly_request_quota}`
    : ''

  const canSearch = Boolean(teamId && selectedSourceId && query.trim())

  const handleSearch = async () => {
    if (!teamId || !selectedSourceId || !query.trim()) return
    setJoinErrorMessage(null)
    const response = await searchExternal.mutateAsync({
      sourceId: selectedSourceId,
      data: {
        team_id: teamId,
        query: query.trim(),
        limit: 10,
        notebook_id: notebookId,
      },
    })
    setSearchCommandId(response.command_id)
  }

  const handleJoin = async (item: ExternalSourceItem) => {
    if (!teamId) return
    setJoinErrorMessage(null)
    setJoiningItem(item)
    try {
      if (item.content_markdown) {
        await snapshotItem.mutateAsync({ itemId: item.id, notebookId })
        setJoiningItem(null)
        setFetchCommandId(null)
        onSnapshot?.()
        return
      }
      const response = await fetchItem.mutateAsync({ itemId: item.id, teamId })
      setFetchCommandId(response.command_id)
    } catch (error) {
      setJoinErrorMessage(error instanceof Error ? error.message : t.externalApi.joinFailed)
      setJoiningItem(null)
      setFetchCommandId(null)
    }
  }

  const joinError = joinErrorMessage
    || fetchCommand.data?.result?.error_message
    || (fetchCommand.data?.status && !WAITING_COMMAND_STATUSES.has(fetchCommand.data.status) && fetchCommand.data.status !== 'completed'
      ? fetchCommand.data.error_message
      : null)

  useEffect(() => {
    if (joinError) {
      setJoiningItem(null)
    }
  }, [joinError])

  return (
    <div className="rounded-md border bg-background p-3">
      {!teamId ? (
        <p className="text-xs text-muted-foreground">{t.externalApi.switchToTeamWorkspace}</p>
      ) : isLoadingAvailableSources ? (
        <div className="flex justify-center py-3">
          <LoadingSpinner />
        </div>
      ) : sources.length === 0 ? (
        <p className="text-xs text-muted-foreground">{t.externalApi.noAuthorizedSources}</p>
      ) : (
        <div className="flex flex-col gap-3">
          <div
            data-testid="external-source-selector-row"
            className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between"
          >
            <div className="flex min-w-0 flex-1 flex-col gap-2 sm:flex-row sm:items-center">
              <Label className="shrink-0 text-xs">{t.common.source}</Label>
              <Select value={selectedSourceId} onValueChange={setSelectedSourceId}>
                <SelectTrigger className="h-9 min-w-0 sm:max-w-56">
                  <SelectValue placeholder={t.externalApi.selectSource} />
                </SelectTrigger>
                <SelectContent>
                  {sources.map((source) => (
                    <SelectItem key={source.id} value={source.id}>
                      {source.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex shrink-0 items-center gap-2">
              {selectedSource && (
                <p className="truncate text-xs text-muted-foreground">
                  {t.externalApi.quotaUsage.replace('{usage}', usageText)}
                </p>
              )}
              {availableSources.isFetching && <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />}
            </div>
          </div>

          <div className="flex gap-2">
            <Input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder={t.externalApi.searchPlaceholder}
              className="h-9"
            />
            <Button type="button" size="sm" onClick={handleSearch} disabled={!canSearch || searchExternal.isPending}>
              <Search className="h-4 w-4" />
              <span className="sr-only">{t.externalApi.searchAction}</span>
            </Button>
          </div>

          {isWaitingForSearchResult && (
            <div className="flex items-center gap-2 rounded-md border border-dashed px-3 py-2 text-xs text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              <span>{t.externalApi.waitingForResults}</span>
            </div>
          )}

          {searchCommand.isLoading && !isWaitingForSearchResult && (
            <div className="flex justify-center py-3">
              <LoadingSpinner />
            </div>
          )}

          {commandStatus && !hasCompletedSearch && !isWaitingForSearchResult && (
            <Badge variant="outline" className="w-fit">{commandStatus}</Badge>
          )}

          {searchCommand.data?.result?.error_message && (
            <p className="text-xs text-destructive">{searchCommand.data.result.error_message}</p>
          )}

          {isJoining && (
            <div className="flex items-center gap-2 rounded-md border border-dashed px-3 py-2 text-xs text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              <span>{t.externalApi.joining}</span>
            </div>
          )}

          {joinError && (
            <p className="text-xs text-destructive">{joinError}</p>
          )}

          {hasCompletedSearch && searchItems.length === 0 && !searchCommand.data?.result?.error_message && (
            <p className="rounded-md border border-dashed px-3 py-2 text-xs text-muted-foreground">
              {t.externalApi.noResults}
            </p>
          )}

          {hasCompletedSearch && searchItems.length > 0 && (
            <div className="flex flex-col gap-2">
              {searchItems.map((item) => (
                <div key={item.id} className="rounded-md border p-2">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="line-clamp-2 text-sm font-medium">{item.title}</p>
                      {item.summary && (
                        <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">{item.summary}</p>
                      )}
                    </div>
                    {item.url && (
                      <a href={item.url} target="_blank" rel="noreferrer" className="text-muted-foreground hover:text-foreground">
                        <ExternalLink className="h-4 w-4" />
                      </a>
                    )}
                  </div>
                  <div className="mt-2 flex flex-wrap gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      type="button"
                      onClick={() => handleJoin(item)}
                      disabled={!canCreateSource || isJoining}
                    >
                      <Plus className="h-3.5 w-3.5" />
                      {t.externalApi.join}
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}

        </div>
      )}
    </div>
  )
}
