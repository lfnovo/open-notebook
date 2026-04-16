// // 'use client'

// // import { useState, useRef, useEffect, useId } from 'react'
// // import { Button } from '@/components/ui/button'
// // import { Textarea } from '@/components/ui/textarea'
// // import { ScrollArea } from '@/components/ui/scroll-area'
// // import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
// // import { Badge } from '@/components/ui/badge'
// // import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog'
// // import { Bot, User, Send, Loader2, FileText, Lightbulb, StickyNote, Clock } from 'lucide-react'
// // import ReactMarkdown from 'react-markdown'
// // import remarkGfm from 'remark-gfm'
// // import {
// //   SourceChatMessage,
// //   SourceChatContextIndicator,
// //   BaseChatSession
// // } from '@/lib/types/api'
// // import { ModelSelector } from './ModelSelector'
// // import { ContextIndicator } from '@/components/common/ContextIndicator'
// // import { SessionManager } from '@/components/source/SessionManager'
// // import { MessageActions } from '@/components/source/MessageActions'
// // import { convertReferencesToCompactMarkdown, createCompactReferenceLinkComponent } from '@/lib/utils/source-references'
// // import { useModalManager } from '@/lib/hooks/use-modal-manager'
// // import { toast } from 'sonner'
// // import { useTranslation } from '@/lib/hooks/use-translation'
// // import { StudioActionsCard } from './StudioSection'

// // interface NotebookContextStats {
// //   sourcesInsights: number
// //   sourcesFull: number
// //   notesCount: number
// //   tokenCount?: number
// //   charCount?: number
// // }

// // interface ChatPanelProps {
// //   messages: SourceChatMessage[]
// //   isStreaming: boolean
// //   contextIndicators: SourceChatContextIndicator | null
// //   onSendMessage: (message: string, modelOverride?: string) => void
// //   modelOverride?: string
// //   onModelChange?: (model?: string) => void
// //   // Session management props
// //   sessions?: BaseChatSession[]
// //   currentSessionId?: string | null
// //   onCreateSession?: (title: string) => void
// //   onSelectSession?: (sessionId: string) => void
// //   onDeleteSession?: (sessionId: string) => void
// //   onUpdateSession?: (sessionId: string, title: string) => void
// //   loadingSessions?: boolean
// //   // Generic props for reusability
// //   title?: string
// //   contextType?: 'source' | 'notebook'
// //   // Notebook context stats (for notebook chat)
// //   notebookContextStats?: NotebookContextStats
// //   // Notebook ID for saving notes
// //   notebookId?: string
// // }

// // export function ChatPanel({
// //   messages,
// //   isStreaming,
// //   contextIndicators,
// //   onSendMessage,
// //   modelOverride,
// //   onModelChange,
// //   sessions = [],
// //   currentSessionId,
// //   onCreateSession,
// //   onSelectSession,
// //   onDeleteSession,
// //   onUpdateSession,
// //   loadingSessions = false,
// //   title,
// //   contextType = 'source',
// //   notebookContextStats,
// //   notebookId
// // }: ChatPanelProps) {
// //   const { t } = useTranslation()
// //   const chatInputId = useId()
// //   const [input, setInput] = useState('')
// //   const [sessionManagerOpen, setSessionManagerOpen] = useState(false)
// //   const scrollAreaRef = useRef<HTMLDivElement>(null)
// //   const messagesEndRef = useRef<HTMLDivElement>(null)
// //   const { openModal } = useModalManager()

// //   const handleReferenceClick = (type: string, id: string) => {
// //     const modalType = type === 'source_insight' ? 'insight' : type as 'source' | 'note' | 'insight'

// //     try {
// //       openModal(modalType, id)
// //       // Note: The modal system uses URL parameters and doesn't throw errors for missing items.
// //       // The modal component itself will handle displaying "not found" states.
// //       // This try-catch is here for future enhancements or unexpected errors.
// //     } catch {
// //       toast.error(t.common.noResults)
// //     }
// //   }

// //   // Auto-scroll to bottom when new messages arrive
// //   useEffect(() => {
// //     messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
// //   }, [messages])

// //   const handleSend = () => {
// //     if (input.trim() && !isStreaming) {
// //       onSendMessage(input.trim(), modelOverride)
// //       setInput('')
// //     }
// //   }

// //   const handleKeyDown = (e: React.KeyboardEvent) => {
// //     // Detect platform for correct modifier key
// //     const isMac = typeof navigator !== 'undefined' && navigator.userAgent.toUpperCase().indexOf('MAC') >= 0
// //     const isModifierPressed = isMac ? e.metaKey : e.ctrlKey

// //     if (e.key === 'Enter' && isModifierPressed) {
// //       e.preventDefault()
// //       handleSend()
// //     }
// //   }

// //   // Detect platform for placeholder text
// //   const isMac = typeof navigator !== 'undefined' && navigator.userAgent.toUpperCase().indexOf('MAC') >= 0
// //   const keyHint = isMac ? '⌘+Enter' : 'Ctrl+Enter'

