'use client'

import { useMemo, useState } from 'react'
import { Copy, Edit3, MoreVertical, Trash2, Users } from 'lucide-react'

import { EpisodeProfile, SpeakerProfile } from '@/lib/types/podcasts'
import {
  useDeleteEpisodeProfile,
  useDuplicateEpisodeProfile,
} from '@/lib/hooks/use-podcasts'
import { EpisodeProfileFormDialog } from '@/components/podcasts/forms/EpisodeProfileFormDialog'
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

interface EpisodeProfilesPanelProps {
  episodeProfiles: EpisodeProfile[]
  speakerProfiles: SpeakerProfile[]
  modelOptions: Record<string, string[]>
}

function findSpeakerSummary(
  speakerProfiles: SpeakerProfile[],
  speakerName: string
) {
  return speakerProfiles.find((profile) => profile.name === speakerName)
}

export function EpisodeProfilesPanel({
  episodeProfiles,
  speakerProfiles,
  modelOptions,
}: EpisodeProfilesPanelProps) {
  const [createOpen, setCreateOpen] = useState(false)
  const [editProfile, setEditProfile] = useState<EpisodeProfile | null>(null)

  const deleteProfile = useDeleteEpisodeProfile()
  const duplicateProfile = useDuplicateEpisodeProfile()

  const sortedProfiles = useMemo(
    () =>
      [...episodeProfiles].sort((a, b) => a.name.localeCompare(b.name, 'en')), 
    [episodeProfiles]
  )

  const disableCreate = speakerProfiles.length === 0

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold">Episode profiles</h2>
          <p className="text-sm text-muted-foreground">
            Define reusable generation settings for your shows.
          </p>
        </div>
        <Button onClick={() => setCreateOpen(true)} disabled={disableCreate}>
          Create profile
        </Button>
      </div>

      {disableCreate ? (
        <p className="rounded-lg border border-dashed bg-amber-50 p-4 text-sm text-amber-900">
          Create a speaker profile before adding an episode profile.
        </p>
      ) : null}

      {sortedProfiles.length === 0 ? (
        <div className="rounded-lg border border-dashed bg-muted/30 p-10 text-center text-sm text-muted-foreground">
          No episode profiles yet. Create one to kickstart podcast generation.
        </div>
      ) : (
        <div className="space-y-4">
          {sortedProfiles.map((profile) => {
            const speakerSummary = findSpeakerSummary(
              speakerProfiles,
              profile.speaker_config
            )

            return (
              <Card key={profile.id} className="shadow-sm">
                <CardHeader className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
                  <div>
                    <CardTitle className="text-lg font-semibold">
                      {profile.name}
                    </CardTitle>
                    <CardDescription className="text-sm text-muted-foreground">
                      {profile.description || 'No description provided.'}
                    </CardDescription>
                  </div>
                  <div className="flex items-center gap-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setEditProfile(profile)}
                    >
                      <Edit3 className="mr-2 h-4 w-4" /> Edit
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
                          className="w-44"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <DropdownMenuItem
                            onClick={() => duplicateProfile.mutate(profile.id)}
                            disabled={duplicateProfile.isPending}
                          >
                            <Copy className="h-4 w-4 mr-2" />
                            Duplicate
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <AlertDialogTrigger asChild>
                            <DropdownMenuItem className="text-destructive focus:text-destructive">
                              <Trash2 className="h-4 w-4 mr-2" />
                              Delete
                            </DropdownMenuItem>
                          </AlertDialogTrigger>
                        </DropdownMenuContent>
                      </DropdownMenu>
                      <AlertDialogContent>
                        <AlertDialogHeader>
                          <AlertDialogTitle>Delete profile?</AlertDialogTitle>
                          <AlertDialogDescription>
                            This will remove “{profile.name}”. Existing episodes keep their
                            data, but new ones will no longer use this configuration.
                          </AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                          <AlertDialogCancel>Cancel</AlertDialogCancel>
                          <AlertDialogAction
                            onClick={() => deleteProfile.mutate(profile.id)}
                            disabled={deleteProfile.isPending}
                          >
                            {deleteProfile.isPending ? 'Deleting…' : 'Delete'}
                          </AlertDialogAction>
                        </AlertDialogFooter>
                      </AlertDialogContent>
                    </AlertDialog>
                  </div>
                </CardHeader>

                <CardContent className="space-y-4 text-sm">
                  <div className="grid gap-3 md:grid-cols-2">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                        Outline model
                      </p>
                      <p className="text-foreground">
                        {profile.outline_provider} / {profile.outline_model}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                        Transcript model
                      </p>
                      <p className="text-foreground">
                        {profile.transcript_provider} / {profile.transcript_model}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                        Segments
                      </p>
                      <p className="text-foreground">{profile.num_segments}</p>
                    </div>
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                        Speaker profile
                      </p>
                      <div className="flex items-center gap-2 text-foreground">
                        <Users className="h-4 w-4" />
                        <span>{profile.speaker_config}</span>
                        {speakerSummary ? (
                          <Badge variant="outline" className="text-xs">
                            {speakerSummary.tts_provider} / {speakerSummary.tts_model}
                          </Badge>
                        ) : null}
                      </div>
                    </div>
                  </div>

                  {profile.default_briefing ? (
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                        Default briefing
                      </p>
                      <p className="mt-1 whitespace-pre-wrap text-muted-foreground">
                        {profile.default_briefing}
                      </p>
                    </div>
                  ) : null}
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}

      <EpisodeProfileFormDialog
        mode="create"
        open={createOpen}
        onOpenChange={setCreateOpen}
        speakerProfiles={speakerProfiles}
        modelOptions={modelOptions}
      />

      <EpisodeProfileFormDialog
        mode="edit"
        open={Boolean(editProfile)}
        onOpenChange={(open) => {
          if (!open) {
            setEditProfile(null)
          }
        }}
        speakerProfiles={speakerProfiles}
        modelOptions={modelOptions}
        initialData={editProfile ?? undefined}
      />
    </div>
  )
}
