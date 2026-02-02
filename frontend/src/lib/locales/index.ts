import { zhCN } from './zh-CN';
import { enUS } from './en-US';
import { zhTW } from './zh-TW';
import { ptBR } from './pt-BR';
import { jaJP } from './ja-JP';
import { frFR } from './fr-FR';
import { itIT } from './it-IT';
import { ruRU } from './ru-RU';

export const resources = {
  'zh-CN': { translation: zhCN },
  'en-US': { translation: enUS },
  'zh-TW': { translation: zhTW },
  'pt-BR': { translation: ptBR },
  'ja-JP': { translation: jaJP },
  'fr-FR': { translation: frFR },
  'it-IT': { translation: itIT },
  'ru-RU': { translation: ruRU },
} as const;

export type TranslationKeys = typeof enUS;

export type LanguageCode = 'zh-CN' | 'en-US' | 'zh-TW' | 'pt-BR' | 'ja-JP' | 'fr-FR' | 'it-IT' | 'ru-RU';

export type Language = {
  code: LanguageCode;
  label: string;
};

export const languages: Language[] = [
  { code: 'en-US', label: 'English' },
  { code: 'zh-CN', label: '简体中文' },
  { code: 'zh-TW', label: '繁體中文' },
  { code: 'pt-BR', label: 'Português' },
  { code: 'ja-JP', label: '日本語' },
  { code: 'fr-FR', label: 'Français' },
  { code: 'it-IT', label: 'Italiano' },
  { code: 'ru-RU', label: 'Русский' },
];

export { zhCN, enUS, zhTW, ptBR, jaJP, frFR, itIT, ruRU };
