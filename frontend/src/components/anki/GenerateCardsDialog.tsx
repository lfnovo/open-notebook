'use client'

import { useState } from 'react'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Loader2, Plus, X } from 'lucide-react'
import { useSources } from '@/lib/hooks/use-sources'
import { useNotebooks } from '@/lib/hooks/use-notebooks'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Checkbox } from '@/components/ui/checkbox'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Badge } from '@/components/ui/badge'
import { toast } from 'sonner'
import ankiApi from '@/lib/api/anki'
import { useCreateCard } from '@/lib/hooks/use-anki'

interface GenerateCardsDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  deckId: string
}

export function GenerateCardsDialog({ open, onOpenChange, deckId }: GenerateCardsDialogProps) {
  const [selectedNotebook, setSelectedNotebook] = useState<string>('')
  const [selectedSources, setSelectedSources] = useState<string[]>([])
  const [selectedModel, setSelectedModel] = useState('qwen2.5:3b')
  const [userPrompt, setUserPrompt] = useState('')
  const [numCards, setNumCards] = useState(1)
  const [isGenerating, setIsGenerating] = useState(false)
  const [generatedCards, setGeneratedCards] = useState<any[]>([])
  const [isAddingCards, setIsAddingCards] = useState(false)

  const { data: notebooks } = useNotebooks()
  const { data: sources } = useSources(selectedNotebook)
  const createCard = useCreateCard()

  const handleToggleSource = (sourceId: string) => {
    setSelectedSources(prev =>
      prev.includes(sourceId)
        ? prev.filter(id => id !== sourceId)
        : [...prev, sourceId]
    )
  }

  const handleGenerate = async () => {
    if (selectedSources.length === 0) {
      toast.error('Please select at least one source')
      return
    }
    if (!userPrompt.trim()) {
      toast.error('Please provide instructions for card generation')
      return
    }

    setIsGenerating(true)
    try {
      const result = await ankiApi.generateCards(deckId, {
        source_ids: selectedSources,
        user_prompt: userPrompt,
        model_id: selectedModel,
        num_cards: numCards
      })

      setGeneratedCards(result.cards)
      toast.success(`Generated ${result.cards.length} card${result.cards.length > 1 ? 's' : ''}`)
    } catch (error: any) {
      console.error('Error generating cards:', error)
      toast.error(error?.response?.data?.detail || 'Failed to generate cards')
    } finally {
      setIsGenerating(false)
    }
  }

  const handleAddCard = async (card: any, index: number) => {
    setIsAddingCards(true)
    try {
      await createCard.mutateAsync({
        front: card.front,
        back: card.back,
        notes: card.notes,
        tags: card.suggested_tags || [],
        deck_id: deckId
      })

      // Remove card from generated list
      setGeneratedCards(prev => prev.filter((_, i) => i !== index))
      toast.success('Card added to deck')
    } catch (error) {
      toast.error('Failed to add card')
    } finally {
      setIsAddingCards(false)
    }
  }

  const handleAddAllCards = async () => {
    setIsAddingCards(true)
    try {
      for (const card of generatedCards) {
        await createCard.mutateAsync({
          front: card.front,
          back: card.back,
          notes: card.notes,
          tags: card.suggested_tags || [],
          deck_id: deckId
        })
      }
      toast.success(`Added ${generatedCards.length} cards to deck`)
      setGeneratedCards([])
      onOpenChange(false)
    } catch (error) {
      toast.error('Failed to add all cards')
    } finally {
      setIsAddingCards(false)
    }
  }

  const handleClose = () => {
    setSelectedNotebook('')
    setSelectedSources([])
    setUserPrompt('')
    setNumCards(1)
    setGeneratedCards([])
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Generate Cards from Sources</DialogTitle>
          <DialogDescription>
            Select sources and provide instructions to generate flashcards with AI
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          {/* Notebook Selection */}
          <div className="space-y-2">
            <Label>Notebook</Label>
            <Select value={selectedNotebook} onValueChange={setSelectedNotebook}>
              <SelectTrigger>
                <SelectValue placeholder="Select a notebook" />
              </SelectTrigger>
              <SelectContent>
                {notebooks?.map(notebook => (
                  <SelectItem key={notebook.id} value={notebook.id}>
                    {notebook.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Source Selection */}
          {selectedNotebook && sources && sources.length > 0 && (
            <div className="space-y-2">
              <Label>Sources ({selectedSources.length} selected)</Label>
              <ScrollArea className="h-40 border rounded-md p-4">
                <div className="space-y-2">
                  {sources.map(source => (
                    <div key={source.id} className="flex items-center space-x-2">
                      <Checkbox
                        id={source.id}
                        checked={selectedSources.includes(source.id)}
                        onCheckedChange={() => handleToggleSource(source.id)}
                      />
                      <label htmlFor={source.id} className="text-sm cursor-pointer flex-1">
                        {source.title}
                      </label>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            </div>
          )}

          {/* Model Selection */}
          <div className="space-y-2">
            <Label>AI Model</Label>
            <Select value={selectedModel} onValueChange={setSelectedModel}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="qwen2.5:3b">qwen2.5:3b (Fast, 1.9GB)</SelectItem>
                <SelectItem value="qwen2.5:7b">qwen2.5:7b (Better quality, 4.7GB - may fail on low memory)</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* User Prompt */}
          <div className="space-y-2">
            <Label>Instructions</Label>
            <Textarea
              placeholder="E.g., Generate vocabulary cards for advanced Dutch learners, focusing on formal language..."
              value={userPrompt}
              onChange={(e) => setUserPrompt(e.target.value)}
              rows={4}
            />
          </div>

          {/* Number of Cards */}
          <div className="space-y-2">
            <Label>Number of Cards</Label>
            <Input
              type="number"
              min={1}
              max={10}
              value={numCards}
              onChange={(e) => setNumCards(parseInt(e.target.value) || 1)}
            />
          </div>

          {/* Generate Button */}
          <Button 
            onClick={handleGenerate} 
            disabled={isGenerating || selectedSources.length === 0 || !userPrompt.trim()}
            className="w-full"
          >
            {isGenerating ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Generating...
              </>
            ) : (
              'Generate Cards'
            )}
          </Button>

          {/* Generated Cards Preview */}
          {generatedCards.length > 0 && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="font-semibold">Generated Cards</h3>
                <Button onClick={handleAddAllCards} disabled={isAddingCards} size="sm">
                  <Plus className="mr-2 h-4 w-4" />
                  Add All
                </Button>
              </div>
              
              <div className="space-y-4">
                {generatedCards.map((card, index) => (
                  <div key={index} className="border rounded-lg p-4 space-y-3">
                    <div>
                      <Label className="text-xs text-muted-foreground">Front</Label>
                      <p className="mt-1">{card.front}</p>
                    </div>
                    <div>
                      <Label className="text-xs text-muted-foreground">Back</Label>
                      <p className="mt-1">{card.back}</p>
                    </div>
                    {card.notes && (
                      <div>
                        <Label className="text-xs text-muted-foreground">Notes</Label>
                        <p className="mt-1 text-sm text-muted-foreground">{card.notes}</p>
                      </div>
                    )}
                    {card.suggested_tags && card.suggested_tags.length > 0 && (
                      <div className="flex gap-2">
                        {card.suggested_tags.map((tag: string) => (
                          <Badge key={tag} variant="secondary">{tag}</Badge>
                        ))}
                      </div>
                    )}
                    <div className="flex gap-2">
                      <Button 
                        size="sm" 
                        onClick={() => handleAddCard(card, index)}
                        disabled={isAddingCards}
                      >
                        <Plus className="mr-2 h-3 w-3" />
                        Add to Deck
                      </Button>
                      <Button 
                        size="sm" 
                        variant="ghost"
                        onClick={() => setGeneratedCards(prev => prev.filter((_, i) => i !== index))}
                      >
                        <X className="mr-2 h-3 w-3" />
                        Dismiss
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
