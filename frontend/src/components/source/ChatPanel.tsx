'use client'

import { useState, useRef, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Bot, User, Send, Loader2, FileText, Lightbulb, StickyNote, Clock, Plus, Trash2, Edit2, Check, X } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { 
  SourceChatMessage, 
  SourceChatContextIndicator,
  SourceChatSession
} from '@/lib/types/api'
import { ModelSelector } from './ModelSelector'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
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
import { formatDistanceToNow } from 'date-fns'

interface ChatPanelProps {
  messages: SourceChatMessage[]
  isStreaming: boolean
  contextIndicators: SourceChatContextIndicator | null
  onSendMessage: (message: string, modelOverride?: string) => void
  modelOverride?: string
  onModelChange?: (model?: string) => void
  // Session management props
  sessions?: SourceChatSession[]
  currentSessionId?: string | null
  onCreateSession?: (title: string) => void
  onSelectSession?: (sessionId: string) => void
  onUpdateSession?: (sessionId: string, title: string) => void
  onDeleteSession?: (sessionId: string) => void
  loadingSessions?: boolean
}

export function ChatPanel({ 
  messages, 
  isStreaming, 
  contextIndicators,
  onSendMessage,
  modelOverride,
  onModelChange,
  sessions = [],
  currentSessionId,
  onCreateSession,
  onSelectSession,
  onUpdateSession,
  onDeleteSession,
  loadingSessions = false
}: ChatPanelProps) {
  const [input, setInput] = useState('')
  const [showNewSessionDialog, setShowNewSessionDialog] = useState(false)
  const [newSessionTitle, setNewSessionTitle] = useState('')
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null)
  const [editingSessionId, setEditingSessionId] = useState<string | null>(null)
  const [editTitle, setEditTitle] = useState('')
  const scrollAreaRef = useRef<HTMLDivElement>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = () => {
    if (input.trim() && !isStreaming) {
      onSendMessage(input.trim(), modelOverride)
      setInput('')
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    // Detect platform for correct modifier key
    const isMac = typeof navigator !== 'undefined' && navigator.userAgent.toUpperCase().indexOf('MAC') >= 0
    const isModifierPressed = isMac ? e.metaKey : e.ctrlKey

    if (e.key === 'Enter' && isModifierPressed) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleCreateSession = () => {
    if (newSessionTitle.trim() && onCreateSession) {
      onCreateSession(newSessionTitle.trim())
      setNewSessionTitle('')
      setShowNewSessionDialog(false)
    }
  }

  const handleDeleteConfirm = () => {
    if (deleteConfirmId && onDeleteSession) {
      onDeleteSession(deleteConfirmId)
      setDeleteConfirmId(null)
    }
  }

  const currentSession = sessions.find(s => s.id === currentSessionId)

  // Detect platform for placeholder text
  const isMac = typeof navigator !== 'undefined' && navigator.userAgent.toUpperCase().indexOf('MAC') >= 0
  const keyHint = isMac ? '⌘+Enter' : 'Ctrl+Enter'

  return (
    <>
    <Card className="flex flex-col h-full">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Bot className="h-5 w-5" />
            Chat with Source
          </CardTitle>
          <div className="flex items-center gap-2">
            {/* Session selector */}
            {onSelectSession && sessions.length > 0 && (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="sm" className="gap-2">
                    <Clock className="h-4 w-4" />
                    {currentSession ? (
                      <span className="text-xs max-w-[100px] truncate">
                        {currentSession.title}
                      </span>
                    ) : (
                      <span className="text-xs">Sessions</span>
                    )}
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-[250px]">
                  {sessions.map((session) => (
                    <DropdownMenuItem
                      key={session.id}
                      onClick={() => onSelectSession(session.id)}
                      className={currentSessionId === session.id ? 'bg-accent' : ''}
                    >
                      <div className="flex-1">
                        <div className="font-medium text-sm truncate">
                          {session.title}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {formatDistanceToNow(new Date(session.created), { addSuffix: true })}
                        </div>
                      </div>
                    </DropdownMenuItem>
                  ))}
                </DropdownMenuContent>
              </DropdownMenu>
            )}
            
            {/* New session button */}
            {onCreateSession && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowNewSessionDialog(true)}
              >
                <Plus className="h-4 w-4" />
              </Button>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent className="flex-1 flex flex-col min-h-0 p-0">
        <ScrollArea className="flex-1 px-4" ref={scrollAreaRef}>
          <div className="space-y-4 py-4">
            {messages.length === 0 ? (
              <div className="text-center text-muted-foreground py-8">
                <Bot className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p className="text-sm">Start a conversation about this source</p>
                <p className="text-xs mt-2">Ask questions to understand the content better</p>
              </div>
            ) : (
              messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex gap-3 ${
                    message.type === 'human' ? 'justify-end' : 'justify-start'
                  }`}
                >
                  {message.type === 'ai' && (
                    <div className="flex-shrink-0">
                      <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
                        <Bot className="h-4 w-4" />
                      </div>
                    </div>
                  )}
                  <div
                    className={`rounded-lg px-4 py-2 max-w-[80%] ${
                      message.type === 'human'
                        ? 'bg-primary text-primary-foreground'
                        : 'bg-muted'
                    }`}
                  >
                    {message.type === 'ai' ? (
                      <div className="prose prose-sm prose-neutral dark:prose-invert max-w-none prose-headings:font-semibold prose-a:text-blue-600 prose-code:bg-muted prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-p:mb-4 prose-p:leading-7 prose-li:mb-2">
                        <ReactMarkdown
                          components={{
                            p: ({ children }) => <p className="mb-4">{children}</p>,
                            h1: ({ children }) => <h1 className="mb-4 mt-6">{children}</h1>,
                            h2: ({ children }) => <h2 className="mb-3 mt-5">{children}</h2>,
                            h3: ({ children }) => <h3 className="mb-3 mt-4">{children}</h3>,
                            h4: ({ children }) => <h4 className="mb-2 mt-4">{children}</h4>,
                            h5: ({ children }) => <h5 className="mb-2 mt-3">{children}</h5>,
                            h6: ({ children }) => <h6 className="mb-2 mt-3">{children}</h6>,
                            li: ({ children }) => <li className="mb-1">{children}</li>,
                            ul: ({ children }) => <ul className="mb-4 space-y-1">{children}</ul>,
                            ol: ({ children }) => <ol className="mb-4 space-y-1">{children}</ol>,
                          }}
                        >
                          {message.content}
                        </ReactMarkdown>
                      </div>
                    ) : (
                      <p className="text-sm">{message.content}</p>
                    )}
                  </div>
                  {message.type === 'human' && (
                    <div className="flex-shrink-0">
                      <div className="h-8 w-8 rounded-full bg-primary flex items-center justify-center">
                        <User className="h-4 w-4 text-primary-foreground" />
                      </div>
                    </div>
                  )}
                </div>
              ))
            )}
            {isStreaming && (
              <div className="flex gap-3 justify-start">
                <div className="flex-shrink-0">
                  <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
                    <Bot className="h-4 w-4" />
                  </div>
                </div>
                <div className="rounded-lg px-4 py-2 bg-muted">
                  <Loader2 className="h-4 w-4 animate-spin" />
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        </ScrollArea>

        {/* Context Indicators */}
        {contextIndicators && (
          <div className="border-t px-4 py-2">
            <div className="flex flex-wrap gap-2 text-xs">
              {contextIndicators.sources?.length > 0 && (
                <Badge variant="outline" className="gap-1">
                  <FileText className="h-3 w-3" />
                  {contextIndicators.sources.length} source{contextIndicators.sources.length > 1 ? 's' : ''}
                </Badge>
              )}
              {contextIndicators.insights?.length > 0 && (
                <Badge variant="outline" className="gap-1">
                  <Lightbulb className="h-3 w-3" />
                  {contextIndicators.insights.length} insight{contextIndicators.insights.length > 1 ? 's' : ''}
                </Badge>
              )}
              {contextIndicators.notes?.length > 0 && (
                <Badge variant="outline" className="gap-1">
                  <StickyNote className="h-3 w-3" />
                  {contextIndicators.notes.length} note{contextIndicators.notes.length > 1 ? 's' : ''}
                </Badge>
              )}
            </div>
          </div>
        )}

        {/* Input Area */}
        <div className="border-t p-4 space-y-3">
          {/* Model selector */}
          {onModelChange && (
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">Model</span>
              <ModelSelector
                currentModel={modelOverride}
                onModelChange={onModelChange}
                disabled={isStreaming}
              />
            </div>
          )}
          
          <div className="flex gap-2 items-end">
            <Textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={`Ask a question about this source... (${keyHint} to send)`}
              disabled={isStreaming}
              className="flex-1 min-h-[40px] max-h-[100px] resize-none py-2 px-3"
              rows={1}
            />
            <Button
              onClick={handleSend}
              disabled={!input.trim() || isStreaming}
              size="icon"
              className="h-[40px] w-[40px] flex-shrink-0"
            >
              {isStreaming ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>

    {/* New Session Dialog */}
    <AlertDialog open={showNewSessionDialog} onOpenChange={setShowNewSessionDialog}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Create New Chat Session</AlertDialogTitle>
          <AlertDialogDescription>
            Start a new conversation about this source. Give it a memorable title.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <div className="py-4">
          <Input
            value={newSessionTitle}
            onChange={(e) => setNewSessionTitle(e.target.value)}
            placeholder="Session title..."
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                e.preventDefault()
                handleCreateSession()
              }
            }}
          />
        </div>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction onClick={handleCreateSession}>
            Create Session
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>

    {/* Delete Confirmation Dialog */}
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