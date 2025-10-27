'use client'

import { useEffect } from 'react'
import { toast } from 'sonner'
import { getConfig } from '@/lib/config'

/**
 * Hook to check for version updates and display notification.
 * Should be called once per session in the dashboard layout.
 */
export function useVersionCheck() {
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
            toast.info(`Version ${config.latestVersion} available`, {
              description: 'A new version of Open Notebook is available.',
              duration: Infinity, // No auto-dismiss - user must manually dismiss
              closeButton: true, // Show close button for dismissing
              action: {
                label: 'View on GitHub',
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

            console.log(
              `🔔 [Version Check] Update available: ${config.version} → ${config.latestVersion}`
            )
          } else {
            console.log(
              `🔕 [Version Check] Notification dismissed for version ${config.latestVersion}`
            )
          }
        } else if (config.latestVersion) {
          console.log(
            `✅ [Version Check] Running latest version: ${config.version}`
          )
        } else {
          console.log(
            `⚠️ [Version Check] Could not check for updates (offline or GitHub unavailable)`
          )
        }
      } catch (error) {
        console.error('❌ [Version Check] Failed to check version:', error)
        // Silently fail - don't disrupt user experience
      }
    }

    // Run version check
    checkVersion()
  }, []) // Run once on mount
}
