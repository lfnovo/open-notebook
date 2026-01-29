'use client'

import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Upload, FileIcon } from 'lucide-react'

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { useCreateModule } from '@/lib/hooks/use-modules'
import { useCreateSource } from '@/lib/hooks/use-sources'
import type { ModuleResponse, CreateSourceRequest } from '@/lib/types/api'
import { useTranslation } from '@/lib/hooks/use-translation'
import { cn } from '@/lib/utils'

const createModuleSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  description: z.string().optional(),
})

type CreateModuleFormData = z.infer<typeof createModuleSchema>

interface CreateModuleDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onCreated?: (module: ModuleResponse) => void
}

export function CreateModuleDialog({ open, onOpenChange, onCreated }: CreateModuleDialogProps) {
  const { t } = useTranslation()
  const createModule = useCreateModule()
  const createSource = useCreateSource()
  const [files, setFiles] = useState<File[]>([])
  const [isUploading, setIsUploading] = useState(false)
  const {
    register,
    handleSubmit,
    formState: { errors, isValid },
    reset,
  } = useForm<CreateModuleFormData>({
    resolver: zodResolver(createModuleSchema),
    mode: 'onChange',
    defaultValues: {
      name: '',
      description: '',
    },
  })

  const closeDialog = () => {
    setFiles([])
    onOpenChange(false)
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = e.target.files
    if (selectedFiles) {
      setFiles(Array.from(selectedFiles))
    }
  }

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    const droppedFiles = e.dataTransfer.files
    if (droppedFiles.length > 0) {
      setFiles((prev) => [...prev, ...Array.from(droppedFiles)])
    }
  }

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
  }

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index))
  }

  const onSubmit = async (data: CreateModuleFormData) => {
    try {
      setIsUploading(true)
      // Create the module first
      const module = await createModule.mutateAsync(data)
      
      // Upload files as sources if any were selected
      if (files.length > 0 && module) {
        await Promise.allSettled(
          files.map((file) => {
            const createRequest = {
              type: 'upload' as const,
              modules: [module.id],
              embed: true,
              async_processing: true,
            } as CreateSourceRequest & { file?: File }
            createRequest.file = file
            return createSource.mutateAsync(createRequest)
          })
        )
      }

      if (module && onCreated) {
        onCreated(module)
      }
      closeDialog()
      reset()
    } catch (error) {
      console.error('Error creating module:', error)
    } finally {
      setIsUploading(false)
    }
  }

  useEffect(() => {
    if (!open) {
      reset()
      setFiles([])
    }
  }, [open, reset])

  const isSubmitting = createModule.isPending || isUploading

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle>{t.modules.createNew}</DialogTitle>
          <DialogDescription>
            {t.modules.createNewDesc}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="module-name">{t.modules.namePlaceholder} *</Label>
            <Input
              id="module-name"
              {...register('name')}
              placeholder={t.modules.namePlaceholder}
              autoComplete="off"
            />
            {errors.name && (
              <p className="text-sm text-destructive">{errors.name.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="module-description">{t.common.description}</Label>
            <Textarea
              id="module-description"
              {...register('description')}
              placeholder={t.modules.descPlaceholder}
              rows={4}
            />
          </div>

          {/* File upload area */}
          <div className="space-y-2">
            <Label htmlFor="module-files">{t.sources.fileLabel}</Label>
            <div
              className={cn(
                'border-2 border-dashed rounded-lg p-6 transition-colors',
                'hover:border-primary/50 cursor-pointer',
                files.length > 0 && 'border-primary'
              )}
              onDrop={handleDrop}
              onDragOver={handleDragOver}
            >
              <input
                id="module-files"
                type="file"
                multiple
                className="hidden"
                onChange={handleFileChange}
                accept=".pdf,.doc,.docx,.pptx,.ppt,.xlsx,.xls,.txt,.md,.epub,.mp4,.avi,.mov,.wmv,.mp3,.wav,.m4a,.aac,.jpg,.jpeg,.png,.tiff,.zip,.tar,.gz,.html"
              />
              <label htmlFor="module-files" className="cursor-pointer">
                <div className="flex flex-col items-center justify-center gap-2">
                  <Upload className="h-8 w-8 text-muted-foreground" />
                  <div className="text-center">
                    <span className="text-sm font-medium">
                      {files.length === 0
                        ? 'Upload or drop your files'
                        : `${files.length} file(s) selected`}
                    </span>
                    {files.length === 0 && (
                      <p className="text-xs text-muted-foreground mt-1">
                        *maximum 30Mb per file
                      </p>
                    )}
                  </div>
                </div>
              </label>
            </div>

            {/* Selected files list */}
            {files.length > 0 && (
              <div className="mt-2 space-y-2">
                {files.map((file, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between p-2 bg-muted rounded-md"
                  >
                    <div className="flex items-center gap-2 flex-1 min-w-0">
                      <FileIcon className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                      <span className="text-sm truncate">{file.name}</span>
                      <span className="text-xs text-muted-foreground flex-shrink-0">
                        ({(file.size / 1024 / 1024).toFixed(2)} MB)
                      </span>
                    </div>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => removeFile(index)}
                      className="h-6 w-6 p-0"
                    >
                      ×
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </div>

          <DialogFooter className="gap-2 sm:gap-0">
            <Button type="button" variant="outline" onClick={closeDialog} disabled={isSubmitting}>
              {t.common.cancel}
            </Button>
            <Button type="submit" disabled={!isValid || isSubmitting}>
              {isSubmitting ? t.common.creating : t.modules.createNew}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
