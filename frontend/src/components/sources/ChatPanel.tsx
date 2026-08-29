'use client'

import { memo, useCallback, useState, useRef, useEffect, useId, useMemo } from 'react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Dialog, DialogContent, DialogTitle, DialogHeader, DialogDescription, DialogFooter } from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Bot, User, Send, Loader2, FileText, Lightbulb, StickyNote, Clock, MessageCircleQuestion, ListChecks, ChevronLeft } from 'lucide-react'
import { MarkdownRenderer } from '@/components/ui/markdown-renderer'
import {
  SourceChatMessage,
  SourceChatContextIndicator,
  BaseChatSession
} from '@/lib/types/api'
import { ModelSelector } from './ModelSelector'
import { ContextIndicator } from '@/components/common/ContextIndicator'
import { SessionManager } from '@/components/sources/SessionManager'
import { MessageActions } from '@/components/sources/MessageActions'
import { convertReferencesToCompactMarkdown, createCompactReferenceLinkComponent } from '@/lib/utils/source-references'
import { useModalManager } from '@/lib/hooks/use-modal-manager'
import { toast } from 'sonner'
import { useTranslation } from '@/lib/hooks/use-translation'
import { QUICK_PROMPTS, QuickPromptTemplate, buildQuickPrompt } from '@/lib/quick-prompts'

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

  // Self-explanation starter (see ChatComposer): clicking the suggestion
  // below drops a pre-written prompt into the composer instead of sending it
  // immediately, so the learner still writes the explanation themselves.
  // `draftVersion` lets the same text be reused twice in a row and still
  // trigger the composer's sync effect.
  const [draftPrompt, setDraftPrompt] = useState('')
  const [draftVersion, setDraftVersion] = useState(0)
  const useSelfExplanationPrompt = useCallback(() => {
    setDraftPrompt(t('chat.selfExplainPromptTemplate'))
    setDraftVersion((v) => v + 1)
  }, [t])

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
                <div className="mt-5 mx-auto max-w-sm rounded-lg border border-dashed p-3 text-left">
                  <div className="flex items-start gap-2">
                    <MessageCircleQuestion className="h-4 w-4 mt-0.5 shrink-0 text-teal" />
                    <div className="space-y-1">
                      <p className="text-xs font-medium text-foreground">{t('chat.selfExplainTitle')}</p>
                      <p className="text-xs text-muted-foreground">{t('chat.selfExplainDesc')}</p>
                      <Button variant="outline" size="sm" className="mt-1" onClick={useSelfExplanationPrompt}>
                        {t('chat.selfExplainButton')}
                      </Button>
                    </div>
                  </div>
                </div>
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
          draftPrompt={draftPrompt}
          draftVersion={draftVersion}
        />
      </CardContent>
    </Card>

    </>
  )
}

// Composer owns the input state so keystrokes (including IME composition) only
// re-render this small component instead of the whole message history.
interface ChatComposerProps {
  onSendMessage: (message: string, modelOverride?: string) => void
  isStreaming: boolean
  modelOverride?: string
  onModelChange?: (model?: string) => void
  /** Set by ChatPanel's self-explanation suggestion. `draftVersion` bumps on
   * every click (even reusing the same text) so the sync effect below fires
   * each time, instead of keying off the text itself. */
  draftPrompt?: string
  draftVersion?: number
}

