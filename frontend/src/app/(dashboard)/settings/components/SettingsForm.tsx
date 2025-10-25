'use client'

import { useEffect, useState } from 'react'
import { useForm, Controller } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { Alert, AlertTitle, AlertDescription } from '@/components/ui/alert'
import { useSettings, useUpdateSettings } from '@/lib/hooks/use-settings'
import { ChevronDownIcon } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { SettingsResponse } from '@/lib/types/api'

interface ProviderFieldConfig {
  env: string
  label: string
  type?: 'text' | 'password'
  placeholder?: string
  helper?: string
}

interface ProviderConfig {
  id: string
  name: string
  description?: string
  fields: ProviderFieldConfig[]
}

const PROVIDER_CONFIGS: ProviderConfig[] = [
  {
    id: 'openai',
    name: 'OpenAI',
    description: 'Used for GPT models, Whisper, and text-to-speech.',
    fields: [
      {
        env: 'OPENAI_API_KEY',
        label: 'API Key',
        placeholder: 'sk-...',
        type: 'password',
      },
    ],
  },
  {
    id: 'azure',
    name: 'Azure OpenAI',
    description: 'Configure when using Azure-hosted OpenAI deployments.',
    fields: [
      { env: 'AZURE_OPENAI_API_KEY', label: 'API Key', type: 'password' },
      {
        env: 'AZURE_OPENAI_ENDPOINT',
        label: 'Endpoint URL',
        type: 'text',
        placeholder: 'https://your-resource.openai.azure.com',
      },
      { env: 'AZURE_OPENAI_DEPLOYMENT_NAME', label: 'Deployment Name', type: 'text' },
      {
        env: 'AZURE_OPENAI_API_VERSION',
        label: 'API Version',
        type: 'text',
        helper: 'Example: 2024-12-01-preview',
      },
    ],
  },
  {
    id: 'anthropic',
    name: 'Anthropic',
    description: 'Claude models for chat and tools.',
    fields: [{ env: 'ANTHROPIC_API_KEY', label: 'API Key', type: 'password' }],
  },
  {
    id: 'google',
    name: 'Google / Gemini',
    description: 'Gemini models for chat, embeddings, and speech.',
    fields: [
      { env: 'GEMINI_API_KEY', label: 'Gemini API Key', type: 'password' },
      {
        env: 'GOOGLE_API_KEY',
        label: 'Legacy Google API Key',
        type: 'password',
        helper: 'Only required for some older Gemini setups.',
      },
    ],
  },
  {
    id: 'vertex',
    name: 'Vertex AI',
    description: 'Google Cloud Vertex AI models.',
    fields: [
      { env: 'VERTEX_PROJECT', label: 'Project ID', type: 'text' },
      { env: 'VERTEX_LOCATION', label: 'Location', type: 'text' },
      {
        env: 'GOOGLE_APPLICATION_CREDENTIALS',
        label: 'Service Account JSON Path',
        type: 'text',
        helper: 'Absolute path to the service account JSON file accessible by the API container.',
      },
    ],
  },
  {
    id: 'groq',
    name: 'Groq',
    description: 'Groq hosted Llama and Mixtral models.',
    fields: [{ env: 'GROQ_API_KEY', label: 'API Key', type: 'password' }],
  },
  {
    id: 'mistral',
    name: 'Mistral',
    description: 'Mistral AI hosted models.',
    fields: [{ env: 'MISTRAL_API_KEY', label: 'API Key', type: 'password' }],
  },
  {
    id: 'deepseek',
    name: 'DeepSeek',
    description: 'DeepSeek chat and reasoning models.',
    fields: [{ env: 'DEEPSEEK_API_KEY', label: 'API Key', type: 'password' }],
  },
  {
    id: 'xai',
    name: 'xAI',
    description: 'Grok models provided by xAI.',
    fields: [{ env: 'XAI_API_KEY', label: 'API Key', type: 'password' }],
  },
  {
    id: 'openrouter',
    name: 'OpenRouter',
    description: 'Router for accessing community hosted models.',
    fields: [{ env: 'OPENROUTER_API_KEY', label: 'API Key', type: 'password' }],
  },
  {
    id: 'voyage',
    name: 'Voyage AI',
    description: 'High quality embeddings and rerankers.',
    fields: [{ env: 'VOYAGE_API_KEY', label: 'API Key', type: 'password' }],
  },
  {
    id: 'elevenlabs',
    name: 'ElevenLabs',
    description: 'Text-to-speech voices.',
    fields: [{ env: 'ELEVENLABS_API_KEY', label: 'API Key', type: 'password' }],
  },
  {
    id: 'ollama',
    name: 'Ollama',
    description: 'Local models served via Ollama.',
    fields: [
      {
        env: 'OLLAMA_API_BASE',
        label: 'API Base URL',
        type: 'text',
        placeholder: 'http://localhost:11434',
      },
    ],
  },
  {
    id: 'openai_compatible',
    name: 'OpenAI Compatible',
    description: 'Generic OpenAI-compatible endpoints (LM Studio, LocalAI, vLLM, etc.).',
    fields: [
      {
        env: 'OPENAI_COMPATIBLE_BASE_URL',
        label: 'Default Base URL',
        type: 'text',
        placeholder: 'http://localhost:1234/v1',
      },
      { env: 'OPENAI_COMPATIBLE_API_KEY', label: 'Default API Key', type: 'password' },
      {
        env: 'OPENAI_COMPATIBLE_BASE_URL_LLM',
        label: 'LLM Base URL',
        type: 'text',
        helper: 'Overrides the default base URL for chat models.',
      },
      { env: 'OPENAI_COMPATIBLE_API_KEY_LLM', label: 'LLM API Key', type: 'password' },
      { env: 'OPENAI_COMPATIBLE_BASE_URL_EMBEDDING', label: 'Embedding Base URL', type: 'text' },
      { env: 'OPENAI_COMPATIBLE_API_KEY_EMBEDDING', label: 'Embedding API Key', type: 'password' },
      { env: 'OPENAI_COMPATIBLE_BASE_URL_STT', label: 'Speech-to-Text Base URL', type: 'text' },
      { env: 'OPENAI_COMPATIBLE_API_KEY_STT', label: 'Speech-to-Text API Key', type: 'password' },
      { env: 'OPENAI_COMPATIBLE_BASE_URL_TTS', label: 'Text-to-Speech Base URL', type: 'text' },
      { env: 'OPENAI_COMPATIBLE_API_KEY_TTS', label: 'Text-to-Speech API Key', type: 'password' },
    ],
  },
  {
    id: 'content_extraction',
    name: 'Content Extraction',
    description: 'Optional keys for Firecrawl and Jina when processing URLs.',
    fields: [
      { env: 'FIRECRAWL_API_KEY', label: 'Firecrawl API Key', type: 'password' },
      { env: 'JINA_API_KEY', label: 'Jina API Key', type: 'password' },
    ],
  },
]
const settingsSchema = z.object({
  default_content_processing_engine_doc: z.enum(['auto', 'docling', 'simple']).optional(),
  default_content_processing_engine_url: z.enum(['auto', 'firecrawl', 'jina', 'simple']).optional(),
  default_embedding_option: z.enum(['ask', 'always', 'never']).optional(),
  auto_delete_files: z.enum(['yes', 'no']).optional(),
  provider_credentials: z.record(z.string(), z.string().optional()).optional(),
})

