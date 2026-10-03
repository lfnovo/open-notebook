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

const LIMIT_OPTIONS = [3, 5, 10] as const

export interface DiscoverFormValues {
  query: string
  notebookId: string
  limit: number
  dryRun: boolean
}

interface DiscoverFormProps {
  notebooks: { id: string; name: string }[]
  submitting: boolean
  onSubmit: (values: DiscoverFormValues) => void
}

export function DiscoverForm({
  notebooks,
  submitting,
  onSubmit,
}: DiscoverFormProps) {
  const { t } = useTranslation()
  const [query, setQuery] = useState('')
  const [notebookId, setNotebookId] = useState('')
  const [limit, setLimit] = useState<number>(5)
  const [dryRun, setDryRun] = useState(false)

  const hasNotebooks = notebooks.length > 0
  const canSubmit = hasNotebooks && query.trim().length > 0 && !submitting

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!canSubmit) return
    onSubmit({ query: query.trim(), notebookId, limit, dryRun })
  }

  return (
    <form className="space-y-4" onSubmit={handleSubmit}>
      {!hasNotebooks && (
        <p className="text-sm text-destructive">{t('discover.noNotebooks')}</p>
      )}

      <div className="space-y-2">
        <Label htmlFor="discover-topic">{t('discover.topicLabel')}</Label>
        <Input
          id="discover-topic"
          placeholder={t('discover.topicPlaceholder')}
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor="discover-notebook">{t('discover.notebookLabel')}</Label>
          <Select value={notebookId} onValueChange={setNotebookId}>
            <SelectTrigger id="discover-notebook">
              <SelectValue placeholder={t('discover.notebookPlaceholder')} />
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
          <Label htmlFor="discover-limit">{t('discover.limitLabel')}</Label>
          <Select
            value={String(limit)}
            onValueChange={(value) => setLimit(Number(value))}
          >
            <SelectTrigger id="discover-limit">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {LIMIT_OPTIONS.map((option) => (
                <SelectItem key={option} value={String(option)}>
                  {option}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <Checkbox
          id="discover-dry-run"
          checked={dryRun}
          onCheckedChange={(checked) => setDryRun(checked === true)}
        />
        <Label htmlFor="discover-dry-run">{t('discover.dryRunLabel')}</Label>
      </div>

      <Button type="submit" disabled={!canSubmit}>
        {submitting ? t('discover.submitting') : t('discover.submit')}
      </Button>
    </form>
  )
}
