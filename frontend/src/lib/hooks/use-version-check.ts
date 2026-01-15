import { useEffect, useRef, useState } from 'react'
import { toast } from 'sonner'
import { getConfig } from '@/lib/config'
import { AppConfig } from '@/lib/types/config'
import { useTranslation } from '@/lib/hooks/use-translation'

/**
 * Hook to check for version updates and display notification.
 * Should be called once per session in the dashboard layout.
 */
export function useVersionCheck() {
  const { t } = useTranslation()
  const hasFetched = useRef(false)
  const [serverConfig, setServerConfig] = useState<AppConfig | null>(null)

  // 1. Fetch config only once
  useEffect(() => {
    if (!hasFetched.current) {
      hasFetched.current = true
      getConfig()
        .then(config => {
           setServerConfig(config)
           if (process.env.NODE_ENV === 'development') {
             if (config.hasUpdate) {
                console.log(`🔔 [Version Check] Update available: ${config.version} → ${config.latestVersion}`)
             } else {
                console.log(`✅ [Version Check] Running latest version: ${config.version}`)
             }
           }
        })
        .catch(err => {
          if (process.env.NODE_ENV === 'development') {
            console.error('❌ [Version Check] Failed to check version:', err)
          }
        })
    }
  }, [])

  // 2. Display/Update notification when config or language changes
  useEffect(() => {
    if (!serverConfig?.hasUpdate || !serverConfig.latestVersion) return

    // Check if user has dismissed this version in this session
    const dismissKey = `version_notification_dismissed_${serverConfig.latestVersion}`
    const isDismissed = sessionStorage.getItem(dismissKey)

    if (!isDismissed) {
      // Use a stable ID to update the existing toast instead of creating duplicates
      const toastId = `version-update-${serverConfig.latestVersion}`

      toast.info(t.advanced.updateAvailable.replace('{version}', serverConfig.latestVersion), {
        id: toastId, // Stable ID allows content update
        description: t.advanced.updateAvailableDesc,
        duration: Infinity,
        closeButton: true,
        action: {
          label: t.advanced.viewOnGithub,
          onClick: () => {
             window.open(
               'https://github.com/lfnovo/open-notebook',
               '_blank',
               'noopener,noreferrer'
             )
          },
        },
        onDismiss: () => {
          sessionStorage.setItem(dismissKey, 'true')
        },
      })
    }
  }, [serverConfig, t]) // Re-run when config is loaded or language (t) changes
}
