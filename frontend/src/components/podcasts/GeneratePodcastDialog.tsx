'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { Loader2 } from 'lucide-react'
import { useQueries, useQueryClient } from '@tanstack/react-query'

import { useNotebooks } from '@/lib/hooks/use-notebooks'
import { useEpisodeProfiles, useGeneratePodcast } from '@/lib/hooks/use-podcasts'
import { chatApi } from '@/lib/api/chat'
import { sourcesApi } from '@/lib/api/sources'
import { notesApi } from '@/lib/api/notes'
import { BuildContextRequest, NoteResponse, NotebookResponse, SourceListResponse } from '@/lib/types/api'
import type { QueryClient } from '@tanstack/react-query'
import { PodcastGenerationRequest } from '@/lib/types/podcasts'
import { QUERY_KEYS } from '@/lib/api/query-client'
import { useToast } from '@/lib/hooks/use-toast'
import { useTranslation } from '@/lib/hooks/use-translation'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Label } from '@/components/ui/label'
import { Separator } from '@/components/ui/separator'
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion'

type SourceMode = 'off' | 'insights' | 'full'

interface NotebookSelection {
  sources: Record<string, SourceMode>
  notes: Record<string, SourceMode>
}

// Helper function to format large numbers with K/M suffixes
function formatNumber(num: number): string {
  if (num >= 1000000) {
    return `${(num / 1000000).toFixed(1)}M`
  }
  if (num >= 1000) {
    return `${(num / 1000).toFixed(1)}K`
  }
  return num.toString()
}

function hasSelections(selection?: NotebookSelection): boolean {
  if (!selection) {
    return false
  }
  return (
    Object.values(selection.sources).some((mode) => mode !== 'off') ||
    Object.values(selection.notes).some((mode) => mode !== 'off')
  )
}

function getSourceDefaultMode(source: SourceListResponse): SourceMode {
  return source.insights_count && source.insights_count > 0 ? 'insights' : 'full'
}

interface GeneratePodcastDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

interface NotebookSummary {
  notebookId: string
  sources: number
  notes: number
}

interface ContentSelectionPanelProps {
  notebooks: NotebookResponse[]
  isLoading: boolean
  selectedNotebookSummaries: NotebookSummary[]
  tokenCount: number
  charCount: number
  expandedNotebooks: string[]
  setExpandedNotebooks: (notebooks: string[]) => void
  selections: Record<string, NotebookSelection>
  sourcesByNotebook: Record<string, SourceListResponse[]>
  notesByNotebook: Record<string, NoteResponse[]>
  fetchingNotebookIds: Set<string>
  handleNotebookToggle: (notebookId: string, checked: boolean | 'indeterminate') => void
  handleSourceModeChange: (notebookId: string, sourceId: string, mode: SourceMode) => void
  handleNoteToggle: (notebookId: string, noteId: string, checked: boolean | 'indeterminate') => void
  queryClient: QueryClient
}

