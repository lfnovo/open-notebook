import { zhCN } from './zh-CN';
import { enUS } from './en-US';
import { zhTW } from './zh-TW';
import { ptBR } from './pt-BR';
import { jaJP } from './ja-JP';
import { itIT } from './it-IT';

export const resources = {
  'zh-CN': { translation: zhCN },
  'en-US': { translation: enUS },
  'zh-TW': { translation: zhTW },
  'pt-BR': { translation: ptBR },
  'ja-JP': { translation: jaJP },
  'it-IT': { translation: itIT },
} as const;

export type TranslationKeys = typeof enUS;

export type LanguageCode = 'zh-CN' | 'en-US' | 'zh-TW' | 'pt-BR' | 'ja-JP' | 'it-IT';

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
  { code: 'it-IT', label: 'Italiano' },
];

export { zhCN, enUS, zhTW, ptBR, jaJP, itIT };
