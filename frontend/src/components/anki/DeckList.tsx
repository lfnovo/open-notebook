'use client'

import React from 'react'
import { useDecks } from '@/lib/hooks/use-anki'
import { DeckCard } from './DeckCard'
import { Loader2 } from 'lucide-react'
import type { AnkiDeck } from '@/lib/api/anki'

interface DeckListProps {
  onDeckClick?: (deckId: string) => void
  onEditDeck?: (deck: AnkiDeck) => void
  onDeleteDeck?: (deckId: string) => void
  onAddCard?: (deckId: string) => void
}

export function DeckList({ onDeckClick, onEditDeck, onDeleteDeck, onAddCard }: DeckListProps) {
  const { data: decks, isLoading, error } = useDecks()

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-12">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4">
        <p className="text-sm text-red-800">Failed to load decks. Please try again.</p>
      </div>
    )
  }

  if (!decks || decks.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-gray-300 p-12 text-center">
        <p className="text-muted-foreground">No decks yet. Create your first deck to get started!</p>
      </div>
    )
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {decks.map((deck) => (
        <DeckCard
          key={deck.id}
          deck={deck}
          onClick={onDeckClick}
          onEdit={onEditDeck}
          onDelete={onDeleteDeck}
          onAddCard={onAddCard}
        />
      ))}
    </div>
  )
}
