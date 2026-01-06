"use client"

import { FormSection } from "@/components/ui/form-section"
import { useTranslation } from "@/lib/hooks/use-translation"
import { CheckboxList } from "@/components/ui/checkbox-list"
import { NotebookResponse } from "@/lib/types/api"

interface NotebooksStepProps {
  notebooks: NotebookResponse[]
  selectedNotebooks: string[]
  onToggleNotebook: (notebookId: string) => void
  loading?: boolean
}

export function NotebooksStep({
  notebooks,
  selectedNotebooks,
  onToggleNotebook,
  loading = false
}: NotebooksStepProps) {
  const { t } = useTranslation()
  const notebookItems = notebooks.map((notebook) => ({
    id: notebook.id,
    title: notebook.name,
    description: notebook.description || undefined
  }))

  return (
    <div className="space-y-6">
      <FormSection
        title={`${t.notebooks.title} (${t.common.optional})`}
        description={t.sources.addExistingDesc}
      >
        <CheckboxList
          items={notebookItems}
          selectedIds={selectedNotebooks}
          onToggle={onToggleNotebook}
          loading={loading}
          emptyMessage={t.sources.noNotebooksFound}
        />
      </FormSection>
    </div>
  )
}