// Extracted component for content selection panel
function ContentSelectionPanel({
  notebooks,
  isLoading,
  selectedNotebookSummaries,
  tokenCount,
  charCount,
  expandedNotebooks,
  setExpandedNotebooks,
  selections,
  sourcesByNotebook,
  notesByNotebook,
  fetchingNotebookIds,
  handleNotebookToggle,
  handleSourceModeChange,
  handleNoteToggle,
  queryClient,
}: ContentSelectionPanelProps) {
  const { t, language } = useTranslation()

  // Cache all translation strings at render time to avoid repeated Proxy accesses in loops
  // This prevents the infinite loop detection from triggering
  const tr = {
    content: t.podcasts.content,
    contentDesc: t.podcasts.contentDesc,
    itemsSelected: t.podcasts.itemsSelected,
    tokens: t.podcasts.tokens,
    chars: t.podcasts.chars,
    loadingNotebooks: t.podcasts.loadingNotebooks,
    noNotebooksFoundInPodcasts: t.podcasts.noNotebooksFoundInPodcasts,
    sources: t.podcasts.sources,
    notes: t.podcasts.notes,
    noContentSelected: t.podcasts.noContentSelected,
    noSources: t.podcasts.noSources,
    untitledSource: t.podcasts.untitledSource,
    link: t.podcasts.link,
    file: t.podcasts.file,
    embedded: t.podcasts.embedded,
    notEmbedded: t.podcasts.notEmbedded,
    selectMode: t.podcasts.selectMode,
    noNotes: t.podcasts.noNotes,
    untitledNote: t.podcasts.untitledNote,
    commonUpdated: t.common.updated,
    summary: t.podcasts.summary,
    fullContent: t.podcasts.fullContent,
  }

  // Pre-compute source modes once to avoid repeated t.podcasts access in loops
  const sourceModes = [
    { value: 'insights', label: tr.summary },
    { value: 'full', label: tr.fullContent },
  ] as const

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            {tr.content}
          </h3>
          <p className="text-xs text-muted-foreground">
            {tr.contentDesc}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="outline">
            {tr.itemsSelected.replace(
              '{count}',
              selectedNotebookSummaries.reduce(
                (acc: number, summary: NotebookSummary) => acc + summary.sources + summary.notes,
                0
              ).toString()
            )}
          </Badge>
          {(tokenCount > 0 || charCount > 0) && (
            <span className="text-xs text-muted-foreground">
              {tokenCount > 0 && tr.tokens.replace('{count}', formatNumber(tokenCount))}
              {tokenCount > 0 && charCount > 0 && ' / '}
              {charCount > 0 && tr.chars.replace('{count}', formatNumber(charCount))}
            </span>
          )}
        </div>
      </div>

      <div className="rounded-lg border bg-muted/30">
        {isLoading ? (
          <div className="flex items-center justify-center py-16 text-sm text-muted-foreground">
            <Loader2 className="mr-2 h-4 w-4 animate-spin" /> {tr.loadingNotebooks}
          </div>
        ) : notebooks.length === 0 ? (
          <div className="p-6 text-sm text-muted-foreground">
            {tr.noNotebooksFoundInPodcasts}
          </div>
        ) : (
          <ScrollArea className="h-[60vh]">
            <Accordion
              type="multiple"
              value={expandedNotebooks}
              onValueChange={(value) => setExpandedNotebooks(value as string[])}
              className="w-full"
            >
              {notebooks.map((notebook: NotebookResponse, index: number) => {
                const sources = sourcesByNotebook[notebook.id] ?? []
                const notes = notesByNotebook[notebook.id] ?? []
                const selection = selections[notebook.id]
                const summary = selectedNotebookSummaries[index]
                const notebookChecked = summary.sources + summary.notes > 0
                const totalItems = sources.length + notes.length
                const isIndeterminate =
                  notebookChecked &&
                  summary.sources + summary.notes > 0 &&
                  summary.sources + summary.notes < totalItems

                return (
                  <AccordionItem key={notebook.id} value={notebook.id}>
                    <div className="flex items-start gap-3 px-4 pt-3">
                      <Checkbox
                        id={`notebook-toggle-${notebook.id}`}
                        checked={isIndeterminate ? 'indeterminate' : notebookChecked}
                        onCheckedChange={(checked) => {
                          handleNotebookToggle(notebook.id, checked)
                          queryClient.prefetchQuery({
                            queryKey: QUERY_KEYS.sources(notebook.id),
                            queryFn: () => sourcesApi.list({ notebook_id: notebook.id }),
                          })
                          queryClient.prefetchQuery({
                            queryKey: QUERY_KEYS.notes(notebook.id),
                            queryFn: () => notesApi.list({ notebook_id: notebook.id }),
                          })
                        }}
                        onClick={(event) => event.stopPropagation()}
                      />
                      <AccordionTrigger className="flex-1 px-0 py-0 hover:no-underline">
                        <Label
                          htmlFor={`notebook-toggle-${notebook.id}`}
                          className="flex w-full items-center justify-between gap-3 pointer-events-none"
                        >
                          <div className="text-left">
                            <p className="font-medium text-sm text-foreground">
                              {notebook.name}
                            </p>
                            <p className="text-xs text-muted-foreground">
                              {summary.sources + summary.notes > 0
                                ? `${summary.sources} ${tr.sources}, ${summary.notes} ${tr.notes}`
                                : tr.noContentSelected}
                            </p>
                          </div>
                          <Badge variant="outline" className="text-xs">
                            {sources.length} {tr.sources} · {notes.length} {tr.notes}
                          </Badge>
                        </Label>
                      </AccordionTrigger>
                    </div>
                    <AccordionContent>
                      <div className="space-y-4 px-4 pb-4">
                        <div className="space-y-2">
                          <div className="flex items-center justify-between">
                            <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                              {tr.sources}
                            </h4>
                            {fetchingNotebookIds.has(notebook.id) && (
                              <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />
                            )}
                          </div>
                          {sources.length === 0 ? (
                            <p className="text-xs text-muted-foreground">
                              {tr.noSources}
                            </p>
                          ) : (
                            <div className="space-y-2">
                              {sources.map((source: SourceListResponse) => {
                                const mode = selection?.sources?.[source.id] ?? 'off'
                                return (
                                  <div
                                    key={source.id}
                                    className="flex items-center gap-3 rounded border bg-background px-3 py-2"
                                  >
                                    <Checkbox
                                      id={`source-selection-${source.id}`}
                                      checked={mode !== 'off'}
                                      onCheckedChange={(checked) =>
                                        handleSourceModeChange(
                                          notebook.id,
                                          source.id,
                                          checked ? getSourceDefaultMode(source) : 'off'
                                        )
                                      }
                                    />
                                    <Label
                                      htmlFor={`source-selection-${source.id}`}
                                      className="flex flex-1 flex-col gap-1 cursor-pointer"
                                    >
                                      <span className="text-sm font-medium text-foreground">
                                        {source.title || tr.untitledSource}
                                      </span>
                                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                        <span>{source.asset?.url ? tr.link : tr.file}</span>
                                        <span>•</span>
                                        <span>{source.embedded ? tr.embedded : tr.notEmbedded}</span>
                                      </div>
                                    </Label>
                                    <Select
                                      value={mode === 'off' ? 'off' : mode}
                                      onValueChange={(value) =>
                                        handleSourceModeChange(
                                          notebook.id,
                                          source.id,
                                          value as SourceMode
                                        )
                                      }
                                      disabled={mode === 'off'}
                                    >
                                      <SelectTrigger className="w-[140px]">
                                        <SelectValue placeholder={tr.selectMode} />
                                      </SelectTrigger>
                                      <SelectContent>
                                        {sourceModes.map((option) => (
                                          <SelectItem
                                            key={option.value}
                                            value={option.value}
                                            disabled={
                                              option.value === 'insights' &&
                                              (!source.insights_count || source.insights_count === 0)
                                            }
                                          >
                                            {option.label}
                                          </SelectItem>
                                        ))}
                                      </SelectContent>
                                    </Select>
                                  </div>
                                )
                              })}
                            </div>
                          )}
                        </div>

                        <Separator />

                        <div className="space-y-2">
                          <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                            {tr.notes}
                          </h4>
                          {notes.length === 0 ? (
                            <p className="text-xs text-muted-foreground">
                              {tr.noNotes}
                            </p>
                          ) : (
                            <div className="space-y-2">
                              {notes.map((note: NoteResponse) => {
                                const mode = selection?.notes?.[note.id] ?? 'off'
                                return (
                                  <div
                                    key={note.id}
                                    className="flex items-center gap-3 rounded border bg-background px-3 py-2"
                                  >
                                    <Checkbox
                                      id={`note-selection-${note.id}`}
                                      checked={mode !== 'off'}
                                      onCheckedChange={(checked) =>
                                        handleNoteToggle(
                                          notebook.id,
                                          note.id,
                                          Boolean(checked)
                                        )
                                      }
                                    />
                                    <Label
                                      htmlFor={`note-selection-${note.id}`}
                                      className="flex flex-1 flex-col cursor-pointer"
                                    >
                                      <span className="text-sm font-medium text-foreground">
                                        {note.title || tr.untitledNote}
                                      </span>
                                      <span className="text-xs text-muted-foreground">
                                        {tr.commonUpdated}{' '}
                                        {new Date(note.updated).toLocaleString(
                                          language.startsWith('zh') ? language : 'en-US'
                                        )}
                                      </span>
                                    </Label>
                                  </div>
                                )
                              })}
                            </div>
                          )}
                        </div>
                      </div>
                    </AccordionContent>
                  </AccordionItem>
                )
              })}
            </Accordion>
          </ScrollArea>
        )}
      </div>
    </div>
  )
}

