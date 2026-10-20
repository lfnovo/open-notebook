import { resources } from './locales'
import { languageToDirection, resolveLanguage } from './language-resolution'

// Runs in <head> before hydration, like themeScript. Only the locale codes are
// embedded, not translation bundles or untrusted localStorage values.
export const languageScript = `
(function() {
  var preference;
  try { preference = localStorage.getItem('i18nextLng'); } catch (e) {}
  preference = preference || (navigator.languages && navigator.languages[0]) || navigator.language;
  var language = (${resolveLanguage.toString()})(preference, ${JSON.stringify(Object.keys(resources))});
  document.documentElement.lang = language;
  document.documentElement.dir = (${languageToDirection.toString()})(language);
})();
`
