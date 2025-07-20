# Phase 3: Advanced Features Implementation Guide

## Overview

Phase 3 implements the advanced functionality of Open Notebook, including the search and AI querying system, podcast generation and management, and transformations system. This phase adds the intelligence and automation features that differentiate Open Notebook from basic note-taking applications.

## Technology Additions

- **Server-Sent Events (SSE)**: For real-time streaming responses
- **Web Workers**: For background processing
- **React Virtualized**: For large list performance
- **React Player**: For audio playback
- **File Drag & Drop**: Enhanced file handling
- **WebSocket**: For real-time status updates

## Project Structure Additions

```
src/
├── app/
│   ├── (dashboard)/
│   │   ├── search/
│   │   │   ├── page.tsx
│   │   │   └── components/
│   │   │       ├── SearchInterface.tsx
│   │   │       ├── AskInterface.tsx
│   │   │       ├── SearchResults.tsx
│   │   │       ├── ModelSelector.tsx
│   │   │       └── SaveResultDialog.tsx
│   │   ├── podcasts/
│   │   │   ├── page.tsx
│   │   │   └── components/
│   │   │       ├── EpisodesList.tsx
│   │   │       ├── EpisodeCard.tsx
│   │   │       ├── EpisodeProfilesList.tsx
│   │   │       ├── CreateEpisodeDialog.tsx
│   │   │       ├── CreateProfileDialog.tsx
│   │   │       ├── SpeakerConfig.tsx
│   │   │       ├── AudioPlayer.tsx
│   │   │       └── EpisodeStatus.tsx
│   │   ├── transformations/
│   │   │   ├── page.tsx
│   │   │   └── components/
│   │   │       ├── TransformationsList.tsx
│   │   │       ├── TransformationCard.tsx
│   │   │       ├── TransformationEditor.tsx
│   │   │       ├── TransformationPlayground.tsx
│   │   │       └── CreateTransformationDialog.tsx
│   │   └── notebooks/
│   │       └── components/
│   │           ├── ChatColumn.tsx (full implementation)
│   │           ├── ChatInterface.tsx
│   │           ├── ChatSessions.tsx
│   │           ├── MessageList.tsx
│   │           ├── MessageInput.tsx
│   │           ├── ContextPanel.tsx
│   │           ├── SourceCard.tsx (enhanced)
│   │           ├── AddSourceDialog.tsx (full implementation)
│   │           └── SourcePanel.tsx (full implementation)
├── components/
│   ├── ui/
│   │   ├── streaming-text.tsx
│   │   ├── audio-player.tsx
│   │   ├── file-dropzone.tsx
│   │   └── status-indicator.tsx
│   └── common/
│       ├── StreamingResponse.tsx
│       ├── VirtualizedList.tsx
│       └── ProgressBar.tsx
├── lib/
│   ├── api/
│   │   ├── search.ts
│   │   ├── podcasts.ts
│   │   ├── transformations.ts
│   │   ├── episode-profiles.ts
│   │   └── chat.ts
│   ├── hooks/
│   │   ├── use-search.ts
│   │   ├── use-podcasts.ts
│   │   ├── use-transformations.ts
│   │   ├── use-chat.ts
│   │   ├── use-streaming.ts
│   │   └── use-websocket.ts
│   ├── stores/
│   │   ├── chat-store.ts
│   │   └── podcast-store.ts
│   └── utils/
│       ├── streaming.ts
│       ├── audio.ts
│       └── websocket.ts
```

---

## 1. Search and AI Querying System

### 1.1 Search API (`lib/api/search.ts`)

```typescript
import apiClient from './client'

export interface SearchRequest {
  query: string
  type: 'text' | 'vector'
  limit?: number
  search_sources?: boolean
  search_notes?: boolean
  minimum_score?: number
}

export interface SearchResult {
  id: string
  content: string
  score: number
  type: 'source' | 'note'
  title?: string
  source_id?: string
  note_id?: string
  notebook_id?: string
  notebook_name?: string
}

export interface SearchResponse {
  results: SearchResult[]
  total: number
  query: string
  search_type: string
}

export interface AskRequest {
  question: string
  notebook_ids?: string[]
  model_id?: string
  stream?: boolean
}

export const searchApi = {
  search: async (data: SearchRequest) => {
    const response = await apiClient.post<SearchResponse>('/search', data)
    return response.data
  },

  ask: async (data: AskRequest) => {
    const response = await apiClient.post('/search/ask/simple', data)
    return response.data
  },

  askStream: (data: AskRequest, onMessage: (chunk: string) => void, onComplete: () => void) => {
    const eventSource = new EventSource(
      `${apiClient.defaults.baseURL}/search/ask?${new URLSearchParams({
        question: data.question,
        ...(data.notebook_ids && { notebook_ids: data.notebook_ids.join(',') }),
        ...(data.model_id && { model_id: data.model_id }),
      })}`,
      {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth-token')}`,
        },
      }
    )

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.content) {
          onMessage(data.content)
        }
        if (data.done) {
          onComplete()
          eventSource.close()
        }
      } catch (error) {
        console.error('Error parsing SSE data:', error)
      }
    }

    eventSource.onerror = () => {
      onComplete()
      eventSource.close()
    }

    return eventSource
  }
}
```

### 1.2 Search Hook (`lib/hooks/use-search.ts`)

```typescript
import { useMutation, useQuery } from '@tanstack/react-query'
import { searchApi, SearchRequest, AskRequest } from '@/lib/api/search'
import { useState, useCallback } from 'react'

