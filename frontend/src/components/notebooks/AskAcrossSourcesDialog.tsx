'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Loader2, AlertCircle } from 'lucide-react'

import { useSources } from '@/lib/hooks/use-sources'
import { commandsApi } from '@/lib/api/commands'
import { QUERY_KEYS } from '@/lib/api/query-client'
import { useToast } from '@/lib/hooks/use-toast'
import { useTranslation } from '@/lib/hooks/use-translation'
import { getApiErrorMessage } from '@/lib/utils/error-handler'
import { isStudyJobActive, FAILED_STUDY_JOB_STATUSES } from '@/lib/types/study'
import { AskAcrossSourcesResult } from '@/lib/types/commands'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { CheckboxList } from '@/components/ui/checkbox-list'
import { Alert, AlertDescription } from '@/components/ui/alert'

interface AskAcrossSourcesDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  notebookId: string
}

export function AskAcrossSourcesDialog({
  open,
  onOpenChange,
  notebookId,
}: AskAcrossSourcesDialogProps) {
  const { t } = useTranslation()
  const { toast } = useToast()
  const queryClient = useQueryClient()

  const [question, setQuestion] = useState('')
  const [selectedSourceIds, setSelectedSourceIds] = useState<string[]>([])
  const [jobId, setJobId] = useState<string | undefined>(undefined)

  const sourcesQuery = useSources(notebookId)
  const sources = useMemo(() => sourcesQuery.data ?? [], [sourcesQuery.data])
  const checkboxItems = useMemo(
    () => sources.map((source) => ({ id: source.id, title: source.title || t('sources.untitledSource') })),
    [sources, t]
  )

  // All sources start checked - the point of this dialog is combining
  // everything relevant in the notebook; she can uncheck what she doesn't want.
  useEffect(() => {
    if (open) {
      setSelectedSourceIds(sources.map((source) => source.id))
    }
  }, [open, sources])

  const toggleSource = useCallback((id: string) => {
    setSelectedSourceIds((current) =>
      current.includes(id) ? current.filter((existing) => existing !== id) : [...current, id]
    )
  }, [])

  const submitMutation = useMutation({
    mutationFn: () =>
      commandsApi.submit('ask_across_sources', 'open_notebook', {
        notebook_id: notebookId,
        question: question.trim(),
        context_config: {
          sources: Object.fromEntries(
            sources.map((source) => [
              source.id,
              selectedSourceIds.includes(source.id) ? 'full content' : 'not in',
            ])
          ),
          notes: {},
        },
      }),
    onError: (error: unknown) => {
      toast({
        title: t('askSources.submitError'),
        description: getApiErrorMessage(error, (key) => t(key), 'apiErrors.failedToSendMessage'),
        variant: 'destructive',
      })
    },
  })

  const jobStatus = useQuery({
    queryKey: QUERY_KEYS.commandJob(jobId ?? ''),
    queryFn: () => commandsApi.getStatus<AskAcrossSourcesResult>(jobId as string),
    enabled: !!jobId,
    refetchInterval: (query) => (isStudyJobActive(query.state.data?.status) ? 3000 : false),
  })

  const jobStatusValue = jobStatus.data?.status
  const isFailed = !!jobStatusValue && (FAILED_STUDY_JOB_STATUSES as string[]).includes(jobStatusValue)
  const isRunning = !!jobId && !isFailed && jobStatusValue !== 'completed'

  const resetState = useCallback(() => {
    setQuestion('')
    setSelectedSourceIds(sources.map((source) => source.id))
    setJobId(undefined)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (!open) resetState()
  }, [open, resetState])

  // Watch the in-flight job: once it resolves, refresh Notas (that's where
  // the answer lands - see commands/ask_sources_command.py) and close.
  useEffect(() => {
    if (!jobId || !jobStatus.data) return

    if (jobStatus.data.status === 'completed') {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.notes(notebookId) })
      toast({
        title: t('askSources.completeTitle'),
        description: t('askSources.completeDesc'),
      })
      onOpenChange(false)
    }
    // Failed: leave the dialog open with the inline error (handled in render).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId, jobStatus.data?.status])

  const handleSubmit = useCallback(async () => {
    if (!question.trim()) {
      toast({
        title: t('askSources.questionRequired'),
        variant: 'destructive',
      })
      return
    }
    if (selectedSourceIds.length === 0) {
      toast({
        title: t('askSources.selectAtLeastOne'),
        variant: 'destructive',
      })
      return
    }

    try {
      const response = await submitMutation.mutateAsync()
      setJobId(response.job_id)
    } catch {
      // onError above already toasted.
    }
  }, [question, selectedSourceIds, submitMutation, t, toast])

  const isSubmitting = submitMutation.isPending || isRunning

  return (
    <Dialog
      open={open}
      onOpenChange={(value) => {
        onOpenChange(value)
        if (!value) resetState()
      }}
    >
      <DialogContent className="sm:max-w-[520px]">
        <DialogHeader>
          <DialogTitle>{t('askSources.title')}</DialogTitle>
          <DialogDescription>{t('askSources.description')}</DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-2">
            <Label>{t('askSources.selectSourcesLabel')}</Label>
            <CheckboxList
              items={checkboxItems}
              selectedIds={selectedSourceIds}
              onToggle={toggleSource}
              loading={sourcesQuery.isLoading}
              emptyMessage={t('askSources.noSources')}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="ask_sources_question">{t('askSources.questionLabel')}</Label>
            <Textarea
              id="ask_sources_question"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder={t('askSources.questionPlaceholder')}
              disabled={isRunning}
              rows={3}
            />
          </div>

          {isRunning ? (
            <div className="flex items-center gap-2 rounded-lg border bg-muted/30 p-3 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              <div>
                <p className="font-medium text-foreground">{t('askSources.running')}</p>
                <p className="text-xs">{t('askSources.runningDesc')}</p>
              </div>
            </div>
          ) : null}

          {isFailed ? (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                {jobStatus.data?.error_message || t('askSources.failed')}
              </AlertDescription>
            </Alert>
          ) : null}

          <div className="flex flex-col gap-2">
            {isFailed ? (
              <Button onClick={() => setJobId(undefined)} className="w-full">
                {t('study.tryAgain')}
              </Button>
            ) : (
              <Button onClick={handleSubmit} disabled={isSubmitting} className="w-full">
                {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                {isSubmitting ? t('askSources.running') : t('askSources.submitBtn')}
              </Button>
            )}
            <Button
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={isRunning}
              className="w-full"
            >
              {t('study.close')}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
