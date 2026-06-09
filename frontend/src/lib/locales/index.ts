import { zhCN } from './zh-CN';
import { enUS } from './en-US';
import { zhTW } from './zh-TW';
import { ptBR } from './pt-BR';
import { jaJP } from './ja-JP';
import { itIT } from './it-IT';
import { frFR } from './fr-FR';
import { ruRU } from './ru-RU';
import { bnIN } from './bn-IN';
import { caES } from './ca-ES';
import { esES } from './es-ES';
import { deDE } from './de-DE';
import { plPL } from './pl-PL';
import { trTR } from './tr-TR';

export const resources = {
  'zh-CN': { translation: zhCN },
  'en-US': { translation: enUS },
  'zh-TW': { translation: zhTW },
  'pt-BR': { translation: ptBR },
  'ja-JP': { translation: jaJP },
  'it-IT': { translation: itIT },
  'fr-FR': { translation: frFR },
  'ru-RU': { translation: ruRU },
  'bn-IN': { translation: bnIN },
  'ca-ES': { translation: caES },
  'es-ES': { translation: esES },
  'de-DE': { translation: deDE },
  'pl-PL': { translation: plPL },
  'tr-TR': { translation: trTR },
} as const;

export type TranslationKeys = typeof enUS;

export type LanguageCode = 'zh-CN' | 'en-US' | 'zh-TW' | 'pt-BR' | 'ja-JP' | 'it-IT' | 'fr-FR' | 'ru-RU' | 'bn-IN' | 'ca-ES' | 'es-ES' | 'de-DE' | 'pl-PL' | 'tr-TR';

export type Language = {
  code: LanguageCode;
  label: string;
};

export const languages: Language[] = [
  { code: 'en-US', label: 'English' },
  { code: 'tr-TR', label: 'Türkçe' },
  { code: 'ca-ES', label: 'Català' },
  { code: 'zh-CN', label: '简体中文' },
  { code: 'zh-TW', label: '繁體中文' },
  { code: 'pt-BR', label: 'Português' },
  { code: 'ja-JP', label: '日本語' },
  { code: 'it-IT', label: 'Italiano' },
  { code: 'fr-FR', label: 'Français' },
  { code: 'ru-RU', label: 'Русский' },
  { code: 'bn-IN', label: 'বাংলা' },
  { code: 'es-ES', label: 'Español' },
  { code: 'de-DE', label: 'Deutsch' },
  { code: 'pl-PL', label: 'Polski' },
];

export { zhCN, enUS, zhTW, ptBR, jaJP, itIT, frFR, ruRU, bnIN, caES, esES, deDE, plPL, trTR };
