'use client'

import { useTheme } from '@/lib/stores/theme-store'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Sun, Moon, Monitor } from 'lucide-react'
import { useTranslation } from '@/lib/hooks/use-translation'

interface ThemeToggleProps {
  iconOnly?: boolean
}

export function ThemeToggle({ iconOnly = false }: ThemeToggleProps) {
  const { theme, setTheme } = useTheme()
  const { t } = useTranslation()

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button 
          variant={iconOnly ? "ghost" : "outline"} 
          size={iconOnly ? "icon" : "default"} 
          className={iconOnly ? "h-9 w-full sidebar-menu-item" : "w-full justify-start gap-2 sidebar-menu-item"}
        >
          <div className="relative h-[1.2rem] w-[1.2rem]">
            <Sun className="absolute inset-0 h-[1.2rem] w-[1.2rem] rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
            <Moon className="absolute inset-0 h-[1.2rem] w-[1.2rem] rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
          </div>
          {!iconOnly && <span>{t.common.theme}</span>}
          <span className="sr-only">{t.navigation.theme}</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem 
          onClick={() => setTheme('light')}
          className={theme === 'light' ? 'bg-accent' : ''}
        >
          <Sun className="mr-2 h-4 w-4" />
          <span>{t.common.light}</span>
        </DropdownMenuItem>
        <DropdownMenuItem 
          onClick={() => setTheme('dark')}
          className={theme === 'dark' ? 'bg-accent' : ''}
        >
          <Moon className="mr-2 h-4 w-4" />
          <span>{t.common.dark}</span>
        </DropdownMenuItem>
        <DropdownMenuItem 
          onClick={() => setTheme('system')}
          className={theme === 'system' ? 'bg-accent' : ''}
        >
          <Monitor className="mr-2 h-4 w-4" />
          <span>{t.common.system}</span>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}