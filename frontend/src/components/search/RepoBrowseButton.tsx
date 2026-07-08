'use client'

import { useRef, useState } from 'react'
import { useTranslation } from '@/lib/hooks/use-translation'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { FolderOpen } from 'lucide-react'

export function joinRepoPath(root: string, folderName: string): string {
  return `${root.replace(/\/+$/, '')}/${folderName}`
}

interface RepoBrowseButtonProps {
  allowedRoots: string[]
  disabled?: boolean
  onPick: (path: string) => void
}

export function RepoBrowseButton({ allowedRoots, disabled, onPick }: RepoBrowseButtonProps) {
  const { t } = useTranslation()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [selectedRoot, setSelectedRoot] = useState(allowedRoots[0])

  const handleBrowseClick = () => {
    // Reset so re-picking the same folder still fires onChange.
    if (fileInputRef.current) fileInputRef.current.value = ''
    fileInputRef.current?.click()
  }

  const handleFilesSelected = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files || files.length === 0) return
    // A browser can only ever expose the top-level picked folder's name — never
    // an absolute path, and never anything about folders above it.
    const relativePath = (files[0] as File & { webkitRelativePath?: string }).webkitRelativePath
    const folderName = relativePath ? relativePath.split('/')[0] : files[0].name
    onPick(joinRepoPath(selectedRoot, folderName))
  }

  return (
    <div className="space-y-1">
      <div className="flex items-center gap-2">
        {allowedRoots.length > 1 && (
          <Select value={selectedRoot} onValueChange={setSelectedRoot} disabled={disabled}>
            <SelectTrigger className="w-[220px]" size="sm">
              <SelectValue placeholder={t('reviewPage.repoPathBrowseRoot')} />
            </SelectTrigger>
            <SelectContent>
              {allowedRoots.map((root) => (
                <SelectItem key={root} value={root}>
                  {root}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={disabled}
          onClick={handleBrowseClick}
        >
          <FolderOpen className="h-4 w-4" />
          {t('reviewPage.repoPathBrowse')}
        </Button>
      </div>
      <p className="text-xs text-muted-foreground">{t('reviewPage.repoPathBrowseHelp')}</p>
      <input
        ref={fileInputRef}
        type="file"
        className="hidden"
        onChange={handleFilesSelected}
        // @ts-expect-error non-standard attribute, not in React's DOM typings
        webkitdirectory=""
        // @ts-expect-error non-standard attribute, not in React's DOM typings
        directory=""
      />
    </div>
  )
}
