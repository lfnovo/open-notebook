'use client'

import { useEffect, useMemo, useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
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
  useExternalApiTeamGrants,
  useTestExternalApiConnection,
} from '@/lib/hooks/use-external-api'
import type {
  ExternalApiCapability,
  ExternalApiConnection,
  ExternalApiConnectionTestResult,
  ExternalApiConnectionTarget,
  ExternalApiSource,
  ExternalApiTeamGrant,
} from '@/lib/api/external-api'
import {
  Check,
  ChevronDown,
  FileSearch,
  KeyRound,
  Loader2,
  Plus,
  Plug,
  RefreshCw,
  UsersRound,
  WandSparkles,
  X,
} from 'lucide-react'

const SOURCE_CAPABILITIES: ExternalApiCapability[] = ['search', 'fetch']
const OUTPUT_CAPABILITIES: ExternalApiCapability[] = ['output']

const getConnectionCapabilities = (targetType: ExternalApiConnectionTarget | undefined): ExternalApiCapability[] =>
  targetType === 'output' ? OUTPUT_CAPABILITIES : SOURCE_CAPABILITIES

const formatJson = (value: unknown) => JSON.stringify(value, null, 2)

export default function ExternalApiSettingsPage() {
  const { t } = useTranslation()
  const connections = useExternalApiConnections()
  const sources = useExternalApiSources()
  const teams = useTeams()
  const testConnection = useTestExternalApiConnection()

  const [connectionDialogTarget, setConnectionDialogTarget] = useState<ExternalApiConnectionTarget | null>(null)

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
  const outputConnectionItems = useMemo(
    () => connectionItems.filter((connection) => (connection.target_type ?? 'source') === 'output'),
    [connectionItems]
  )
  const sourceByConnectionId = useMemo(() => {
    const map = new Map<string, ExternalApiSource>()
    sourceItems.forEach((source) => map.set(source.connection_id, source))
    return map
  }, [sourceItems])
  const teamItems = useMemo(
    () => (teams.data?.items ?? []).filter((team) => team.type === 'workspace'),
    [teams.data?.items]
  )

  const activeConnectionCount = connectionItems.filter((connection) => connection.enabled).length
  const isLoading = connections.isLoading || sources.isLoading || teams.isLoading

  const capabilityLabel = (capability: ExternalApiCapability) => {
    if (capability === 'search') return t.externalApi.capabilitySearch
    if (capability === 'fetch') return t.externalApi.capabilityFetch
    return t.externalApi.capabilityOutput
  }

  const refreshAll = () => {
    connections.refetch()
    sources.refetch()
    teams.refetch()
  }

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="p-6">
        <div className="max-w-7xl">
          <div className="mb-6 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <h1 className="text-2xl font-semibold tracking-normal">{t.navigation.externalApi}</h1>
              <p className="text-sm text-muted-foreground">{t.externalApi.description}</p>
            </div>
            <Button variant="outline" size="sm" onClick={refreshAll}>
              <RefreshCw className="h-4 w-4" />
              {t.common.refresh}
            </Button>
          </div>

          {isLoading ? (
            <div className="flex justify-center py-12">
              <LoadingSpinner />
            </div>
          ) : (
            <div className="flex flex-col gap-6">
              <div className="grid gap-3 md:grid-cols-3">
                <OverviewTile
                  icon={<Plug className="h-5 w-5" />}
                  label={t.externalApi.connectionOverview}
                  value={`${activeConnectionCount}/${connectionItems.length}`}
                  detail={`${sourceConnectionItems.length} ${t.externalApi.sourceApi} / ${outputConnectionItems.length} ${t.externalApi.outputArtifactApi}`}
                />
                <OverviewTile
                  icon={<FileSearch className="h-5 w-5" />}
                  label={t.externalApi.sourceOverview}
                  value={String(sourceItems.length)}
                  detail={t.externalApi.sourceOverviewDetail}
                />
                <OverviewTile
                  icon={<UsersRound className="h-5 w-5" />}
                  label={t.externalApi.teamOverview}
                  value={String(teamItems.length)}
                  detail={t.externalApi.teamOverviewDetail}
                />
              </div>

              <div className="flex flex-col gap-4">
                <ConnectionTargetSection
                  targetType="source"
                  title={t.externalApi.sourceApi}
                  description={t.externalApi.sourceApiDescription}
                  connections={sourceConnectionItems}
                  sourceByConnectionId={sourceByConnectionId}
                  teams={teamItems}
                  testConnection={testConnection}
                  onAdd={() => setConnectionDialogTarget('source')}
                  capabilityLabel={capabilityLabel}
                />
                <ConnectionTargetSection
                  targetType="output"
                  title={t.externalApi.outputArtifactApi}
                  description={t.externalApi.outputApiDescription}
                  connections={outputConnectionItems}
                  sourceByConnectionId={sourceByConnectionId}
                  teams={teamItems}
                  testConnection={testConnection}
                  onAdd={() => setConnectionDialogTarget('output')}
                  capabilityLabel={capabilityLabel}
                />
              </div>
            </div>
          )}

          <ConnectionFormDialog
            open={connectionDialogTarget !== null}
            targetType={connectionDialogTarget ?? 'source'}
            onOpenChange={(open) => setConnectionDialogTarget(open ? connectionDialogTarget : null)}
          />
        </div>
      </div>
    </div>
  )
}

