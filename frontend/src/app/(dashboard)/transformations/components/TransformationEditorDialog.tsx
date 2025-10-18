'use client'

import { useEffect } from 'react'
import { Controller, useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'
import { MarkdownEditor } from '@/components/ui/markdown-editor'
import { useCreateTransformation, useUpdateTransformation, useTransformation } from '@/lib/hooks/use-transformations'
import { Transformation } from '@/lib/types/transformations'
import { useQueryClient } from '@tanstack/react-query'
import { TRANSFORMATION_QUERY_KEYS } from '@/lib/hooks/use-transformations'

const transformationSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  title: z.string().optional(),
  description: z.string().optional(),
  prompt: z.string().min(1, 'Prompt is required'),
  apply_default: z.boolean().optional(),
})

type TransformationFormData = z.infer<typeof transformationSchema>

interface TransformationEditorDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  transformation?: Transformation
}

export function TransformationEditorDialog({ open, onOpenChange, transformation }: TransformationEditorDialogProps) {
  const isEditing = Boolean(transformation)
  const { data: fetchedTransformation, isLoading } = useTransformation(transformation?.id ?? '', {
    enabled: open && Boolean(transformation?.id),
  })
  const createTransformation = useCreateTransformation()
  const updateTransformation = useUpdateTransformation()
  const queryClient = useQueryClient()

  const {
    control,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<TransformationFormData>({
    resolver: zodResolver(transformationSchema),
    defaultValues: {
      name: '',
      title: '',
      description: '',
      prompt: '',
      apply_default: false,
    },
  })

  useEffect(() => {
    if (!open) {
      reset({ name: '', title: '', description: '', prompt: '', apply_default: false })
      return
    }

    const source = fetchedTransformation ?? transformation
    reset({
      name: source?.name ?? '',
      title: source?.title ?? '',
      description: source?.description ?? '',
      prompt: source?.prompt ?? '',
      apply_default: source?.apply_default ?? false,
    })
  }, [open, transformation, fetchedTransformation, reset])

  const onSubmit = async (data: TransformationFormData) => {
    if (transformation) {
      await updateTransformation.mutateAsync({
        id: transformation.id,
        data: {
          name: data.name,
          title: data.title || undefined,
          description: data.description || undefined,
          prompt: data.prompt,
          apply_default: Boolean(data.apply_default),
        },
      })
      queryClient.invalidateQueries({ queryKey: TRANSFORMATION_QUERY_KEYS.transformation(transformation.id) })
    } else {
      await createTransformation.mutateAsync({
        name: data.name,
        title: data.title || data.name,
        description: data.description || '',
        prompt: data.prompt,
        apply_default: Boolean(data.apply_default),
      })
    }

    reset()
    onOpenChange(false)
  }

  const handleClose = () => {
    reset()
    onOpenChange(false)
  }

  const isSaving = transformation ? updateTransformation.isPending : createTransformation.isPending

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-4xl w-full max-h-[90vh] overflow-hidden p-0">
        <DialogTitle className="sr-only">
          {isEditing ? 'Edit transformation' : 'Create transformation'}
        </DialogTitle>
        <form onSubmit={handleSubmit(onSubmit)} className="flex h-full flex-col">
          {isEditing && isLoading ? (
            <div className="flex-1 flex items-center justify-center py-10">
              <span className="text-sm text-muted-foreground">Loading transformation…</span>
            </div>
          ) : (
            <>
              <div className="border-b px-6 py-4 space-y-4">
                <div>
                  <Label htmlFor="transformation-name" className="text-sm font-medium">
                    Name
                  </Label>
                  <Controller
                    control={control}
                    name="name"
                    render={({ field }) => (
                      <Input
                        id="transformation-name"
                        {...field}
                        placeholder="Unique identifier, e.g. key_topics"
                      />
                    )}
                  />
                  {errors.name && (
                    <p className="text-sm text-red-600 mt-1">{errors.name.message}</p>
                  )}
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="transformation-title" className="text-sm font-medium">
                      Title
                    </Label>
                    <Controller
                      control={control}
                      name="title"
                      render={({ field }) => (
                        <Input
                          id="transformation-title"
                          {...field}
                          placeholder="Displayed title, defaults to name"
                        />
                      )}
                    />
                  </div>
                  <div className="flex items-center gap-2 pt-6 md:pt-8">
                    <Controller
                      control={control}
                      name="apply_default"
                      render={({ field }) => (
                        <Checkbox
                          id="transformation-default"
                          checked={field.value}
                          onCheckedChange={(checked) => field.onChange(Boolean(checked))}
                        />
                      )}
                    />
                    <Label htmlFor="transformation-default" className="text-sm">
                      Suggest by default on new sources
                    </Label>
                  </div>
                </div>

                <div>
                  <Label htmlFor="transformation-description" className="text-sm font-medium">
                    Description
                  </Label>
                  <Controller
                    control={control}
                    name="description"
                    render={({ field }) => (
                      <Textarea
                        id="transformation-description"
                        {...field}
                        placeholder="Describe what this transformation does."
                        rows={2}
                      />
                    )}
                  />
                </div>
              </div>

              <div className="flex-1 overflow-y-auto px-6 py-4">
                <Label className="text-sm font-medium">Prompt</Label>
                <Controller
                  control={control}
                  name="prompt"
                  render={({ field }) => (
                    <MarkdownEditor
                      key={transformation?.id ?? 'new-transformation'}
                      value={field.value}
                      onChange={field.onChange}
                      height={420}
                      placeholder="Write the prompt that will power this transformation..."
                      className="rounded-md border"
                    />
                  )}
                />
                {errors.prompt && (
                  <p className="text-sm text-red-600 mt-1">{errors.prompt.message}</p>
                )}
                <p className="text-xs text-muted-foreground mt-3">
                  Prompts should be written with the source content in mind. You can ask the model to
                  summarise, extract insights, or produce structured outputs such as tables.
                </p>
              </div>
            </>
          )}

          <div className="border-t px-6 py-4 flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={handleClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={isSaving || (isEditing && isLoading)}>
              {isSaving
                ? isEditing ? 'Saving…' : 'Creating…'
                : isEditing
                  ? 'Save Transformation'
                  : 'Create Transformation'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
