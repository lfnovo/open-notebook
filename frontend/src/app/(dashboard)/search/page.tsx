'use client'

import { useMemo, useState } from 'react'
import { AppShell } from '@/components/layout/AppShell'
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
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { StreamingResponse } from '@/components/search/StreamingResponse'
import { AdvancedModelsDialog } from '@/components/search/AdvancedModelsDialog'
import { SaveToNotebooksDialog } from '@/components/search/SaveToNotebooksDialog'

export default function SearchPage() {
  // Search state
  const [searchQuery, setSearchQuery] = useState('')
  const [searchType, setSearchType] = useState<'text' | 'vector'>('text')
  const [searchSources, setSearchSources] = useState(true)
  const [searchNotes, setSearchNotes] = useState(true)

  // Ask state
  const [askQuestion, setAskQuestion] = useState('')

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

  const modelNameById = useMemo(() => {
    if (!availableModels) {
      return new Map<string, string>()
    }
    return new Map(availableModels.map((model) => [model.id, model.name]))
  }, [availableModels])

  const resolveModelName = (id?: string | null) => {
    if (!id) return 'Not set'
    return modelNameById.get(id) ?? id
  }

  const hasEmbeddingModel = !!modelDefaults?.default_embedding_model

  const handleSearch = () => {
    if (!searchQuery.trim()) return

    searchMutation.mutate({
      query: searchQuery,
      type: searchType,
      limit: 100,
      search_sources: searchSources,
      search_notes: searchNotes,
      minimum_score: 0.2
    })
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch()
    }
  }

  const handleAsk = () => {
    if (!askQuestion.trim() || !modelDefaults?.default_chat_model) return

    const models = customModels || {
      strategy: modelDefaults.default_chat_model,
      answer: modelDefaults.default_chat_model,
      finalAnswer: modelDefaults.default_chat_model
    }

    ask.sendAsk(askQuestion, models)
  }

  return (
    <AppShell>
      <div className="p-4 md:p-6">
        <h1 className="text-xl md:text-2xl font-bold mb-4 md:mb-6">Ask and Search</h1>

        <Tabs defaultValue="ask" className="w-full space-y-6">
          <div className="space-y-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Choose a mode</p>
            <TabsList aria-label="Ask or search your knowledge base" className="w-full max-w-xl">
              <TabsTrigger value="ask">
                <MessageCircleQuestion className="h-4 w-4" />
                Ask (beta)
              </TabsTrigger>
              <TabsTrigger value="search">
                <Search className="h-4 w-4" />
                Search
              </TabsTrigger>
            </TabsList>
          </div>

          <TabsContent value="ask" className="mt-6">
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Ask Your Knowledge Base (beta)</CardTitle>
                <p className="text-sm text-muted-foreground">
                  The LLM will answer your query based on the documents in your knowledge base.
                </p>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Question Input */}
                <div className="space-y-2">
                  <Label htmlFor="ask-question">Question</Label>
                  <Textarea
                    id="ask-question"
                    placeholder="Enter your question..."
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
                    aria-label="Enter your question to ask the knowledge base"
                  />
                  <p className="text-xs text-muted-foreground">Press Cmd/Ctrl+Enter to submit</p>
                </div>

                {/* Models Display */}
                {!hasEmbeddingModel ? (
                  <div className="flex items-center gap-2 p-3 text-sm text-amber-600 dark:text-amber-500 bg-amber-50 dark:bg-amber-950/20 rounded-md">
                    <AlertCircle className="h-4 w-4" />
                    <span>You can&apos;t use this feature because you have no embedding model selected. Please set one up in the Models page.</span>
                  </div>
                ) : (
                  <>
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <Label className="text-xs text-muted-foreground">
                          {customModels ? 'Using Custom Models' : 'Using Default Models'}
                        </Label>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setShowAdvancedModels(true)}
                          disabled={ask.isStreaming}
                          className="h-auto py-1 px-2"
                        >
                          <Settings className="h-3 w-3 mr-1" />
                          Advanced
                        </Button>
                      </div>
                      <div className="flex gap-2 text-xs flex-wrap">
                        <Badge variant="secondary">
                          Strategy: {resolveModelName(customModels?.strategy || modelDefaults?.default_chat_model)}
                        </Badge>
                        <Badge variant="secondary">
                          Answer: {resolveModelName(customModels?.answer || modelDefaults?.default_chat_model)}
                        </Badge>
                        <Badge variant="secondary">
                          Final: {resolveModelName(customModels?.finalAnswer || modelDefaults?.default_chat_model)}
                        </Badge>
                      </div>
                    </div>

                    <div className="flex flex-col sm:flex-row gap-2">
                      <Button
                        onClick={handleAsk}
                        disabled={ask.isStreaming || !askQuestion.trim()}
                        className="w-full"
                      >
                        {ask.isStreaming ? (
                          <>
                            <LoadingSpinner size="sm" className="mr-2" />
                            Processing...
                          </>
                        ) : (
                          'Ask'
                        )}
                      </Button>

                      {ask.finalAnswer && (
                        <Button
                          variant="outline"
                          onClick={() => setShowSaveDialog(true)}
                          className="w-full"
                        >
                          <Save className="h-4 w-4 mr-2" />
                          Save to Notebooks
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
                <AdvancedModelsDialog
                  open={showAdvancedModels}
                  onOpenChange={setShowAdvancedModels}
                  defaultModels={{
                    strategy: customModels?.strategy || modelDefaults?.default_chat_model || '',
                    answer: customModels?.answer || modelDefaults?.default_chat_model || '',
                    finalAnswer: customModels?.finalAnswer || modelDefaults?.default_chat_model || ''
                  }}
                  onSave={setCustomModels}
                />

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
                <CardTitle className="text-lg">Search</CardTitle>
                <p className="text-sm text-muted-foreground">
                  Search your knowledge base for specific keywords or concepts
                </p>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Search Input */}
                <div className="space-y-2">
                  <div className="flex flex-col sm:flex-row gap-2">
                    <Input
                      id="search-query"
                      placeholder="Enter search query..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      onKeyPress={handleKeyPress}
                      disabled={searchMutation.isPending}
                      className="flex-1"
                      aria-label="Enter search query"
                    />
                    <Button
                      onClick={handleSearch}
                      disabled={searchMutation.isPending || !searchQuery.trim()}
                      aria-label="Search knowledge base"
                      className="w-full sm:w-auto"
                    >
                      {searchMutation.isPending ? (
                        <LoadingSpinner size="sm" />
                      ) : (
                        <Search className="h-4 w-4 mr-2" />
                      )}
                      Search
                    </Button>
                  </div>
                  <p className="text-xs text-muted-foreground">Press Enter to search</p>
                </div>

                {/* Search Options */}
                <div className="space-y-4">
                  {/* Search Type */}
                  <div className="space-y-2">
                    <Label>Search Type</Label>
                    {!hasEmbeddingModel && (
                      <div className="flex items-center gap-2 text-sm text-amber-600 dark:text-amber-500">
                        <AlertCircle className="h-4 w-4" />
                        <span>Vector search requires an embedding model. Only text search is available.</span>
                      </div>
                    )}
                    <RadioGroup
                      value={searchType}
                      onValueChange={(value: 'text' | 'vector') => setSearchType(value)}
                      disabled={modelsLoading || searchMutation.isPending}
                    >
                      <div className="flex items-center space-x-2">
                        <RadioGroupItem value="text" id="text" />
                        <Label htmlFor="text" className="font-normal cursor-pointer">
                          Text Search
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
                          Vector Search
                        </Label>
                      </div>
                    </RadioGroup>
                  </div>

                  {/* Search Locations */}
                  <div className="space-y-2">
                    <Label>Search In</Label>
                    <div className="space-y-2">
                      <div className="flex items-center space-x-2">
                        <Checkbox
                          id="sources"
                          checked={searchSources}
                          onCheckedChange={(checked) => setSearchSources(checked as boolean)}
                          disabled={searchMutation.isPending}
                        />
                        <Label htmlFor="sources" className="font-normal cursor-pointer">
                          Search Sources
                        </Label>
                      </div>
                      <div className="flex items-center space-x-2">
                        <Checkbox
                          id="notes"
                          checked={searchNotes}
                          onCheckedChange={(checked) => setSearchNotes(checked as boolean)}
                          disabled={searchMutation.isPending}
                        />
                        <Label htmlFor="notes" className="font-normal cursor-pointer">
                          Search Notes
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
                        {searchMutation.data.total_count} result{searchMutation.data.total_count !== 1 ? 's' : ''} found
                      </h3>
                      <Badge variant="outline">{searchMutation.data.search_type} search</Badge>
                    </div>

                    {searchMutation.data.results.length === 0 ? (
                      <Card>
                        <CardContent className="pt-6 text-center text-muted-foreground">
                          No results found for &ldquo;{searchQuery}&rdquo;
                        </CardContent>
                      </Card>
                    ) : (
                      <div className="space-y-2 max-h-[60vh] overflow-y-auto pr-2">
                        {searchMutation.data.results.map((result, index) => {
                          // Parse type from parent_id (format: "source:id" or "note:id" or "source_insight:id")
                          const [type, id] = result.parent_id.split(':')
                          const modalType = type === 'source_insight' ? 'insight' : type as 'source' | 'note' | 'insight'

                          return (
                          <Card key={index}>
                            <CardContent className="pt-4">
                              <div className="flex items-start justify-between gap-4">
                                <div className="flex-1">
                                  <button
                                    onClick={() => openModal(modalType, id)}
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
                                    Matches ({result.matches.length})
                                  </CollapsibleTrigger>
                                  <CollapsibleContent className="mt-2 space-y-1">
                                    {result.matches.map((match, i) => (
                                      <div key={i} className="text-sm pl-6 py-1 border-l-2 border-muted">
                                        {match}
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
    </AppShell>
  )
}
