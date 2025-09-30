'use client'

import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { X } from 'lucide-react'
import { useCreateNotebook } from '@/lib/hooks/use-notebooks'

const createNotebookSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  description: z.string().optional(),
})

type CreateNotebookFormData = z.infer<typeof createNotebookSchema>

interface CreateNotebookFormProps {
  onClose: () => void
}

export function CreateNotebookForm({ onClose }: CreateNotebookFormProps) {
  const createNotebook = useCreateNotebook()
  const {
    register,
    handleSubmit,
    formState: { errors, isValid },
    reset
  } = useForm<CreateNotebookFormData>({
    resolver: zodResolver(createNotebookSchema),
  })

  const onSubmit = async (data: CreateNotebookFormData) => {
    await createNotebook.mutateAsync(data)
    reset()
    onClose()
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Create New Notebook</CardTitle>
            <CardDescription>
              Start organizing your research with a new notebook
            </CardDescription>
          </div>
          <Button variant="ghost" size="sm" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>
      </CardHeader>
      
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <Label htmlFor="name">Name *</Label>
            <Input
              id="name"
              {...register('name')}
              placeholder="Enter notebook name"
            />
            {errors.name && (
              <p className="text-sm text-red-600 mt-1">{errors.name.message}</p>
            )}
          </div>
          
          <div>
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              {...register('description')}
              placeholder="Describe the purpose and scope of this notebook..."
              rows={3}
            />
          </div>
          
          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button 
              type="submit" 
              disabled={!isValid || createNotebook.isPending}
            >
              {createNotebook.isPending ? 'Creating...' : 'Create Notebook'}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}