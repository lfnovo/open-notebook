'use client'

import { FormEvent, useEffect, useMemo, useState } from 'react'
import { Bot, Edit, Loader2, Plus, Search, SlidersHorizontal, Trash2, UserPlus, Users, Wand2, X } from 'lucide-react'
import { Team, TeamMember, TeamMemberStatus, TeamModelDefaults, TeamRole } from '@/lib/api/teams'
import {
  useActiveUsers,
  useCreateTeam,
  useDeleteTeam,
  useRemoveTeamMember,
  useTeamMembers,
  useTeamModels,
  useTeamModelDefaults,
  useTeamTransformations,
  useTeams,
  useUpdateTeam,
  useUpdateTeamModels,
  useUpdateTeamModelDefaults,
  useUpdateTeamTransformations,
  useUpsertTeamMember,
} from '@/lib/hooks/use-teams'
import { useModels } from '@/lib/hooks/use-models'
import { useTransformations } from '@/lib/hooks/use-transformations'
import { useTranslation } from '@/lib/hooks/use-translation'
import { useAuthStore } from '@/lib/stores/auth-store'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { OperationGuide } from '@/components/common/OperationGuide'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

const TEAM_ROLES: TeamRole[] = ['owner', 'admin', 'member', 'viewer']
const MEMBER_STATUSES: TeamMemberStatus[] = ['active', 'disabled']
const EMPTY_TEAMS: Team[] = []

function roleLabel(role: TeamRole, t: ReturnType<typeof useTranslation>['t']) {
  const labels: Record<TeamRole, string> = {
    owner: t.teams.roleOwner,
    admin: t.teams.roleAdmin,
    member: t.teams.roleMember,
    viewer: t.teams.roleViewer,
  }
  return labels[role]
}

function statusLabel(status: TeamMemberStatus | 'invited', t: ReturnType<typeof useTranslation>['t']) {
  const labels = {
    active: t.teams.statusActive,
    disabled: t.teams.statusDisabled,
    invited: t.teams.statusInvited,
  }
  return labels[status]
}

type TeamModelDefaultKey = keyof Omit<TeamModelDefaults, 'team_id'>

interface TeamDefaultConfig {
  key: TeamModelDefaultKey
  label: string
  description: string
  modelType: 'language' | 'embedding'
}

