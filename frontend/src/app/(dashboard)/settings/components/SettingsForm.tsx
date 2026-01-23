'use client'

import { useForm, Controller } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Checkbox } from '@/components/ui/checkbox'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { Alert, AlertTitle, AlertDescription } from '@/components/ui/alert'
import { useSettings, useUpdateSettings } from '@/lib/hooks/use-settings'
import { useEffect, useState } from 'react'
import { ChevronDownIcon } from 'lucide-react'

const settingsSchema = z.object({
  default_content_processing_engine_doc: z.enum(['auto', 'docling', 'simple']).optional(),
  default_content_processing_engine_url: z.enum(['auto', 'firecrawl', 'jina', 'simple']).optional(),
  default_embedding_option: z.enum(['ask', 'always', 'never']).optional(),
  auto_delete_files: z.enum(['yes', 'no']).optional(),
  smol_docling_enabled: z.boolean().optional(),
  document_parser: z.enum(['content_core', 'smol_docling']).optional(),
  smol_docling_use_gpu: z.boolean().optional(),
})

type SettingsFormData = z.infer<typeof settingsSchema>

export function SettingsForm() {
  const { data: settings, isLoading, error } = useSettings()
  const updateSettings = useUpdateSettings()
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({})
  const [hasResetForm, setHasResetForm] = useState(false)
  
  
  const {
    control,
    handleSubmit,
    reset,
    formState: { isDirty }
  } = useForm<SettingsFormData>({
    resolver: zodResolver(settingsSchema),
    defaultValues: {
      default_content_processing_engine_doc: undefined,
      default_content_processing_engine_url: undefined,
      default_embedding_option: undefined,
      auto_delete_files: undefined,
      smol_docling_enabled: undefined,
      document_parser: undefined,
      smol_docling_use_gpu: undefined,
    }
  })


  const toggleSection = (section: string) => {
    setExpandedSections(prev => ({ ...prev, [section]: !prev[section] }))
  }

  useEffect(() => {
    if (settings && settings.default_content_processing_engine_doc && !hasResetForm) {
      const formData = {
        default_content_processing_engine_doc: settings.default_content_processing_engine_doc as 'auto' | 'docling' | 'simple',
        default_content_processing_engine_url: settings.default_content_processing_engine_url as 'auto' | 'firecrawl' | 'jina' | 'simple',
        default_embedding_option: settings.default_embedding_option as 'ask' | 'always' | 'never',
        auto_delete_files: settings.auto_delete_files as 'yes' | 'no',
        smol_docling_enabled: settings.smol_docling_enabled || false,
        document_parser: (settings.document_parser as 'content_core' | 'smol_docling') || 'content_core',
        smol_docling_use_gpu: settings.smol_docling_use_gpu ?? true,
      }
      reset(formData)
      setHasResetForm(true)
    }
  }, [hasResetForm, reset, settings])

  const onSubmit = async (data: SettingsFormData) => {
    await updateSettings.mutateAsync(data)
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

          <div className="flex items-start space-x-2 pt-4 border-t">
            <Controller
              name="smol_docling_enabled"
              control={control}
              render={({ field }) => (
                <Checkbox
                  id="smol_docling"
                  checked={field.value}
                  onCheckedChange={field.onChange}
                  disabled={true}
                />
              )}
            />
            <div className="grid gap-1.5 leading-none">
              <Label
                htmlFor="smol_docling"
                className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
              >
                Enable Smol Docling Integration (Legacy Toggle)
              </Label>
              <p className="text-sm text-muted-foreground">
                Use the Document Parser setting below instead.
              </p>
            </div>
          </div>

          <div className="space-y-3 pt-4 border-t">
            <Label htmlFor="document_parser">Document Parser (PDF/Image)</Label>
            <Controller
              name="document_parser"
              control={control}
              render={({ field }) => (
                <Select
                  key={field.value}
                  value={field.value || 'content_core'}
                  onValueChange={field.onChange}
                  disabled={field.disabled || isLoading}
                >
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Select document parser" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="content_core">Content Core (Default)</SelectItem>
                    <SelectItem value="smol_docling">SmolDocling (VLM-based)</SelectItem>
                  </SelectContent>
                </Select>
              )}
            />
            <Collapsible open={expandedSections.parser} onOpenChange={() => toggleSection('parser')}>
              <CollapsibleTrigger className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors">
                <ChevronDownIcon className={`h-4 w-4 transition-transform ${expandedSections.parser ? 'rotate-180' : ''}`} />
                Help me choose
              </CollapsibleTrigger>
              <CollapsibleContent className="mt-2 text-sm text-muted-foreground space-y-2">
                <p>Choose how PDF and image files are converted to text:</p>
                <p>• <strong>Content Core (Default)</strong> uses traditional extraction methods. Fast and reliable for most documents.</p>
                <p>• <strong>SmolDocling (VLM-based)</strong> uses a vision-language model (256M parameters) to understand document structure. Better for complex documents with tables, formulas, charts, and mixed layouts. Requires more computational resources.</p>
              </CollapsibleContent>
            </Collapsible>
          </div>

          <div className="flex items-start space-x-2 pt-2">
            <Controller
              name="smol_docling_use_gpu"
              control={control}
              render={({ field }) => (
                <Checkbox
                  id="smol_docling_gpu"
                  checked={field.value}
                  onCheckedChange={field.onChange}
                />
              )}
            />
            <div className="grid gap-1.5 leading-none">
              <Label
                htmlFor="smol_docling_gpu"
                className="text-sm font-medium leading-none"
              >
                Use GPU Acceleration for SmolDocling
              </Label>
              <p className="text-sm text-muted-foreground">
                Enable to use CUDA or Apple Silicon GPU if available. Disable to force CPU-only processing.
              </p>
            </div>
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
