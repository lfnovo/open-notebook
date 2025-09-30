'use client'

import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
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
import { useCreateNote } from '@/lib/hooks/use-notes'

const createNoteSchema = z.object({
  title: z.string().optional(),
  content: z.string().min(1, 'Content is required'),
})

type CreateNoteFormData = z.infer<typeof createNoteSchema>

interface AddNoteDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  notebookId: string
}

export function AddNoteDialog({ open, onOpenChange, notebookId }: AddNoteDialogProps) {
  const createNote = useCreateNote()
  const {
    register,
    handleSubmit,
    formState: { errors },
    reset
  } = useForm<CreateNoteFormData>({
    resolver: zodResolver(createNoteSchema),
  })

  const onSubmit = async (data: CreateNoteFormData) => {
    await createNote.mutateAsync({
      title: data.title || undefined,
      content: data.content,
      note_type: 'human',
      notebook_id: notebookId,
    })
    reset()
    onOpenChange(false)
  }

  const handleClose = () => {
    reset()
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[550px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Create New Note</DialogTitle>
          <DialogDescription>
            Write a note to capture your thoughts and insights.
          </DialogDescription>
        </DialogHeader>
        
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <Label htmlFor="title" className="mb-2 block">Title (optional)</Label>
            <Input
              id="title"
              {...register('title')}
              placeholder="Enter note title"
            />
          </div>
          
          <div>
            <Label htmlFor="content" className="mb-2 block">Content *</Label>
            <Textarea
              id="content"
              {...register('content')}
              placeholder="Write your note content here..."
              rows={10}
              className="min-h-[200px] resize-y"
            />
            {errors.content && (
              <p className="text-sm text-red-600 mt-1">{errors.content.message}</p>
            )}
          </div>
          
          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={handleClose}>
              Cancel
            </Button>
            <Button 
              type="submit" 
              disabled={createNote.isPending}
            >
              {createNote.isPending ? 'Creating...' : 'Create Note'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}