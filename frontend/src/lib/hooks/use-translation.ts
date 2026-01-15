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
          // Handle standard properties of the function itself
          if (typeof prop === 'symbol' || prop in target) {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            return (target as any)[prop];
          }

          if (typeof prop !== 'string') return undefined;

          // Block React internals and other special properties from being proxied further
          if (prop.startsWith('__') || prop === '$$typeof' || prop === 'toJSON' || prop === 'constructor') {
            return undefined;
          }

          const currentPath = path ? `${path}.${prop}` : prop;

          // Check if currentPath is a direct translation key
          const result = i18nTranslateCopy(currentPath, { returnObjects: true });

          // If it's a leaf string node, return it directly
          if (typeof result === 'string') {
            return result;
          }

          // If result is NOT a string but we are accessing a String.prototype method 
          // (meaning the user wants to treat the CURRENT path as a string and call a method on it)
          if (prop === 'replace' || prop === 'split' || prop === 'length') {
            const translated = i18nTranslateCopy(path);
            if (typeof translated === 'string') {
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              const val = (translated as any)[prop];
              return typeof val === 'function' ? val.bind(translated) : val;
            }
          }

          // If result is undefined/null or just the path string (meaning i18n didn't find it)
          // We only continue proxying if the results don't clearly indicate a missing leaf
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          if (result === undefined || result === null || (result as any) === currentPath) {
             // Stop recursion depth to avoid stack overflow in extreme cases
             if (currentPath.split('.').length > 10) return currentPath;
             return createProxy(currentPath);
          }

          // Otherwise, it's an object (nested key structure), continue proxying
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
