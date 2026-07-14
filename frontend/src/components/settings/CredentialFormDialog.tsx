'use client'

import { useState, useEffect, useMemo } from 'react'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Loader2 } from 'lucide-react'
import { useTranslation } from '@/lib/hooks/use-translation'
import { useCreateCredential, useUpdateCredential } from '@/lib/hooks/use-credentials'
import { Credential, CreateCredentialRequest } from '@/lib/api/credentials'
import { buildCredentialUpdatePayload } from '@/lib/credential-update-payload'
import { useProviders } from '@/lib/hooks/use-providers'

interface CredentialFormDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  provider: string
  credential?: Credential | null
}

export function CredentialFormDialog({
  open,
  onOpenChange,
  provider,
  credential,
}: CredentialFormDialogProps) {
  const { t } = useTranslation()
  const createCredential = useCreateCredential()
  const updateCredential = useUpdateCredential()
  const { data: providers } = useProviders()
  const providerInfo = useMemo(
    () => providers?.find(p => p.name === provider),
    [providers, provider]
  )
  const providerDisplayName = providerInfo?.display_name || provider
  const isEditing = !!credential
  const isSubmitting = createCredential.isPending || updateCredential.isPending

  const isVertex = provider === 'vertex'
  const isOllama = provider === 'ollama'
  const isOpenAICompatible = provider === 'openai_compatible'
  const requiresApiKey = !isVertex && !isOllama && !isOpenAICompatible

  const [name, setName] = useState('')
  const [apiKey, setApiKey] = useState('')
  const [baseUrl, setBaseUrl] = useState('')
  const [showApiKey, setShowApiKey] = useState(false)
  const [project, setProject] = useState('')
  const [location, setLocation] = useState('')
  const [credentialsPath, setCredentialsPath] = useState('')
  const [numCtx, setNumCtx] = useState('')
  // Modalities
  const [modalities, setModalities] = useState<string[]>([])

  useEffect(() => {
    if (credential) {
      setName(credential.name || '')
      setBaseUrl(credential.base_url || '')
      setApiKey('')
      setProject(credential.project || '')
      setLocation(credential.location || '')
      setCredentialsPath(credential.credentials_path || '')
      setNumCtx(credential.num_ctx ? String(credential.num_ctx) : '')
      setModalities(credential.modalities || [])
    } else {
      setName('')
      setBaseUrl('')
      setApiKey('')
      setProject('')
      setLocation('')
      setCredentialsPath('')
      setNumCtx('')
      setModalities(providerInfo?.modalities ?? ['language'])
    }
    // providerInfo keeps a stable reference for a given provider (react-query
    // caches the list for the whole session), so this only re-runs when the
    // dialog target or the fetched registry actually changes.
  }, [credential, provider, providerInfo])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    const onSuccess = () => {
      onOpenChange(false)
    }

    if (isEditing && credential) {
      const data = buildCredentialUpdatePayload(credential, {
        name, apiKey, baseUrl, modalities, project, location,
        credentialsPath, numCtx, isVertex, isOllama,
      })
      updateCredential.mutate({ credentialId: credential.id, data }, { onSuccess })
    } else {
      const data: CreateCredentialRequest = {
        name: name || `${providerDisplayName} Config`,
        provider,
        modalities,
        api_key: apiKey.trim() || undefined,
        base_url: baseUrl || undefined,
      }
      if (isVertex) {
        data.project = project.trim() || undefined
        data.location = location.trim() || undefined
        data.credentials_path = credentialsPath.trim() || undefined
      }
      if (isOllama && numCtx.trim()) {
        data.num_ctx = Number(numCtx)
      }
      createCredential.mutate(data, { onSuccess })
    }
  }

  const isValid = isEditing
    ? true
    : isVertex
      ? name.trim() !== '' && project.trim() !== '' && location.trim() !== ''
      : name.trim() !== '' && (!requiresApiKey || apiKey.trim() !== '')

  const docsUrl = providerInfo?.docs_url ?? undefined

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>
            {isEditing
              ? t('apiKeys.editConfig', { provider: providerDisplayName })
              : t('apiKeys.addConfig', { provider: providerDisplayName })}
          </DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Name */}
          <div className="space-y-2">
            <Label htmlFor="cred-name">{t('apiKeys.configName')}</Label>
            <input
              id="cred-name"
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={`${providerDisplayName} Production`}
              disabled={isSubmitting}
            />
            <p className="text-xs text-muted-foreground">{t('apiKeys.configNameHint')}</p>
          </div>

          {/* Vertex fields */}
          {isVertex ? (
            <>
              <div className="space-y-2">
                <Label htmlFor="vertex-project">{t('apiKeys.vertexProject')}</Label>
                <input
                  id="vertex-project"
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  value={project}
                  onChange={(e) => setProject(e.target.value)}
                  placeholder="my-gcp-project"
                  disabled={isSubmitting}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="vertex-location">{t('apiKeys.vertexLocation')}</Label>
                <input
                  id="vertex-location"
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  value={location}
                  onChange={(e) => setLocation(e.target.value)}
                  placeholder="us-central1"
                  disabled={isSubmitting}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="vertex-creds">
                  {t('apiKeys.vertexCredentials')}
                  <span className="text-muted-foreground font-normal ml-1">({t('common.optional')})</span>
                </Label>
                <input
                  id="vertex-creds"
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  value={credentialsPath}
                  onChange={(e) => setCredentialsPath(e.target.value)}
                  placeholder="/path/to/service-account.json"
                  disabled={isSubmitting}
                />
              </div>
            </>
          ) : (
            /* API Key */
            <div className="space-y-2">
              <Label htmlFor="api-key">
                {t('models.apiKey')}
                {!requiresApiKey && <span className="text-muted-foreground font-normal ml-1">({t('common.optional')})</span>}
              </Label>
              <div className="relative">
                <input
                  id="api-key"
                  type={showApiKey ? 'text' : 'password'}
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm pr-10"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder={isEditing ? '••••••••••••' : 'sk-...'}
                  disabled={isSubmitting}
                  autoComplete="off"
                />
                <button
                  type="button"
                  onClick={() => setShowApiKey(!showApiKey)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground text-xs"
                  tabIndex={-1}
                >
                  {showApiKey ? 'Hide' : 'Show'}
                </button>
              </div>
              {isEditing && <p className="text-xs text-muted-foreground">{t('apiKeys.apiKeyEditHint')}</p>}
              {docsUrl && (
                <a href={docsUrl} target="_blank" rel="noopener noreferrer" className="text-xs text-primary hover:underline">
                  {t('apiKeys.getApiKey')} &rarr;
                </a>
              )}
            </div>
          )}

          {/* Base URL (non-Vertex) */}
          {!isVertex && (
            <div className="space-y-2">
              <Label htmlFor="base-url" className="text-muted-foreground">{t('apiKeys.baseUrl')}</Label>
              <input
                id="base-url"
                type="url"
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={baseUrl}
                onChange={(e) => setBaseUrl(e.target.value)}
                placeholder={isOllama ? 'http://localhost:11434' : 'https://api.example.com/v1'}
                disabled={isSubmitting}
              />
              <p className="text-xs text-muted-foreground">{t('apiKeys.baseUrlOverrideHint')}</p>
            </div>
          )}

          {/* num_ctx (Ollama only) */}
          {isOllama && (
            <div className="space-y-2">
              <Label htmlFor="num-ctx" className="text-muted-foreground">
                {t('apiKeys.numCtx')}
                <span className="text-muted-foreground font-normal ml-1">({t('common.optional')})</span>
              </Label>
              <input
                id="num-ctx"
                type="number"
                min={1}
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={numCtx}
                onChange={(e) => setNumCtx(e.target.value)}
                placeholder="8192"
                disabled={isSubmitting}
              />
              <p className="text-xs text-muted-foreground">{t('apiKeys.numCtxHint')}</p>
            </div>
          )}

          {/* Actions */}
          <div className="flex justify-end gap-2 pt-4 border-t">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={isSubmitting}>
              {t('common.cancel')}
            </Button>
            <Button type="submit" disabled={!isValid || isSubmitting}>
              {isSubmitting && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
              {isEditing ? t('common.save') : t('apiKeys.addConfig')}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