function TeamDefaultModelsPanel({ team }: { team: Team }) {
  const { t } = useTranslation()
  const isWorkspace = team.type === 'workspace'
  const { data: teamModels } = useTeamModels(isWorkspace ? team.id : undefined)
  const { data: defaults } = useTeamModelDefaults(isWorkspace ? team.id : undefined)
  const updateDefaults = useUpdateTeamModelDefaults(team.id)
  const allowedModels = teamModels?.models ?? []

  const configs: TeamDefaultConfig[] = [
    {
      key: 'default_chat_model',
      label: t.models.chatModelLabel,
      description: t.models.chatModelDesc,
      modelType: 'language',
    },
    {
      key: 'default_embedding_model',
      label: t.models.embeddingModelLabel,
      description: t.models.embeddingModelDesc,
      modelType: 'embedding',
    },
    {
      key: 'default_transformation_model',
      label: t.models.transformationModelLabel,
      description: t.models.transformationModelDesc,
      modelType: 'language',
    },
    {
      key: 'default_tools_model',
      label: t.models.toolsModelLabel,
      description: t.models.toolsModelDesc,
      modelType: 'language',
    },
    {
      key: 'large_context_model',
      label: t.models.largeContextModelLabel,
      description: t.models.largeContextModelDesc,
      modelType: 'language',
    },
  ]

  const handleChange = (key: TeamModelDefaultKey, value: string | null) => {
    updateDefaults.mutate({ [key]: value })
  }

  if (!isWorkspace || !team.can_manage) {
    return null
  }

  return (
    <section className="space-y-4 border-b p-4">
      <div className="flex items-start gap-2">
        <SlidersHorizontal className="mt-0.5 h-4 w-4 text-muted-foreground" />
        <div>
          <h3 className="text-sm font-semibold tracking-normal">{t.teams.modelDefaults}</h3>
          <p className="text-xs text-muted-foreground">{t.teams.modelDefaultsDesc}</p>
        </div>
      </div>

      {allowedModels.length === 0 ? (
        <div className="rounded-md border p-4 text-sm text-muted-foreground">
          {t.teams.noTeamModelsAvailable}
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {configs.map((config) => {
            const available = allowedModels
              .filter((model) => model.type === config.modelType)
              .sort((a, b) => a.name.localeCompare(b.name))
            const currentValue = defaults?.[config.key] || undefined
            const currentIsAllowed = currentValue && available.some((model) => model.id === currentValue)
            const value = currentIsAllowed ? currentValue : undefined

            return (
              <div key={config.key} className="space-y-1">
                <Label className="text-xs">{config.label}</Label>
                <div className="flex gap-1">
                  <Select
                    value={value}
                    onValueChange={(nextValue) => handleChange(config.key, nextValue)}
                    disabled={updateDefaults.isPending || available.length === 0}
                  >
                    <SelectTrigger className="h-8 text-xs">
                      <SelectValue placeholder={t.teams.inheritSystemDefault} />
                    </SelectTrigger>
                    <SelectContent>
                      {available.map((model) => (
                        <SelectItem key={model.id} value={model.id}>
                          <div className="flex w-full items-center justify-between">
                            <span>{model.name}</span>
                            <span className="ml-2 text-xs text-muted-foreground">{model.provider}</span>
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {value && (
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 shrink-0"
                      disabled={updateDefaults.isPending}
                      onClick={() => handleChange(config.key, null)}
                      aria-label={t.teams.clearTeamDefault}
                    >
                      <X className="h-3.5 w-3.5" />
                    </Button>
                  )}
                </div>
                <p className="text-[10px] leading-tight text-muted-foreground">{config.description}</p>
              </div>
            )
          })}
        </div>
      )}
    </section>
  )
}

function TeamAdminAllowlistPanel({ team }: { team: Team }) {
  const { t } = useTranslation()
  const isWorkspace = team.type === 'workspace'
  const { data: models = [], isLoading: modelsLoading } = useModels()
  const { data: transformations = [], isLoading: transformationsLoading } = useTransformations()
  const { data: teamModels } = useTeamModels(isWorkspace ? team.id : undefined)
  const { data: teamTransformations } = useTeamTransformations(isWorkspace ? team.id : undefined)
  const updateTeamModels = useUpdateTeamModels(team.id)
  const updateTeamTransformations = useUpdateTeamTransformations(team.id)
  const canManage = isWorkspace
  const selectedModelIds = teamModels?.model_ids ?? []
  const selectedTransformationIds = teamTransformations?.transformation_ids ?? []

  const toggleModel = (modelId: string, checked: boolean) => {
    const next = checked
      ? Array.from(new Set([...selectedModelIds, modelId]))
      : selectedModelIds.filter((id) => id !== modelId)
    updateTeamModels.mutate(next)
  }

  const toggleTransformation = (transformationId: string, checked: boolean) => {
    const next = checked
      ? Array.from(new Set([...selectedTransformationIds, transformationId]))
      : selectedTransformationIds.filter((id) => id !== transformationId)
    updateTeamTransformations.mutate(next)
  }

  if (!isWorkspace) {
    return null
  }

  return (
    <div className="grid gap-4 border-b p-4 lg:grid-cols-2">
      <section className="min-w-0 space-y-3">
        <div className="flex items-start gap-2">
          <Bot className="mt-0.5 h-4 w-4 text-muted-foreground" />
          <div>
            <h3 className="text-sm font-semibold tracking-normal">{t.teams.allowedModels}</h3>
            <p className="text-xs text-muted-foreground">{t.teams.allowedModelsDesc}</p>
          </div>
        </div>
        {modelsLoading ? (
          <div className="flex min-h-24 items-center justify-center rounded-md border">
            <LoadingSpinner />
          </div>
        ) : models.length === 0 ? (
          <div className="rounded-md border p-4 text-sm text-muted-foreground">
            {t.teams.noModelsAvailable}
          </div>
        ) : (
          <div className="space-y-2">
            {models.map((model) => {
              const inputId = `team-${team.id}-model-${model.id}`
              return (
                <div key={model.id} className="flex items-start gap-3 rounded-md border p-3">
                  <Checkbox
                    id={inputId}
                    checked={selectedModelIds.includes(model.id)}
                    disabled={!canManage || updateTeamModels.isPending}
                    onCheckedChange={(checked) => toggleModel(model.id, Boolean(checked))}
                  />
                  <div className="min-w-0">
                    <Label htmlFor={inputId} className="cursor-pointer text-sm font-medium">
                      {model.name}
                    </Label>
                    <p className="truncate text-xs text-muted-foreground">
                      {model.provider} · {model.type}
                    </p>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </section>

      <section className="min-w-0 space-y-3">
        <div className="flex items-start gap-2">
          <Wand2 className="mt-0.5 h-4 w-4 text-muted-foreground" />
          <div>
            <h3 className="text-sm font-semibold tracking-normal">{t.teams.allowedTransformations}</h3>
            <p className="text-xs text-muted-foreground">{t.teams.allowedTransformationsDesc}</p>
          </div>
        </div>
        {transformationsLoading ? (
          <div className="flex min-h-24 items-center justify-center rounded-md border">
            <LoadingSpinner />
          </div>
        ) : transformations.length === 0 ? (
          <div className="rounded-md border p-4 text-sm text-muted-foreground">
            {t.teams.noTransformationsAvailable}
          </div>
        ) : (
          <div className="space-y-2">
            {transformations.map((transformation) => {
              const inputId = `team-${team.id}-transformation-${transformation.id}`
              return (
                <div key={transformation.id} className="flex items-start gap-3 rounded-md border p-3">
                  <Checkbox
                    id={inputId}
                    checked={selectedTransformationIds.includes(transformation.id)}
                    disabled={!canManage || updateTeamTransformations.isPending}
                    onCheckedChange={(checked) => toggleTransformation(transformation.id, Boolean(checked))}
                  />
                  <div className="min-w-0">
                    <Label htmlFor={inputId} className="cursor-pointer text-sm font-medium">
                      {transformation.title}
                    </Label>
                    <p className="line-clamp-2 text-xs text-muted-foreground">
                      {transformation.description || transformation.name}
                    </p>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </section>
    </div>
  )
}

function TeamAllowlistPanel({ team }: { team: Team }) {
  const role = useAuthStore((state) => state.role)

  if (role !== 'admin' || team.type !== 'workspace') {
    return null
  }

  return <TeamAdminAllowlistPanel team={team} />
}

function TeamDialog({
  open,
  team,
  onOpenChange,
}: {
  open: boolean
  team?: Team | null
  onOpenChange: (open: boolean) => void
}) {
  const { t } = useTranslation()
  const createTeam = useCreateTeam()
  const updateTeam = useUpdateTeam()
  const [name, setName] = useState('')
  const [slug, setSlug] = useState('')
  const [ownerQuery, setOwnerQuery] = useState('')
  const [ownerId, setOwnerId] = useState('')
  const isEditing = !!team
  const { data: ownerData, isLoading: ownersLoading } = useActiveUsers(
    ownerQuery,
    undefined,
    open && !isEditing
  )
  const ownerUsers = ownerData?.items ?? []

  useEffect(() => {
    setName(team?.name || '')
    setSlug(team?.slug || '')
    setOwnerQuery('')
    setOwnerId('')
  }, [team, open])

  const isPending = createTeam.isPending || updateTeam.isPending

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault()
    if (!name.trim() || isPending) return
    if (!isEditing && !ownerId) return

    const onSuccess = () => onOpenChange(false)
    if (team) {
      updateTeam.mutate({ teamId: team.id, data: { name: name.trim() } }, { onSuccess })
    } else {
      createTeam.mutate(
        { name: name.trim(), slug: slug.trim() || undefined, owner_id: ownerId },
        { onSuccess }
      )
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <form onSubmit={handleSubmit} className="space-y-5">
          <DialogHeader>
            <DialogTitle>{isEditing ? t.teams.editTeam : t.teams.createTeam}</DialogTitle>
          </DialogHeader>
          <div className="space-y-2">
            <Label htmlFor="team-name">{t.common.name}</Label>
            <Input
              id="team-name"
              value={name}
              onChange={(event) => setName(event.target.value)}
              autoFocus
            />
          </div>
          {!isEditing && (
            <div className="space-y-2">
              <Label htmlFor="team-slug">{t.teams.slugLabel}</Label>
              <Input
                id="team-slug"
                value={slug}
                onChange={(event) => setSlug(event.target.value)}
                placeholder={t.teams.slugPlaceholder}
              />
            </div>
          )}
          {!isEditing && (
            <div className="space-y-2">
              <Label htmlFor="team-owner-search">{t.teams.owner}</Label>
              <div className="relative">
                <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  id="team-owner-search"
                  value={ownerQuery}
                  onChange={(event) => setOwnerQuery(event.target.value)}
                  className="pl-9"
                  placeholder={t.teams.searchUsers}
                />
              </div>
              <Select value={ownerId} onValueChange={setOwnerId}>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder={ownersLoading ? t.common.loading : t.teams.selectOwner} />
                </SelectTrigger>
                <SelectContent>
                  {ownerUsers.map((user) => (
                    <SelectItem key={user.id} value={user.id}>
                      {user.display_name || user.username} · {user.username}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              {t.common.cancel}
            </Button>
            <Button type="submit" disabled={!name.trim() || isPending || (!isEditing && !ownerId)}>
              {isPending && <Loader2 className="h-4 w-4 animate-spin" />}
              {t.common.save}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

function AddMemberDialog({
  open,
  teamId,
  onOpenChange,
}: {
  open: boolean
  teamId: string
  onOpenChange: (open: boolean) => void
}) {
  const { t } = useTranslation()
  const [query, setQuery] = useState('')
  const [userId, setUserId] = useState('')
  const [role, setRole] = useState<TeamRole>('member')
  const { data, isLoading } = useActiveUsers(query, teamId, open)
  const upsertMember = useUpsertTeamMember(teamId)
  const users = data?.items ?? []

  useEffect(() => {
    if (!open) {
      setQuery('')
      setUserId('')
      setRole('member')
    }
  }, [open])

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault()
    if (!userId || upsertMember.isPending) return
    upsertMember.mutate(
      { user_id: userId, role, status: 'active' },
      { onSuccess: () => onOpenChange(false) }
    )
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <form onSubmit={handleSubmit} className="space-y-5">
          <DialogHeader>
            <DialogTitle>{t.teams.addMember}</DialogTitle>
          </DialogHeader>
          <div className="space-y-2">
            <Label htmlFor="member-search">{t.common.search}</Label>
            <div className="relative">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                id="member-search"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                className="pl-9"
                placeholder={t.teams.searchUsers}
              />
            </div>
          </div>
          <div className="space-y-2">
            <Label>{t.teams.member}</Label>
            <Select value={userId} onValueChange={setUserId}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder={isLoading ? t.common.loading : t.teams.selectUser} />
              </SelectTrigger>
              <SelectContent>
                {users.map((user) => (
                  <SelectItem key={user.id} value={user.id}>
                    {user.display_name || user.username} · {user.username}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>{t.teams.role}</Label>
            <Select value={role} onValueChange={(value) => setRole(value as TeamRole)}>
              <SelectTrigger className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {TEAM_ROLES.map((item) => (
                  <SelectItem key={item} value={item}>
                    {roleLabel(item, t)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              {t.common.cancel}
            </Button>
            <Button type="submit" disabled={!userId || upsertMember.isPending}>
              {upsertMember.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
              {t.common.add}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

function MembersPanel({ team }: { team: Team }) {
  const { t } = useTranslation()
  const { data, isLoading, error } = useTeamMembers(team.id)
  const upsertMember = useUpsertTeamMember(team.id)
  const removeMember = useRemoveTeamMember(team.id)
  const [addOpen, setAddOpen] = useState(false)
  const isSystem = team.type === 'system'
  const canManage = !isSystem && Boolean(team.can_manage)
  const members = data ?? []

  const updateMember = (
    member: TeamMember,
    updates: Partial<{ role: TeamRole; status: TeamMemberStatus }>
  ) => {
    upsertMember.mutate({
      user_id: member.user,
      role: updates.role || member.role,
      status: updates.status || (member.status === 'invited' ? 'active' : member.status),
    })
  }

  return (
    <div className="min-w-0 flex-1 rounded-md border">
      <div className="flex flex-col gap-3 border-b p-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-semibold tracking-normal">{team.name}</h2>
            <Badge variant={isSystem ? 'secondary' : 'outline'}>
              {isSystem ? t.teams.system : t.teams.workspace}
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground">{team.slug}</p>
        </div>
        <Button
          size="sm"
          onClick={() => setAddOpen(true)}
          disabled={!canManage}
        >
          <UserPlus className="h-4 w-4" />
          {t.teams.addMember}
        </Button>
      </div>

      {isSystem && (
        <div className="border-b bg-muted/30 px-4 py-3 text-sm text-muted-foreground">
          {t.teams.publicReadOnly}
        </div>
      )}

      <TeamDefaultModelsPanel team={team} />
      <TeamAllowlistPanel team={team} />

      {isLoading ? (
        <div className="flex min-h-48 items-center justify-center">
          <LoadingSpinner />
        </div>
      ) : error ? (
        <div className="p-4 text-sm text-destructive">{t.common.error}</div>
      ) : members.length === 0 ? (
        <div className="p-8 text-center text-sm text-muted-foreground">
          {t.teams.noMembers}
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-muted/40 text-left">
              <tr>
                <th className="px-4 py-3 font-medium">{t.teams.member}</th>
                <th className="px-4 py-3 font-medium">{t.teams.role}</th>
                <th className="px-4 py-3 font-medium">{t.teams.status}</th>
                <th className="w-20 px-4 py-3 text-right font-medium">{t.common.actions}</th>
              </tr>
            </thead>
            <tbody>
              {members.map((member) => {
                const user = member.user_info
                return (
                  <tr key={member.id} className="border-t">
                    <td className="px-4 py-3">
                      <div className="font-medium">{user?.display_name || user?.username || member.user}</div>
                      <div className="text-xs text-muted-foreground">{user?.email || user?.username || member.user}</div>
                    </td>
                    <td className="px-4 py-3">
                      <Select
                        value={member.role}
                        disabled={!canManage || upsertMember.isPending}
                        onValueChange={(value) => updateMember(member, { role: value as TeamRole })}
                      >
                        <SelectTrigger size="sm" className="w-32">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {TEAM_ROLES.map((role) => (
                            <SelectItem key={role} value={role}>
                              {roleLabel(role, t)}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </td>
                    <td className="px-4 py-3">
                      <Select
                        value={member.status}
                        disabled={!canManage || upsertMember.isPending}
                        onValueChange={(value) => updateMember(member, { status: value as TeamMemberStatus })}
                      >
                        <SelectTrigger size="sm" className="w-32">
                          <SelectValue>{statusLabel(member.status, t)}</SelectValue>
                        </SelectTrigger>
                        <SelectContent>
                          {MEMBER_STATUSES.map((status) => (
                            <SelectItem key={status} value={status}>
                              {statusLabel(status, t)}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Button
                        variant="ghost"
                        size="icon"
                        disabled={!canManage || removeMember.isPending}
                        onClick={() => removeMember.mutate(member.user)}
                        aria-label={t.teams.removeMember}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      <AddMemberDialog open={addOpen} teamId={team.id} onOpenChange={setAddOpen} />
    </div>
  )
}

function TeamMembershipPanel({ team }: { team: Team }) {
  const { t } = useTranslation()
  const role = team.current_user_role

  return (
    <div className="min-w-0 flex-1 rounded-md border p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-semibold tracking-normal">{team.name}</h2>
            {role && <Badge variant="outline">{roleLabel(role, t)}</Badge>}
          </div>
          <p className="text-sm text-muted-foreground">{team.slug}</p>
        </div>
      </div>
      <div className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
        <div className="rounded-md border p-3">
          <div className="text-xs text-muted-foreground">{t.teams.members}</div>
          <div className="mt-1 font-medium">{t.teams.members}: {team.member_count}</div>
        </div>
        <div className="rounded-md border p-3">
          <div className="text-xs text-muted-foreground">{t.teams.shares}</div>
          <div className="mt-1 font-medium">{t.teams.shares}: {team.share_count}</div>
        </div>
      </div>
    </div>
  )
}

export default function TeamsPage() {
  const { t } = useTranslation()
  const role = useAuthStore((state) => state.role)
  const [query, setQuery] = useState('')
  const [selectedTeamId, setSelectedTeamId] = useState<string | null>(null)
  const [createOpen, setCreateOpen] = useState(false)
  const [editingTeam, setEditingTeam] = useState<Team | null>(null)
  const { data, isLoading, error } = useTeams(query)
  const deleteTeam = useDeleteTeam()
  const teams = data?.items ?? EMPTY_TEAMS
  const isSystemAdmin = role === 'admin'

  useEffect(() => {
    if (!teams.length) {
      setSelectedTeamId(null)
      return
    }
    if (!selectedTeamId || !teams.some((team) => team.id === selectedTeamId)) {
      const preferredTeam =
        teams.find((team) => team.type === 'workspace' && team.can_manage) ||
        teams.find((team) => team.type === 'workspace') ||
        teams[0]
      setSelectedTeamId(preferredTeam.id)
    }
  }, [selectedTeamId, teams])

  const selectedTeam = useMemo(
    () => teams.find((team) => team.id === selectedTeamId) || null,
    [selectedTeamId, teams]
  )

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <LoadingSpinner />
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 p-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <Users className="h-6 w-6 text-muted-foreground" />
            <div>
              <h1 className="text-2xl font-semibold tracking-normal">{t.navigation.teams}</h1>
              <p className="text-sm text-muted-foreground">{t.teams.description}</p>
            </div>
          </div>
          {isSystemAdmin && (
            <Button onClick={() => setCreateOpen(true)}>
              <Plus className="h-4 w-4" />
              {t.teams.createTeam}
            </Button>
          )}
        </div>

        <div className="relative max-w-md">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            className="pl-9"
            placeholder={t.teams.searchTeams}
          />
        </div>

        <OperationGuide
          title={t.teams.guideTitle}
          description={t.teams.guideDescription}
          steps={[
            t.teams.guideCreateTeam,
            t.teams.guideAssignMembers,
            t.teams.guideReviewShares,
          ]}
        />

        {error ? (
          <div className="rounded-md border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">
            {t.common.error}
          </div>
        ) : teams.length === 0 ? (
          <div className="rounded-md border p-8 text-center text-sm text-muted-foreground">
            {t.teams.empty}
          </div>
        ) : (
          <div className="flex flex-col gap-4 lg:flex-row">
            <div className="w-full shrink-0 overflow-hidden rounded-md border lg:w-96">
              <table className="w-full text-sm">
                <thead className="bg-muted/50 text-left">
                  <tr>
                    <th className="px-4 py-3 font-medium">{t.common.name}</th>
                    <th className="px-4 py-3 text-right font-medium">{t.common.actions}</th>
                  </tr>
                </thead>
                <tbody>
                  {teams.map((team) => {
                    const isSelected = team.id === selectedTeamId
                    const isSystem = team.type === 'system'
                    const canEditTeam = !isSystem && Boolean(team.can_manage)
                    const canDeleteTeam = !isSystem && isSystemAdmin
                    return (
                      <tr
                        key={team.id}
                        className={`cursor-pointer border-t ${isSelected ? 'bg-muted/60' : ''}`}
                        onClick={() => setSelectedTeamId(team.id)}
                      >
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-2">
                            <span className="font-medium">{team.name}</span>
                            {isSystem && <Badge variant="secondary">{t.teams.system}</Badge>}
                          </div>
                          <div className="mt-1 flex flex-wrap gap-3 text-xs text-muted-foreground">
                            <span>{team.slug}</span>
                            <span>{t.teams.members}: {team.member_count}</span>
                            <span>{t.teams.shares}: {team.share_count}</span>
                          </div>
                        </td>
                        <td className="px-4 py-3 text-right">
                          <div className="flex justify-end gap-1">
                            {canEditTeam && (
                              <Button
                                variant="ghost"
                                size="icon"
                                onClick={(event) => {
                                  event.stopPropagation()
                                  setEditingTeam(team)
                                }}
                                aria-label={t.teams.editTeam}
                              >
                                <Edit className="h-4 w-4" />
                              </Button>
                            )}
                            {canDeleteTeam && (
                              <Button
                                variant="ghost"
                                size="icon"
                                disabled={deleteTeam.isPending}
                                onClick={(event) => {
                                  event.stopPropagation()
                                  deleteTeam.mutate(team.id)
                                }}
                                aria-label={t.teams.deleteTeam}
                              >
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            )}
                          </div>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>

            {selectedTeam && (
              selectedTeam.can_manage ? (
                <MembersPanel team={selectedTeam} />
              ) : (
                <TeamMembershipPanel team={selectedTeam} />
              )
            )}
          </div>
        )}

        <TeamDialog open={createOpen} onOpenChange={setCreateOpen} />
        <TeamDialog
          open={!!editingTeam}
          team={editingTeam}
          onOpenChange={(open) => !open && setEditingTeam(null)}
        />
      </div>
    </div>
  )
}
