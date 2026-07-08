'use client'

import { useMemo, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { useTranslation } from '@/lib/hooks/use-translation'
import { useNotebooks } from '@/lib/hooks/use-notebooks'
import {
  useCreateReview,
  useReviewStatus,
  useReviewReport,
  useReviewConfig,
  useRecentReviewPaths,
} from '@/lib/hooks/use-review'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Popover,
  PopoverAnchor,
  PopoverContent,
} from '@/components/ui/popover'
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandItem,
  CommandList,
} from '@/components/ui/command'
import { RepoBrowseButton } from '@/components/search/RepoBrowseButton'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { AlertCircle, FolderGit2 } from 'lucide-react'
import { getApiErrorMessage } from '@/lib/utils/error-handler'

// `key` matches the backend verdict values; `labelKey` is referenced literally so
// the i18n unused-key check can see it.
const VERDICTS: { key: string; labelKey: string; emoji: string; className: string }[] = [
  { key: 'follows', labelKey: 'reviewPage.verdictFollows', emoji: '✅', className: 'bg-green-100 text-green-800 dark:bg-green-950/40 dark:text-green-300' },
  { key: 'partial', labelKey: 'reviewPage.verdictPartial', emoji: '🟡', className: 'bg-amber-100 text-amber-800 dark:bg-amber-950/40 dark:text-amber-300' },
  { key: 'violates', labelKey: 'reviewPage.verdictViolates', emoji: '❌', className: 'bg-red-100 text-red-800 dark:bg-red-950/40 dark:text-red-300' },
  { key: 'not-found', labelKey: 'reviewPage.verdictNotFound', emoji: '⚪', className: 'bg-muted text-muted-foreground' },
]

