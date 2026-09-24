// This script runs before React hydration to prevent theme flash and set text direction
export const themeScript = `
(function() {
  try {
    var theme = JSON.parse(localStorage.getItem('theme-storage') || '{}').state?.theme || 'system';
    var systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    var effectiveTheme = theme === 'system' ? (systemPrefersDark ? 'dark' : 'light') : theme;

    document.documentElement.classList.remove('light', 'dark');
    document.documentElement.classList.add(effectiveTheme);
    document.documentElement.setAttribute('data-theme', effectiveTheme);
  } catch (e) {
    // Fallback to light theme
    document.documentElement.classList.add('light');
    document.documentElement.setAttribute('data-theme', 'light');
  }
})();
`

// Inline script to set dir and lang before React hydration.
// Must be self-contained (no imports) and match the locale->direction logic in @/lib/locales/index.ts
export const directionScript = `
(function() {
  try {
    // RTL language prefixes (must match RTL_LANGUAGE_PREFIXES in @/lib/locales/index.ts)
    var rtlPrefixes = ['ar', 'he', 'fa', 'ur'];

    // Read persisted language from i18next's default localStorage key
    var locale = localStorage.getItem('i18nextLng');

    // Fallback to navigator language if not persisted
    if (!locale) {
      locale = navigator.language || 'en-US';
    }

    // Check language prefix (e.g., 'ar-YE' -> 'ar', 'he-IL' -> 'he')
    var lang = locale.split('-')[0].toLowerCase();
    var isRTL = rtlPrefixes.includes(lang);

    var dir = isRTL ? 'rtl' : 'ltr';

    document.documentElement.dir = dir;
    document.documentElement.lang = locale;
  } catch (e) {
    // Fallback to LTR English
    document.documentElement.dir = 'ltr';
    document.documentElement.lang = 'en-US';
  }
})();
`
