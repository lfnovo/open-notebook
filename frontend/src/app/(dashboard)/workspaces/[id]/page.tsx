'use client'

import { useParams } from 'next/navigation'
import { AppShell } from '@/components/layout/AppShell'
import { useWorkspace } from '@/lib/hooks/use-workspaces'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { FileText, StickyNote, MessageCircle } from 'lucide-react'

export default function WorkspaceDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { data: workspace, isLoading } = useWorkspace(id)

  if (isLoading) {
    return (
      <AppShell>
        <div className="flex items-center justify-center h-64">
          <LoadingSpinner />
        </div>
      </AppShell>
    )
  }

  if (!workspace) {
    return <AppShell><div className="p-6">Workspace not found</div></AppShell>
  }

  return (
    <AppShell>
      <div className="flex flex-col gap-4 p-6">
        <div>
          <h1 className="text-2xl font-bold">{workspace.name}</h1>
          {workspace.description && (
            <p className="text-muted-foreground mt-1">{workspace.description}</p>
          )}
        </div>
        <Tabs defaultValue="sources" className="w-full">
          <TabsList>
            <TabsTrigger value="sources">
              <FileText className="h-4 w-4 mr-2" />Sources
            </TabsTrigger>
            <TabsTrigger value="notes">
              <StickyNote className="h-4 w-4 mr-2" />Notes
            </TabsTrigger>
            <TabsTrigger value="chat">
              <MessageCircle className="h-4 w-4 mr-2" />Chat
            </TabsTrigger>
          </TabsList>
          <TabsContent value="sources">
            <div className="text-muted-foreground py-8 text-center">
              Sources tab — coming with full workspace integration
            </div>
          </TabsContent>
          <TabsContent value="notes">
            <div className="text-muted-foreground py-8 text-center">
              Notes tab — coming with full workspace integration
            </div>
          </TabsContent>
          <TabsContent value="chat">
            <div className="text-muted-foreground py-8 text-center">
              Chat tab — coming with full workspace integration
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </AppShell>
  )
}
