'use client'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { ArrowDown, ArrowUp, Plus, X } from 'lucide-react'
import { useTranslation } from '@/lib/hooks/use-translation'
import { Model } from '@/lib/types/models'

// Radix Select reserves "" for "no selection".
const ADD_PLACEHOLDER = '__add__'

interface FallbackChainEditorProps {
  /** All registered models of the type this default slot uses. */
  available: Model[]
  /** The currently selected primary model id for this slot, if any. */
  primaryModelId?: string
  /** Ordered fallback model ids, primary excluded (primary is always first/implicit). */
  fallbackIds: string[]
  onChange: (ids: string[]) => void
  id: string
}

/**
 * Reorderable "try these models, in order, if the primary fails" list.
 * Plain up/down/remove buttons rather than drag-and-drop - no DnD library
 * is in this project's dependencies, and a short list (realistically 1-4
 * entries) doesn't need one.
 */
export function FallbackChainEditor({
  available,
  primaryModelId,
  fallbackIds,
  onChange,
  id,
}: FallbackChainEditorProps) {
  const { t } = useTranslation()

  const byId = new Map(available.map(m => [m.id, m]))
  const addable = available
    .filter(m => m.id !== primaryModelId && !fallbackIds.includes(m.id))
    .sort((a, b) => a.name.localeCompare(b.name))

  const move = (index: number, delta: number) => {
    const next = [...fallbackIds]
    const target = index + delta
    if (target < 0 || target >= next.length) return
    ;[next[index], next[target]] = [next[target], next[index]]
    onChange(next)
  }

  const remove = (index: number) => {
    onChange(fallbackIds.filter((_, i) => i !== index))
  }

  const add = (modelId: string) => {
    if (modelId === ADD_PLACEHOLDER) return
    onChange([...fallbackIds, modelId])
  }

  if (!primaryModelId) {
    return null
  }

  return (
    <div className="space-y-1.5 rounded-md border border-dashed p-2">
      <p className="text-[10px] font-medium text-muted-foreground">
        {t('models.fallbackChainLabel')}
      </p>
      {fallbackIds.length === 0 && (
        <p className="text-[10px] text-muted-foreground italic">
          {t('models.fallbackChainEmpty')}
        </p>
      )}
      {fallbackIds.length > 0 && (
        <ol className="space-y-1">
          {fallbackIds.map((fid, index) => {
            const model = byId.get(fid)
            return (
              <li key={fid} className="flex items-center gap-1.5">
                <Badge variant="secondary" className="shrink-0">{index + 1}</Badge>
                <div className="flex min-w-0 flex-1 items-center justify-between gap-1 text-xs">
                  <span className="truncate" title={model?.name ?? fid}>
                    {model?.name ?? t('models.fallbackChainUnknownModel')}
                  </span>
                  {model && (
                    <span className="shrink-0 text-[10px] text-muted-foreground">{model.provider}</span>
                  )}
                </div>
                <div className="flex shrink-0 items-center">
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6"
                    disabled={index === 0}
                    onClick={() => move(index, -1)}
                    aria-label={t('models.fallbackChainMoveUp')}
                  >
                    <ArrowUp className="h-3 w-3" />
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6"
                    disabled={index === fallbackIds.length - 1}
                    onClick={() => move(index, 1)}
                    aria-label={t('models.fallbackChainMoveDown')}
                  >
                    <ArrowDown className="h-3 w-3" />
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6"
                    onClick={() => remove(index)}
                    aria-label={t('models.fallbackChainRemove')}
                  >
                    <X className="h-3 w-3" />
                  </Button>
                </div>
              </li>
            )
          })}
        </ol>
      )}
      {addable.length > 0 && (
        <Select value={ADD_PLACEHOLDER} onValueChange={add}>
          <SelectTrigger id={id} className="h-7 text-[11px]">
            <span className="flex items-center gap-1 text-muted-foreground">
              <Plus className="h-3 w-3" />
              <SelectValue placeholder={t('models.fallbackChainAdd')} />
            </span>
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ADD_PLACEHOLDER} disabled>
              {t('models.fallbackChainAdd')}
            </SelectItem>
            {addable.map(model => (
              <SelectItem key={model.id} value={model.id}>
                <div className="flex items-center justify-between w-full">
                  <span>{model.name}</span>
                  <span className="text-xs text-muted-foreground ml-2">{model.provider}</span>
                </div>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      )}
    </div>
  )
}
