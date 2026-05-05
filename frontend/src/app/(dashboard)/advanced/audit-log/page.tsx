'use client'

import { useState } from 'react'
import { Search, ShieldCheck } from 'lucide-react'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useAuditLog } from '@/lib/hooks/use-audit-log'
import { useTranslation } from '@/lib/hooks/use-translation'

function metadataSummary(metadata: Record<string, unknown>) {
  const entries = Object.entries(metadata || {})
  if (entries.length === 0) return ''
  return entries
    .slice(0, 4)
    .map(([key, value]) => `${key}: ${typeof value === 'object' ? JSON.stringify(value) : String(value)}`)
    .join(' · ')
}

export default function AuditLogPage() {
  const { t } = useTranslation()
  const [actorId, setActorId] = useState('')
  const [action, setAction] = useState('')
  const [targetId, setTargetId] = useState('')
  const [offset, setOffset] = useState(0)
  const limit = 50
  const { data, isLoading, error } = useAuditLog({
    actor_id: actorId.trim() || undefined,
    action: action.trim() || undefined,
    target_id: targetId.trim() || undefined,
    limit,
    offset,
  })
  const logs = data?.items ?? []

  const resetFilters = () => {
    setActorId('')
    setAction('')
    setTargetId('')
    setOffset(0)
  }

  return (
          <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 p-6">
        <div className="flex items-center gap-3">
          <ShieldCheck className="h-6 w-6 text-muted-foreground" />
          <div>
            <h1 className="text-2xl font-semibold tracking-normal">{t.auditLog.title}</h1>
            <p className="text-sm text-muted-foreground">{t.auditLog.description}</p>
          </div>
        </div>

        <div className="grid gap-3 lg:grid-cols-[1fr_1fr_1fr_auto]">
          <div className="relative">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              value={actorId}
              onChange={(event) => {
                setActorId(event.target.value)
                setOffset(0)
              }}
              className="pl-9"
              placeholder={t.auditLog.actorFilter}
            />
          </div>
          <Input
            value={action}
            onChange={(event) => {
              setAction(event.target.value)
              setOffset(0)
            }}
            placeholder={t.auditLog.actionFilter}
          />
          <Input
            value={targetId}
            onChange={(event) => {
              setTargetId(event.target.value)
              setOffset(0)
            }}
            placeholder={t.auditLog.targetFilter}
          />
          <Button variant="outline" onClick={resetFilters}>
            {t.common.resetToDefault}
          </Button>
        </div>

        {isLoading ? (
          <div className="flex h-64 items-center justify-center">
            <LoadingSpinner />
          </div>
        ) : error ? (
          <div className="rounded-md border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">
            {t.common.error}
          </div>
        ) : logs.length === 0 ? (
          <div className="rounded-md border p-8 text-center text-sm text-muted-foreground">
            {t.auditLog.empty}
          </div>
        ) : (
          <div className="overflow-hidden rounded-md border">
            <table className="w-full text-sm">
              <thead className="bg-muted/50 text-left">
                <tr>
                  <th className="px-4 py-3 font-medium">{t.auditLog.created}</th>
                  <th className="px-4 py-3 font-medium">{t.auditLog.action}</th>
                  <th className="px-4 py-3 font-medium">{t.auditLog.actor}</th>
                  <th className="px-4 py-3 font-medium">{t.auditLog.target}</th>
                  <th className="px-4 py-3 font-medium">{t.auditLog.metadata}</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((entry) => (
                  <tr key={entry.id} className="border-t">
                    <td className="whitespace-nowrap px-4 py-3 text-muted-foreground">
                      {entry.created}
                    </td>
                    <td className="px-4 py-3">
                      <Badge variant="outline">{entry.action}</Badge>
                    </td>
                    <td className="px-4 py-3">
                      <div className="font-medium">{entry.actor_username || t.common.unknown}</div>
                      <div className="text-xs text-muted-foreground">{entry.actor_id}</div>
                    </td>
                    <td className="px-4 py-3">
                      <div>{entry.target_type || '-'}</div>
                      <div className="text-xs text-muted-foreground">{entry.target_id}</div>
                    </td>
                    <td className="max-w-md px-4 py-3 text-muted-foreground">
                      <div className="truncate">{metadataSummary(entry.metadata)}</div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="flex items-center justify-between border-t pt-4">
          <Button
            variant="outline"
            disabled={offset === 0}
            onClick={() => setOffset((value) => Math.max(0, value - limit))}
          >
            {t.common.previous}
          </Button>
          <span className="text-sm text-muted-foreground">
            {t.common.page} {Math.floor(offset / limit) + 1}
          </span>
          <Button
            variant="outline"
            disabled={logs.length < limit}
            onClick={() => setOffset((value) => value + limit)}
          >
            {t.common.next}
          </Button>
        </div>
      </div>
  )
}