// //   return (
// //     <>
// //     <Card className="flex flex-col h-full flex-1 overflow-hidden my-2">
// //       <CardHeader className="pb-3 flex-shrink-0">
// //         <div className="flex items-center justify-between">
// //           <CardTitle className="flex items-center gap-2">
// //             <Bot className="h-5 w-5" />
// //             {title || (contextType === 'source' ? t.chat.chatWith.replace('{name}', t.navigation.sources) : t.chat.chatWith.replace('{name}', t.common.notebook))}
// //           </CardTitle>
// //           {onSelectSession && onCreateSession && onDeleteSession && (
// //             <Dialog open={sessionManagerOpen} onOpenChange={setSessionManagerOpen}>
// //               <Button
// //                 variant="ghost"
// //                 size="sm"
// //                 className="gap-2"
// //                 onClick={() => setSessionManagerOpen(true)}
// //                 disabled={loadingSessions}
// //               >
// //                 <Clock className="h-4 w-4" />
// //                 <span className="text-xs">{t.chat.sessions}</span>
// //               </Button>
// //               <DialogContent className="sm:max-w-[420px] p-0 overflow-hidden">
// //                 <DialogTitle className="sr-only">{t.chat.sessionsTitle}</DialogTitle>
// //                 <SessionManager
// //                   sessions={sessions}
// //                   currentSessionId={currentSessionId ?? null}
// //                   onCreateSession={(title) => onCreateSession?.(title)}
// //                   onSelectSession={(sessionId) => {
// //                     onSelectSession(sessionId)
// //                     setSessionManagerOpen(false)
// //                   }}
// //                   onUpdateSession={(sessionId, title) => onUpdateSession?.(sessionId, title)}
// //                   onDeleteSession={(sessionId) => onDeleteSession?.(sessionId)}
// //                   loadingSessions={loadingSessions}
// //                 />
// //               </DialogContent>
// //             </Dialog>
// //           )}
// //         </div>
// //       </CardHeader>
// //       <CardContent className="flex-1 flex flex-col min-h-0 p-0">
// //         <ScrollArea className="flex-1 min-h-0 px-4" ref={scrollAreaRef}>
// //           <div className="space-y-4 py-4">
// //             {messages.length === 0 ? (
// //               <div className="text-center text-muted-foreground py-8">
// //                 <Bot className="h-12 w-12 mx-auto mb-4 opacity-50" />
// //                 <p className="text-sm">
// //                   {t.chat.startConversation.replace('{type}', contextType === 'source' ? t.navigation.sources : t.common.notebook)}
// //                 </p>
// //                 <p className="text-xs mt-2">{t.chat.askQuestions}</p>
// //               </div>
// //             ) : (
// //               messages.map((message) => (
// //                 <div
// //                   key={message.id}
// //                   className={`flex gap-3 ${
// //                     message.type === 'human' ? 'justify-end' : 'justify-start'
// //                   }`}
// //                 >
// //                   {message.type === 'ai' && (
// //                     <div className="flex-shrink-0">
// //                       <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
// //                         <Bot className="h-4 w-4" />
// //                       </div>
// //                     </div>
// //                   )}
// //                   <div className="flex flex-col gap-2 max-w-[80%]">
// //                     <div
// //                       className={`rounded-lg px-4 py-2 ${
// //                         message.type === 'human'
// //                           ? 'bg-primary text-primary-foreground'
// //                           : 'bg-muted'
// //                       }`}
// //                     >
// //                       {message.type === 'ai' ? (
// //                         <AIMessageContent
// //                           content={message.content}
// //                           onReferenceClick={handleReferenceClick}
// //                         />
// //                       ) : (
// //                         <p className="text-sm break-all">{message.content}</p>
// //                       )}
// //                     </div>
// //                     {message.type === 'ai' && (
// //                       <MessageActions
// //                         content={message.content}
// //                         notebookId={notebookId}
// //                       />
// //                     )}
// //                   </div>
// //                   {message.type === 'human' && (
// //                     <div className="flex-shrink-0">
// //                       <div className="h-8 w-8 rounded-full bg-primary flex items-center justify-center">
// //                         <User className="h-4 w-4 text-primary-foreground" />
// //                       </div>
// //                     </div>
// //                   )}
// //                 </div>
// //               ))
// //             )}
// //             {isStreaming && (
// //               <div className="flex gap-3 justify-start">
// //                 <div className="flex-shrink-0">
// //                   <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
// //                     <Bot className="h-4 w-4" />
// //                   </div>
// //                 </div>
// //                 <div className="rounded-lg px-4 py-2 bg-muted">
// //                   <Loader2 className="h-4 w-4 animate-spin" />
// //                 </div>
// //               </div>
// //             )}
// //             <div ref={messagesEndRef} />
// //           </div>
// //         </ScrollArea>

// //         {/* Context Indicators */}
// //         {contextIndicators && (
// //           <div className="border-t px-4 py-2">
// //             <div className="flex flex-wrap gap-2 text-xs">
// //               {contextIndicators.sources?.length > 0 && (
// //                 <Badge variant="outline" className="gap-1">
// //                   <FileText className="h-3 w-3" />
// //                   {contextIndicators.sources.length} {t.navigation.sources}
// //                 </Badge>
// //               )}
// //               {contextIndicators.insights?.length > 0 && (
// //                 <Badge variant="outline" className="gap-1">
// //                   <Lightbulb className="h-3 w-3" />
// //                   {contextIndicators.insights.length} {contextIndicators.insights.length === 1 ? t.common.insight : t.common.insights}
// //                 </Badge>
// //               )}
// //               {contextIndicators.notes?.length > 0 && (
// //                 <Badge variant="outline" className="gap-1">
// //                   <StickyNote className="h-3 w-3" />
// //                   {contextIndicators.notes.length} {contextIndicators.notes.length === 1 ? t.common.note : t.common.notes}
// //                 </Badge>
// //               )}
// //             </div>
// //           </div>
// //         )}

// //         {/* Notebook Context Indicator */}
// //         {notebookContextStats && (
// //           <ContextIndicator
// //             sourcesInsights={notebookContextStats.sourcesInsights}
// //             sourcesFull={notebookContextStats.sourcesFull}
// //             notesCount={notebookContextStats.notesCount}
// //             tokenCount={notebookContextStats.tokenCount}
// //             charCount={notebookContextStats.charCount}
// //           />
// //         )}

