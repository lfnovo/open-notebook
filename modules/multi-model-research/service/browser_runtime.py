"""Dedicated, long-lived, visible Chrome for provider web sessions.

Deliberately NOT headless. Headless Chrome reports itself as `HeadlessChrome/...`
in the User-Agent and provider bot protection refuses it outright, so a headless
runtime can never reach a usable research page. Nothing in this module hides the
browser's identity: the automation flags stay on, the fingerprint is untouched,
and security verifications are surfaced to the user to complete in the window —
never solved, replayed or bypassed here. The everyday Chrome profile is never
attached to and its cookies are never read.
"""
from __future__ import annotations
import asyncio
import json
import os
from pathlib import Path
import subprocess
import time
from urllib.parse import urlparse
from playwright.async_api import async_playwright

PROVIDERS = {
    'ChatGPT': {
        'url': 'https://chatgpt.com/',
        'hosts': {'chatgpt.com'},
        'auth_hosts': {'auth.openai.com', 'auth0.openai.com', 'accounts.google.com',
                       'login.microsoftonline.com', 'appleid.apple.com', 'platform.openai.com'},
        'auth_paths': ('/auth/login', '/auth/signup', '/login', '/signup'),
        'editor': '#prompt-textarea[contenteditable="true"], textarea#prompt-textarea',
    },
    'Gemini': {
        'url': 'https://gemini.google.com/app',
        'hosts': {'gemini.google.com'},
        'auth_hosts': {'accounts.google.com', 'accounts.youtube.com'},
        'auth_paths': ('/signin', '/ServiceLogin'),
        'editor': '.ql-editor[contenteditable="true"], rich-textarea [contenteditable="true"]',
    },
    'Claude': {
        'url': 'https://claude.ai/new',
        'hosts': {'claude.ai'},
        'auth_hosts': {'accounts.google.com', 'login.anthropic.com'},
        'auth_paths': ('/login', '/magic-link', '/onboarding'),
        'editor': '[contenteditable="true"].ProseMirror, [contenteditable="true"][role="textbox"]',
    },
}
# Visible sign-in affordances. Matched as exact accessible names to avoid catching
# unrelated prose such as "sign in to save activity" inside a marketing panel.
SIGNIN_NAMES = ('Log in', 'Login', 'Sign in', 'Sign up', 'Giriş yap', 'Oturum aç', 'Kaydol', 'Üye ol')
CHALLENGE_TITLES = ('just a moment', 'bir dakika', 'verify you are human', 'security verification',
                    'checking your browser', 'attention required', 'un momento')
CHALLENGE_TEXT = ('Verify you are human', 'İnsan olduğunuzu doğrulayın', 'Doğrulama yapmanız gerekiyor',
                  'Performing security verification', 'Güvenlik doğrulaması yapılıyor')
QUOTA_TEXT = ('you’ve reached your', "you've reached your", 'usage limit reached', 'limitine ulaştın',
              'limitinize ulaştınız', 'research limit', 'araştırma sınırına', 'out of research',
              'no research left', 'upgrade to continue')
# Research entries are matched by their exact visible label, never by a page-wide text scan.
# Deep Think is a reasoning mode, not the required web Deep Research tool.
RESEARCH_LABELS = ('Deep research', 'Deep Research', 'Derin araştırma', 'Derin Araştırma',
                   'Research', 'Araştırma')


CHROME = os.environ.get('RESEARCH_CHROME', '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')


class BrowserAttention(Exception):
    """A condition only the user can clear. Never retried automatically."""

    def __init__(self, message, kind='browser_changed'):
        super().__init__(message)
        self.kind = kind


