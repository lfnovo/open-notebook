import { useMemo } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { podcastsApi, EpisodeProfileInput, SpeakerProfileInput } from '@/lib/api/podcasts'
import { QUERY_KEYS } from '@/lib/api/query-client'
import { useToast } from '@/lib/hooks/use-toast'
import {
  ACTIVE_EPISODE_STATUSES,
  EpisodeProfile,
  EpisodeStatusGroups,
  PodcastEpisode,
  PodcastGenerationRequest,
  groupEpisodesByStatus,
  speakerUsageMap,
} from '@/lib/types/podcasts'

interface EpisodeStatusCounts {
  total: number
  running: number
  completed: number
  failed: number
  pending: number
}

function hasActiveEpisodes(episodes: PodcastEpisode[]) {
  return episodes.some((episode) => {
    const status = episode.job_status ?? 'unknown'
    return ACTIVE_EPISODE_STATUSES.includes(status)
  })
}

export function usePodcastEpisodes(options?: { autoRefresh?: boolean }) {
  const { autoRefresh = true } = options ?? {}

  const query = useQuery({
    queryKey: QUERY_KEYS.podcastEpisodes,
    queryFn: podcastsApi.listEpisodes,
    refetchInterval: (current) => {
      if (!autoRefresh) {
        return false
      }

      const data = current.state.data as PodcastEpisode[] | undefined
      if (!data || data.length === 0) {
        return false
      }

      return hasActiveEpisodes(data) ? 15_000 : false
    },
  })

  const episodes = useMemo(() => query.data ?? [], [query.data])

  const statusGroups = useMemo<EpisodeStatusGroups>(
    () => groupEpisodesByStatus(episodes),
    [episodes]
  )

  const statusCounts = useMemo<EpisodeStatusCounts>(
    () => ({
      total: episodes.length,
      running: statusGroups.running.length,
      completed: statusGroups.completed.length,
      failed: statusGroups.failed.length,
      pending: statusGroups.pending.length,
    }),
    [episodes.length, statusGroups]
  )

  const active = useMemo(() => hasActiveEpisodes(episodes), [episodes])

  return {
    ...query,
    episodes,
    statusGroups,
    statusCounts,
    hasActiveEpisodes: active,
  }
}

export function useDeletePodcastEpisode() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: (episodeId: string) => podcastsApi.deleteEpisode(episodeId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.podcastEpisodes })
      toast({
        title: 'Episode deleted',
        description: 'Podcast episode removed successfully.',
      })
    },
    onError: () => {
      toast({
        title: 'Failed to delete episode',
        description: 'Please try again or check the server logs for details.',
        variant: 'destructive',
      })
    },
  })
}

export function useEpisodeProfiles() {
  const query = useQuery({
    queryKey: QUERY_KEYS.episodeProfiles,
    queryFn: podcastsApi.listEpisodeProfiles,
  })

  return {
    ...query,
    episodeProfiles: query.data ?? [],
  }
}

export function useCreateEpisodeProfile() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: (payload: EpisodeProfileInput) =>
      podcastsApi.createEpisodeProfile(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.episodeProfiles })
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.podcastEpisodes })
      toast({
        title: 'Episode profile created',
        description: 'The new episode profile is ready to use.',
      })
    },
    onError: () => {
      toast({
        title: 'Failed to create episode profile',
        description: 'Double-check the form and try again.',
        variant: 'destructive',
      })
    },
  })
}

export function useUpdateEpisodeProfile() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: ({
      profileId,
      payload,
    }: {
      profileId: string
      payload: EpisodeProfileInput
    }) => podcastsApi.updateEpisodeProfile(profileId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.episodeProfiles })
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.podcastEpisodes })
      toast({
        title: 'Episode profile updated',
        description: 'Changes saved successfully.',
      })
    },
    onError: () => {
      toast({
        title: 'Failed to update episode profile',
        description: 'Please try again later.',
        variant: 'destructive',
      })
    },
  })
}

