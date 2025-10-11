'use client'

import { useMemo } from 'react'
import { useNotebookChat } from '@/lib/hooks/useNotebookChat'
import { useSources } from '@/lib/hooks/use-sources'
import { useNotes } from '@/lib/hooks/use-notes'
import { ChatPanel } from '@/components/source/ChatPanel'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { Card, CardContent } from '@/components/ui/card'
import { AlertCircle } from 'lucide-react'
import { ContextSelections } from '../[id]/page'

interface ChatColumnProps {
  notebookId: string
  contextSelections: ContextSelections
}

export function ChatColumn({ notebookId, contextSelections }: ChatColumnProps) {
  // Fetch sources and notes for this notebook
  const { data: sources = [], isLoading: sourcesLoading } = useSources(notebookId)
  const { data: notes = [], isLoading: notesLoading } = useNotes(notebookId)

  // Initialize notebook chat hook
  const chat = useNotebookChat({
    notebookId,
    sources,
    notes,
    contextSelections
  })

  // Calculate context stats for indicator
  const contextStats = useMemo(() => {
    let sourcesInsights = 0
    let sourcesFull = 0
    let notesCount = 0

    // Count sources by mode
    sources.forEach(source => {
      const mode = contextSelections.sources[source.id]
      if (mode === 'insights') {
        sourcesInsights++
      } else if (mode === 'full') {
        sourcesFull++
      }
    })

    // Count notes that are included (not 'off')
    notes.forEach(note => {
      const mode = contextSelections.notes[note.id]
      if (mode === 'full') {
        notesCount++
      }
    })

    return {
      sourcesInsights,
      sourcesFull,
      notesCount,
      tokenCount: chat.tokenCount,
      charCount: chat.charCount
    }
  }, [sources, notes, contextSelections, chat.tokenCount, chat.charCount])

  // Show loading state while sources/notes are being fetched
  if (sourcesLoading || notesLoading) {
    return (
      <Card className="h-full flex flex-col">
        <CardContent className="flex-1 flex items-center justify-center">
          <LoadingSpinner size="lg" />
        </CardContent>
      </Card>
    )
  }

  // Show error state if data fetch failed (unlikely but good to handle)
  if (!sources && !notes) {
    return (
      <Card className="h-full flex flex-col">
        <CardContent className="flex-1 flex items-center justify-center">
          <div className="text-center text-muted-foreground">
            <AlertCircle className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p className="text-sm">Unable to load chat</p>
            <p className="text-xs mt-2">Please try refreshing the page</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <ChatPanel
      title="Chat with Notebook"
      contextType="notebook"
      messages={chat.messages}
      isStreaming={chat.isSending}
      contextIndicators={null}
      onSendMessage={(message, modelOverride) => chat.sendMessage(message, modelOverride)}
      modelOverride={chat.currentSession?.model_override ?? undefined}
      onModelChange={(model) => {
        if (chat.currentSessionId) {
          chat.updateSession(chat.currentSessionId, { model_override: model ?? null })
        }
      }}
      sessions={chat.sessions}
      currentSessionId={chat.currentSessionId}
      onCreateSession={(title) => chat.createSession(title)}
      onSelectSession={chat.switchSession}
      onUpdateSession={(sessionId, title) => chat.updateSession(sessionId, { title })}
      onDeleteSession={chat.deleteSession}
      loadingSessions={chat.loadingSessions}
      notebookContextStats={contextStats}
      notebookId={notebookId}
    />
  )
}
