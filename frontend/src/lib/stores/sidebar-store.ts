import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface SidebarState {
  isCollapsed: boolean
  toggleCollapse: () => void
  setCollapsed: (collapsed: boolean) => void
  /** Whether the Sections group in the sidebar is hidden. */
  sectionsHidden: boolean
  toggleSections: () => void
}

export const useSidebarStore = create<SidebarState>()(
  persist(
    (set) => ({
      isCollapsed: false,
      toggleCollapse: () => set((state) => ({ isCollapsed: !state.isCollapsed })),
      setCollapsed: (collapsed) => set({ isCollapsed: collapsed }),
      sectionsHidden: false,
      toggleSections: () => set((state) => ({ sectionsHidden: !state.sectionsHidden })),
    }),
    {
      name: 'sidebar-storage',
    }
  )
)
