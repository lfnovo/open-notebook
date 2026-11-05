'use client'

import { useCallback, useMemo, useState } from 'react'
import { FileText, Loader2, Upload } from 'lucide-react'

import { useReadScriptPodcast, useSpeakerProfiles } from '@/lib/hooks/use-podcasts'
import { useTranslation } from '@/lib/hooks/use-translation'
import { useToast } from '@/lib/hooks/use-toast'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { cn } from '@/lib/utils'

const SCRIPT_FILE_RE = /\.(txt|md|markdown)$/i
export const MAX_SCRIPT_CHARS = 500_000

export function isScriptFile(file: File): boolean {
  return SCRIPT_FILE_RE.test(file.name) || file.type === 'text/plain' || file.type === 'text/markdown'
}

interface ReadScriptDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function ReadScriptDialog({ open, onOpenChange }: ReadScriptDialogProps) {
  const { t } = useTranslation()
  const { toast } = useToast()
  const { speakerProfiles, isLoading } = useSpeakerProfiles()
  const readScript = useReadScriptPodcast()

  const [profileId, setProfileId] = useState('')
  const [episodeName, setEpisodeName] = useState('')
  const [script, setScript] = useState('')
  const [fileName, setFileName] = useState<string | null>(null)
  const [dragging, setDragging] = useState(false)

  const selectedProfile = useMemo(
    () => speakerProfiles.find((p) => p.id === profileId),
    [speakerProfiles, profileId]
  )

  const reset = () => {
    setProfileId('')
    setEpisodeName('')
    setScript('')
    setFileName(null)
    setDragging(false)
  }

  const loadFile = useCallback(
    async (file: File | undefined) => {
      if (!file) return
      if (!isScriptFile(file)) {
        toast({ title: t('podcasts.scriptUnsupportedFile'), variant: 'destructive' })
        return
      }
      const text = await file.text()
      setScript(text)
      setFileName(file.name)
      setEpisodeName((name) => name || file.name.replace(SCRIPT_FILE_RE, ''))
    },
    [t, toast]
  )

  const tooLong = script.length > MAX_SCRIPT_CHARS
  const canSubmit =
    !!selectedProfile && episodeName.trim() !== '' && script.trim() !== '' && !tooLong && !readScript.isPending

  const handleSubmit = async () => {
    if (!selectedProfile) return
    await readScript.mutateAsync({
      speaker_profile: selectedProfile.id,
      episode_name: episodeName.trim(),
      script,
    })
    onOpenChange(false)
    reset()
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(value) => {
        onOpenChange(value)
        if (!value) reset()
      }}
    >
      <DialogContent className="w-[90vw] max-w-[760px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{t('podcasts.readScriptTitle')}</DialogTitle>
          <DialogDescription>{t('podcasts.readScriptDesc')}</DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="script_speaker_profile">{t('podcasts.speakerProfile')}</Label>
              <Select value={profileId} onValueChange={setProfileId} disabled={isLoading}>
                <SelectTrigger id="script_speaker_profile">
                  <SelectValue placeholder={t('podcasts.scriptVoicePlaceholder')} />
                </SelectTrigger>
                <SelectContent>
                  {speakerProfiles.map((profile) => (
                    <SelectItem key={profile.id} value={profile.id} disabled={!profile.voice_model}>
                      {profile.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {selectedProfile ? (
                <p className="text-xs text-muted-foreground">
                  {t('podcasts.scriptSpeakers')}{' '}
                  <strong>{selectedProfile.speakers.map((s) => s.name).join(', ')}</strong>
                </p>
              ) : null}
            </div>
            <div className="space-y-2">
              <Label htmlFor="script_episode_name">{t('podcasts.episodeName')}</Label>
              <Input
                id="script_episode_name"
                value={episodeName}
                onChange={(event) => setEpisodeName(event.target.value)}
                placeholder={t('podcasts.episodeNamePlaceholder')}
                autoComplete="off"
              />
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between gap-2">
              <Label htmlFor="script_text">{t('podcasts.scriptLabel')}</Label>
              <Button asChild variant="outline" size="sm">
                <label className="cursor-pointer">
                  <Upload className="mr-2 h-4 w-4" />
                  {t('podcasts.scriptChooseFile')}
                  <input
                    type="file"
                    accept=".txt,.md,.markdown,text/plain,text/markdown"
                    className="hidden"
                    data-testid="script-file-input"
                    onChange={(event) => {
                      void loadFile(event.target.files?.[0])
                      event.target.value = ''
                    }}
                  />
                </label>
              </Button>
            </div>
            <div
              data-testid="script-drop-zone"
              onDragOver={(event) => {
                event.preventDefault()
                setDragging(true)
              }}
              onDragLeave={() => setDragging(false)}
              onDrop={(event) => {
                event.preventDefault()
                setDragging(false)
                void loadFile(event.dataTransfer.files?.[0])
              }}
              className={cn('relative rounded-md', dragging && 'ring-2 ring-primary')}
            >
              <Textarea
                id="script_text"
                value={script}
                onChange={(event) => {
                  setScript(event.target.value)
                  setFileName(null)
                }}
                placeholder={t('podcasts.scriptPlaceholder')}
                className="min-h-[260px] font-mono text-xs"
              />
              {dragging ? (
                <div className="pointer-events-none absolute inset-0 flex items-center justify-center rounded-md bg-background/80 text-sm font-medium">
                  {t('podcasts.scriptDropHere')}
                </div>
              ) : null}
            </div>
            <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
              <span className="flex items-center gap-1">
                {fileName ? (
                  <>
                    <FileText className="h-3.5 w-3.5" /> {fileName}
                  </>
                ) : (
                  t('podcasts.scriptHint')
                )}
              </span>
              <span className={cn(tooLong && 'text-destructive')}>
                {t('podcasts.scriptChars', { chars: script.length.toLocaleString() })}
              </span>
            </div>
          </div>

          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => onOpenChange(false)} disabled={readScript.isPending}>
              {t('common.cancel')}
            </Button>
            <Button onClick={handleSubmit} disabled={!canSubmit}>
              {readScript.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {t('podcasts.readScriptSubmit')}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
