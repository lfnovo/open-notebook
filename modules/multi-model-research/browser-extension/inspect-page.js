(() => {
  'use strict';
  const providers = {'chatgpt.com':'ChatGPT','gemini.google.com':'Gemini','claude.ai':'Claude'};
  if (location.protocol !== 'https:' || !providers[location.hostname]) return {error:'unsupported_page'};
  const visible = el => {
    if (!el || !el.getClientRects().length) return false;
    for (let current = el; current; current = current.parentElement) {
      const s = getComputedStyle(current);
      if (s.display === 'none' || s.visibility === 'hidden' || Number(s.opacity) === 0) return false;
    }
    return true;
  };
  const label = el => (el.getAttribute('aria-label') || el.innerText || el.getAttribute('title') || '').trim();
  const controls = [...document.querySelectorAll('button,a,[role="button"],[role="menuitem"],[role="menuitemradio"],[role="menuitemcheckbox"],[role="option"]')].filter(visible);
  const signIn = /^(log in|login|sign in|sign up|giriş yap|oturum aç|kaydol|üye ol)$/i;
  const research = /^(deep research|derin araştırma|research|araştırma)$/i;
  const titleChallenge = /just a moment|bir dakika|verify you are human|security verification|checking your browser/i.test(document.title);
  const securityChallenge = titleChallenge || [...document.querySelectorAll('h1,h2,[role="alert"]')].filter(visible).some(el => /verify you are human|performing security verification|insan olduğunuzu doğrulayın|güvenlik doğrulaması/i.test(el.innerText || ''));
  const selectors = {
    'ChatGPT':'#prompt-textarea[contenteditable="true"], textarea#prompt-textarea',
    'Gemini':'.ql-editor[contenteditable="true"], rich-textarea [contenteditable="true"]',
    'Claude':'[contenteditable="true"].ProseMirror, [contenteditable="true"][role="textbox"]'
  };
  const provider = providers[location.hostname];
  const composer = [...document.querySelectorAll(selectors[provider])].some(visible);
  const signInVisible = controls.some(el => signIn.test(label(el)));
  const researchVisible = controls.some(el => research.test(label(el)));
  // Return only coarse UI signals: no page text, titles, history, cookie values,
  // account identifiers, URLs with query parameters, prompts or report content.
  return {
    provider,
    checked_at: new Date().toISOString(),
    security_challenge_visible: securityChallenge,
    sign_in_control_visible: signInVisible,
    composer_visible: composer,
    research_control_visible: researchVisible,
    authentication_verified: false,
    research_access_verified: false,
    research_submitted: false
  };
})()
