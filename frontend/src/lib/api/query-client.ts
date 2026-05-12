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
  notebooks: ['notebooks'] as const,
  notebook: (id: string) => ['notebooks', id] as const,
  publicNotebooks: ['notebooks', 'public'] as const,
  publicSources: ['sources', 'public'] as const,
  workspaces: ['workspaces'] as const,
  workspace: (id: string) => ['workspaces', id] as const,
  workspacePolicy: (id?: string | null) => ['workspaces', id || 'none', 'policy'] as const,
  workspaceSystemPolicy: ['workspaces', 'system-policy'] as const,
  workspaceNotebooks: (workspaceId?: string | null, archived?: boolean) =>
    ['workspaces', workspaceId || 'none', 'notebooks', archived ?? 'all'] as const,
  workspaceSources: (workspaceId?: string | null, notebookId?: string) =>
    ['workspaces', workspaceId || 'none', 'sources', notebookId || 'all'] as const,
  workspaceSourcesInfinite: (workspaceId: string | null | undefined, notebookId: string) =>
    ['workspaces', workspaceId || 'none', 'sources', 'infinite', notebookId] as const,
  notes: (notebookId?: string) => ['notes', notebookId] as const,
  note: (id: string) => ['notes', id] as const,
  sources: (notebookId?: string) => ['sources', notebookId] as const,
  sourcesInfinite: (notebookId: string) => ['sources', 'infinite', notebookId] as const,
  source: (id: string) => ['sources', id] as const,
  settings: ['settings'] as const,
  sourceChatSessions: (sourceId: string) => ['source-chat', sourceId, 'sessions'] as const,
  sourceChatSession: (sourceId: string, sessionId: string) => ['source-chat', sourceId, 'sessions', sessionId] as const,
  notebookChatSessions: (notebookId: string) => ['notebook-chat', notebookId, 'sessions'] as const,
  notebookChatSession: (sessionId: string) => ['notebook-chat', 'sessions', sessionId] as const,
  podcastEpisodes: ['podcasts', 'episodes'] as const,
  podcastEpisode: (episodeId: string) => ['podcasts', 'episodes', episodeId] as const,
  episodeProfiles: ['podcasts', 'episode-profiles'] as const,
  speakerProfiles: ['podcasts', 'speaker-profiles'] as const,
  languages: ['languages'] as const,
  teams: ['teams'] as const,
  teamMembers: (teamId: string) => ['teams', teamId, 'members'] as const,
  teamModels: (teamId: string) => ['teams', teamId, 'models'] as const,
  teamModelDefaults: (teamId: string) => ['teams', teamId, 'model-defaults'] as const,
  teamTransformations: (teamId: string) => ['teams', teamId, 'transformations'] as const,
  users: ['users'] as const,
  shareGrants: (resourceType: string, resourceId: string) => ['share-grants', resourceType, resourceId] as const,
  externalApiConnections: ['external-api', 'connections'] as const,
  externalApiSources: ['external-api', 'sources'] as const,
  externalApiTeamGrants: (sourceId?: string | null) =>
    ['external-api', 'sources', sourceId || 'none', 'team-grants'] as const,
  externalApiAvailableSources: (teamId?: string | null) =>
    ['external-api', 'available-sources', teamId || 'none'] as const,
  externalApiCommand: (commandId?: string | null) =>
    ['external-api', 'commands', commandId || 'none'] as const,
  externalApiUsage: (teamId?: string | null, month?: string | null) =>
    ['external-api', 'usage', teamId || 'none', month || 'current'] as const,
}
