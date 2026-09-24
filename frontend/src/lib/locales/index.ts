import { arYE } from './ar-YE';
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
  'ar-YE': { translation: arYE },
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

export type LanguageCode = keyof typeof resources;

export type Language = {
  code: LanguageCode;
  label: string;
};

export const languages: Language[] = [
  { code: 'ar-YE', label: 'العربية' },
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

export { arYE, zhCN, enUS, zhTW, ptBR, jaJP, itIT, frFR, ruRU, bnIN, caES, esES, deDE, plPL, trTR };

/**
 * Text direction for a given locale.
 * RTL locales: Arabic (ar, ar-*), Hebrew (he, he-*), Persian (fa, fa-*), Urdu (ur, ur-*).
 * All other supported locales are LTR.
 */
export type TextDirection = 'ltr' | 'rtl';

const RTL_LANGUAGE_PREFIXES = ['ar', 'he', 'fa', 'ur'] as const;

export function getDirection(locale: string): TextDirection {
  const lang = locale.split('-')[0].toLowerCase()
  return (RTL_LANGUAGE_PREFIXES as readonly string[]).includes(lang) ? 'rtl' : 'ltr'
}

export function isRTLLocale(locale: string): boolean {
  return getDirection(locale) === 'rtl'
}
