export type EpisodeStatus =
  | 'running'
  | 'processing'
  | 'completed'
  | 'failed'
  | 'error'
  | 'pending'
  | 'submitted'
  | 'unknown'

export interface EpisodeProfile {
  id: string
  name: string
  description: string
  speaker_config: string
  outline_provider: string
  outline_model: string
  transcript_provider: string
  transcript_model: string
  default_briefing: string
  num_segments: number
}

export interface SpeakerVoiceConfig {
  name: string
  voice_id: string
  backstory: string
  personality: string
}

export interface SpeakerProfile {
  id: string
  name: string
  description: string
  tts_provider: string
  tts_model: string
  speakers: SpeakerVoiceConfig[]
}

export interface PodcastEpisode {
  id: string
  name: string
  episode_profile: EpisodeProfile
  speaker_profile: SpeakerProfile
  briefing: string
  audio_file?: string | null
  audio_url?: string | null
  transcript?: Record<string, unknown> | null
  outline?: Record<string, unknown> | null
  created?: string | null
  job_status?: EpisodeStatus | null
}

export interface PodcastGenerationRequest {
  episode_profile: string
  speaker_profile: string
  episode_name: string
  content?: string
  notebook_id?: string
  briefing_suffix?: string | null
}

export interface PodcastGenerationResponse {
  job_id: string
  status: string
  message: string
  episode_profile: string
  episode_name: string
}

export type EpisodeStatusGroup = 'running' | 'completed' | 'failed' | 'pending'

export type EpisodeStatusGroups = Record<EpisodeStatusGroup, PodcastEpisode[]>

export const ACTIVE_EPISODE_STATUSES: EpisodeStatus[] = [
  'running',
  'processing',
  'pending',
  'submitted',
]

export const FAILED_EPISODE_STATUSES: EpisodeStatus[] = ['failed', 'error']

export function groupEpisodesByStatus(episodes: PodcastEpisode[]): EpisodeStatusGroups {
  return episodes.reduce<EpisodeStatusGroups>(
    (groups, episode) => {
      const status = episode.job_status || 'unknown'

      if (status === 'running' || status === 'processing') {
        groups.running.push(episode)
        return groups
      }

      if (status === 'completed') {
        groups.completed.push(episode)
        return groups
      }

      if (FAILED_EPISODE_STATUSES.includes(status)) {
        groups.failed.push(episode)
        return groups
      }

      groups.pending.push(episode)
      return groups
    },
    { running: [], completed: [], failed: [], pending: [] }
  )
}

export function speakerUsageMap(
  speakerProfiles: SpeakerProfile[] | undefined,
  episodeProfiles: EpisodeProfile[] | undefined
): Record<string, number> {
  if (!speakerProfiles || !episodeProfiles) {
    return {}
  }

  const usage: Record<string, number> = {}

  for (const profile of speakerProfiles) {
    usage[profile.name] = 0
  }

  for (const episodeProfile of episodeProfiles) {
    const key = episodeProfile.speaker_config
    if (key in usage) {
      usage[key] += 1
    }
  }

  return usage
}
