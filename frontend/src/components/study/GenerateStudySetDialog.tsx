'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { Loader2, AlertCircle } from 'lucide-react'

import { useNotebooks } from '@/lib/hooks/use-notebooks'
import { useModels } from '@/lib/hooks/use-models'
import {
  useGenerateFlashcards,
  useGenerateQuiz,
  useStudyJobStatus,
} from '@/lib/hooks/use-study'
import { QUERY_KEYS } from '@/lib/api/query-client'
import { useQueryClient } from '@tanstack/react-query'
import { useToast } from '@/lib/hooks/use-toast'
import { useTranslation } from '@/lib/hooks/use-translation'
import { FAILED_STUDY_JOB_STATUSES, StudyKind } from '@/lib/types/study'
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
import { Label } from '@/components/ui/label'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Alert, AlertDescription } from '@/components/ui/alert'

interface GenerateStudySetDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  /** Preselects a notebook (e.g. when opened from within a notebook's own view). */
  notebookId?: string
  /** Called once generation finishes successfully, with the new study set's id. */
  onGenerated?: (studySetId: string) => void
}

export function GenerateStudySetDialog({
  open,
  onOpenChange,
  notebookId,
  onGenerated,
}: GenerateStudySetDialogProps) {
  const { t } = useTranslation()
  const { toast } = useToast()
  const queryClient = useQueryClient()

  const [kind, setKind] = useState<StudyKind>('flashcards')
  const [selectedNotebookId, setSelectedNotebookId] = useState(notebookId ?? '')
  const [name, setName] = useState('')
  const [itemCount, setItemCount] = useState(10)
  const [modelId, setModelId] = useState('default')
  const [jobId, setJobId] = useState<string | undefined>(undefined)

  const notebooksQuery = useNotebooks()
  const notebooks = useMemo(() => notebooksQuery.data ?? [], [notebooksQuery.data])
  const modelsQuery = useModels()
  const languageModels = useMemo(
    () => (modelsQuery.data ?? []).filter((model) => model.type === 'language'),
    [modelsQuery.data]
  )

  const generateFlashcards = useGenerateFlashcards()
  const generateQuiz = useGenerateQuiz()
  const activeMutation = kind === 'flashcards' ? generateFlashcards : generateQuiz

  const jobStatus = useStudyJobStatus(jobId)
  const jobStatusValue = jobStatus.data?.status
  const isFailed = !!jobStatusValue && (FAILED_STUDY_JOB_STATUSES as string[]).includes(jobStatusValue)

  const resetState = useCallback(() => {
    setKind('flashcards')
    setSelectedNotebookId(notebookId ?? '')
    setName('')
    setItemCount(10)
    setModelId('default')
    setJobId(undefined)
  }, [notebookId])

  useEffect(() => {
    if (!open) {
      resetState()
    }
  }, [open, resetState])

  // Watch the in-flight job: once it resolves, either finish up (refresh the
  // notebook's study sets, toast, close) or surface the failure inline.
  useEffect(() => {
    if (!jobId || !jobStatus.data) return

    if (jobStatus.data.status === 'completed') {
      const studySetId = jobStatus.data.result?.study_set_id
      if (selectedNotebookId) {
        queryClient.invalidateQueries({
          queryKey: QUERY_KEYS.studySetsForNotebook(selectedNotebookId),
        })
      }
      toast({
        title: t('study.generationComplete'),
        description: t('study.generationCompleteDesc', { name }),
      })
      onOpenChange(false)
      if (studySetId) {
        onGenerated?.(studySetId)
      }
    }
    // Failed/error: leave the dialog open with the inline error (handled in render).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId, jobStatus.data?.status])

  const handleSubmit = useCallback(async () => {
    if (!selectedNotebookId) {
      toast({
        title: t('study.notebookRequired'),
        description: t('study.notebookRequiredDesc'),
        variant: 'destructive',
      })
      return
    }

    if (!name.trim()) {
      toast({
        title: t('study.nameRequired'),
        description: t('study.nameRequiredDesc'),
        variant: 'destructive',
      })
      return
    }

    try {
      const response = await activeMutation.mutateAsync({
        notebook_id: selectedNotebookId,
        name: name.trim(),
        item_count: itemCount,
        model_id: modelId === 'default' ? undefined : modelId,
      })
      setJobId(response.job_id)
    } catch {
      // useGenerateStudySet's onError already toasts.
    }
  }, [activeMutation, itemCount, modelId, name, selectedNotebookId, t, toast])

  const isGenerating = !!jobId && !isFailed && jobStatus.data?.status !== 'completed'
  const isSubmitting = activeMutation.isPending || isGenerating

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
          <DialogTitle>{t('study.generateTitle')}</DialogTitle>
          <DialogDescription>{t('study.generateDesc')}</DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-2">
            <Label>{t('study.kindLabel')}</Label>
            <Tabs value={kind} onValueChange={(value) => setKind(value as StudyKind)}>
              <TabsList className="w-full">
                <TabsTrigger value="flashcards" className="flex-1" disabled={isGenerating}>
                  {t('study.kindFlashcards')}
                </TabsTrigger>
                <TabsTrigger value="quiz" className="flex-1" disabled={isGenerating}>
                  {t('study.kindQuiz')}
                </TabsTrigger>
              </TabsList>
            </Tabs>
          </div>

          <div className="space-y-2">
            <Label htmlFor="study_notebook">{t('study.notebookLabel')}</Label>
            {notebooksQuery.isLoading ? (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" /> {t('study.loadingNotebooks')}
              </div>
            ) : notebooks.length === 0 ? (
              <div className="rounded-lg border border-dashed bg-muted/30 p-3 text-sm text-muted-foreground">
                {t('study.noNotebooksDesc')}
              </div>
            ) : (
              <Select
                value={selectedNotebookId}
                onValueChange={setSelectedNotebookId}
                disabled={isGenerating}
              >
                <SelectTrigger id="study_notebook">
                  <SelectValue placeholder={t('study.notebookPlaceholder')} />
                </SelectTrigger>
                <SelectContent>
                  {notebooks.map((notebook) => (
                    <SelectItem key={notebook.id} value={notebook.id}>
                      {notebook.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </div>

          <p className="text-xs text-muted-foreground">{t('study.interleavingHint')}</p>

          <div className="space-y-2">
            <Label htmlFor="study_name">{t('study.nameLabel')}</Label>
            <Input
              id="study_name"
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder={t('study.namePlaceholder')}
              disabled={isGenerating}
              autoComplete="off"
            />
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="study_item_count">{t('study.itemCountLabel')}</Label>
              <Input
                id="study_item_count"
                type="number"
                min={1}
                max={50}
                value={itemCount}
                onChange={(event) => setItemCount(Number(event.target.value) || 1)}
                disabled={isGenerating}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="study_model">{t('study.modelLabel')}</Label>
              <Select value={modelId} onValueChange={setModelId} disabled={isGenerating}>
                <SelectTrigger id="study_model">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="default">{t('study.modelDefault')}</SelectItem>
                  {languageModels.map((model) => (
                    <SelectItem key={model.id} value={model.id}>
                      {model.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {isGenerating ? (
            <div className="flex items-center gap-2 rounded-lg border bg-muted/30 p-3 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              <div>
                <p className="font-medium text-foreground">{t('study.generating')}</p>
                <p className="text-xs">{t('study.generatingDesc')}</p>
              </div>
            </div>
          ) : null}

          {isFailed ? (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                {jobStatus.data?.error_message || t('study.generationFailed')}
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
                {isSubmitting ? t('study.generating') : t('study.generateBtn')}
              </Button>
            )}
            <Button
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={isGenerating}
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
