'use client'

import { useMemo, useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { useTranslation } from '@/lib/hooks/use-translation'
import { useTeams } from '@/lib/hooks/use-teams'
import {
  useCreateExternalApiConnection,
  useCreateExternalApiSource,
  useCreateExternalApiTeamGrant,
  useExternalApiConnections,
  useExternalApiSources,
  useTestExternalApiConnection,
} from '@/lib/hooks/use-external-api'
import type { ExternalApiCapability, ExternalApiConnectionTarget } from '@/lib/api/external-api'
import { CheckCircle2, Plug, RefreshCw, ShieldCheck } from 'lucide-react'

const SOURCE_CAPABILITIES: ExternalApiCapability[] = ['search', 'fetch']
const OUTPUT_CAPABILITIES: ExternalApiCapability[] = ['output']

const getConnectionCapabilities = (targetType: ExternalApiConnectionTarget | undefined): ExternalApiCapability[] =>
  targetType === 'output' ? OUTPUT_CAPABILITIES : SOURCE_CAPABILITIES

export default function ExternalApiSettingsPage() {
  const { t } = useTranslation()
  const connections = useExternalApiConnections()
  const sources = useExternalApiSources()
  const teams = useTeams()
  const createConnection = useCreateExternalApiConnection()
  const createSource = useCreateExternalApiSource()
  const createGrant = useCreateExternalApiTeamGrant()
  const testConnection = useTestExternalApiConnection()

  const [connectionName, setConnectionName] = useState('')
  const [connectionTargetType, setConnectionTargetType] = useState<ExternalApiConnectionTarget>('source')
  const [baseUrl, setBaseUrl] = useState('')
  const [apiKey, setApiKey] = useState('')
  const [timeoutSeconds, setTimeoutSeconds] = useState('30')

  const [sourceConnectionId, setSourceConnectionId] = useState('')
  const [sourceName, setSourceName] = useState('')
  const [sourceKey, setSourceKey] = useState('')
  const [sourceDescription, setSourceDescription] = useState('')

  const [grantSourceId, setGrantSourceId] = useState('')
  const [grantTeamId, setGrantTeamId] = useState('')
  const [grantQuota, setGrantQuota] = useState('100')

  const connectionItems = useMemo(() => connections.data?.items ?? [], [connections.data?.items])
  const sourceItems = useMemo(
    () =>
      (sources.data?.items ?? []).filter((source) =>
        source.capabilities.some((capability) => SOURCE_CAPABILITIES.includes(capability))
      ),
    [sources.data?.items]
  )
  const sourceConnectionItems = useMemo(
    () => connectionItems.filter((connection) => (connection.target_type ?? 'source') === 'source'),
    [connectionItems]
  )
  const teamItems = useMemo(
    () => (teams.data?.items ?? []).filter((team) => team.type === 'workspace'),
    [teams.data?.items]
  )

  const isLoading = connections.isLoading || sources.isLoading || teams.isLoading

  const handleCreateConnection = async (event: React.FormEvent) => {
    event.preventDefault()
    await createConnection.mutateAsync({
      name: connectionName,
      target_type: connectionTargetType,
      base_url: baseUrl,
      api_key: apiKey,
      timeout_seconds: Number(timeoutSeconds) || 30,
      enabled: true,
    })
    setConnectionName('')
    setConnectionTargetType('source')
    setBaseUrl('')
    setApiKey('')
    setTimeoutSeconds('30')
  }

  const handleCreateSource = async (event: React.FormEvent) => {
    event.preventDefault()
    await createSource.mutateAsync({
      connection_id: sourceConnectionId,
      name: sourceName,
      key: sourceKey,
      description: sourceDescription || undefined,
      capabilities: SOURCE_CAPABILITIES,
      enabled: true,
    })
    setSourceName('')
    setSourceKey('')
    setSourceDescription('')
  }

  const handleCreateGrant = async (event: React.FormEvent) => {
    event.preventDefault()
    await createGrant.mutateAsync({
      sourceId: grantSourceId,
      data: {
        team_id: grantTeamId,
        monthly_request_quota: Number(grantQuota) || 0,
        enabled: true,
      },
    })
    setGrantQuota('100')
  }

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="p-6">
        <div className="max-w-6xl">
          <div className="mb-6 flex items-center justify-between gap-4">
            <div>
              <h1 className="text-2xl font-semibold tracking-normal">{t.navigation.externalApi}</h1>
              <p className="text-sm text-muted-foreground">
                {t.externalApi.description}
              </p>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                connections.refetch()
                sources.refetch()
                teams.refetch()
              }}
            >
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>

          {isLoading ? (
            <div className="flex justify-center py-12">
              <LoadingSpinner />
            </div>
          ) : (
            <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
              <div className="flex flex-col gap-6">
                <Card>
                  <CardHeader>
                    <CardTitle>{t.externalApi.connections}</CardTitle>
                    <CardDescription>{t.externalApi.connectionsDescription}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="flex flex-col gap-3">
                      {connectionItems.length === 0 ? (
                        <p className="text-sm text-muted-foreground">{t.externalApi.noConnections}</p>
                      ) : (
                        connectionItems.map((connection) => (
                          <div key={connection.id} className="rounded-md border p-3">
                            <div className="flex items-start justify-between gap-3">
                              <div className="min-w-0">
                                <div className="flex items-center gap-2">
                                  <Plug className="h-4 w-4 text-muted-foreground" />
                                  <h3 className="font-medium">{connection.name}</h3>
                                  <Badge variant={connection.enabled ? 'secondary' : 'outline'}>
                                    {connection.enabled ? t.externalApi.enabled : t.externalApi.disabled}
                                  </Badge>
                                  <Badge variant="outline">
                                    {(connection.target_type ?? 'source') === 'output'
                                      ? t.externalApi.outputArtifactApi
                                      : t.externalApi.sourceApi}
                                  </Badge>
                                  {connection.api_key_configured && (
                                    <Badge variant="outline">
                                      <ShieldCheck className="h-3 w-3" />
                                      {t.externalApi.keyStored}
                                    </Badge>
                                  )}
                                </div>
                                <p className="mt-1 truncate text-sm text-muted-foreground">{connection.base_url}</p>
                                <div className="mt-2 flex flex-wrap gap-1">
                                  {getConnectionCapabilities(connection.target_type).map((capability) => (
                                    <Badge key={capability} variant="secondary">{capability}</Badge>
                                  ))}
                                </div>
                              </div>
                              <Button
                                variant="outline"
                                size="sm"
                                disabled={testConnection.isPending}
                                onClick={() => testConnection.mutate(connection.id)}
                              >
                                {t.externalApi.test}
                              </Button>
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle>{t.externalApi.sources}</CardTitle>
                    <CardDescription>{t.externalApi.sourcesDescription}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="flex flex-col gap-3">
                      {sourceItems.length === 0 ? (
                        <p className="text-sm text-muted-foreground">{t.externalApi.noSources}</p>
                      ) : (
                        sourceItems.map((source) => (
                          <div key={source.id} className="rounded-md border p-3">
                            <div className="flex items-start justify-between gap-3">
                              <div>
                                <h3 className="font-medium">{source.name}</h3>
                                <p className="text-xs text-muted-foreground">{source.key}</p>
                                {source.description && (
                                  <p className="mt-1 text-sm text-muted-foreground">{source.description}</p>
                                )}
                              </div>
                              <div className="flex flex-wrap justify-end gap-1">
                                {source.capabilities
                                  .filter((capability) => SOURCE_CAPABILITIES.includes(capability as ExternalApiCapability))
                                  .map((capability) => (
                                  <Badge key={capability} variant="secondary">{capability}</Badge>
                                ))}
                              </div>
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  </CardContent>
                </Card>
              </div>

              <div className="flex flex-col gap-6">
                <Card>
                  <CardHeader>
                    <CardTitle>{t.externalApi.addConnection}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <form onSubmit={handleCreateConnection} className="flex flex-col gap-3">
                      <div className="flex flex-col gap-2">
                        <Label htmlFor="connection-name">{t.common.name}</Label>
                        <Input id="connection-name" value={connectionName} onChange={(event) => setConnectionName(event.target.value)} required />
                      </div>
                      <div className="flex flex-col gap-2">
                        <Label>{t.externalApi.apiTarget}</Label>
                        <Select value={connectionTargetType} onValueChange={(value) => setConnectionTargetType(value as ExternalApiConnectionTarget)}>
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="source">{t.externalApi.sourceApi}</SelectItem>
                            <SelectItem value="output">{t.externalApi.outputArtifactApi}</SelectItem>
                          </SelectContent>
                        </Select>
                        <p className="text-xs text-muted-foreground">
                          {connectionTargetType === 'output'
                            ? t.externalApi.outputApiDescription
                            : t.externalApi.sourceApiDescription}
                        </p>
                        <div className="flex flex-wrap gap-1">
                          {getConnectionCapabilities(connectionTargetType).map((capability) => (
                            <Badge key={capability} variant="secondary">{capability}</Badge>
                          ))}
                        </div>
                      </div>
                      <div className="flex flex-col gap-2">
                        <Label htmlFor="connection-url">{t.externalApi.baseUrl}</Label>
                        <Input id="connection-url" value={baseUrl} onChange={(event) => setBaseUrl(event.target.value)} placeholder="https://provider.example.com" required />
                      </div>
                      <div className="flex flex-col gap-2">
                        <Label htmlFor="connection-key">{t.externalApi.apiKey}</Label>
                        <Input id="connection-key" type="password" value={apiKey} onChange={(event) => setApiKey(event.target.value)} required />
                      </div>
                      <div className="flex flex-col gap-2">
                        <Label htmlFor="connection-timeout">{t.externalApi.timeoutSeconds}</Label>
                        <Input id="connection-timeout" type="number" min="1" max="300" value={timeoutSeconds} onChange={(event) => setTimeoutSeconds(event.target.value)} />
                      </div>
                      <Button type="submit" disabled={createConnection.isPending}>
                        {createConnection.isPending ? t.common.saving : t.common.save}
                      </Button>
                    </form>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle>{t.externalApi.addSource}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <form onSubmit={handleCreateSource} className="flex flex-col gap-3">
                      <div className="flex flex-col gap-2">
                        <Label>{t.externalApi.connection}</Label>
                        <Select value={sourceConnectionId} onValueChange={setSourceConnectionId}>
                          <SelectTrigger>
                            <SelectValue placeholder={t.externalApi.selectConnection} />
                          </SelectTrigger>
                          <SelectContent>
                            {sourceConnectionItems.map((connection) => (
                              <SelectItem key={connection.id} value={connection.id}>{connection.name}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        {sourceConnectionItems.length === 0 && (
                          <p className="text-xs text-muted-foreground">{t.externalApi.noSourceConnections}</p>
                        )}
                      </div>
                      <div className="flex flex-col gap-2">
                        <Label htmlFor="source-name">{t.common.name}</Label>
                        <Input id="source-name" value={sourceName} onChange={(event) => setSourceName(event.target.value)} required />
                      </div>
                      <div className="flex flex-col gap-2">
                        <Label htmlFor="source-key">{t.externalApi.sourceKey}</Label>
                        <Input id="source-key" value={sourceKey} onChange={(event) => setSourceKey(event.target.value)} placeholder="paper_search" required />
                      </div>
                      <div className="flex flex-col gap-2">
                        <Label htmlFor="source-desc">{t.common.description}</Label>
                        <Textarea id="source-desc" value={sourceDescription} onChange={(event) => setSourceDescription(event.target.value)} rows={3} />
                      </div>
                      <div className="flex flex-col gap-2">
                        <Label>{t.externalApi.capabilities}</Label>
                        <div className="flex flex-wrap gap-1">
                          {SOURCE_CAPABILITIES.map((capability) => (
                            <Badge key={capability} variant="secondary">{capability}</Badge>
                          ))}
                        </div>
                      </div>
                      <Button type="submit" disabled={createSource.isPending || !sourceConnectionId || sourceConnectionItems.length === 0}>
                        {createSource.isPending ? t.common.saving : t.common.save}
                      </Button>
                    </form>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle>{t.externalApi.grantToTeam}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <form onSubmit={handleCreateGrant} className="flex flex-col gap-3">
                      <div className="flex flex-col gap-2">
                        <Label>{t.common.source}</Label>
                        <Select value={grantSourceId} onValueChange={setGrantSourceId}>
                          <SelectTrigger>
                            <SelectValue placeholder={t.externalApi.selectSource} />
                          </SelectTrigger>
                          <SelectContent>
                            {sourceItems.map((source) => (
                              <SelectItem key={source.id} value={source.id}>{source.name}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="flex flex-col gap-2">
                        <Label>{t.externalApi.team}</Label>
                        <Select value={grantTeamId} onValueChange={setGrantTeamId}>
                          <SelectTrigger>
                            <SelectValue placeholder={t.externalApi.selectTeam} />
                          </SelectTrigger>
                          <SelectContent>
                            {teamItems.map((team) => (
                              <SelectItem key={team.id} value={team.id}>{team.name}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="flex flex-col gap-2">
                        <Label htmlFor="grant-quota">{t.externalApi.monthlyRequestQuota}</Label>
                        <Input id="grant-quota" type="number" min="0" value={grantQuota} onChange={(event) => setGrantQuota(event.target.value)} />
                      </div>
                      <Button type="submit" disabled={createGrant.isPending || !grantSourceId || !grantTeamId}>
                        {createGrant.isPending ? t.common.saving : t.externalApi.grant}
                      </Button>
                    </form>
                  </CardContent>
                </Card>

                {testConnection.data && (
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <CheckCircle2 className="h-4 w-4" />
                        {t.externalApi.lastTest}
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <p className="text-sm">
                        {testConnection.data.ok ? t.externalApi.connectionSucceeded : testConnection.data.message || t.externalApi.connectionFailed}
                      </p>
                    </CardContent>
                  </Card>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
