"use client"

import { useMemo, useState } from "react"
import { Control, FieldErrors, UseFormRegister, UseFormSetValue, useWatch } from "react-hook-form"
import { FileIcon, LinkIcon, FileTextIcon } from "lucide-react"
import { useTranslation } from "@/lib/hooks/use-translation"
import { FormSection } from "@/components/ui/form-section"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { Controller } from "react-hook-form"

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

// Helper functions for batch URL parsing
function parseUrls(text: string): string[] {
  return text
    .split('\n')
    .map(line => line.trim())
    .filter(line => line.length > 0)
}

function validateUrl(url: string): boolean {
  try {
    new URL(url)
    return true
  } catch {
    return false
  }
}

export function parseAndValidateUrls(text: string): {
  valid: string[]
  invalid: { url: string; line: number }[]
} {
  const lines = text.split('\n')
  const valid: string[] = []
  const invalid: { url: string; line: number }[] = []

  lines.forEach((line, index) => {
    const trimmed = line.trim()
    if (trimmed.length === 0) return // skip empty lines

    if (validateUrl(trimmed)) {
      valid.push(trimmed)
    } else {
      invalid.push({ url: trimmed, line: index + 1 })
    }
  })

  return { valid, invalid }
}

import { TranslationKeys } from '@/lib/locales'

const getSourceTypes = (t: TranslationKeys) => [
  {
    value: 'link' as const,
    label: t.sources.addUrl,
    icon: LinkIcon,
    description: t.sources.processDescription,
  },
  {
    value: 'upload' as const,
    label: t.sources.uploadFile,
    icon: FileIcon,
    description: t.sources.processDescription,
  },
  {
    value: 'text' as const,
    label: t.sources.enterText,
    icon: FileTextIcon,
    description: t.sources.processDescription,
  },
]

interface SourceTypeStepProps {
  control: Control<CreateSourceFormData>
  register: UseFormRegister<CreateSourceFormData>
  setValue: UseFormSetValue<CreateSourceFormData>
  errors: FieldErrors<CreateSourceFormData>
  urlValidationErrors?: { url: string; line: number }[]
  onClearUrlErrors?: () => void
}

const MAX_BATCH_SIZE = 50

