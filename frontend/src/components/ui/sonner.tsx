"use client"

import { useThemeStore } from "@/lib/stores/theme-store"
import { Toaster as Sonner, ToasterProps } from "sonner"
import { useDirection } from "@/components/ui/directional-icons"

const Toaster = ({ ...props }: ToasterProps) => {
  const theme = useThemeStore((state) => state.theme)
  const systemTheme = useThemeStore((state) => state.getSystemTheme())
  const effectiveTheme = theme === 'system' ? systemTheme : theme

  // Sonner respects the `dir` prop for RTL layout
  const dir = useDirection()

  return (
    <Sonner
      theme={effectiveTheme as ToasterProps["theme"]}
      dir={dir as ToasterProps["dir"]}
      className="toaster group"
      style={
        {
          "--normal-bg": "var(--popover)",
          "--normal-text": "var(--popover-foreground)",
          "--normal-border": "var(--border)",
          "--success-bg": "var(--popover)",
          "--success-text": "var(--popover-foreground)",
          "--success-border": "var(--border)",
        } as React.CSSProperties
      }
      {...props}
    />
  )
}

export { Toaster }
