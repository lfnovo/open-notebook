'use client'

import { useState } from 'react'
import { Plus, FileText, Book, ChevronDown } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { AddSourceDialog } from '@/components/sources/AddSourceDialog'

interface AddButtonProps {
  variant?: 'default' | 'outline' | 'ghost'
  size?: 'sm' | 'default' | 'lg'
  className?: string
  iconOnly?: boolean
}

export function AddButton({
  variant = 'default',
  size = 'default',
  className,
  iconOnly = false
}: AddButtonProps) {
  const [sourceDialogOpen, setSourceDialogOpen] = useState(false)

  const handleAddSource = () => {
    setSourceDialogOpen(true)
  }

  const handleAddNotebook = () => {
    // TODO: Implement notebook creation when ready
  }

  if (iconOnly) {
    return (
      <>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant={variant}
              size={size}
              className={className}
            >
              <Plus className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" side="right">
            <DropdownMenuItem onClick={handleAddSource} className="gap-2">
              <FileText className="h-4 w-4" />
              Source
            </DropdownMenuItem>
            <DropdownMenuItem onClick={handleAddNotebook} className="gap-2">
              <Book className="h-4 w-4" />
              Notebook <span className="text-xs text-muted-foreground ml-auto">Coming soon</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        <AddSourceDialog
          open={sourceDialogOpen}
          onOpenChange={setSourceDialogOpen}
        />
      </>
    )
  }

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant={variant}
            size={size}
            className={className}
          >
            <Plus className="h-4 w-4 mr-2" />
            Add
            <ChevronDown className="h-3 w-3 ml-auto" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start">
          <DropdownMenuItem onClick={handleAddSource} className="gap-2">
            <FileText className="h-4 w-4" />
            Source
          </DropdownMenuItem>
          <DropdownMenuItem onClick={handleAddNotebook} className="gap-2">
            <Book className="h-4 w-4" />
            Notebook <span className="text-xs text-muted-foreground ml-auto">Coming soon</span>
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <AddSourceDialog
        open={sourceDialogOpen}
        onOpenChange={setSourceDialogOpen}
      />
    </>
  )
}