// //         {/* Input Area */}
// //         <div className="flex-shrink-0 p-4 space-y-3 border-t">
// //           {/* Model selector */}
// //           {onModelChange && (
// //             <div className="flex items-center justify-between">
// //               <span className="text-xs text-muted-foreground">{t.chat.model}</span>
// //               <ModelSelector
// //                 currentModel={modelOverride}
// //                 onModelChange={onModelChange}
// //                 disabled={isStreaming}
// //               />
// //             </div>
// //           )}

// //           <div className="flex gap-2 items-end min-w-0">
// //             <Textarea
// //               id={chatInputId}
// //               name="chat-message"
// //               autoComplete="off"
// //               value={input}
// //               onChange={(e) => setInput(e.target.value)}
// //               onKeyDown={handleKeyDown}
// //               placeholder={`${t.chat.sendPlaceholder} (${t.chat.pressToSend.replace('{key}', keyHint)})`}
// //               disabled={isStreaming}
// //               className="flex-1 min-h-[40px] max-h-[100px] resize-none py-2 px-3 min-w-0"
// //               rows={1}
// //             />
// //             <Button
// //               onClick={handleSend}
// //               disabled={!input.trim() || isStreaming}
// //               size="icon"
// //               className="h-[40px] w-[40px] flex-shrink-0"
// //             >
// //               {isStreaming ? (
// //                 <Loader2 className="h-4 w-4 animate-spin" />
// //               ) : (
// //                 <Send className="h-4 w-4" />
// //               )}
// //             </Button>
// //           </div>
// //         </div>
// //       </CardContent>
// //     </Card>

   
    

// //     </>
// //   )
// // }

// // // Helper component to render AI messages with clickable references
// // function AIMessageContent({
// //   content,
// //   onReferenceClick
// // }: {
// //   content: string
// //   onReferenceClick: (type: string, id: string) => void
// // }) {
// //   const { t } = useTranslation()
// //   // Convert references to compact markdown with numbered citations
// //   const markdownWithCompactRefs = convertReferencesToCompactMarkdown(content, t.common.references)

// //   // Create custom link component for compact references
// //   const LinkComponent = createCompactReferenceLinkComponent(onReferenceClick)

// //   return (
// //     <div className="prose prose-sm prose-neutral dark:prose-invert max-w-none break-words prose-headings:font-semibold prose-a:text-blue-600 prose-a:break-all prose-code:bg-muted prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-p:mb-4 prose-p:leading-7 prose-li:mb-2">
// //       <ReactMarkdown
// //         remarkPlugins={[remarkGfm]}
// //         components={{
// //           a: LinkComponent,
// //           p: ({ children }) => <p className="mb-4">{children}</p>,
// //           h1: ({ children }) => <h1 className="mb-4 mt-6">{children}</h1>,
// //           h2: ({ children }) => <h2 className="mb-3 mt-5">{children}</h2>,
// //           h3: ({ children }) => <h3 className="mb-3 mt-4">{children}</h3>,
// //           h4: ({ children }) => <h4 className="mb-2 mt-4">{children}</h4>,
// //           h5: ({ children }) => <h5 className="mb-2 mt-3">{children}</h5>,
// //           h6: ({ children }) => <h6 className="mb-2 mt-3">{children}</h6>,
// //           li: ({ children }) => <li className="mb-1">{children}</li>,
// //           ul: ({ children }) => <ul className="mb-4 space-y-1">{children}</ul>,
// //           ol: ({ children }) => <ol className="mb-4 space-y-1">{children}</ol>,
// //           table: ({ children }) => (
// //             <div className="my-4 overflow-x-auto">
// //               <table className="min-w-full border-collapse border border-border">{children}</table>
// //             </div>
// //           ),
// //           thead: ({ children }) => <thead className="bg-muted">{children}</thead>,
// //           tbody: ({ children }) => <tbody>{children}</tbody>,
// //           tr: ({ children }) => <tr className="border-b border-border">{children}</tr>,
// //           th: ({ children }) => <th className="border border-border px-3 py-2 text-left font-semibold">{children}</th>,
// //           td: ({ children }) => <td className="border border-border px-3 py-2">{children}</td>,
// //         }}
// //       >
// //         {markdownWithCompactRefs}
// //       </ReactMarkdown>
// //     </div>
// //   )
// // }





// 'use client'

// import React, { useState, useRef, useEffect, useId, useCallback, useMemo } from 'react'
// import { Button } from '@/components/ui/button'
// import { Textarea } from '@/components/ui/textarea'
// import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
// import { Badge } from '@/components/ui/badge'
// import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog'
// import { Bot, User, Send, FileText, Lightbulb, StickyNote, Clock } from 'lucide-react'
// import ReactMarkdown from 'react-markdown'
// import remarkGfm from 'remark-gfm'
// import {
//   SourceChatMessage,
//   SourceChatContextIndicator,
//   BaseChatSession
// } from '@/lib/types/api'
// import { ModelSelector } from './ModelSelector'
// import { ContextIndicator } from '@/components/common/ContextIndicator'
// import { SessionManager } from '@/components/source/SessionManager'
// import { MessageActions } from '@/components/source/MessageActions'
// import { convertReferencesToCompactMarkdown, createCompactReferenceLinkComponent } from '@/lib/utils/source-references'
// import { useModalManager } from '@/lib/hooks/use-modal-manager'
// import { toast } from 'sonner'
// import { useTranslation } from '@/lib/hooks/use-translation'
// import { StudioActionsCard } from './StudioSection'

// interface NotebookContextStats {
//   sourcesInsights: number
//   sourcesFull: number
//   notesCount: number
//   tokenCount?: number
//   charCount?: number
// }

