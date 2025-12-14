'use client'

import React, { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Plus } from 'lucide-react'
import { AppShell } from '@/components/layout/AppShell'
import { DeckList, CreateDeckDialog, CreateCardDialog } from '@/components/anki'
import type { AnkiDeck } from '@/lib/api/anki'
import { useDeleteDeck } from '@/lib/hooks/use-anki'
import { useRouter } from 'next/navigation'

export default function AnkiPage() {
  const router = useRouter()
  const [createDeckOpen, setCreateDeckOpen] = useState(false)
  const [createCardDeckId, setCreateCardDeckId] = useState<string | null>(null)
  
  const deleteDeck = useDeleteDeck()

  const handleDeckClick = (deckId: string) => {
    router.push(`/anki/${encodeURIComponent(deckId)}`)
  }

  const handleEditDeck = (deck: AnkiDeck) => {
    // TODO: Implement deck editing
    console.log('Edit deck:', deck)
  }

  const handleDeleteDeck = async (deckId: string) => {
    if (confirm('Are you sure you want to delete this deck? This will not delete the cards.')) {
      await deleteDeck.mutateAsync({ deckId, deleteCards: false })
    }
  }

  const handleAddCard = (deckId: string) => {
    setCreateCardDeckId(deckId)
  }

  return (
    <AppShell>
      <div className="container mx-auto py-8 px-4">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold">Anki Flashcards 🎯</h1>
            <p className="text-muted-foreground mt-1">
              Create and manage your language learning flashcards
            </p>
          </div>
          <Button onClick={() => setCreateDeckOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            New Deck
          </Button>
        </div>

        <DeckList
          onDeckClick={handleDeckClick}
          onEditDeck={handleEditDeck}
          onDeleteDeck={handleDeleteDeck}
          onAddCard={handleAddCard}
        />

        <CreateDeckDialog open={createDeckOpen} onOpenChange={setCreateDeckOpen} />
        
        {createCardDeckId && (
          <CreateCardDialog
            open={!!createCardDeckId}
            onOpenChange={(open) => !open && setCreateCardDeckId(null)}
            deckId={createCardDeckId}
          />
        )}
      </div>
    </AppShell>
  )
}
