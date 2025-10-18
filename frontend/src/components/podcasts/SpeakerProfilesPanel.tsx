'use client'

import { useMemo, useState } from 'react'
import { Copy, Edit3, MoreVertical, Trash2, Volume2 } from 'lucide-react'

import { SpeakerProfile } from '@/lib/types/podcasts'
import {
  useDeleteSpeakerProfile,
  useDuplicateSpeakerProfile,
} from '@/lib/hooks/use-podcasts'
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

interface SpeakerProfilesPanelProps {
  speakerProfiles: SpeakerProfile[]
  modelOptions: Record<string, string[]>
  usage: Record<string, number>
}

export function SpeakerProfilesPanel({
  speakerProfiles,
  modelOptions,
  usage,
}: SpeakerProfilesPanelProps) {
  const [createOpen, setCreateOpen] = useState(false)
  const [editProfile, setEditProfile] = useState<SpeakerProfile | null>(null)

  const deleteProfile = useDeleteSpeakerProfile()
  const duplicateProfile = useDuplicateSpeakerProfile()

  const sortedProfiles = useMemo(
    () =>
      [...speakerProfiles].sort((a, b) => a.name.localeCompare(b.name, 'en')), 
    [speakerProfiles]
  )

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold">Speaker profiles</h2>
          <p className="text-sm text-muted-foreground">
            Configure voices and personalities for generated episodes.
          </p>
        </div>
        <Button onClick={() => setCreateOpen(true)}>Create speaker</Button>
      </div>

      {sortedProfiles.length === 0 ? (
        <div className="rounded-lg border border-dashed bg-muted/30 p-8 text-center text-sm text-muted-foreground">
          No speaker profiles yet. Create one to make episode templates available.
        </div>
      ) : (
        <div className="space-y-4">
          {sortedProfiles.map((profile) => {
            const usageCount = usage[profile.name] ?? 0
            const deleteDisabled = usageCount > 0

            return (
              <Card key={profile.id} className="shadow-sm">
                <CardHeader className="flex flex-col gap-2">
                  <div className="flex items-center justify-between gap-2">
                    <div>
                      <CardTitle className="text-lg font-semibold">
                        {profile.name}
                      </CardTitle>
                      <CardDescription className="text-sm text-muted-foreground">
                        {profile.description || 'No description provided.'}
                      </CardDescription>
                    </div>
                    <Badge variant="outline" className="text-xs">
                      {profile.tts_provider} / {profile.tts_model}
                    </Badge>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Badge
                      variant={usageCount > 0 ? 'secondary' : 'outline'}
                      className="text-xs"
                    >
                      {usageCount > 0
                        ? `Used by ${usageCount} episode${usageCount === 1 ? '' : 's'}`
                        : 'Unused'}
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
                          <span className="text-xs text-muted-foreground">
                            Voice ID: {speaker.voice_id}
                          </span>
                        </div>
                        <p className="mt-2 text-xs text-muted-foreground whitespace-pre-wrap">
                          <span className="font-semibold">Backstory:</span> {speaker.backstory}
                        </p>
                        <p className="mt-2 text-xs text-muted-foreground whitespace-pre-wrap">
                          <span className="font-semibold">Personality:</span> {speaker.personality}
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
                          className="w-48"
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
                            <DropdownMenuItem
                              className="text-destructive focus:text-destructive"
                              disabled={deleteDisabled}
                            >
                              <Trash2 className="h-4 w-4 mr-2" />
                              Delete
                            </DropdownMenuItem>
                          </AlertDialogTrigger>
                        </DropdownMenuContent>
                      </DropdownMenu>
                      <AlertDialogContent>
                        <AlertDialogHeader>
                          <AlertDialogTitle>Delete speaker profile?</AlertDialogTitle>
                          <AlertDialogDescription>
                            Deleting “{profile.name}” cannot be undone.
                          </AlertDialogDescription>
                          {deleteDisabled ? (
                            <p className="mt-2 text-sm text-muted-foreground">
                              Remove this speaker from episode profiles before deleting it.
                            </p>
                          ) : null}
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                          <AlertDialogCancel>Cancel</AlertDialogCancel>
                          <AlertDialogAction
                            onClick={() => deleteProfile.mutate(profile.id)}
                            disabled={deleteDisabled || deleteProfile.isPending}
                          >
                            {deleteProfile.isPending ? 'Deleting…' : 'Delete'}
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
        modelOptions={modelOptions}
      />

      <SpeakerProfileFormDialog
        mode="edit"
        open={Boolean(editProfile)}
        onOpenChange={(open) => {
          if (!open) {
            setEditProfile(null)
          }
        }}
        modelOptions={modelOptions}
        initialData={editProfile ?? undefined}
      />
    </div>
  )
}