function ConnectionFormDialog({
  open,
  targetType,
  onOpenChange,
}: {
  open: boolean
  targetType: ExternalApiConnectionTarget
  onOpenChange: (open: boolean) => void
}) {
  const { t } = useTranslation()
  const createConnection = useCreateExternalApiConnection()
  const createSource = useCreateExternalApiSource()
  const [connectionName, setConnectionName] = useState('')
  const [baseUrl, setBaseUrl] = useState('')
  const [apiKey, setApiKey] = useState('')
  const [timeoutSeconds, setTimeoutSeconds] = useState('30')
  const [sourceName, setSourceName] = useState('')
  const [sourceKey, setSourceKey] = useState('')
  const [sourceDescription, setSourceDescription] = useState('')

  const capabilities = getConnectionCapabilities(targetType)
  const isSubmitting = createConnection.isPending || createSource.isPending
  const isSourceTarget = targetType === 'source'
  const isValid =
    connectionName.trim() !== '' &&
    baseUrl.trim() !== '' &&
    apiKey.trim() !== '' &&
    (!isSourceTarget || (sourceName.trim() !== '' && sourceKey.trim() !== ''))

  useEffect(() => {
    if (!open) return
    if (!sourceName && connectionName) {
      setSourceName(connectionName)
    }
  }, [connectionName, open, sourceName])

  const capabilityLabel = (capability: ExternalApiCapability) => {
    if (capability === 'search') return t.externalApi.capabilitySearch
    if (capability === 'fetch') return t.externalApi.capabilityFetch
    return t.externalApi.capabilityOutput
  }

  const reset = () => {
    setConnectionName('')
    setBaseUrl('')
    setApiKey('')
    setTimeoutSeconds('30')
    setSourceName('')
    setSourceKey('')
    setSourceDescription('')
  }

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    const createdConnection = await createConnection.mutateAsync({
      name: connectionName.trim(),
      target_type: targetType,
      base_url: baseUrl.trim(),
      api_key: apiKey,
      timeout_seconds: Number(timeoutSeconds) || 30,
      enabled: true,
    })

    if (isSourceTarget) {
      await createSource.mutateAsync({
        connection_id: createdConnection.id,
        name: sourceName.trim(),
        key: sourceKey.trim(),
        description: sourceDescription.trim() || undefined,
        capabilities: SOURCE_CAPABILITIES,
        enabled: true,
      })
    }

    reset()
    onOpenChange(false)
  }

  const targetLabel = isSourceTarget ? t.externalApi.sourceApi : t.externalApi.outputArtifactApi

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>
            {(isSourceTarget ? t.externalApi.addSourceIntegration : t.externalApi.addOutputIntegration).replace(
              '{target}',
              targetLabel
            )}
          </DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="space-y-3">
            <h3 className="text-sm font-medium">{t.externalApi.endpointConfiguration}</h3>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="connection-name">{t.common.name}</Label>
                <Input
                  id="connection-name"
                  value={connectionName}
                  onChange={(event) => setConnectionName(event.target.value)}
                  placeholder={isSourceTarget ? 'Paper Search' : 'Report Generator'}
                  disabled={isSubmitting}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="connection-timeout">{t.externalApi.timeoutSeconds}</Label>
                <Input
                  id="connection-timeout"
                  type="number"
                  min="1"
                  max="300"
                  value={timeoutSeconds}
                  onChange={(event) => setTimeoutSeconds(event.target.value)}
                  disabled={isSubmitting}
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="connection-url">{t.externalApi.baseUrl}</Label>
              <Input
                id="connection-url"
                value={baseUrl}
                onChange={(event) => setBaseUrl(event.target.value)}
                placeholder="https://provider.example.com"
                disabled={isSubmitting}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="connection-key">{t.externalApi.apiKey}</Label>
              <Input
                id="connection-key"
                type="password"
                value={apiKey}
                onChange={(event) => setApiKey(event.target.value)}
                disabled={isSubmitting}
                autoComplete="off"
                required
              />
            </div>
          </div>

          {isSourceTarget && (
            <div className="space-y-3 border-t pt-5">
              <h3 className="text-sm font-medium">{t.externalApi.sourceDefinition}</h3>
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="source-name">{t.common.source}</Label>
                  <Input
                    id="source-name"
                    value={sourceName}
                    onChange={(event) => setSourceName(event.target.value)}
                    disabled={isSubmitting}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="source-key">{t.externalApi.sourceKey}</Label>
                  <Input
                    id="source-key"
                    value={sourceKey}
                    onChange={(event) => setSourceKey(event.target.value)}
                    placeholder="paper_search"
                    disabled={isSubmitting}
                    required
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="source-desc">{t.common.description}</Label>
                <Textarea
                  id="source-desc"
                  value={sourceDescription}
                  onChange={(event) => setSourceDescription(event.target.value)}
                  rows={3}
                  disabled={isSubmitting}
                />
              </div>
            </div>
          )}

          <div className="flex flex-wrap gap-1">
            {capabilities.map((capability) => (
              <Badge key={capability} variant="secondary">
                {capabilityLabel(capability)}
              </Badge>
            ))}
          </div>

          <div className="flex justify-end gap-2 border-t pt-4">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={isSubmitting}>
              {t.common.cancel}
            </Button>
            <Button type="submit" disabled={!isValid || isSubmitting}>
              {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {t.apiKeys.addConfig}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}

