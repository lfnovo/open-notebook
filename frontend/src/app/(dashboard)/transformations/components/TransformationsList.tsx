'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Plus } from 'lucide-react'
import { TransformationCard } from './TransformationCard'
import { EmptyState } from '@/components/common/EmptyState'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { Wand2 } from 'lucide-react'
import { Transformation } from '@/lib/types/transformations'
import { TransformationEditorDialog } from './TransformationEditorDialog'
import { useTranslation } from '@/lib/hooks/use-translation'

interface TransformationsListProps {
  transformations: Transformation[] | undefined
  isLoading: boolean
  onPlayground?: (transformation: Transformation) => void
}

export function TransformationsList({ transformations, isLoading, onPlayground }: TransformationsListProps) {
  const { t } = useTranslation()
  const [editorOpen, setEditorOpen] = useState(false)
  const [editingTransformation, setEditingTransformation] = useState<Transformation | undefined>()

  const handleOpenEditor = (trans?: Transformation) => {
    setEditingTransformation(trans)
    setEditorOpen(true)
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
        title={t.transformations.noTransformations}
        description={t.transformations.createOne}
        action={
          <Button onClick={() => handleOpenEditor()}>
            <Plus className="h-4 w-4 mr-2" />
            {t.transformations.createNew}
          </Button>
        }
      />
    )
  }

  return (
    <>
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <h2 className="text-lg font-semibold">{t.transformations.listTitle}</h2>
          <Button onClick={() => handleOpenEditor()}>
            <Plus className="h-4 w-4 mr-2" />
            {t.transformations.createNew}
          </Button>
        </div>

        <div className="space-y-4">
          {transformations.map((transformation) => (
            <TransformationCard
              key={transformation.id}
              transformation={transformation}
              onPlayground={onPlayground ? () => onPlayground(transformation) : undefined}
              onEdit={() => handleOpenEditor(transformation)}
            />
          ))}
        </div>
      </div>

      <TransformationEditorDialog
        open={editorOpen}
        onOpenChange={(open) => {
          setEditorOpen(open)
          if (!open) {
            setEditingTransformation(undefined)
          }
        }}
        transformation={editingTransformation}
      />
    </>
  )
}
