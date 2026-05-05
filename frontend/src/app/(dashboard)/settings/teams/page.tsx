'use client'

import { Users } from 'lucide-react'
import { useTeams } from '@/lib/hooks/use-teams'
import { useTranslation } from '@/lib/hooks/use-translation'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { Badge } from '@/components/ui/badge'

export default function TeamsPage() {
  const { t } = useTranslation()
  const { data, isLoading, error } = useTeams()
  const teams = data?.items ?? []

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <LoadingSpinner />
      </div>
    )
  }

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 p-6">
      <div className="flex items-center gap-3">
        <Users className="h-6 w-6 text-muted-foreground" />
        <div>
          <h1 className="text-2xl font-semibold tracking-normal">{t.navigation.teams}</h1>
          <p className="text-sm text-muted-foreground">{t.teams.description}</p>
        </div>
      </div>

      {error ? (
        <div className="rounded-md border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">
          {t.common.error}
        </div>
      ) : teams.length === 0 ? (
        <div className="rounded-md border p-8 text-center text-sm text-muted-foreground">
          {t.teams.empty}
        </div>
      ) : (
        <div className="overflow-hidden rounded-md border">
          <table className="w-full text-sm">
            <thead className="bg-muted/50 text-left">
              <tr>
                <th className="px-4 py-3 font-medium">{t.common.name}</th>
                <th className="px-4 py-3 font-medium">Slug</th>
                <th className="px-4 py-3 font-medium">{t.teams.members}</th>
                <th className="px-4 py-3 font-medium">{t.teams.shares}</th>
                <th className="px-4 py-3 font-medium">{t.common.type}</th>
              </tr>
            </thead>
            <tbody>
              {teams.map((team) => (
                <tr key={team.id} className="border-t">
                  <td className="px-4 py-3 font-medium">{team.name}</td>
                  <td className="px-4 py-3 text-muted-foreground">{team.slug}</td>
                  <td className="px-4 py-3">{team.member_count}</td>
                  <td className="px-4 py-3">{team.share_count}</td>
                  <td className="px-4 py-3">
                    <Badge variant={team.type === 'system' ? 'secondary' : 'outline'}>
                      {team.type === 'system' ? t.teams.system : t.teams.workspace}
                    </Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
