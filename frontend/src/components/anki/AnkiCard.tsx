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
import { MoreVertical, Edit, Trash2, Volume2, Image as ImageIcon } from 'lucide-react'
import type { AnkiCard as AnkiCardType } from '@/lib/api/anki'

interface AnkiCardProps {
  card: AnkiCardType
  onEdit?: (card: AnkiCardType) => void
  onDelete?: (cardId: string) => void
  onPlayAudio?: (card: AnkiCardType) => void
  className?: string
}

const CEFR_COLORS = {
  A1: 'bg-green-100 text-green-800',
  A2: 'bg-green-200 text-green-900',
  B1: 'bg-blue-100 text-blue-800',
  B2: 'bg-blue-200 text-blue-900',
  C1: 'bg-purple-100 text-purple-800',
  C2: 'bg-purple-200 text-purple-900',
} as const

export function AnkiCard({ card, onEdit, onDelete, onPlayAudio, className }: AnkiCardProps) {
  const handleEdit = () => {
    if (onEdit) onEdit(card)
  }

  const handleDelete = () => {
    if (onDelete) onDelete(card.id)
  }

  const handlePlayAudio = () => {
    if (onPlayAudio) onPlayAudio(card)
  }

  const cefrColor = card.cefr_level
    ? CEFR_COLORS[card.cefr_level as keyof typeof CEFR_COLORS] || 'bg-gray-100 text-gray-800'
    : 'bg-gray-100 text-gray-800'

  return (
    <Card className={className}>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <CardTitle className="text-lg font-semibold">{card.front}</CardTitle>
          </div>
          <div className="flex items-center gap-2">
            {card.cefr_level && (
              <Badge variant="outline" className={cefrColor}>
                {card.cefr_level}
              </Badge>
            )}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="sm">
                  <MoreVertical className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={handleEdit}>
                  <Edit className="mr-2 h-4 w-4" />
                  Edit
                </DropdownMenuItem>
                {card.audio_metadata?.reference_mp3 && (
                  <DropdownMenuItem onClick={handlePlayAudio}>
                    <Volume2 className="mr-2 h-4 w-4" />
                    Play Audio
                  </DropdownMenuItem>
                )}
                <DropdownMenuItem onClick={handleDelete} className="text-red-600">
                  <Trash2 className="mr-2 h-4 w-4" />
                  Delete
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          <div>
            <p className="text-sm font-medium text-muted-foreground">Translation:</p>
            <p className="text-base">{card.back}</p>
          </div>

          {card.notes && (
            <div>
              <p className="text-sm font-medium text-muted-foreground">Notes:</p>
              <p className="text-sm">{card.notes}</p>
            </div>
          )}

          {card.image_metadata && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <ImageIcon className="h-4 w-4" />
              <span>Image attached</span>
            </div>
          )}

          {card.audio_metadata && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Volume2 className="h-4 w-4" />
              <span>Audio available</span>
            </div>
          )}

          {card.tags.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {card.tags.map((tag) => (
                <Badge key={tag} variant="secondary" className="text-xs">
                  {tag}
                </Badge>
              ))}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
