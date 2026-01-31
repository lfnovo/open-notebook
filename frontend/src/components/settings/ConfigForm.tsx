'use client'

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Checkbox } from '@/components/ui/checkbox'
import { Loader2 } from 'lucide-react'
import { useTranslation } from '@/lib/hooks/use-translation'
import {
  CreateProviderConfigRequest,
  UpdateProviderConfigRequest,
  ProviderCredential,
} from '@/lib/api/api-keys'

interface ConfigFormProps {
  provider: string
  providerDisplayName: string
  config?: ProviderCredential | null // Edit mode when provided
  onSubmit: (data: CreateProviderConfigRequest | UpdateProviderConfigRequest) => void
  onCancel: () => void
  isSubmitting?: boolean
  defaultUrl?: string
}

/**
 * Form component for creating or editing a provider configuration
 */
export function ConfigForm({
  provider,
  providerDisplayName,
  config,
  onSubmit,
  onCancel,
  isSubmitting = false,
  defaultUrl,
}: ConfigFormProps) {
  const { t } = useTranslation()
  const isEditing = !!config

  // Form state
  const [name, setName] = useState('')
  const [apiKey, setApiKey] = useState('')
  const [baseUrl, setBaseUrl] = useState('')
  const [model, setModel] = useState('')
  const [isDefault, setIsDefault] = useState(false)
  const [showApiKey, setShowApiKey] = useState(false)

  // Initialize form with config data in edit mode
  useEffect(() => {
    if (config) {
      setName(config.name || '')
      setBaseUrl(config.base_url || defaultUrl || '')
      setModel(config.model || '')
      setIsDefault(config.is_default)
      // API key is never returned from API (security), so leave empty
      setApiKey('')
    } else {
      // New config - use defaults
      setName('')
      setBaseUrl(defaultUrl || '')
      setModel('')
      setIsDefault(false)
      setApiKey('')
    }
  }, [config, defaultUrl])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    if (isEditing) {
      // Update request - only include changed fields
      const updateData: UpdateProviderConfigRequest = {}

      if (name !== config.name) {
        updateData.name = name
      }
      if (baseUrl !== (config.base_url || '') && baseUrl !== (defaultUrl || '')) {
        updateData.base_url = baseUrl
      }
      if (model !== (config.model || '')) {
        updateData.model = model
      }
      if (apiKey.trim()) {
        updateData.api_key = apiKey.trim()
      }
      if (isDefault !== config.is_default) {
        // Handle default status separately
      }

      onSubmit(updateData)
    } else {
      // Create request
      const createData: CreateProviderConfigRequest = {
        name: name || `${providerDisplayName} Config`,
        api_key: apiKey.trim() || undefined,
        base_url: baseUrl || defaultUrl || undefined,
        model: model || undefined,
        is_default: isDefault,
      }

      onSubmit(createData)
    }
  }

  const isValid = isEditing
    ? true // In edit mode, we can submit with no changes (for setting default)
    : name.trim() !== '' && apiKey.trim() !== '' // In create mode, need name and api_key

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {/* Config name */}
      <div className="space-y-2">
        <Label htmlFor="config-name">{t.apiKeys.configName}</Label>
        <Input
          id="config-name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder={`${providerDisplayName} Production`}
          disabled={isSubmitting}
        />
        <p className="text-xs text-muted-foreground">
          {t.apiKeys.configNameHint}
        </p>
      </div>

      {/* API Key */}
      <div className="space-y-2">
        <Label htmlFor="api-key">{t.models.apiKey}</Label>
        <div className="relative">
          <Input
            id="api-key"
            type={showApiKey ? 'text' : 'password'}
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder={isEditing ? '••••••••••••' : 'sk-...'}
            disabled={isSubmitting}
            className="pr-10"
            autoComplete="off"
          />
          <button
            type="button"
            onClick={() => setShowApiKey(!showApiKey)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
            tabIndex={-1}
          >
            {showApiKey ? (
              <span className="text-xs">Hide</span>
            ) : (
              <span className="text-xs">Show</span>
            )}
          </button>
        </div>
        {!isEditing && (
          <p className="text-xs text-muted-foreground">
            {t.apiKeys.apiKeyHint}
          </p>
        )}
        {isEditing && (
          <p className="text-xs text-muted-foreground">
            {t.apiKeys.apiKeyEditHint}
          </p>
        )}
      </div>

      {/* Base URL */}
      <div className="space-y-2">
        <Label htmlFor="base-url">{t.apiKeys.baseUrl}</Label>
        <Input
          id="base-url"
          type="url"
          value={baseUrl}
          onChange={(e) => setBaseUrl(e.target.value)}
          placeholder={defaultUrl || 'https://api.example.com/v1'}
          disabled={isSubmitting}
        />
        {defaultUrl && (
          <p className="text-xs text-muted-foreground">
            {t.apiKeys.baseUrlHint.replace('{url}', defaultUrl)}
          </p>
        )}
      </div>

      {/* Default model */}
      <div className="space-y-2">
        <Label htmlFor="model">{t.apiKeys.defaultModel}</Label>
        <Input
          id="model"
          value={model}
          onChange={(e) => setModel(e.target.value)}
          placeholder="gpt-4, gpt-3.5-turbo, etc."
          disabled={isSubmitting}
        />
        <p className="text-xs text-muted-foreground">
          {t.apiKeys.defaultModelHint}
        </p>
      </div>

      {/* Set as default checkbox */}
      <div className="flex items-center space-x-2">
        <Checkbox
          id="is-default"
          checked={isDefault}
          onCheckedChange={(checked) => setIsDefault(checked as boolean)}
          disabled={isSubmitting}
        />
        <Label htmlFor="is-default" className="cursor-pointer">
          {t.apiKeys.setAsDefault}
        </Label>
      </div>

      {/* Form actions */}
      <div className="flex justify-end gap-2 pt-4 border-t">
        <Button type="button" variant="outline" onClick={onCancel} disabled={isSubmitting}>
          {t.common.cancel}
        </Button>
        <Button type="submit" disabled={!isValid || isSubmitting}>
          {isSubmitting && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
          {isEditing ? t.common.save : t.apiKeys.addConfig}
        </Button>
      </div>
    </form>
  )
}
