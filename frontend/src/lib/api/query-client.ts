import { QueryClient } from '@tanstack/react-query'

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      gcTime: 10 * 60 * 1000, // 10 minutes
      retry: 2,
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: 1,
    },
  },
})

export const QUERY_KEYS = {
  modules: ['modules'] as const,
  module: (id: string) => ['modules', id] as const,
  notes: (moduleId?: string) => ['notes', moduleId] as const,
  note: (id: string) => ['notes', id] as const,
  sources: (moduleId?: string) => ['sources', moduleId] as const,
  sourcesInfinite: (moduleId: string) => ['sources', 'infinite', moduleId] as const,
  source: (id: string) => ['sources', id] as const,
  settings: ['settings'] as const,
  sourceChatSessions: (sourceId: string) => ['source-chat', sourceId, 'sessions'] as const,
  sourceChatSession: (sourceId: string, sessionId: string) => ['source-chat', sourceId, 'sessions', sessionId] as const,
  moduleChatSessions: (moduleId: string) => ['module-chat', moduleId, 'sessions'] as const,
  moduleChatSession: (sessionId: string) => ['module-chat', 'sessions', sessionId] as const,
  podcastEpisodes: ['podcasts', 'episodes'] as const,
  podcastEpisode: (episodeId: string) => ['podcasts', 'episodes', episodeId] as const,
  episodeProfiles: ['podcasts', 'episode-profiles'] as const,
  speakerProfiles: ['podcasts', 'speaker-profiles'] as const,
}
