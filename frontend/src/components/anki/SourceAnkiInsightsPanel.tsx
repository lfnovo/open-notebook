'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Checkbox } from '@/components/ui/checkbox'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Sparkles, Plus, Loader2, ChevronDown, ChevronRight } from 'lucide-react'
import { toast } from 'sonner'
import ankiApi from '@/lib/api/anki'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'

interface SourceAnkiInsightsPanelProps {
  sourceId: string
  deckId?: string
  onCardsCreated?: () => void
}

export function SourceAnkiInsightsPanel({ sourceId, deckId, onCardsCreated }: SourceAnkiInsightsPanelProps) {
  const [selectedCards, setSelectedCards] = useState<Record<string, number[]>>({})
  const [isCreating, setIsCreating] = useState(false)
  const [expandedInsights, setExpandedInsights] = useState<Record<string, boolean>>({})

  const { data: insights, isLoading } = useQuery({
    queryKey: ['anki-insights', 'source', sourceId],
    queryFn: () => ankiApi.getSourceAnkiInsights(sourceId),
    refetchOnWindowFocus: false,
  })

  const toggleCardSelection = (insightId: string, cardIndex: number) => {
    setSelectedCards(prev => {
      const current = prev[insightId] || []
      const newSelection = current.includes(cardIndex)
        ? current.filter(i => i !== cardIndex)
        : [...current, cardIndex]
      
      return {
        ...prev,
        [insightId]: newSelection
      }
    })
  }

  const selectAllInInsight = (insightId: string, cardCount: number) => {
    setSelectedCards(prev => ({
      ...prev,
      [insightId]: Array.from({ length: cardCount }, (_, i) => i)
    }))
  }

  const toggleInsightExpanded = (insightId: string) => {
    setExpandedInsights(prev => ({
      ...prev,
      [insightId]: !prev[insightId]
    }))
  }

  const handleCreateCards = async (insightId: string) => {
    if (!deckId) {
      toast.error('Please select a deck first')
      return
    }

    const cardIndices = selectedCards[insightId]
    if (!cardIndices || cardIndices.length === 0) {
      toast.error('Please select at least one card')
      return
    }

    setIsCreating(true)
    try {
      const result = await ankiApi.createCardsFromInsight(deckId, insightId, cardIndices)
      toast.success(`Created ${result.cards_created} card${result.cards_created > 1 ? 's' : ''}`)
      
      setSelectedCards(prev => {
        const newSelection = { ...prev }
        delete newSelection[insightId]
        return newSelection
      })
      
      onCardsCreated?.()
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Failed to create cards')
    } finally {
      setIsCreating(false)
    }
  }

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5" />
            AI-Generated Card Suggestions
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin" />
          </div>
        </CardContent>
      </Card>
    )
  }

  if (!insights || insights.total_cards === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5" />
            AI-Generated Card Suggestions
          </CardTitle>
          <CardDescription>
            No card suggestions found. Apply Anki transformations to this source to generate cards.
          </CardDescription>
        </CardHeader>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Sparkles className="h-5 w-5" />
          AI-Generated Card Suggestions
        </CardTitle>
        <CardDescription>
          {insights.total_cards} card{insights.total_cards > 1 ? 's' : ''} suggested from transformations
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[500px] pr-4">
          <div className="space-y-4">
            {insights.insights.map(insight => {
              const insightId = insight.insight_id
              const isExpanded = expandedInsights[insightId] ?? true // Default expanded for single source
              const selectedCount = selectedCards[insightId]?.length || 0

              return (
                <Collapsible
                  key={insightId}
                  open={isExpanded}
                  onOpenChange={() => toggleInsightExpanded(insightId)}
                >
                  <div className="border rounded-lg p-4 space-y-3">
                    <div className="flex items-center justify-between">
                      <CollapsibleTrigger className="flex items-center gap-2 text-sm font-medium hover:underline">
                        {isExpanded ? (
                          <ChevronDown className="h-4 w-4" />
                        ) : (
                          <ChevronRight className="h-4 w-4" />
                        )}
                        {insight.insight_type}
                        <Badge variant="secondary">{insight.card_count} cards</Badge>
                      </CollapsibleTrigger>
                      
                      <div className="flex items-center gap-2">
                        {selectedCount > 0 && (
                          <span className="text-sm text-muted-foreground">
                            {selectedCount} selected
                          </span>
                        )}
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => selectAllInInsight(insightId, insight.card_count)}
                        >
                          Select All
                        </Button>
                        <Button
                          size="sm"
                          onClick={() => handleCreateCards(insightId)}
                          disabled={isCreating || selectedCount === 0 || !deckId}
                        >
                          {isCreating ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            <>
                              <Plus className="mr-2 h-4 w-4" />
                              Add Selected
                            </>
                          )}
                        </Button>
                      </div>
                    </div>

                    <CollapsibleContent className="space-y-2 pt-2">
                      {insight.cards.map((card, index) => (
                        <div
                          key={index}
                          className="flex items-start gap-3 p-3 bg-muted/50 rounded-md"
                        >
                          <Checkbox
                            checked={selectedCards[insightId]?.includes(index) || false}
                            onCheckedChange={() => toggleCardSelection(insightId, index)}
                            className="mt-1"
                          />
                          <div className="flex-1 space-y-2">
                            <div>
                              <div className="text-xs font-medium text-muted-foreground">Front</div>
                              <div className="text-sm">{card.front}</div>
                            </div>
                            <div>
                              <div className="text-xs font-medium text-muted-foreground">Back</div>
                              <div className="text-sm">{card.back}</div>
                            </div>
                            {card.notes && (
                              <div>
                                <div className="text-xs font-medium text-muted-foreground">Notes</div>
                                <div className="text-xs text-muted-foreground">{card.notes}</div>
                              </div>
                            )}
                            {card.suggested_tags && card.suggested_tags.length > 0 && (
                              <div className="flex gap-1 flex-wrap">
                                {card.suggested_tags.map(tag => (
                                  <Badge key={tag} variant="outline" className="text-xs">
                                    {tag}
                                  </Badge>
                                ))}
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </CollapsibleContent>
                  </div>
                </Collapsible>
              )
            })}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  )
}
