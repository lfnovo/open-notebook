'use client'

import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { MoreVertical, Edit, Trash2, Plus, BookOpen } from 'lucide-react'
import type { AnkiDeck } from '@/lib/api/anki'
import { useDeckCards } from '@/lib/hooks/use-anki'

interface DeckCardProps {
  deck: AnkiDeck
  onEdit?: (deck: AnkiDeck) => void
  onDelete?: (deckId: string) => void
  onAddCard?: (deckId: string) => void
  onClick?: (deckId: string) => void
  className?: string
}

export function DeckCard({ deck, onEdit, onDelete, onAddCard, onClick, className }: DeckCardProps) {
  const { data: cards } = useDeckCards(deck.id, { limit: 1000 })
  const cardCount = cards?.length || 0

  const handleEdit = (e: React.MouseEvent) => {
    e.stopPropagation()
    if (onEdit) onEdit(deck)
  }

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation()
    if (onDelete) onDelete(deck.id)
  }

  const handleAddCard = (e: React.MouseEvent) => {
    e.stopPropagation()
    if (onAddCard) onAddCard(deck.id)
  }

  const handleClick = () => {
    if (onClick) onClick(deck.id)
  }

  return (
    <Card className={`cursor-pointer transition-shadow hover:shadow-md ${className}`} onClick={handleClick}>
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <BookOpen className="h-5 w-5 text-muted-foreground" />
              <CardTitle className="text-lg">{deck.name}</CardTitle>
            </div>
            {deck.description && (
              <p className="mt-1 text-sm text-muted-foreground">{deck.description}</p>
            )}
          </div>
          <DropdownMenu>
            <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
              <Button variant="ghost" size="sm">
                <MoreVertical className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={handleAddCard}>
                <Plus className="mr-2 h-4 w-4" />
                Add Card
              </DropdownMenuItem>
              <DropdownMenuItem onClick={handleEdit}>
                <Edit className="mr-2 h-4 w-4" />
                Edit Deck
              </DropdownMenuItem>
              <DropdownMenuItem onClick={handleDelete} className="text-red-600">
                <Trash2 className="mr-2 h-4 w-4" />
                Delete Deck
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </CardHeader>
      <CardContent>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-2xl font-bold">{cardCount}</p>
            <p className="text-sm text-muted-foreground">
              {cardCount === 1 ? 'card' : 'cards'}
            </p>
          </div>
          {deck.tags.length > 0 && (
            <div className="flex flex-wrap gap-1 justify-end">
              {deck.tags.slice(0, 3).map((tag) => (
                <Badge key={tag} variant="secondary" className="text-xs">
                  {tag}
                </Badge>
              ))}
              {deck.tags.length > 3 && (
                <Badge variant="secondary" className="text-xs">
                  +{deck.tags.length - 3}
                </Badge>
              )}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
