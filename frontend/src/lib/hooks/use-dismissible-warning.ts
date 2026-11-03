'use client'

import { useCallback, useEffect, useState } from 'react'
import { getConfig } from '@/lib/config'

export function useDismissibleWarning(storageKey: string, active: boolean) {
  const [dismissed, setDismissed] = useState(false)
  const [buildId, setBuildId] = useState<string | null>(null)

  useEffect(() => {
    if (!active) {
      setBuildId(null)
      return
    }
    let mounted = true
    getConfig()
      .then(config => {
        if (mounted) setBuildId(config.buildTime || config.version)
      })
      .catch(() => {
        if (mounted) setBuildId('unknown')
      })
    return () => {
      mounted = false
    }
  }, [active])

  useEffect(() => {
    if (!buildId) return
    const versionedKey = `${storageKey}:${buildId}`
    if (!active) {
      window.localStorage.removeItem(versionedKey)
      setDismissed(false)
      return
    }

    setDismissed(window.localStorage.getItem(versionedKey) === 'dismissed')
  }, [active, buildId, storageKey])

  const dismiss = useCallback(() => {
    if (!buildId) return
    window.localStorage.setItem(`${storageKey}:${buildId}`, 'dismissed')
    setDismissed(true)
  }, [buildId, storageKey])

  return { dismissed, dismiss }
}