// interface ChatPanelProps {
//   messages: SourceChatMessage[]
//   isStreaming: boolean

//   contextIndicators: SourceChatContextIndicator | null
//   onSendMessage: (message: string, modelOverride?: string) => void
//   modelOverride?: string
//   onModelChange?: (model?: string) => void
//   // Session management props
//   sessions?: BaseChatSession[]
//   currentSessionId?: string | null
//   onCreateSession?: (title: string) => void
//   onSelectSession?: (sessionId: string) => void
//   onDeleteSession?: (sessionId: string) => void
//   onUpdateSession?: (sessionId: string, title: string) => void
//   loadingSessions?: boolean
//   // Generic props for reusability
//   title?: string
//   contextType?: 'source' | 'notebook'
//   // Notebook context stats (for notebook chat)
//   notebookContextStats?: NotebookContextStats
//   // Notebook ID for saving notes
//   notebookId?: string

//   // Suggested questions

//   // Suggested follow-up questions
//   suggestedQuestions?: string[]
// }

// export function ChatPanel({
//   messages,
//   isStreaming,
//   contextIndicators,
//   onSendMessage,
//   modelOverride,
//   onModelChange,
//   sessions = [],
//   currentSessionId,
//   onCreateSession,
//   onSelectSession,
//   onDeleteSession,
//   onUpdateSession,
//   loadingSessions = false,
//   title,
//   contextType = 'source',
//   notebookContextStats,
//   notebookId,
//   suggestedQuestions = []
// }: ChatPanelProps) {
//   const { t } = useTranslation()
//   const chatInputId = useId()
//   const [sessionManagerOpen, setSessionManagerOpen] = useState(false)
//   const [thinkingLabel, setThinkingLabel] = useState('Thinking...')
//   const scrollAreaRef = useRef<HTMLDivElement>(null)
//   const messagesEndRef = useRef<HTMLDivElement>(null)
//   const isAtBottomRef = useRef(true)
//   const prevMessageCountRef = useRef(0)
//   const thinkingTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)
//   const { openModal } = useModalManager()

//   // Cycle through thinking labels while streaming
//   const THINKING_LABELS = [
//     'Thinking...',
//     'Searching documents...',
//     'Analyzing data...',
//     'Reading source...',
//     'Drafting response...',
//   ]
//   useEffect(() => {
//     if (isStreaming) {
//       let idx = 0
//       setThinkingLabel(THINKING_LABELS[0])
//       thinkingTimerRef.current = setInterval(() => {
//         idx = (idx + 1) % THINKING_LABELS.length
//         setThinkingLabel(THINKING_LABELS[idx])
//       }, 1800)
//     } else {
//       if (thinkingTimerRef.current) clearInterval(thinkingTimerRef.current)
//       setThinkingLabel('Thinking...')
//     }
//     return () => { if (thinkingTimerRef.current) clearInterval(thinkingTimerRef.current) }
//   }, [isStreaming])

//   const handleReferenceClick = (type: string, id: string) => {
//     const modalType = type === 'source_insight' ? 'insight' : type as 'source' | 'note' | 'insight'
//     try {
//       openModal(modalType, id)
//     } catch {
//       toast.error(t.common.noResults)
//     }
//   }

//   // Memoize the send message callback to prevent unnecessary re-renders
//   const memoizedOnSendMessage = useCallback(onSendMessage, [onSendMessage])

//   // Track if user is scrolled to bottom
//   const handleScroll = useCallback(() => {
//     const el = scrollAreaRef.current
//     if (!el) return
//     isAtBottomRef.current = el.scrollHeight - el.scrollTop - el.clientHeight < 80
//   }, [])

//   // Memoize the reference click handler
//   const memoizedHandleReferenceClick = useCallback(handleReferenceClick, [openModal, t.common.noResults])

//   // Scroll to bottom on new messages when appropriate
//   useEffect(() => {
//     const newCount = messages.length
//     const lastMsg = messages[messages.length - 1]
//     if (newCount > prevMessageCountRef.current) {
//       const shouldScroll = lastMsg?.type === 'human' || isAtBottomRef.current
//       if (shouldScroll) {
//         messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
//         isAtBottomRef.current = true
//       }
//     }
//     prevMessageCountRef.current = newCount
//   }, [messages])

//   const handleSend = useCallback((messageText: string) => {
//     if (messageText.trim() && !isStreaming) {
//       onSendMessage(messageText.trim(), modelOverride)
//     }
//   }, [isStreaming, onSendMessage, modelOverride])

//   const keyHint = 'Enter'


//   return (
//     <div className="flex flex-col h-full min-h-0 overflow-hidden">
//     <Card className="flex flex-col h-full min-h-0 overflow-hidden">
//       <CardHeader className="pb-3 flex-shrink-0">
//         <div className="flex items-center justify-between">
//           <CardTitle className="flex items-center gap-2">
//             <Bot className="h-5 w-5" />
//             {title || (contextType === 'source' ? t.chat.chatWith.replace('{name}', t.navigation.sources) : t.chat.chatWith.replace('{name}', t.common.notebook))}
//           </CardTitle>
//           {onSelectSession && onCreateSession && onDeleteSession && (
//             <Dialog open={sessionManagerOpen} onOpenChange={setSessionManagerOpen}>
//               <Button
//                 variant="ghost"
//                 size="sm"
//                 className="gap-2"
//                 onClick={() => setSessionManagerOpen(true)}
//                 disabled={loadingSessions}
//               >
//                 <Clock className="h-4 w-4" />
//                 <span className="text-xs">{t.chat.sessions}</span>
//               </Button>
//               <DialogContent className="sm:max-w-[420px] p-0 overflow-hidden">
//                 <DialogTitle className="sr-only">{t.chat.sessionsTitle}</DialogTitle>
//                 <SessionManager
//                   sessions={sessions}
//                   currentSessionId={currentSessionId ?? null}
//                   onCreateSession={(title) => onCreateSession?.(title)}
//                   onSelectSession={(sessionId) => {
//                     onSelectSession(sessionId)
//                     setSessionManagerOpen(false)
//                   }}
//                   onUpdateSession={(sessionId, title) => onUpdateSession?.(sessionId, title)}
//                   onDeleteSession={(sessionId) => onDeleteSession?.(sessionId)}
//                   loadingSessions={loadingSessions}
//                 />
//               </DialogContent>
//             </Dialog>
//           )}
//         </div>
//       </CardHeader>

