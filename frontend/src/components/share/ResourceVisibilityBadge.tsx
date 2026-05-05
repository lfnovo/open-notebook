'use client'

import { Eye, Lock, Users } from 'lucide-react'
import type { MouseEvent } from 'react'
import type { ResourceVisibility } from '@/lib/types/api'
import { cn } from '@/lib/utils'

interface ResourceVisibilityBadgeProps {
  visibility: ResourceVisibility
  labels: Record<ResourceVisibility, string>
  title: string
  onClick: (event: MouseEvent<HTMLButtonElement>) => void
  className?: string
  disabled?: boolean
}

const visibilityConfig = {
  public: {
    icon: Eye,
    className: 'bg-primary text-primary-foreground hover:bg-primary/90',
  },
  team: {
    icon: Users,
    className:
      'border border-primary/30 bg-secondary text-secondary-foreground hover:bg-primary hover:text-primary-foreground',
  },
  private: {
    icon: Lock,
    className:
      'border border-border bg-muted text-muted-foreground hover:bg-secondary hover:text-secondary-foreground',
  },
} satisfies Record<ResourceVisibility, { icon: typeof Eye; className: string }>

export function ResourceVisibilityBadge({
  visibility,
  labels,
  title,
  onClick,
  className,
  disabled = false,
}: ResourceVisibilityBadgeProps) {
  const config = visibilityConfig[visibility]
  const Icon = config.icon

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={cn(
        'inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold transition-colors',
        config.className,
        disabled && 'cursor-not-allowed opacity-60 hover:bg-muted hover:text-muted-foreground',
        className
      )}
      title={title}
    >
      <Icon className="h-3 w-3" />
      {labels[visibility]}
    </button>
  )
}