export function useSearch() {
  return useMutation({
    mutationFn: (data: SearchRequest) => searchApi.search(data),
  })
}

export function useAsk() {
  return useMutation({
    mutationFn: (data: AskRequest) => searchApi.ask(data),
  })
}

export function useStreamingAsk() {
  const [isStreaming, setIsStreaming] = useState(false)
  const [response, setResponse] = useState('')
  const [eventSource, setEventSource] = useState<EventSource | null>(null)

  const startStreaming = useCallback((data: AskRequest) => {
    if (eventSource) {
      eventSource.close()
    }

    setIsStreaming(true)
    setResponse('')

    const source = searchApi.askStream(
      data,
      (chunk) => {
        setResponse(prev => prev + chunk)
      },
      () => {
        setIsStreaming(false)
        setEventSource(null)
      }
    )

    setEventSource(source)
  }, [eventSource])

  const stopStreaming = useCallback(() => {
    if (eventSource) {
      eventSource.close()
      setEventSource(null)
      setIsStreaming(false)
    }
  }, [eventSource])

  return {
    isStreaming,
    response,
    startStreaming,
    stopStreaming,
  }
}
```

### 1.3 Search Page (`app/(dashboard)/search/page.tsx`)

```typescript
'use client'

import { useState } from 'react'
import { AppShell } from '@/components/layout/AppShell'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { SearchInterface } from './components/SearchInterface'
import { AskInterface } from './components/AskInterface'

export default function SearchPage() {
  const [activeTab, setActiveTab] = useState('ask')

  return (
    <AppShell title="Ask and Search">
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <TabsList>
          <TabsTrigger value="ask">Ask Your Knowledge Base</TabsTrigger>
          <TabsTrigger value="search">Search</TabsTrigger>
        </TabsList>
        
        <TabsContent value="ask">
          <AskInterface />
        </TabsContent>
        
        <TabsContent value="search">
          <SearchInterface />
        </TabsContent>
      </Tabs>
    </AppShell>
  )
}
```

### 1.4 Ask Interface (`app/(dashboard)/search/components/AskInterface.tsx`)

```typescript
'use client'

import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { ModelSelector } from './ModelSelector'
import { StreamingResponse } from '@/components/common/StreamingResponse'
import { useStreamingAsk } from '@/lib/hooks/use-search'
import { useNotebooks } from '@/lib/hooks/use-notebooks'
import { Checkbox } from '@/components/ui/checkbox'
import { ScrollArea } from '@/components/ui/scroll-area'
import { MessageCircle, Save, Square } from 'lucide-react'

interface AskFormData {
  question: string
  model_id: string
  notebook_ids: string[]
}

