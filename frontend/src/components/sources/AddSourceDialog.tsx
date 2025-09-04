'use client'

import { useState } from 'react'
import { useForm, Controller } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { FileIcon, LinkIcon, FileTextIcon, LoaderIcon } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { Checkbox } from '@/components/ui/checkbox'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { 
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { 
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
} from '@/components/ui/command'
import { CheckIcon, ChevronDownIcon, XIcon } from 'lucide-react'
import { useNotebooks } from '@/lib/hooks/use-notebooks'
import { useTransformations } from '@/lib/hooks/use-transformations'
import { useCreateSource } from '@/lib/hooks/use-sources'
import { NotebookResponse, CreateSourceRequest } from '@/lib/types/api'
import { Transformation } from '@/lib/types/transformations'

const createSourceSchema = z.object({
  type: z.enum(['link', 'upload', 'text'], {
    required_error: 'Please select a source type',
  }),
  title: z.string().optional(),
  // Conditional fields based on type - will be validated with superRefine
  url: z.string().optional(),
  content: z.string().optional(),
  file: z.any().optional(),
  // Multi-select fields
  notebooks: z.array(z.string()).optional(),
  transformations: z.array(z.string()).optional(),
  embed: z.boolean(),
  async_processing: z.boolean(),
}).refine((data) => {
  // Validate based on type
  if (data.type === 'link') {
    return !!data.url && data.url.trim() !== ''
  }
  if (data.type === 'text') {
    return !!data.content && data.content.trim() !== ''
  }
  if (data.type === 'upload') {
    if (data.file instanceof FileList) {
      return data.file.length > 0
    }
    return !!data.file
  }
  return true
}, {
  message: 'Please provide the required content for the selected source type',
  path: ['type'],
})

type CreateSourceFormData = z.infer<typeof createSourceSchema>

interface AddSourceDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  defaultNotebookId?: string
}

const SOURCE_TYPES = [
  {
    value: 'link' as const,
    label: 'Link',
    icon: LinkIcon,
    description: 'Add a web page or URL',
  },
  {
    value: 'upload' as const,
    label: 'Upload',
    icon: FileIcon,
    description: 'Upload a document or file',
  },
  {
    value: 'text' as const,
    label: 'Text',
    icon: FileTextIcon,
    description: 'Add text content directly',
  },
]

