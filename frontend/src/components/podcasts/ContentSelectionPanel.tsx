'use client'

import { Loader2 } from 'lucide-react'
import { useQueryClient } from '@tanstack/react-query'

import { sourcesApi } from '@/lib/api/sources'
import { notesApi } from '@/lib/api/notes'
import { NoteResponse, NotebookResponse, SourceListResponse } from '@/lib/types/api'
import { QUERY_KEYS } from '@/lib/api/query-client'
import { useTranslation } from '@/lib/hooks/use-translation'
import { Checkbox } from '@/components/ui/checkbox'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Label } from '@/components/ui/label'
import { Separator } from '@/components/ui/separator'
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion'

import {
  NotebookSelection,
  NotebookSummary,
  SourceMode,
  formatNumber,
  getSourceDefaultMode,
} from './generate-podcast-selection'

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
  onNotebookToggle: (notebookId: string, checked: boolean | 'indeterminate') => void
  onSourceModeChange: (notebookId: string, sourceId: string, mode: SourceMode) => void
  onNoteToggle: (notebookId: string, noteId: string, checked: boolean | 'indeterminate') => void
}

export function ContentSelectionPanel({
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
  onNotebookToggle,
  onSourceModeChange,
  onNoteToggle,
}: ContentSelectionPanelProps) {
  const { t, language } = useTranslation()
  const queryClient = useQueryClient()

  const sourceModes = [
    { value: 'insights', label: t('podcasts.summary') },
    { value: 'full', label: t('podcasts.fullContent') },
  ] as const

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            {t('podcasts.content')}
          </h3>
          <p className="text-xs text-muted-foreground">
            {t('podcasts.contentDesc')}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="outline">
            {t('podcasts.itemsSelected', { count: selectedNotebookSummaries.reduce(
                (acc: number, summary: NotebookSummary) => acc + summary.sources + summary.notes,
                0
              ) })}
          </Badge>
          {(tokenCount > 0 || charCount > 0) && (
            <span className="text-xs text-muted-foreground">
              {tokenCount > 0 && t('podcasts.tokens', { value: formatNumber(tokenCount) })}
              {tokenCount > 0 && charCount > 0 && ' / '}
              {charCount > 0 && t('podcasts.chars', { value: formatNumber(charCount) })}
            </span>
          )}
        </div>
      </div>

      <div className="rounded-lg border bg-muted/30">
        {isLoading ? (
          <div className="flex items-center justify-center py-16 text-sm text-muted-foreground">
            <Loader2 className="mr-2 h-4 w-4 animate-spin" /> {t('podcasts.loadingNotebooks')}
          </div>
        ) : notebooks.length === 0 ? (
          <div className="p-6 text-sm text-muted-foreground">
            {t('podcasts.noNotebooksFoundInPodcasts')}
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
                          onNotebookToggle(notebook.id, checked)
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
                                ? `${summary.sources} ${t('podcasts.sources')}, ${summary.notes} ${t('podcasts.notes')}`
                                : t('podcasts.noContentSelected')}
                            </p>
                          </div>
                          <Badge variant="outline" className="text-xs">
                            {sources.length} {t('podcasts.sources')} · {notes.length} {t('podcasts.notes')}
                          </Badge>
                        </Label>
                      </AccordionTrigger>
                    </div>
                    <AccordionContent>
                      <div className="space-y-4 px-4 pb-4">
                        <div className="space-y-2">
                          <div className="flex items-center justify-between">
                            <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                              {t('podcasts.sources')}
                            </h4>
                            {fetchingNotebookIds.has(notebook.id) && (
                              <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />
                            )}
                          </div>
                          {sources.length === 0 ? (
                            <p className="text-xs text-muted-foreground">
                              {t('podcasts.noSources')}
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
                                        onSourceModeChange(
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
                                        {source.title || t('podcasts.untitledSource')}
                                      </span>
                                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                        <span>{source.asset?.url ? t('podcasts.link') : t('podcasts.file')}</span>
                                        <span>•</span>
                                        <span>{source.embedded ? t('podcasts.embedded') : t('podcasts.notEmbedded')}</span>
                                      </div>
                                    </Label>
                                    <Select
                                      value={mode === 'off' ? 'off' : mode}
                                      onValueChange={(value) =>
                                        onSourceModeChange(
                                          notebook.id,
                                          source.id,
                                          value as SourceMode
                                        )
                                      }
                                      disabled={mode === 'off'}
                                    >
                                      <SelectTrigger className="w-[140px]">
                                        <SelectValue placeholder={t('podcasts.selectMode')} />
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
                            {t('podcasts.notes')}
                          </h4>
                          {notes.length === 0 ? (
                            <p className="text-xs text-muted-foreground">
                              {t('podcasts.noNotes')}
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
                                        onNoteToggle(
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
                                        {note.title || t('podcasts.untitledNote')}
                                      </span>
                                      <span className="text-xs text-muted-foreground">
                                        {t('common.updated')}{' '}
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
