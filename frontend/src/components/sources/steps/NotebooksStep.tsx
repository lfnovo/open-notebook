"use client"

import { FormSection } from "@/components/ui/form-section"
import { useTranslation } from "@/lib/hooks/use-translation"
import { CheckboxList } from "@/components/ui/checkbox-list"
import { ModuleResponse } from "@/lib/types/api"

interface ModulesStepProps {
  modules: ModuleResponse[]
  selectedModules: string[]
  onToggleModule: (moduleId: string) => void
  loading?: boolean
}

export function ModulesStep({
  modules,
  selectedModules,
  onToggleModule,
  loading = false
}: ModulesStepProps) {
  const { t } = useTranslation()
  const moduleItems = modules.map((module) => ({
    id: module.id,
    title: module.name,
    description: module.description || undefined
  }))

  return (
    <div className="space-y-6">
      <FormSection
        title={`${t.modules.title} (${t.common.optional})`}
        description={t.sources.addExistingDesc}
      >
        <CheckboxList
          items={moduleItems}
          selectedIds={selectedModules}
          onToggle={onToggleModule}
          loading={loading}
          emptyMessage={t.sources.noModulesFound}
        />
      </FormSection>
    </div>
  )
}