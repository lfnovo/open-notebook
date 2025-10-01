'use client'

import { useEffect } from 'react'
import { useThemeStore } from '@/lib/stores/theme-store'

interface ThemeProviderProps {
  children: React.ReactNode
}

export function ThemeProvider({ children }: ThemeProviderProps) {
  const { theme, getSystemTheme, getEffectiveTheme } = useThemeStore()

  useEffect(() => {
    // Initialize theme on mount
    const root = window.document.documentElement
    const effectiveTheme = getEffectiveTheme()
    
    // Remove all possible theme classes first
    root.classList.remove('light', 'dark')
    
    // Add the effective theme class
    root.classList.add(effectiveTheme)
    
    // Set the data attribute as well for better component compatibility
    root.setAttribute('data-theme', effectiveTheme)

    // Listen for system theme changes when using system preference
    if (theme === 'system') {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
      
      const handleChange = () => {
        const newSystemTheme = getSystemTheme()
        root.classList.remove('light', 'dark')
        root.classList.add(newSystemTheme)
        root.setAttribute('data-theme', newSystemTheme)
      }

      mediaQuery.addEventListener('change', handleChange)
      return () => mediaQuery.removeEventListener('change', handleChange)
    }
  }, [theme, getSystemTheme, getEffectiveTheme])

  return <>{children}</>
}