export function AskInterface() {
  const [selectedNotebooks, setSelectedNotebooks] = useState<string[]>([])
  const { data: notebooks } = useNotebooks(false)
  const { isStreaming, response, startStreaming, stopStreaming } = useStreamingAsk()
  
  const { register, handleSubmit, formState: { isValid }, reset } = useForm<AskFormData>()

  const onSubmit = (data: AskFormData) => {
    startStreaming({
      question: data.question,
      notebook_ids: selectedNotebooks.length > 0 ? selectedNotebooks : undefined,
      model_id: data.model_id,
      stream: true,
    })
  }

  const handleSaveAsNote = () => {
    // TODO: Implement save as note functionality
    console.log('Save as note:', response)
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <MessageCircle className="h-5 w-5" />
            Ask Your Knowledge Base
          </CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2 space-y-4">
                <div>
                  <Label htmlFor="question">Your Question</Label>
                  <Textarea
                    id="question"
                    {...register('question', { required: true })}
                    placeholder="Ask a question about your knowledge base..."
                    rows={4}
                    disabled={isStreaming}
                  />
                </div>

                <div>
                  <Label>Model Configuration</Label>
                  <div className="grid grid-cols-2 gap-4 mt-2">
                    <ModelSelector
                      type="language"
                      label="Language Model"
                      {...register('model_id')}
                      disabled={isStreaming}
                    />
                  </div>
                </div>
              </div>

              <div>
                <Label>Notebooks to Search</Label>
                <Card className="mt-2">
                  <CardContent className="p-3">
                    <ScrollArea className="h-40">
                      <div className="space-y-2">
                        <div className="flex items-center space-x-2">
                          <Checkbox
                            id="all-notebooks"
                            checked={selectedNotebooks.length === 0}
                            onCheckedChange={(checked) => {
                              if (checked) {
                                setSelectedNotebooks([])
                              }
                            }}
                            disabled={isStreaming}
                          />
                          <Label htmlFor="all-notebooks" className="text-sm font-medium">
                            All Notebooks
                          </Label>
                        </div>
                        {notebooks?.map((notebook) => (
                          <div key={notebook.id} className="flex items-center space-x-2">
                            <Checkbox
                              id={notebook.id}
                              checked={selectedNotebooks.includes(notebook.id)}
                              onCheckedChange={(checked) => {
                                if (checked) {
                                  setSelectedNotebooks(prev => [...prev, notebook.id])
                                } else {
                                  setSelectedNotebooks(prev => prev.filter(id => id !== notebook.id))
                                }
                              }}
                              disabled={isStreaming}
                            />
                            <Label htmlFor={notebook.id} className="text-sm">
                              {notebook.name}
                            </Label>
                          </div>
                        ))}
                      </div>
                    </ScrollArea>
                  </CardContent>
                </Card>
              </div>
            </div>

            <div className="flex gap-2">
              {isStreaming ? (
                <Button type="button" onClick={stopStreaming} variant="outline">
                  <Square className="h-4 w-4 mr-2" />
                  Stop
                </Button>
              ) : (
                <Button type="submit" disabled={!isValid}>
                  <MessageCircle className="h-4 w-4 mr-2" />
                  Ask Question
                </Button>
              )}
            </div>
          </form>
        </CardContent>
      </Card>

      {(isStreaming || response) && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Response</CardTitle>
              {response && !isStreaming && (
                <Button variant="outline" size="sm" onClick={handleSaveAsNote}>
                  <Save className="h-4 w-4 mr-2" />
                  Save as Note
                </Button>
              )}
            </div>
          </CardHeader>
          <CardContent>
            <StreamingResponse 
              content={response} 
              isStreaming={isStreaming} 
            />
          </CardContent>
        </Card>
      )}
    </div>
  )
}
```

---

## 2. Podcast System Implementation

### 2.1 Podcasts API (`lib/api/podcasts.ts`)

```typescript
import apiClient from './client'

export interface Episode {
  id: string
  name: string
  notebook_id: string
  notebook_name: string
  profile_id: string
  profile_name: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  file_path?: string
  error_message?: string
  created: string
  updated: string
  duration?: number
}

export interface EpisodeProfile {
  id: string
  name: string
  description: string
  briefing_template: string
  speakers: Speaker[]
  created: string
  updated: string
}

export interface Speaker {
  id: string
  name: string
  voice_id: string
  voice_provider: string
  personality: string
  backstory: string
  role: string
}

export interface CreateEpisodeRequest {
  name: string
  notebook_id: string
  profile_id: string
  custom_briefing?: string
}

