'use client'

import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Languages } from 'lucide-react'
import { useTranslation } from '@/lib/hooks/use-translation'

interface LanguageToggleProps {
  iconOnly?: boolean
}

export function LanguageToggle({ iconOnly = false }: LanguageToggleProps) {
  const { language, setLanguage, t } = useTranslation()
  
  // Keep the actual language code for proper comparison
  const currentLang = language || 'en-US'

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button 
          variant={iconOnly ? "ghost" : "outline"} 
          size={iconOnly ? "icon" : "default"} 
          className={iconOnly ? "h-9 w-full" : "w-full justify-start gap-2"}
        >
          <Languages className="h-[1.2rem] w-[1.2rem]" />
          {!iconOnly && <span>{t.common.language}</span>}
          <span className="sr-only">{t.navigation.language}</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem 
          onClick={() => setLanguage('en-US')}
          className={currentLang === 'en-US' ? 'bg-accent' : ''}
        >
          <span>{t.common.english}</span>
        </DropdownMenuItem>
        <DropdownMenuItem 
          onClick={() => setLanguage('zh-CN')}
          className={currentLang === 'zh-CN' ? 'bg-accent' : ''}
        >
          <span>{t.common.chinese}</span>
        </DropdownMenuItem>
        <DropdownMenuItem 
          onClick={() => setLanguage('zh-TW')}
          className={currentLang === 'zh-TW' ? 'bg-accent' : ''}
        >
          <span>{t.common.traditionalChinese}</span>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
