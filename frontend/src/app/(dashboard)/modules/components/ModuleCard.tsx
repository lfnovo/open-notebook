'use client'

import { useRouter } from 'next/navigation'
import { ModuleResponse } from '@/lib/types/api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { MoreHorizontal, Archive, ArchiveRestore, Trash2, FileText, StickyNote } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useUpdateModule, useDeleteModule } from '@/lib/hooks/use-modules'
import { ConfirmDialog } from '@/components/common/ConfirmDialog'
import { useState } from 'react'
import { useTranslation } from '@/lib/hooks/use-translation'
import { getDateLocale } from '@/lib/utils/date-locale'
interface ModuleCardProps {
  module: ModuleResponse
}

export function ModuleCard({ module }: ModuleCardProps) {
  const { t, language } = useTranslation()
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)
  const router = useRouter()
  const updateModule = useUpdateModule()
  const deleteModule = useDeleteModule()

  const handleArchiveToggle = (e: React.MouseEvent) => {
    e.stopPropagation()
    updateModule.mutate({
      id: module.id,
      data: { archived: !module.archived }
    })
  }

  const handleDelete = () => {
    deleteModule.mutate(module.id)
    setShowDeleteDialog(false)
  }

  const handleCardClick = () => {
    router.push(`/modules/${encodeURIComponent(module.id)}`)
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
              <div className="flex-1 min-w-0">
                <CardTitle className="text-base truncate group-hover:text-primary transition-colors">
                  {module.name}
                </CardTitle>
                {module.archived && (
                  <Badge variant="secondary" className="mt-1">
                    {t.modules.archived}
                  </Badge>
                )}
              </div>
              
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="opacity-0 group-hover:opacity-100 transition-opacity"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <MoreHorizontal className="h-4 w-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" onClick={(e) => e.stopPropagation()}>
                  <DropdownMenuItem onClick={handleArchiveToggle}>
                    {module.archived ? (
                      <>
                        <ArchiveRestore className="h-4 w-4 mr-2" />
                        {t.modules.unarchive}
                      </>
                    ) : (
                      <>
                        <Archive className="h-4 w-4 mr-2" />
                        {t.modules.archive}
                      </>
                    )}
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    onClick={(e) => {
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
          </CardHeader>
          
          <CardContent>
            <CardDescription className="line-clamp-2 text-sm">
              {module.description || t.chat.noDescription}
            </CardDescription>

            <div className="mt-3 text-xs text-muted-foreground">
              {t.common.updated.replace('{time}', formatDistanceToNow(new Date(module.updated), { 
                addSuffix: true,
                locale: getDateLocale(language)
              }))}
            </div>

            {/* Item counts footer */}
            <div className="mt-3 flex items-center gap-1.5 border-t pt-3">
              <Badge variant="outline" className="text-xs flex items-center gap-1 px-1.5 py-0.5 text-primary border-primary/50">
                <FileText className="h-3 w-3" />
                <span>{module.source_count}</span>
              </Badge>
              <Badge variant="outline" className="text-xs flex items-center gap-1 px-1.5 py-0.5 text-primary border-primary/50">
                <StickyNote className="h-3 w-3" />
                <span>{module.note_count}</span>
              </Badge>
            </div>
          </CardContent>
      </Card>

      <ConfirmDialog
        open={showDeleteDialog}
        onOpenChange={setShowDeleteDialog}
        title={t.modules.deleteModule}
        description={t.modules.deleteModuleDesc.replace('{name}', module.name)}
        confirmText={t.common.delete}
        confirmVariant="destructive"
        onConfirm={handleDelete}
      />
    </>
  )
}