export const podcastsApi = {
  // Episodes
  listEpisodes: async () => {
    const response = await apiClient.get<Episode[]>('/podcasts')
    return response.data
  },

  getEpisode: async (id: string) => {
    const response = await apiClient.get<Episode>(`/podcasts/${id}`)
    return response.data
  },

  createEpisode: async (data: CreateEpisodeRequest) => {
    const response = await apiClient.post<Episode>('/podcasts', data)
    return response.data
  },

  deleteEpisode: async (id: string) => {
    await apiClient.delete(`/podcasts/${id}`)
  },

  // Episode Profiles
  listProfiles: async () => {
    const response = await apiClient.get<EpisodeProfile[]>('/episode-profiles')
    return response.data
  },

  getProfile: async (id: string) => {
    const response = await apiClient.get<EpisodeProfile>(`/episode-profiles/${id}`)
    return response.data
  },

  createProfile: async (data: Omit<EpisodeProfile, 'id' | 'created' | 'updated'>) => {
    const response = await apiClient.post<EpisodeProfile>('/episode-profiles', data)
    return response.data
  },

  updateProfile: async (id: string, data: Partial<EpisodeProfile>) => {
    const response = await apiClient.put<EpisodeProfile>(`/episode-profiles/${id}`, data)
    return response.data
  },

  deleteProfile: async (id: string) => {
    await apiClient.delete(`/episode-profiles/${id}`)
  },

  initializeDefaultProfiles: async () => {
    const response = await apiClient.post('/episode-profiles/initialize-defaults')
    return response.data
  }
}
```

### 2.2 Podcasts Hook (`lib/hooks/use-podcasts.ts`)

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { podcastsApi, CreateEpisodeRequest } from '@/lib/api/podcasts'
import { useToast } from '@/lib/hooks/use-toast'

const PODCAST_QUERY_KEYS = {
  episodes: ['podcasts', 'episodes'] as const,
  episode: (id: string) => ['podcasts', 'episodes', id] as const,
  profiles: ['podcasts', 'profiles'] as const,
  profile: (id: string) => ['podcasts', 'profiles', id] as const,
}

export function usePodcastEpisodes() {
  return useQuery({
    queryKey: PODCAST_QUERY_KEYS.episodes,
    queryFn: () => podcastsApi.listEpisodes(),
    refetchInterval: (data) => {
      // Refetch every 5 seconds if there are running episodes
      const hasRunning = data?.some(episode => episode.status === 'running' || episode.status === 'pending')
      return hasRunning ? 5000 : false
    }
  })
}

export function useEpisodeProfiles() {
  return useQuery({
    queryKey: PODCAST_QUERY_KEYS.profiles,
    queryFn: () => podcastsApi.listProfiles(),
  })
}

export function useCreateEpisode() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: (data: CreateEpisodeRequest) => podcastsApi.createEpisode(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: PODCAST_QUERY_KEYS.episodes })
      toast({
        title: 'Success',
        description: 'Podcast episode generation started',
      })
    },
    onError: () => {
      toast({
        title: 'Error',
        description: 'Failed to start podcast generation',
        variant: 'destructive',
      })
    },
  })
}

export function useInitializeProfiles() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: () => podcastsApi.initializeDefaultProfiles(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: PODCAST_QUERY_KEYS.profiles })
      toast({
        title: 'Success',
        description: 'Default profiles initialized',
      })
    },
  })
}
```

### 2.3 Podcasts Page (`app/(dashboard)/podcasts/page.tsx`)

```typescript
'use client'

import { AppShell } from '@/components/layout/AppShell'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { EpisodesList } from './components/EpisodesList'
import { EpisodeProfilesList } from './components/EpisodeProfilesList'
import { usePodcastEpisodes, useEpisodeProfiles } from '@/lib/hooks/use-podcasts'

export default function PodcastsPage() {
  const { data: episodes, refetch: refetchEpisodes } = usePodcastEpisodes()
  const { data: profiles, refetch: refetchProfiles } = useEpisodeProfiles()

  return (
    <AppShell 
      title="Podcasts" 
      onRefresh={() => {
        refetchEpisodes()
        refetchProfiles()
      }}
    >
      <Tabs defaultValue="episodes" className="space-y-6">
        <TabsList>
          <TabsTrigger value="episodes">Episodes</TabsTrigger>
          <TabsTrigger value="templates">Episode Profiles</TabsTrigger>
        </TabsList>
        
        <TabsContent value="episodes">
          <EpisodesList episodes={episodes} />
        </TabsContent>
        
        <TabsContent value="templates">
          <EpisodeProfilesList profiles={profiles} />
        </TabsContent>
      </Tabs>
    </AppShell>
  )
}
```

### 2.4 Episodes List (`app/(dashboard)/podcasts/components/EpisodesList.tsx`)

