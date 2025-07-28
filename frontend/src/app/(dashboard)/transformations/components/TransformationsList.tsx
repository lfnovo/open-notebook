'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Plus } from 'lucide-react'
import { TransformationCard } from './TransformationCard'
import { EmptyState } from '@/components/common/EmptyState'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { Wand2 } from 'lucide-react'
import { Transformation } from '@/lib/types/transformations'
import { useCreateTransformation } from '@/lib/hooks/use-transformations'

interface TransformationsListProps {
  transformations: Transformation[] | undefined
  isLoading: boolean
  onPlayground?: (transformation: Transformation) => void
}

export function TransformationsList({ transformations, isLoading, onPlayground }: TransformationsListProps) {
  const [newTransformationId, setNewTransformationId] = useState<string | null>(null)
  const createTransformation = useCreateTransformation()

  const handleCreateTransformation = async () => {
    const result = await createTransformation.mutateAsync({
      name: 'New Transformation',
      title: 'New Transformation Title',
      description: 'New Transformation Description',
      prompt: 'New Transformation Prompt',
      apply_default: false
    })
    setNewTransformationId(result.id)
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  if (!transformations || transformations.length === 0) {
    return (
      <EmptyState
        icon={Wand2}
        title="No transformations yet"
        description="Create your first transformation to process and extract insights from your content."
        action={
          <Button onClick={handleCreateTransformation} disabled={createTransformation.isPending}>
            <Plus className="h-4 w-4 mr-2" />
            Create New Transformation
          </Button>
        }
      />
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-lg font-semibold">Your Transformations</h2>
        <Button onClick={handleCreateTransformation} disabled={createTransformation.isPending}>
          <Plus className="h-4 w-4 mr-2" />
          Create New Transformation
        </Button>
      </div>

      <div className="space-y-4">
        {transformations.map((transformation) => (
          <TransformationCard
            key={transformation.id}
            transformation={transformation}
            isExpanded={transformation.id === newTransformationId}
            onPlayground={onPlayground ? () => onPlayground(transformation) : undefined}
          />
        ))}
      </div>
    </div>
  )
}