'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Loader2 } from 'lucide-react'
import { useQueries } from '@tanstack/react-query'

import { useNotebooks } from '@/lib/hooks/use-notebooks'
import { useEpisodeProfiles, useGeneratePodcast } from '@/lib/hooks/use-podcasts'
import { chatApi } from '@/lib/api/chat'
import { sourcesApi } from '@/lib/api/sources'
import { notesApi } from '@/lib/api/notes'
import { NoteResponse, SourceListResponse } from '@/lib/types/api'
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
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'

import { ContentSelectionPanel } from './ContentSelectionPanel'
import {
  NotebookSelection,
  SourceMode,
  getSourceDefaultMode,
  hasSelections,
  selectionsToContextConfigs,
} from './generate-podcast-selection'

const TOKEN_COUNT_DEBOUNCE_MS = 400

interface GeneratePodcastDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function GeneratePodcastDialog({ open, onOpenChange }: GeneratePodcastDialogProps) {
  const { t } = useTranslation()
  const { toast } = useToast()
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

  // Generation counter: any newer effect run invalidates in-flight count requests,
  // so a slow, stale response can never overwrite a fresher one.
  const countRequestIdRef = useRef(0)

  // Update token/char counts when selections change (debounced + stale-guarded)
  useEffect(() => {
    const requestId = ++countRequestIdRef.current

    if (!open) {
      return
    }

    const configs = selectionsToContextConfigs(selections)

    if (configs.length === 0) {
      setTokenCount(0)
      setCharCount(0)
      return
    }

    const timer = setTimeout(async () => {
      try {
        let totalTokens = 0
        let totalChars = 0

        // Build context for each notebook and sum up counts
        for (const { notebookId, contextConfig } of configs) {
          const response = await chatApi.buildContext({
            notebook_id: notebookId,
            context_config: contextConfig,
          })

          if (requestId !== countRequestIdRef.current) {
            return
          }

          totalTokens += response.token_count
          totalChars += response.char_count
        }

        setTokenCount(totalTokens)
        setCharCount(totalChars)
      } catch (error) {
        if (requestId === countRequestIdRef.current) {
          console.error('Error updating context counts:', error)
          // Don't reset counts on error, keep previous values
        }
      }
    }, TOKEN_COUNT_DEBOUNCE_MS)

    return () => clearTimeout(timer)
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

    const tasks = selectionsToContextConfigs(selections)

    if (tasks.length === 0) {
      return ''
    }

    for (const task of tasks) {
      try {
        const response = await chatApi.buildContext({
          notebook_id: task.notebookId,
          context_config: task.contextConfig,
        })
        const notebookName = notebooks.find((nb) => nb.id === task.notebookId)?.name ?? task.notebookId
        const contextString = JSON.stringify(response.context, null, 2)
        const snippet = `${t('common.notebookLabel', { name: notebookName })}\n${contextString}`
        parts.push(snippet)
      } catch (error) {
        console.error('Failed to build context for notebook', task.notebookId, error)
        throw new Error(t('podcasts.buildContextFailed'))
      }
    }

    return parts.join('\n\n')
  }, [notebooks, selections, t])

  const handleSubmit = useCallback(async () => {
    if (!selectedEpisodeProfile) {
      toast({
        title: t('podcasts.profileRequired'),
        description: t('podcasts.profileRequiredDesc'),
        variant: 'destructive',
      })
      return
    }

    if (!episodeName.trim()) {
      toast({
        title: t('podcasts.nameRequired'),
        description: t('podcasts.nameRequiredDesc'),
        variant: 'destructive',
      })
      return
    }

    // The generation API takes the speaker profile by name; the episode
    // profile stores a record ID, so use the API-resolved name. It is null
    // when the referenced speaker profile no longer exists.
    const speakerProfileName = selectedEpisodeProfile.speaker_config_name
    if (!speakerProfileName) {
      toast({
        title: t('podcasts.speakerProfileMissing'),
        description: t('podcasts.speakerProfileMissingDesc'),
        variant: 'destructive',
      })
      return
    }

    setIsBuildingContext(true)
    try {
      const content = await buildContentFromSelections()
      if (!content.trim()) {
        toast({
          title: t('podcasts.addContext'),
          description: t('podcasts.addContextDesc'),
          variant: 'destructive',
        })
        return
      }

      const payload: PodcastGenerationRequest = {
        episode_profile: selectedEpisodeProfile.name,
        speaker_profile: speakerProfileName,
        episode_name: episodeName.trim(),
        content,
        briefing_suffix: instructions.trim() ? instructions.trim() : undefined,
      }

      // mutateAsync resolves only after the mutation's onSuccess handler has
      // awaited the episode list refetch, so it is safe to close immediately.
      await generatePodcast.mutateAsync(payload)

      toast({
        title: t('common.success'),
        description: t('podcasts.podcastTaskStarted'),
      })

      onOpenChange(false)
      resetState()
    } catch (error) {
      console.error('Failed to generate podcast', error)
      toast({
        title: t('podcasts.generationFailed'),
        description: error instanceof Error ? error.message : t('common.refreshPage'),
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
          <DialogTitle>{t('podcasts.generateEpisode')}</DialogTitle>
          <DialogDescription>
            {t('podcasts.generateEpisodeDesc')}
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
            onNotebookToggle={handleNotebookToggle}
            onSourceModeChange={handleSourceModeChange}
            onNoteToggle={handleNoteToggle}
          />

          <div className="space-y-6">
            <div className="space-y-3">
              <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                {t('podcasts.episodeSettings')}
              </h3>
              {episodeProfilesQuery.isLoading ? (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" /> {t('podcasts.loadingProfiles')}
                </div>
              ) : episodeProfiles.length === 0 ? (
                <div className="rounded-lg border border-dashed bg-muted/30 p-4 text-sm text-muted-foreground">
                  {t('podcasts.noProfilesFound')}
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="episode_profile">{t('podcasts.episodeProfile')}</Label>
                    <Select
                      value={episodeProfileId}
                      onValueChange={setEpisodeProfileId}
                      disabled={episodeProfiles.length === 0}
                    >
                      <SelectTrigger id="episode_profile">
                        <SelectValue placeholder={t('podcasts.episodeProfilePlaceholder')} />
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
                        {selectedEpisodeProfile.speaker_config_name ? (
                          <>
                            {t('podcasts.usesSpeakerProfile')}{' '}
                            <strong>{selectedEpisodeProfile.speaker_config_name}</strong>
                          </>
                        ) : (
                          t('podcasts.speakerProfileMissingDesc')
                        )}
                      </p>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="episode_name">{t('podcasts.episodeName')}</Label>
                    <Input
                      id="episode_name"
                      name="episode_name"
                      value={episodeName}
                      onChange={(event) => setEpisodeName(event.target.value)}
                      placeholder={t('podcasts.episodeNamePlaceholder')}
                      autoComplete="off"
                    />
                  </div>

                   <div className="space-y-2">
                    <Label htmlFor="instructions">{t('podcasts.additionalInstructions')}</Label>
                    <Textarea
                      id="instructions"
                      name="instructions"
                      placeholder={t('podcasts.instructionsPlaceholder')}
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
                {isSubmitting ? t('podcasts.generating') : t('podcasts.generate')}
              </Button>
              <Button
                variant="outline"
                onClick={() => onOpenChange(false)}
                disabled={isSubmitting}
                className="w-full"
              >
                {t('common.cancel')}
              </Button>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