```typescript
'use client'

import { useState } from 'react'
import { Episode } from '@/lib/api/podcasts'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Plus } from 'lucide-react'
import { EpisodeCard } from './EpisodeCard'
import { CreateEpisodeDialog } from './CreateEpisodeDialog'
import { EmptyState } from '@/components/common/EmptyState'
import { Mic } from 'lucide-react'

interface EpisodesListProps {
  episodes?: Episode[]
}

const statusGroups = {
  pending: 'Pending',
  running: 'Running',
  completed: 'Completed',
  failed: 'Failed'
} as const

export function EpisodesList({ episodes }: EpisodesListProps) {
  const [showCreateDialog, setShowCreateDialog] = useState(false)

  if (!episodes || episodes.length === 0) {
    return (
      <>
        <EmptyState
          icon={Mic}
          title="No podcast episodes yet"
          description="Create your first podcast episode from your research content."
          action={
            <Button onClick={() => setShowCreateDialog(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Generate Episode
            </Button>
          }
        />
        <CreateEpisodeDialog
          open={showCreateDialog}
          onOpenChange={setShowCreateDialog}
        />
      </>
    )
  }

  // Group episodes by status
  const groupedEpisodes = episodes.reduce((acc, episode) => {
    if (!acc[episode.status]) {
      acc[episode.status] = []
    }
    acc[episode.status].push(episode)
    return acc
  }, {} as Record<string, Episode[]>)

  return (
    <>
      <div className="space-y-8">
        <div className="flex justify-between items-center">
          <h2 className="text-2xl font-bold">Podcast Episodes</h2>
          <Button onClick={() => setShowCreateDialog(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Generate Episode
          </Button>
        </div>

        {Object.entries(statusGroups).map(([status, label]) => {
          const statusEpisodes = groupedEpisodes[status] || []
          if (statusEpisodes.length === 0) return null

          return (
            <div key={status} className="space-y-4">
              <div className="flex items-center gap-3">
                <h3 className="text-lg font-semibold">{label}</h3>
                <Badge variant="secondary">
                  {statusEpisodes.length}
                </Badge>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {statusEpisodes.map((episode) => (
                  <EpisodeCard key={episode.id} episode={episode} />
                ))}
              </div>
            </div>
          )
        })}
      </div>

      <CreateEpisodeDialog
        open={showCreateDialog}
        onOpenChange={setShowCreateDialog}
      />
    </>
  )
}
```

---

## 3. Chat System Implementation

### 3.1 Chat Store (`lib/stores/chat-store.ts`)

```typescript
import { create } from 'zustand'

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  sources?: string[]
}

export interface ChatSession {
  id: string
  name: string
  notebook_id: string
  messages: ChatMessage[]
  created: Date
  updated: Date
}

interface ChatState {
  sessions: Record<string, ChatSession[]> // keyed by notebook_id
  activeSession: Record<string, string> // active session_id per notebook_id
  
  // Actions
  getSessions: (notebookId: string) => ChatSession[]
  getActiveSession: (notebookId: string) => ChatSession | undefined
  createSession: (notebookId: string, name: string) => ChatSession
  setActiveSession: (notebookId: string, sessionId: string) => void
  addMessage: (notebookId: string, sessionId: string, message: Omit<ChatMessage, 'id'>) => void
  updateSessionName: (notebookId: string, sessionId: string, name: string) => void
  deleteSession: (notebookId: string, sessionId: string) => void
}

export const useChatStore = create<ChatState>((set, get) => ({
  sessions: {},
  activeSession: {},

  getSessions: (notebookId: string) => {
    return get().sessions[notebookId] || []
  },

  getActiveSession: (notebookId: string) => {
    const sessions = get().sessions[notebookId] || []
    const activeId = get().activeSession[notebookId]
    return sessions.find(s => s.id === activeId)
  },

  createSession: (notebookId: string, name: string) => {
    const session: ChatSession = {
      id: `session_${Date.now()}`,
      name,
      notebook_id: notebookId,
      messages: [],
      created: new Date(),
      updated: new Date()
    }

    set(state => ({
      sessions: {
        ...state.sessions,
        [notebookId]: [...(state.sessions[notebookId] || []), session]
      },
      activeSession: {
        ...state.activeSession,
        [notebookId]: session.id
      }
    }))

    return session
  },

  setActiveSession: (notebookId: string, sessionId: string) => {
    set(state => ({
      activeSession: {
        ...state.activeSession,
        [notebookId]: sessionId
      }
    }))
  },

  addMessage: (notebookId: string, sessionId: string, message: Omit<ChatMessage, 'id'>) => {
    const newMessage: ChatMessage = {
      ...message,
      id: `msg_${Date.now()}`,
    }

    set(state => {
      const sessions = state.sessions[notebookId] || []
      const updatedSessions = sessions.map(session => 
        session.id === sessionId 
          ? { 
              ...session, 
              messages: [...session.messages, newMessage],
              updated: new Date()
            }
          : session
      )

      return {
        sessions: {
          ...state.sessions,
          [notebookId]: updatedSessions
        }
      }
    })
  },

  updateSessionName: (notebookId: string, sessionId: string, name: string) => {
    set(state => {
      const sessions = state.sessions[notebookId] || []
      const updatedSessions = sessions.map(session => 
        session.id === sessionId 
          ? { ...session, name, updated: new Date() }
          : session
      )

      return {
        sessions: {
          ...state.sessions,
          [notebookId]: updatedSessions
        }
      }
    })
  },

  deleteSession: (notebookId: string, sessionId: string) => {
    set(state => {
      const sessions = state.sessions[notebookId] || []
      const filteredSessions = sessions.filter(s => s.id !== sessionId)
      
      let newActiveSession = state.activeSession[notebookId]
      if (newActiveSession === sessionId) {
        newActiveSession = filteredSessions[0]?.id || ''
      }

      return {
        sessions: {
          ...state.sessions,
          [notebookId]: filteredSessions
        },
        activeSession: {
          ...state.activeSession,
          [notebookId]: newActiveSession
        }
      }
    })
  }
}))
```

