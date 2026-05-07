'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useSearchParams } from 'next/navigation'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeRaw from 'rehype-raw'
import { useTranslation } from '@/lib/hooks/use-translation'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Button } from '@/components/ui/button'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Label } from '@/components/ui/label'
import { Checkbox } from '@/components/ui/checkbox'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { Search, ChevronDown, AlertCircle, Settings, Save, MessageCircleQuestion } from 'lucide-react'
import { useSearch } from '@/lib/hooks/use-search'
import { useAsk } from '@/lib/hooks/use-ask'
import { useModelDefaults, useModels } from '@/lib/hooks/use-models'
import { useModalManager } from '@/lib/hooks/use-modal-manager'
import { useAuthStore } from '@/lib/stores/auth-store'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { StreamingResponse } from '@/components/search/StreamingResponse'
import { AdvancedModelsDialog } from '@/components/search/AdvancedModelsDialog'
import { SaveToNotebooksDialog } from '@/components/search/SaveToNotebooksDialog'

type ModalResourceType = 'source' | 'note' | 'insight'

function stringFromRecordIdPart(value: unknown): string | null {
  if (typeof value === 'string' || typeof value === 'number') {
    return String(value)
  }
  if (value && typeof value === 'object' && 'id' in value) {
    return stringFromRecordIdPart((value as { id?: unknown }).id)
  }
  return null
}

function parseSearchParentRef(parentId: unknown): { type: ModalResourceType; id: string } | null {
  let rawId: string | null = null

  if (Array.isArray(parentId)) {
    for (const item of parentId) {
      const parsedItem = parseSearchParentRef(item)
      if (parsedItem) {
        return parsedItem
      }
    }
  } else if (typeof parentId === 'string') {
    rawId = parentId
  } else if (parentId && typeof parentId === 'object') {
    const record = parentId as { tb?: unknown; table?: unknown; id?: unknown }
    const table = typeof record.tb === 'string'
      ? record.tb
      : typeof record.table === 'string'
        ? record.table
        : null
    const idPart = stringFromRecordIdPart(record.id)

    if (table && idPart) {
      rawId = idPart.startsWith(`${table}:`) ? idPart : `${table}:${idPart}`
    } else {
      rawId = idPart
    }
  }

  if (!rawId) {
    return null
  }

  const separatorIndex = rawId.indexOf(':')
  if (separatorIndex <= 0 || separatorIndex === rawId.length - 1) {
    return null
  }

  const rawType = rawId.slice(0, separatorIndex)
  const id = rawId.slice(separatorIndex + 1)
  const type = rawType === 'source_insight' ? 'insight' : rawType

  if (type !== 'source' && type !== 'note' && type !== 'insight') {
    return null
  }

  return { type, id }
}

