import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { AxiosError } from 'axios'
import { ankiApi } from '@/lib/api/anki'
import type {
  CardCreateRequest,
  CardUpdateRequest,
  DeckCreateRequest,
  CEFRClassifyRequest,
  ImageSearchRequest,
  ExportSessionCreateRequest,
} from '@/lib/api/anki'
import { useToast } from '@/lib/hooks/use-toast'

// ============================================================================
// Query Keys
// ============================================================================

export const ANKI_QUERY_KEYS = {
  decks: ['anki', 'decks'] as const,
  deck: (deckId: string) => ['anki', 'decks', deckId] as const,
  deckCards: (deckId: string) => ['anki', 'decks', deckId, 'cards'] as const,
  card: (cardId: string) => ['anki', 'cards', cardId] as const,
  exportSession: (sessionId: string) => ['anki', 'export-sessions', sessionId] as const,
}

// ============================================================================
// Deck Hooks
// ============================================================================

export function useDecks() {
  return useQuery({
    queryKey: ANKI_QUERY_KEYS.decks,
    queryFn: () => ankiApi.decks.list(),
    staleTime: 2 * 60 * 1000, // 2 minutes
  })
}

export function useDeck(deckId: string) {
  return useQuery({
    queryKey: ANKI_QUERY_KEYS.deck(deckId),
    queryFn: () => ankiApi.decks.get(deckId),
    enabled: !!deckId,
    staleTime: 2 * 60 * 1000,
  })
}

export function useCreateDeck() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: (data: DeckCreateRequest) => ankiApi.decks.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ANKI_QUERY_KEYS.decks })
      toast({
        title: 'Success',
        description: 'Deck created successfully',
      })
    },
    onError: (error: Error) => {
      toast({
        title: 'Error',
        description: (error as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Failed to create deck',
        variant: 'destructive',
      })
    },
  })
}

export function useDeleteDeck() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: ({ deckId, deleteCards }: { deckId: string; deleteCards?: boolean }) =>
      ankiApi.decks.delete(deckId, deleteCards),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ANKI_QUERY_KEYS.decks })
      toast({
        title: 'Success',
        description: 'Deck deleted successfully',
      })
    },
    onError: (error: Error) => {
      toast({
        title: 'Error',
        description: (error as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Failed to delete deck',
        variant: 'destructive',
      })
    },
  })
}

// ============================================================================
// Card Hooks
// ============================================================================

export function useDeckCards(deckId: string, params?: { skip?: number; limit?: number }) {
  return useQuery({
    queryKey: [...ANKI_QUERY_KEYS.deckCards(deckId), params],
    queryFn: () => ankiApi.cards.listByDeck(deckId, params),
    enabled: !!deckId,
    staleTime: 1 * 60 * 1000, // 1 minute
  })
}

export function useCard(cardId: string) {
  return useQuery({
    queryKey: ANKI_QUERY_KEYS.card(cardId),
    queryFn: () => ankiApi.cards.get(cardId),
    enabled: !!cardId,
    staleTime: 1 * 60 * 1000,
  })
}

export function useCreateCard() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: (data: CardCreateRequest) => ankiApi.cards.create(data),
    onSuccess: (card) => {
      // Invalidate deck cards query
      queryClient.invalidateQueries({
        queryKey: ANKI_QUERY_KEYS.deckCards(card.deck_id),
      })
      toast({
        title: 'Success',
        description: 'Card created successfully',
      })
    },
    onError: (error: Error) => {
      toast({
        title: 'Error',
        description: (error as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Failed to create card',
        variant: 'destructive',
      })
    },
  })
}

export function useUpdateCard() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: ({ cardId, data }: { cardId: string; data: CardUpdateRequest }) =>
      ankiApi.cards.update(cardId, data),
    onSuccess: (card, variables) => {
      // Invalidate specific card and deck cards
      queryClient.invalidateQueries({ queryKey: ANKI_QUERY_KEYS.card(variables.cardId) })
      queryClient.invalidateQueries({ queryKey: ANKI_QUERY_KEYS.deckCards(card.deck_id) })
      toast({
        title: 'Success',
        description: 'Card updated successfully',
      })
    },
    onError: (error: Error) => {
      toast({
        title: 'Error',
        description: (error as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Failed to update card',
        variant: 'destructive',
      })
    },
  })
}