type SettingsFormData = z.infer<typeof settingsSchema>

export function SettingsForm() {
  const { data: settings, isLoading, error } = useSettings()
  const updateSettings = useUpdateSettings()
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({})

  const {
    control,
    handleSubmit,
    reset,
    register,
    watch,
    formState: { isDirty },
  } = useForm<SettingsFormData>({
    resolver: zodResolver(settingsSchema),
    defaultValues: {
      default_content_processing_engine_doc: undefined,
      default_content_processing_engine_url: undefined,
      default_embedding_option: undefined,
      auto_delete_files: undefined,
      provider_credentials: {},
    },
  })

  const toggleSection = (section: string) => {
    setExpandedSections((prev) => ({ ...prev, [section]: !prev[section] }))
  }

  useEffect(() => {
    if (!settings) {
      return
    }

    const providerCredentials = Object.fromEntries(
      Object.entries(settings.provider_credentials ?? {}).map(([key, value]) => [
        key,
        value ?? '',
      ]),
    ) as Record<string, string>

    reset({
      default_content_processing_engine_doc: (settings.default_content_processing_engine_doc ?? undefined) as
        | 'auto'
        | 'docling'
        | 'simple'
        | undefined,
      default_content_processing_engine_url: (settings.default_content_processing_engine_url ?? undefined) as
        | 'auto'
        | 'firecrawl'
        | 'jina'
        | 'simple'
        | undefined,
      default_embedding_option: (settings.default_embedding_option ?? undefined) as
        | 'ask'
        | 'always'
        | 'never'
        | undefined,
      auto_delete_files: (settings.auto_delete_files ?? undefined) as 'yes' | 'no' | undefined,
      provider_credentials: providerCredentials,
    })
  }, [reset, settings])

  const providerCredentials = watch('provider_credentials') || {}

  const onSubmit = async (data: SettingsFormData) => {
    const { provider_credentials, ...rest } = data

    const existingCredentials = settings?.provider_credentials ?? {}
    const providerUpdates: Record<string, string | null> = {}
    const formCredentials = provider_credentials ?? {}

    const allKeys = new Set([
      ...Object.keys(existingCredentials),
      ...Object.keys(formCredentials),
    ])

    allKeys.forEach((key) => {
      const rawValue = formCredentials[key]
      const trimmedValue = rawValue?.trim()

      if (trimmedValue) {
        providerUpdates[key] = trimmedValue
      } else if (key in existingCredentials) {
        providerUpdates[key] = null
      }
    })

    const payload: Partial<SettingsResponse> = {
      ...rest,
    }

    if (Object.keys(providerUpdates).length > 0) {
      payload.provider_credentials = providerUpdates
    }

    await updateSettings.mutateAsync(payload)
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertTitle>Failed to load settings</AlertTitle>
        <AlertDescription>
          {error instanceof Error ? error.message : 'An unexpected error occurred.'}
        </AlertDescription>
      </Alert>
    )
  }
  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Content Processing</CardTitle>
          <CardDescription>
            Configure how documents and URLs are processed
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-3">
            <Label htmlFor="doc_engine">Document Processing Engine</Label>
            <Controller
              name="default_content_processing_engine_doc"
              control={control}
              render={({ field }) => (
                <Select
                  key={field.value}
                  value={field.value || ''}
                  onValueChange={field.onChange}
                  disabled={field.disabled || isLoading}
                >
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Select document processing engine" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="auto">Auto (Recommended)</SelectItem>
                    <SelectItem value="docling">Docling</SelectItem>
                    <SelectItem value="simple">Simple</SelectItem>
                  </SelectContent>
                </Select>
              )}
            />
            <Collapsible open={expandedSections.doc} onOpenChange={() => toggleSection('doc')}>
              <CollapsibleTrigger className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors">
                <ChevronDownIcon className={`h-4 w-4 transition-transform ${expandedSections.doc ? 'rotate-180' : ''}`} />
                Help me choose
              </CollapsibleTrigger>
              <CollapsibleContent className="mt-2 text-sm text-muted-foreground space-y-2">
                <p>• <strong>Docling</strong> is a little slower but more accurate, specially if the documents contain tables and images.</p>
                <p>• <strong>Simple</strong> will extract any content from the document without formatting it. It&apos;s ok for simple documents, but will lose quality in complex ones.</p>
                <p>• <strong>Auto (recommended)</strong> will try to process through docling and default to simple.</p>
              </CollapsibleContent>
            </Collapsible>
          </div>

          <div className="space-y-3">
            <Label htmlFor="url_engine">URL Processing Engine</Label>
            <Controller
              name="default_content_processing_engine_url"
              control={control}
              render={({ field }) => (
                <Select
                  key={field.value}
                  value={field.value || ''}
                  onValueChange={field.onChange}
                  disabled={field.disabled || isLoading}
                >
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Select URL processing engine" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="auto">Auto (Recommended)</SelectItem>
                    <SelectItem value="firecrawl">Firecrawl</SelectItem>
                    <SelectItem value="jina">Jina</SelectItem>
                    <SelectItem value="simple">Simple</SelectItem>
                  </SelectContent>
                </Select>
              )}
            />
            <Collapsible open={expandedSections.url} onOpenChange={() => toggleSection('url')}>
              <CollapsibleTrigger className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors">
                <ChevronDownIcon className={`h-4 w-4 transition-transform ${expandedSections.url ? 'rotate-180' : ''}`} />
                Help me choose
              </CollapsibleTrigger>
              <CollapsibleContent className="mt-2 text-sm text-muted-foreground space-y-2">
                <p>• <strong>Firecrawl</strong> is a paid service (with a free tier), and very powerful.</p>
                <p>• <strong>Jina</strong> is a good option as well and also has a free tier.</p>
                <p>• <strong>Simple</strong> will use basic HTTP extraction and will miss content on javascript-based websites.</p>
                <p>• <strong>Auto (recommended)</strong> will try to use firecrawl (if API Key is present). Then, it will use Jina until reaches the limit (or will keep using Jina if you setup the API Key). It will fallback to simple, when none of the previous options is possible.</p>
              </CollapsibleContent>
            </Collapsible>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Embedding and Search</CardTitle>
          <CardDescription>
            Configure search and embedding options
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-3">
            <Label htmlFor="embedding">Default Embedding Option</Label>
            <Controller
              name="default_embedding_option"
              control={control}
              render={({ field }) => (
                <Select
                  key={field.value}
                  value={field.value || ''}
                  onValueChange={field.onChange}
                  disabled={field.disabled || isLoading}
                >
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Select embedding option" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ask">Ask</SelectItem>
                    <SelectItem value="always">Always</SelectItem>
                    <SelectItem value="never">Never</SelectItem>
                  </SelectContent>
                </Select>
              )}
            />
            <Collapsible open={expandedSections.embedding} onOpenChange={() => toggleSection('embedding')}>
              <CollapsibleTrigger className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors">
                <ChevronDownIcon className={`h-4 w-4 transition-transform ${expandedSections.embedding ? 'rotate-180' : ''}`} />
                Help me choose
              </CollapsibleTrigger>
              <CollapsibleContent className="mt-2 text-sm text-muted-foreground space-y-2">
                <p>Embedding the content will make it easier to find by you and by your AI agents. If you are running a local embedding model (Ollama, for example), you shouldn&apos;t worry about cost and just embed everything. For online providers, you might want to be careful only if you process a lot of content (like 100s of documents at a day).</p>
                <p>• Choose <strong>always</strong> if you are running a local embedding model or if your content volume is not that big</p>
                <p>• Choose <strong>ask</strong> if you want to decide every time</p>
                <p>• Choose <strong>never</strong> if you don&apos;t care about vector search or do not have an embedding provider.</p>
                <p>As a reference, OpenAI&apos;s text-embedding-3-small costs about 0.02 for 1 million tokens -- which is about 30 times the Wikipedia page for Earth. With Gemini API, Text Embedding 004 is free with a rate limit of 1500 requests per minute.</p>
              </CollapsibleContent>
            </Collapsible>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>AI Provider Credentials</CardTitle>
          <CardDescription>
            Save API keys and endpoints for the providers you use. Changes take effect immediately for new requests.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {PROVIDER_CONFIGS.map((provider) => {
            const providerKey = `provider-${provider.id}`
            const providerValues = provider.fields.map((field) => providerCredentials?.[field.env])
            const isConfigured = providerValues.some(
              (value) => typeof value === 'string' && value.trim().length > 0,
            )

            return (
              <div key={provider.id} className="rounded-lg border border-border bg-card">
                <button
                  type="button"
                  onClick={() => toggleSection(providerKey)}
                  className="flex w-full items-center justify-between gap-4 rounded-t-lg p-4 text-left transition-colors hover:bg-muted/60"
                  aria-expanded={Boolean(expandedSections[providerKey])}
                >
                  <div className="space-y-1">
                    <p className="font-medium">{provider.name}</p>
                    {provider.description && (
                      <p className="text-sm text-muted-foreground">{provider.description}</p>
                    )}
                  </div>
                  <div className="flex items-center gap-3">
                    <Badge variant={isConfigured ? 'default' : 'outline'} className="text-xs">
                      {isConfigured ? 'Configured' : 'Not configured'}
                    </Badge>
                    <ChevronDownIcon
                      className={`h-4 w-4 transition-transform ${expandedSections[providerKey] ? 'rotate-180' : ''}`}
                    />
                  </div>
                </button>
                {expandedSections[providerKey] && (
                  <div className="space-y-4 border-t border-border p-4 pt-3">
                    {provider.fields.map((field) => (
                      <div key={field.env} className="space-y-2">
                        <Label htmlFor={field.env}>{field.label}</Label>
                        <Input
                          id={field.env}
                          type={field.type === 'text' ? 'text' : 'password'}
                          placeholder={field.placeholder}
                          autoComplete="off"
                          spellCheck={false}
                          {...register(`provider_credentials.${field.env}`)}
                        />
                        {field.helper && (
                          <p className="text-xs text-muted-foreground">{field.helper}</p>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )
          })}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>File Management</CardTitle>
          <CardDescription>
            Configure file handling and storage options
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-3">
            <Label htmlFor="auto_delete">Auto Delete Files</Label>
            <Controller
              name="auto_delete_files"
              control={control}
              render={({ field }) => (
                <Select
                  key={field.value}
                  value={field.value || ''}
                  onValueChange={field.onChange}
                  disabled={field.disabled || isLoading}
                >
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Select auto delete option" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="yes">Yes</SelectItem>
                    <SelectItem value="no">No</SelectItem>
                  </SelectContent>
                </Select>
              )}
            />
            <Collapsible open={expandedSections.files} onOpenChange={() => toggleSection('files')}>
              <CollapsibleTrigger className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors">
                <ChevronDownIcon className={`h-4 w-4 transition-transform ${expandedSections.files ? 'rotate-180' : ''}`} />
                Help me choose
              </CollapsibleTrigger>
              <CollapsibleContent className="mt-2 text-sm text-muted-foreground space-y-2">
                <p>Once your files are uploaded and processed, they are not required anymore. Most users should allow Open Notebook to delete uploaded files from the upload folder automatically. Choose <strong>no</strong>, ONLY if you are using Notebook as the primary storage location for those files (which you shouldn&apos;t be at all). This option will soon be deprecated in favor of always downloading the files.</p>
                <p>• Choose <strong>yes</strong> (recommended) to automatically delete uploaded files after processing</p>
                <p>• Choose <strong>no</strong> only if you need to keep the original files in the upload folder</p>
              </CollapsibleContent>
            </Collapsible>
          </div>
        </CardContent>
      </Card>

      <div className="flex justify-end">
        <Button
          type="submit"
          disabled={!isDirty || updateSettings.isPending}
        >
          {updateSettings.isPending ? 'Saving...' : 'Save Settings'}
        </Button>
      </div>
    </form>
  )
}
