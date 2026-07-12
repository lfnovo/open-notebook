import { MessageSquare, Code, Mic, Volume2 } from 'lucide-react'

export type ModelType = 'language' | 'embedding' | 'text_to_speech' | 'speech_to_text'

// Provider display names
export const PROVIDER_DISPLAY_NAMES: Record<string, string> = {
  openai: 'OpenAI',
  anthropic: 'Anthropic',
  google: 'Google AI',
  groq: 'Groq',
  mistral: 'Mistral AI',
  deepseek: 'DeepSeek',
  xai: 'xAI (Grok)',
  openrouter: 'OpenRouter',
  voyage: 'Voyage AI',
  elevenlabs: 'ElevenLabs',
  deepgram: 'Deepgram',
  ollama: 'Ollama',
  azure: 'Azure OpenAI',
  vertex: 'Google Vertex AI',
  openai_compatible: 'OpenAI Compatible',
  dashscope: 'DashScope (Qwen)',
  minimax: 'MiniMax',
}

// All providers in display order
export const ALL_PROVIDERS = [
  'openai', 'anthropic', 'google', 'groq', 'mistral', 'deepseek',
  'xai', 'openrouter', 'dashscope', 'minimax', 'voyage', 'elevenlabs', 'deepgram', 'ollama',
  'azure', 'vertex', 'openai_compatible',
]

// Default modalities per provider
export const PROVIDER_MODALITIES: Record<string, ModelType[]> = {
  openai: ['language', 'embedding', 'text_to_speech', 'speech_to_text'],
  anthropic: ['language'],
  google: ['language', 'embedding', 'text_to_speech', 'speech_to_text'],
  groq: ['language', 'speech_to_text'],
  mistral: ['language', 'embedding', 'speech_to_text', 'text_to_speech'],
  deepseek: ['language'],
  xai: ['language', 'text_to_speech'],
  openrouter: ['language', 'embedding'],
  voyage: ['embedding'],
  elevenlabs: ['text_to_speech', 'speech_to_text'],
  deepgram: ['text_to_speech'],
  ollama: ['language', 'embedding'],
  azure: ['language', 'embedding', 'text_to_speech', 'speech_to_text'],
  vertex: ['language', 'embedding', 'text_to_speech'],
  openai_compatible: ['language', 'embedding', 'text_to_speech', 'speech_to_text'],
  dashscope: ['language'],
  minimax: ['language'],
}

// Documentation links
export const PROVIDER_DOCS: Record<string, string> = {
  openai: 'https://platform.openai.com/api-keys',
  anthropic: 'https://console.anthropic.com/settings/keys',
  google: 'https://aistudio.google.com/app/apikey',
  groq: 'https://console.groq.com/keys',
  mistral: 'https://console.mistral.ai/api-keys/',
  deepseek: 'https://platform.deepseek.com/api_keys',
  xai: 'https://console.x.ai/',
  openrouter: 'https://openrouter.ai/keys',
  voyage: 'https://dash.voyageai.com/api-keys',
  elevenlabs: 'https://elevenlabs.io/app/settings/api-keys',
  deepgram: 'https://console.deepgram.com/',
  azure: 'https://portal.azure.com/#view/Microsoft_Azure_ProjectOxford/CognitiveServicesHub/~/OpenAI',
  vertex: 'https://cloud.google.com/vertex-ai/docs/start/cloud-environment',
  openai_compatible: 'https://github.com/lfnovo/open-notebook/blob/main/docs/5-CONFIGURATION/openai-compatible.md',
  dashscope: 'https://help.aliyun.com/zh/model-studio/getting-started/',
  minimax: 'https://platform.minimaxi.com/document/Guides',
}

export const TYPE_ICONS: Record<ModelType, React.ReactNode> = {
  language: <MessageSquare className="h-3 w-3" />,
  embedding: <Code className="h-3 w-3" />,
  text_to_speech: <Volume2 className="h-3 w-3" />,
  speech_to_text: <Mic className="h-3 w-3" />,
}

export const TYPE_COLORS: Record<ModelType, string> = {
  language: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
  embedding: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300',
  text_to_speech: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
  speech_to_text: 'bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-300',
}

export const TYPE_COLOR_INACTIVE = 'bg-muted text-muted-foreground opacity-50'

export const TYPE_LABELS: Record<ModelType, string> = {
  language: 'Language',
  embedding: 'Embedding',
  text_to_speech: 'TTS',
  speech_to_text: 'STT',
}
