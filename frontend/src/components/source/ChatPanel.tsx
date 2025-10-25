'use client'

import { useState, useRef, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog'
import { Bot, User, Send, Loader2, FileText, Lightbulb, StickyNote, Clock } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import {
  SourceChatMessage,
  SourceChatContextIndicator,
  BaseChatSession
} from '@/lib/types/api'
import { ModelSelector } from './ModelSelector'
import { ContextIndicator } from '@/components/common/ContextIndicator'
import { SessionManager } from '@/components/source/SessionManager'
import { MessageActions } from '@/components/source/MessageActions'
import { convertReferencesToCompactMarkdown, createCompactReferenceLinkComponent } from '@/lib/utils/source-references'
import { useModalManager } from '@/lib/hooks/use-modal-manager'
import { toast } from 'sonner'

interface NotebookContextStats {
  sourcesInsights: number
  sourcesFull: number
  notesCount: number
  tokenCount?: number
  charCount?: number
}

interface ChatPanelProps {
  messages: SourceChatMessage[]
  isStreaming: boolean
  contextIndicators: SourceChatContextIndicator | null
  onSendMessage: (message: string, modelOverride?: string) => void
  modelOverride?: string
  onModelChange?: (model?: string) => void
  // Session management props
  sessions?: BaseChatSession[]
  currentSessionId?: string | null
  onCreateSession?: (title: string) => void
  onSelectSession?: (sessionId: string) => void
  onDeleteSession?: (sessionId: string) => void
  onUpdateSession?: (sessionId: string, title: string) => void
  loadingSessions?: boolean
  // Generic props for reusability
  title?: string
  contextType?: 'source' | 'notebook'
  // Notebook context stats (for notebook chat)
  notebookContextStats?: NotebookContextStats
  // Notebook ID for saving notes
  notebookId?: string
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
  onDeleteSession,
  onUpdateSession,
  loadingSessions = false,
  title = 'Chat with Source',
  contextType = 'source',
  notebookContextStats,
  notebookId
}: ChatPanelProps) {
  const [input, setInput] = useState('')
  const [sessionManagerOpen, setSessionManagerOpen] = useState(false)
  const scrollAreaRef = useRef<HTMLDivElement>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const { openModal } = useModalManager()

  const handleReferenceClick = (type: string, id: string) => {
    const modalType = type === 'source_insight' ? 'insight' : type as 'source' | 'note' | 'insight'

    try {
      openModal(modalType, id)
      // Note: The modal system uses URL parameters and doesn't throw errors for missing items.
      // The modal component itself will handle displaying "not found" states.
      // This try-catch is here for future enhancements or unexpected errors.
    } catch {
      const typeLabel = type === 'source_insight' ? 'insight' : type
      toast.error(`This ${typeLabel} could not be found`)
    }
  }

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

  // Detect platform for placeholder text
  const isMac = typeof navigator !== 'undefined' && navigator.userAgent.toUpperCase().indexOf('MAC') >= 0
  const keyHint = isMac ? '⌘+Enter' : 'Ctrl+Enter'

  return (
    <>
    <Card className="flex flex-col h-full flex-1 overflow-hidden">
      <CardHeader className="pb-3 flex-shrink-0">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Bot className="h-5 w-5" />
            {title}
          </CardTitle>
          {onSelectSession && onCreateSession && onDeleteSession && (
            <Dialog open={sessionManagerOpen} onOpenChange={setSessionManagerOpen}>
              <Button
                variant="ghost"
                size="sm"
                className="gap-2"
                onClick={() => setSessionManagerOpen(true)}
                disabled={loadingSessions}
              >
                <Clock className="h-4 w-4" />
                <span className="text-xs">Sessions</span>
              </Button>
              <DialogContent className="sm:max-w-[420px] p-0 overflow-hidden">
                <DialogTitle className="sr-only">Chat Sessions</DialogTitle>
                <SessionManager
                  sessions={sessions}
                  currentSessionId={currentSessionId ?? null}
                  onCreateSession={(title) => onCreateSession?.(title)}
                  onSelectSession={(sessionId) => {
                    onSelectSession(sessionId)
                    setSessionManagerOpen(false)
                  }}
                  onUpdateSession={(sessionId, title) => onUpdateSession?.(sessionId, title)}
                  onDeleteSession={(sessionId) => onDeleteSession?.(sessionId)}
                  loadingSessions={loadingSessions}
                />
              </DialogContent>
            </Dialog>
          )}
        </div>
      </CardHeader>
      <CardContent className="flex-1 flex flex-col min-h-0 p-0">
        <ScrollArea className="flex-1 min-h-0 px-4" ref={scrollAreaRef}>
          <div className="space-y-4 py-4">
            {messages.length === 0 ? (
              <div className="text-center text-muted-foreground py-8">
                <Bot className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p className="text-sm">
                  Start a conversation about this {contextType}
                </p>
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
                  <div className="flex flex-col gap-2 max-w-[80%]">
                    <div
                      className={`rounded-lg px-4 py-2 ${
                        message.type === 'human'
                          ? 'bg-primary text-primary-foreground'
                          : 'bg-muted'
                      }`}
                    >
                      {message.type === 'ai' ? (
                        <AIMessageContent
                          content={message.content}
                          onReferenceClick={handleReferenceClick}
                        />
                      ) : (
                        <p className="text-sm break-words overflow-wrap-anywhere">{message.content}</p>
                      )}
                    </div>
                    {message.type === 'ai' && (
                      <MessageActions
                        content={message.content}
                        notebookId={notebookId}
                      />
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

        {/* Notebook Context Indicator */}
        {notebookContextStats && (
          <ContextIndicator
            sourcesInsights={notebookContextStats.sourcesInsights}
            sourcesFull={notebookContextStats.sourcesFull}
            notesCount={notebookContextStats.notesCount}
            tokenCount={notebookContextStats.tokenCount}
            charCount={notebookContextStats.charCount}
          />
        )}

        {/* Input Area */}
        <div className="flex-shrink-0 p-4 space-y-3 border-t">
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
              placeholder={`Ask a question about this ${contextType}... (${keyHint} to send)`}
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

    </>
  )
}

// Helper component to render AI messages with clickable references
function AIMessageContent({
  content,
  onReferenceClick
}: {
  content: string
  onReferenceClick: (type: string, id: string) => void
}) {
  // Convert references to compact markdown with numbered citations
  const markdownWithCompactRefs = convertReferencesToCompactMarkdown(content)

  // Create custom link component for compact references
  const LinkComponent = createCompactReferenceLinkComponent(onReferenceClick)

  return (
    <div className="prose prose-sm prose-neutral dark:prose-invert max-w-none break-words prose-headings:font-semibold prose-a:text-blue-600 prose-a:break-all prose-code:bg-muted prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-p:mb-4 prose-p:leading-7 prose-li:mb-2">
      <ReactMarkdown
        components={{
          a: LinkComponent,
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
        {markdownWithCompactRefs}
      </ReactMarkdown>
    </div>
  )
}
