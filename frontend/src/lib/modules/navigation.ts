'use client'
import { Puzzle, Telescope, type LucideIcon } from 'lucide-react'
import type { TFunction } from 'i18next'
import { useModules } from './hooks'
import { moduleEntries } from './generated'

export type NavigationItem = { name: string; href: string; icon: LucideIcon; iconClass?: string }
export function useModuleNavigation(t: TFunction) {
  const { data } = useModules()
  return (section: string): NavigationItem[] => (data || [])
    .filter(m => m.enabled && m.frontend?.section === section && moduleEntries[m.id])
    .map(m => ({ name: t(m.frontend!.label_key), href: m.frontend!.route, icon: m.frontend!.icon === 'telescope' ? Telescope : Puzzle }))
}
