'use client'

import { useState } from 'react'
import { ChevronDown, Notebook as NotebookIcon } from 'lucide-react'
import { useTranslation } from '@/lib/hooks/use-translation'
import { useNotebooks } from '@/lib/hooks/use-notebooks'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { CheckboxList } from '@/components/ui/checkbox-list'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'

interface NotebookScopeSelectorProps {
  selectedIds: string[]
  onChange: (ids: string[]) => void
  disabled?: boolean
}

/**
 * Optional notebook scope shared by the Search and Ask tabs (#574, #87).
 * Nothing selected means the whole knowledge base — the historical behavior.
 */
export function NotebookScopeSelector({ selectedIds, onChange, disabled = false }: NotebookScopeSelectorProps) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  const { data: notebooks, isLoading } = useNotebooks(false) // false = not archived

  const items = (notebooks ?? []).map((nb) => ({
    id: nb.id,
    title: nb.name,
    description: nb.description || undefined
  }))

  const handleToggle = (id: string) => {
    if (disabled) return
    onChange(selectedIds.includes(id) ? selectedIds.filter((x) => x !== id) : [...selectedIds, id])
  }

  const summary =
    selectedIds.length === 0
      ? t('searchPage.scopeAllNotebooks')
      : t('searchPage.scopeNotebooksSelected', { count: selectedIds.length })

  return (
    <Collapsible open={open} onOpenChange={setOpen} className="space-y-2" data-testid="notebook-scope">
      <div className="flex items-center justify-between gap-2">
        <CollapsibleTrigger asChild>
          <button
            type="button"
            className="flex items-center gap-2 text-sm font-medium leading-none hover:text-foreground"
            aria-expanded={open}
            disabled={disabled}
          >
            <NotebookIcon className="h-4 w-4" />
            {t('searchPage.scopeNotebooks')}
            <Badge variant={selectedIds.length === 0 ? 'outline' : 'secondary'} className="font-normal">
              {summary}
            </Badge>
            <ChevronDown className={`h-4 w-4 transition-transform ${open ? 'rotate-180' : ''}`} />
          </button>
        </CollapsibleTrigger>
        {selectedIds.length > 0 && (
          <Button
            variant="ghost"
            size="sm"
            className="h-auto py-1 px-2"
            onClick={() => onChange([])}
            disabled={disabled}
          >
            {t('searchPage.scopeClear')}
          </Button>
        )}
      </div>
      <CollapsibleContent className="space-y-2">
        <CheckboxList
          items={items}
          selectedIds={selectedIds}
          onToggle={handleToggle}
          loading={isLoading}
          emptyMessage={t('searchPage.scopeNoNotebooks')}
        />
        <p className="text-xs text-muted-foreground">{t('searchPage.scopeHint')}</p>
      </CollapsibleContent>
    </Collapsible>
  )
}