class BrowserRuntime:
    def __init__(self, root: Path, headless=False):
        self.root = Path(root)
        self.profile = self.root / 'browser-profile'
        self.lockfile = self.root / 'browser.lock'
        # A plain, automation-free Chrome used only for signing in. It owns the profile
        # exclusively while it runs, so the automation context must stay closed.
        self.loginpid = self.root / 'login-browser.pid'
        self.context = None
        self.playwright = None
        self.pages = {}
        self.lock = asyncio.Lock()
        # Only tests may set this. Production must stay headful; see module docstring.
        self.headless = headless
        self.identity = None

    # ---- lifecycle -------------------------------------------------------
    def login_browser_pid(self):
        """The pid of a live sign-in Chrome, or None."""
        if not self.loginpid.exists():
            return None
        try:
            pid = int(self.loginpid.read_text().strip())
            os.kill(pid, 0)
        except (ValueError, ProcessLookupError, OSError):
            self.loginpid.unlink(missing_ok=True)
            return None
        return pid

    def _claim_lock(self):
        """Refuse to share the profile with another live browser of ours."""
        pid = self.login_browser_pid()
        if pid:
            raise BrowserAttention(
                'Hesap giriş penceresi açık (pid ' + str(pid) + '). Girişleri tamamlayıp o '
                'Chrome penceresini tamamen kapatın, sonra tekrar deneyin.', 'login_required')
        if self.lockfile.exists():
            try:
                held = json.loads(self.lockfile.read_text())
                os.kill(int(held['pid']), 0)
            except (ValueError, KeyError, ProcessLookupError, json.JSONDecodeError, OSError):
                self.lockfile.unlink(missing_ok=True)
            else:
                if int(held['pid']) != os.getpid():
                    raise BrowserAttention(
                        'Araştırma tarayıcısı profili başka bir süreç tarafından kullanılıyor. '
                        'Diğer pencereyi kapatıp tekrar deneyin.', 'browser_unavailable')
        self.lockfile.write_text(json.dumps({'pid': os.getpid(), 'since': time.time()}))
        self.lockfile.chmod(0o600)

    async def start(self):
        async with self.lock:
            if self.context:
                return
            self._claim_lock()
            self.profile.mkdir(exist_ok=True, parents=True, mode=0o700)
            self.profile.chmod(0o700)
            self.playwright = await async_playwright().start()
            try:
                self.context = await self.playwright.chromium.launch_persistent_context(
                    str(self.profile), channel='chrome', headless=self.headless,
                    # Manual sign-in and automation share one profile and one macOS keychain
                    # entry. Playwright's mock keychain would make those cookies unreadable.
                    ignore_default_args=['--use-mock-keychain'],
                    args=['--disable-session-crashed-bubble', '--hide-crash-restore-bubble',
                          '--window-position=40,40'],
                    chromium_sandbox=True, accept_downloads=True,
                    viewport=None if not self.headless else {'width': 1440, 'height': 1000},
                )
            except Exception:
                await self.playwright.stop()
                self.playwright = None
                self.lockfile.unlink(missing_ok=True)
                raise BrowserAttention(
                    'Araştırma tarayıcısı açılamadı. Aynı profili kullanan başka bir pencere '
                    'açıksa kapatın.', 'browser_unavailable')
            self.context.set_default_timeout(8000)
            await self._verify_identity()

    async def _verify_identity(self):
        """Fail loudly if this ever regresses to a headless build."""
        page = await self.context.new_page()
        try:
            await page.goto('about:blank')
            self.identity = await page.evaluate('()=>({ua:navigator.userAgent})')
        finally:
            await page.close()
        if 'HeadlessChrome' in (self.identity.get('ua') or '') and not self.headless:
            await self._teardown()
            raise BrowserAttention(
                'Tarayıcı penceresiz kipte açıldı. Sağlayıcı doğrulaması bu kipi reddeder; '
                'araştırma başlatılmadı.', 'browser_unavailable')

    async def _teardown(self):
        if self.context:
            try:
                await self.context.close()
            except Exception:
                pass
        if self.playwright:
            try:
                await self.playwright.stop()
            except Exception:
                pass
        self.context = self.playwright = None
        self.pages.clear()
        self.lockfile.unlink(missing_ok=True)

    async def close(self):
        async with self.lock:
            await self._teardown()

    # ---- pages -----------------------------------------------------------
    async def page(self, key, provider, url=None):
        await self.start()
        page = self.pages.get(key)
        target = url or PROVIDERS[provider]['url']
        if urlparse(target).hostname not in PROVIDERS[provider]['hosts']:
            raise BrowserAttention('Araştırma adresi sağlayıcının izin verilen alan adıyla eşleşmiyor.')
        if page and not page.is_closed():
            # A tab left on an error page must be re-navigated, not reused as-is.
            if urlparse(page.url).hostname in PROVIDERS[provider]['hosts'] | PROVIDERS[provider]['auth_hosts']:
                return page
            try:
                await page.goto(target, wait_until='domcontentloaded', timeout=60000)
                return page
            except Exception:
                await page.close()
        page = await self.context.new_page()
        self.pages[key] = page
        try:
            await page.goto(target, wait_until='domcontentloaded', timeout=60000)
        except Exception:
            await page.close()
            self.pages.pop(key, None)
            raise BrowserAttention('Sağlayıcı sayfası yüklenemedi; bağlantı tekrar denenebilir.',
                                   'browser_unavailable')
        return page

    async def release(self, key):
        page = self.pages.pop(key, None)
        if page and not page.is_closed():
            try:
                await page.close()
            except Exception:
                pass

    # ---- state inspection ------------------------------------------------
    async def _any_visible(self, locator, limit=12):
        try:
            total = min(await locator.count(), limit)
        except Exception:
            return False
        for i in range(total):
            try:
                if await locator.nth(i).is_visible():
                    return True
            except Exception:
                continue
        return False

    async def _visible(self, page, selector):
        return await self._any_visible(page.locator(selector))

    async def _named_visible(self, page, role, names):
        """Playwright matches one accessible name at a time, so each is tried separately."""
        for name in names:
            if await self._any_visible(page.get_by_role(role, name=name, exact=True), limit=6):
                return True
        return False

    async def check(self, page, provider):
        """Inspect visible UI only. Never reads cookies, tokens or private endpoints."""
        title = (await page.title()).lower()
        parsed = urlparse(page.url)
        host = parsed.hostname or ''
        spec = PROVIDERS[provider]
        if any(t in title for t in CHALLENGE_TITLES):
            raise BrowserAttention(
                provider + ' güvenlik doğrulaması istiyor. Araştırma tarayıcısı penceresinde '
                'doğrulamayı siz tamamlayın; iş bekletildi.', 'verification_required')
        for label in CHALLENGE_TEXT:
            if await self._visible(page, 'text=' + label):
                raise BrowserAttention(
                    provider + ' güvenlik doğrulaması bekliyor. Araştırma tarayıcısı penceresinde '
                    'doğrulamayı siz tamamlayın.', 'verification_required')
        if host in spec['auth_hosts'] or (host in spec['hosts'] and parsed.path in spec['auth_paths']):
            raise BrowserAttention(provider + ' hesabına giriş gerekli. Araştırma tarayıcısı '
                                   'penceresinden giriş yapın.', 'login_required')
        if host not in spec['hosts']:
            raise BrowserAttention(provider + ' beklenmeyen bir adrese yönlendirdi: ' + host,
                                   'login_required')
        if await self._named_visible(page, 'button', SIGNIN_NAMES) or await self._named_visible(page, 'link', SIGNIN_NAMES):
            raise BrowserAttention(provider + ' web hesabına giriş gerekli.', 'login_required')
        alerts = await page.locator('[role="alert"], [role="dialog"]').all_text_contents()
        notices = '\n'.join(alerts).lower()
        if any(x in notices for x in QUOTA_TEXT):
            raise BrowserAttention(provider + ' araştırma kotası doldu. Başlatılmış işler korunuyor.',
                                   'quota_wait')

    async def research_entry(self, page, provider):
        """Locate the provider's real research-mode control without activating it.

        Returns the locator when the mode is genuinely offered to this account, or
        None. A missing entry means the account cannot run Deep Research; the caller
        must stop rather than fall back to an ordinary chat.
        """
        for label in RESEARCH_LABELS:
            for role in ('button', 'menuitem', 'menuitemradio', 'menuitemcheckbox', 'option', 'radio'):
                loc = page.get_by_role(role, name=label, exact=True)
                for i in range(min(await loc.count(), 6)):
                    item = loc.nth(i)
                    try:
                        if await item.is_visible() and await item.is_enabled():
                            return item
                    except Exception:
                        continue
        return None

    async def status(self, provider, deep=False):
        """Report the provider connection. `deep` also confirms research-mode access."""
        key = 'connection:' + provider
        try:
            page = await self.page(key, provider)
            await self.check(page, provider)
            editor = page.locator(PROVIDERS[provider]['editor'])
            try:
                await editor.first.wait_for(state='visible', timeout=12000)
            except Exception:
                # A challenge or sign-in wall can appear after the first paint.
                await self.check(page, provider)
                raise BrowserAttention(
                    provider + ' sayfası açıldı ancak kullanılabilir sohbet alanı doğrulanamadı.',
                    'browser_changed')
            if not deep:
                return {'provider': provider, 'status': 'connected',
                        'message': 'Oturum açık. Araştırma modu erişimi iş başlatılırken doğrulanır.'}
            entry = await self.research_entry(page, provider)
            if entry is None:
                return {'provider': provider, 'status': 'research_unavailable',
                        'message': provider + ' hesabında Deep Research modu görünmüyor. '
                        'Abonelik veya kota durumunu kontrol edin; normal sohbete düşülmedi.'}
            return {'provider': provider, 'status': 'connected',
                    'message': 'Oturum açık ve araştırma modu bu hesapta mevcut.'}
        except BrowserAttention as exc:
            return {'provider': provider, 'status': exc.kind, 'message': str(exc)}
        except Exception:
            return {'provider': provider, 'status': 'browser_changed',
                    'message': provider + ' bağlantısı doğrulanamadı.'}

    async def open_login_browser(self):
        """Launch a plain Chrome on this profile so the user can sign in personally.

        Providers refuse sign-in from an automation-controlled browser, so this must not
        go through Playwright: no CDP connection, no automation flags. The Chrome binary
        is executed directly rather than through `open -a`, which hands arguments to an
        already-running Chrome and would silently use the everyday profile instead.

        Credentials are never typed, read or stored by this service.
        """
        pid = self.login_browser_pid()
        if pid:
            return {'pid': pid, 'already_open': True}
        if not os.access(CHROME, os.X_OK):
            raise BrowserAttention('Google Chrome bulunamadı: ' + CHROME, 'browser_unavailable')
        # The automation browser must release the profile before Chrome opens it.
        await self.close()
        self.profile.mkdir(exist_ok=True, parents=True, mode=0o700)
        process = subprocess.Popen(
            [CHROME, '--user-data-dir=' + str(self.profile), '--no-first-run',
             '--no-default-browser-check'] + [spec['url'] for spec in PROVIDERS.values()],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        self.loginpid.write_text(str(process.pid))
        self.loginpid.chmod(0o600)
        return {'pid': process.pid, 'already_open': False}