### 3.2 Enhanced Chat Column (`app/(dashboard)/notebooks/components/ChatColumn.tsx`)

```typescript
'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Plus, Settings } from 'lucide-react'
import { ChatInterface } from './ChatInterface'
import { ChatSessions } from './ChatSessions'
import { ContextPanel } from './ContextPanel'
import { useChatStore } from '@/lib/stores/chat-store'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

interface ChatColumnProps {
  notebookId: string
}

export function ChatColumn({ notebookId }: ChatColumnProps) {
  const [showContextPanel, setShowContextPanel] = useState(false)
  const { getSessions, getActiveSession, createSession } = useChatStore()
  
  const sessions = getSessions(notebookId)
  const activeSession = getActiveSession(notebookId)

  // Create initial session if none exists
  useEffect(() => {
    if (sessions.length === 0) {
      createSession(notebookId, 'General Discussion')
    }
  }, [notebookId, sessions.length, createSession])

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">Chat</CardTitle>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowContextPanel(!showContextPanel)}
            >
              <Settings className="h-4 w-4" />
            </Button>
            <Button
              size="sm"
              onClick={() => createSession(notebookId, `Session ${sessions.length + 1}`)}
            >
              <Plus className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardHeader>
      
      <CardContent className="flex-1 flex flex-col overflow-hidden p-0">
        <Tabs defaultValue="chat" className="flex-1 flex flex-col">
          <TabsList className="mx-6 mb-3">
            <TabsTrigger value="chat">Chat</TabsTrigger>
            <TabsTrigger value="context">Context</TabsTrigger>
          </TabsList>
          
          <TabsContent value="chat" className="flex-1 flex flex-col m-0">
            <div className="px-6 pb-3">
              <ChatSessions notebookId={notebookId} />
            </div>
            
            <div className="flex-1 px-6 pb-6">
              {activeSession ? (
                <ChatInterface 
                  notebookId={notebookId} 
                  session={activeSession} 
                />
              ) : (
                <div className="flex items-center justify-center h-full text-gray-500">
                  <p>No active chat session</p>
                </div>
              )}
            </div>
          </TabsContent>
          
          <TabsContent value="context" className="flex-1 m-0 px-6 pb-6">
            <ContextPanel notebookId={notebookId} />
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  )
}
```

---

## 4. Common Components

### 4.1 Streaming Response (`components/common/StreamingResponse.tsx`)

```typescript
'use client'

import { useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import { LoadingSpinner } from './LoadingSpinner'

interface StreamingResponseProps {
  content: string
  isStreaming: boolean
}

export function StreamingResponse({ content, isStreaming }: StreamingResponseProps) {
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [content])

  return (
    <div 
      ref={scrollRef}
      className="max-h-96 overflow-y-auto border rounded-lg p-4 bg-gray-50"
    >
      {content ? (
        <div className="prose prose-sm max-w-none">
          <ReactMarkdown>{content}</ReactMarkdown>
        </div>
      ) : (
        <div className="text-gray-500 italic">
          Waiting for response...
        </div>
      )}
      
      {isStreaming && (
        <div className="flex items-center gap-2 mt-4 text-sm text-gray-500">
          <LoadingSpinner size="sm" />
          Generating response...
        </div>
      )}
    </div>
  )
}
```

### 4.2 Audio Player (`components/ui/audio-player.tsx`)