//       <CardContent className="flex-1 flex flex-col min-h-0 p-0 overflow-hidden">
//         <div className="flex-1 min-h-0 overflow-y-auto px-4" ref={scrollAreaRef} onScroll={handleScroll} style={{ overflowAnchor: 'auto' }}>
//           <div className="space-y-4 py-4">
//             {messages.length === 0 && !isStreaming ? (
//               <div className="text-center text-muted-foreground py-8">
//                 <Bot className="h-12 w-12 mx-auto mb-4 opacity-50" />
//                 <p className="text-sm">
//                   {t.chat.startConversation.replace('{type}', contextType === 'source' ? t.navigation.sources : t.common.notebook)}
//                 </p>
//                 <p className="text-xs mt-2">{t.chat.askQuestions}</p>
//               </div>
//             ) : (
//               messages.map((message) => (
//                 <div
//                   key={message.id}
//                   className={`flex gap-3 ${
//                     message.type === 'human' ? 'justify-end' : 'justify-start'
//                   }`}
//                 >
//                   {message.type === 'ai' && (
//                     <div className="flex-shrink-0">
//                       <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
//                         <Bot className="h-4 w-4" />
//                       </div>
//                     </div>
//                   )}
//                   <div className="flex flex-col gap-2 max-w-[80%]">
//                     <div
//                       className={`rounded-lg px-4 py-2 ${
//                         message.type === 'human'
//                           ? 'bg-primary text-primary-foreground'
//                           : 'bg-muted'
//                       }`}
//                     >
//                       {message.type === 'ai' ? (
//                         <AIMessageContent
//                           content={message.content}
//                           onReferenceClick={memoizedHandleReferenceClick}
//                         />
//                       ) : (
//                         <p className="text-sm break-all">{message.content}</p>
//                       )}
//                     </div>
//                     {message.type === 'ai' && (
//                       <MessageActions
//                         content={message.content}
//                         notebookId={notebookId}
//                       />
//                     )}
//                   </div>
//                   {message.type === 'human' && (
//                     <div className="flex-shrink-0">
//                       <div className="h-8 w-8 rounded-full bg-primary flex items-center justify-center">
//                         <User className="h-4 w-4 text-primary-foreground" />
//                       </div>
//                     </div>
//                   )}
//                 </div>
//               ))
//             )}

//             {/* Render suggested questions outside the message loop for better performance */}
//             {suggestedQuestions.length > 0 && messages.length > 0 && (
//               <SuggestedQuestionsCard
//                 suggestedQuestions={suggestedQuestions}
//                 onSelectQuestion={(question) => memoizedOnSendMessage(question, modelOverride)}
//                 isStreaming={isStreaming}
//               />
//             )}

//             <div ref={messagesEndRef} />
//           </div>
//         </div>

//         {/* Context Indicators */}
//         {contextIndicators && (
//           <div className="border-t px-4 py-2">
//             <div className="flex flex-wrap gap-2 text-xs">
//               {contextIndicators.sources?.length > 0 && (
//                 <Badge variant="outline" className="gap-1">
//                   <FileText className="h-3 w-3" />
//                   {contextIndicators.sources.length} {t.navigation.sources}
//                 </Badge>
//               )}
//               {contextIndicators.insights?.length > 0 && (
//                 <Badge variant="outline" className="gap-1">
//                   <Lightbulb className="h-3 w-3" />
//                   {contextIndicators.insights.length} {contextIndicators.insights.length === 1 ? t.common.insight : t.common.insights}
//                 </Badge>
//               )}
//               {contextIndicators.notes?.length > 0 && (
//                 <Badge variant="outline" className="gap-1">
//                   <StickyNote className="h-3 w-3" />
//                   {contextIndicators.notes.length} {contextIndicators.notes.length === 1 ? t.common.note : t.common.notes}
//                 </Badge>
//               )}
//             </div>
//           </div>
//         )}

//         {/* Notebook Context Indicator */}
//         {notebookContextStats && (
//           <ContextIndicator
//             sourcesInsights={notebookContextStats.sourcesInsights}
//             sourcesFull={notebookContextStats.sourcesFull}
//             notesCount={notebookContextStats.notesCount}
//             tokenCount={notebookContextStats.tokenCount}
//             charCount={notebookContextStats.charCount}
//           />
//         )}

//         {/* Input Area */}
//         <ChatInputArea
//           onSendMessage={handleSend}
//           isStreaming={isStreaming}
//           modelOverride={modelOverride}
//           onModelChange={onModelChange}
//           chatInputId={chatInputId}
//           keyHint={keyHint}
//           t={t}
//         />
//       </CardContent>
//     </Card>
//     </div>
//   )
// }

// // Helper component to render AI messages with clickable references - memoized for performance
// const AIMessageContent = React.memo(function AIMessageContentComponent({
//   content,
//   onReferenceClick
// }: {
//   content: string
//   onReferenceClick: (type: string, id: string) => void
// }) {
//   const { t } = useTranslation()
//   const markdownWithCompactRefs = convertReferencesToCompactMarkdown(content, t.common.references)
//   const LinkComponent = createCompactReferenceLinkComponent(onReferenceClick)

