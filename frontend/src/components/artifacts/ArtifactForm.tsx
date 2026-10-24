'use client'

import { FormEvent, useState } from 'react'

import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useTranslation } from '@/lib/hooks/use-translation'
import { useArtifactFormStore } from '@/lib/stores/artifact-form-store'
import {
  ARTIFACT_VARIANTS,
  type ArtifactFormat,
  type ArtifactKind,
  type ArtifactVariant,
} from '@/lib/types/artifacts'

const KIND_OPTIONS: ArtifactKind[] = ['report', 'deck']

/**
 * i18n key per variant, spelled out instead of built from the variant name:
 * the locale lint scans source files for literal keys, so a computed key would
 * look unused and its translation would be dropped at the next cleanup.
 */
const VARIANT_LABEL_KEY: Record<ArtifactVariant, string> = {
  document: 'artifacts.variantDocument',
  illustrated: 'artifacts.variantIllustrated',
  presenter: 'artifacts.variantPresenter',
  detailed: 'artifacts.variantDetailed',
}

const FORMAT_OPTIONS: ArtifactFormat[] = ['md', 'html', 'docx', 'pptx']
const LANGUAGE_OPTIONS = [
  'en',
  'it',
  'es',
  'fr',
  'de',
  'pt',
  'zh',
  'ja',
  'ru',
  'pl',
  'tr',
  'ca',
  'bn',
] as const
const SECTION_OPTIONS = [3, 5, 8] as const
const SUPPORTED_LANGUAGES: readonly string[] = LANGUAGE_OPTIONS

export function defaultArtifactLanguage(uiLanguage: string): string {
  const base = (uiLanguage || '').split('-')[0].toLowerCase()
  return SUPPORTED_LANGUAGES.includes(base) ? base : 'en'
}

export interface ArtifactFormValues {
  notebookId: string
  kind: ArtifactKind
  variant: ArtifactVariant
  title: string
  formats: ArtifactFormat[]
  language: string
  sections: number
}

interface ArtifactFormProps {
  notebooks: { id: string; name: string }[]
  submitting: boolean
  onSubmit: (values: ArtifactFormValues) => void
}

function toggleFormat(current: ArtifactFormat[], format: ArtifactFormat) {
  return current.includes(format)
    ? current.filter((item) => item !== format)
    : [...current, format]
}

export function ArtifactForm({
  notebooks,
  submitting,
  onSubmit,
}: ArtifactFormProps) {
  const { t, language: uiLanguage } = useTranslation()
  const [notebookId, setNotebookId] = useState('')
  const kind = useArtifactFormStore((state) => state.kind)
  const setKind = useArtifactFormStore((state) => state.setKind)
  const variant = useArtifactFormStore((state) => state.variant)
  const setVariant = useArtifactFormStore((state) => state.setVariant)
  const [title, setTitle] = useState('')
  const [formats, setFormats] = useState<ArtifactFormat[]>(['md', 'docx'])
  const [language, setLanguage] = useState(() =>
    defaultArtifactLanguage(uiLanguage)
  )
  const [sections, setSections] = useState<number>(5)

  const hasNotebooks = notebooks.length > 0
  const canSubmit = hasNotebooks && formats.length > 0 && !submitting
  const variantOptions = ARTIFACT_VARIANTS[kind]

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!canSubmit) return
    onSubmit({
      notebookId,
      kind,
      variant,
      title: title.trim(),
      formats,
      language,
      sections,
    })
  }

  return (
    <form className="space-y-4" onSubmit={handleSubmit}>
      {!hasNotebooks && (
        <p className="text-sm text-destructive">{t('artifacts.noNotebooks')}</p>
      )}

      <div className="grid gap-4 sm:grid-cols-3">
        <div className="space-y-2">
          <Label htmlFor="artifact-notebook">{t('artifacts.notebookLabel')}</Label>
          <Select value={notebookId} onValueChange={setNotebookId}>
            <SelectTrigger id="artifact-notebook" className="w-full">
              <SelectValue placeholder={t('artifacts.notebookPlaceholder')} />
            </SelectTrigger>
            <SelectContent>
              {notebooks.map((notebook) => (
                <SelectItem key={notebook.id} value={notebook.id}>
                  {notebook.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label htmlFor="artifact-kind">{t('artifacts.kindLabel')}</Label>
          <Select
            value={kind}
            onValueChange={(value) => setKind(value as ArtifactKind)}
          >
            <SelectTrigger id="artifact-kind" className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {KIND_OPTIONS.map((option) => (
                <SelectItem key={option} value={option}>
                  {option === 'deck'
                    ? t('artifacts.kindDeck')
                    : t('artifacts.kindReport')}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label htmlFor="artifact-variant">{t('artifacts.variantLabel')}</Label>
          <Select
            value={variant}
            onValueChange={(value) => setVariant(value as ArtifactVariant)}
          >
            <SelectTrigger id="artifact-variant" className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {variantOptions.map((option) => (
                <SelectItem key={option} value={option}>
                  {t(VARIANT_LABEL_KEY[option])}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="artifact-title">{t('artifacts.titleLabel')}</Label>
        <Input
          id="artifact-title"
          placeholder={t('artifacts.titlePlaceholder')}
          value={title}
          onChange={(event) => setTitle(event.target.value)}
        />
      </div>

      <div className="space-y-2">
        <Label>{t('artifacts.formatsLabel')}</Label>
        <div className="flex flex-wrap gap-4">
          {FORMAT_OPTIONS.map((format) => (
            <div key={format} className="flex items-center gap-2">
              <Checkbox
                id={`artifact-format-${format}`}
                checked={formats.includes(format)}
                onCheckedChange={() =>
                  setFormats((current) => toggleFormat(current, format))
                }
              />
              <Label htmlFor={`artifact-format-${format}`}>
                {format.toUpperCase()}
              </Label>
            </div>
          ))}
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor="artifact-language">{t('artifacts.languageLabel')}</Label>
          <Select value={language} onValueChange={setLanguage}>
            <SelectTrigger id="artifact-language" className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {LANGUAGE_OPTIONS.map((option) => (
                <SelectItem key={option} value={option}>
                  {option.toUpperCase()}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label htmlFor="artifact-sections">{t('artifacts.sectionsLabel')}</Label>
          <Select
            value={String(sections)}
            onValueChange={(value) => setSections(Number(value))}
          >
            <SelectTrigger id="artifact-sections" className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {SECTION_OPTIONS.map((option) => (
                <SelectItem key={option} value={String(option)}>
                  {option}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      <Button type="submit" disabled={!canSubmit}>
        {submitting ? t('artifacts.submitting') : t('artifacts.submit')}
      </Button>
    </form>
  )
}
