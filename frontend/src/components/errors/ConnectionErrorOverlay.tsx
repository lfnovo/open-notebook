'use client'

import { useState } from 'react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { Database, Server, ChevronDown, ExternalLink } from 'lucide-react'
import { ConnectionError } from '@/lib/types/config'
import { useTranslation } from '@/lib/hooks/use-translation'

interface ConnectionErrorOverlayProps {
  error: ConnectionError
  onRetry: () => void
}

export function ConnectionErrorOverlay({
  error,
  onRetry,
}: ConnectionErrorOverlayProps) {
  const { t } = useTranslation()
  const [showDetails, setShowDetails] = useState(false)
  const isApiError = error.type === 'api-unreachable'

  return (
    <div
      className="fixed inset-0 bg-background z-50 flex items-center justify-center p-4"
      role="alert"
      aria-live="assertive"
      aria-atomic="true"
    >
      <Card className="max-w-2xl w-full p-8 space-y-6">
        {/* Error icon and title */}
        <div className="flex items-center gap-4">
          {isApiError ? (
            <Server className="w-12 h-12 text-destructive" aria-hidden="true" />
          ) : (
            <Database className="w-12 h-12 text-destructive" aria-hidden="true" />
          )}
          <div>
            <h1 className="text-2xl font-bold" id="error-title">
              {isApiError
                ? t.connectionErrors.apiTitle
                : t.connectionErrors.dbTitle}
            </h1>
            <p className="text-muted-foreground">
              {isApiError
                ? t.connectionErrors.apiDesc
                : t.connectionErrors.dbDesc}
            </p>
          </div>
        </div>

        {/* Troubleshooting instructions */}
        <div className="space-y-4 border-l-4 border-primary pl-4">
          <h2 className="font-semibold">{t.connectionErrors.troubleshooting}</h2>
          <ul className="list-disc list-inside space-y-2 text-sm">
            {isApiError ? (
              <>
                <li>{t.connectionErrors.apiUnreachable1}</li>
                <li>{t.connectionErrors.apiUnreachable2}</li>
                <li>{t.connectionErrors.apiUnreachable3}</li>
              </>
            ) : (
              <>
                <li>{t.connectionErrors.dbFailed1}</li>
                <li>{t.connectionErrors.dbFailed2}</li>
                <li>{t.connectionErrors.dbFailed3}</li>
              </>
            )}
          </ul>

          <h2 className="font-semibold mt-4">{t.connectionErrors.quickFixes}</h2>
          {isApiError ? (
            <div className="space-y-2 text-sm bg-muted p-4 rounded">
              <p className="font-medium">{t.connectionErrors.setApiUrl}</p>
              <code className="block bg-background p-2 rounded text-xs">
                # {t.connectionErrors.dockerLabel}:
                <br />
                docker run -e API_URL=http://your-host:5055 ...
                <br />
                <br />
                # {t.connectionErrors.localDevLabel}:
                <br />
                API_URL=http://localhost:5055
              </code>
            </div>
          ) : (
            <div className="space-y-2 text-sm bg-muted p-4 rounded">
              <p className="font-medium">{t.connectionErrors.checkSurreal}</p>
              <code className="block bg-background p-2 rounded text-xs">
                # {t.connectionErrors.dockerLabel}:
                <br />
                docker compose ps | grep surrealdb
                <br />
                docker compose logs surrealdb
              </code>
            </div>
          )}
        </div>

        {/* Documentation link */}
        <div className="text-sm">
          <p>{t.connectionErrors.seeDocumentation}</p>
          <a
            href="https://github.com/lfnovo/open-notebook"
            target="_blank"
            rel="noopener noreferrer"
            className="text-primary hover:underline inline-flex items-center gap-1"
          >
            {t.connectionErrors.docLink}
            <ExternalLink className="w-4 h-4" />
          </a>
        </div>

        {/* Collapsible technical details */}
        {error.details && (
          <Collapsible open={showDetails} onOpenChange={setShowDetails}>
            <CollapsibleTrigger asChild>
              <Button variant="ghost" size="sm" className="w-full justify-between">
                <span>{t.connectionErrors.showTechnical}</span>
                <ChevronDown
                  className={`w-4 h-4 transition-transform ${
                    showDetails ? 'rotate-180' : ''
                  }`}
                />
              </Button>
            </CollapsibleTrigger>
            <CollapsibleContent className="pt-4">
              <div className="space-y-2 text-sm bg-muted p-4 rounded font-mono">
                {error.details.attemptedUrl && (
                  <div>
                    <strong>{t.connectionErrors.attemptedUrl}:</strong> {error.details.attemptedUrl}
                  </div>
                )}
                {error.details.message && (
                  <div>
                    <strong>{t.connectionErrors.message}:</strong> {error.details.message}
                  </div>
                )}
                {error.details.technicalMessage && (
                  <div>
                    <strong>{t.connectionErrors.technicalDetails}:</strong>{' '}
                    {error.details.technicalMessage}
                  </div>
                )}
                {error.details.stack && (
                  <div>
                    <strong>{t.connectionErrors.stackTrace}:</strong>
                    <pre className="mt-2 overflow-x-auto text-xs">
                      {error.details.stack}
                    </pre>
                  </div>
                )}
              </div>
            </CollapsibleContent>
          </Collapsible>
        )}

        {/* Retry button */}
        <div className="pt-4 border-t">
          <Button onClick={onRetry} className="w-full" size="lg">
            {t.connectionErrors.retryLabel}
          </Button>
          <p className="text-xs text-muted-foreground text-center mt-2">
            {t.connectionErrors.retryHint}
          </p>
        </div>
      </Card>
    </div>
  )
}