export function AddSourceDialog({ 
  open, 
  onOpenChange, 
  defaultNotebookId 
}: AddSourceDialogProps) {
  const [step, setStep] = useState<'form' | 'processing'>('form')
  const [processingStatus, setProcessingStatus] = useState<{
    message: string
    progress?: number
  } | null>(null)
  const [notebookOpen, setNotebookOpen] = useState(false)
  const [transformationOpen, setTransformationOpen] = useState(false)
  const [localSelectedNotebooks, setLocalSelectedNotebooks] = useState<string[]>(
    defaultNotebookId ? [defaultNotebookId] : []
  )
  const [localSelectedTransformations, setLocalSelectedTransformations] = useState<string[]>([])
  
  const createSource = useCreateSource()
  const { data: notebooks = [], isLoading: notebooksLoading } = useNotebooks()
  const { data: transformations = [], isLoading: transformationsLoading } = useTransformations()

  const {
    register,
    handleSubmit,
    control,
    watch,
    formState: { errors },
    reset,
    setValue,
    getValues,
  } = useForm<CreateSourceFormData>({
    resolver: zodResolver(createSourceSchema),
    defaultValues: {
      notebooks: defaultNotebookId ? [defaultNotebookId] : [],
      embed: true,
      async_processing: true,
      transformations: [],
    },
  })

  const selectedType = watch('type')
  // Use local state instead of watch for better reactivity
  const selectedNotebooks = localSelectedNotebooks
  const selectedTransformations = localSelectedTransformations

  const onSubmit = async (data: CreateSourceFormData) => {
    try {
      setStep('processing')
      setProcessingStatus({ message: 'Submitting source for processing...' })

      // Create the request object using local state for notebooks/transformations
      const createRequest: CreateSourceRequest = {
        type: data.type,
        notebooks: localSelectedNotebooks,
        url: data.type === 'link' ? data.url : undefined,
        content: data.type === 'text' ? data.content : undefined,
        title: data.title,
        transformations: localSelectedTransformations,
        embed: data.embed,
        delete_source: false,
        async_processing: data.async_processing,
      }
      
      // Add file for upload type (extract from FileList)
      if (data.type === 'upload' && data.file) {
        const file = data.file instanceof FileList ? data.file[0] : data.file
        const requestWithFile = createRequest as CreateSourceRequest & { file?: File }
        requestWithFile.file = file
      }

      await createSource.mutateAsync(createRequest)

      if (data.async_processing) {
        setProcessingStatus({ 
          message: 'Source submitted for async processing. You can monitor progress in the sources list.',
          progress: 100 
        })
        
        // Auto-close after showing success message
        setTimeout(() => {
          handleClose()
        }, 3000)
      } else {
        setProcessingStatus({ 
          message: 'Source processed successfully!',
          progress: 100 
        })
        
        setTimeout(() => {
          handleClose()
        }, 1500)
      }
    } catch (error) {
      console.error('Error creating source:', error)
      setProcessingStatus({ 
        message: 'Error creating source. Please try again.',
      })
      
      // Reset to form after showing error
      setTimeout(() => {
        setStep('form')
        setProcessingStatus(null)
      }, 3000)
    }
  }

  const handleClose = () => {
    reset()
    setStep('form')
    setProcessingStatus(null)
    setLocalSelectedNotebooks(defaultNotebookId ? [defaultNotebookId] : [])
    setLocalSelectedTransformations([])
    setNotebookOpen(false)
    setTransformationOpen(false)
    onOpenChange(false)
  }

  const handleNotebookToggle = (notebookId: string) => {
    console.log('📝 handleNotebookToggle called with:', notebookId)
    const updated = localSelectedNotebooks.includes(notebookId)
      ? localSelectedNotebooks.filter(id => id !== notebookId)
      : [...localSelectedNotebooks, notebookId]
    console.log('📝 Updated notebooks:', updated)
    setLocalSelectedNotebooks(updated)
    // Also update form state for submission
    setValue('notebooks', updated)
  }

  const handleTransformationToggle = (transformationId: string) => {
    console.log('📝 handleTransformationToggle called with:', transformationId)
    const updated = localSelectedTransformations.includes(transformationId)
      ? localSelectedTransformations.filter(id => id !== transformationId)
      : [...localSelectedTransformations, transformationId]
    console.log('📝 Updated transformations:', updated)
    setLocalSelectedTransformations(updated)
    // Also update form state for submission
    setValue('transformations', updated)
  }

  if (step === 'processing') {
    return (
      <Dialog open={open} onOpenChange={() => {}}>
        <DialogContent className="sm:max-w-[500px]" showCloseButton={false}>
          <DialogHeader>
            <DialogTitle>Processing Source</DialogTitle>
            <DialogDescription>
              Your source is being processed. This may take a few moments.
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            <div className="flex items-center gap-3">
              <LoaderIcon className="h-5 w-5 animate-spin text-blue-600" />
              <span className="text-sm text-gray-600">
                {processingStatus?.message || 'Processing...'}
              </span>
            </div>
            
            {processingStatus?.progress && (
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div 
                  className="bg-blue-600 h-2 rounded-full transition-all duration-300" 
                  style={{ width: `${processingStatus.progress}%` }}
                />
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>
    )
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[700px] max-h-[90vh] overflow-hidden">
        <DialogHeader>
          <DialogTitle>Add New Source</DialogTitle>
          <DialogDescription>
            Add content from links, uploads, or text to your notebooks.
          </DialogDescription>
        </DialogHeader>
        
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <ScrollArea className="max-h-[65vh] pr-4">
            <div className="space-y-4">
              {/* Source Type Selection */}
              <div>
                <Label className="text-base font-medium">Source Type</Label>
                <p className="text-sm text-gray-600 mb-3">
                  Choose how you want to add your content
                </p>
                <Controller
                  control={control}
                  name="type"
                  render={({ field }) => (
                    <Tabs 
                      value={field.value} 
                      onValueChange={(value) => field.onChange(value as 'link' | 'upload' | 'text')}
                      className="w-full"
                    >
                      <TabsList className="grid w-full grid-cols-3">
                        {SOURCE_TYPES.map((type) => {
                          const Icon = type.icon
                          return (
                            <TabsTrigger key={type.value} value={type.value} className="gap-2">
                              <Icon className="h-4 w-4" />
                              {type.label}
                            </TabsTrigger>
                          )
                        })}
                      </TabsList>
                      
                      {SOURCE_TYPES.map((type) => (
                        <TabsContent key={type.value} value={type.value} className="mt-4">
                          <p className="text-sm text-gray-600 mb-4">{type.description}</p>
                          
                          {/* Type-specific fields */}
                          {type.value === 'link' && (
                            <div>
                              <Label htmlFor="url" className="mb-2 block">URL *</Label>
                              <Input
                                id="url"
                                {...register('url')}
                                placeholder="https://example.com/article"
                                type="url"
                              />
                              {errors.url && (
                                <p className="text-sm text-red-600 mt-1">{errors.url.message}</p>
                              )}
                            </div>
                          )}
                          
                          {type.value === 'upload' && (
                            <div>
                              <Label htmlFor="file" className="mb-2 block">File *</Label>
                              <Input
                                id="file"
                                type="file"
                                {...register('file')}
                                accept=".pdf,.doc,.docx,.txt,.md,.epub"
                              />
                              <p className="text-xs text-gray-500 mt-1">
                                Supported formats: PDF, DOC, DOCX, TXT, MD, EPUB
                              </p>
                              {errors.file && (
                                <p className="text-sm text-red-600 mt-1">{errors.file.message}</p>
                              )}
                            </div>
                          )}
                          
                          {type.value === 'text' && (
                            <div>
                              <Label htmlFor="content" className="mb-2 block">Text Content *</Label>
                              <Textarea
                                id="content"
                                {...register('content')}
                                placeholder="Paste or type your content here..."
                                rows={6}
                              />
                              {errors.content && (
                                <p className="text-sm text-red-600 mt-1">{errors.content.message}</p>
                              )}
                            </div>
                          )}
                        </TabsContent>
                      ))}
                    </Tabs>
                  )}
                />
                {errors.type && (
                  <p className="text-sm text-red-600 mt-1">{errors.type.message}</p>
                )}
              </div>

              {/* Title */}
              <div>
                <Label htmlFor="title" className="mb-2 block">Title (optional)</Label>
                <Input
                  id="title"
                  {...register('title')}
                  placeholder="Give your source a descriptive title"
                />
                <p className="text-xs text-gray-500 mt-1">
                  If left empty, a title will be generated from the content
                </p>
              </div>

              {/* Notebook Selection */}
              <div className="space-y-3">
                <Label className="text-base font-medium">Notebooks (optional)</Label>
                <div className="border rounded-md p-3 bg-gray-50">
                  <ScrollArea className="max-h-24">
                    <div className="space-y-2 pr-3">
                      {notebooks.map((notebook: NotebookResponse) => (
                        <Controller
                          key={notebook.id}
                          control={control}
                          name="notebooks"
                          render={({ field }) => (
                            <label className="flex items-start gap-2 cursor-pointer">
                              <Checkbox
                                checked={field.value?.includes(notebook.id) || false}
                                onCheckedChange={(checked) => {
                                  const currentValue = field.value || []
                                  if (checked) {
                                    field.onChange([...currentValue, notebook.id])
                                  } else {
                                    field.onChange(currentValue.filter((id: string) => id !== notebook.id))
                                  }
                                }}
                                className="mt-1"
                              />
                              <div className="flex-1">
                                <span className="text-sm font-medium">{notebook.name}</span>
                                {notebook.description && (
                                  <p className="text-xs text-gray-600">{notebook.description}</p>
                                )}
                              </div>
                            </label>
                          )}
                        />
                      ))}
                    </div>
                  </ScrollArea>
                </div>
                {errors.notebooks && (
                  <p className="text-sm text-red-600 mt-1">{errors.notebooks.message}</p>
                )}
              </div>

              {/* Transformation Selection */}
              <div className="space-y-3">
                <Label className="text-base font-medium">Transformations (optional)</Label>
                <div className="border rounded-md p-3 bg-gray-50">
                  <ScrollArea className="max-h-24">
                    <div className="space-y-2 pr-3">
                      {transformations.map((transformation: Transformation) => (
                        <Controller
                          key={transformation.id}
                          control={control}
                          name="transformations"
                          render={({ field }) => (
                            <label className="flex items-start gap-2 cursor-pointer">
                              <Checkbox
                                checked={field.value?.includes(transformation.id) || false}
                                onCheckedChange={(checked) => {
                                  const currentValue = field.value || []
                                  if (checked) {
                                    field.onChange([...currentValue, transformation.id])
                                  } else {
                                    field.onChange(currentValue.filter((id: string) => id !== transformation.id))
                                  }
                                }}
                                className="mt-1"
                              />
                              <div className="flex-1">
                                <span className="text-sm font-medium">{transformation.title}</span>
                                <p className="text-xs text-gray-600">{transformation.description}</p>
                              </div>
                            </label>
                          )}
                        />
                      ))}
                    </div>
                  </ScrollArea>
                </div>
              </div>

              {/* Processing Options */}
              <div className="space-y-3">
                <Label className="text-base font-medium mb-2 block">Processing Options</Label>
                
                <Controller
                  control={control}
                  name="embed"
                  render={({ field }) => (
                    <label className="flex items-start gap-2 cursor-pointer">
                      <Checkbox
                        checked={field.value}
                        onCheckedChange={field.onChange}
                        className="mt-1"
                      />
                      <div>
                        <span className="text-sm font-medium">Enable embedding for search</span>
                        <p className="text-xs text-gray-600">
                          Allows this source to be found in vector searches and AI queries
                        </p>
                      </div>
                    </label>
                  )}
                />
                
                <Controller
                  control={control}
                  name="async_processing"
                  render={({ field }) => (
                    <label className="flex items-start gap-2 cursor-pointer">
                      <Checkbox
                        checked={field.value}
                        onCheckedChange={field.onChange}
                        className="mt-1"
                      />
                      <div>
                        <span className="text-sm font-medium">Async processing (recommended)</span>
                        <p className="text-xs text-gray-600">
                          Process in the background for better performance
                        </p>
                      </div>
                    </label>
                  )}
                />
              </div>
            </div>
          </ScrollArea>

          {/* Footer */}
          <div className="flex justify-end gap-2 pt-4 border-t">
            <Button type="button" variant="outline" onClick={handleClose}>
              Cancel
            </Button>
            <Button 
              type="submit" 
              disabled={createSource.isPending || !selectedType}
              className="min-w-[120px]"
            >
              {createSource.isPending ? 'Creating...' : 'Add Source'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}