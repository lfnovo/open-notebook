'use client'

import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Label } from '@/components/ui/label'
import { useModels } from '@/lib/hooks/use-models'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'

interface ModelSelectorProps {
  label?: string
  modelType: 'language' | 'embedding' | 'speech_to_text' | 'text_to_speech'
  value: string
  onChange: (value: string) => void
  placeholder?: string
  disabled?: boolean
}

export function ModelSelector({ 
  label, 
  modelType, 
  value, 
  onChange, 
  placeholder = 'Select a model',
  disabled = false 
}: ModelSelectorProps) {
  const { data: models, isLoading } = useModels()
  
  // Filter models by type
  const filteredModels = models?.filter(model => model.type === modelType) || []
  return (
    <div className="space-y-2">
      {label && <Label>{label}</Label>}
      <Select value={value} onValueChange={onChange} disabled={disabled || isLoading}>
        <SelectTrigger>
          <SelectValue placeholder={placeholder} />
        </SelectTrigger>
        <SelectContent>
          {isLoading ? (
            <div className="flex items-center justify-center py-2">
              <LoadingSpinner size="sm" />
            </div>
          ) : filteredModels.length === 0 ? (
            <div className="text-sm text-muted-foreground py-2 px-2">
              No {modelType.replace('_', ' ')} models available
            </div>
          ) : (
            filteredModels.map((model) => (
              <SelectItem key={model.id} value={model.id}>
                <div className="flex items-center justify-between w-full">
                  <span>{model.name}</span>
                  <span className="text-xs text-muted-foreground ml-2">{model.provider}</span>
                </div>
              </SelectItem>
            ))
          )}
        </SelectContent>
      </Select>
    </div>
  )
}