export function SourceTypeStep({ control, register, setValue, errors, urlValidationErrors, onClearUrlErrors }: SourceTypeStepProps) {
  const { t } = useTranslation()
  // Watch the selected type and inputs to detect batch mode
  const selectedType = useWatch({ control, name: 'type' })
  const urlInput = useWatch({ control, name: 'url' })
  const fileInput = useWatch({ control, name: 'file' })

  // Track if HTML content was pasted
  const [hasHtmlContent, setHasHtmlContent] = useState(false)

  // Handle paste event to check for HTML content in clipboard
  const handleTextPaste = (event: React.ClipboardEvent<HTMLTextAreaElement>) => {
    const htmlContent = event.clipboardData.getData('text/html')

    // If HTML content is available, use it instead of plain text
    if (htmlContent) {
      event.preventDefault()
      // Get current content and cursor position
      const textarea = event.currentTarget
      const start = textarea.selectionStart
      const end = textarea.selectionEnd
      const currentValue = textarea.value

      // Insert HTML content at cursor position (replacing selection if any)
      const newValue = currentValue.substring(0, start) + htmlContent + currentValue.substring(end)
      setValue('content', newValue, { shouldValidate: true })
      setHasHtmlContent(true)
    } else {
      // Plain text paste - clear the HTML indicator
      setHasHtmlContent(false)
    }
  }

  // Batch mode detection
  const { isBatchMode, itemCount, urlCount, fileCount } = useMemo(() => {
    let urlCount = 0
    let fileCount = 0

    if (selectedType === 'link' && urlInput) {
      const urls = parseUrls(urlInput)
      urlCount = urls.length
    }

    if (selectedType === 'upload' && fileInput) {
      const fileList = fileInput as FileList
      fileCount = fileList?.length || 0
    }

    const isBatchMode = urlCount > 1 || fileCount > 1
    const itemCount = selectedType === 'link' ? urlCount : fileCount

    return { isBatchMode, itemCount, urlCount, fileCount }
  }, [selectedType, urlInput, fileInput])

  // Check for batch size limit
  const isOverLimit = itemCount > MAX_BATCH_SIZE
  return (
    <div className="space-y-6">
      <FormSection
        title={t.sources.title}
        description={t.sources.processDescription}
      >
        <Controller
          control={control}
          name="type"
          render={({ field }) => (
            <Tabs 
              value={field.value || ''} 
              onValueChange={(value) => field.onChange(value as 'link' | 'upload' | 'text')}
              className="w-full"
            >
              <TabsList className="grid w-full grid-cols-3">
                {getSourceTypes(t).map((type) => {
                  const Icon = type.icon
                  return (
                    <TabsTrigger key={type.value} value={type.value} className="gap-2">
                      <Icon className="h-4 w-4" />
                      {type.label}
                    </TabsTrigger>
                  )
                })}
              </TabsList>
              
              {getSourceTypes(t).map((type) => (
                <TabsContent key={type.value} value={type.value} className="mt-4">
                  <p className="text-sm text-muted-foreground mb-4">{type.description}</p>
                  
                  {/* Type-specific fields */}
                  {type.value === 'link' && (
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <Label htmlFor="url">{t.sources.urlLabel}</Label>
                        {urlCount > 0 && (
                          <Badge variant={isOverLimit ? "destructive" : "secondary"}>
                            {t.sources.urlsCount.replace('{count}', urlCount.toString())}
                            {isOverLimit && ` (${t.sources.maxItems.replace('{count}', MAX_BATCH_SIZE.toString())})`}
                          </Badge>
                        )}
                      </div>
                      <Textarea
                        id="url"
                        {...register('url', {
                          onChange: () => onClearUrlErrors?.()
                        })}
                        placeholder={t.sources.enterUrlsPlaceholder}
                        rows={urlCount > 1 ? 6 : 2}
                        className="font-mono text-sm"
                      />
                      <p className="text-xs text-muted-foreground mt-1">
                        {t.sources.batchUrlHint}
                      </p>
                      {errors.url && (
                        <p className="text-sm text-destructive mt-1">{errors.url.message}</p>
                      )}
                      {urlValidationErrors && urlValidationErrors.length > 0 && (
                        <div className="mt-2 p-3 bg-destructive/10 rounded-md border border-destructive/20">
                          <p className="text-sm font-medium text-destructive mb-2">
                            {t.sources.invalidUrlsDetected}
                          </p>
                          <ul className="space-y-1">
                            {urlValidationErrors.map((error, idx) => (
                              <li key={idx} className="text-xs text-destructive flex items-start gap-2">
                                <span className="font-mono bg-destructive/20 px-1 rounded">
                                  {t.sources.lineLabel.replace('{line}', error.line.toString())}
                                </span>
                                <span className="truncate">{error.url}</span>
                              </li>
                            ))}
                          </ul>
                          <p className="text-xs text-muted-foreground mt-2">
                            {t.sources.fixInvalidUrls}
                          </p>
                        </div>
                      )}
                    </div>
                  )}
                  
                  {type.value === 'upload' && (
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <Label htmlFor="file">{t.sources.fileLabel}</Label>
                        {fileCount > 0 && (
                          <Badge variant={isOverLimit ? "destructive" : "secondary"}>
                            {t.sources.filesCount.replace('{count}', fileCount.toString())}
                            {isOverLimit && ` (${t.sources.maxItems.replace('{count}', MAX_BATCH_SIZE.toString())})`}
                          </Badge>
                        )}
                      </div>
                      <Input
                        id="file"
                        type="file"
                        multiple
                        {...register('file')}
                        accept=".pdf,.doc,.docx,.pptx,.ppt,.xlsx,.xls,.txt,.md,.epub,.mp4,.avi,.mov,.wmv,.mp3,.wav,.m4a,.aac,.jpg,.jpeg,.png,.tiff,.zip,.tar,.gz,.html"
                      />
                      <p className="text-xs text-muted-foreground mt-1">
                        {t.sources.selectMultipleFilesHint}
                      </p>
                      {fileCount > 1 && fileInput instanceof FileList && (
                        <div className="mt-2 p-3 bg-muted rounded-md">
                          <p className="text-xs font-medium mb-2">{t.sources.selectedFiles}</p>
                          <ul className="space-y-1 max-h-32 overflow-y-auto">
                            {Array.from(fileInput).map((file, idx) => (
                              <li key={idx} className="text-xs text-muted-foreground flex items-center gap-2">
                                <FileIcon className="h-3 w-3" />
                                <span className="truncate">{file.name}</span>
                                <span className="text-muted-foreground/50">
                                  ({(file.size / 1024).toFixed(1)} KB)
                                </span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                      {errors.file && (
                        <p className="text-sm text-destructive mt-1">{errors.file.message}</p>
                      )}
                      {isOverLimit && selectedType === 'upload' && (
                        <p className="text-sm text-destructive mt-1">
                          {t.sources.maxFilesAllowed.replace('{count}', MAX_BATCH_SIZE.toString())}
                        </p>
                      )}
                    </div>
                  )}
                  
                  {type.value === 'text' && (
                    <div>
                      <Label htmlFor="content" className="mb-2 block">{t.sources.textContentLabel}</Label>
                      {hasHtmlContent && (
                        <div className="mb-2 p-2 bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800 rounded-md">
                          <p className="text-sm text-blue-700 dark:text-blue-300">
                            {t.sources.htmlDetected}
                          </p>
                        </div>
                      )}
                      <Textarea
                        id="content"
                        {...register('content')}
                        placeholder={t.sources.textPlaceholder}
                        rows={6}
                        onPaste={handleTextPaste}
                      />
                      {errors.content && (
                        <p className="text-sm text-destructive mt-1">{errors.content.message}</p>
                      )}
                    </div>
                  )}
                </TabsContent>
              ))}
            </Tabs>
          )}
        />
        {errors.type && (
          <p className="text-sm text-destructive mt-1">{errors.type.message}</p>
        )}
      </FormSection>

      {/* Hide title field in batch mode - titles will be auto-generated */}
      {!isBatchMode && (
        <FormSection
          htmlFor="source-title"
          title={selectedType === 'text' ? `${t.common.title} *` : `${t.common.title} (${t.common.optional})`}
          description={selectedType === 'text'
            ? t.sources.titleRequired
            : t.sources.titleGenerated
          }
        >
          <Input
            id="source-title"
            {...register('title')}
            placeholder={t.sources.titlePlaceholder}
            autoComplete="off"
          />
          {errors.title && (
            <p className="text-sm text-destructive mt-1">{errors.title.message}</p>
          )}
        </FormSection>
      )}

      {/* Batch mode indicator */}
      {isBatchMode && (
        <div className="p-4 bg-primary/5 border border-primary/20 rounded-lg">
          <div className="flex items-center gap-2 mb-2">
            <Badge variant="default">{t.common.batchMode}</Badge>
            <span className="text-sm font-medium">
              {t.sources.batchCount.replace('{count}', itemCount.toString()).replace('{type}', selectedType === 'link' ? t.sources.addUrl : t.sources.uploadFile)}
            </span>
          </div>
          <p className="text-xs text-muted-foreground">
            {t.sources.batchTitlesAuto}
            {t.sources.batchCommonSettings}
          </p>
        </div>
      )}
    </div>
  )
}
