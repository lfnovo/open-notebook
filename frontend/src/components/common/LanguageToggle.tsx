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
          className={iconOnly ? "h-9 w-full sidebar-menu-item" : "w-full justify-start gap-2 sidebar-menu-item"}
        >
          <Languages className="h-[1.2rem] w-[1.2rem]" />
          {!iconOnly && <span>{t.common.language}</span>}
          <span className="sr-only">{t.navigation.language}</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem 
          onClick={() => setLanguage('en-US')}
          className={currentLang === 'en-US' || currentLang.startsWith('en') ? 'bg-accent' : ''}
        >
          <span>{t.common.english}</span>
        </DropdownMenuItem>
        <DropdownMenuItem 
          onClick={() => setLanguage('zh-CN')}
          className={currentLang === 'zh-CN' || currentLang.startsWith('zh-Hans') || currentLang === 'zh' ? 'bg-accent' : ''}
        >
          <span>{t.common.chinese}</span>
        </DropdownMenuItem>
        <DropdownMenuItem
          onClick={() => setLanguage('zh-TW')}
          className={currentLang === 'zh-TW' || currentLang.startsWith('zh-Hant') ? 'bg-accent' : ''}
        >
          <span>{t.common.traditionalChinese}</span>
        </DropdownMenuItem>
        <DropdownMenuItem
          onClick={() => setLanguage('pt-BR')}
          className={currentLang === 'pt-BR' || currentLang.startsWith('pt') ? 'bg-accent' : ''}
        >
          <span>{t.common.portuguese}</span>
        </DropdownMenuItem>
        <DropdownMenuItem
          onClick={() => setLanguage('ja-JP')}
          className={currentLang === 'ja-JP' || currentLang.startsWith('ja') ? 'bg-accent' : ''}
        >
          <span>{t.common.japanese}</span>
        </DropdownMenuItem>
        <DropdownMenuItem
          onClick={() => setLanguage('ru-RU')}
          className={currentLang === 'ru-RU' || currentLang.startsWith('ru') ? 'bg-accent' : ''}
        >
          <span>{t.common.russian}</span>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
