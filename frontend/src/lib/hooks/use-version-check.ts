'use client'

import { useEffect, useRef } from 'react'
import { toast } from 'sonner'
import { getConfig } from '@/lib/config'
import { useTranslation } from '@/lib/hooks/use-translation'

/**
 * Hook to check for version updates and display notification.
 * Should be called once per session in the dashboard layout.
 */
export function useVersionCheck() {
  const { t } = useTranslation()
  const hasChecked = useRef(false)

  useEffect(() => {
    const checkVersion = async () => {
      try {
        const config = await getConfig()

        // Only show notification if update is available
        if (config.hasUpdate && config.latestVersion) {
          // Check if user has dismissed this version in this session
          const dismissKey = `version_notification_dismissed_${config.latestVersion}`
          const isDismissed = sessionStorage.getItem(dismissKey)

          if (!isDismissed) {
            // Show persistent toast notification
            toast.info(t.advanced.updateAvailable.replace('{version}', config.latestVersion), {
              description: t.advanced.updateAvailableDesc,
              duration: Infinity, // No auto-dismiss - user must manually dismiss
              closeButton: true, // Show close button for dismissing
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
                // Store dismissal in session storage
                sessionStorage.setItem(dismissKey, 'true')
              },
            })

            if (process.env.NODE_ENV === 'development') {
              console.log(
                `🔔 [Version Check] Update available: ${config.version} → ${config.latestVersion}`
              )
            }
          } else {
            if (process.env.NODE_ENV === 'development') {
              console.log(
                `🔕 [Version Check] Notification dismissed for version ${config.latestVersion}`
              )
            }
          }
        } else if (config.latestVersion) {
          if (process.env.NODE_ENV === 'development') {
            console.log(
              `✅ [Version Check] Running latest version: ${config.version}`
            )
          }
        } else {
          if (process.env.NODE_ENV === 'development') {
            console.log(
              `⚠️ [Version Check] Could not check for updates (offline or GitHub unavailable)`
            )
          }
        }
      } catch (error) {
        if (process.env.NODE_ENV === 'development') {
          console.error('❌ [Version Check] Failed to check version:', error)
        }
        // Silently fail - don't disrupt user experience
      }
    }

    // Run version check
    if (!hasChecked.current) {
        hasChecked.current = true
        checkVersion()
    }
  }, []) // Run once on mount
}
