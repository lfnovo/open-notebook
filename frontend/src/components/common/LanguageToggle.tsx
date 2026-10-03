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
import { languages, type LanguageCode } from '@/lib/locales'

interface LanguageToggleProps {
  iconOnly?: boolean
}

export function LanguageToggle({ iconOnly = false }: LanguageToggleProps) {
  const { language, setLanguage, t } = useTranslation()
  
  // Keep the actual language code for proper comparison
  const currentLang = language || 'en-US'
  // Exhaustive so adding a locale also requires its translated menu name.
  const translatedLabels: Record<LanguageCode, string> = {
    'en-US': t('common.english'),
    'ca-ES': t('common.catalan'),
    'zh-CN': t('common.chinese'),
    'zh-TW': t('common.traditionalChinese'),
    'pt-BR': t('common.portuguese'),
    'ja-JP': t('common.japanese'),
    'fr-FR': t('common.french'),
    'ru-RU': t('common.russian'),
    'bn-IN': t('common.bengali'),
    'es-ES': t('common.spanish'),
    'de-DE': t('common.german'),
    'pl-PL': t('common.polish'),
    'tr-TR': t('common.turkish'),
    'it-IT': t('common.italian'),
    'ar-SA': t('common.arabic'),
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button 
          variant={iconOnly ? "ghost" : "outline"} 
          size={iconOnly ? "icon" : "default"} 
          className={iconOnly ? "h-9 w-full sidebar-menu-item" : "w-full justify-start gap-2 sidebar-menu-item"}
        >
          <Languages className="h-[1.2rem] w-[1.2rem]" />
          {!iconOnly && <span>{t('common.language')}</span>}
          <span className="sr-only">{t('navigation.language')}</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {languages.map(({ code }) => {
          // Keep Simplified and Traditional Chinese distinct when matching variants.
          const isSelected = code === 'zh-CN'
            ? currentLang === code || currentLang.startsWith('zh-Hans') || currentLang === 'zh'
            : code === 'zh-TW'
              ? currentLang === code || currentLang.startsWith('zh-Hant')
              : currentLang.split('-')[0] === code.split('-')[0]

          return (
            <DropdownMenuItem
              key={code}
              onClick={() => setLanguage(code)}
              className={isSelected ? 'bg-accent' : ''}
            >
              <span dir="auto">{translatedLabels[code]}</span>
            </DropdownMenuItem>
          )
        })}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
