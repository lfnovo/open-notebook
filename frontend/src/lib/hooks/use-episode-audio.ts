import { useEffect, useState } from 'react'

import apiClient from '@/lib/api/client'
import { resolvePodcastAssetUrl } from '@/lib/api/podcasts'
import { useTranslation } from '@/lib/hooks/use-translation'
import type { PodcastEpisode } from '@/lib/types/podcasts'

/**
 * Resolves a playable audio src for an episode. Protected endpoints are
 * fetched through apiClient (auth header) and exposed as a blob URL.
 */
export function useEpisodeAudio(
  episode: Pick<PodcastEpisode, 'audio_url' | 'audio_file'>,
  enabled = true
) {
  const { t } = useTranslation()
  const [audioSrc, setAudioSrc] = useState<string | undefined>()
  const [audioError, setAudioError] = useState<string | null>(null)

  useEffect(() => {
    let revokeUrl: string | undefined
    let cancelled = false
    setAudioError(null)
    // Never keep a (about to be revoked) previous URL while the next one loads.
    setAudioSrc(undefined)

    if (!enabled) {
      return
    }

    const load = async () => {
      const directAudioUrl = await resolvePodcastAssetUrl(episode.audio_url ?? episode.audio_file)

      if (cancelled) return

      if (!directAudioUrl || !episode.audio_url) {
        setAudioSrc(directAudioUrl)
        return
      }

      try {
        // apiClient attaches the auth header; directAudioUrl is absolute so
        // the dynamic baseURL is ignored.
        const response = await apiClient.get<Blob>(directAudioUrl, {
          responseType: 'blob',
        })
        if (cancelled) return
        revokeUrl = URL.createObjectURL(response.data)
        setAudioSrc(revokeUrl)
      } catch (error) {
        if (cancelled) return
        console.error('Unable to load podcast audio', error)
        setAudioError(t('podcasts.audioUnavailable'))
        setAudioSrc(undefined)
      }
    }

    void load()

    return () => {
      cancelled = true
      if (revokeUrl) {
        URL.revokeObjectURL(revokeUrl)
      }
    }
  }, [episode.audio_url, episode.audio_file, enabled, t])

  return { audioSrc, audioError }
}