export function GeneratePodcastDialog({ open, onOpenChange }: GeneratePodcastDialogProps) {
  const { t } = useTranslation()
  const { toast } = useToast()
  const queryClient = useQueryClient()
  const [expandedNotebooks, setExpandedNotebooks] = useState<string[]>([])
  const [selections, setSelections] = useState<Record<string, NotebookSelection>>({})
  const [episodeProfileId, setEpisodeProfileId] = useState<string>('')
  const [episodeName, setEpisodeName] = useState('')
  const [instructions, setInstructions] = useState('')

  const [isBuildingContext, setIsBuildingContext] = useState(false)
  const [tokenCount, setTokenCount] = useState<number>(0)
  const [charCount, setCharCount] = useState<number>(0)

  const notebooksQuery = useNotebooks()
  const episodeProfilesQuery = useEpisodeProfiles()
  const generatePodcast = useGeneratePodcast()

  const notebooks = useMemo(
    () => notebooksQuery.data ?? [],
    [notebooksQuery.data]
  )
  const episodeProfiles = useMemo(
    () => episodeProfilesQuery.episodeProfiles ?? [],
    [episodeProfilesQuery.episodeProfiles]
  )

  // Fetch sources and notes for notebooks using useQueries
  const sourcesQueries = useQueries({
    queries: notebooks.map((notebook) => ({
      queryKey: QUERY_KEYS.sources(notebook.id),
      queryFn: () => sourcesApi.list({ notebook_id: notebook.id }),
      enabled:
        open &&
        (expandedNotebooks.includes(notebook.id) || hasSelections(selections[notebook.id])),
    })),
  })

  const notesQueries = useQueries({
    queries: notebooks.map((notebook) => ({
      queryKey: QUERY_KEYS.notes(notebook.id),
      queryFn: () => notesApi.list({ notebook_id: notebook.id }),
      enabled:
        open &&
        (expandedNotebooks.includes(notebook.id) || hasSelections(selections[notebook.id])),
    })),
  })

  const sourcesByNotebook = useMemo<Record<string, SourceListResponse[]>>(() => {
    const map: Record<string, SourceListResponse[]> = {}
    notebooks.forEach((notebook, index) => {
      map[notebook.id] = sourcesQueries[index]?.data ?? []
    })
    return map
  }, [notebooks, sourcesQueries])

  const notesByNotebook = useMemo<Record<string, NoteResponse[]>>(() => {
    const map: Record<string, NoteResponse[]> = {}
    notebooks.forEach((notebook, index) => {
      map[notebook.id] = notesQueries[index]?.data ?? []
    })
    return map
  }, [notebooks, notesQueries])

  // Stable key for fetching state - only changes when actual fetching states change
  const fetchingKey = useMemo(
    () => sourcesQueries.map((q) => q.isFetching ? '1' : '0').join(''),
    [sourcesQueries]
  )

  // Stable set of notebook IDs that are currently fetching sources
  const fetchingNotebookIds = useMemo(() => {
    const ids = new Set<string>()
    notebooks.forEach((notebook, index) => {
      if (sourcesQueries[index]?.isFetching) {
        ids.add(notebook.id)
      }
    })
    return ids
  }, [notebooks, fetchingKey])

  // Create a stable key based on actual data to prevent effect running on every render
  // Only changes when actual source/note IDs change, not on every useQueries reference change
  const dataKey = useMemo(() => {
    const sourceIds = sourcesQueries
      .map((q) => q.data?.map((s) => s.id)?.join(',') ?? '')
      .join('|')
    const noteIds = notesQueries
      .map((q) => q.data?.map((n) => n.id)?.join(',') ?? '')
      .join('|')
    return `${sourceIds}::${noteIds}`
  }, [sourcesQueries, notesQueries])

  // Initialise selection defaults when content loads
  // Using dataKey instead of sourcesQueries/notesQueries to prevent running on every render
  useEffect(() => {
    if (!open) {
      return
    }

    setSelections((prev) => {
      let changed = false
      const next = { ...prev }

      notebooks.forEach((notebook, index) => {
        const sources = sourcesQueries[index]?.data
        const notes = notesQueries[index]?.data

        if (!sources && !notes) {
          return
        }

        if (!next[notebook.id]) {
          next[notebook.id] = { sources: {}, notes: {} }
          changed = true
        }

        if (sources) {
          const currentSources = next[notebook.id].sources
          sources.forEach((source) => {
            if (!(source.id in currentSources)) {
              currentSources[source.id] = getSourceDefaultMode(source)
              changed = true
            }
          })
        }

        if (notes) {
          const currentNotes = next[notebook.id].notes
          notes.forEach((note) => {
            if (!(note.id in currentNotes)) {
              currentNotes[note.id] = 'full'
              changed = true
            }
          })
        }
      })

      return changed ? next : prev
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, notebooks, dataKey])

  const resetState = useCallback(() => {
    setExpandedNotebooks([])
    setSelections({})
    setEpisodeProfileId('')
    setEpisodeName('')
    setInstructions('')
    setTokenCount(0)
    setCharCount(0)
  }, [])

  useEffect(() => {
    if (!open) {
      resetState()
    }
  }, [open, resetState])

  // Update token/char counts when selections change
  useEffect(() => {
    if (!open) {
      return
    }

    const updateContextCounts = async () => {
      // Check if there are any selections
      const hasAnySelections = Object.values(selections).some((selection) =>
        Object.values(selection.sources).some((mode) => mode !== 'off') ||
        Object.values(selection.notes).some((mode) => mode !== 'off')
      )

      if (!hasAnySelections) {
        setTokenCount(0)
        setCharCount(0)
        return
      }

      try {
        let totalTokens = 0
        let totalChars = 0

        // Build context for each notebook and sum up counts
        for (const [notebookId, selection] of Object.entries(selections)) {
          const sourcesConfig = Object.entries(selection.sources)
            .filter(([, mode]) => mode !== 'off')
            .reduce<Record<string, string>>((acc, [sourceId, mode]) => {
              const normalizedId = sourceId.replace(/^source:/, '')
              acc[normalizedId] = mode === 'insights' ? 'insights' : 'full content'
              return acc
            }, {})

          const notesConfig = Object.entries(selection.notes)
            .filter(([, mode]) => mode !== 'off')
            .reduce<Record<string, string>>((acc, [noteId]) => {
              const normalizedId = noteId.replace(/^note:/, '')
              acc[normalizedId] = 'full content'
              return acc
            }, {})

          if (Object.keys(sourcesConfig).length === 0 && Object.keys(notesConfig).length === 0) {
            continue
          }

          const response = await chatApi.buildContext({
            notebook_id: notebookId,
            context_config: {
              sources: sourcesConfig,
              notes: notesConfig,
            },
          })

          totalTokens += response.token_count
          totalChars += response.char_count
        }

        setTokenCount(totalTokens)
        setCharCount(totalChars)
      } catch (error) {
        console.error('Error updating context counts:', error)
        // Don't reset counts on error, keep previous values
      }
    }

    updateContextCounts()
  }, [open, selections])

  const selectedEpisodeProfile = useMemo(() => {
    if (!episodeProfileId) {
      return undefined
    }
    return episodeProfiles.find((profile) => profile.id === episodeProfileId)
  }, [episodeProfileId, episodeProfiles])

  const selectedNotebookSummaries = useMemo(() => {
    return notebooks.map((notebook) => {
      const selection = selections[notebook.id]
      if (!selection) {
        return { notebookId: notebook.id, sources: 0, notes: 0 }
      }
      const sourcesCount = Object.values(selection.sources).filter(
        (mode) => mode !== 'off'
      ).length
      const notesCount = Object.values(selection.notes).filter(
        (mode) => mode !== 'off'
      ).length
      return { notebookId: notebook.id, sources: sourcesCount, notes: notesCount }
    })
  }, [notebooks, selections])

  const handleNotebookToggle = useCallback(
    (notebookId: string, checked: boolean | 'indeterminate') => {
      const shouldCheck = checked === 'indeterminate' ? true : checked
      const sources = sourcesByNotebook[notebookId] ?? []
      const notes = notesByNotebook[notebookId] ?? []
      setSelections((prev) => {
        if (shouldCheck) {
          const nextSources: Record<string, SourceMode> = {}
          sources.forEach((source) => {
            nextSources[source.id] = getSourceDefaultMode(source)
          })
          const nextNotes: Record<string, SourceMode> = {}
          notes.forEach((note) => {
            nextNotes[note.id] = 'full'
          })
          return {
            ...prev,
            [notebookId]: {
              sources: nextSources,
              notes: nextNotes,
            },
          }
        }

        const clearedSources: Record<string, SourceMode> = {}
        sources.forEach((source) => {
          clearedSources[source.id] = 'off'
        })
        const clearedNotes: Record<string, SourceMode> = {}
        notes.forEach((note) => {
          clearedNotes[note.id] = 'off'
        })

        return {
          ...prev,
          [notebookId]: {
            sources: clearedSources,
            notes: clearedNotes,
          },
        }
      })
    },
    [notesByNotebook, sourcesByNotebook]
  )

  const handleSourceModeChange = useCallback(
    (notebookId: string, sourceId: string, mode: SourceMode) => {
      setSelections((prev) => ({
        ...prev,
        [notebookId]: {
          sources: {
            ...(prev[notebookId]?.sources ?? {}),
            [sourceId]: mode,
          },
          notes: prev[notebookId]?.notes ?? {},
        },
      }))
    },
    []
  )

  const handleNoteToggle = useCallback(
    (notebookId: string, noteId: string, checked: boolean | 'indeterminate') => {
      setSelections((prev) => ({
        ...prev,
        [notebookId]: {
          sources: prev[notebookId]?.sources ?? {},
          notes: {
            ...(prev[notebookId]?.notes ?? {}),
            [noteId]: checked ? 'full' : 'off',
          },
        },
      }))
    },
    []
  )

  const buildContentFromSelections = useCallback(async () => {
    const parts: string[] = []

    const tasks: Array<{ notebookId: string; payload: BuildContextRequest }> = []

    Object.entries(selections).forEach(([notebookId, selection]) => {
      const sourcesConfig = Object.entries(selection.sources)
        .filter(([, mode]) => mode !== 'off')
        .reduce<Record<string, string>>((acc, [sourceId, mode]) => {
          const normalizedId = sourceId.replace(/^source:/, '')
          acc[normalizedId] = mode === 'insights' ? 'insights' : 'full content'
          return acc
        }, {})

      const notesConfig = Object.entries(selection.notes)
        .filter(([, mode]) => mode !== 'off')
        .reduce<Record<string, string>>((acc, [noteId]) => {
          const normalizedId = noteId.replace(/^note:/, '')
          acc[normalizedId] = 'full content'
          return acc
        }, {})

      if (Object.keys(sourcesConfig).length === 0 && Object.keys(notesConfig).length === 0) {
        return
      }

      tasks.push({
        notebookId,
        payload: {
          notebook_id: notebookId,
          context_config: {
            sources: sourcesConfig,
            notes: notesConfig,
          },
        },
      })
    })

    if (tasks.length === 0) {
      return ''
    }

    for (const task of tasks) {
      try {
        const response = await chatApi.buildContext(task.payload)
        const notebookName = notebooks.find((nb) => nb.id === task.notebookId)?.name ?? task.notebookId
        const contextString = JSON.stringify(response.context, null, 2)
        const snippet = `${t.common.notebookLabel.replace('{name}', notebookName)}\n${contextString}`
        parts.push(snippet)
      } catch (error) {
        console.error('Failed to build context for notebook', task.notebookId, error)
        throw new Error(t.podcasts.buildContextFailed)
      }
    }

    return parts.join('\n\n')
  }, [notebooks, selections, t])

  const handleSubmit = useCallback(async () => {
    if (!selectedEpisodeProfile) {
      toast({
        title: t.podcasts.profileRequired,
        description: t.podcasts.profileRequiredDesc,
        variant: 'destructive',
      })
      return
    }

    if (!episodeName.trim()) {
      toast({
        title: t.podcasts.nameRequired,
        description: t.podcasts.nameRequiredDesc,
        variant: 'destructive',
      })
      return
    }

    setIsBuildingContext(true)
    try {
      const content = await buildContentFromSelections()
      if (!content.trim()) {
        toast({
          title: t.podcasts.addContext,
          description: t.podcasts.addContextDesc,
          variant: 'destructive',
        })
        return
      }

      const payload: PodcastGenerationRequest = {
        episode_profile: selectedEpisodeProfile.name,
        speaker_profile: selectedEpisodeProfile.speaker_config,
        episode_name: episodeName.trim(),
        content,
        briefing_suffix: instructions.trim() ? instructions.trim() : undefined,
      }

      await generatePodcast.mutateAsync(payload)

      toast({
        title: t.common.success,
        description: t.podcasts.podcastTaskStarted,
      })

      // Delay closing dialog slightly to ensure refetch completes
      setTimeout(() => {
        onOpenChange(false)
        resetState()
      }, 500)
    } catch (error) {
      console.error('Failed to generate podcast', error)
      toast({
        title: t.podcasts.generationFailed,
        description: error instanceof Error ? error.message : t.common.refreshPage,
        variant: 'destructive',
      })
    } finally {
      setIsBuildingContext(false)
    }
  }, [
    buildContentFromSelections,
    episodeName,
    generatePodcast,
    instructions,
    onOpenChange,
    resetState,
    selectedEpisodeProfile,
    toast,
    t,
  ])

  const isSubmitting = generatePodcast.isPending || isBuildingContext

  return (
    <Dialog open={open} onOpenChange={(value) => {
      onOpenChange(value)
      if (!value) {
        resetState()
      }
    }}>
      <DialogContent className="w-[80vw] max-w-[1080px] max-h-[90vh] overflow-hidden">
        <DialogHeader>
          <DialogTitle>{t.podcasts.generateEpisode}</DialogTitle>
          <DialogDescription>
            {t.podcasts.generateEpisodeDesc}
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-6 md:grid-cols-[2fr_1fr] xl:grid-cols-[3fr_1fr]">
          <ContentSelectionPanel
            notebooks={notebooks}
            isLoading={notebooksQuery.isLoading}
            selectedNotebookSummaries={selectedNotebookSummaries}
            tokenCount={tokenCount}
            charCount={charCount}
            expandedNotebooks={expandedNotebooks}
            setExpandedNotebooks={setExpandedNotebooks}
            selections={selections}
            sourcesByNotebook={sourcesByNotebook}
            notesByNotebook={notesByNotebook}
            fetchingNotebookIds={fetchingNotebookIds}
            handleNotebookToggle={handleNotebookToggle}
            handleSourceModeChange={handleSourceModeChange}
            handleNoteToggle={handleNoteToggle}
            queryClient={queryClient}
          />

          <div className="space-y-6">
            <div className="space-y-3">
              <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                {t.podcasts.episodeSettings}
              </h3>
              {episodeProfilesQuery.isLoading ? (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" /> {t.podcasts.loadingProfiles}
                </div>
              ) : episodeProfiles.length === 0 ? (
                <div className="rounded-lg border border-dashed bg-muted/30 p-4 text-sm text-muted-foreground">
                  {t.podcasts.noProfilesFound}
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="episode_profile">{t.podcasts.episodeProfile}</Label>
                    <Select
                      value={episodeProfileId}
                      onValueChange={setEpisodeProfileId}
                      disabled={episodeProfiles.length === 0}
                    >
                      <SelectTrigger id="episode_profile">
                        <SelectValue placeholder={t.podcasts.episodeProfilePlaceholder} />
                      </SelectTrigger>
                      <SelectContent>
                        {episodeProfiles.map((profile) => (
                          <SelectItem key={profile.id} value={profile.id}>
                            {profile.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {selectedEpisodeProfile && (
                      <p className="text-xs text-muted-foreground">
                        {t.podcasts.usesSpeakerProfile}{' '}
                        <strong>{selectedEpisodeProfile.speaker_config}</strong>
                      </p>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="episode_name">{t.podcasts.episodeName}</Label>
                    <Input
                      id="episode_name"
                      name="episode_name"
                      value={episodeName}
                      onChange={(event) => setEpisodeName(event.target.value)}
                      placeholder={t.podcasts.episodeNamePlaceholder}
                      autoComplete="off"
                    />
                  </div>

                   <div className="space-y-2">
                    <Label htmlFor="instructions">{t.podcasts.additionalInstructions}</Label>
                    <Textarea
                      id="instructions"
                      name="instructions"
                      placeholder={t.podcasts.instructionsPlaceholder}
                      value={instructions}
                      onChange={(event) => setInstructions(event.target.value)}
                      className="min-h-[100px] text-xs"
                      autoComplete="off"
                    />
                  </div>
                </div>
              )}
            </div>

            <div className="flex flex-col gap-3">
              <Button
                onClick={handleSubmit}
                disabled={isSubmitting}
                className="w-full"
              >
                {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                {isSubmitting ? t.podcasts.generating : t.podcasts.generate}
              </Button>
              <Button
                variant="outline"
                onClick={() => onOpenChange(false)}
                disabled={isSubmitting}
                className="w-full"
              >
                {t.common.cancel}
              </Button>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
