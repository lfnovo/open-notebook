'use client'

import { useEffect, useState } from 'react'
import { useDebounce } from 'use-debounce'
import Link from 'next/link'
import { FileIcon, LoaderIcon, Search } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Label } from '@/components/ui/label'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { useTranslation } from '@/lib/hooks/use-translation'
import { useDriveStatus, useDriveFiles, useImportDriveFile } from '@/lib/hooks/use-drive'
import { DriveFile } from '@/lib/types/drive'
import { NotebookResponse } from '@/lib/types/api'

interface DriveImportPanelProps {
  notebooks: NotebookResponse[]
  notebooksLoading: boolean
  defaultNotebookId?: string
  onImported: () => void
  onCancel: () => void
}

export function DriveImportPanel({
  notebooks,
  notebooksLoading,
  defaultNotebookId,
  onImported,
  onCancel,
}: DriveImportPanelProps) {
  const { t } = useTranslation()
  const { data: status, isLoading: statusLoading } = useDriveStatus()
  const connected = status?.connected ?? false

  const [notebookId, setNotebookId] = useState(defaultNotebookId ?? '')
  const [searchInput, setSearchInput] = useState('')
  const [debouncedQuery] = useDebounce(searchInput, 300)
  const [pageToken, setPageToken] = useState<string | undefined>(undefined)
  const [allFiles, setAllFiles] = useState<DriveFile[]>([])
  const [selectedFileId, setSelectedFileId] = useState<string | null>(null)

  const { data, isLoading, isFetching, isError } = useDriveFiles(
    debouncedQuery,
    pageToken,
    connected
  )
  const importFile = useImportDriveFile()

  // Reset pagination/selection whenever the search term changes.
  useEffect(() => {
    setPageToken(undefined)
    setSelectedFileId(null)
  }, [debouncedQuery])

  // Replace the list on a fresh search (pageToken undefined), append on "load more".
  useEffect(() => {
    if (!data) return
    setAllFiles((prev) => (pageToken ? [...prev, ...data.files] : data.files))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data])

  const handleImport = async () => {
    if (!selectedFileId || !notebookId) return
    try {
      await importFile.mutateAsync({ file_id: selectedFileId, notebook_id: notebookId })
      onImported()
    } catch {
      // Error toast handled by the hook's onError
    }
  }

  const formatDate = (value?: string | null) => {
    if (!value) return ''
    try {
      return new Date(value).toLocaleDateString()
    } catch {
      return ''
    }
  }

  if (statusLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
        <LoaderIcon className="h-8 w-8 mb-2 animate-spin" />
        <p>{t('common.loading')}</p>
      </div>
    )
  }

  if (!connected) {
    return (
      <div className="py-8">
        <Alert>
          <AlertDescription className="flex flex-col gap-3">
            <span>{t('drive.connectPromptDesc')}</span>
            <Link href="/settings" className="text-sm text-primary hover:underline w-fit">
              {t('drive.goToSettings')}
            </Link>
          </AlertDescription>
        </Alert>
      </div>
    )
  }

  const needsNotebookPicker = !defaultNotebookId

  return (
    <div className="space-y-4">
      {needsNotebookPicker && (
        <div className="space-y-2">
          <Label htmlFor="drive-notebook">{t('navigation.notebooks')}</Label>
          <Select value={notebookId} onValueChange={setNotebookId} disabled={notebooksLoading}>
            <SelectTrigger id="drive-notebook" className="w-full">
              <SelectValue placeholder={t('notebooks.searchPlaceholder')} />
            </SelectTrigger>
            <SelectContent>
              {notebooks.map((notebook) => (
                <SelectItem key={notebook.id} value={notebook.id}>
                  {notebook.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )}

      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder={t('drive.searchPlaceholder')}
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          className="pl-10"
        />
        {isFetching && (
          <LoaderIcon className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 animate-spin text-muted-foreground" />
        )}
      </div>

      <ScrollArea className="h-[320px] border rounded-md">
        {isError ? (
          <div className="flex flex-col items-center justify-center h-[200px] text-muted-foreground">
            <p>{t('drive.filesLoadError')}</p>
          </div>
        ) : isLoading && allFiles.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-[200px] text-muted-foreground">
            <LoaderIcon className="h-8 w-8 mb-2 animate-spin" />
            <p>{t('common.loading')}</p>
          </div>
        ) : allFiles.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-[200px] text-muted-foreground">
            <FileIcon className="h-10 w-10 mb-2 opacity-50" />
            <p>{t('drive.noFilesFound')}</p>
          </div>
        ) : (
          <div className="space-y-1 p-2">
            {allFiles.map((file) => {
              const isSelected = selectedFileId === file.id
              return (
                <button
                  type="button"
                  key={file.id}
                  onClick={() => setSelectedFileId(file.id)}
                  className={`w-full flex items-center gap-3 p-2 rounded-md text-left transition-colors ${
                    isSelected ? 'bg-accent' : 'hover:bg-accent/50'
                  }`}
                >
                  {file.icon_link ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={file.icon_link} alt="" className="h-4 w-4 shrink-0" />
                  ) : (
                    <FileIcon className="h-4 w-4 shrink-0 text-muted-foreground" />
                  )}
                  <span className="flex-1 min-w-0 truncate text-sm">{file.name}</span>
                  <span className="shrink-0 text-xs text-muted-foreground">
                    {formatDate(file.modified_time)}
                  </span>
                </button>
              )
            })}
            {data?.next_page_token && (
              <div className="flex justify-center pt-2">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  disabled={isFetching}
                  onClick={() => setPageToken(data.next_page_token || undefined)}
                >
                  {isFetching ? (
                    <LoaderIcon className="h-4 w-4 animate-spin" />
                  ) : (
                    t('drive.loadMore')
                  )}
                </Button>
              </div>
            )}
          </div>
        )}
      </ScrollArea>

      <div className="flex justify-between items-center pt-2 border-t border-border">
        <Button type="button" variant="outline" onClick={onCancel} disabled={importFile.isPending}>
          {t('common.cancel')}
        </Button>
        <Button
          type="button"
          onClick={handleImport}
          disabled={!selectedFileId || !notebookId || importFile.isPending}
          className="min-w-[120px]"
        >
          {importFile.isPending ? t('common.adding') : t('drive.import')}
        </Button>
      </div>
    </div>
  )
}
