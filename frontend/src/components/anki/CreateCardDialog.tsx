'use client'

import React, { useState, useEffect } from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { useCreateCard, useUpdateCard } from '@/lib/hooks/use-anki'
import type { AnkiCard } from '@/lib/api/anki'

interface CreateCardDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  deckId: string
  card?: AnkiCard // Optional: if provided, we're editing
}

export function CreateCardDialog({ open, onOpenChange, deckId, card }: CreateCardDialogProps) {
  const [front, setFront] = useState('')
  const [back, setBack] = useState('')
  const [notes, setNotes] = useState('')
  const [tags, setTags] = useState('')

  const createCard = useCreateCard()
  const updateCard = useUpdateCard()

  const isEditing = !!card

  // Populate form when editing
  useEffect(() => {
    if (card) {
      setFront(card.front)
      setBack(card.back)
      setNotes(card.notes || '')
      setTags(card.tags.join(', '))
    } else {
      // Reset form when creating new
      setFront('')
      setBack('')
      setNotes('')
      setTags('')
    }
  }, [card, open])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    const tagArray = tags
      .split(',')
      .map((t) => t.trim())
      .filter((t) => t.length > 0)

    if (isEditing && card) {
      // Update existing card
      await updateCard.mutateAsync({
        cardId: card.id,
        data: {
          front,
          back,
          notes: notes || undefined,
          tags: tagArray,
        },
      })
    } else {
      // Create new card
      await createCard.mutateAsync({
        front,
        back,
        notes: notes || undefined,
        deck_id: deckId,
        tags: tagArray,
      })
    }

    // Reset form and close
    setFront('')
    setBack('')
    setNotes('')
    setTags('')
    onOpenChange(false)
  }

  const isPending = isEditing ? updateCard.isPending : createCard.isPending

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>{isEditing ? 'Edit Flashcard' : 'Create New Flashcard'}</DialogTitle>
          <DialogDescription>
            {isEditing
              ? 'Update the flashcard content and metadata.'
              : 'Add a new flashcard to your deck. You can add images and audio later.'}
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit}>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="front">Front (Question) *</Label>
              <Input
                id="front"
                value={front}
                onChange={(e) => setFront(e.target.value)}
                placeholder="e.g., werken"
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="back">Back (Answer) *</Label>
              <Input
                id="back"
                value={back}
                onChange={(e) => setBack(e.target.value)}
                placeholder="e.g., to work"
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="notes">Notes</Label>
              <Textarea
                id="notes"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Additional notes, context, or examples..."
                rows={3}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="tags">Tags</Label>
              <Input
                id="tags"
                value={tags}
                onChange={(e) => setTags(e.target.value)}
                placeholder="verb, work, B1 (comma-separated)"
              />
            </div>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={!front.trim() || !back.trim() || isPending}>
              {isPending ? (isEditing ? 'Updating...' : 'Creating...') : isEditing ? 'Update Card' : 'Create Card'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
