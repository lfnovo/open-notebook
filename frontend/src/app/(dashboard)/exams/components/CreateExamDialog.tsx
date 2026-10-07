'use client'

import { useEffect, useId, useMemo, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Loader2, Sparkles } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Checkbox } from '@/components/ui/checkbox'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { useNotebooks } from '@/lib/hooks/use-notebooks'
import { useSources } from '@/lib/hooks/use-sources'
import { useModels } from '@/lib/hooks/use-models'
import { useLanguages } from '@/lib/hooks/use-podcasts'
import { useCreateExam } from '@/lib/hooks/use-exams'
import { useTranslation } from '@/lib/hooks/use-translation'
import { ExamDifficulty } from '@/lib/types/exams'

const DEFAULT_VALUE = '__default__'
const MAX_PER_TYPE = 50

interface CreateExamDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  initialNotebookId?: string
}

function clampCount(value: string) {
  const n = Number.parseInt(value, 10)
  return Number.isNaN(n) ? 0 : Math.min(Math.max(n, 0), MAX_PER_TYPE)
}

export function CreateExamDialog({ open, onOpenChange, initialNotebookId }: CreateExamDialogProps) {
  const { t } = useTranslation()
  const router = useRouter()
  const fieldId = useId()
  const { data: notebooks = [] } = useNotebooks(false)
  const { data: models = [] } = useModels()
  const { data: languages = [] } = useLanguages()
  const createExam = useCreateExam()

  const [notebookId, setNotebookId] = useState(initialNotebookId ?? '')
  const [selectedSources, setSelectedSources] = useState<Set<string>>(new Set())
  const [includeImages, setIncludeImages] = useState(true)
  const [includeNotes, setIncludeNotes] = useState(false)
  const [numMultipleChoice, setNumMultipleChoice] = useState(5)
  const [numMultipleSelect, setNumMultipleSelect] = useState(2)
  const [numFillBlank, setNumFillBlank] = useState(3)
  const [numOpen, setNumOpen] = useState(2)
  const [difficulty, setDifficulty] = useState<ExamDifficulty>('medium')
  const [language, setLanguage] = useState(DEFAULT_VALUE)
  const [modelId, setModelId] = useState(DEFAULT_VALUE)
  const [title, setTitle] = useState('')
  const [instructions, setInstructions] = useState('')

  const { data: sourcesData, isLoading: sourcesLoading } = useSources(notebookId || undefined)
  const sources = useMemo(() => sourcesData ?? [], [sourcesData])
  const languageModels = useMemo(() => models.filter((m) => m.type === 'language'), [models])

  useEffect(() => {
    if (open && initialNotebookId) setNotebookId(initialNotebookId)
  }, [open, initialNotebookId])

  // Select every source of the chosen notebook by default.
  useEffect(() => {
    setSelectedSources(new Set(sources.map((s) => s.id)))
  }, [sources])

  const total = numMultipleChoice + numMultipleSelect + numFillBlank + numOpen
  const canSubmit =
    !!notebookId && total > 0 && (selectedSources.size > 0 || includeNotes) && !createExam.isPending

  const toggleSource = (id: string, checked: boolean) => {
    setSelectedSources((prev) => {
      const next = new Set(prev)
      if (checked) next.add(id)
      else next.delete(id)
      return next
    })
  }

  const handleSubmit = () => {
    const allSelected = selectedSources.size === sources.length
    createExam.mutate({
      notebook_id: notebookId,
      title: title.trim() || undefined,
      source_ids: allSelected ? undefined : Array.from(selectedSources),
      include_notes: includeNotes,
      include_images: includeImages,
      num_multiple_choice: numMultipleChoice,
      num_multiple_select: numMultipleSelect,
      num_fill_blank: numFillBlank,
      num_open: numOpen,
      difficulty,
      language: language === DEFAULT_VALUE ? undefined : language,
      instructions: instructions.trim() || undefined,
      model_id: modelId === DEFAULT_VALUE ? undefined : modelId,
    }, {
      onSuccess: (exam) => {
        onOpenChange(false)
        router.push(`/exams/${encodeURIComponent(exam.id)}`)
      },
    })
  }

  return (
    <Dialog open={open} onOpenChange={(value) => !createExam.isPending && onOpenChange(value)}>
      <DialogContent className="sm:max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{t('exams.newExam')}</DialogTitle>
          <DialogDescription>{t('exams.newExamDesc')}</DialogDescription>
        </DialogHeader>

        <div className="space-y-5">
          <div className="space-y-2">
            <Label htmlFor={`${fieldId}-notebook`}>{t('exams.notebook')}</Label>
            <Select value={notebookId} onValueChange={setNotebookId}>
              <SelectTrigger id={`${fieldId}-notebook`} className="w-full">
                <SelectValue placeholder={t('exams.selectNotebook')} />
              </SelectTrigger>
              <SelectContent>
                {notebooks.map((nb) => (
                  <SelectItem key={nb.id} value={nb.id}>
                    {nb.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {notebookId && (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label>{t('exams.sources')}</Label>
                {sources.length > 0 && (
                  <Button
                    type="button"
                    variant="link"
                    size="sm"
                    className="h-auto p-0"
                    onClick={() =>
                      setSelectedSources(
                        selectedSources.size === sources.length
                          ? new Set()
                          : new Set(sources.map((s) => s.id))
                      )
                    }
                  >
                    {selectedSources.size === sources.length ? t('exams.selectNone') : t('exams.selectAll')}
                  </Button>
                )}
              </div>
              <div className="max-h-48 overflow-y-auto rounded-md border p-3 space-y-2">
                {sourcesLoading && <p className="text-sm text-muted-foreground">{t('common.loading')}</p>}
                {!sourcesLoading && sources.length === 0 && (
                  <p className="text-sm text-muted-foreground">{t('exams.noSources')}</p>
                )}
                {sources.map((source) => (
                  <label key={source.id} className="flex items-center gap-2 text-sm cursor-pointer">
                    <Checkbox
                      checked={selectedSources.has(source.id)}
                      onCheckedChange={(checked) => toggleSource(source.id, checked === true)}
                    />
                    <span className="truncate">{source.title || t('exams.untitledSource')}</span>
                  </label>
                ))}
              </div>
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <Checkbox checked={includeNotes} onCheckedChange={(c) => setIncludeNotes(c === true)} />
                {t('exams.includeNotes')}
              </label>
            </div>
          )}

          <div className="space-y-1">
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <Checkbox checked={includeImages} onCheckedChange={(c) => setIncludeImages(c === true)} />
              {t('exams.includeImages')}
            </label>
            <p className="text-xs text-muted-foreground">{t('exams.imagesHint')}</p>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="space-y-2">
              <Label htmlFor={`${fieldId}-mc`}>{t('exams.types.multiple_choice')}</Label>
              <Input
                id={`${fieldId}-mc`}
                type="number"
                min={0}
                max={MAX_PER_TYPE}
                value={numMultipleChoice}
                onChange={(e) => setNumMultipleChoice(clampCount(e.target.value))}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor={`${fieldId}-ms`}>{t('exams.types.multiple_select')}</Label>
              <Input
                id={`${fieldId}-ms`}
                type="number"
                min={0}
                max={MAX_PER_TYPE}
                value={numMultipleSelect}
                onChange={(e) => setNumMultipleSelect(clampCount(e.target.value))}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor={`${fieldId}-fb`}>{t('exams.types.fill_blank')}</Label>
              <Input
                id={`${fieldId}-fb`}
                type="number"
                min={0}
                max={MAX_PER_TYPE}
                value={numFillBlank}
                onChange={(e) => setNumFillBlank(clampCount(e.target.value))}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor={`${fieldId}-open`}>{t('exams.types.open')}</Label>
              <Input
                id={`${fieldId}-open`}
                type="number"
                min={0}
                max={MAX_PER_TYPE}
                value={numOpen}
                onChange={(e) => setNumOpen(clampCount(e.target.value))}
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor={`${fieldId}-difficulty`}>{t('exams.difficulty')}</Label>
              <Select value={difficulty} onValueChange={(v) => setDifficulty(v as ExamDifficulty)}>
                <SelectTrigger id={`${fieldId}-difficulty`} className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="easy">{t('exams.difficulties.easy')}</SelectItem>
                  <SelectItem value="medium">{t('exams.difficulties.medium')}</SelectItem>
                  <SelectItem value="hard">{t('exams.difficulties.hard')}</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor={`${fieldId}-language`}>{t('exams.language')}</Label>
              <Select value={language} onValueChange={setLanguage}>
                <SelectTrigger id={`${fieldId}-language`} className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={DEFAULT_VALUE}>{t('exams.sameAsSources')}</SelectItem>
                  {languages.map((lang) => (
                    <SelectItem key={lang.code} value={lang.name}>
                      {lang.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor={`${fieldId}-title`}>{t('exams.examTitle')}</Label>
            <Input
              id={`${fieldId}-title`}
              value={title}
              placeholder={t('exams.examTitlePlaceholder')}
              onChange={(e) => setTitle(e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor={`${fieldId}-instructions`}>{t('exams.instructions')}</Label>
            <Textarea
              id={`${fieldId}-instructions`}
              value={instructions}
              rows={3}
              placeholder={t('exams.instructionsPlaceholder')}
              onChange={(e) => setInstructions(e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor={`${fieldId}-model`}>{t('exams.model')}</Label>
            <Select value={modelId} onValueChange={setModelId}>
              <SelectTrigger id={`${fieldId}-model`} className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={DEFAULT_VALUE}>{t('exams.defaultModel')}</SelectItem>
                {languageModels.map((model) => (
                  <SelectItem key={model.id} value={model.id}>
                    {model.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">{t('exams.modelHint')}</p>
          </div>
        </div>

        <DialogFooter className="items-center gap-3">
          {createExam.isPending && (
            <p className="text-sm text-muted-foreground mr-auto">{t('exams.generatingHint')}</p>
          )}
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={createExam.isPending}>
            {t('common.cancel')}
          </Button>
          <Button onClick={handleSubmit} disabled={!canSubmit}>
            {createExam.isPending ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Sparkles className="h-4 w-4 mr-2" />
            )}
            {createExam.isPending ? t('exams.generating') : t('exams.generate', { n: total })}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
