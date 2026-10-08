'use client'

import { memo, useCallback, useState, useRef, useEffect, useId } from 'react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog'
import { Bot, User, Send, Loader2, FileText, Lightbulb, StickyNote, Clock, ImagePlus } from 'lucide-react'
import {
  SourceChatMessage,
  SourceChatContextIndicator,
  BaseChatSession,
  ChatImage
} from '@/lib/types/api'
import { ModelSelector } from './ModelSelector'
import { ContextIndicator } from '@/components/common/ContextIndicator'
import { SessionManager } from '@/components/sources/SessionManager'
import { MessageActions } from '@/components/sources/MessageActions'
import { useModalManager } from '@/lib/hooks/use-modal-manager'
import { toast } from 'sonner'
import { useTranslation } from '@/lib/hooks/use-translation'
import { ChatImages } from './ChatImages'
import { ChatResponseContent } from './ChatResponseContent'
import { readChatImages, CHAT_IMAGE_TYPES } from '@/lib/utils/chat-images'

type SendChatMessage = (message: string, modelOverride?: string, images?: ChatImage[], visualTools?: boolean) => void | boolean | Promise<void | boolean>

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
  onSendMessage: SendChatMessage
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
  title,
  contextType = 'source',
  notebookContextStats,
  notebookId
}: ChatPanelProps) {
  const { t } = useTranslation()
  const [sessionManagerOpen, setSessionManagerOpen] = useState(false)
  const scrollAreaRef = useRef<HTMLDivElement>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const { openModal } = useModalManager()

  // Stable reference-click handler so memoized messages don't re-render on
  // composer keystrokes (which no longer re-render this component at all, since
  // the input state lives in the ChatComposer child).
  const handleReferenceClick = useCallback((type: string, id: string) => {
    const modalType = type === 'source_insight' ? 'insight' : type as 'source' | 'note' | 'insight'

    try {
      openModal(modalType, id)
      // Note: The modal system uses URL parameters and doesn't throw errors for missing items.
      // The modal component itself will handle displaying "not found" states.
      // This try-catch is here for future enhancements or unexpected errors.
    } catch {
      toast.error(t('common.noResults'))
    }
  }, [openModal, t])

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  return (
    <>
    <Card className="flex flex-col h-full flex-1 overflow-hidden">
      <CardHeader className="pb-3 flex-shrink-0">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.13em] text-muted-foreground">
            <span aria-hidden className="h-3.5 w-[3px] rounded-full bg-teal" />
            {title || (contextType === 'source' ? t('chat.chatWith', { name: t('navigation.sources') }) : t('chat.chatWith', { name: t('common.notebook') }))}
          </CardTitle>
          {onSelectSession && onCreateSession && onDeleteSession && (
            <Dialog open={sessionManagerOpen} onOpenChange={setSessionManagerOpen}>
              <Button
                variant="ghost"
                size="sm"
                className="gap-2 text-muted-foreground"
                onClick={() => setSessionManagerOpen(true)}
                disabled={loadingSessions}
              >
                <Clock className="h-4 w-4" />
                <span className="text-xs">{t('chat.sessions')}</span>
              </Button>
              <DialogContent className="sm:max-w-[420px] p-0 overflow-hidden">
                <DialogTitle className="sr-only">{t('chat.sessionsTitle')}</DialogTitle>
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
                  {t('chat.startConversation', { type: contextType === 'source' ? t('navigation.sources') : t('common.notebook') })}
                </p>
                <p className="text-xs mt-2">{t('chat.askQuestions')}</p>
              </div>
            ) : (
              messages.map((message) => (
                <ChatMessage
                  key={message.id}
                  message={message}
                  notebookId={notebookId}
                  onReferenceClick={handleReferenceClick}
                />
              ))
            )}
            {isStreaming && (
              <div className="flex gap-3 justify-start">
                <div className="flex-shrink-0">
                  <div className="h-8 w-8 rounded-full bg-teal-tint flex items-center justify-center">
                    <Bot className="h-4 w-4 text-teal" />
                  </div>
                </div>
                <div className="rounded-lg px-4 py-2 bg-card border">
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
                  {contextIndicators.sources.length} {t('navigation.sources')}
                </Badge>
              )}
              {contextIndicators.insights?.length > 0 && (
                <Badge variant="outline" className="gap-1">
                  <Lightbulb className="h-3 w-3" />
                  {contextIndicators.insights.length} {contextIndicators.insights.length === 1 ? t('common.insight') : t('common.insights')}
                </Badge>
              )}
              {contextIndicators.notes?.length > 0 && (
                <Badge variant="outline" className="gap-1">
                  <StickyNote className="h-3 w-3" />
                  {contextIndicators.notes.length} {contextIndicators.notes.length === 1 ? t('common.note') : t('common.notes')}
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
        <ChatComposer
          onSendMessage={onSendMessage}
          isStreaming={isStreaming}
          modelOverride={modelOverride}
          onModelChange={onModelChange}
        />
      </CardContent>
    </Card>

    </>
  )
}

// Composer owns the input state so keystrokes (including IME composition) only
// re-render this small component instead of the whole message history.
interface ChatComposerProps {
  onSendMessage: SendChatMessage
  isStreaming: boolean
  modelOverride?: string
  onModelChange?: (model?: string) => void
}

function ChatComposer({
  onSendMessage,
  isStreaming,
  modelOverride,
  onModelChange
}: ChatComposerProps) {
  const { t } = useTranslation()
  const chatInputId = useId()
  const [input, setInput] = useState('')
  const [images, setImages] = useState<ChatImage[]>([])
  const [visualTools, setVisualTools] = useState(false)
  const [readingImages, setReadingImages] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const readingRef = useRef(false)
  const busy = isStreaming || readingImages || submitting

  const addImages = async (files: File[]) => {
    if (busy || readingRef.current || !files.length) return
    readingRef.current = true
    setReadingImages(true)
    try {
      const added = await readChatImages(files, images.length)
      setImages(previous => [...previous, ...added])
    } catch (error) {
      toast.error(t(error instanceof Error ? error.message : 'chat.imageReadFailed'))
    } finally {
      readingRef.current = false
      setReadingImages(false)
    }
  }

  const handleSend = () => {
    if ((!input.trim() && !images.length) || busy || readingRef.current) return
    const clearDraft = (success: void | boolean) => {
      if (success !== false) {
        setInput('')
        setImages([])
      }
    }
    const result = visualTools
      ? onSendMessage(input.trim(), modelOverride, images, true)
      : images.length
      ? onSendMessage(input.trim(), modelOverride, images)
      : onSendMessage(input.trim(), modelOverride)
    if (result instanceof Promise) {
      setSubmitting(true)
      result.then(clearDraft).catch(() => {
        toast.error(t('apiErrors.failedToSendMessage'))
      }).finally(() => setSubmitting(false))
    } else {
      clearDraft(result)
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
    <div className="flex-shrink-0 p-4 space-y-3 border-t"
      onDragOver={event => event.preventDefault()}
      onDrop={event => {
        event.preventDefault()
        void addImages(Array.from(event.dataTransfer.files))
      }}>
      {/* Model selector */}
      {onModelChange && (
        <div className="flex items-center justify-between">
          <span className="text-xs text-muted-foreground">{t('chat.model')}</span>
          <ModelSelector
            currentModel={modelOverride}
            onModelChange={onModelChange}
            disabled={busy}
          />
        </div>
      )}

      {images.length > 0 && <ChatImages images={images} disabled={busy}
        onRemove={index => setImages(previous => previous.filter((_, position) => position !== index))} />}
      <p className="text-xs text-muted-foreground">{t('chat.imageHint')}</p>
      <label className="flex items-center gap-2 text-xs text-muted-foreground">
        <input type="checkbox" checked={visualTools} disabled={busy}
          onChange={event => setVisualTools(event.target.checked)} />
        {t('chat.visualResponses')}
      </label>
      {visualTools && <p className="text-xs text-muted-foreground">{t('chat.visualResponsesHint')}</p>}
      <input ref={fileInputRef} type="file" accept={CHAT_IMAGE_TYPES.join(',')} multiple
        aria-label={t('chat.attachImages')} className="hidden" disabled={busy}
        onChange={event => {
          void addImages(Array.from(event.target.files || []))
          event.target.value = ''
        }} />
      <div className="flex gap-2 items-end min-w-0">
        <Button type="button" variant="outline" size="icon" className="h-[40px] w-[40px] flex-shrink-0"
          aria-label={t('chat.attachImages')} title={t('chat.attachImages')} disabled={busy}
          onClick={() => fileInputRef.current?.click()}>
          {readingImages ? <Loader2 className="h-4 w-4 animate-spin" /> : <ImagePlus className="h-4 w-4" />}
        </Button>
        <Textarea
          id={chatInputId}
          name="chat-message"
          autoComplete="off"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          onPaste={event => {
            const files = Array.from(event.clipboardData.files)
            if (files.length) {
              event.preventDefault()
              void addImages(files)
            }
          }}
          placeholder={`${t('chat.sendPlaceholder')} (${t('chat.pressToSend', { key: keyHint })})`}
          disabled={busy}
          className="flex-1 min-h-[40px] max-h-[100px] resize-none py-2 px-3 min-w-0"
          rows={1}
        />
        <Button
          onClick={handleSend}
          disabled={(!input.trim() && !images.length) || busy}
          aria-label={t('chat.sendMessage')}
          size="icon"
          className="h-[40px] w-[40px] flex-shrink-0"
        >
          {busy ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Send className="h-4 w-4" />
          )}
        </Button>
      </div>
    </div>
  )
}

// Single chat message row. Memoized so historical messages don't re-render when
// unrelated state (e.g. the composer input) changes.
interface ChatMessageProps {
  message: SourceChatMessage
  notebookId?: string
  onReferenceClick: (type: string, id: string) => void
}

const ChatMessage = memo(function ChatMessage({
  message,
  notebookId,
  onReferenceClick
}: ChatMessageProps) {
  const { t } = useTranslation()
  const exportContent = message.content
    .replace(/\[\[image:(\d+)\]\]/g, (_, number) => message.images?.[Number(number) - 1]?.name ?? '')
    .replace(/\[\[quiz:[^\]]+\]\]/g, t('chat.inlineQuiz'))
    .replace(/\[\[quiz-unavailable\]\]/g, t('chat.quizPreparationFailed'))
  return (
    <div
      className={`flex gap-3 ${
        message.type === 'human' ? 'justify-end' : 'justify-start'
      }`}
    >
      {message.type === 'ai' && (
        <div className="flex-shrink-0">
          <div className="h-8 w-8 rounded-full bg-teal-tint flex items-center justify-center">
            <Bot className="h-4 w-4 text-teal" />
          </div>
        </div>
      )}
      <div className="flex flex-col gap-2 max-w-[80%]">
        <div
          className={`rounded-lg px-4 py-2 border ${
            message.type === 'human'
              ? 'bg-muted'
              : 'bg-card'
          }`}
        >
          {message.type === 'ai' ? (
            <div className="space-y-3">
              <ChatResponseContent content={message.content} images={message.images} quizzes={message.quizzes} onReferenceClick={onReferenceClick} />
            </div>
          ) : (
            <div className="space-y-2">
              {!!message.images?.length && <ChatImages images={message.images} />}
              {message.content && <p className="text-sm break-all">{message.content}</p>}
            </div>
          )}
        </div>
        {message.type === 'ai' && (
          <MessageActions
            content={exportContent}
            notebookId={notebookId}
          />
        )}
      </div>
      {message.type === 'human' && (
        <div className="flex-shrink-0">
          <div className="h-8 w-8 rounded-full bg-muted border flex items-center justify-center">
            <User className="h-4 w-4 text-muted-foreground" />
          </div>
        </div>
      )}
    </div>
  )
})