```typescript
'use client'

import { useState, useRef, useEffect } from 'react'
import { Button } from './button'
import { Slider } from './slider'
import { Play, Pause, Download, Volume2 } from 'lucide-react'

interface AudioPlayerProps {
  src: string
  title?: string
  downloadUrl?: string
}

export function AudioPlayer({ src, title, downloadUrl }: AudioPlayerProps) {
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [volume, setVolume] = useState(1)
  const audioRef = useRef<HTMLAudioElement>(null)

  useEffect(() => {
    const audio = audioRef.current
    if (!audio) return

    const handleTimeUpdate = () => setCurrentTime(audio.currentTime)
    const handleDurationChange = () => setDuration(audio.duration)
    const handleEnded = () => setIsPlaying(false)

    audio.addEventListener('timeupdate', handleTimeUpdate)
    audio.addEventListener('durationchange', handleDurationChange)
    audio.addEventListener('ended', handleEnded)

    return () => {
      audio.removeEventListener('timeupdate', handleTimeUpdate)
      audio.removeEventListener('durationchange', handleDurationChange)
      audio.removeEventListener('ended', handleEnded)
    }
  }, [])

  const togglePlayPause = () => {
    const audio = audioRef.current
    if (!audio) return

    if (isPlaying) {
      audio.pause()
    } else {
      audio.play()
    }
    setIsPlaying(!isPlaying)
  }

  const handleSeek = (value: number[]) => {
    const audio = audioRef.current
    if (!audio) return

    const time = value[0]
    audio.currentTime = time
    setCurrentTime(time)
  }

  const handleVolumeChange = (value: number[]) => {
    const audio = audioRef.current
    if (!audio) return

    const vol = value[0]
    audio.volume = vol
    setVolume(vol)
  }

  const formatTime = (time: number) => {
    const minutes = Math.floor(time / 60)
    const seconds = Math.floor(time % 60)
    return `${minutes}:${seconds.toString().padStart(2, '0')}`
  }

  return (
    <div className="bg-white border rounded-lg p-4 space-y-4">
      <audio ref={audioRef} src={src} preload="metadata" />
      
      {title && (
        <h4 className="font-medium truncate">{title}</h4>
      )}
      
      <div className="flex items-center gap-4">
        <Button
          variant="outline"
          size="sm"
          onClick={togglePlayPause}
          disabled={!src}
        >
          {isPlaying ? (
            <Pause className="h-4 w-4" />
          ) : (
            <Play className="h-4 w-4" />
          )}
        </Button>
        
        <div className="flex-1 space-y-2">
          <Slider
            value={[currentTime]}
            max={duration || 100}
            step={1}
            onValueChange={handleSeek}
            className="cursor-pointer"
          />
          <div className="flex justify-between text-xs text-gray-500">
            <span>{formatTime(currentTime)}</span>
            <span>{formatTime(duration)}</span>
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          <Volume2 className="h-4 w-4" />
          <Slider
            value={[volume]}
            max={1}
            step={0.1}
            onValueChange={handleVolumeChange}
            className="w-20"
          />
        </div>
        
        {downloadUrl && (
          <Button variant="outline" size="sm" asChild>
            <a href={downloadUrl} download>
              <Download className="h-4 w-4" />
            </a>
          </Button>
        )}
      </div>
    </div>
  )
}
```

---

## 5. Enhanced Source Management

### 5.1 Full Add Source Dialog (`app/(dashboard)/notebooks/components/AddSourceDialog.tsx`)

