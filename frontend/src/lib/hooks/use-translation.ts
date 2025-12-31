import { useTranslation as useI18nTranslation } from 'react-i18next'
import { useMemo, useCallback } from 'react'

export function useTranslation() {
  const { t: i18nTranslate, i18n } = useI18nTranslation()
  
  // High-performance Recursive Proxy to support t.section.sub.key syntax with full type safety
  // This version handles any nesting depth and transparently supports string methods like .replace()
  const t = useMemo(() => {
    const i18nTranslateCopy = i18nTranslate;
    
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const createProxy = (path: string): any => {
      // Base function for t('key') or t.path({ options })
      const proxyTarget = (keyOrOptions?: string | unknown, options?: unknown) => {
        if (typeof keyOrOptions === 'string') {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          return i18nTranslateCopy(path ? `${path}.${keyOrOptions}` : keyOrOptions, options as any);
        }
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        return i18nTranslateCopy(path, keyOrOptions as any);
      };

      return new Proxy(proxyTarget, {
        get(target, prop) {
          // Handle standard properties
          if (typeof prop === 'symbol' || prop in target) {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            return (target as any)[prop];
          }

          if (typeof prop !== 'string') return undefined;

          const currentPath = path ? `${path}.${prop}` : prop;

          // If the property is a standard string method or property (like .replace, .length, .split)
          // we resolve the current path to its translation and return the string's property
          if (prop in String.prototype || prop === 'length') {
            const translated = i18nTranslateCopy(path);
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            const val = (translated as any)[prop];
            return typeof val === 'function' ? val.bind(translated) : val;
          }

          // Check if currentPath is a leaf string node or an object
          const result = i18nTranslateCopy(currentPath, { returnObjects: true });

          if (typeof result === 'string') {
            // Leaf node: return the string directly so React can render it
            return result;
          }

          // If result is undefined or null, return empty string to prevent .replace() errors
          if (result === undefined || result === null) {
            return '';
          }

          // Otherwise, assume it's a nested key and return a new proxy for that path
          return createProxy(currentPath);
        }
      });
    };

    return createProxy('');
  }, [i18nTranslate])

  const setLanguage = useCallback((lang: string) => i18n.changeLanguage(lang), [i18n])

  return useMemo(() => ({ 
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    t: t as any, // Keep as any here to allow both function and property access in TS
    i18n,
    language: i18n.language, 
    setLanguage 
  }), [t, i18n, setLanguage])
}
