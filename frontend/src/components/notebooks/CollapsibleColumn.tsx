'use client'

import { ReactNode } from 'react'
import { Button } from '@/components/ui/button'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { ChevronLeft, LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'

interface CollapsibleColumnProps {
  isCollapsed: boolean
  onToggle: () => void
  collapsedIcon: LucideIcon
  collapsedLabel: string
  children: ReactNode
}

export function CollapsibleColumn({
  isCollapsed,
  onToggle,
  collapsedIcon: CollapsedIcon,
  collapsedLabel,
  children,
}: CollapsibleColumnProps) {
  if (isCollapsed) {
    return (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <button
              onClick={onToggle}
              className={cn(
                'flex flex-col items-center justify-center gap-3',
                'w-12 h-full min-h-0',
                'border rounded-lg',
                'bg-card hover:bg-accent/50',
                'transition-all duration-150',
                'cursor-pointer group',
                'py-6'
              )}
              aria-label={`Expand ${collapsedLabel}`}
            >
              <CollapsedIcon className="h-5 w-5 text-muted-foreground group-hover:text-foreground transition-colors flex-shrink-0" />
              <div
                className="text-xs font-medium text-muted-foreground group-hover:text-foreground transition-colors whitespace-nowrap"
                style={{ writingMode: 'vertical-rl', transform: 'rotate(180deg)', textOrientation: 'mixed' }}
              >
                {collapsedLabel}
              </div>
            </button>
          </TooltipTrigger>
          <TooltipContent side="right">
            <p>Expand {collapsedLabel}</p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    )
  }

  return (
    <div className="h-full min-h-0 transition-all duration-150">
      {children}
    </div>
  )
}

// Factory function to create a collapse button for card headers
export function createCollapseButton(onToggle: () => void, label: string) {
  return (
    <div className="hidden lg:block">
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              onClick={(e) => {
                e.stopPropagation()
                onToggle()
              }}
              className="h-7 w-7 hover:bg-accent"
              aria-label={`Collapse ${label}`}
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
          </TooltipTrigger>
          <TooltipContent>
            <p>Collapse {label}</p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    </div>
  )
}