function SearchMatchMarkdown({ content }: { content: string }) {
  return (
    <div className="prose prose-sm prose-neutral dark:prose-invert max-w-none break-words prose-headings:mt-0 prose-headings:mb-2 prose-headings:text-sm prose-headings:font-semibold prose-p:my-1 prose-p:leading-6 prose-ul:my-2 prose-ol:my-2 prose-li:my-1 prose-code:rounded prose-code:bg-muted prose-code:px-1 prose-code:py-0.5 prose-pre:overflow-x-auto prose-a:break-all">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeRaw]}
        components={{
          img: () => null,
          table: ({ children }) => (
            <div className="my-2 max-w-full overflow-x-auto rounded-md border border-border">
              <table className="min-w-full border-collapse text-xs">{children}</table>
            </div>
          ),
          thead: ({ children }) => <thead className="bg-muted/80">{children}</thead>,
          tr: ({ children }) => <tr className="border-b border-border last:border-b-0">{children}</tr>,
          th: ({ children }) => <th className="border-r border-border px-2 py-1.5 text-left font-semibold last:border-r-0">{children}</th>,
          td: ({ children }) => <td className="border-r border-border px-2 py-1.5 align-top last:border-r-0">{children}</td>,
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}

export default function SearchPage() {
  const { t } = useTranslation()
  const searchCopy = t.searchPage
  // URL params
  const searchParams = useSearchParams()
  const urlQuery = searchParams?.get('q') || ''
  const rawMode = searchParams?.get('mode')
  const urlMode = rawMode === 'search' ? 'search' : 'ask'

  // Tab state (controlled)
  const [activeTab, setActiveTab] = useState<'ask' | 'search'>(
    urlMode === 'search' ? 'search' : 'ask'
  )

  // Search state
  const [searchQuery, setSearchQuery] = useState(urlMode === 'search' ? urlQuery : '')
  const [searchType, setSearchType] = useState<'text' | 'vector'>('text')
  const [searchSources, setSearchSources] = useState(true)
  const [searchNotes, setSearchNotes] = useState(true)

  // Ask state
  const [askQuestion, setAskQuestion] = useState(urlMode === 'ask' ? urlQuery : '')

  // Advanced models dialog
  const [showAdvancedModels, setShowAdvancedModels] = useState(false)
  const [customModels, setCustomModels] = useState<{
    strategy: string
    answer: string
    finalAnswer: string
  } | null>(null)

  // Save to notebooks dialog
  const [showSaveDialog, setShowSaveDialog] = useState(false)

  // Hooks
  const searchMutation = useSearch()
  const ask = useAsk()
  const { data: modelDefaults, isLoading: modelsLoading } = useModelDefaults()
  const { data: availableModels } = useModels()
  const { openModal } = useModalManager()
  const role = useAuthStore((state) => state.role)
  const canCustomizeModels = role === 'admin'

  const modelNameById = useMemo(() => {
    if (!availableModels) {
      return new Map<string, string>()
    }
    return new Map(availableModels.map((model) => [model.id, model.name]))
  }, [availableModels])

  const resolveModelName = (id?: string | null) => {
    if (!id) return searchCopy.notSet
    return modelNameById.get(id) ?? id
  }

  const hasEmbeddingModel = !!modelDefaults?.default_embedding_model
  const defaultAskModel = modelDefaults?.default_tools_model || modelDefaults?.default_chat_model || ''

  // Track if we've already auto-triggered from URL params
  const hasAutoTriggeredRef = useRef(false)
  const lastUrlParamsRef = useRef({ q: '', mode: '' })

  const handleSearch = useCallback(() => {
    if (!searchQuery.trim()) return

    searchMutation.mutate({
      query: searchQuery,
      type: searchType,
      limit: 100,
      search_sources: searchSources,
      search_notes: searchNotes,
      minimum_score: 0.2
    })
  }, [searchQuery, searchType, searchSources, searchNotes, searchMutation])

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch()
    }
  }

  const handleAsk = useCallback(() => {
    if (!askQuestion.trim() || !defaultAskModel) return

    const models = canCustomizeModels && customModels ? customModels : {
      strategy: defaultAskModel,
      answer: defaultAskModel,
      finalAnswer: defaultAskModel
    }

    ask.sendAsk(askQuestion, models)
  }, [askQuestion, defaultAskModel, canCustomizeModels, customModels, ask])

  // Auto-trigger search/ask when arriving with URL params
  useEffect(() => {
    // Skip if already triggered or no query
    if (hasAutoTriggeredRef.current || !urlQuery) return

    // Wait for models to load before triggering ask
    if (urlMode === 'ask' && modelsLoading) return

    if (urlMode === 'search') {
      handleSearch()
      hasAutoTriggeredRef.current = true
    } else if (urlMode === 'ask' && defaultAskModel) {
      handleAsk()
      hasAutoTriggeredRef.current = true
    }
  }, [urlQuery, urlMode, modelsLoading, defaultAskModel, handleSearch, handleAsk])

  // Handle URL param changes while on page (e.g., from command palette again)
  useEffect(() => {
    const currentQ = searchParams?.get('q') || ''
    const rawCurrentMode = searchParams?.get('mode')
    const currentMode = rawCurrentMode === 'search' ? 'search' : 'ask'

    // Check if URL params have changed
    if (currentQ !== lastUrlParamsRef.current.q || currentMode !== lastUrlParamsRef.current.mode) {
      lastUrlParamsRef.current = { q: currentQ, mode: currentMode }

      if (currentQ) {
        // Update state based on mode
        if (currentMode === 'search') {
          setSearchQuery(currentQ)
          setActiveTab('search')
          // Reset trigger flag so we auto-trigger with new params
          hasAutoTriggeredRef.current = false
        } else {
          setAskQuestion(currentQ)
          setActiveTab('ask')
          hasAutoTriggeredRef.current = false
        }
      }
    }
  }, [searchParams])

  return (
    <div className="flex-1 min-h-0 overflow-y-auto p-4 md:p-6">
        <h1 className="text-xl md:text-2xl font-bold mb-4 md:mb-6">{searchCopy.askAndSearch}</h1>

        <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as 'ask' | 'search')} className="w-full space-y-6">
          <div className="space-y-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{searchCopy.chooseAMode}</p>
            <TabsList aria-label={t.common.accessibility.searchKB} className="w-full max-w-xl">
              <TabsTrigger value="ask">
                <MessageCircleQuestion className="h-4 w-4" />
                {searchCopy.askBeta}
              </TabsTrigger>
              <TabsTrigger value="search">
                <Search className="h-4 w-4" />
                {searchCopy.search}
              </TabsTrigger>
            </TabsList>
          </div>

          <TabsContent value="ask" className="mt-6">
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">{searchCopy.askYourKb}</CardTitle>
                <p className="text-sm text-muted-foreground">
                  {searchCopy.askYourKbDesc}
                </p>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Question Input */}
                <div className="space-y-2">
                  <Label htmlFor="ask-question">{searchCopy.question}</Label>
                  <Textarea
                    id="ask-question"
                    name="ask-question"
                    placeholder={searchCopy.enterQuestionPlaceholder}
                    value={askQuestion}
                    onChange={(e) => setAskQuestion(e.target.value)}
                    onKeyDown={(e) => {
                      // Submit on Cmd/Ctrl+Enter
                      if ((e.metaKey || e.ctrlKey) && e.key === 'Enter' && !ask.isStreaming && askQuestion.trim()) {
                        e.preventDefault()
                        handleAsk()
                      }
                    }}
                    disabled={ask.isStreaming}
                    rows={3}
                    aria-label={t.common.accessibility.enterQuestion}
                  />
                  <p className="text-xs text-muted-foreground">{searchCopy.pressToSubmit}</p>
                </div>

                {/* Models Display */}
                {!hasEmbeddingModel ? (
                  <div className="flex items-center gap-2 p-3 text-sm text-amber-600 dark:text-amber-500 bg-amber-50 dark:bg-amber-950/20 rounded-md">
                    <AlertCircle className="h-4 w-4" />
                    <span>{searchCopy.noEmbeddingModel}</span>
                  </div>
                ) : (
                  <>
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <Label className="text-xs text-muted-foreground">
                          {canCustomizeModels && customModels ? searchCopy.usingCustomModels : searchCopy.usingDefaultModels}
                        </Label>
                        {canCustomizeModels && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setShowAdvancedModels(true)}
                            disabled={ask.isStreaming}
                            className="h-auto py-1 px-2"
                          >
                            <Settings className="h-3 w-3 mr-1" />
                            {searchCopy.advanced}
                          </Button>
                        )}
                      </div>
                      <div className="flex gap-2 text-xs flex-wrap">
                        <Badge variant="secondary">
                          {searchCopy.strategy}: {resolveModelName((canCustomizeModels ? customModels?.strategy : undefined) || defaultAskModel)}
                        </Badge>
                        <Badge variant="secondary">
                          {searchCopy.answer}: {resolveModelName((canCustomizeModels ? customModels?.answer : undefined) || defaultAskModel)}
                        </Badge>
                        <Badge variant="secondary">
                          {searchCopy.final}: {resolveModelName((canCustomizeModels ? customModels?.finalAnswer : undefined) || defaultAskModel)}
                        </Badge>
                      </div>
                    </div>

                    <div className="flex flex-col sm:flex-row gap-2">
                      <Button
                        onClick={handleAsk}
                        disabled={ask.isStreaming || !askQuestion.trim()}
                        className="w-full sm:w-auto sm:flex-1"
                      >
                        {ask.isStreaming ? (
                          <>
                            <LoadingSpinner size="sm" className="mr-2" />
                            {searchCopy.processing}
                          </>
                        ) : (
                          searchCopy.ask
                        )}
                      </Button>

                      {ask.finalAnswer && (
                        <Button
                          variant="outline"
                          onClick={() => setShowSaveDialog(true)}
                          className="w-full sm:w-auto sm:flex-1"
                        >
                          <Save className="h-4 w-4 mr-2" />
                          {searchCopy.saveToNotebooks}
                        </Button>
                      )}
                    </div>
                  </>
                )}

                {/* Streaming Response */}
                <StreamingResponse
                  isStreaming={ask.isStreaming}
                  strategy={ask.strategy}
                  answers={ask.answers}
                  finalAnswer={ask.finalAnswer}
                />

                {/* Advanced Models Dialog */}
                {canCustomizeModels && (
                  <AdvancedModelsDialog
                    open={showAdvancedModels}
                    onOpenChange={setShowAdvancedModels}
                    defaultModels={{
                      strategy: customModels?.strategy || defaultAskModel,
                      answer: customModels?.answer || defaultAskModel,
                      finalAnswer: customModels?.finalAnswer || defaultAskModel
                    }}
                    onSave={setCustomModels}
                  />
                )}

                {/* Save to Notebooks Dialog */}
                {ask.finalAnswer && (
                  <SaveToNotebooksDialog
                    open={showSaveDialog}
                    onOpenChange={setShowSaveDialog}
                    question={askQuestion}
                    answer={ask.finalAnswer}
                  />
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="search" className="mt-6">
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">{searchCopy.search}</CardTitle>
                <p className="text-sm text-muted-foreground">
                  {searchCopy.searchDesc}
                </p>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Search Input */}
                <div className="space-y-2">
                  <Label htmlFor="search-query" className="sr-only">
                    {searchCopy.search}
                  </Label>
                  <div className="flex flex-col sm:flex-row gap-2">
                    <Input
                      id="search-query"
                      name="search-query"
                      placeholder={searchCopy.enterSearchPlaceholder}
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      onKeyPress={handleKeyPress}
                      disabled={searchMutation.isPending}
                      className="flex-1"
                      aria-label={t.common.accessibility.enterSearch}
                      autoComplete="off"
                    />
                    <Button
                      onClick={handleSearch}
                      disabled={searchMutation.isPending || !searchQuery.trim()}
                      aria-label={t.common.accessibility.searchKBBtn}
                      className="w-full sm:w-auto"
                    >
                      {searchMutation.isPending ? (
                        <LoadingSpinner size="sm" />
                      ) : (
                        <Search className="h-4 w-4 mr-2" />
                      )}
                      {searchCopy.search}
                    </Button>
                  </div>
                  <p className="text-xs text-muted-foreground">{searchCopy.pressToSearch}</p>
                </div>

                {/* Search Options */}
                <div className="space-y-4">
                  {/* Search Type */}
                  <div className="space-y-2" role="group" aria-labelledby="search-type-label">
                    <span id="search-type-label" className="text-sm font-medium leading-none">{searchCopy.searchType}</span>
                    {!hasEmbeddingModel && (
                      <div className="flex items-center gap-2 text-sm text-amber-600 dark:text-amber-500">
                        <AlertCircle className="h-4 w-4" />
                        <span>{searchCopy.vectorSearchWarning}</span>
                      </div>
                    )}
                    <RadioGroup
                      name="search-type"
                      value={searchType}
                      onValueChange={(value: 'text' | 'vector') => setSearchType(value)}
                      disabled={modelsLoading || searchMutation.isPending}
                    >
                      <div className="flex items-center space-x-2">
                        <RadioGroupItem value="text" id="text" />
                        <Label htmlFor="text" className="font-normal cursor-pointer">
                          {searchCopy.textSearch}
                        </Label>
                      </div>
                      <div className="flex items-center space-x-2">
                        <RadioGroupItem
                          value="vector"
                          id="vector"
                          disabled={!hasEmbeddingModel || searchMutation.isPending}
                        />
                        <Label
                          htmlFor="vector"
                          className={`font-normal ${!hasEmbeddingModel ? 'text-muted-foreground cursor-not-allowed' : 'cursor-pointer'}`}
                        >
                          {searchCopy.vectorSearch}
                        </Label>
                      </div>
                    </RadioGroup>
                  </div>

                  {/* Search Locations */}
                  <div className="space-y-2" role="group" aria-labelledby="search-in-label">
                    <span id="search-in-label" className="text-sm font-medium leading-none">{searchCopy.searchIn}</span>
                    <div className="space-y-2">
                      <div className="flex items-center space-x-2">
                        <Checkbox
                          id="sources"
                          name="sources"
                          checked={searchSources}
                          onCheckedChange={(checked) => setSearchSources(checked as boolean)}
                          disabled={searchMutation.isPending}
                        />
                        <Label htmlFor="sources" className="font-normal cursor-pointer">
                          {searchCopy.searchSources}
                        </Label>
                      </div>
                      <div className="flex items-center space-x-2">
                        <Checkbox
                          id="notes"
                          name="notes"
                          checked={searchNotes}
                          onCheckedChange={(checked) => setSearchNotes(checked as boolean)}
                          disabled={searchMutation.isPending}
                        />
                        <Label htmlFor="notes" className="font-normal cursor-pointer">
                          {searchCopy.searchNotes}
                        </Label>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Search Results */}
                {searchMutation.data && (
                  <div className="mt-6 space-y-3">
                    <div className="flex items-center justify-between">
                      <h3 className="text-sm font-medium">
                        {searchCopy.resultsFound.replace('{count}', searchMutation.data.total_count.toString())}
                      </h3>
                      <Badge variant="outline">{searchMutation.data.search_type === 'text' ? searchCopy.textSearch : searchCopy.vectorSearch}</Badge>
                    </div>

                    {searchMutation.data.results.length === 0 ? (
                      <Card>
                        <CardContent className="pt-6 text-center text-muted-foreground">
                          {searchCopy.noResultsFor.replace('{query}', searchQuery)}
                        </CardContent>
                      </Card>
                    ) : (
                      <div className="space-y-2 max-h-[60vh] overflow-y-auto pr-2">
                        {searchMutation.data.results.map((result, index) => {
                          const parentRef = parseSearchParentRef(result.parent_id)
                          if (!parentRef) {
                            console.warn('Search result with invalid parent_id:', result)
                            return null
                          }

                          return (
                          <Card key={index}>
                            <CardContent className="pt-4">
                              <div className="flex items-start justify-between gap-4">
                                <div className="flex-1">
                                  <button
                                    onClick={() => openModal(parentRef.type, parentRef.id)}
                                    className="text-primary hover:underline font-medium"
                                  >
                                    {result.title}
                                  </button>
                                  <Badge variant="secondary" className="ml-2">
                                    {result.final_score.toFixed(2)}
                                  </Badge>
                                </div>
                              </div>

                              {result.matches && result.matches.length > 0 && (
                                <Collapsible className="mt-3">
                                  <CollapsibleTrigger className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground">
                                    <ChevronDown className="h-4 w-4" />
                                    {searchCopy.matches.replace('{count}', result.matches.length.toString())}
                                  </CollapsibleTrigger>
                                  <CollapsibleContent className="mt-2 space-y-1">
                                    {result.matches.map((match, i) => (
                                      <div key={i} className="text-sm pl-6 py-1 border-l-2 border-muted">
                                        <SearchMatchMarkdown content={match} />
                                      </div>
                                    ))}
                                  </CollapsibleContent>
                                </Collapsible>
                              )}
                            </CardContent>
                          </Card>
                        )})}
                      </div>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
  )
}
