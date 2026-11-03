'use client'

import Link from 'next/link'
import { usePathname, useSearchParams } from 'next/navigation'
import { ChevronDown, ChevronRight, Layers } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { useSections } from '@/lib/hooks/use-sections'
import { useTranslation } from '@/lib/hooks/use-translation'
import { useSidebarStore } from '@/lib/stores/sidebar-store'
import { notebooksHref } from '@/lib/utils/folders'

/** Notebook sections as sidebar links; the header shows or hides the list. */
export function SidebarSections() {
  const { t } = useTranslation()
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const { sectionsHidden, toggleSections } = useSidebarStore()
  const { data: sections } = useSections()

  if (!sections || sections.length === 0) {
    return null
  }

  const activeSection = pathname === '/notebooks' ? searchParams.get('section') : null

  return (
    <div className="space-y-1">
      <button
        type="button"
        onClick={toggleSections}
        aria-expanded={!sectionsHidden}
        aria-label={sectionsHidden ? t('sections.showInSidebar') : t('sections.hideInSidebar')}
        className="flex w-full items-center gap-1 px-3 text-left text-[10.5px] font-bold uppercase tracking-[0.14em] text-sidebar-foreground/40 hover:text-sidebar-foreground/70 focus-visible:outline-none focus-visible:text-sidebar-foreground"
      >
        {sectionsHidden ? (
          <ChevronRight className="h-3 w-3" aria-hidden />
        ) : (
          <ChevronDown className="h-3 w-3" aria-hidden />
        )}
        {t('sections.title')}
      </button>

      {!sectionsHidden &&
        sections.map((section) => (
          <Link key={section.id} href={notebooksHref({ sectionId: section.id })}>
            <Button
              variant="ghost"
              className={cn(
                'w-full justify-start gap-2.5 text-[13px] font-medium text-sidebar-foreground/80 sidebar-menu-item',
                section.id === activeSection && 'bg-popover font-semibold text-sidebar-foreground ring-1 ring-inset ring-border'
              )}
            >
              <Layers className="h-4 w-4 shrink-0 opacity-85 text-sage" />
              <span className="truncate">{section.name}</span>
            </Button>
          </Link>
        ))}
    </div>
  )
}
