'use client'

import { useRouter } from 'next/navigation'
import { NotebookResponse } from '@/lib/types/api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { MoreHorizontal, Archive, ArchiveRestore, Trash2, FileText, StickyNote, Lock, User } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useUpdateNotebook } from '@/lib/hooks/use-notebooks'
import { NotebookDeleteDialog } from './NotebookDeleteDialog'
import { useState } from 'react'
import { useTranslation } from '@/lib/hooks/use-translation'
import { getDateLocale } from '@/lib/utils/date-locale'
import { ShareDialog } from '@/components/share/ShareDialog'
import { ResourceVisibilityBadge } from '@/components/share/ResourceVisibilityBadge'
import { useProfile } from '@/lib/hooks/use-profile'

interface NotebookCardProps {
  notebook: NotebookResponse
}

export function NotebookCard({ notebook }: NotebookCardProps) {
  const { t, language } = useTranslation()
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)
  const [showShareDialog, setShowShareDialog] = useState(false)
  const [visibility, setVisibility] = useState(notebook.visibility)
  const router = useRouter()
  const updateNotebook = useUpdateNotebook()
  const { data: profile } = useProfile()
  const creatorLabel = notebook.creator_username || notebook.creator_name
  const canDeleteNotebook = !notebook.owner_id || profile?.id === notebook.owner_id

  const tVisibilityPrivate = t.visibility?.private ?? 'Private'
  const tVisibilityTeam = t.visibility?.team ?? 'Team'
  const tVisibilityPublic = t.visibility?.public ?? 'Public'
  const visibilityLabels = {
    private: tVisibilityPrivate,
    team: tVisibilityTeam,
    public: tVisibilityPublic,
  }

  const handleArchiveToggle = (e: React.MouseEvent) => {
    e.stopPropagation()
    updateNotebook.mutate({
      id: notebook.id,
      data: { archived: !notebook.archived }
    })
  }

  const handleShare = (e: React.MouseEvent) => {
    e.stopPropagation()
    setShowShareDialog(true)
  }

  const handleCardClick = () => {
    router.push(`/notebooks/${encodeURIComponent(notebook.id)}`)
  }

  return (
    <>
      <Card 
        className="group card-hover"
        onClick={handleCardClick}
        style={{ cursor: 'pointer' }}
      >
          <CardHeader className="pb-3">
            <div className="flex items-start justify-between">
              <div className="flex-1 min-w-0 flex items-center gap-2">
                <CardTitle className="text-base truncate group-hover:text-primary transition-colors flex items-center gap-1.5">
                  {notebook.password && <Lock className="h-4 w-4 text-muted-foreground shrink-0" />}
                  {notebook.name}
                </CardTitle>
                {notebook.archived && (
                  <Badge variant="secondary" className="mt-1 shrink-0">
                    {t.notebooks.archived}
                  </Badge>
                )}
              </div>
              
              <div className="flex items-center gap-1 shrink-0" onClick={(e) => e.stopPropagation()}>
                <ResourceVisibilityBadge
                  visibility={visibility}
                  labels={visibilityLabels}
                  title={t.sharing?.title || 'Share'}
                  onClick={handleShare}
                />

                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="opacity-0 group-hover:opacity-100 transition-opacity"
                      aria-label={t.notebooks.actions}
                    >
                      <MoreHorizontal className="h-4 w-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem onClick={handleArchiveToggle}>
                      {notebook.archived ? (
                        <>
                          <ArchiveRestore className="h-4 w-4 mr-2" />
                          {t.notebooks.unarchive}
                        </>
                      ) : (
                        <>
                          <Archive className="h-4 w-4 mr-2" />
                          {t.notebooks.archive}
                        </>
                      )}
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      disabled={!canDeleteNotebook}
                      onClick={(e) => {
                        if (!canDeleteNotebook) return
                        e.stopPropagation()
                        setShowDeleteDialog(true)
                      }}
                      className="text-red-600"
                    >
                      <Trash2 className="h-4 w-4 mr-2" />
                      {t.common.delete}
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            </div>
          </CardHeader>
          
          <CardContent>
            <CardDescription className="line-clamp-2 text-sm">
              {notebook.description || t.chat.noDescription}
            </CardDescription>

            <div className="mt-3 flex items-center justify-between text-xs text-muted-foreground">
              <span>
                {t.common.updated.replace('{time}', formatDistanceToNow(new Date(notebook.updated), { 
                  addSuffix: true,
                  locale: getDateLocale(language)
                }))}
              </span>
              {creatorLabel && (
                <span className="flex items-center gap-1">
                  <User className="h-3 w-3" />
                  {t.notebooks.createdBy}: {creatorLabel}
                </span>
              )}
            </div>

            {/* Item counts footer */}
            <div className="mt-3 flex items-center gap-1.5 border-t pt-3">
              <Badge variant="outline" className="text-xs flex items-center gap-1 px-1.5 py-0.5 text-primary border-primary/50">
                <FileText className="h-3 w-3" />
                <span>{notebook.source_count}</span>
              </Badge>
              <Badge variant="outline" className="text-xs flex items-center gap-1 px-1.5 py-0.5 text-primary border-primary/50">
                <StickyNote className="h-3 w-3" />
                <span>{notebook.note_count}</span>
              </Badge>
            </div>
          </CardContent>
      </Card>

      <NotebookDeleteDialog
        open={showDeleteDialog}
        onOpenChange={setShowDeleteDialog}
        notebookId={notebook.id}
        notebookName={notebook.name}
      />

      <ShareDialog
        open={showShareDialog}
        onOpenChange={setShowShareDialog}
        resourceType="notebook"
        resourceId={notebook.id}
        resourceTitle={notebook.name}
        resourceVisibility={visibility}
        onChanged={setVisibility}
      />
    </>
  )
}