//   return (
//     <div className="prose prose-sm prose-neutral dark:prose-invert max-w-none break-words prose-headings:font-semibold prose-a:text-blue-600 prose-a:break-all prose-code:bg-muted prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-p:mb-4 prose-p:leading-7 prose-li:mb-2">
//       <ReactMarkdown
//         remarkPlugins={[remarkGfm]}
//         components={{
//           a: LinkComponent,
//           p: ({ children }) => <p className="mb-4">{children}</p>,
//           h1: ({ children }) => <h1 className="mb-4 mt-6">{children}</h1>,
//           h2: ({ children }) => <h2 className="mb-3 mt-5">{children}</h2>,
//           h3: ({ children }) => <h3 className="mb-3 mt-4">{children}</h3>,
//           h4: ({ children }) => <h4 className="mb-2 mt-4">{children}</h4>,
//           h5: ({ children }) => <h5 className="mb-2 mt-3">{children}</h5>,
//           h6: ({ children }) => <h6 className="mb-2 mt-3">{children}</h6>,
//           li: ({ children }) => <li className="mb-1">{children}</li>,
//           ul: ({ children }) => <ul className="mb-4 space-y-1">{children}</ul>,
//           ol: ({ children }) => <ol className="mb-4 space-y-1">{children}</ol>,
//           table: ({ children }) => (
//             <div className="my-4 overflow-x-auto">
//               <table className="min-w-full border-collapse border border-border">{children}</table>
//             </div>
//           ),
//           thead: ({ children }) => <thead className="bg-muted">{children}</thead>,
//           tbody: ({ children }) => <tbody>{children}</tbody>,
//           tr: ({ children }) => <tr className="border-b border-border">{children}</tr>,
//           th: ({ children }) => <th className="border border-border px-3 py-2 text-left font-semibold">{children}</th>,
//           td: ({ children }) => <td className="border border-border px-3 py-2">{children}</td>,
//         }}
//       >
//         {markdownWithCompactRefs}
//       </ReactMarkdown>
//     </div>
//   )
// })

// // Suggested questions card component - memoized for performance
// const SuggestedQuestionsCard = React.memo(function SuggestedQuestionsCardComponent({
//   suggestedQuestions,
//   onSelectQuestion,
//   isStreaming
// }: {
//   suggestedQuestions: string[]
//   onSelectQuestion: (question: string) => void
//   isStreaming: boolean
// }) {
//   return (
//     <div className="flex flex-col gap-1.5 mt-3 ml-8">
//       <p className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">Suggested questions</p>
//       <div className="flex flex-col gap-1.5">
//         {suggestedQuestions.map((question, idx) => {
//           const words = question.trim().split(/\s+/)
//           const short = words.length > 8
//             ? words.slice(0, 8).join(' ').replace(/[.,;:!]$/, '') + '?'
//             : question
//           return (
//             <Button
//               key={idx}
//               variant="outline"
//               size="sm"
//               className="justify-start text-left h-auto py-1.5 px-3 text-xs w-fit max-w-full"
//               title={question}
//               onClick={() => onSelectQuestion(question)}
//               disabled={isStreaming}
//             >
//               <Lightbulb className="h-3 w-3 mr-2 shrink-0" />
//               <span className="whitespace-nowrap">{short}</span>
//             </Button>
//           )
//         })}
//       </div>
//     </div>
//   )
// })

// // Input area component - completely isolated with its own state to prevent parent re-renders
// const ChatInputArea = React.memo(function ChatInputAreaComponent({
//   onSendMessage,
//   isStreaming,
//   modelOverride,
//   onModelChange,
//   chatInputId,
//   keyHint,
//   t
// }: {
//   onSendMessage: (message: string) => void
//   isStreaming: boolean
//   modelOverride?: string
//   onModelChange?: (model?: string) => void
//   chatInputId: string
//   keyHint: string
//   t: any
// }) {
//   // Local state - ONLY affects this component, not parent
//   const [input, setInput] = useState('')

//   // Handle input changes - stays local
//   const handleChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
//     setInput(e.target.value)
//   }, [])

//   // Handle send - calls parent with message, then clears local state
//   const handleSend = useCallback(() => {
//     if (input.trim() && !isStreaming) {
//       onSendMessage(input.trim())
//       setInput('')
//     }
//   }, [input, isStreaming, onSendMessage])

//   // Handle key down
//   const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
//     if (e.key === 'Enter' && !e.shiftKey) {
//       e.preventDefault()
//       handleSend()
//     }
//   }, [handleSend])

//   return (
//     <div className="flex-shrink-0 p-4 space-y-3 border-t">
//       {onModelChange && (
//         <div className="flex items-center justify-between">
//           <span className="text-xs text-muted-foreground">{t.chat.model}</span>
//           <ModelSelector
//             currentModel={modelOverride}
//             onModelChange={onModelChange}
//             disabled={isStreaming}
//           />
//         </div>
//       )}
//       <div className="flex gap-2 items-end min-w-0">
//         <Textarea
//           id={chatInputId}
//           name="chat-message"
//           autoComplete="off"
//           value={input}
//           onChange={handleChange}
//           onKeyDown={handleKeyDown}
//           placeholder={`${t.chat.sendPlaceholder} (${t.chat.pressToSend.replace('{key}', keyHint)})`}
//           disabled={isStreaming}
//           className="flex-1 min-h-[40px] max-h-[100px] resize-none py-2 px-3 min-w-0"
//           rows={1}
//         />
//         <Button
//           onClick={handleSend}
//           disabled={!input.trim() || isStreaming}
//           size="icon"
//           className="h-[40px] w-[40px] flex-shrink-0"
//         >
//           {isStreaming ? (
//             <Send className="h-4 w-4 opacity-40" />
//           ) : (
//             <Send className="h-4 w-4" />
//           )}
//         </Button>
//       </div>
//     </div>
//   )
// }, (prevProps, nextProps) => {
//   // Custom comparison - only re-render if these props actually change
//   return (
//     prevProps.isStreaming === nextProps.isStreaming &&
//     prevProps.modelOverride === nextProps.modelOverride &&
//     prevProps.onModelChange === nextProps.onModelChange &&
//     prevProps.onSendMessage === nextProps.onSendMessage
//   )
// })





