'use client'

import Link from 'next/link'
import { Workspace } from '@/lib/api/workspaces'
import { Badge } from '@/components/ui/badge'
import { Card, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { FolderOpen, Lock, Users, Globe } from 'lucide-react'

const visibilityConfig = {
  private: { label: 'Private', icon: Lock, variant: 'secondary' as const },
  shared: { label: 'Shared', icon: Users, variant: 'default' as const },
  community: { label: 'Community', icon: Globe, variant: 'outline' as const },
}

interface WorkspaceCardProps {
  workspace: Workspace
}

export function WorkspaceCard({ workspace }: WorkspaceCardProps) {
  const config = visibilityConfig[workspace.visibility] ?? visibilityConfig.private
  const VisibilityIcon = config.icon

  return (
    <Link href={`/workspaces/${workspace.id}`}>
      <Card className="hover:bg-accent/50 transition-colors cursor-pointer">
        <CardHeader>
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-2">
              <FolderOpen className="h-5 w-5 text-muted-foreground" />
              <CardTitle className="text-base">{workspace.name}</CardTitle>
            </div>
            <Badge variant={config.variant} className="text-xs">
              <VisibilityIcon className="h-3 w-3 mr-1" />
              {config.label}
            </Badge>
          </div>
          {workspace.description && (
            <CardDescription className="line-clamp-2">{workspace.description}</CardDescription>
          )}
        </CardHeader>
      </Card>
    </Link>
  )
}
