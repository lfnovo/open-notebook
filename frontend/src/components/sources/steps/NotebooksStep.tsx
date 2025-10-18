"use client"

import { FormSection } from "@/components/ui/form-section"
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
  const notebookItems = notebooks.map((notebook) => ({
    id: notebook.id,
    title: notebook.name,
    description: notebook.description || undefined
  }))

  return (
    <div className="space-y-6">
      <FormSection
        title="Select Notebooks (optional)"
        description="Choose which notebooks should contain this source. You can select multiple notebooks or leave this empty."
      >
        <CheckboxList
          items={notebookItems}
          selectedIds={selectedNotebooks}
          onToggle={onToggleNotebook}
          loading={loading}
          emptyMessage="No notebooks found."
        />
      </FormSection>
    </div>
  )
}