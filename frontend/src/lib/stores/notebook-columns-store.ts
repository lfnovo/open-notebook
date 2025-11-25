import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface NotebookColumnsState {
  sourcesCollapsed: boolean
  notesCollapsed: boolean
  toggleSources: () => void
  toggleNotes: () => void
  setSources: (collapsed: boolean) => void
  setNotes: (collapsed: boolean) => void
}

export const useNotebookColumnsStore = create<NotebookColumnsState>()(
  persist(
    (set) => ({
      sourcesCollapsed: false,
      notesCollapsed: false,
      toggleSources: () => set((state) => ({ sourcesCollapsed: !state.sourcesCollapsed })),
      toggleNotes: () => set((state) => ({ notesCollapsed: !state.notesCollapsed })),
      setSources: (collapsed) => set({ sourcesCollapsed: collapsed }),
      setNotes: (collapsed) => set({ notesCollapsed: collapsed }),
    }),
    {
      name: 'notebook-columns-storage',
    }
  )
)
