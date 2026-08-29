'use client'

import { useEffect, useRef } from 'react'
import { useSearchParams, useRouter, usePathname } from 'next/navigation'
import { HardDrive, CheckCircle2, Loader2 } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { useTranslation } from '@/lib/hooks/use-translation'
import { useToast } from '@/lib/hooks/use-toast'
import { useDriveStatus, useConnectDrive, useDisconnectDrive } from '@/lib/hooks/use-drive'

/**
 * Google Drive connection card for the Settings page. The connect button
 * does a full-page redirect (not an awaited API call) to Google's consent
 * screen; the OAuth callback (api/routers/drive.py) redirects the browser
 * back here with ?drive=connected or ?drive=error&message=... - this
 * component refetches status on mount and reacts to those query params.
 */
export function DriveConnectionCard() {
  const { t } = useTranslation()
  const { toast } = useToast()
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const { data: status, isLoading, refetch } = useDriveStatus()
  const connect = useConnectDrive()
  const disconnect = useDisconnectDrive()
  const handledRedirectRef = useRef(false)

  useEffect(() => {
    if (!searchParams || handledRedirectRef.current) return
    const drive = searchParams.get('drive')
    if (!drive) return
    handledRedirectRef.current = true

    if (drive === 'connected') {
      toast({ title: t('drive.connected') })
      refetch()
    } else if (drive === 'error') {
      const message = searchParams.get('message')
      toast({
        title: t('drive.connectFailed'),
        description: message || undefined,
        variant: 'destructive',
      })
    }

    // Strip the drive= params from the URL so a page refresh doesn't
    // re-trigger the toast.
    const params = new URLSearchParams(searchParams.toString())
    params.delete('drive')
    params.delete('message')
    const query = params.toString()
    router.replace(query ? `${pathname}?${query}` : pathname)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams])

  const connected = status?.connected ?? false

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <HardDrive className="h-4 w-4" />
          {t('drive.title')}
        </CardTitle>
        <CardDescription>{t('drive.description')}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {isLoading ? (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            {t('common.loading')}
          </div>
        ) : connected ? (
          <Alert className="border-fern/30 bg-fern-tint">
            <CheckCircle2 className="h-4 w-4 text-fern" />
            <AlertDescription className="flex flex-col gap-3 text-fern sm:flex-row sm:items-center sm:justify-between">
              <span>
                {status?.account_email
                  ? t('drive.connectedAs', { email: status.account_email })
                  : t('drive.connectedNoEmail')}
              </span>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => disconnect.mutate()}
                disabled={disconnect.isPending}
                className="shrink-0 border-fern text-fern hover:bg-fern-tint"
              >
                {disconnect.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  t('drive.disconnect')
                )}
              </Button>
            </AlertDescription>
          </Alert>
        ) : (
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-sm text-muted-foreground">{t('drive.notConnected')}</p>
            <Button
              type="button"
              onClick={() => connect.mutate()}
              disabled={connect.isPending}
              className="shrink-0"
            >
              {connect.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                t('drive.connect')
              )}
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
