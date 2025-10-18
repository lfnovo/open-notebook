'use client'

import { Model, ProviderAvailability } from '@/lib/types/models'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { AddModelForm } from './AddModelForm'
import { Bot, Mic, Volume2, Search, Trash2, X, ChevronDown, ChevronUp } from 'lucide-react'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { useDeleteModel } from '@/lib/hooks/use-models'
import { ConfirmDialog } from '@/components/common/ConfirmDialog'
import { useState, useMemo } from 'react'

interface ModelTypeSectionProps {
  type: 'language' | 'embedding' | 'text_to_speech' | 'speech_to_text'
  models: Model[]
  providers: ProviderAvailability
  isLoading: boolean
}

const COLLAPSED_ITEM_COUNT = 5

export function ModelTypeSection({ type, models, providers, isLoading }: ModelTypeSectionProps) {
  const [deleteModel, setDeleteModel] = useState<Model | null>(null)
  const [selectedProvider, setSelectedProvider] = useState<string | null>(null)
  const [isExpanded, setIsExpanded] = useState(false)
  const deleteModelMutation = useDeleteModel()

  const getTypeInfo = () => {
    switch (type) {
      case 'language':
        return {
          title: 'Language Models',
          description: 'Chat, transformations, and text generation',
          icon: Bot,
          iconColor: 'text-blue-500',
          bgColor: 'bg-blue-50 dark:bg-blue-950/20'
        }
      case 'embedding':
        return {
          title: 'Embedding Models',
          description: 'Semantic search and vector embeddings',
          icon: Search,
          iconColor: 'text-green-500',
          bgColor: 'bg-green-50 dark:bg-green-950/20'
        }
      case 'text_to_speech':
        return {
          title: 'Text-to-Speech',
          description: 'Generate audio from text',
          icon: Volume2,
          iconColor: 'text-purple-500',
          bgColor: 'bg-purple-50 dark:bg-purple-950/20'
        }
      case 'speech_to_text':
        return {
          title: 'Speech-to-Text',
          description: 'Transcribe audio to text',
          icon: Mic,
          iconColor: 'text-orange-500',
          bgColor: 'bg-orange-50 dark:bg-orange-950/20'
        }
    }
  }

  const { title, description, icon: Icon, iconColor, bgColor } = getTypeInfo()
  
  // Filter and sort models
  const filteredModels = useMemo(() => {
    let filtered = models.filter(model => model.type === type)
    
    // Apply provider filter if selected
    if (selectedProvider) {
      filtered = filtered.filter(model => model.provider === selectedProvider)
    }
    
    // Sort by name alphabetically
    return filtered.sort((a, b) => a.name.localeCompare(b.name))
  }, [models, type, selectedProvider])

  // Get unique providers for this model type
  const modelProviders = useMemo(() => {
    const typeModels = models.filter(model => model.type === type)
    const uniqueProviders = [...new Set(typeModels.map(m => m.provider))]
    return uniqueProviders.sort()
  }, [models, type])

  const handleDelete = () => {
    if (deleteModel) {
      deleteModelMutation.mutate(deleteModel.id)
      setDeleteModel(null)
    }
  }

  return (
    <>
      <Card className="h-full">
        <CardHeader className="pb-3">
          <div className="flex items-start justify-between gap-2">
            <div className="flex items-center gap-3">
              <div className={`rounded-lg p-2 ${bgColor}`}>
                <Icon className={`h-5 w-5 ${iconColor}`} />
              </div>
              <div>
                <CardTitle className="text-base">{title}</CardTitle>
                <CardDescription className="text-xs">{description}</CardDescription>
              </div>
            </div>
            <AddModelForm modelType={type} providers={providers} />
          </div>
        </CardHeader>
        <CardContent className="pt-0">
          {/* Provider filter badges */}
          {modelProviders.length > 1 && (
            <div className="flex flex-wrap gap-1 mb-3">
              <Badge
                variant={selectedProvider === null ? "default" : "outline"}
                className="cursor-pointer text-xs"
                onClick={() => setSelectedProvider(null)}
              >
                All
              </Badge>
              {modelProviders.map(provider => (
                <Badge
                  key={provider}
                  variant={selectedProvider === provider ? "default" : "outline"}
                  className="cursor-pointer text-xs capitalize"
                  onClick={() => setSelectedProvider(provider === selectedProvider ? null : provider)}
                >
                  {provider}
                  {selectedProvider === provider && (
                    <X className="ml-1 h-2.5 w-2.5" />
                  )}
                </Badge>
              ))}
            </div>
          )}

          {isLoading ? (
            <div className="flex items-center justify-center py-6">
              <LoadingSpinner />
            </div>
          ) : filteredModels.length === 0 ? (
            <div className="text-center py-6 text-sm text-muted-foreground">
              {selectedProvider 
                ? `No ${selectedProvider} models configured`
                : 'No models configured'
              }
            </div>
          ) : (
            <div className="space-y-2">
              <div className={`space-y-2 ${!isExpanded && filteredModels.length > COLLAPSED_ITEM_COUNT ? 'max-h-[280px] overflow-hidden relative' : ''}`}>
                {filteredModels.slice(0, isExpanded ? undefined : COLLAPSED_ITEM_COUNT).map(model => (
                  <div key={model.id} className="flex items-center gap-2 group">
                    <div className="flex-1 flex items-center gap-2 px-3 py-2 rounded-md border bg-muted/30">
                      <span className="font-medium text-sm">{model.name}</span>
                      <Badge variant="outline" className="text-xs">
                        {model.provider}
                      </Badge>
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 opacity-0 group-hover:opacity-100 transition-opacity"
                      onClick={() => setDeleteModel(model)}
                    >
                      <Trash2 className="h-3.5 w-3.5 text-muted-foreground hover:text-destructive" />
                    </Button>
                  </div>
                ))}
                {!isExpanded && filteredModels.length > COLLAPSED_ITEM_COUNT && (
                  <div className="absolute bottom-0 left-0 right-0 h-20 bg-gradient-to-t from-background to-transparent pointer-events-none" />
                )}
              </div>
              {filteredModels.length > COLLAPSED_ITEM_COUNT && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setIsExpanded(!isExpanded)}
                  className="w-full mt-2"
                >
                  {isExpanded ? (
                    <>
                      <ChevronUp className="h-4 w-4 mr-2" />
                      Show less
                    </>
                  ) : (
                    <>
                      <ChevronDown className="h-4 w-4 mr-2" />
                      Show {filteredModels.length - COLLAPSED_ITEM_COUNT} more
                    </>
                  )}
                </Button>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      <ConfirmDialog
        open={!!deleteModel}
        onOpenChange={(open) => !open && setDeleteModel(null)}
        title="Delete Model"
        description={`Are you sure you want to delete "${deleteModel?.name}"? This action cannot be undone.`}
        confirmText="Delete"
        confirmVariant="destructive"
        onConfirm={handleDelete}
      />
    </>
  )
}