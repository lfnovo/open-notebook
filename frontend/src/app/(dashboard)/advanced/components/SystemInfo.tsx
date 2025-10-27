'use client'

import { useEffect, useState } from 'react'
import { Card } from '@/components/ui/card'
import { getConfig } from '@/lib/config'
import { Badge } from '@/components/ui/badge'

export function SystemInfo() {
  const [config, setConfig] = useState<{
    version: string
    latestVersion?: string | null
    hasUpdate?: boolean
  } | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const loadConfig = async () => {
      try {
        const cfg = await getConfig()
        setConfig(cfg)
      } catch (error) {
        console.error('Failed to load config:', error)
      } finally {
        setIsLoading(false)
      }
    }

    loadConfig()
  }, [])

  if (isLoading) {
    return (
      <Card className="p-6">
        <div className="space-y-4">
          <h2 className="text-xl font-semibold">System Information</h2>
          <div className="text-sm text-muted-foreground">Loading...</div>
        </div>
      </Card>
    )
  }

  return (
    <Card className="p-6">
      <div className="space-y-4">
        <h2 className="text-xl font-semibold">System Information</h2>

        <div className="space-y-3">
          {/* Current Version */}
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">Current Version</span>
            <Badge variant="outline">{config?.version || 'Unknown'}</Badge>
          </div>

          {/* Latest Version */}
          {config?.latestVersion && (
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">Latest Version</span>
              <Badge variant="outline">{config.latestVersion}</Badge>
            </div>
          )}

          {/* Update Status */}
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">Status</span>
            {config?.hasUpdate ? (
              <Badge variant="destructive">
                Update Available
              </Badge>
            ) : config?.latestVersion ? (
              <Badge variant="outline" className="text-green-600 border-green-600">
                Up to Date
              </Badge>
            ) : (
              <Badge variant="outline" className="text-muted-foreground">
                Unknown
              </Badge>
            )}
          </div>

          {/* GitHub Repository Link */}
          {config?.hasUpdate && (
            <div className="pt-2 border-t">
              <a
                href="https://github.com/lfnovo/open-notebook"
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-primary hover:underline inline-flex items-center gap-1"
              >
                View on GitHub
                <svg
                  className="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                  />
                </svg>
              </a>
            </div>
          )}

          {/* Version Check Failed Message */}
          {!config?.latestVersion && config?.version && (
            <div className="pt-2 text-xs text-muted-foreground">
              Unable to check for updates. GitHub may be unreachable.
            </div>
          )}
        </div>
      </div>
    </Card>
  )
}