'use client'

import React, { useState, useRef, useEffect, useId, useCallback, useMemo } from 'react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog'
import { Bot, User, Send, FileText, Lightbulb, StickyNote, Clock } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
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
import { useTranslation } from '@/lib/hooks/use-translation'

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
  // Suggested follow-up questions
  suggestedQuestions?: string[]
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
  notebookId,
  suggestedQuestions = []
}: ChatPanelProps) {
  const { t } = useTranslation()
  const chatInputId = useId()
  const [sessionManagerOpen, setSessionManagerOpen] = useState(false)
  const scrollAreaRef = useRef<HTMLDivElement>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const isAtBottomRef = useRef(true)
  const prevMessageCountRef = useRef(0)
  const { openModal } = useModalManager()

  const handleReferenceClick = (type: string, id: string) => {
    const modalType = type === 'source_insight' ? 'insight' : type as 'source' | 'note' | 'insight'
    try {
      openModal(modalType, id)
    } catch {
      toast.error(t.common.noResults)
    }
  }

  // Memoize the send message callback to prevent unnecessary re-renders
  const memoizedOnSendMessage = useCallback(onSendMessage, [onSendMessage])

  // Track if user is scrolled to bottom
  const handleScroll = useCallback(() => {
    const el = scrollAreaRef.current
    if (!el) return
    isAtBottomRef.current = el.scrollHeight - el.scrollTop - el.clientHeight < 80
  }, [])

  // Memoize the reference click handler
  const memoizedHandleReferenceClick = useCallback(handleReferenceClick, [openModal, t.common.noResults])

  // Scroll to bottom on new messages when appropriate
  useEffect(() => {
    const newCount = messages.length
    const lastMsg = messages[messages.length - 1]
    if (newCount > prevMessageCountRef.current) {
      const shouldScroll = lastMsg?.type === 'human' || isAtBottomRef.current
      if (shouldScroll) {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
        isAtBottomRef.current = true
      }
    }
    prevMessageCountRef.current = newCount
  }, [messages])

  const handleSend = useCallback((messageText: string) => {
    if (messageText.trim() && !isStreaming) {
      onSendMessage(messageText.trim(), modelOverride)
    }
  }, [isStreaming, onSendMessage, modelOverride])

  const keyHint = 'Enter'

  return (
    <div className="flex flex-col h-full min-h-0 overflow-hidden">
      <Card className="flex flex-col h-full min-h-0 overflow-hidden">
        <CardHeader className="pb-3 flex-shrink-0">
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Bot className="h-5 w-5" />
              {title || (contextType === 'source' ? t.chat.chatWith.replace('{name}', t.navigation.sources) : t.chat.chatWith.replace('{name}', t.common.notebook))}
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
                  <span className="text-xs">{t.chat.sessions}</span>
                </Button>
                <DialogContent className="sm:max-w-[420px] p-0 overflow-hidden">
                  <DialogTitle className="sr-only">{t.chat.sessionsTitle}</DialogTitle>
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

        <CardContent className="flex-1 flex flex-col min-h-0 p-0 overflow-hidden">
          <div
            className="flex-1 min-h-0 overflow-y-auto px-4"
            ref={scrollAreaRef}
            onScroll={handleScroll}
            style={{ overflowAnchor: 'auto' }}
          >
            <div className="space-y-4 py-4">
              {messages.length === 0 && !isStreaming ? (
                <div className="text-center text-muted-foreground py-8">
                  <Bot className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p className="text-sm">
                    {t.chat.startConversation.replace('{type}', contextType === 'source' ? t.navigation.sources : t.common.notebook)}
                  </p>
                  <p className="text-xs mt-2">{t.chat.askQuestions}</p>
                </div>
              ) : (
                messages.map((message) => (
                  <div
                    key={message.id}
                    className={`flex gap-3 ${message.type === 'human' ? 'justify-end' : 'justify-start'}`}
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
                            onReferenceClick={memoizedHandleReferenceClick}
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
                        <div className="h-8 w-8 rounded-full bg-primary flex items-center justify-center">
                          <User className="h-4 w-4 text-primary-foreground" />
                        </div>
                      </div>
                    )}
                  </div>
                ))
              )}

              {/* ✅ FIX: Only render SuggestedQuestionsCard once, after all messages, when not streaming */}
              {suggestedQuestions.length > 0 && messages.length > 0 && !isStreaming && (
                <SuggestedQuestionsCard
                  key="suggested-questions"
                  suggestedQuestions={suggestedQuestions}
                  onSelectQuestion={(question) => memoizedOnSendMessage(question, modelOverride)}
                  isStreaming={isStreaming}
                />
              )}

              <div ref={messagesEndRef} />
            </div>
          </div>

          {/* Context Indicators */}
          {contextIndicators && (
            <div className="border-t px-4 py-2">
              <div className="flex flex-wrap gap-2 text-xs">
                {contextIndicators.sources?.length > 0 && (
                  <Badge variant="outline" className="gap-1">
                    <FileText className="h-3 w-3" />
                    {contextIndicators.sources.length} {t.navigation.sources}
                  </Badge>
                )}
                {contextIndicators.insights?.length > 0 && (
                  <Badge variant="outline" className="gap-1">
                    <Lightbulb className="h-3 w-3" />
                    {contextIndicators.insights.length} {contextIndicators.insights.length === 1 ? t.common.insight : t.common.insights}
                  </Badge>
                )}
                {contextIndicators.notes?.length > 0 && (
                  <Badge variant="outline" className="gap-1">
                    <StickyNote className="h-3 w-3" />
                    {contextIndicators.notes.length} {contextIndicators.notes.length === 1 ? t.common.note : t.common.notes}
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
          <ChatInputArea
            onSendMessage={handleSend}
            isStreaming={isStreaming}
            modelOverride={modelOverride}
            onModelChange={onModelChange}
            chatInputId={chatInputId}
            keyHint={keyHint}
            t={t}
          />
        </CardContent>
      </Card>
    </div>
  )
}

// Helper component to render AI messages with clickable references - memoized for performance
const AIMessageContent = React.memo(function AIMessageContentComponent({
  content,
  onReferenceClick
}: {
  content: string
  onReferenceClick: (type: string, id: string) => void
}) {
  const { t } = useTranslation()
  const markdownWithCompactRefs = convertReferencesToCompactMarkdown(content, t.common.references)
  const LinkComponent = createCompactReferenceLinkComponent(onReferenceClick)

  return (
    <div className="prose prose-sm prose-neutral dark:prose-invert max-w-none break-words prose-headings:font-semibold prose-a:text-blue-600 prose-a:break-all prose-code:bg-muted prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-p:mb-4 prose-p:leading-7 prose-li:mb-2">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
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
          table: ({ children }) => (
            <div className="my-4 overflow-x-auto">
              <table className="min-w-full border-collapse border border-border">{children}</table>
            </div>
          ),
          thead: ({ children }) => <thead className="bg-muted">{children}</thead>,
          tbody: ({ children }) => <tbody>{children}</tbody>,
          tr: ({ children }) => <tr className="border-b border-border">{children}</tr>,
          th: ({ children }) => <th className="border border-border px-3 py-2 text-left font-semibold">{children}</th>,
          td: ({ children }) => <td className="border border-border px-3 py-2">{children}</td>,
        }}
      >
        {markdownWithCompactRefs}
      </ReactMarkdown>
    </div>
  )
})

