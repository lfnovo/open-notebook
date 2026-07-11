'use client'

import { useMemo, useState, useEffect } from 'react'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Label } from '@/components/ui/label'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Plus, Loader2, AlertCircle } from 'lucide-react'
import { useTranslation } from '@/lib/hooks/use-translation'
import { useDiscoverModels, useRegisterModels } from '@/lib/hooks/use-credentials'
import { Credential, DiscoveredModel } from '@/lib/api/credentials'
import {
  ModelType,
  PROVIDER_DISPLAY_NAMES,
  PROVIDER_MODALITIES,
  TYPE_ICONS,
  TYPE_LABELS,
} from '@/lib/providers'

interface DiscoverModelsDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  credential: Credential
}

export function DiscoverModelsDialog({
  open,
  onOpenChange,
  credential,
}: DiscoverModelsDialogProps) {
  const { t } = useTranslation()
  const discoverModels = useDiscoverModels()
  const registerModels = useRegisterModels()
  const [discoveredModels, setDiscoveredModels] = useState<DiscoveredModel[]>([])
  const [selectedModels, setSelectedModels] = useState<Set<string>>(new Set())
  const [hasDiscovered, setHasDiscovered] = useState(false)
  const [discoveryError, setDiscoveryError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [customModelSelected, setCustomModelSelected] = useState(false)
  // Model type selector - default to credential's first modality
  const [selectedType, setSelectedType] = useState<ModelType>(
    (credential.modalities[0] as ModelType) || 'language'
  )

  useEffect(() => {
    if (open && !hasDiscovered) {
      setDiscoveryError(null)
      discoverModels.mutate(credential.id, {
        onSuccess: (result) => {
          const seen = new Set<string>()
          const unique = result.discovered.filter(m => {
            if (seen.has(m.name)) return false
            seen.add(m.name)
            return true
          })
          setDiscoveredModels(unique)
          setSelectedModels(new Set())
          setHasDiscovered(true)
        },
        onError: (error: unknown) => {
          setHasDiscovered(true)
          const msg = error instanceof Error ? error.message : String(error)
          setDiscoveryError(msg)
        },
      })
    }
    if (!open) {
      setHasDiscovered(false)
      setDiscoveredModels([])
      setSelectedModels(new Set())
      setDiscoveryError(null)
      setSearchQuery('')
      setCustomModelSelected(false)
      setSelectedType((credential.modalities[0] as ModelType) || 'language')
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- intentionally only fires on open/close
  }, [open])

  // Reset custom selection when search changes
  useEffect(() => {
    setCustomModelSelected(false)
  }, [searchQuery])

  // Filter discovered models by search query
  const filteredModels = useMemo(() => {
    if (!searchQuery.trim()) return discoveredModels
    const q = searchQuery.toLowerCase()
    return discoveredModels.filter(m => m.name.toLowerCase().includes(q))
  }, [discoveredModels, searchQuery])

  // Show custom model option when search doesn't exactly match any discovered model
  const showCustomOption = useMemo(() => {
    if (!searchQuery.trim()) return false
    const q = searchQuery.trim().toLowerCase()
    return !discoveredModels.some(m => m.name.toLowerCase() === q)
  }, [discoveredModels, searchQuery])

  const handleRegister = () => {
    const selected = discoveredModels
      .filter(m => selectedModels.has(m.name))
      .map(m => ({
        name: m.name,
        provider: m.provider,
        model_type: selectedType,
      }))
    if (customModelSelected && showCustomOption) {
      selected.push({
        name: searchQuery.trim(),
        provider: credential.provider,
        model_type: selectedType,
      })
    }
    registerModels.mutate(
      { credentialId: credential.id, models: selected },
      { onSuccess: () => onOpenChange(false) }
    )
  }

  const totalSelected = selectedModels.size + (customModelSelected && showCustomOption ? 1 : 0)

  const toggleModel = (name: string) => {
    setSelectedModels(prev => {
      const next = new Set(prev)
      if (next.has(name)) next.delete(name)
      else next.add(name)
      return next
    })
  }

  const toggleAll = () => {
    const filteredNames = filteredModels.map(m => m.name)
    const allFilteredSelected = filteredNames.every(n => selectedModels.has(n))
    if (allFilteredSelected) {
      setSelectedModels(prev => {
        const next = new Set(prev)
        filteredNames.forEach(n => next.delete(n))
        return next
      })
    } else {
      setSelectedModels(prev => {
        const next = new Set(prev)
        filteredNames.forEach(n => next.add(n))
        return next
      })
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg max-h-[85vh] grid-rows-[auto_1fr_auto]">
        <DialogHeader>
          <DialogTitle>
            {t('models.discoverModels')} - {PROVIDER_DISPLAY_NAMES[credential.provider] || credential.provider}
          </DialogTitle>
          <DialogDescription>
            {credential.name}
          </DialogDescription>
        </DialogHeader>

        <div className="min-h-0 overflow-y-auto">
        {discoverModels.isPending ? (
          <div className="flex items-center justify-center py-12">
            <LoadingSpinner size="lg" />
          </div>
        ) : discoveryError ? (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{discoveryError}</AlertDescription>
          </Alert>
        ) : (
          <div className="space-y-4">
            {/* Model type selector */}
            <div className="space-y-2">
              <Label>{t('models.modelType')}</Label>
              <Select value={selectedType} onValueChange={(v) => setSelectedType(v as ModelType)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {(PROVIDER_MODALITIES[credential.provider] || credential.modalities as ModelType[]).map(type => (
                    <SelectItem key={type} value={type}>
                      <div className="flex items-center gap-2">
                        {TYPE_ICONS[type]}
                        {TYPE_LABELS[type]}
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">{t('models.modelTypeHint')}</p>
            </div>

            {/* Search input */}
            <input
              type="text"
              className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm placeholder:text-muted-foreground"
              placeholder={t('models.searchOrAddModel')}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />

            {/* Select all / count (only when there are discovered models to select) */}
            {filteredModels.length > 0 && (
              <div className="flex items-center justify-between">
                <Button variant="outline" size="sm" onClick={toggleAll}>
                  {filteredModels.every(m => selectedModels.has(m.name)) ? t('common.remove') : t('common.addSelected')}
                  {' '}({selectedModels.size}/{filteredModels.length})
                </Button>
              </div>
            )}

            {/* Model list */}
            <div className="space-y-1">
              {filteredModels.map((model) => (
                <label
                  key={model.name}
                  className="flex items-center gap-2 p-1.5 rounded hover:bg-muted cursor-pointer text-sm"
                >
                  <input
                    type="checkbox"
                    checked={selectedModels.has(model.name)}
                    onChange={() => toggleModel(model.name)}
                    className="rounded"
                  />
                  <span className="truncate">{model.name}</span>
                  {model.description && model.description !== model.name && (
                    <span className="text-xs text-muted-foreground truncate">({model.description})</span>
                  )}
                </label>
              ))}

              {/* Custom model option */}
              {showCustomOption && (
                <label className={`flex items-center gap-2 p-1.5 rounded hover:bg-muted cursor-pointer text-sm${filteredModels.length > 0 ? ' border-t mt-1 pt-2' : ''}`}>
                  <input
                    type="checkbox"
                    checked={customModelSelected}
                    onChange={() => setCustomModelSelected(prev => !prev)}
                    className="rounded"
                  />
                  <Plus className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                  <span className="truncate">
                    {t('models.addCustomModel', { name: searchQuery.trim() })}
                  </span>
                </label>
              )}

              {filteredModels.length === 0 && !showCustomOption && (
                <p className="text-center py-4 text-muted-foreground text-sm">{t('models.noModelsFound')}</p>
              )}
            </div>
          </div>
        )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            {t('common.cancel')}
          </Button>
          <Button
            onClick={handleRegister}
            disabled={totalSelected === 0 || registerModels.isPending}
          >
            {registerModels.isPending && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
            {t('common.add')} ({totalSelected})
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
