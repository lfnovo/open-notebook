import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type Theme = 'light' | 'dark' | 'system'

interface ThemeState {
  theme: Theme
  hasHydrated: boolean
  setTheme: (theme: Theme) => void
  setHasHydrated: (state: boolean) => void
  getSystemTheme: () => 'light' | 'dark'
  getEffectiveTheme: () => 'light' | 'dark'
}

export const useThemeStore = create<ThemeState>()(
  persist(
    (set, get) => ({
      theme: 'system',
      hasHydrated: false,

      setHasHydrated: (state: boolean) => {
        set({ hasHydrated: state })
      },
      
      setTheme: (theme: Theme) => {
        set({ theme })
        
        // Apply theme to document immediately
        if (typeof window !== 'undefined') {
          const root = window.document.documentElement
          const effectiveTheme = theme === 'system' ? get().getSystemTheme() : theme
          
          root.classList.remove('light', 'dark')
          root.classList.add(effectiveTheme)
          root.setAttribute('data-theme', effectiveTheme)
        }
      },
      
      getSystemTheme: () => {
        if (typeof window !== 'undefined') {
          return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
        }
        return 'light'
      },
      
      getEffectiveTheme: () => {
        const { theme } = get()
        return theme === 'system' ? get().getSystemTheme() : theme
      }
    }),
    {
      name: 'theme-storage',
      partialize: (state) => ({ theme: state.theme }),
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true)
      }
    }
  )
)

// Hook for components to use theme
export function useTheme() {
  const { theme, hasHydrated, setTheme, getEffectiveTheme } = useThemeStore()
  
  return {
    theme,
    hasHydrated,
    setTheme,
    effectiveTheme: getEffectiveTheme(),
    isDark: getEffectiveTheme() === 'dark'
  }
}
