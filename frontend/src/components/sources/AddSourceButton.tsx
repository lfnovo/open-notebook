'use client'

import { useState } from 'react'
import { PlusIcon } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { AddSourceDialog } from './AddSourceDialog'

interface AddSourceButtonProps {
  defaultNotebookId?: string
  variant?: 'default' | 'outline' | 'ghost'
  size?: 'sm' | 'default' | 'lg'
  className?: string
  iconOnly?: boolean
}

export function AddSourceButton({ 
  defaultNotebookId, 
  variant = 'default',
  size = 'default',
  className,
  iconOnly = false
}: AddSourceButtonProps) {
  const [dialogOpen, setDialogOpen] = useState(false)

  return (
    <>
      <Button
        onClick={() => setDialogOpen(true)}
        variant={variant}
        size={size}
        className={className}
      >
        <PlusIcon className={iconOnly ? "h-4 w-4" : "h-4 w-4 mr-2"} />
        {!iconOnly && "Add Source"}
      </Button>

      <AddSourceDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        defaultNotebookId={defaultNotebookId}
      />
    </>
  )
}