export function ReviewCodePanel() {
  const { t } = useTranslation()
  const { data: notebooks } = useNotebooks()

  const [notebookId, setNotebookId] = useState<string>('')
  const [repoPath, setRepoPath] = useState('')
  const [theme, setTheme] = useState('')
  const [reviewId, setReviewId] = useState<string | null>(null)
  const [pathPopoverOpen, setPathPopoverOpen] = useState(false)
  const { data: reviewConfig } = useReviewConfig()
  const { data: recentPaths } = useRecentReviewPaths()
  const allowedRoots = reviewConfig?.allowed_roots ?? []

  const createReview = useCreateReview()
  const { data: review } = useReviewStatus(reviewId)
  const { data: reportNote } = useReviewReport(
    review?.status === 'completed' ? review?.report_note_id : null
  )

  const isRunning = !!reviewId && review?.status !== 'completed' && review?.status !== 'failed'

  const canSubmit = theme.trim() && repoPath.trim() && notebookId && !createReview.isPending && !isRunning

  const handleSubmit = () => {
    if (!canSubmit) return
    setReviewId(null)
    createReview.mutate(
      { theme: theme.trim(), repo_path: repoPath.trim(), notebook_id: notebookId },
      { onSuccess: (created) => setReviewId(created.id) }
    )
  }

  const submitError = createReview.isError
    ? getApiErrorMessage(createReview.error, t, 'reviewPage.submitError')
    : null

  const statusLabel = useMemo(() => {
    if (createReview.isPending) return t('reviewPage.submitting')
    if (!review) return null
    switch (review.status) {
      case 'queued':
        return t('reviewPage.statusQueued')
      case 'running':
        return t('reviewPage.statusRunning')
      case 'completed':
        return t('reviewPage.statusCompleted')
      case 'failed':
        return t('reviewPage.statusFailed')
      default:
        return review.status
    }
  }, [review, createReview.isPending, t])

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg flex items-center gap-2">
          <FolderGit2 className="h-5 w-5" />
          {t('reviewPage.title')}
        </CardTitle>
        <p className="text-sm text-muted-foreground">{t('reviewPage.description')}</p>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Notebook picker */}
        <div className="space-y-2">
          <Label htmlFor="review-notebook">{t('reviewPage.notebook')}</Label>
          <Select value={notebookId} onValueChange={setNotebookId} disabled={isRunning}>
            <SelectTrigger id="review-notebook">
              <SelectValue placeholder={t('reviewPage.notebookPlaceholder')} />
            </SelectTrigger>
            <SelectContent>
              {(notebooks || []).map((nb) => (
                <SelectItem key={nb.id} value={nb.id}>
                  {nb.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <p className="text-xs text-muted-foreground">{t('reviewPage.notebookHelp')}</p>
        </div>

        {/* Repo path */}
        <div className="space-y-2">
          <Label htmlFor="review-path">{t('reviewPage.repoPath')}</Label>
          <Popover open={pathPopoverOpen} onOpenChange={setPathPopoverOpen}>
            <PopoverAnchor>
              <Input
                id="review-path"
                placeholder={t('reviewPage.repoPathPlaceholder')}
                value={repoPath}
                onChange={(e) => setRepoPath(e.target.value)}
                onFocus={() => setPathPopoverOpen(true)}
                disabled={isRunning}
                autoComplete="off"
              />
            </PopoverAnchor>
            <PopoverContent
              className="w-[--radix-popover-trigger-width] p-0"
              align="start"
              onOpenAutoFocus={(e) => e.preventDefault()}
            >
              <Command shouldFilter={false}>
                <CommandList>
                  <CommandEmpty>{t('reviewPage.repoPathNoRecents')}</CommandEmpty>
                  <CommandGroup heading={t('reviewPage.repoPathRecent')}>
                    {(recentPaths || [])
                      .filter(
                        (path) =>
                          !repoPath.trim() ||
                          path.toLowerCase().includes(repoPath.trim().toLowerCase())
                      )
                      .map((path) => (
                        <CommandItem
                          key={path}
                          value={path}
                          onSelect={() => {
                            setRepoPath(path)
                            setPathPopoverOpen(false)
                          }}
                        >
                          {path}
                        </CommandItem>
                      ))}
                  </CommandGroup>
                </CommandList>
              </Command>
            </PopoverContent>
          </Popover>
          <p className="text-xs text-muted-foreground">{t('reviewPage.repoPathHelp')}</p>
          {allowedRoots.length > 0 && (
            <RepoBrowseButton
              allowedRoots={allowedRoots}
              disabled={isRunning}
              onPick={setRepoPath}
            />
          )}
        </div>

        {/* Theme */}
        <div className="space-y-2">
          <Label htmlFor="review-theme">{t('reviewPage.theme')}</Label>
          <Textarea
            id="review-theme"
            placeholder={t('reviewPage.themePlaceholder')}
            value={theme}
            onChange={(e) => setTheme(e.target.value)}
            disabled={isRunning}
            rows={3}
          />
          <p className="text-xs text-muted-foreground">{t('reviewPage.themeHelp')}</p>
        </div>

        <Button onClick={handleSubmit} disabled={!canSubmit} className="w-full">
          {createReview.isPending || isRunning ? (
            <>
              <LoadingSpinner size="sm" className="mr-2" />
              {statusLabel}
            </>
          ) : (
            t('reviewPage.startReview')
          )}
        </Button>

        {submitError && (
          <div className="flex items-center gap-2 p-3 text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-950/20 rounded-md">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{submitError}</span>
          </div>
        )}

        {/* Live status while running */}
        {isRunning && (
          <div className="flex items-center gap-2 p-3 text-sm text-muted-foreground bg-muted/50 rounded-md">
            <LoadingSpinner size="sm" />
            <span>{t('reviewPage.runningHint')}</span>
          </div>
        )}

        {/* Failed */}
        {review?.status === 'failed' && (
          <div className="flex items-start gap-2 p-3 text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-950/20 rounded-md">
            <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
            <span>{review.error_message || t('reviewPage.statusFailed')}</span>
          </div>
        )}

        {/* Completed: verdict summary + report */}
        {review?.status === 'completed' && (
          <div className="space-y-4">
            {review.summary && (
              <div className="flex flex-wrap gap-2">
                {VERDICTS.map((v) => (
                  <Badge key={v.key} variant="secondary" className={v.className}>
                    {v.emoji} {t(v.labelKey)}: {review.summary?.[v.key] ?? 0}
                  </Badge>
                ))}
              </div>
            )}

            {reportNote ? (
              <div className="prose prose-sm max-w-none dark:prose-invert break-words rounded-md border p-4">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {reportNote.content || ''}
                </ReactMarkdown>
              </div>
            ) : (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <LoadingSpinner size="sm" />
                {t('reviewPage.loadingReport')}
              </div>
            )}

            <p className="text-xs text-muted-foreground">{t('reviewPage.savedAsNote')}</p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
