'use client'

import { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import {
  Bold, Italic, Strikethrough, Link, Quote, Code,
  Image as ImageIcon, Table, List, ListOrdered,
  ChevronLeft, ChevronRight, Columns
} from "lucide-react"
import {
  ResizablePanelGroup,
  ResizablePanel,
  ResizableHandle,
} from "@/components/ui/resizable"
import { Separator } from "@/components/ui/separator"
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { useQueryClient } from '@tanstack/react-query'
import { isAxiosError } from 'axios'
import { sourcesApi } from '@/lib/api/sources'
import { insightsApi, SourceInsightResponse } from '@/lib/api/insights'
import { transformationsApi } from '@/lib/api/transformations'
import { embeddingApi } from '@/lib/api/embedding'
import { SourceDetailResponse } from '@/lib/types/api'
import { Transformation } from '@/lib/types/transformations'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { InlineEdit } from '@/components/common/InlineEdit'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Label } from '@/components/ui/label'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Link as LinkIcon,
  Upload,
  AlignLeft,
  ExternalLink,
  Download,
  Copy,
  CheckCircle,
  Youtube,
  MoreVertical,
  Trash2,
  Sparkles,
  Plus,
  Lightbulb,
  Database,
  AlertCircle,
  MessageSquare,
} from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { getDateLocale } from '@/lib/utils/date-locale'
import { toast } from 'sonner'
import { useTranslation } from '@/lib/hooks/use-translation'
import { SourceInsightDialog } from '@/components/source/SourceInsightDialog'
import { NotebookAssociations } from '@/components/source/NotebookAssociations'

// Safe paginated content renderer — avoids browser crash on large documents
const PAGE = 3000
function SafeContent({ text, noContentLabel }: { text: string; noContentLabel: string }) {
  const [visible, setVisible] = useState(PAGE)
  if (!text) return <p className="text-sm text-muted-foreground">{noContentLabel}</p>
  const slice = text.slice(0, visible)
  const hasMore = visible < text.length
  return (
    <div className="space-y-2">
      {slice.split(/\n{2,}/).filter(Boolean).map((para, i) => (
        <p key={i} className="text-sm leading-relaxed whitespace-pre-wrap break-words">{para}</p>
      ))}
      {hasMore && (
        <div className="pt-3 flex flex-col items-center gap-1">
          <span className="text-xs text-muted-foreground">
            {visible.toLocaleString()} / {text.length.toLocaleString()} chars
          </span>
          <button
            onClick={() => setVisible(v => v + PAGE)}
            className="text-xs text-blue-600 hover:underline"
          >
            Load more
          </button>
        </div>
      )}
    </div>
  )
}

// ─── Smart Document Renderer ───────────────────────────────────────────────
function renderInline(raw: string): React.ReactNode {
  // Strip leading asterisks noise like **** or ***
  const clean = raw.replace(/\*{3,}/g, '').trim()
  const parts = clean.split(/(\*{1,2}[^*]+\*{1,2})/g)
  return parts.map((part, i) => {
    const m = part.match(/^\*{1,2}([^*]+)\*{1,2}$/)
    if (m) return <strong key={i} className="font-semibold text-slate-900 dark:text-white">{m[1].trim()}</strong>
    return part.replace(/\*/g, '').replace(/:-/g, ':')
  })
}