export function useDeleteEpisodeProfile() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: (profileId: string) => podcastsApi.deleteEpisodeProfile(profileId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.episodeProfiles })
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.podcastEpisodes })
      toast({
        title: 'Episode profile deleted',
        description: 'Profile removed successfully.',
      })
    },
    onError: () => {
      toast({
        title: 'Failed to delete episode profile',
        description: 'Ensure the profile is not in use and try again.',
        variant: 'destructive',
      })
    },
  })
}

export function useDuplicateEpisodeProfile() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: (profileId: string) =>
      podcastsApi.duplicateEpisodeProfile(profileId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.episodeProfiles })
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.podcastEpisodes })
      toast({
        title: 'Episode profile duplicated',
        description: 'A copy of the profile has been created.',
      })
    },
    onError: () => {
      toast({
        title: 'Failed to duplicate episode profile',
        description: 'Please try again later.',
        variant: 'destructive',
      })
    },
  })
}

export function useSpeakerProfiles(episodeProfiles?: EpisodeProfile[]) {
  const query = useQuery({
    queryKey: QUERY_KEYS.speakerProfiles,
    queryFn: podcastsApi.listSpeakerProfiles,
  })

  const speakerProfiles = useMemo(() => query.data ?? [], [query.data])

  const usage = useMemo(
    () => speakerUsageMap(speakerProfiles, episodeProfiles),
    [speakerProfiles, episodeProfiles]
  )

  return {
    ...query,
    speakerProfiles,
    usage,
  }
}

export function useCreateSpeakerProfile() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: (payload: SpeakerProfileInput) =>
      podcastsApi.createSpeakerProfile(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.speakerProfiles })
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.episodeProfiles })
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.podcastEpisodes })
      toast({
        title: 'Speaker profile created',
        description: 'The speaker profile is ready to use.',
      })
    },
    onError: () => {
      toast({
        title: 'Failed to create speaker profile',
        description: 'Double-check the form and try again.',
        variant: 'destructive',
      })
    },
  })
}

export function useUpdateSpeakerProfile() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: ({
      profileId,
      payload,
    }: {
      profileId: string
      payload: SpeakerProfileInput
    }) => podcastsApi.updateSpeakerProfile(profileId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.speakerProfiles })
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.episodeProfiles })
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.podcastEpisodes })
      toast({
        title: 'Speaker profile updated',
        description: 'Changes saved successfully.',
      })
    },
    onError: () => {
      toast({
        title: 'Failed to update speaker profile',
        description: 'Please try again later.',
        variant: 'destructive',
      })
    },
  })
}

export function useDeleteSpeakerProfile() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: (profileId: string) => podcastsApi.deleteSpeakerProfile(profileId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.speakerProfiles })
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.episodeProfiles })
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.podcastEpisodes })
      toast({
        title: 'Speaker profile deleted',
        description: 'Profile removed successfully.',
      })
    },
    onError: () => {
      toast({
        title: 'Failed to delete speaker profile',
        description: 'Ensure the profile is not in use and try again.',
        variant: 'destructive',
      })
    },
  })
}

export function useDuplicateSpeakerProfile() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: (profileId: string) =>
      podcastsApi.duplicateSpeakerProfile(profileId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.speakerProfiles })
      toast({
        title: 'Speaker profile duplicated',
        description: 'A copy of the profile has been created.',
      })
    },
    onError: () => {
      toast({
        title: 'Failed to duplicate speaker profile',
        description: 'Please try again later.',
        variant: 'destructive',
      })
    },
  })
}

export function useGeneratePodcast() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: (payload: PodcastGenerationRequest) =>
      podcastsApi.generatePodcast(payload),
    onSuccess: async (response) => {
      // Immediately refetch to show the new episode
      await queryClient.refetchQueries({ queryKey: QUERY_KEYS.podcastEpisodes })
      toast({
        title: 'Podcast generation started',
        description: `Episode "${response.episode_name}" is being created.`,
      })
    },
    onError: () => {
      toast({
        title: 'Failed to start podcast generation',
        description: 'Please try again in a moment.',
        variant: 'destructive',
      })
    },
  })
}
