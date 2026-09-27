import { MessageSquare, Code, Mic, Volume2, Box } from 'lucide-react'

// Provider metadata (names, display names, modalities, docs links) comes
// from the backend registry via GET /api/providers — see useProviders()
// (src/lib/hooks/use-providers.ts). Only genuinely presentational data
// lives here: how each model modality is rendered (icon, color, label).
//
// Modalities arrive as runtime strings from the API, so every lookup has
// a fallback: an unknown modality still renders (generic icon, raw name)
// instead of breaking. Adding a provider must never require a frontend
// edit.

export type ModelType = 'language' | 'embedding' | 'text_to_speech' | 'speech_to_text'

export const MODEL_TYPES: ModelType[] = [
  'language',
  'embedding',
  'text_to_speech',
  'speech_to_text',
]

const TYPE_ICONS: Record<ModelType, React.ReactNode> = {
  language: <MessageSquare className="h-3 w-3" />,
  embedding: <Code className="h-3 w-3" />,
  text_to_speech: <Volume2 className="h-3 w-3" />,
  speech_to_text: <Mic className="h-3 w-3" />,
}

// Mandatory fallback for modality strings the frontend doesn't know yet.
const FALLBACK_TYPE_ICON: React.ReactNode = <Box className="h-3 w-3" />

const TYPE_COLORS: Record<ModelType, string> = {
  language: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
  embedding: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300',
  text_to_speech: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
  speech_to_text: 'bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-300',
}

export const TYPE_COLOR_INACTIVE = 'bg-muted text-muted-foreground opacity-50'

const TYPE_COLOR_FALLBACK = 'bg-muted text-muted-foreground'

const TYPE_LABELS: Record<ModelType, string> = {
  language: 'Language',
  embedding: 'Embedding',
  text_to_speech: 'TTS',
  speech_to_text: 'STT',
}

export function getTypeIcon(type: string): React.ReactNode {
  return TYPE_ICONS[type as ModelType] ?? FALLBACK_TYPE_ICON
}

export function getTypeColor(type: string): string {
  return TYPE_COLORS[type as ModelType] ?? TYPE_COLOR_FALLBACK
}

export function getTypeLabel(type: string): string {
  return TYPE_LABELS[type as ModelType] ?? type
}
