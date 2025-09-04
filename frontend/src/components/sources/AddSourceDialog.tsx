'use client'

import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { LoaderIcon } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { WizardContainer, WizardStep } from '@/components/ui/wizard-container'
import { SourceTypeStep } from './steps/SourceTypeStep'
import { NotebooksStep } from './steps/NotebooksStep'
import { ProcessingStep } from './steps/ProcessingStep'
import { useNotebooks } from '@/lib/hooks/use-notebooks'
import { useTransformations } from '@/lib/hooks/use-transformations'
import { useCreateSource } from '@/lib/hooks/use-sources'
import { CreateSourceRequest } from '@/lib/types/api'

const createSourceSchema = z.object({
  type: z.enum(['link', 'upload', 'text'], {
    required_error: 'Please select a source type',
  }),
  title: z.string().optional(),
  url: z.string().optional(),
  content: z.string().optional(),
  file: z.any().optional(),
  notebooks: z.array(z.string()).optional(),
  transformations: z.array(z.string()).optional(),
  embed: z.boolean(),
  async_processing: z.boolean(),
}).refine((data) => {
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

const WIZARD_STEPS: readonly WizardStep[] = [
  { number: 1, title: 'Source & Content', description: 'Choose type and add content' },
  { number: 2, title: 'Organization', description: 'Select notebooks' },
  { number: 3, title: 'Processing', description: 'Choose transformations and options' },
]

interface ProcessingState {
  message: string
  progress?: number
}

export function AddSourceDialog({ 
  open, 
  onOpenChange, 
  defaultNotebookId 
}: AddSourceDialogProps) {
  // Simplified state management
  const [currentStep, setCurrentStep] = useState(1)
  const [processing, setProcessing] = useState(false)
  const [processingStatus, setProcessingStatus] = useState<ProcessingState | null>(null)
  const [selectedNotebooks, setSelectedNotebooks] = useState<string[]>(
    defaultNotebookId ? [defaultNotebookId] : []
  )
  const [selectedTransformations, setSelectedTransformations] = useState<string[]>([])
  
  // API hooks
  const createSource = useCreateSource()
  const { data: notebooks = [], isLoading: notebooksLoading } = useNotebooks()
  const { data: transformations = [], isLoading: transformationsLoading } = useTransformations()

  // Form setup
  const {
    register,
    handleSubmit,
    control,
    watch,
    formState: { errors },
    reset,
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
  const watchedUrl = watch('url')
  const watchedContent = watch('content')
  const watchedFile = watch('file')

  // Step validation - now reactive with watched values
  const isStepValid = (step: number): boolean => {
    switch (step) {
      case 1:
        if (!selectedType) return false
        if (selectedType === 'link') {
          return !!watchedUrl && watchedUrl.trim() !== ''
        }
        if (selectedType === 'text') {
          return !!watchedContent && watchedContent.trim() !== ''
        }
        if (selectedType === 'upload') {
          if (watchedFile instanceof FileList) {
            return watchedFile.length > 0
          }
          return !!watchedFile
        }
        return true
      case 2:
      case 3:
        return true
      default:
        return false
    }
  }

  // Navigation
  const handleNextStep = (e?: React.MouseEvent) => {
    e?.preventDefault()
    e?.stopPropagation()
    if (currentStep < 3 && isStepValid(currentStep)) {
      setCurrentStep(currentStep + 1)
    }
  }

  const handlePrevStep = (e?: React.MouseEvent) => {
    e?.preventDefault()
    e?.stopPropagation()
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1)
    }
  }

  const handleStepClick = (step: number) => {
    if (step <= currentStep || (step === currentStep + 1 && isStepValid(currentStep))) {
      setCurrentStep(step)
    }
  }

  // Selection handlers
  const handleNotebookToggle = (notebookId: string) => {
    const updated = selectedNotebooks.includes(notebookId)
      ? selectedNotebooks.filter(id => id !== notebookId)
      : [...selectedNotebooks, notebookId]
    setSelectedNotebooks(updated)
  }

  const handleTransformationToggle = (transformationId: string) => {
    const updated = selectedTransformations.includes(transformationId)
      ? selectedTransformations.filter(id => id !== transformationId)
      : [...selectedTransformations, transformationId]
    setSelectedTransformations(updated)
  }

  // Form submission
  const onSubmit = async (data: CreateSourceFormData) => {
    try {
      setProcessing(true)
      setProcessingStatus({ message: 'Submitting source for processing...' })

      const createRequest: CreateSourceRequest = {
        type: data.type,
        notebooks: selectedNotebooks,
        url: data.type === 'link' ? data.url : undefined,
        content: data.type === 'text' ? data.content : undefined,
        title: data.title,
        transformations: selectedTransformations,
        embed: data.embed,
        delete_source: false,
        async_processing: true, // Always use async processing for frontend submissions
      }
      
      if (data.type === 'upload' && data.file) {
        const file = data.file instanceof FileList ? data.file[0] : data.file
        const requestWithFile = createRequest as CreateSourceRequest & { file?: File }
        requestWithFile.file = file
      }

      await createSource.mutateAsync(createRequest)

      setProcessingStatus({ 
        message: 'Source submitted for async processing. You can monitor progress in the sources list.',
        progress: 100 
      })
      setTimeout(() => handleClose(), 3000)
    } catch (error) {
      console.error('Error creating source:', error)
      setProcessingStatus({ 
        message: 'Error creating source. Please try again.',
      })
      setTimeout(() => {
        setProcessing(false)
        setProcessingStatus(null)
      }, 3000)
    }
  }

  // Dialog management
  const handleClose = () => {
    reset()
    setCurrentStep(1)
    setProcessing(false)
    setProcessingStatus(null)
    setSelectedNotebooks(defaultNotebookId ? [defaultNotebookId] : [])
    setSelectedTransformations([])
    onOpenChange(false)
  }

  // Processing view
  if (processing) {
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

  const currentStepValid = isStepValid(currentStep)

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[700px] p-0">
        <DialogHeader className="px-6 pt-6 pb-0">
          <DialogTitle>Add New Source</DialogTitle>
          <DialogDescription>
            Add content from links, uploads, or text to your notebooks.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)}>
          <WizardContainer
            currentStep={currentStep}
            steps={WIZARD_STEPS}
            onStepClick={handleStepClick}
            className="border-0"
          >
            {currentStep === 1 && (
              <SourceTypeStep
                control={control}
                register={register}
                errors={errors}
              />
            )}
            
            {currentStep === 2 && (
              <NotebooksStep
                notebooks={notebooks}
                selectedNotebooks={selectedNotebooks}
                onToggleNotebook={handleNotebookToggle}
                loading={notebooksLoading}
              />
            )}
            
            {currentStep === 3 && (
              <ProcessingStep
                control={control}
                transformations={transformations}
                selectedTransformations={selectedTransformations}
                onToggleTransformation={handleTransformationToggle}
                loading={transformationsLoading}
              />
            )}
          </WizardContainer>

          {/* Navigation */}
          <div className="flex justify-between items-center px-6 py-4 border-t bg-gray-50">
            <Button 
              type="button" 
              variant="outline" 
              onClick={handleClose}
            >
              Cancel
            </Button>

            <div className="flex gap-2">
              {currentStep > 1 && (
                <Button 
                  type="button" 
                  variant="outline"
                  onClick={handlePrevStep}
                >
                  Back
                </Button>
              )}
              
              {currentStep < 3 ? (
                <Button 
                  type="button"
                  onClick={(e) => handleNextStep(e)}
                  disabled={!currentStepValid}
                >
                  Next
                </Button>
              ) : (
                <Button 
                  type="submit" 
                  disabled={createSource.isPending || !selectedType}
                  className="min-w-[120px]"
                >
                  {createSource.isPending ? 'Creating...' : 'Add Source'}
                </Button>
              )}
            </div>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}