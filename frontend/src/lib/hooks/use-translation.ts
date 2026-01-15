import { useTranslation as useI18nTranslation } from 'react-i18next'
import { useMemo, useCallback, useRef } from 'react'
import { emitLanguageChangeEnd, emitLanguageChangeStart } from '@/lib/i18n-events'

/**
 * Custom useTranslation hook that provides a Proxy-based API for accessing translations.
 * 
 * CRITICAL: The Proxy implementation must be carefully designed to avoid infinite loops
 * during language switching. Key safeguards:
 * 1. Strict depth limit (max 4 levels)
 * 2. Blocked properties list to prevent React/JS internals from triggering recursion
 * 3. Early return for missing keys
 * 4. Memoization with stable dependencies
 */
export function useTranslation() {
  const { t: i18nTranslate, i18n } = useI18nTranslation()
  
  // Use a ref to track the current language to avoid unnecessary Proxy recreation
  const languageRef = useRef(i18n.language)
  languageRef.current = i18n.language
  
  // Loop detection
  const accessCounts = useRef<Record<string, number>>({})
  const lastResetTime = useRef(Date.now())

  // High-performance Recursive Proxy with strict safety limits
  const t = useMemo(() => {
    const i18nTranslateCopy = i18nTranslate;
    
    // Set of properties to completely block from Proxy traversal
    const BLOCKED_PROPS = new Set([
      '__proto__', '__esModule', '$$typeof', 'toJSON', 'constructor',
      'valueOf', 'toString', 'inspect', 'nodeType', 'tagName',
      'then', 'catch', 'finally', // Promise methods
      'prototype', 'caller', 'callee', 'arguments', // Function props
      'Symbol(Symbol.toStringTag)', 'Symbol(Symbol.iterator)',
    ]);
    
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const createProxy = (path: string, depth: number = 0): any => {
      // SAFETY: Strict depth limit to prevent stack overflow
      if (depth > 3) {
        return path; // Return the path string as fallback
      }
      
      // Base function for t('key') or t.path({ options })
      const proxyTarget = (keyOrOptions?: string | unknown, options?: unknown) => {
        if (typeof keyOrOptions === 'string') {
          const fullPath = path ? `${path}.${keyOrOptions}` : keyOrOptions;
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          return i18nTranslateCopy(fullPath, options as any);
        }
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        return i18nTranslateCopy(path, keyOrOptions as any);
      };

      return new Proxy(proxyTarget, {
        get(target, prop) {
          // Reset counters every 1s
          const now = Date.now()
          if (now - lastResetTime.current > 1000) {
            accessCounts.current = {}
            lastResetTime.current = now
          }

          if (typeof prop === 'string') {
             const key = path ? `${path}.${prop}` : prop;
             accessCounts.current[key] = (accessCounts.current[key] || 0) + 1;
             
             if (accessCounts.current[key] > 1000) {
               console.error(`[useTranslation] INFINITE LOOP DETECTED on key: "${key}". Breaking recursion.`);
               return key; // Force break
             }
          }

          // Handle Symbol properties immediately
          if (typeof prop === 'symbol') {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            return (target as any)[prop];
          }
          
          // Handle function's own properties
          if (prop in target) {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            return (target as any)[prop];
          }

          if (typeof prop !== 'string') return undefined;

          // Block React internals and JS built-ins
          if (prop.startsWith('__') || prop.startsWith('@@') || BLOCKED_PROPS.has(prop)) {
            return undefined;
          }

          const currentPath = path ? `${path}.${prop}` : prop;

          // Try to get the translation
          const result = i18nTranslateCopy(currentPath, { returnObjects: true });

          // If it's a leaf string, return it directly
          if (typeof result === 'string') {
            return result;
          }

          // Handle String.prototype methods on the current path
          if (prop === 'replace' || prop === 'split' || prop === 'length' ||
              prop === 'trim' || prop === 'toLowerCase' || prop === 'toUpperCase') {
            const translated = i18nTranslateCopy(path);
            if (typeof translated === 'string') {
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              const val = (translated as any)[prop];
              return typeof val === 'function' ? val.bind(translated) : val;
            }
          }

          // If i18n returned the key itself (meaning not found), stop recursion
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          if ((result as any) === currentPath || result === undefined || result === null) {
            return currentPath; // Return path as fallback instead of continuing
          }

          // If it's an object (nested structure), continue with depth limit
          if (typeof result === 'object') {
            return createProxy(currentPath, depth + 1);
          }

          return result;
        }
      });
    };

    return createProxy('', 0);
  }, [i18nTranslate])

  const setLanguage = useCallback(async (lang: string) => {
    if (lang === i18n.language) {
      return i18n.language
    }

    emitLanguageChangeStart(lang)

    try {
      await i18n.changeLanguage(lang)
      return i18n.language
    } finally {
      emitLanguageChangeEnd(lang)
    }
  }, [i18n])

  return useMemo(() => ({ 
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    t: t as any,
    i18n,
    language: i18n.language, 
    setLanguage 
  }), [t, i18n, setLanguage])
}
