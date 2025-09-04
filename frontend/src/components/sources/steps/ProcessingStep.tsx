"use client"

import { Control, Controller } from "react-hook-form"
import { FormSection } from "@/components/ui/form-section"
import { CheckboxList } from "@/components/ui/checkbox-list"
import { Checkbox } from "@/components/ui/checkbox"
import { Transformation } from "@/lib/types/transformations"

interface CreateSourceFormData {
  type: 'link' | 'upload' | 'text'
  title?: string
  url?: string
  content?: string
  file?: FileList | File
  notebooks?: string[]
  transformations?: string[]
  embed: boolean
  async_processing: boolean
}

interface ProcessingStepProps {
  control: Control<CreateSourceFormData>
  transformations: Transformation[]
  selectedTransformations: string[]
  onToggleTransformation: (transformationId: string) => void
  loading?: boolean
}

export function ProcessingStep({
  control,
  transformations,
  selectedTransformations,
  onToggleTransformation,
  loading = false
}: ProcessingStepProps) {
  const transformationItems = transformations.map((transformation) => ({
    id: transformation.id,
    title: transformation.title,
    description: transformation.description
  }))

  return (
    <div className="space-y-8">
      <FormSection
        title="Transformations (optional)"
        description="Apply AI transformations to analyze and extract insights from your content."
      >
        <CheckboxList
          items={transformationItems}
          selectedIds={selectedTransformations}
          onToggle={onToggleTransformation}
          loading={loading}
          emptyMessage="No transformations found."
        />
      </FormSection>

      <FormSection
        title="Processing Settings"
        description="Configure how your source will be processed and stored."
      >
        <div className="space-y-4">
          <Controller
            control={control}
            name="embed"
            render={({ field }) => (
              <label className="flex items-start gap-3 cursor-pointer p-3 rounded-md hover:bg-gray-50">
                <Checkbox
                  checked={field.value}
                  onCheckedChange={field.onChange}
                  className="mt-0.5"
                />
                <div className="flex-1">
                  <span className="text-sm font-medium block">Enable embedding for search</span>
                  <p className="text-xs text-gray-600 mt-1">
                    Allows this source to be found in vector searches and AI queries
                  </p>
                </div>
              </label>
            )}
          />
        </div>
      </FormSection>
    </div>
  )
}