function ChatComposer({
  onSendMessage,
  isStreaming,
  modelOverride,
  onModelChange,
  draftPrompt,
  draftVersion
}: ChatComposerProps) {
  const { t } = useTranslation()
  const chatInputId = useId()
  const [input, setInput] = useState('')

  useEffect(() => {
    if (draftVersion) {
      setInput(draftPrompt ?? '')
    }
    // Only react to a new draftVersion, not every draftPrompt/input change.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [draftVersion])

  // Quick Prompts: a self-contained picker for the 4 conversational study
  // templates (quiz, exam simulation, tutor persona, summary+contradictions).
  // Lives entirely in this component — unlike the self-explanation suggestion
  // above (which is in the parent ChatPanel and reaches in via draftPrompt),
  // this one only ever needs to call this component's own `setInput`.
  const [quickPromptsOpen, setQuickPromptsOpen] = useState(false)
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(null)
  const [fieldValues, setFieldValues] = useState<Record<string, string>>({})

  const selectedTemplate = useMemo(
    () => QUICK_PROMPTS.find((template) => template.id === selectedTemplateId) ?? null,
    [selectedTemplateId]
  )

  const resetQuickPrompts = () => {
    setSelectedTemplateId(null)
    setFieldValues({})
  }

  const handleQuickPromptsOpenChange = (open: boolean) => {
    setQuickPromptsOpen(open)
    if (!open) {
      resetQuickPrompts()
    }
  }

  const handleSelectTemplate = (template: QuickPromptTemplate) => {
    if (template.fields.length === 0) {
      setInput(buildQuickPrompt(template, {}))
      setQuickPromptsOpen(false)
      resetQuickPrompts()
      return
    }
    setSelectedTemplateId(template.id)
    const initialValues: Record<string, string> = {}
    for (const field of template.fields) {
      // Text fields start empty so their placeholder (e.g. "leave blank for
      // all content") stays visible and the default-fallback in
      // buildQuickPrompt actually gets exercised. Select fields need a
      // concrete value pre-selected since there's no blank/placeholder state
      // for a dropdown.
      initialValues[field.key] = field.type === 'select' ? field.defaultValue ?? '' : ''
    }
    setFieldValues(initialValues)
  }

  const handleConfirmTemplate = () => {
    if (!selectedTemplate) return
    setInput(buildQuickPrompt(selectedTemplate, fieldValues))
    setQuickPromptsOpen(false)
    resetQuickPrompts()
  }

  const canConfirmTemplate = selectedTemplate
    ? selectedTemplate.fields.every((field) => !field.required || (fieldValues[field.key] ?? '').trim())
    : false

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
    <div className="flex-shrink-0 p-4 space-y-3 border-t">
      {/* Toolbar: Quick Prompts trigger (left) + model selector (right) */}
      <div className="flex items-center justify-between gap-2">
        <Dialog open={quickPromptsOpen} onOpenChange={handleQuickPromptsOpenChange}>
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="gap-2 text-muted-foreground"
            onClick={() => setQuickPromptsOpen(true)}
            disabled={isStreaming}
          >
            <ListChecks className="h-4 w-4" />
            <span className="text-xs">{t('chat.quickPrompts.triggerLabel')}</span>
          </Button>
          <DialogContent className="sm:max-w-[480px] max-h-[85vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <ListChecks className="h-5 w-5" />
                {t('chat.quickPrompts.dialogTitle')}
              </DialogTitle>
              <DialogDescription>{t('chat.quickPrompts.dialogDescription')}</DialogDescription>
            </DialogHeader>

            {!selectedTemplate ? (
              <div className="grid gap-2 py-2">
                {QUICK_PROMPTS.map((template) => (
                  <button
                    key={template.id}
                    type="button"
                    onClick={() => handleSelectTemplate(template)}
                    className="text-left rounded-lg border p-3 hover:bg-accent hover:text-accent-foreground transition-colors"
                  >
                    <p className="text-sm font-medium">{t(template.titleKey)}</p>
                    <p className="text-xs text-muted-foreground mt-1">{t(template.descriptionKey)}</p>
                  </button>
                ))}
              </div>
            ) : (
              <div className="space-y-4 py-2">
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="gap-1 -ml-2 text-muted-foreground"
                  onClick={resetQuickPrompts}
                >
                  <ChevronLeft className="h-4 w-4" />
                  {t('chat.quickPrompts.backButton')}
                </Button>
                <div>
                  <p className="text-sm font-medium">{t(selectedTemplate.titleKey)}</p>
                  <p className="text-xs text-muted-foreground mt-1">{t(selectedTemplate.descriptionKey)}</p>
                </div>
                <div className="grid gap-3">
                  {selectedTemplate.fields.map((field) => {
                    const fieldId = `${chatInputId}-qp-${field.key}`
                    return (
                      <div key={field.key} className="grid gap-1.5">
                        <Label htmlFor={fieldId}>
                          {t(field.labelKey)}
                          {field.required && <span className="text-destructive"> *</span>}
                        </Label>
                        {field.type === 'text' ? (
                          <Input
                            id={fieldId}
                            value={fieldValues[field.key] ?? ''}
                            onChange={(e) =>
                              setFieldValues((prev) => ({ ...prev, [field.key]: e.target.value }))
                            }
                            placeholder={field.placeholderKey ? t(field.placeholderKey) : undefined}
                          />
                        ) : (
                          <Select
                            value={fieldValues[field.key] ?? field.defaultValue ?? ''}
                            onValueChange={(value) =>
                              setFieldValues((prev) => ({ ...prev, [field.key]: value }))
                            }
                          >
                            <SelectTrigger id={fieldId} className="w-full">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              {field.options?.map((option) => (
                                <SelectItem key={option.value} value={option.value}>
                                  {t(option.labelKey)}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        )}
                      </div>
                    )
                  })}
                </div>
                <DialogFooter>
                  <Button type="button" onClick={handleConfirmTemplate} disabled={!canConfirmTemplate}>
                    {t('chat.quickPrompts.useButton')}
                  </Button>
                </DialogFooter>
              </div>
            )}
          </DialogContent>
        </Dialog>

        {onModelChange && (
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">{t('chat.model')}</span>
            <ModelSelector
              currentModel={modelOverride}
              onModelChange={onModelChange}
              disabled={isStreaming}
            />
          </div>
        )}
      </div>

      <div className="flex gap-2 items-end min-w-0">
        <Textarea
          id={chatInputId}
          name="chat-message"
          autoComplete="off"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={`${t('chat.sendPlaceholder')} (${t('chat.pressToSend', { key: keyHint })})`}
          disabled={isStreaming}
          className="flex-1 min-h-[40px] max-h-[100px] resize-none py-2 px-3 min-w-0"
          rows={1}
        />
        <Button
          onClick={handleSend}
          disabled={!input.trim() || isStreaming}
          size="icon"
          className="h-[40px] w-[40px] flex-shrink-0"
          data-testid="chat-send-button"
        >
          {isStreaming ? (
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
            <AIMessageContent
              content={message.content}
              onReferenceClick={onReferenceClick}
            />
          ) : (
            <p className="text-sm break-all">{message.content}</p>
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
          <div className="h-8 w-8 rounded-full bg-muted border flex items-center justify-center">
            <User className="h-4 w-4 text-muted-foreground" />
          </div>
        </div>
      )}
    </div>
  )
})

// Helper component to render AI messages with clickable references
function AIMessageContent({
  content,
  onReferenceClick
}: {
  content: string
  onReferenceClick: (type: string, id: string) => void
}) {
  const { t } = useTranslation()
  // Convert references to compact markdown with numbered citations
  const markdownWithCompactRefs = convertReferencesToCompactMarkdown(content, t('common.references'))

  // Create custom link component for compact references
  const LinkComponent = createCompactReferenceLinkComponent(onReferenceClick)

  return (
    <MarkdownRenderer components={{
      a: LinkComponent
    }}>
      {markdownWithCompactRefs}
    </MarkdownRenderer>
  )
}