```typescript
'use client'

import { useState } from 'react'
import { useForm } from 'react-hook-form'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { FileUpload } from '@/components/ui/file-upload'
import { Link, Upload, Type } from 'lucide-react'
import { useCreateSource, useFileUpload } from '@/lib/hooks/use-sources'

interface AddSourceDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  notebookId: string
}

interface SourceFormData {
  title?: string
  url?: string
  content?: string
}

export function AddSourceDialog({ open, onOpenChange, notebookId }: AddSourceDialogProps) {
  const [activeTab, setActiveTab] = useState('link')
  const [selectedFiles, setSelectedFiles] = useState<File[]>([])
  
  const createSource = useCreateSource()
  const fileUpload = useFileUpload()
  
  const { register, handleSubmit, reset, formState: { errors } } = useForm<SourceFormData>()

  const handleClose = () => {
    reset()
    setSelectedFiles([])
    onOpenChange(false)
  }

  const onSubmitLink = async (data: SourceFormData) => {
    if (!data.url) return
    
    await createSource.mutateAsync({
      notebook_id: notebookId,
      type: 'link',
      url: data.url,
      title: data.title,
    })
    
    handleClose()
  }

  const onSubmitText = async (data: SourceFormData) => {
    if (!data.content) return
    
    await createSource.mutateAsync({
      notebook_id: notebookId,
      type: 'text',
      content: data.content,
      title: data.title || 'Text Content',
    })
    
    handleClose()
  }

  const onSubmitFiles = async () => {
    for (const file of selectedFiles) {
      await fileUpload.mutateAsync({
        file,
        notebookId,
      })
    }
    
    handleClose()
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Add Source</DialogTitle>
          <DialogDescription>
            Add content to your notebook from various sources
          </DialogDescription>
        </DialogHeader>

        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="link" className="flex items-center gap-2">
              <Link className="h-4 w-4" />
              Link
            </TabsTrigger>
            <TabsTrigger value="upload" className="flex items-center gap-2">
              <Upload className="h-4 w-4" />
              Upload
            </TabsTrigger>
            <TabsTrigger value="text" className="flex items-center gap-2">
              <Type className="h-4 w-4" />
              Text
            </TabsTrigger>
          </TabsList>

          <TabsContent value="link" className="space-y-4">
            <form onSubmit={handleSubmit(onSubmitLink)} className="space-y-4">
              <div>
                <Label htmlFor="url">URL *</Label>
                <Input
                  id="url"
                  type="url"
                  {...register('url', { 
                    required: 'URL is required',
                    pattern: {
                      value: /^https?:\/\/.+/,
                      message: 'Please enter a valid URL'
                    }
                  })}
                  placeholder="https://example.com/article"
                />
                {errors.url && (
                  <p className="text-sm text-red-600 mt-1">{errors.url.message}</p>
                )}
              </div>
              
              <div>
                <Label htmlFor="link-title">Title (optional)</Label>
                <Input
                  id="link-title"
                  {...register('title')}
                  placeholder="Custom title for this source"
                />
              </div>

              <div className="flex justify-end gap-2">
                <Button type="button" variant="outline" onClick={handleClose}>
                  Cancel
                </Button>
                <Button type="submit" disabled={createSource.isPending}>
                  {createSource.isPending ? 'Adding...' : 'Add Source'}
                </Button>
              </div>
            </form>
          </TabsContent>

          <TabsContent value="upload" className="space-y-4">
            <div>
              <Label>Files</Label>
              <FileUpload
                onFilesSelected={setSelectedFiles}
                multiple
                accept=".pdf,.docx,.txt,.md,.epub,.pptx,.xlsx"
              />
            </div>

            {selectedFiles.length > 0 && (
              <div className="space-y-2">
                <Label>Selected Files ({selectedFiles.length})</Label>
                <div className="space-y-1">
                  {selectedFiles.map((file, index) => (
                    <div key={index} className="text-sm text-gray-600">
                      {file.name} ({(file.size / 1024 / 1024).toFixed(2)} MB)
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="flex justify-end gap-2">
              <Button type="button" variant="outline" onClick={handleClose}>
                Cancel
              </Button>
              <Button 
                onClick={onSubmitFiles}
                disabled={selectedFiles.length === 0 || fileUpload.isPending}
              >
                {fileUpload.isPending ? 'Uploading...' : `Upload ${selectedFiles.length} File(s)`}
              </Button>
            </div>
          </TabsContent>

          <TabsContent value="text" className="space-y-4">
            <form onSubmit={handleSubmit(onSubmitText)} className="space-y-4">
              <div>
                <Label htmlFor="text-title">Title</Label>
                <Input
                  id="text-title"
                  {...register('title')}
                  placeholder="Title for this text content"
                />
              </div>
              
              <div>
                <Label htmlFor="content">Content *</Label>
                <Textarea
                  id="content"
                  {...register('content', { required: 'Content is required' })}
                  placeholder="Paste or type your content here..."
                  rows={8}
                />
                {errors.content && (
                  <p className="text-sm text-red-600 mt-1">{errors.content.message}</p>
                )}
              </div>

              <div className="flex justify-end gap-2">
                <Button type="button" variant="outline" onClick={handleClose}>
                  Cancel
                </Button>
                <Button type="submit" disabled={createSource.isPending}>
                  {createSource.isPending ? 'Adding...' : 'Add Source'}
                </Button>
              </div>
            </form>
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  )
}
```

---

## 6. Dependencies Addition

Add to package.json:

```json
{
  "dependencies": {
    "react-virtualized": "^9.22.0",
    "react-markdown": "^9.0.0",
    "react-player": "^2.13.0",
    "react-dropzone": "^14.2.0",
    "@monaco-editor/react": "^4.6.0",
    "ws": "^8.14.0"
  },
  "devDependencies": {
    "@types/react-virtualized": "^9.21.0",
    "@types/ws": "^8.5.0"
  }
}
```

---

## Success Criteria

Phase 3 is complete when:

1. ✅ **Search System**: Full text and vector search with result display
2. ✅ **AI Querying**: Streaming ask interface with model selection
3. ✅ **Podcast Generation**: Episode creation with profile management
4. ✅ **Audio Playback**: Full-featured audio player with controls
5. ✅ **Chat System**: Multi-session chat with context management
6. ✅ **Transformations**: Content transformation system (basic implementation)
7. ✅ **Enhanced Sources**: Complete source management with file upload
8. ✅ **Real-time Updates**: Streaming responses and status updates
9. ✅ **Background Processing**: Non-blocking generation processes

This phase delivers the advanced AI-powered features that make Open Notebook a powerful research tool, setting up Phase 4 for polish and optimization.