export function useDeleteCard() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: (cardId: string) => ankiApi.cards.delete(cardId),
    onSuccess: () => {
      // Invalidate all deck cards queries
      queryClient.invalidateQueries({ queryKey: ['anki', 'decks'] })
      toast({
        title: 'Success',
        description: 'Card deleted successfully',
      })
    },
    onError: (error: Error) => {
      toast({
        title: 'Error',
        description: (error as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Failed to delete card',
        variant: 'destructive',
      })
    },
  })
}

// ============================================================================
// CEFR Hooks
// ============================================================================

export function useClassifyCEFR() {
  const { toast } = useToast()

  return useMutation({
    mutationFn: (data: CEFRClassifyRequest) => ankiApi.cefr.classify(data),
    onError: (error: Error) => {
      toast({
        title: 'Error',
        description: (error as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Failed to classify CEFR level',
        variant: 'destructive',
      })
    },
  })
}

export function useSetCardCEFR() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: ({ cardId, text }: { cardId: string; text: string }) =>
      ankiApi.cefr.setCardCEFR(cardId, text),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ANKI_QUERY_KEYS.card(variables.cardId) })
      toast({
        title: 'Success',
        description: 'CEFR level updated successfully',
      })
    },
    onError: (error: Error) => {
      toast({
        title: 'Error',
        description: (error as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Failed to vote on CEFR level',
        variant: 'destructive',
      })
    },
  })
}

// ============================================================================
// Image Hooks
// ============================================================================

export function useSearchImage() {
  const { toast } = useToast()

  return useMutation({
    mutationFn: (data: ImageSearchRequest) => ankiApi.images.search(data),
    onError: (error: Error) => {
      toast({
        title: 'Error',
        description: (error as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Failed to search images',
        variant: 'destructive',
      })
    },
  })
}

export function useUploadCardImage() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: ({ cardId, file }: { cardId: string; file: File }) =>
      ankiApi.images.upload(cardId, file),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ANKI_QUERY_KEYS.card(variables.cardId) })
      toast({
        title: 'Success',
        description: 'Image uploaded successfully',
      })
    },
    onError: (error: Error) => {
      toast({
        title: 'Error',
        description: (error as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Failed to upload image',
        variant: 'destructive',
      })
    },
  })
}

// ============================================================================
// Audio Hooks
// ============================================================================

export function useGenerateAudio() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: ({ cardId, text, language }: { cardId: string; text: string; language?: string }) =>
      ankiApi.audio.generate(cardId, text, language),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ANKI_QUERY_KEYS.card(variables.cardId) })
      toast({
        title: 'Success',
        description: 'Audio generated successfully',
      })
    },
    onError: (error: Error) => {
      toast({
        title: 'Error',
        description: (error as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Failed to generate audio',
        variant: 'destructive',
      })
    },
  })
}

export function useTranscribeAudio() {
  const { toast } = useToast()

  return useMutation({
    mutationFn: ({ cardId, file, referenceText }: { cardId: string; file: File; referenceText: string }) =>
      ankiApi.audio.transcribe(cardId, file, referenceText),
    onSuccess: (result) => {
      const scorePercent = Math.round(result.phonetic_score * 100)
      toast({
        title: 'Transcription Complete',
        description: `Score: ${scorePercent}% - "${result.transcribed_text}"`,
      })
    },
    onError: (error: AxiosError<{ detail?: string }>) => {
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to transcribe audio',
        variant: 'destructive',
      })
    },
  })
}

// ============================================================================
// Export Session Hooks
// ============================================================================

export function useCreateExportSession() {
  const { toast } = useToast()

  return useMutation({
    mutationFn: (data: ExportSessionCreateRequest) => ankiApi.exportSessions.create(data),
    onSuccess: () => {
      toast({
        title: 'Success',
        description: 'Export session created successfully',
      })
    },
    onError: (error: Error) => {
      toast({
        title: 'Error',
        description: (error as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Failed to create export session',
        variant: 'destructive',
      })
    },
  })
}

export function useExportSession(sessionId: string) {
  return useQuery({
    queryKey: ANKI_QUERY_KEYS.exportSession(sessionId),
    queryFn: () => ankiApi.exportSessions.get(sessionId),
    enabled: !!sessionId,
  })
}
