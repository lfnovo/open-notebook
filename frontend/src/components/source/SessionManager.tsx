'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Badge } from '@/components/ui/badge'
import { 
  MessageSquare, 
  Plus, 
  Trash2, 
  Edit2, 
  Check,
  X,
  Clock
} from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { BaseChatSession } from '@/lib/types/api'

interface SessionManagerProps {
  sessions: BaseChatSession[]
  currentSessionId: string | null
  onCreateSession: (title: string) => void
  onSelectSession: (sessionId: string) => void
  onUpdateSession: (sessionId: string, title: string) => void
  onDeleteSession: (sessionId: string) => void
  loadingSessions: boolean
}

export function SessionManager({
  sessions,
  currentSessionId,
  onCreateSession,
  onSelectSession,
  onUpdateSession,
  onDeleteSession,
  loadingSessions
}: SessionManagerProps) {
  const [isCreating, setIsCreating] = useState(false)
  const [newSessionTitle, setNewSessionTitle] = useState('')
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editTitle, setEditTitle] = useState('')
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null)

  const handleCreateSession = () => {
    if (newSessionTitle.trim()) {
      onCreateSession(newSessionTitle.trim())
      setNewSessionTitle('')
      setIsCreating(false)
    }
  }

  const handleStartEdit = (session: BaseChatSession) => {
    setEditingId(session.id)
    setEditTitle(session.title)
  }

  const handleSaveEdit = () => {
    if (editingId && editTitle.trim()) {
      onUpdateSession(editingId, editTitle.trim())
      setEditingId(null)
      setEditTitle('')
    }
  }

  const handleCancelEdit = () => {
    setEditingId(null)
    setEditTitle('')
  }

  const handleDeleteConfirm = () => {
    if (deleteConfirmId) {
      onDeleteSession(deleteConfirmId)
      setDeleteConfirmId(null)
    }
  }

  return (
    <>
      <Card className="h-full flex flex-col">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center justify-between">
            <span className="flex items-center gap-2">
              <MessageSquare className="h-5 w-5" />
              Chat Sessions
            </span>
            <Button
              size="sm"
              variant="outline"
              onClick={() => setIsCreating(true)}
            >
              <Plus className="h-4 w-4" />
            </Button>
          </CardTitle>
        </CardHeader>
        <CardContent className="flex-1 p-0 min-h-0">
          <ScrollArea className="h-full px-4">
            {isCreating && (
              <div className="p-3 border rounded-lg mb-3">
                <Input
                  value={newSessionTitle}
                  onChange={(e) => setNewSessionTitle(e.target.value)}
                  placeholder="Session title..."
                  className="mb-2"
                  autoFocus
                  onKeyPress={(e) => {
                    if (e.key === 'Enter') handleCreateSession()
                  }}
                />
                <div className="flex gap-2">
                  <Button size="sm" onClick={handleCreateSession}>
                    Create
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      setIsCreating(false)
                      setNewSessionTitle('')
                    }}
                  >
                    Cancel
                  </Button>
                </div>
              </div>
            )}

            {loadingSessions ? (
              <div className="text-center py-8 text-muted-foreground">
                Loading sessions...
              </div>
            ) : sessions.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <MessageSquare className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p className="text-sm">No chat sessions yet</p>
                <p className="text-xs mt-2">Create a session to start chatting</p>
              </div>
            ) : (
              <div className="space-y-2 pb-4">
                {sessions.map((session) => (
                  <div
                    key={session.id}
                    className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                      currentSessionId === session.id
                        ? 'bg-primary/10 border-primary'
                        : 'hover:bg-muted'
                    }`}
                    onClick={() => onSelectSession(session.id)}
                  >
                    {editingId === session.id ? (
                      <div className="space-y-2" onClick={(e) => e.stopPropagation()}>
                        <Input
                          value={editTitle}
                          onChange={(e) => setEditTitle(e.target.value)}
                          onKeyPress={(e) => {
                            if (e.key === 'Enter') handleSaveEdit()
                            if (e.key === 'Escape') handleCancelEdit()
                          }}
                          autoFocus
                        />
                        <div className="flex gap-2">
                          <Button size="sm" onClick={handleSaveEdit}>
                            <Check className="h-3 w-3" />
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={handleCancelEdit}
                          >
                            <X className="h-3 w-3" />
                          </Button>
                        </div>
                      </div>
                    ) : (
                      <>
                        <div className="flex items-start justify-between mb-1">
                          <h4 className="font-medium text-sm">
                            {session.title}
                          </h4>
                          <div className="flex gap-1" onClick={(e) => e.stopPropagation()}>
                            <Button
                              size="sm"
                              variant="ghost"
                              className="h-6 w-6 p-0"
                              onClick={() => handleStartEdit(session)}
                            >
                              <Edit2 className="h-3 w-3" />
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              className="h-6 w-6 p-0"
                              onClick={() => setDeleteConfirmId(session.id)}
                            >
                              <Trash2 className="h-3 w-3" />
                            </Button>
                          </div>
                        </div>
                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                          <Clock className="h-3 w-3" />
                          {formatDistanceToNow(new Date(session.created), { addSuffix: true })}
                        </div>
                        {session.message_count && session.message_count > 0 && (
                          <Badge variant="secondary" className="mt-2 text-xs">
                            {session.message_count} messages
                          </Badge>
                        )}
                        {session.model_override && (
                          <Badge variant="outline" className="mt-2 ml-2 text-xs">
                            {session.model_override}
                          </Badge>
                        )}
                      </>
                    )}
                  </div>
                ))}
              </div>
            )}
          </ScrollArea>
        </CardContent>
      </Card>

      <AlertDialog open={!!deleteConfirmId} onOpenChange={() => setDeleteConfirmId(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Chat Session?</AlertDialogTitle>
            <AlertDialogDescription>
              This action cannot be undone. All messages in this session will be permanently deleted.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleDeleteConfirm}>
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}