// ✅ FIX: Suggested questions card - shows FULL question text, no truncation
const SuggestedQuestionsCard = React.memo(function SuggestedQuestionsCardComponent({
  suggestedQuestions,
  onSelectQuestion,
  isStreaming
}: {
  suggestedQuestions: string[]
  onSelectQuestion: (question: string) => void
  isStreaming: boolean
}) {
  return (
    <div className="flex flex-col gap-1.5 mt-3 ml-8">
      <p className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
        Suggested questions
      </p>
      <div className="flex flex-col gap-1.5">
        {suggestedQuestions.map((question, idx) => (
          <Button
            key={idx}
            variant="outline"
            size="sm"
            className="justify-start text-left h-auto py-1.5 px-3 text-xs w-fit max-w-sm"
            onClick={() => onSelectQuestion(question)}
            disabled={isStreaming}
            title={question}
          >
            <Lightbulb className="h-3 w-3 mr-2 shrink-0 mt-0.5 flex-shrink-0" />
            <span className="truncate">{question}</span>
          </Button>
        ))}
      </div>
    </div>
  )
})

// Input area component - completely isolated with its own state to prevent parent re-renders
const ChatInputArea = React.memo(function ChatInputAreaComponent({
  onSendMessage,
  isStreaming,
  modelOverride,
  onModelChange,
  chatInputId,
  keyHint,
  t
}: {
  onSendMessage: (message: string) => void
  isStreaming: boolean
  modelOverride?: string
  onModelChange?: (model?: string) => void
  chatInputId: string
  keyHint: string
  t: any
}) {
  const [input, setInput] = useState('')

  const handleChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value)
  }, [])

  const handleSend = useCallback(() => {
    if (input.trim() && !isStreaming) {
      onSendMessage(input.trim())
      setInput('')
    }
  }, [input, isStreaming, onSendMessage])

  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }, [handleSend])

  return (
    <div className="flex-shrink-0 p-4 space-y-3 border-t">
      {onModelChange && (
        <div className="flex items-center justify-between">
          <span className="text-xs text-muted-foreground">{t.chat.model}</span>
          <ModelSelector
            currentModel={modelOverride}
            onModelChange={onModelChange}
            disabled={isStreaming}
          />
        </div>
      )}
      <div className="flex gap-2 items-end min-w-0">
        <Textarea
          id={chatInputId}
          name="chat-message"
          autoComplete="off"
          value={input}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder={`${t.chat.sendPlaceholder} (${t.chat.pressToSend.replace('{key}', keyHint)})`}
          disabled={isStreaming}
          className="flex-1 min-h-[40px] max-h-[100px] resize-none py-2 px-3 min-w-0"
          rows={1}
        />
        <Button
          onClick={handleSend}
          disabled={!input.trim() || isStreaming}
          size="icon"
          className="h-[40px] w-[40px] flex-shrink-0"
        >
          <Send className={`h-4 w-4 ${isStreaming ? 'opacity-40' : ''}`} />
        </Button>
      </div>
    </div>
  )
}, (prevProps, nextProps) => {
  return (
    prevProps.isStreaming === nextProps.isStreaming &&
    prevProps.modelOverride === nextProps.modelOverride &&
    prevProps.onModelChange === nextProps.onModelChange &&
    prevProps.onSendMessage === nextProps.onSendMessage
  )
})