function ConnectionTargetSection({
  targetType,
  title,
  description,
  connections,
  sourceByConnectionId,
  teams,
  testConnection,
  onAdd,
  capabilityLabel,
}: {
  targetType: ExternalApiConnectionTarget
  title: string
  description: string
  connections: ExternalApiConnection[]
  sourceByConnectionId: Map<string, ExternalApiSource>
  teams: Array<{ id: string; name: string }>
  testConnection: ReturnType<typeof useTestExternalApiConnection>
  onAdd: () => void
  capabilityLabel: (capability: ExternalApiCapability) => string
}) {
  const { t } = useTranslation()
  const hasConnections = connections.length > 0

  return (
    <Card className={!hasConnections ? 'opacity-80' : undefined}>
      <CardHeader className="pb-3">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <CardTitle className="flex items-center gap-2 text-lg">
              {targetType === 'output' ? <WandSparkles className="h-5 w-5" /> : <FileSearch className="h-5 w-5" />}
              {title}
            </CardTitle>
            <CardDescription className="mt-1">{description}</CardDescription>
          </div>
          {hasConnections ? (
            <Badge className="w-fit bg-emerald-100 text-emerald-700 hover:bg-emerald-100 dark:bg-emerald-900/30 dark:text-emerald-300">
              <Check className="mr-1 h-3 w-3" />
              {t.apiKeys.configured}
            </Badge>
          ) : (
            <Badge variant="outline" className="w-fit border-dashed text-muted-foreground">
              <X className="mr-1 h-3 w-3" />
              {t.apiKeys.notConfigured}
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {!hasConnections && (
          <EmptyState
            icon={targetType === 'output' ? <WandSparkles className="h-5 w-5" /> : <FileSearch className="h-5 w-5" />}
            title={t.externalApi.noConnections}
            description={t.externalApi.noConnectionsHint}
          />
        )}

        {connections.map((connection) => (
          <ConnectionConfigCard
            key={connection.id}
            connection={connection}
            source={sourceByConnectionId.get(connection.id)}
            teams={teams}
            testConnection={testConnection}
            capabilityLabel={capabilityLabel}
          />
        ))}

        <Button variant="outline" size="sm" onClick={onAdd} className="w-full gap-2">
          <Plus className="h-4 w-4" />
          {targetType === 'source' ? t.externalApi.addSourceIntegration : t.externalApi.addOutputIntegration}
        </Button>
      </CardContent>
    </Card>
  )
}

function ConnectionConfigCard({
  connection,
  source,
  teams,
  testConnection,
  capabilityLabel,
}: {
  connection: ExternalApiConnection
  source?: ExternalApiSource
  teams: Array<{ id: string; name: string }>
  testConnection: ReturnType<typeof useTestExternalApiConnection>
  capabilityLabel: (capability: ExternalApiCapability) => string
}) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  const targetType = connection.target_type ?? 'source'
  const isTestingThisConnection = testConnection.isPending && testConnection.variables === connection.id
  const testResult =
    testConnection.variables === connection.id && testConnection.data
      ? testConnection.data
      : null
  const capabilities = getConnectionCapabilities(targetType)

  return (
    <Collapsible open={open} onOpenChange={setOpen} className="rounded-md border p-3">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-medium">{source?.name || connection.name}</span>
            <Badge variant={connection.enabled ? 'secondary' : 'outline'}>
              {connection.enabled ? t.externalApi.enabled : t.externalApi.disabled}
            </Badge>
            {targetType === 'source' && source && <Badge variant="outline">{source.key}</Badge>}
            {targetType === 'source' && !source && <Badge variant="outline">{t.externalApi.noLinkedSource}</Badge>}
          </div>
          <p className="mt-1 truncate text-sm text-muted-foreground">{connection.name}</p>
        </div>
        <CollapsibleTrigger asChild>
          <Button variant="ghost" size="sm" className="shrink-0 gap-1">
            {open ? t.externalApi.hideDetails : t.externalApi.showDetails}
            <ChevronDown className={`h-4 w-4 transition-transform ${open ? 'rotate-180' : ''}`} />
          </Button>
        </CollapsibleTrigger>
      </div>

      <CollapsibleContent className="mt-3 space-y-3 border-t pt-3">
        <div className="grid gap-2 text-sm text-muted-foreground md:grid-cols-2">
          <div>
            <span className="text-xs uppercase tracking-wide">{t.externalApi.baseUrl}</span>
            <p className="truncate text-foreground">{connection.base_url}</p>
          </div>
          <div>
            <span className="text-xs uppercase tracking-wide">{t.externalApi.timeoutSeconds}</span>
            <p className="text-foreground">
              {t.externalApi.timeoutValue.replace('{seconds}', String(connection.timeout_seconds))}
            </p>
          </div>
          <div>
            <span className="text-xs uppercase tracking-wide">{t.externalApi.apiKey}</span>
            <p className="flex items-center gap-1 text-foreground">
              <KeyRound className="h-3 w-3" />
              {connection.api_key_configured ? t.externalApi.keyStored : t.externalApi.keyMissing}
            </p>
          </div>
          {source && (
            <div>
              <span className="text-xs uppercase tracking-wide">{t.externalApi.sourceKey}</span>
              <p className="text-foreground">{source.key}</p>
            </div>
          )}
        </div>

        {source?.description && (
          <p className="rounded-md bg-muted px-3 py-2 text-sm text-muted-foreground">{source.description}</p>
        )}

        {targetType === 'source' && source && (
          <SourceGrantManager source={source} teams={teams} isOpen={open} />
        )}

        {testResult && <ConnectionTestResultPanel result={testResult} />}

        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap gap-1">
            {capabilities.map((capability) => (
              <Badge key={capability} variant="secondary">
                {capabilityLabel(capability)}
              </Badge>
            ))}
          </div>
          <Button
            variant="outline"
            size="sm"
            disabled={testConnection.isPending}
            onClick={() => testConnection.mutate(connection.id)}
          >
            {isTestingThisConnection ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plug className="h-4 w-4" />}
            <span>{isTestingThisConnection ? t.externalApi.testing : t.externalApi.test}</span>
          </Button>
        </div>
      </CollapsibleContent>
    </Collapsible>
  )
}

function ConnectionTestResultPanel({ result }: { result: ExternalApiConnectionTestResult }) {
  const { t } = useTranslation()

  return (
    <div className="space-y-3 rounded-md border bg-background p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="text-sm font-medium">{t.externalApi.lastTest}</p>
          {result.message && <p className="mt-1 text-xs text-muted-foreground">{result.message}</p>}
        </div>
        <Badge variant={result.ok ? 'secondary' : 'destructive'}>
          {result.ok ? t.externalApi.connectionSucceeded : t.externalApi.connectionFailed}
        </Badge>
      </div>
      <div className="grid gap-3 lg:grid-cols-2">
        <div>
          <p className="mb-1 text-xs uppercase tracking-wide text-muted-foreground">{t.externalApi.testStatus}</p>
          <pre className="max-h-44 overflow-auto rounded-md bg-muted p-3 text-xs text-foreground">
            {formatJson({ ok: result.ok, status: result.status, message: result.message ?? undefined })}
          </pre>
        </div>
        <div>
          <p className="mb-1 text-xs uppercase tracking-wide text-muted-foreground">{t.externalApi.healthResponse}</p>
          <pre className="max-h-44 overflow-auto rounded-md bg-muted p-3 text-xs text-foreground">
            {formatJson(result.health ?? {})}
          </pre>
        </div>
        {result.manifest && (
          <div className="lg:col-span-2">
            <p className="mb-1 text-xs uppercase tracking-wide text-muted-foreground">{t.externalApi.manifestResponse}</p>
            <pre className="max-h-56 overflow-auto rounded-md bg-muted p-3 text-xs text-foreground">
              {formatJson(result.manifest)}
            </pre>
          </div>
        )}
      </div>
    </div>
  )
}

function SourceGrantManager({
  source,
  teams,
  isOpen,
}: {
  source: ExternalApiSource
  teams: Array<{ id: string; name: string }>
  isOpen: boolean
}) {
  const { t } = useTranslation()
  const grants = useExternalApiTeamGrants(source.id, isOpen)
  const createGrant = useCreateExternalApiTeamGrant()
  const [teamId, setTeamId] = useState('')
  const [quota, setQuota] = useState('100')

  const grantItems = useMemo(() => grants.data?.items ?? [], [grants.data?.items])
  const grantedTeamIds = useMemo(
    () => new Set(grantItems.map((grant) => grant.team_id)),
    [grantItems]
  )
  const availableTeams = useMemo(
    () => teams.filter((team) => !grantedTeamIds.has(team.id)),
    [grantedTeamIds, teams]
  )

  useEffect(() => {
    if (!teamId && availableTeams.length > 0) {
      setTeamId(availableTeams[0].id)
    }
    if (teamId && !availableTeams.some((team) => team.id === teamId)) {
      setTeamId('')
    }
  }, [availableTeams, teamId])

  const handleGrant = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!teamId) return
    await createGrant.mutateAsync({
      sourceId: source.id,
      data: {
        team_id: teamId,
        monthly_request_quota: Number(quota) || 0,
        enabled: true,
      },
    })
    setQuota('100')
  }

  return (
    <div className="space-y-3 rounded-md border bg-muted/20 p-3">
      <div className="flex items-center justify-between gap-3">
        <h4 className="text-sm font-medium">{t.externalApi.authorizedTeams}</h4>
      </div>

      {grantItems.length === 0 ? (
        <p className="text-sm text-muted-foreground">{t.externalApi.noTeamGrants}</p>
      ) : (
        <div className="flex flex-col divide-y rounded-md border bg-background">
          {grantItems.map((grant: ExternalApiTeamGrant) => (
            <div key={grant.id} className="flex flex-wrap items-center justify-between gap-2 p-2 text-sm">
              <div className="min-w-0">
                <span className="font-medium">{grant.team_name || grant.team_id}</span>
                <span className="ml-2 text-muted-foreground">
                  {t.externalApi.quotaValue.replace('{quota}', String(grant.monthly_request_quota))}
                </span>
              </div>
              <Badge variant={grant.enabled ? 'secondary' : 'outline'}>
                {grant.enabled ? t.externalApi.enabled : t.externalApi.disabled}
              </Badge>
            </div>
          ))}
        </div>
      )}

      <form onSubmit={handleGrant} className="grid gap-2 md:grid-cols-[minmax(0,1fr)_140px_auto]">
        <Select value={teamId} onValueChange={setTeamId} disabled={availableTeams.length === 0}>
          <SelectTrigger>
            <SelectValue placeholder={t.externalApi.selectTeam} />
          </SelectTrigger>
          <SelectContent>
            {availableTeams.map((team) => (
              <SelectItem key={team.id} value={team.id}>{team.name}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Input
          aria-label={t.externalApi.monthlyRequestQuota}
          type="number"
          min="0"
          value={quota}
          onChange={(event) => setQuota(event.target.value)}
        />
        <Button type="submit" disabled={createGrant.isPending || !teamId}>
          {createGrant.isPending ? t.common.saving : t.externalApi.grant}
        </Button>
      </form>
      {availableTeams.length === 0 && teams.length > 0 && (
        <p className="text-xs text-muted-foreground">{t.externalApi.allTeamsGranted}</p>
      )}
      {teams.length === 0 && (
        <p className="text-xs text-muted-foreground">{t.externalApi.grantPrerequisite}</p>
      )}
    </div>
  )
}

function OverviewTile({
  icon,
  label,
  value,
  detail,
}: {
  icon: React.ReactNode
  label: string
  value: string
  detail: string
}) {
  return (
    <Card>
      <CardContent className="flex items-center gap-3 p-4">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground">
          {icon}
        </div>
        <div className="min-w-0">
          <p className="text-sm text-muted-foreground">{label}</p>
          <p className="text-2xl font-semibold tracking-normal">{value}</p>
          <p className="truncate text-xs text-muted-foreground">{detail}</p>
        </div>
      </CardContent>
    </Card>
  )
}

function EmptyState({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode
  title: string
  description: string
}) {
  return (
    <div className="flex items-start gap-3 rounded-md border border-dashed p-4">
      <div className="mt-0.5 text-muted-foreground">{icon}</div>
      <div>
        <p className="font-medium">{title}</p>
        <p className="mt-1 text-sm text-muted-foreground">{description}</p>
      </div>
    </div>
  )
}
