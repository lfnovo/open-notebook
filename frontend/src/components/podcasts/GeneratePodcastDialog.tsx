'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { Loader2 } from 'lucide-react'
import { useQueries, useQueryClient } from '@tanstack/react-query'

import { useNotebooks } from '@/lib/hooks/use-notebooks'
import { useEpisodeProfiles, useGeneratePodcast } from '@/lib/hooks/use-podcasts'
import { chatApi } from '@/lib/api/chat'
import { sourcesApi } from '@/lib/api/sources'
import { notesApi } from '@/lib/api/notes'
import { BuildContextRequest, NoteResponse, SourceListResponse } from '@/lib/types/api'
import { PodcastGenerationRequest } from '@/lib/types/podcasts'
import { QUERY_KEYS } from '@/lib/api/query-client'
import { useToast } from '@/lib/hooks/use-toast'
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

const SOURCE_MODES = [
  { value: 'insights', label: 'Summary' },
  { value: 'full', label: 'Full content' },
] as const

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

export function GeneratePodcastDialog({ open, onOpenChange }: GeneratePodcastDialogProps) {
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

  // Initialise selection defaults when content loads
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
  }, [open, notebooks, sourcesQueries, notesQueries])

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
        const snippet = `Notebook: ${notebookName}\n${contextString}`
        parts.push(snippet)
      } catch (error) {
        console.error('Failed to build context for notebook', task.notebookId, error)
        throw new Error('Failed to build context. Please review your selections.')
      }
    }

    return parts.join('\n\n')
  }, [notebooks, selections])

  const handleSubmit = useCallback(async () => {
    if (!selectedEpisodeProfile) {
      toast({
        title: 'Episode profile required',
        description: 'Select an episode profile before generating a podcast.',
        variant: 'destructive',
      })
      return
    }

    if (!episodeName.trim()) {
      toast({
        title: 'Episode name required',
        description: 'Provide a name for the episode.',
        variant: 'destructive',
      })
      return
    }

    setIsBuildingContext(true)
    try {
      const content = await buildContentFromSelections()
      if (!content.trim()) {
        toast({
          title: 'Add context',
          description: 'Select at least one source or note to include in the episode.',
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

      // Delay closing dialog slightly to ensure refetch completes
      setTimeout(() => {
        onOpenChange(false)
        resetState()
      }, 500)
    } catch (error) {
      console.error('Failed to generate podcast', error)
      toast({
        title: 'Podcast generation failed',
        description: error instanceof Error ? error.message : 'Please try again later.',
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
          <DialogTitle>Generate Podcast Episode</DialogTitle>
          <DialogDescription>
            Select the content to include and configure the episode details before generating a new podcast episode.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-6 md:grid-cols-[2fr_1fr] xl:grid-cols-[3fr_1fr]">
          <div className="flex flex-col gap-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                  Content
                </h3>
                <p className="text-xs text-muted-foreground">
                  Pick notebooks, sources, and notes to include in this episode.
                </p>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant="outline">
                  {selectedNotebookSummaries.reduce(
                    (acc, summary) => acc + summary.sources + summary.notes,
                    0
                  )}{' '}
                  items selected
                </Badge>
                {(tokenCount > 0 || charCount > 0) && (
                  <span className="text-xs text-muted-foreground">
                    {tokenCount > 0 && `${formatNumber(tokenCount)} tokens`}
                    {tokenCount > 0 && charCount > 0 && ' / '}
                    {charCount > 0 && `${formatNumber(charCount)} chars`}
                  </span>
                )}
              </div>
            </div>

            <div className="rounded-lg border bg-muted/30">
              {notebooksQuery.isLoading ? (
                <div className="flex items-center justify-center py-16 text-sm text-muted-foreground">
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Loading notebooks
                </div>
              ) : notebooks.length === 0 ? (
                <div className="p-6 text-sm text-muted-foreground">
                  No notebooks found. Create a notebook and add content before generating a podcast.
                </div>
              ) : (
                <ScrollArea className="h-[60vh]">
                  <Accordion
                    type="multiple"
                    value={expandedNotebooks}
                    onValueChange={(value) => setExpandedNotebooks(value as string[])}
                    className="w-full"
                  >
                    {notebooks.map((notebook, index) => {
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
                              <div className="flex w-full items-center justify-between gap-3">
                                <div className="text-left">
                                  <p className="font-medium text-sm text-foreground">
                                    {notebook.name}
                                  </p>
                                  <p className="text-xs text-muted-foreground">
                                    {summary.sources + summary.notes > 0
                                      ? `${summary.sources} sources, ${summary.notes} notes`
                                      : 'No content selected'}
                                  </p>
                                </div>
                                <Badge variant="outline" className="text-xs">
                                  {sources.length} sources · {notes.length} notes
                                </Badge>
                              </div>
                            </AccordionTrigger>
                          </div>
                          <AccordionContent>
                            <div className="space-y-4 px-4 pb-4">
                              <div className="space-y-2">
                                <div className="flex items-center justify-between">
                                  <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                                    Sources
                                  </h4>
                                  {sourcesQueries[index]?.isFetching && (
                                    <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />
                                  )}
                                </div>
                                {sources.length === 0 ? (
                                  <p className="text-xs text-muted-foreground">
                                    No sources available in this notebook.
                                  </p>
                                ) : (
                                  <div className="space-y-2">
                                    {sources.map((source) => {
                                      const mode = selection?.sources?.[source.id] ?? 'off'
                                      return (
                                        <div
                                          key={source.id}
                                          className="flex items-center gap-3 rounded border bg-background px-3 py-2"
                                        >
                                          <Checkbox
                                            checked={mode !== 'off'}
                                            onCheckedChange={(checked) =>
                                              handleSourceModeChange(
                                                notebook.id,
                                                source.id,
                                                checked ? getSourceDefaultMode(source) : 'off'
                                              )
                                            }
                                          />
                                          <div className="flex flex-1 flex-col gap-1">
                                            <span className="text-sm font-medium text-foreground">
                                              {source.title || 'Untitled source'}
                                            </span>
                                            <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                              <span>{source.asset?.url ? 'Link' : 'File'}</span>
                                              <span>•</span>
                                              <span>{source.embedded ? 'Embedded' : 'Not embedded'}</span>
                                            </div>
                                          </div>
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
                                              <SelectValue placeholder="Select mode" />
                                            </SelectTrigger>
                                            <SelectContent>
                                              {SOURCE_MODES.map((option) => (
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
                                  Notes
                                </h4>
                                {notes.length === 0 ? (
                                  <p className="text-xs text-muted-foreground">
                                    No notes available in this notebook.
                                  </p>
                                ) : (
                                  <div className="space-y-2">
                                    {notes.map((note) => {
                                      const mode = selection?.notes?.[note.id] ?? 'off'
                                      return (
                                        <div
                                          key={note.id}
                                          className="flex items-center gap-3 rounded border bg-background px-3 py-2"
                                        >
                                          <Checkbox
                                            checked={mode !== 'off'}
                                            onCheckedChange={(checked) =>
                                              handleNoteToggle(
                                                notebook.id,
                                                note.id,
                                                Boolean(checked)
                                              )
                                            }
                                          />
                                          <div className="flex flex-1 flex-col">
                                            <span className="text-sm font-medium text-foreground">
                                              {note.title || 'Untitled note'}
                                            </span>
                                            <span className="text-xs text-muted-foreground">
                                              Updated {new Date(note.updated).toLocaleString()}
                                            </span>
                                          </div>
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

          <div className="space-y-6">
            <div className="space-y-3">
              <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                Episode Settings
              </h3>
              {episodeProfilesQuery.isLoading ? (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" /> Loading episode profiles
                </div>
              ) : episodeProfiles.length === 0 ? (
                <div className="rounded-lg border border-dashed bg-muted/30 p-4 text-sm text-muted-foreground">
                  No episode profiles found. Create an episode profile before generating a podcast.
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="episode_profile">Episode profile</Label>
                    <Select
                      value={episodeProfileId}
                      onValueChange={setEpisodeProfileId}
                      disabled={episodeProfiles.length === 0}
                    >
                      <SelectTrigger id="episode_profile">
                        <SelectValue placeholder="Select an episode profile" />
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
                        Uses speaker profile <strong>{selectedEpisodeProfile.speaker_config}</strong>
                      </p>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="episode_name">Episode name</Label>
                    <Input
                      id="episode_name"
                      value={episodeName}
                      onChange={(event) => setEpisodeName(event.target.value)}
                      placeholder="e.g., AI and the Future of Work"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="instructions">Additional instructions</Label>
                    <Textarea
                      id="instructions"
                      value={instructions}
                      onChange={(event) => setInstructions(event.target.value)}
                      placeholder="Any supplemental guidance to append to the episode briefing..."
                      rows={6}
                    />
                    <p className="text-xs text-muted-foreground">
                      These instructions will be appended to the episode profile&apos;s default briefing.
                    </p>
                  </div>
                </div>
              )}
            </div>

            <Separator />

            <div className="flex flex-col gap-3">
              <Button
                onClick={handleSubmit}
                disabled={isSubmitting || episodeProfiles.length === 0}
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Generating episode...
                  </>
                ) : (
                  'Generate Podcast'
                )}
              </Button>
              <p className="text-xs text-muted-foreground">
                The episode will appear in the Episodes list once generation starts. Refresh the list to monitor progress.
              </p>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
