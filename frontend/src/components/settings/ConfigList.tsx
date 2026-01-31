'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Trash2,
  Edit,
  Star,
  StarOff,
  Plus,
  AlertTriangle,
  Check,
  X,
  Loader2,
  Plug,
  RefreshCw,
} from 'lucide-react'
import { useTranslation } from '@/lib/hooks/use-translation'
import { ProviderCredential } from '@/lib/api/api-keys'
import {
  useDeleteProviderConfig,
  useSetProviderDefault,
  useTestConnection,
  useSyncModels,
  useProviderModelCount,
} from '@/lib/hooks/use-api-keys'

interface ConfigListProps {
  provider: string
  providerDisplayName: string
  configs: ProviderCredential[]
  onAddConfig: () => void
  onEditConfig: (configId: string) => void
  isLoading?: boolean
}

/**
 * Component to display and manage a list of provider configurations
 */
export function ConfigList({
  provider,
  providerDisplayName,
  configs,
  onAddConfig,
  onEditConfig,
  isLoading = false,
}: ConfigListProps) {
  const { t } = useTranslation()
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false)
  const [configToDelete, setConfigToDelete] = useState<ProviderCredential | null>(null)
  const [setDefaultConfirmOpen, setSetDefaultConfirmOpen] = useState(false)
  const [configToSetDefault, setConfigToSetDefault] = useState<ProviderCredential | null>(null)

  const deleteConfig = useDeleteProviderConfig()
  const setDefault = useSetProviderDefault()
  const { testConnection, isPending: isTestPending, testResults } = useTestConnection()
  const syncModels = useSyncModels()
  const { data: modelCount } = useProviderModelCount(provider)
  const totalModels = modelCount?.total || 0

  const handleDeleteClick = (config: ProviderCredential) => {
    setConfigToDelete(config)
    setDeleteConfirmOpen(true)
  }

  const handleDeleteConfirm = () => {
    if (configToDelete) {
      deleteConfig.mutate(
        { provider, configId: configToDelete.id },
        {
          onSuccess: () => {
            setDeleteConfirmOpen(false)
            setConfigToDelete(null)
          },
        }
      )
    }
  }

  const handleSetDefaultClick = (config: ProviderCredential) => {
    setConfigToSetDefault(config)
    setSetDefaultConfirmOpen(true)
  }

  const handleSetDefaultConfirm = () => {
    if (configToSetDefault) {
      setDefault.mutate(
        { provider, configId: configToSetDefault.id },
        {
          onSuccess: () => {
            setSetDefaultConfirmOpen(false)
            setConfigToSetDefault(null)
          },
        }
      )
    }
  }

  const handleTestConnection = (configId: string) => {
    testConnection(`${provider}:${configId}`)
  }

  const getTestResult = (configId: string) => {
    const key = `${provider}:${configId}`
    return testResults[key]
  }

  if (isLoading) {
    return (
      <div className="space-y-3">
        <div className="animate-pulse space-y-2">
          <div className="h-16 bg-muted rounded-md" />
          <div className="h-16 bg-muted rounded-md" />
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {/* Empty state */}
      {configs.length === 0 ? (
        <div className="text-center py-8 border-2 border-dashed rounded-lg">
          <p className="text-muted-foreground mb-3">{t.apiKeys.noConfigs}</p>
          <p className="text-sm text-muted-foreground mb-4">
            {t.apiKeys.noConfigsHint}
          </p>
          <Button onClick={onAddConfig} variant="outline" className="gap-2">
            <Plus className="h-4 w-4" />
            {t.apiKeys.addConfig}
          </Button>
        </div>
      ) : (
        <>
          {/* Config list */}
          <div className="space-y-2">
            {configs.map((config) => {
              const testResult = getTestResult(config.id)
              const isDeleting = deleteConfig.isPending
              const isSettingDefault = setDefault.isPending

              return (
                <div
                  key={config.id}
                  className={`flex items-center gap-3 p-3 rounded-lg border bg-card ${
                    config.is_default
                      ? 'border-primary/50 ring-1 ring-primary/20'
                      : ''
                  }`}
                >
                  {/* Default indicator */}
                  {config.is_default ? (
                    <Badge
                      variant="default"
                      className="bg-primary/10 text-primary hover:bg-primary/10 gap-1 shrink-0"
                    >
                      <Star className="h-3 w-3" />
                      {t.apiKeys.defaultBadge}
                    </Badge>
                  ) : (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="shrink-0"
                      onClick={() => handleSetDefaultClick(config)}
                      disabled={isSettingDefault}
                      title={t.apiKeys.setAsDefault}
                    >
                      <StarOff className="h-4 w-4 text-muted-foreground" />
                    </Button>
                  )}

                  {/* Config info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium truncate">{config.name}</span>
                      {config.model && (
                        <Badge variant="secondary" className="text-xs shrink-0">
                          {config.model}
                        </Badge>
                      )}
                      {config.base_url && (
                        <span className="text-xs text-muted-foreground truncate shrink-0">
                          {config.base_url}
                        </span>
                      )}
                    </div>
                    {config.is_default && (
                      <p className="text-xs text-muted-foreground">
                        {t.apiKeys.defaultDescription}
                      </p>
                    )}
                  </div>

                  {/* Test connection result */}
                  {testResult && (
                    <div className="shrink-0">
                      {testResult.success ? (
                        <Check className="h-4 w-4 text-emerald-500" />
                      ) : (
                        <X className="h-4 w-4 text-destructive" />
                      )}
                    </div>
                  )}

                  {/* Actions */}
                  <div className="flex items-center gap-1 shrink-0">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleTestConnection(config.id)}
                      disabled={isTestPending}
                      title={t.apiKeys.testConnection}
                    >
                      {isTestPending ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : testResult?.success === true ? (
                        <Check className="h-4 w-4 text-emerald-500" />
                      ) : testResult?.success === false ? (
                        <X className="h-4 w-4 text-destructive" />
                      ) : (
                        <Plug className="h-4 w-4" />
                      )}
                    </Button>

                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => onEditConfig(config.id)}
                      disabled={isDeleting || isSettingDefault}
                      title={t.common.edit}
                    >
                      <Edit className="h-4 w-4" />
                    </Button>

                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDeleteClick(config)}
                      disabled={isDeleting || isSettingDefault}
                      className="text-destructive hover:text-destructive hover:bg-destructive/10"
                      title={t.common.delete}
                    >
                      {isDeleting ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Trash2 className="h-4 w-4" />
                      )}
                    </Button>
                  </div>
                </div>
              )
            })}
          </div>

          {/* Add config button */}
          <Button
            variant="outline"
            size="sm"
            onClick={onAddConfig}
            className="w-full gap-2 mt-2"
          >
            <Plus className="h-4 w-4" />
            {t.apiKeys.addConfig}
          </Button>

          {/* Actions footer with sync and model count */}
          <div className="flex items-center gap-2 pt-2 border-t mt-4">
            <Button
              variant="outline"
              size="sm"
              onClick={() => syncModels.mutate(provider)}
              disabled={syncModels.isPending}
              className="gap-1.5"
            >
              {syncModels.isPending ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <RefreshCw className="h-3.5 w-3.5" />
              )}
              {syncModels.isPending ? t.apiKeys.syncing : t.apiKeys.syncModels}
            </Button>
            {totalModels > 0 && (
              <Badge variant="secondary" className="ml-auto">
                {t.apiKeys.modelsConfigured.replace('{count}', totalModels.toString())}
              </Badge>
            )}
          </div>
        </>
      )}

      {/* Delete confirmation dialog */}
      <Dialog open={deleteConfirmOpen} onOpenChange={setDeleteConfirmOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t.apiKeys.deleteConfig}</DialogTitle>
            <DialogDescription>
              {t.apiKeys.deleteConfigConfirm.replace(
                '{name}',
                configToDelete?.name || ''
              )}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteConfirmOpen(false)}>
              {t.common.cancel}
            </Button>
            <Button
              variant="destructive"
              onClick={handleDeleteConfirm}
              disabled={deleteConfig.isPending}
            >
              {deleteConfig.isPending && (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              )}
              {t.common.delete}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Set default confirmation dialog */}
      <Dialog open={setDefaultConfirmOpen} onOpenChange={setSetDefaultConfirmOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t.apiKeys.setAsDefault}</DialogTitle>
            <DialogDescription>
              {t.apiKeys.setDefaultConfirm.replace(
                '{name}',
                configToSetDefault?.name || ''
              )}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setSetDefaultConfirmOpen(false)}>
              {t.common.cancel}
            </Button>
            <Button
              onClick={handleSetDefaultConfirm}
              disabled={setDefault.isPending}
            >
              {setDefault.isPending && (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              )}
              {t.common.confirm}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
