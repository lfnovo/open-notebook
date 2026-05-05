'use client'

import { useEffect, useMemo, useState } from 'react'
import { Globe2, Loader2, Share2, Trash2, Users } from 'lucide-react'
import { PUBLIC_TEAM_ID, ShareGrant, ShareResourceType } from '@/lib/api/share-grants'
import {
  useCreateShareGrant,
  useDeleteShareGrant,
  useShareGrants,
} from '@/lib/hooks/use-share-grants'
import { useTeams } from '@/lib/hooks/use-teams'
import { useTranslation } from '@/lib/hooks/use-translation'
import { OperationGuide } from '@/components/common/OperationGuide'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

interface ShareDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  resourceType: ShareResourceType
  resourceId: string
  resourceTitle: string
  onChanged?: (visibility: 'private' | 'public') => void
}

const EMPTY_TEAMS: NonNullable<ReturnType<typeof useTeams>['data']>['items'] = []

function grantLabel(grant: ShareGrant, teamNames: Map<string, string>, t: ReturnType<typeof useTranslation>['t']) {
  if (grant.target_type === 'team' && grant.target_id === PUBLIC_TEAM_ID) {
    return t.sharing.publicTarget
  }
  if (grant.target_type === 'team') {
    return teamNames.get(grant.target_id) || grant.target_id
  }
  return grant.target_id
}

