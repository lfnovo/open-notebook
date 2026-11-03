'use client'

import { Suspense, useMemo, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'

import { AppShell } from '@/components/layout/AppShell'
import { NotebookList } from './components/NotebookList'
import { RecentlyViewed } from './components/RecentlyViewed'
import { Button } from '@/components/ui/button'
import { Plus, RefreshCw, Compass, Mic, FolderPlus, Layers, ChevronRight } from 'lucide-react'
import { useNotebooks } from '@/lib/hooks/use-notebooks'
import { CreateNotebookDialog } from '@/components/notebooks/CreateNotebookDialog'
import { DiscoverNotebookDialog } from '@/components/notebooks/DiscoverNotebookDialog'
import type { DiscoverMode } from '@/components/notebooks/discover-notebook'
import { Input } from '@/components/ui/input'
import { useTranslation } from '@/lib/hooks/use-translation'
import { useFolders } from '@/lib/hooks/use-folders'
import { FolderDialog } from '@/components/notebooks/FolderDialog'
import { FolderCard } from '@/components/notebooks/FolderCard'
import { useSections } from '@/lib/hooks/use-sections'
import { SectionDialog } from '@/components/notebooks/SectionDialog'
import { SectionCard } from '@/components/notebooks/SectionCard'
import {
  foldersInSection,
  groupNotebooksByFolder,
  notebooksHref,
  notebooksInFolder,
  unsectionedFolders,
} from '@/lib/utils/folders'

export default function NotebooksPage() {
  // useSearchParams needs a Suspense boundary for static prerendering.
  return (
    <Suspense fallback={null}>
      <NotebooksPageContent />
    </Suspense>
  )
}

function NotebooksPageContent() {
  const { t } = useTranslation()
  const router = useRouter()
  const searchParams = useSearchParams()
  const folderParam = searchParams.get('folder')
  const sectionParam = searchParams.get('section')
  const [createDialogOpen, setCreateDialogOpen] = useState(false)
  const [discoverMode, setDiscoverMode] = useState<DiscoverMode | null>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [folderDialogOpen, setFolderDialogOpen] = useState(false)
  const [sectionDialogOpen, setSectionDialogOpen] = useState(false)
  const { data: folders } = useFolders()
  const { data: sections } = useSections()
  const { data: notebooks, isLoading, refetch } = useNotebooks(false)
  const { data: archivedNotebooks } = useNotebooks(true)

  const normalizedQuery = searchTerm.trim().toLowerCase()

  const filteredActive = useMemo(() => {
    if (!notebooks) {
      return undefined
    }
    if (!normalizedQuery) {
      return notebooks
    }
    return notebooks.filter((notebook) =>
      notebook.name.toLowerCase().includes(normalizedQuery)
    )
  }, [notebooks, normalizedQuery])

  const filteredArchived = useMemo(() => {
    if (!archivedNotebooks) {
      return undefined
    }
    if (!normalizedQuery) {
      return archivedNotebooks
    }
    return archivedNotebooks.filter((notebook) =>
      notebook.name.toLowerCase().includes(normalizedQuery)
    )
  }, [archivedNotebooks, normalizedQuery])

  const folderList = useMemo(() => folders ?? [], [folders])
  const sectionList = useMemo(() => sections ?? [], [sections])
  const currentFolder = folderParam
    ? folderList.find((folder) => folder.id === folderParam) ?? null
    : null
  // An open folder sits under its own section; otherwise ?section= picks one.
  const currentSectionId = currentFolder ? currentFolder.section_id : sectionParam
  const currentSection = currentSectionId
    ? sectionList.find((section) => section.id === currentSectionId) ?? null
    : null
  const inSectionView = !currentFolder && currentSection !== null
  const isSearching = normalizedQuery.length > 0

  // Counts come from the unfiltered active notebooks so search never skews them.
  const grouped = useMemo(
    () => groupNotebooksByFolder(folderList, notebooks ?? []),
    [folderList, notebooks]
  )

  const visibleFolderCards = useMemo(
    () =>
      grouped.folderCards.filter(
        ({ folder }) => !normalizedQuery || folder.name.toLowerCase().includes(normalizedQuery)
      ),
    [grouped.folderCards, normalizedQuery]
  )

  // Top level shows folders outside any section; a search looks in all of them.
  const rootFolderCards = useMemo(() => {
    if (normalizedQuery) return visibleFolderCards
    const loose = new Set(unsectionedFolders(folderList, sectionList).map((folder) => folder.id))
    return visibleFolderCards.filter(({ folder }) => loose.has(folder.id))
  }, [visibleFolderCards, folderList, sectionList, normalizedQuery])

  const visibleSections = useMemo(
    () =>
      sectionList.filter(
        (section) => !normalizedQuery || section.name.toLowerCase().includes(normalizedQuery)
      ),
    [sectionList, normalizedQuery]
  )

  const sectionFolderCards = useMemo(() => {
    if (!currentSection) return []
    const inside = new Set(foldersInSection(folderList, currentSection.id).map((folder) => folder.id))
    return visibleFolderCards.filter(({ folder }) => inside.has(folder.id))
  }, [currentSection, folderList, visibleFolderCards])

  const openFolder = (folder: { id: string; section_id?: string | null }) =>
    router.push(notebooksHref({ sectionId: folder.section_id, folderId: folder.id }))

  const ungroupedFiltered = useMemo(
    () =>
      grouped.ungrouped.filter(
        (notebook) => !normalizedQuery || notebook.name.toLowerCase().includes(normalizedQuery)
      ),
    [grouped.ungrouped, normalizedQuery]
  )

  const folderNotebooks = useMemo(
    () => (currentFolder && filteredActive ? notebooksInFolder(filteredActive, currentFolder.id) : undefined),
    [currentFolder, filteredActive]
  )

  const archivedForView = useMemo(() => {
    if (!filteredArchived) return undefined
    return currentFolder ? notebooksInFolder(filteredArchived, currentFolder.id) : filteredArchived
  }, [currentFolder, filteredArchived])

  const hasArchived =
    !inSectionView &&
    ((archivedForView?.length ?? 0) > 0 || (!currentFolder && (archivedNotebooks?.length ?? 0) > 0))

  return (
    <AppShell>
      <div className="flex-1 overflow-y-auto">
        <div className="p-6 space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <h1 className="font-display text-2xl font-bold tracking-tight">{t('notebooks.title')}</h1>
            <Button variant="outline" size="sm" onClick={() => refetch()}>
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <Input
              id="notebook-search"
              name="notebook-search"
              value={searchTerm}
              onChange={(event) => setSearchTerm(event.target.value)}
              placeholder={t('notebooks.searchPlaceholder')}
              autoComplete="off"
              aria-label={t('common.accessibility.searchNotebooks') || "Search notebooks"}
              className="w-full sm:w-64"
            />
            <Button onClick={() => setCreateDialogOpen(true)}>
              <Plus className="h-4 w-4 mr-2" />
              {t('notebooks.newNotebook')}
            </Button>
            <Button variant="outline" onClick={() => setSectionDialogOpen(true)}>
              <Layers className="h-4 w-4 mr-2" />
              {t('sections.newSection')}
            </Button>
            <Button variant="outline" onClick={() => setFolderDialogOpen(true)}>
              <FolderPlus className="h-4 w-4 mr-2" />
              {t('folders.newFolder')}
            </Button>
            <Button variant="outline" onClick={() => setDiscoverMode('notebook')}>
              <Compass className="h-4 w-4 mr-2" />
              {t('notebooks.discoverNotebook')}
            </Button>
            <Button variant="outline" onClick={() => setDiscoverMode('podcast')}>
              <Mic className="h-4 w-4 mr-2" />
              {t('notebooks.discoverPodcast')}
            </Button>
          </div>
        </div>
        
        <div className="space-y-8">
          {currentFolder ? (
            <>
              <Breadcrumb
                label={t('folders.breadcrumb')}
                allLabel={t('folders.allNotebooks')}
                section={currentSection}
                current={currentFolder.name}
                onNavigate={router.push}
              />

              <NotebookList
                notebooks={folderNotebooks}
                isLoading={isLoading}
                title={currentFolder.name}
                emptyTitle={isSearching ? t('common.noMatches') : t('folders.emptyFolder')}
                emptyDescription={isSearching ? t('common.tryDifferentSearch') : t('folders.emptyFolderDesc')}
              />
            </>
          ) : inSectionView && currentSection ? (
            <>
              <Breadcrumb
                label={t('folders.breadcrumb')}
                allLabel={t('folders.allNotebooks')}
                current={currentSection.name}
                onNavigate={router.push}
              />

              {sectionFolderCards.length > 0 ? (
                <section className="space-y-4">
                  <div className="flex items-center gap-2">
                    <h2 className="font-display text-lg font-semibold tracking-tight">
                      {currentSection.name}
                    </h2>
                    <span className="text-sm text-muted-foreground">({sectionFolderCards.length})</span>
                  </div>
                  <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
                    {sectionFolderCards.map(({ folder, notebookCount }) => (
                      <FolderCard
                        key={folder.id}
                        folder={folder}
                        notebookCount={notebookCount}
                        onOpen={openFolder}
                      />
                    ))}
                  </div>
                </section>
              ) : (
                <div className="rounded-lg border border-dashed p-8 text-center">
                  <p className="font-medium">
                    {isSearching ? t('common.noMatches') : t('sections.emptySection')}
                  </p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {isSearching ? t('common.tryDifferentSearch') : t('sections.emptySectionDesc')}
                  </p>
                </div>
              )}
            </>
          ) : (
            <>
              {!isSearching && <RecentlyViewed />}

              {visibleSections.length > 0 && (
                <section className="space-y-4">
                  <div className="flex items-center gap-2">
                    <h2 className="font-display text-lg font-semibold tracking-tight">
                      {t('sections.title')}
                    </h2>
                    <span className="text-sm text-muted-foreground">({visibleSections.length})</span>
                  </div>
                  <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
                    {visibleSections.map((section) => (
                      <SectionCard
                        key={section.id}
                        section={section}
                        onOpen={(sec) => router.push(notebooksHref({ sectionId: sec.id }))}
                      />
                    ))}
                  </div>
                </section>
              )}

              {rootFolderCards.length > 0 && (
                <section className="space-y-4">
                  <div className="flex items-center gap-2">
                    <h2 className="font-display text-lg font-semibold tracking-tight">
                      {t('folders.title')}
                    </h2>
                    <span className="text-sm text-muted-foreground">({rootFolderCards.length})</span>
                  </div>
                  <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
                    {rootFolderCards.map(({ folder, notebookCount }) => (
                      <FolderCard
                        key={folder.id}
                        folder={folder}
                        notebookCount={notebookCount}
                        onOpen={openFolder}
                      />
                    ))}
                  </div>
                </section>
              )}

              {/* While searching, match notebooks across all folders. */}
              {(isSearching || ungroupedFiltered.length > 0 || isLoading || (folderList.length === 0 && sectionList.length === 0)) && (
                <NotebookList
                  notebooks={isSearching ? filteredActive : ungroupedFiltered}
                  isLoading={isLoading}
                  title={
                    !isSearching && (folderList.length > 0 || sectionList.length > 0)
                      ? t('folders.ungrouped')
                      : t('notebooks.activeNotebooks')
                  }
                  emptyTitle={isSearching ? t('common.noMatches') : undefined}
                  emptyDescription={isSearching ? t('common.tryDifferentSearch') : undefined}
                  onAction={!isSearching ? () => setCreateDialogOpen(true) : undefined}
                  actionLabel={!isSearching ? t('notebooks.newNotebook') : undefined}
                />
              )}
            </>
          )}

          {hasArchived && (
            <NotebookList
              notebooks={archivedForView}
              isLoading={false}
              title={t('notebooks.archivedNotebooks')}
              collapsible
              emptyTitle={isSearching ? t('common.noMatches') : undefined}
              emptyDescription={isSearching ? t('common.tryDifferentSearch') : undefined}
            />
          )}
        </div>
        </div>
      </div>

      <SectionDialog open={sectionDialogOpen} onOpenChange={setSectionDialogOpen} />
      <FolderDialog
        open={folderDialogOpen}
        onOpenChange={setFolderDialogOpen}
        defaultSectionId={currentSection?.id}
      />
      <CreateNotebookDialog
        open={createDialogOpen}
        onOpenChange={setCreateDialogOpen}
      />
      <DiscoverNotebookDialog
        open={discoverMode !== null}
        onOpenChange={(open) => { if (!open) setDiscoverMode(null) }}
        mode={discoverMode ?? 'notebook'}
      />
    </AppShell>
  )
}

interface BreadcrumbProps {
  label: string
  allLabel: string
  /** Section the current level sits under; omitted when the section itself is current. */
  section?: { id: string; name: string } | null
  current: string
  onNavigate: (href: string) => void
}

function Breadcrumb({ label, allLabel, section, current, onNavigate }: BreadcrumbProps) {
  return (
    <nav aria-label={label} className="flex flex-wrap items-center gap-1 text-sm">
      <Button variant="ghost" size="sm" className="px-2" onClick={() => onNavigate(notebooksHref())}>
        {allLabel}
      </Button>
      <ChevronRight className="h-4 w-4 text-muted-foreground" aria-hidden />
      {section && (
        <>
          <Button
            variant="ghost"
            size="sm"
            className="px-2"
            onClick={() => onNavigate(notebooksHref({ sectionId: section.id }))}
          >
            {section.name}
          </Button>
          <ChevronRight className="h-4 w-4 text-muted-foreground" aria-hidden />
        </>
      )}
      <span className="px-2 font-medium" aria-current="page">
        {current}
      </span>
    </nav>
  )
}