function SmartDocumentRenderer({ text }: { text: string }) {
  const lines = text.replace(/\r\n/g, '\n').split('\n')

  type Block =
    | { type: 'section';    label: string }
    | { type: 'subheading'; text: string }
    | { type: 'keyval';     key: string; value: string }
    | { type: 'bullet';     text: string }
    | { type: 'timeline';   year: string; title: string; detail: string }
    | { type: 'paragraph';  text: string }

  const blocks: Block[] = []

  for (const rawLine of lines) {
    const line = rawLine.trim()
    if (!line) continue

    // ── PART section header
    const partM = line.match(/^\*{0,2}(PART\s*[-–—\s]*(?:I{1,3}V?|VI{0,3}|IX|X{1,3}|\d+)[^*]*)\*{0,2}$/i)
    if (partM) {
      blocks.push({ type: 'section', label: partM[1].replace(/\*+/g, '').trim().toUpperCase() })
      continue
    }

    // ── Bold-only line = sub-heading
    const headM = line.match(/^\*{1,2}([^*\n]{2,80})\*{1,2}$/)
    if (headM) {
      blocks.push({ type: 'subheading', text: headM[1].trim() })
      continue
    }

    // ── Key : Value  (e.g. "Date of birth : 21 Oct" or "**Name**:- Value")
    const kvM = line.match(/^\*{0,2}([^*:|\n]{2,40})\*{0,2}\s*:[-\s]\*{0,2}\s*(.+)$/)
    if (kvM) {
      blocks.push({ type: 'keyval', key: kvM[1].replace(/\*/g, '').trim(), value: kvM[2].replace(/\*/g, '').trim() })
      continue
    }

    // ── Timeline: year at start
    const yrM = line.match(/^((?:19|20)\d{2}(?:[–\-]\d{2,4})?)[:\s,.\-–]+((?:\*{1,2}[^*\n]+\*{1,2})?[^\n]*)/)
    if (yrM) {
      // Next line might be detail — handle as single block; detail collected later
      const rest = yrM[2].replace(/\*{1,2}/g, '').trim()
      // If the rest starts with bold, treat that as the title
      const titleM = yrM[2].match(/^\*{1,2}([^*]+)\*{1,2}(.*)/)
      if (titleM) {
        blocks.push({ type: 'timeline', year: yrM[1], title: titleM[1].trim(), detail: titleM[2].trim() })
      } else {
        blocks.push({ type: 'timeline', year: yrM[1], title: rest, detail: '' })
      }
      continue
    }

    // ── Bullet
    if (/^[-•]\s+/.test(line)) {
      blocks.push({ type: 'bullet', text: line.replace(/^[-•]\s+/, '') })
      continue
    }

    blocks.push({ type: 'paragraph', text: line })
  }

  // ── Attach consecutive paragraphs after timeline as its detail
  for (let i = 0; i < blocks.length - 1; i++) {
    if (blocks[i].type === 'timeline' && blocks[i + 1].type === 'paragraph') {
      const b = blocks[i] as Extract<Block, { type: 'timeline' }>
      const next = blocks[i + 1] as Extract<Block, { type: 'paragraph' }>
      if (!b.detail) { b.detail = next.text; blocks.splice(i + 1, 1) }
    }
  }

  // ── Group consecutive same-type blocks
  type Group =
    | { kind: 'section';  label: string }
    | { kind: 'subheading'; text: string }
    | { kind: 'keyvals';  pairs: { key: string; value: string }[] }
    | { kind: 'bullets';  items: string[] }
    | { kind: 'timeline'; items: { year: string; title: string; detail: string }[] }
    | { kind: 'paragraph'; text: string }

  const groups: Group[] = []
  for (const b of blocks) {
    const last = groups[groups.length - 1]
    if (b.type === 'keyval') {
      if (last?.kind === 'keyvals') { last.pairs.push({ key: b.key, value: b.value }); continue }
      groups.push({ kind: 'keyvals', pairs: [{ key: b.key, value: b.value }] }); continue
    }
    if (b.type === 'bullet') {
      if (last?.kind === 'bullets') { last.items.push(b.text); continue }
      groups.push({ kind: 'bullets', items: [b.text] }); continue
    }
    if (b.type === 'timeline') {
      if (last?.kind === 'timeline') { last.items.push(b); continue }
      groups.push({ kind: 'timeline', items: [b] }); continue
    }
    if (b.type === 'section')    { groups.push({ kind: 'section',    label: b.label }); continue }
    if (b.type === 'subheading') { groups.push({ kind: 'subheading', text: b.text  }); continue }
    if (b.type === 'paragraph')  { groups.push({ kind: 'paragraph',  text: b.text  }); continue }
  }

  return (
    <div>
      {groups.map((g, i) => {
        /* ── Section divider ── */
        if (g.kind === 'section') return (
          <div key={i} className={`flex items-center gap-3 ${i > 0 ? 'mt-9' : 'mt-1'} mb-4`}>
            <div className="h-px flex-1 bg-slate-200 dark:bg-slate-700" />
            <span className="text-[9px] font-black tracking-[0.22em] text-slate-400 dark:text-slate-500 uppercase shrink-0 px-1">
              {g.label}
            </span>
            <div className="h-px flex-1 bg-slate-200 dark:bg-slate-700" />
          </div>
        )

        /* ── Sub-heading ── */
        if (g.kind === 'subheading') return (
          <p key={i} className="text-[13px] font-bold text-slate-700 dark:text-slate-200 mt-5 mb-2 uppercase tracking-wide">
            {g.text}
          </p>
        )

        /* ── Key-value grid ── */
        if (g.kind === 'keyvals') return (
          <div key={i} className="grid grid-cols-2 gap-x-6 gap-y-3 mb-5 bg-slate-50 dark:bg-slate-800/40 rounded-xl p-4 border border-slate-100 dark:border-slate-800">
            {g.pairs.map((kv, j) => (
              <div key={j}>
                <p className="text-[10px] font-semibold uppercase tracking-[0.1em] text-slate-400 dark:text-slate-500 mb-0.5">{kv.key}</p>
                <p className="text-sm font-semibold text-slate-800 dark:text-slate-100">{renderInline(kv.value)}</p>
              </div>
            ))}
          </div>
        )

        /* ── Bullet list ── */
        if (g.kind === 'bullets') return (
          <ul key={i} className="mb-4 space-y-2">
            {g.items.map((item, j) => (
              <li key={j} className="flex items-start gap-2.5">
                <span className="mt-[7px] h-1.5 w-1.5 rounded-full bg-blue-500 shrink-0" />
                <span className="text-sm text-slate-600 dark:text-slate-300 leading-[1.75]">
                  {renderInline(item)}
                </span>
              </li>
            ))}
          </ul>
        )

        /* ── Timeline ── */
        if (g.kind === 'timeline') return (
          <div key={i} className="relative mb-5 mt-2">
            <div className="absolute left-[52px] top-0 bottom-0 w-px bg-slate-200 dark:bg-slate-700" />
            <div className="space-y-5">
              {g.items.map((item, j) => (
                <div key={j} className="flex gap-4 items-start relative">
                  <span className="w-12 shrink-0 text-right text-[11px] font-bold text-blue-600 dark:text-blue-400 tabular-nums pt-0.5 leading-5">
                    {item.year}
                  </span>
                  <div className="relative flex-1 pl-4">
                    <div className="absolute left-[-5px] top-[6px] h-2 w-2 rounded-full bg-blue-500 ring-2 ring-white dark:ring-slate-900" />
                    {item.title && (
                      <p className="text-[13px] font-semibold text-slate-800 dark:text-slate-100 leading-snug">
                        {item.title}
                      </p>
                    )}
                    {item.detail && (
                      <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5 leading-relaxed">
                        {renderInline(item.detail)}
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )

        /* ── Paragraph ── */
        if (g.kind === 'paragraph') return (
          <p key={i} className="text-sm text-slate-600 dark:text-slate-300 leading-[1.85] mb-3">
            {renderInline(g.text)}
          </p>
        )

        return null
      })}
    </div>
  )
}

interface SourceDetailContentProps {
  sourceId: string
  showChatButton?: boolean
  onChatClick?: () => void
  onClose?: () => void
}
export default function SystemPromptEditor() {
  const [content, setContent] = useState(`You are an expert information designer...`)
  const [viewMode, setViewMode] = useState<'editor' | 'split' | 'preview'>('split')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const showEditorOnly = () => setViewMode('editor')
  const showSplitView = () => setViewMode('split')
  const showPreviewOnly = () => setViewMode('preview')

  const insertFormat = (before: string, after: string = '') => {
    if (!textareaRef.current) return
    const textarea = textareaRef.current
    const start = textarea.selectionStart
    const end = textarea.selectionEnd
    const selectedText = content.substring(start, end)
    const newText = content.substring(0, start) + before + selectedText + after + content.substring(end)
    setContent(newText)
    setTimeout(() => {
      textarea.focus()
      textarea.setSelectionRange(start + before.length, end + before.length)
    }, 0)
  }

  return (
    <div className="flex flex-col h-[600px] w-full border rounded-xl overflow-hidden bg-background shadow-sm">
      {/* 1. Header & Toolbar */}
      <div className="flex items-center justify-between px-3 py-2 border-b bg-muted/10">
        <div className="flex items-center gap-1 overflow-x-auto no-scrollbar">
          <h2 className="text-sm font-semibold mr-4 shrink-0">System Prompt</h2>
          <ToolbarButton icon={<Bold className="h-4 w-4" />} onClick={() => insertFormat('**', '**')} />
          <ToolbarButton icon={<Italic className="h-4 w-4" />} onClick={() => insertFormat('_', '_')} />
          <ToolbarButton icon={<Strikethrough className="h-4 w-4" />} onClick={() => insertFormat('~~', '~~')} />
          <Separator orientation="vertical" className="mx-1 h-6" />
          <ToolbarButton icon={<Link className="h-4 w-4" />} onClick={() => insertFormat('[', '](url)')} />
          <ToolbarButton icon={<Quote className="h-4 w-4" />} onClick={() => insertFormat('> ')} />
          <ToolbarButton icon={<Code className="h-4 w-4" />} onClick={() => insertFormat('`', '`')} />
          <Separator orientation="vertical" className="mx-1 h-6" />
          <ToolbarButton icon={<ImageIcon className="h-4 w-4" />} onClick={() => insertFormat('![alt](', ')')} />
          <ToolbarButton icon={<Table className="h-4 w-4" />} onClick={() => insertFormat('\n| Column 1 | Column 2 |\n| -------- | -------- |\n| Text     | Text     |\n')} />
          <ToolbarButton icon={<List className="h-4 w-4" />} onClick={() => insertFormat('- ')} />
          <ToolbarButton icon={<ListOrdered className="h-4 w-4" />} onClick={() => insertFormat('1. ')} />
        </div>

        {/* 2. Layout Switcher (The 3 Buttons) */}
        <div className="flex items-center border rounded-md p-1 bg-background">
          <Button variant={viewMode === 'editor' ? 'secondary' : 'ghost'} size="icon" className="h-7 w-7" onClick={showEditorOnly} title="Editor Only">
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <Button variant={viewMode === 'split' ? 'secondary' : 'ghost'} size="icon" className="h-7 w-7" onClick={showSplitView} title="Split View">
            <Columns className="h-4 w-4" />
          </Button>
          <Button variant={viewMode === 'preview' ? 'secondary' : 'ghost'} size="icon" className="h-7 w-7" onClick={showPreviewOnly} title="Preview Only">
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* 3. Main Content Area */}
      <div className="flex-1 overflow-hidden h-full">
        {viewMode === 'editor' && (
          <div className="h-full p-4 overflow-y-auto">
            <textarea
              ref={textareaRef}
              value={content}
              onChange={(e) => setContent(e.target.value)}
              className="w-full h-full text-sm font-mono bg-transparent outline-none border-none resize-none leading-relaxed"
              placeholder="Start typing your system prompt..."
            />
          </div>
        )}

        {viewMode === 'preview' && (
          <div className="h-full p-6 bg-slate-50 dark:bg-slate-900/50 overflow-y-auto">
            <div className="prose prose-sm xl:prose-base dark:prose-invert max-w-none">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {content}
              </ReactMarkdown>
            </div>
          </div>
        )}

        {viewMode === 'split' && (
          <ResizablePanelGroup direction="horizontal">
            {/* Editor Panel */}
            <ResizablePanel defaultSize={50} minSize={20}>
              <div className="h-full p-4 overflow-y-auto">
                <textarea
                  ref={textareaRef}
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  className="w-full h-full text-sm font-mono bg-transparent outline-none border-none resize-none leading-relaxed"
                  placeholder="Start typing your system prompt..."
                />
              </div>
            </ResizablePanel>

            <ResizableHandle withHandle className="bg-border" />

            {/* Preview Panel */}
            <ResizablePanel defaultSize={50} minSize={20}>
              <div className="h-full p-6 bg-slate-50 dark:bg-slate-900/50 overflow-y-auto border-l">
                <div className="prose prose-sm xl:prose-base dark:prose-invert max-w-none">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {content}
                  </ReactMarkdown>
                </div>
              </div>
            </ResizablePanel>
          </ResizablePanelGroup>
        )}
      </div>
    </div>
  )
}


// Sub-component for Toolbar Buttons
function ToolbarButton({ icon, onClick }: { icon: React.ReactNode, onClick?: () => void }) {
  return (
    <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-foreground" onClick={onClick}>
      {icon}
    </Button>
  )
}


export function SourceDetailContent({
  sourceId,
  showChatButton = false,
  onChatClick,
  onClose
}: SourceDetailContentProps) {
  const { t, language } = useTranslation()
  const queryClient = useQueryClient()
  const [source, setSource] = useState<SourceDetailResponse | null>(null)
  const [insights, setInsights] = useState<SourceInsightResponse[]>([])
  const [transformations, setTransformations] = useState<Transformation[]>([])
  const [selectedTransformation, setSelectedTransformation] = useState<string>('')
  const [loading, setLoading] = useState(true)
  const [loadingInsights, setLoadingInsights] = useState(false)
  const [creatingInsight, setCreatingInsight] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  const [isEmbedding, setIsEmbedding] = useState(false)
  const [isDownloadingFile, setIsDownloadingFile] = useState(false)
  const [fileAvailable, setFileAvailable] = useState<boolean | null>(null)
  const [selectedInsight, setSelectedInsight] = useState<SourceInsightResponse | null>(null)
  const [insightToDelete, setInsightToDelete] = useState<string | null>(null)
  const [deletingInsight, setDeletingInsight] = useState(false)
  const [isMarkdownView, setIsMarkdownView] = useState(false)


  const fetchSource = useCallback(async () => {
    try {
      setLoading(true)
      const data = await sourcesApi.get(sourceId)
      setSource(data)
      if (typeof data.file_available === 'boolean') {
        setFileAvailable(data.file_available)
      } else if (!data.asset?.file_path) {
        setFileAvailable(null)
      } else {
        setFileAvailable(null)
      }
    } catch (err) {
      console.error('Failed to fetch source:', err)
      setError(t.sources.loadFailed)
    } finally {
      setLoading(false)
    }
  }, [sourceId, t])

  const fetchInsights = useCallback(async () => {
    try {
      setLoadingInsights(true)
      const data = await insightsApi.listForSource(sourceId)
      setInsights(data)
    } catch (err) {
      console.error('Failed to fetch insights:', err)
    } finally {
      setLoadingInsights(false)
    }
  }, [sourceId])

  const fetchTransformations = useCallback(async () => {
    try {
      const data = await transformationsApi.list()
      setTransformations(data)
    } catch (err) {
      console.error('Failed to fetch transformations:', err)
    }
  }, [])

  useEffect(() => {
    if (sourceId) {
      void fetchSource()
      void fetchInsights()
      void fetchTransformations()
    }
  }, [fetchInsights, fetchSource, fetchTransformations, sourceId])

  const createInsight = async () => {
    if (!selectedTransformation) {
      toast.error(t.sources.selectTransformation)
      return
    }

    try {
      setCreatingInsight(true)
      const response = await insightsApi.create(sourceId, {
        transformation_id: selectedTransformation
      })
      // Show toast for async operation
      toast.success(t.sources.insightGenerationStarted)
      setSelectedTransformation('')

      // Poll for command completion if we have a command_id
      if (response.command_id) {
        // Poll in background (don't block UI)
        insightsApi.waitForCommand(response.command_id, {
          maxAttempts: 120, // Up to 4 minutes (120 * 2s)
          intervalMs: 2000
        }).then(success => {
          if (success) {
            void fetchInsights()
            // Invalidate sources queries so notebook page refreshes with updated insights_count
            queryClient.invalidateQueries({ queryKey: ['sources'] })
          }
        }).catch(err => {
          console.error('Error waiting for insight command:', err)
        })
      } else {
        // Fallback: refresh after delay if no command_id
        setTimeout(() => {
          void fetchInsights()
          // Also invalidate sources queries
          queryClient.invalidateQueries({ queryKey: ['sources'] })
        }, 5000)
      }
    } catch (err) {
      console.error('Failed to create insight:', err)
      toast.error(t.common.error)
    } finally {
      setCreatingInsight(false)
    }
  }

  const handleDeleteInsight = async (e?: React.MouseEvent) => {
    e?.preventDefault()
    if (!insightToDelete) return

    try {
      setDeletingInsight(true)
      await insightsApi.delete(insightToDelete)
      toast.success(t.common.success)
      setInsightToDelete(null)
      await fetchInsights()
    } catch (err) {
      console.error('Failed to delete insight:', err)
      toast.error(t.common.error)
    } finally {
      setDeletingInsight(false)
    }
  }

  const handleUpdateTitle = async (title: string) => {
    if (!source || title === source.title) return

    try {
      await sourcesApi.update(sourceId, { title })
      toast.success(t.common.success)
      setSource({ ...source, title })
    } catch (err) {
      console.error('Failed to update source title:', err)
      toast.error(t.common.error)
      await fetchSource()
    }
  }

  const handleEmbedContent = async () => {
    if (!source) return

    try {
      setIsEmbedding(true)
      const response = await embeddingApi.embedContent(sourceId, 'source')
      toast.success(response.message || t.common.success)
      await fetchSource()
    } catch (err) {
      console.error('Failed to embed content:', err)
      toast.error(t.common.error)
    } finally {
      setIsEmbedding(false)
    }
  }

  const extractFilename = (pathOrUrl: string | undefined, fallback: string) => {
    if (!pathOrUrl) {
      return fallback
    }
    const segments = pathOrUrl.split(/[/\\]/)
    return segments.pop() || fallback
  }

  const parseContentDisposition = (header?: string | null) => {
    if (!header) {
      return null
    }
    const match = header.match(/filename\*?=([^;]+)/i)
    if (!match) {
      return null
    }
    const value = match[1].trim()
    if (value.toLowerCase().startsWith("utf-8''")) {
      return decodeURIComponent(value.slice(7))
    }
    return value.replace(/^["']|["']$/g, '')
  }

  const handleDownloadFile = async () => {
    if (!source?.asset?.file_path || isDownloadingFile || fileAvailable === false) {
      return
    }

    try {
      setIsDownloadingFile(true)
      const response = await sourcesApi.downloadFile(source.id)
      const filenameFromHeader = parseContentDisposition(
        response.headers?.['content-disposition'] as string | undefined
      )
      const fallbackName = extractFilename(source.asset.file_path, `source-${source.id}`)
      const filename = filenameFromHeader || fallbackName

      const blobUrl = window.URL.createObjectURL(response.data)
      const link = document.createElement('a')
      link.href = blobUrl
      link.download = filename
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(blobUrl)
      setFileAvailable(true)
      toast.success(t.common.success)
    } catch (err) {
      console.error('Failed to download file:', err)
      if (isAxiosError(err) && err.response?.status === 404) {
        setFileAvailable(false)
        toast.error(t.sources.fileUnavailable)
      } else {
        toast.error(t.common.error)
      }
    } finally {
      setIsDownloadingFile(false)
    }
  }

  const getSourceIcon = () => {
    if (!source) return null
    if (source.asset?.url) return <LinkIcon className="h-5 w-5" />
    if (source.asset?.file_path) return <Upload className="h-5 w-5" />
    return <AlignLeft className="h-5 w-5" />
  }

  const getSourceType = () => {
    if (!source) return 'unknown'
    if (source.asset?.url) return 'link'
    if (source.asset?.file_path) return 'file'
    return 'text'
  }

  const handleCopyUrl = useCallback(() => {
    if (source?.asset?.url) {
      navigator.clipboard.writeText(source.asset.url)
      setCopied(true)
      toast.success(t.sources.urlCopied)
      setTimeout(() => setCopied(false), 2000)
    }
  }, [source, t])

  const handleOpenExternal = useCallback(() => {
    if (source?.asset?.url) {
      window.open(source.asset.url, '_blank')
    }
  }, [source])

  const getYouTubeVideoId = (url: string): string | null => {
    const patterns = [
      /(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)/,
      /youtube\.com\/watch\?.*v=([^&\n?#]+)/
    ]

    for (const pattern of patterns) {
      const match = url.match(pattern)
      if (match) return match[1]
    }
    return null
  }

  const isYouTubeUrl = useMemo(() => {
    if (!source?.asset?.url) return false
    return !!(getYouTubeVideoId(source.asset.url))
  }, [source?.asset?.url])

  const youTubeVideoId = useMemo(() => {
    if (!source?.asset?.url) return null
    return getYouTubeVideoId(source.asset.url)
  }, [source?.asset?.url])

  const handleDelete = async () => {
    if (!source) return

    if (confirm(t.sources.deleteSourceConfirm || t.common.confirm)) {
      try {
        await sourcesApi.delete(source.id)
        toast.success(t.common.success)
        onClose?.()
      } catch (error) {
        console.error('Failed to delete source:', error)
        toast.error(t.common.error)
      }
    }
  }

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center p-8">
        <LoadingSpinner />
      </div>
    )
  }

  if (error || !source) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-4 p-8">
        <p className="text-red-500">{error || t.sources.notFound}</p>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="pb-4 px-2">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <InlineEdit
              value={source.title || ''}
              onSave={handleUpdateTitle}
              className="text-2xl font-bold"
              inputClassName="text-2xl font-bold"
              placeholder={t.sources.titlePlaceholder}
              emptyText={t.sources.untitledSource}
            />
            <p className="mt-1 text-sm text-muted-foreground">
              {t.sources.id}: {source.id}
            </p>
          </div>
          <div className="flex items-center gap-2">
            {getSourceIcon()}
            <Badge variant="secondary" className="text-sm">
              {getSourceType()}
            </Badge>

            {/* Chat with source button - only in modal */}
            {showChatButton && onChatClick && (
              <Button variant="outline" size="sm" onClick={onChatClick}>
                <MessageSquare className="h-4 w-4 mr-2" />
                {t.chat.chatWith.replace('{name}', t.navigation.sources)}
              </Button>
            )}

            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon">
                  <MoreVertical className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                {source.asset?.file_path && (
                  <>
                    <DropdownMenuItem
                      onClick={handleDownloadFile}
                      disabled={isDownloadingFile || fileAvailable === false}
                    >
                      <Download className="mr-2 h-4 w-4" />
                      {fileAvailable === false
                        ? t.sources.fileUnavailable
                        : isDownloadingFile
                          ? t.sources.preparing
                          : t.sources.downloadFile}
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                  </>
                )}
                <DropdownMenuItem
                  onClick={handleEmbedContent}
                  disabled={isEmbedding || source.embedded}
                >
                  <Database className="mr-2 h-4 w-4" />
                  {isEmbedding ? t.sources.embedding : source.embedded ? t.sources.alreadyEmbedded : t.sources.embedContent}
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  className="text-destructive"
                  onClick={handleDelete}
                >
                  <Trash2 className="mr-2 h-4 w-4" />
                  {t.sources.deleteSource}
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </div>

      {/* Tabs Content */}
      <div className="flex-1 overflow-y-auto px-2">
        <Tabs defaultValue="content" className="w-full">
          <TabsList className="grid w-full grid-cols-3 sticky top-0 z-10">
            <TabsTrigger value="content">{t.sources.content}</TabsTrigger>
            <TabsTrigger value="insights">
              {t.common.insights} {insights.length > 0 && `(${insights.length})`}
            </TabsTrigger>
            <TabsTrigger value="details">{t.sources.details}</TabsTrigger>
          </TabsList>

          <TabsContent value="content" className="mt-6">
            <Card>
              <CardHeader className="flex flex-row items-start justify-between">
                <div className="space-y-1.5">
                  <CardTitle className="flex items-center gap-2">
                    {isYouTubeUrl && <Youtube className="h-5 w-5" />}
                    {t.sources.content}
                  </CardTitle>
                  {source.asset?.url && !isYouTubeUrl && (
                    <CardDescription className="flex items-center gap-2">
                      <LinkIcon className="h-4 w-4" />
                      <a
                        href={source.asset.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="hover:underline text-blue-600"
                      >
                        {source.asset.url}
                      </a>
                    </CardDescription>
                  )}
                </div>
                {!isYouTubeUrl && source.full_text && (
                  <Button
                    variant="outline"
                    size="sm"
                    className="gap-2 font-semibold border-blue-200 text-blue-600 hover:bg-blue-50 hover:text-blue-700 hover:border-blue-400 dark:border-blue-800 dark:text-blue-400 dark:hover:bg-blue-950 transition-all"
                    onClick={() => setIsMarkdownView(true)}
                  >
                    <Sparkles className="h-4 w-4" />
                    Formatted View
                  </Button>
                )}
              </CardHeader>
              <CardContent>
                {isYouTubeUrl && youTubeVideoId && (
                  <div className="mb-6">
                    <div className="aspect-video rounded-lg overflow-hidden bg-black">
                      <iframe
                        src={`https://www.youtube.com/embed/${youTubeVideoId}`}
                        title={t.common.accessibility.ytVideo}
                        className="w-full h-full"
                        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                        allowFullScreen
                      />
                    </div>
                    {source.asset?.url && (
                      <div className="mt-2">
                        <a
                          href={source.asset.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-sm text-muted-foreground hover:underline inline-flex items-center gap-1"
                        >
                          <ExternalLink className="h-3 w-3" />
                          {t.sources.openOnYoutube}
                        </a>
                      </div>
                    )}
                  </div>
                )}
                {!isYouTubeUrl && source.full_text && (
                  <SafeContent text={source.full_text || ''} noContentLabel={t.sources.noContent} />
                )}
                {!isYouTubeUrl && !source.full_text && (
                  <SafeContent text={''} noContentLabel={t.sources.noContent} />
                )}
              </CardContent>
            </Card>

            {isMarkdownView && source.full_text && (
              <div
                className="fixed inset-0 z-[100] flex flex-col bg-white dark:bg-slate-900 w-full h-full overflow-hidden"
              >
                {/* ─── Header ─── */}
                <div className="flex items-center justify-between px-8 py-5 bg-slate-900 dark:bg-slate-950 shrink-0 border-b border-b-slate-800 shadow-sm relative z-10">
                  <div className="flex items-center gap-4">
                    <div className="h-9 w-9 rounded-lg bg-blue-600 flex items-center justify-center shadow-inner">
                      <Sparkles className="h-5 w-5 text-white" />
                    </div>
                    <div>
                      <p className="text-[11px] font-bold text-slate-400 uppercase tracking-widest leading-tight">Document Reader</p>
                      <h2 className="text-[15px] font-bold text-white leading-tight mt-0.5">Formatted View</h2>
                    </div>
                  </div>
                  <button
                    onClick={() => setIsMarkdownView(false)}
                    className="h-9 w-9 rounded-full bg-white/10 hover:bg-white/20 flex items-center justify-center text-slate-300 hover:text-white transition-all ring-1 ring-white/10"
                    aria-label="Close"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M18 6 6 18M6 6l12 12"/></svg>
                  </button>
                </div>

                {/* ─── Body ─── */}
                <div className="flex-1 overflow-y-auto bg-slate-50 dark:bg-[#0a0c10]">
                  <div className="max-w-[1100px] w-full mx-auto bg-white dark:bg-slate-900 min-h-full px-12 py-10 shadow-sm border-x border-slate-200 dark:border-slate-800">
                    <SmartDocumentRenderer text={source.full_text} />
                  </div>
                </div>

                {/* ─── Footer ─── */}
                <div className="flex items-center justify-between px-8 py-4 border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 shrink-0 relative z-10 w-full">
                  <span className="text-xs font-medium text-slate-500 dark:text-slate-400">
                    {(source.full_text.length / 1000).toFixed(1)}K characters total
                  </span>
                  <Button size="sm" variant="outline" onClick={() => setIsMarkdownView(false)} className="font-semibold px-6 shadow-sm">
                    Close View
                  </Button>
                </div>
              </div>
            )}
          </TabsContent>

          <TabsContent value="insights" className="mt-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center justify-between">
                  <span className="flex items-center gap-2">
                    <Lightbulb className="h-5 w-5" />
                    {t.common.insights}
                  </span>
                  <Badge variant="secondary">{insights.length}</Badge>
                </CardTitle>
                <CardDescription>
                  {t.sources.insightsDesc}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Create New Insight */}
                <div className="rounded-lg border bg-muted/30 p-4">
                  <Label
                    htmlFor="transformation-select"
                    className="mb-3 text-sm font-semibold flex items-center gap-2"
                  >
                    <Sparkles className="h-4 w-4" />
                    {t.sources.generateNewInsight}
                  </Label>
                  <div className="flex gap-2">
                    <Select
                      name="transformation"
                      value={selectedTransformation}
                      onValueChange={setSelectedTransformation}
                      disabled={creatingInsight}
                    >
                      <SelectTrigger id="transformation-select" className="flex-1">
                        <SelectValue placeholder={t.sources.selectTransformation} />
                      </SelectTrigger>
                      <SelectContent>
                        {transformations.map((trans) => (
                          <SelectItem key={trans.id} value={trans.id}>
                            {trans.title || trans.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <Button
                      size="sm"
                      onClick={createInsight}
                      disabled={!selectedTransformation || creatingInsight}
                    >
                      {creatingInsight ? (
                        <>
                          <LoadingSpinner className="mr-2 h-3 w-3" />
                          {t.common.creating}
                        </>
                      ) : (
                        <>
                          <Plus className="mr-2 h-4 w-4" />
                          {t.common.create}
                        </>
                      )}
                    </Button>
                  </div>
                </div>

                {/* Insights List */}
                {loadingInsights ? (
                  <div className="flex items-center justify-center py-8">
                    <LoadingSpinner />
                  </div>
                ) : insights.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">
                    <Lightbulb className="h-12 w-12 mx-auto mb-3 opacity-50" />
                    <p className="text-sm">{t.sources.noInsightsYet}</p>
                    <p className="text-xs mt-1">{t.sources.createFirstInsight}</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {insights.map((insight) => (
                      <div key={insight.id} className="rounded-lg border bg-background p-4">
                        <div className="flex items-start justify-between">
                          <div className="flex items-center gap-2">
                            <Badge variant="outline" className="text-xs uppercase">
                              {insight.insight_type}
                            </Badge>
                          </div>
                        </div>
                        <p className="mt-2 text-sm text-muted-foreground">
                          {insight.content.slice(0, 180)}{insight.content.length > 180 ? '…' : ''}
                        </p>
                        <div className="mt-3 flex justify-end gap-2">
                          <Button size="sm" variant="outline" onClick={() => setSelectedInsight(insight)}>
                            {t.sources.viewInsight}
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => setInsightToDelete(insight.id)}
                            className="text-destructive hover:text-destructive"
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="details" className="mt-6">
            <Card>
              <CardHeader>
                <CardTitle>{t.sources.details}</CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Embedding Alert */}
                {!source.embedded && (
                  <Alert>
                    <AlertCircle className="h-4 w-4" />
                    <AlertTitle>
                      {t.sources.notEmbeddedAlert}
                    </AlertTitle>
                    <AlertDescription>
                      {t.sources.notEmbeddedDesc}
                      <div className="mt-3">
                        <Button
                          onClick={handleEmbedContent}
                          disabled={isEmbedding}
                          size="sm"
                        >
                          <Database className="mr-2 h-4 w-4" />
                          {isEmbedding ? t.sources.embedding : t.sources.embedContent}
                        </Button>
                      </div>
                    </AlertDescription>
                  </Alert>
                )}

                {/* Source Information */}
                <div className="space-y-4">
                  {source.asset?.url && (
                    <div>
                      <h3 className="mb-2 text-sm font-semibold">{t.common.url}</h3>
                      <div className="flex items-center gap-2">
                        <code className="flex-1 rounded bg-muted px-2 py-1 text-sm">
                          {source.asset.url}
                        </code>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={handleCopyUrl}
                        >
                          {copied ? (
                            <CheckCircle className="h-4 w-4" />
                          ) : (
                            <Copy className="h-4 w-4" />
                          )}
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={handleOpenExternal}
                        >
                          <ExternalLink className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  )}

                  {source.asset?.file_path && (
                    <div className="space-y-2">
                      <h3 className="text-sm font-semibold">{t.sources.uploadedFile}</h3>
                      <div className="flex flex-wrap items-center gap-2">
                        <code className="rounded bg-muted px-2 py-1 text-sm">
                          {source.asset.file_path}
                        </code>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={handleDownloadFile}
                          disabled={isDownloadingFile || fileAvailable === false}
                        >
                          <Download className="mr-2 h-4 w-4" />
                          {fileAvailable === false
                            ? t.sources.fileUnavailable
                            : isDownloadingFile
                              ? t.sources.preparing
                              : t.common.download}
                        </Button>
                      </div>
                      {fileAvailable === false ? (
                        <p className="text-xs text-muted-foreground">
                          {t.sources.fileUnavailableDesc}
                        </p>
                      ) : null}
                    </div>
                  )}

                  {source.topics && source.topics.length > 0 && (
                    <div>
                      <h3 className="mb-2 text-sm font-semibold">{t.sources.topics}</h3>
                      <div className="flex flex-wrap gap-2">
                        {source.topics.map((topic, idx) => (
                          <Badge key={idx} variant="outline">
                            {topic}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* Metadata */}
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="text-sm font-semibold">{t.sources.metadata}</h3>
                    <div className="flex items-center gap-2">
                      <Database className="h-3.5 w-3.5 text-muted-foreground" />
                      <Badge variant={source.embedded ? "default" : "secondary"} className="text-xs">
                        {source.embedded ? t.sources.embedded : t.sources.notEmbedded}
                      </Badge>
                    </div>
                  </div>
                  <div className="grid gap-4 sm:grid-cols-2">
                    <div>
                      <p className="text-xs font-medium text-muted-foreground">{t.common.created_label}</p>
                      <p className="text-sm">
                        {formatDistanceToNow(new Date(source.created), {
                          addSuffix: true,
                          locale: getDateLocale(language)
                        })}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {new Date(source.created).toLocaleString()}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs font-medium text-muted-foreground">{t.common.updated_label}</p>
                      <p className="text-sm">
                        {formatDistanceToNow(new Date(source.updated), {
                          addSuffix: true,
                          locale: getDateLocale(language)
                        })}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {new Date(source.updated).toLocaleString()}
                      </p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Notebook Associations */}
            <NotebookAssociations
              sourceId={sourceId}
              currentNotebookIds={source.notebooks || []}
              onSave={fetchSource}
            />
          </TabsContent>
        </Tabs>
      </div>

      <SourceInsightDialog
        open={Boolean(selectedInsight)}
        onOpenChange={(open) => {
          if (!open) {
            setSelectedInsight(null)
          }
        }}
        insight={selectedInsight ?? undefined}
        onDelete={async (insightId) => {
          try {
            await insightsApi.delete(insightId)
            toast.success(t.common.success)
            setSelectedInsight(null)
            await fetchInsights()
          } catch (err) {
            console.error('Failed to delete insight:', err)
            toast.error(t.common.error)
          }
        }}
      />

      <AlertDialog open={!!insightToDelete} onOpenChange={() => setInsightToDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t.sources.deleteInsight}</AlertDialogTitle>
            <AlertDialogDescription>
              {t.sources.deleteInsightConfirm}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deletingInsight}>{t.common.cancel}</AlertDialogCancel>
            <AlertDialogAction asChild>
              <Button
                onClick={handleDeleteInsight}
                disabled={deletingInsight}
                variant="destructive"
              >
                {deletingInsight ? t.common.deleting : t.common.delete}
              </Button>
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}