export function ShareDialog({
  open,
  onOpenChange,
  resourceType,
  resourceId,
  resourceTitle,
  onChanged,
}: ShareDialogProps) {
  const { t } = useTranslation()
  const { data: grants, isLoading: grantsLoading, error: grantsError } = useShareGrants(resourceType, open ? resourceId : undefined)
  const { data: teamsData } = useTeams()
  const createGrant = useCreateShareGrant()
  const deleteGrant = useDeleteShareGrant(resourceType, resourceId)
  const [selectedTeamId, setSelectedTeamId] = useState('')
  const [confirmPublic, setConfirmPublic] = useState(false)
  const [confirmRevokeGrant, setConfirmRevokeGrant] = useState<ShareGrant | null>(null)

  const teams = teamsData?.items ?? EMPTY_TEAMS
  const teamNames = useMemo(
    () => new Map(teams.map((team) => [team.id, team.name])),
    [teams]
  )
  const publicGrant = (grants || []).find(
    (grant) => grant.target_type === 'team' && grant.target_id === PUBLIC_TEAM_ID
  )
  const shareableTeams = teams.filter(
    (team) =>
      team.type !== 'system' &&
      !(grants || []).some((grant) => grant.target_type === 'team' && grant.target_id === team.id)
  )

  useEffect(() => {
    if (!open) {
      setSelectedTeamId('')
      setConfirmPublic(false)
      setConfirmRevokeGrant(null)
    }
  }, [open])

  const isPending = createGrant.isPending || deleteGrant.isPending

  const sharePublic = () => {
    createGrant.mutate(
      {
        resource_type: resourceType,
        resource_id: resourceId,
        target_type: 'team',
        target_id: PUBLIC_TEAM_ID,
        permission: 'read',
      },
      {
        onSuccess: () => {
          setConfirmPublic(false)
          onChanged?.('public')
        },
      }
    )
  }

  const shareTeam = () => {
    if (!selectedTeamId) return
    createGrant.mutate(
      {
        resource_type: resourceType,
        resource_id: resourceId,
        target_type: 'team',
        target_id: selectedTeamId,
        permission: 'read',
      },
      {
        onSuccess: () => setSelectedTeamId(''),
      }
    )
  }

  const revokeGrant = (grant: ShareGrant) => {
    deleteGrant.mutate(grant.id, {
      onSuccess: () => {
        if (grant.target_type === 'team' && grant.target_id === PUBLIC_TEAM_ID) {
          onChanged?.('private')
        }
        setConfirmRevokeGrant(null)
      },
    })
  }

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Share2 className="h-5 w-5" />
              {t.sharing.title}
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-5">
            <div>
              <div className="text-sm font-medium">{resourceTitle}</div>
              <div className="text-sm text-muted-foreground">
                {resourceType === 'source' ? t.common.source : t.common.notebook}
              </div>
            </div>

            {grantsError ? (
              <Alert variant="destructive">
                <AlertTitle>{t.common.error}</AlertTitle>
                <AlertDescription>{t.sharing.manageDenied}</AlertDescription>
              </Alert>
            ) : (
              <>
                <Alert>
                  <Globe2 className="h-4 w-4" />
                  <AlertTitle>{t.sharing.publicShareNoticeTitle}</AlertTitle>
                  <AlertDescription>{t.sharing.publicShareNotice}</AlertDescription>
                </Alert>

                <OperationGuide
                  title={t.sharing.guideTitle}
                  description={t.sharing.guideDescription}
                  steps={[
                    t.sharing.guideChooseTarget,
                    t.sharing.guideConfirmScope,
                    t.sharing.guideReviewAccess,
                  ]}
                />

                <div className="rounded-md border">
                  <div className="flex flex-col gap-3 border-b p-4 sm:flex-row sm:items-center sm:justify-between">
                    <div className="flex items-start gap-3">
                      <Globe2 className="mt-0.5 h-5 w-5 text-muted-foreground" />
                      <div>
                        <div className="font-medium">{t.sharing.publicTarget}</div>
                        <div className="text-sm text-muted-foreground">{t.sharing.publicTargetDesc}</div>
                      </div>
                    </div>
                    {publicGrant ? (
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={isPending}
                        onClick={() => setConfirmRevokeGrant(publicGrant)}
                      >
                        <Trash2 className="h-4 w-4" />
                        {t.sharing.revokeShare}
                      </Button>
                    ) : (
                      <Button
                        size="sm"
                        disabled={isPending || grantsLoading}
                        onClick={() => setConfirmPublic(true)}
                      >
                        {isPending && <Loader2 className="h-4 w-4 animate-spin" />}
                        {t.sharing.shareToWeb}
                      </Button>
                    )}
                  </div>

                  <div className="space-y-4 p-4">
                    <div className="flex flex-col gap-3 sm:flex-row">
                      <Select value={selectedTeamId} onValueChange={setSelectedTeamId}>
                        <SelectTrigger className="w-full sm:flex-1">
                          <SelectValue placeholder={t.sharing.selectTeam} />
                        </SelectTrigger>
                        <SelectContent>
                          {shareableTeams.map((team) => (
                            <SelectItem key={team.id} value={team.id}>
                              {team.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <Button
                        variant="outline"
                        disabled={!selectedTeamId || isPending}
                        onClick={shareTeam}
                      >
                        <Users className="h-4 w-4" />
                        {t.sharing.shareToTeam}
                      </Button>
                    </div>

                    <div className="space-y-2">
                      <div className="text-sm font-medium">{t.sharing.currentGrants}</div>
                      {grantsLoading ? (
                        <div className="flex h-20 items-center justify-center">
                          <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                        </div>
                      ) : (grants || []).length === 0 ? (
                        <div className="rounded-md border border-dashed p-4 text-sm text-muted-foreground">
                          {t.sharing.noGrants}
                        </div>
                      ) : (
                        <div className="divide-y rounded-md border">
                          {(grants || []).map((grant) => (
                            <div key={grant.id} className="flex items-center justify-between gap-3 p-3">
                              <div className="min-w-0">
                                <div className="truncate text-sm font-medium">
                                  {grantLabel(grant, teamNames, t)}
                                </div>
                                <div className="text-xs text-muted-foreground">
                                  {grant.target_type === 'team' ? t.sharing.teamTarget : t.sharing.userTarget}
                                </div>
                              </div>
                              <div className="flex items-center gap-2">
                                <Badge variant="outline">{t.sharing.readOnly}</Badge>
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  disabled={isPending}
                                  onClick={() => setConfirmRevokeGrant(grant)}
                                  aria-label={t.sharing.revokeShare}
                                >
                                  <Trash2 className="h-4 w-4" />
                                </Button>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </>
            )}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => onOpenChange(false)}>
              {t.common.close}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={confirmPublic} onOpenChange={setConfirmPublic}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>{t.sharing.publicConfirmTitle}</DialogTitle>
          </DialogHeader>
          <Alert>
            <AlertTitle>{t.common.warning}</AlertTitle>
            <AlertDescription>{t.sharing.publicShareWarning}</AlertDescription>
          </Alert>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmPublic(false)}>
              {t.common.cancel}
            </Button>
            <Button onClick={sharePublic} disabled={isPending}>
              {isPending && <Loader2 className="h-4 w-4 animate-spin" />}
              {t.sharing.shareToWeb}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={!!confirmRevokeGrant} onOpenChange={(open) => !open && setConfirmRevokeGrant(null)}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>{t.sharing.revokeShare}</DialogTitle>
          </DialogHeader>
          {confirmRevokeGrant?.target_type === 'team' && confirmRevokeGrant.target_id === PUBLIC_TEAM_ID ? (
            <Alert>
              <AlertTitle>{t.common.warning}</AlertTitle>
              <AlertDescription>{t.sharing.publicRevokeWarning}</AlertDescription>
            </Alert>
          ) : (
            <p className="text-sm text-muted-foreground">{t.sharing.revokeTeamWarning}</p>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmRevokeGrant(null)}>
              {t.common.cancel}
            </Button>
            <Button
              variant="destructive"
              disabled={!confirmRevokeGrant || isPending}
              onClick={() => confirmRevokeGrant && revokeGrant(confirmRevokeGrant)}
            >
              {isPending && <Loader2 className="h-4 w-4 animate-spin" />}
              {t.sharing.revokeShare}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
