'use client'

import { useMemo, useState } from 'react'
import { AlertTriangle, Copy, Edit3, MoreVertical, Trash2, Volume2 } from 'lucide-react'

import { SpeakerProfile, needsModelSetup } from '@/lib/types/podcasts'
import {
  useDeleteSpeakerProfile,
  useDuplicateSpeakerProfile,
} from '@/lib/hooks/use-podcasts'
import { useModels } from '@/lib/hooks/use-models'
import { SpeakerProfileFormDialog } from '@/components/podcasts/forms/SpeakerProfileFormDialog'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useTranslation } from '@/lib/hooks/use-translation'

interface SpeakerProfilesPanelProps {
  speakerProfiles: SpeakerProfile[]
  usage: Record<string, number>
}

export function SpeakerProfilesPanel({
  speakerProfiles,
  usage,
}: SpeakerProfilesPanelProps) {
  const { t } = useTranslation()
  const [createOpen, setCreateOpen] = useState(false)
  const [editProfile, setEditProfile] = useState<SpeakerProfile | null>(null)

  const deleteProfile = useDeleteSpeakerProfile()
  const duplicateProfile = useDuplicateSpeakerProfile()
  const { data: models = [] } = useModels()

  const modelNameMap = useMemo(() => {
    const map: Record<string, string> = {}
    for (const m of models) {
      map[m.id] = `${m.provider} / ${m.name}`
    }
    return map
  }, [models])

  const sortedProfiles = useMemo(
    () =>
      [...speakerProfiles].sort((a, b) => a.name.localeCompare(b.name, 'en')),
    [speakerProfiles]
  )

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold">{t.podcasts.speakerProfilesTitle}</h2>
          <p className="text-sm text-muted-foreground">
            {t.podcasts.speakerProfilesDesc}
          </p>
        </div>
        <Button onClick={() => setCreateOpen(true)}>{t.podcasts.createSpeaker}</Button>
      </div>

      {sortedProfiles.length === 0 ? (
        <div className="rounded-lg border border-dashed bg-muted/30 p-8 text-center text-sm text-muted-foreground">
          {t.podcasts.noSpeakerProfiles}
        </div>
      ) : (
        <div className="space-y-4">
          {sortedProfiles.map((profile) => {
            const usageCount = usage[profile.name] ?? 0
            const deleteDisabled = usageCount > 0
            const unconfigured = needsModelSetup(profile)

            return (
              <Card key={profile.id} className="shadow-sm">
                <CardHeader className="flex flex-col gap-2">
                  <div className="flex items-center justify-between gap-2">
                    <div>
                      <div className="flex items-center gap-2">
                        <CardTitle className="text-lg font-semibold">
                          {profile.name}
                        </CardTitle>
                        {unconfigured ? (
                          <Badge variant="outline" className="text-amber-600 border-amber-300 text-xs">
                            <AlertTriangle className="h-3 w-3 mr-1" />
                            {t.podcasts.setupRequired}
                          </Badge>
                        ) : null}
                      </div>
                      <CardDescription className="text-sm text-muted-foreground">
                        {profile.description || t.podcasts.noDescription}
                      </CardDescription>
                    </div>
                    <Badge variant="outline" className="text-xs">
                      {profile.voice_model
                        ? (modelNameMap[profile.voice_model] ?? profile.voice_model)
                        : (profile.tts_provider
                          ? `${profile.tts_provider} / ${profile.tts_model}`
                          : t.podcasts.notConfigured)}
                    </Badge>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Badge
                      variant={usageCount > 0 ? 'secondary' : 'outline'}
                      className="text-xs"
                    >
                      {usageCount > 0
                        ? (usageCount === 1 ? t.podcasts.usedByCount_one : t.podcasts.usedByCount_other.replace('{count}', usageCount.toString()))
                        : t.podcasts.unused}
                    </Badge>
                  </div>
                </CardHeader>

                <CardContent className="space-y-4 text-sm">
                  <div className="space-y-3">
                    {profile.speakers.map((speaker) => (
                      <div
                        key={speaker.name}
                        className="rounded-md border bg-muted/30 p-3"
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <Volume2 className="h-4 w-4" />
                            <span className="font-medium text-foreground">
                              {speaker.name}
                            </span>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-muted-foreground">
                              {t.podcasts.voiceId}: {speaker.voice_id}
                            </span>
                            {speaker.voice_model ? (
                              <Badge variant="secondary" className="text-xs">
                                {modelNameMap[speaker.voice_model] ?? speaker.voice_model}
                              </Badge>
                            ) : null}
                          </div>
                        </div>
                        <p className="mt-2 text-xs text-muted-foreground whitespace-pre-wrap">
                          <span className="font-semibold">{t.podcasts.backstory}:</span> {speaker.backstory}
                        </p>
                        <p className="mt-2 text-xs text-muted-foreground whitespace-pre-wrap">
                          <span className="font-semibold">{t.podcasts.personality}:</span> {speaker.personality}
                        </p>
                      </div>
                    ))}
                  </div>

                  <div className="flex flex-wrap items-center justify-end gap-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setEditProfile(profile)}
                    >
                      <Edit3 className="mr-2 h-4 w-4" /> {t.podcasts.edit}
                    </Button>
                    <AlertDialog>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8"
                            onClick={(e) => e.stopPropagation()}
                          >
                            <MoreVertical className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent
                          align="end"
                          className="w-48"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <DropdownMenuItem
                            onClick={() => duplicateProfile.mutate(profile.id)}
                            disabled={duplicateProfile.isPending}
                          >
                            <Copy className="h-4 w-4 mr-2" />
                            {t.podcasts.duplicate}
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <AlertDialogTrigger asChild>
                            <DropdownMenuItem
                              className="text-destructive focus:text-destructive"
                              disabled={deleteDisabled}
                            >
                              <Trash2 className="h-4 w-4 mr-2" />
                              {t.podcasts.delete}
                            </DropdownMenuItem>
                          </AlertDialogTrigger>
                        </DropdownMenuContent>
                      </DropdownMenu>
                      <AlertDialogContent>
                        <AlertDialogHeader>
                          <AlertDialogTitle>{t.podcasts.deleteSpeakerProfileTitle}</AlertDialogTitle>
                          <AlertDialogDescription>
                            {t.podcasts.deleteSpeakerProfileDesc.replace('{name}', profile.name)}
                          </AlertDialogDescription>
                          {deleteDisabled ? (
                            <p className="mt-2 text-sm text-muted-foreground">
                              {t.podcasts.deleteSpeakerDisabledHint}
                            </p>
                          ) : null}
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                          <AlertDialogCancel>{t.common.cancel}</AlertDialogCancel>
                          <AlertDialogAction
                            onClick={() => deleteProfile.mutate(profile.id)}
                            disabled={deleteDisabled || deleteProfile.isPending}
                          >
                            {deleteProfile.isPending ? t.podcasts.deleting : t.podcasts.delete}
                          </AlertDialogAction>
                        </AlertDialogFooter>
                      </AlertDialogContent>
                    </AlertDialog>
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}

      <SpeakerProfileFormDialog
        mode="create"
        open={createOpen}
        onOpenChange={setCreateOpen}
      />

      <SpeakerProfileFormDialog
        mode="edit"
        open={Boolean(editProfile)}
        onOpenChange={(open) => {
          if (!open) {
            setEditProfile(null)
          }
        }}
        initialData={editProfile ?? undefined}
      />
    </div>
  )
}
