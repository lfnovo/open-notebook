"""Durable native web research using the user's signed-in Chrome extension."""
from __future__ import annotations
import asyncio
import time
from pathlib import Path
from urllib.parse import urlsplit
from markdownify import markdownify
from bs4 import BeautifulSoup
from browser_runtime import BrowserAttention, PROVIDERS
from browser_research import BrowserResearch
from extension_bridge import ExtensionBridge
from workflow import citations, digest, now


def report_markdown(html):
    """Keep report text/figures; decorative source favicons are not evidence URLs."""
    document=BeautifulSoup(html,'html.parser')
    for image in document.select('img[src]'):
        url=urlsplit(image['src'])
        if url.hostname and url.hostname.endswith('.gstatic.com') and ('favicon' in url.path.lower() or '/immersives/google_logo_icon_' in url.path):
            image.decompose()
    # Provider source cards put block elements inside anchors. Markdown link
    # labels cannot contain blank paragraphs: normalize their text before
    # conversion so adjacent cards keep separate, usable hrefs.
    for anchor in document.select('a[href]'):
        if anchor.find(['div','p']) and not anchor.find('img'):
            label=' '.join(anchor.get_text(' ',strip=True).split())
            anchor.clear();anchor.append(label)
    def code_language(element):
        classes = list(element.get('class', []))
        if element.code:
            classes += element.code.get('class', [])
        return next((x.removeprefix('language-') for x in classes if x in ('language-evidence-ledger','language-json')), '')
    return markdownify(str(document),heading_style='ATX',code_language_callback=code_language,
                       strip=['script','style','button','svg','nav']).strip()


def check_state(state):
    if state.get('challenge_visible'):
        raise BrowserAttention('Sağlayıcı güvenlik doğrulaması bekliyor; araştırma sekmesinden tamamlayın.', 'verification_required')
    if state.get('quota_visible'):
        raise BrowserAttention('Sağlayıcının araştırma kotası doldu.', 'quota_wait')


def is_evidence_url(value):
    """A public source candidate, NOT proof that it supports a claim.

    Keep public vendor documentation (e.g. openai.com); exclude conversation,
    authentication and report-rendering infrastructure on domain boundaries.
    """
    try:
        url = urlsplit(value)
        host = (url.hostname or '').lower()
        blocked = ('chatgpt.com', 'claude.ai', 'gemini.google.com', 'accounts.google.com',
                   'auth.openai.com', 'oaiusercontent.com', 'gstatic.com')
        return url.scheme in ('http', 'https') and bool(host) and not any(host == x or host.endswith('.'+x) for x in blocked)
    except (ValueError, TypeError):
        return False


def report_sources(content, links):
    seen = set(citations(content))
    for link in links:
        url = link.get('url', '')
        if is_evidence_url(url) and url not in seen:
            seen.add(url)
            content += '\n\n- ['+(link.get('title') or url)+']('+url+')'
    return content, [url for url in citations(content) if is_evidence_url(url)]


class ExtensionRuntime:
    transport = 'extension'
    def __init__(self, root=None):
        self.bridge = ExtensionBridge(root) if root else ExtensionBridge()

    @property
    def context(self):
        return self.bridge.connected()

    def login_browser_pid(self):
        return None

    async def close(self):
        # The user's Chrome and running remote jobs stay open on service shutdown.
        pass

    async def open_login_browser(self):
        if not self.bridge.connected():
            raise BrowserAttention('Günlük Chrome’da Open Notebook araştırma eklentisini açıp yerel bağlantıyı başlatın.', 'browser_unavailable')
        return {'pid': None, 'already_open': True, 'transport': 'extension'}

    async def state(self, provider, key, wait_ready=0):
        deadline = time.monotonic() + wait_ready
        consecutive_ready=0
        while True:
            value = await self.bridge.request('inspect', provider, key)
            check_state(value)
            if value.get('composer_visible') and value.get('tools_ready') and not value.get('sign_in_visible'):
                consecutive_ready+=1
                if not wait_ready or consecutive_ready>=2:return value
            else:consecutive_ready=0
            if time.monotonic() >= deadline:
                if value.get('sign_in_visible'):
                    raise BrowserAttention('Günlük Chrome profilinde '+provider+' hesabına giriş gerekli.', 'login_required')
                raise BrowserAttention(provider+' sayfasının yüklenmesi tamamlanmadı.', 'browser_changed')
            await asyncio.sleep(2)

    async def status(self, provider, deep=False):
        key = 'connection:' + provider
        try:
            await self.bridge.request('open', provider, key)
            state = await self.state(provider, key, wait_ready=45)
            if deep and not state.get('research_selected'):
                state = await self.bridge.request('select_research', provider, key)
            return {'provider': provider, 'status': 'connected', 'transport': 'extension',
                    'message': 'Araştırma modu seçilebildi; gerçek rapor üretimi ayrıca doğrulanmalıdır.' if deep else 'Chrome sayfasına erişiliyor; araştırma modu iş başlatılırken doğrulanır.'}
        except BrowserAttention as exc:
            return {'provider': provider, 'status': exc.kind, 'transport': 'extension', 'message': str(exc)}


class ExtensionResearch(BrowserResearch):
    def __init__(self, runtime, root, timeout=7200, poll_seconds=8, max_watch_seconds=86400):
        super().__init__(runtime, root, timeout=timeout, poll_seconds=poll_seconds)
        self.max_watch_seconds = max(timeout, max_watch_seconds)

    async def research(self, run_id, stage, prompt, progress):
        sid, provider = stage['id'], stage['provider']
        folder = self.folder(run_id, sid)
        key = run_id + ':' + sid
        job = self.load(run_id, sid)
        if job and job.get('phase') == 'completed':
            path = folder / 'report.md'
            if not path.is_file() or digest(path.read_text()) != job.get('report_sha256'):
                raise BrowserAttention('Saklanan raporun bütünlüğü doğrulanamadı.')
            return {'content': path.read_text(), 'url': job['url']}
        if not job:
            job = {'phase': 'prepared', 'provider': provider, 'transport': 'extension',
                   'prompt_sha256': digest(prompt), 'created_at': now(),
                   'marker': 'ON-' + run_id[:12] + '-' + sid, 'url': None, 'research_started': False}
            self.save(run_id, sid, job)
        elif job['prompt_sha256'] != digest(prompt):
            raise BrowserAttention('Görev paketi değişmiş; gönderim tekrarlanmadı.', 'submission_uncertain')
        elif job.get('transport') != 'extension':
            raise BrowserAttention('Önceki görev başka tarayıcı bağlantısıyla başlatılmış. Otomatik tekrar yapılmadı.', 'submission_uncertain')
        bridge = self.runtime.bridge
        await bridge.request('open', provider, key, url=job.get('url'), marker=job['marker'])
        state = await self.runtime.state(provider, key, wait_ready=60)
        full = prompt + '\n\nKullanıcıdan ek soru isteme; makul varsayımları belirt. Görev kimliği: ' + job['marker']
        if job['phase'] in ('submitting', 'submit_unconfirmed'):
            if not state.get('marker_present'):
                raise BrowserAttention('Önceki gönderimin sonucu belirsiz. Aynı araştırma yeniden gönderilmedi.', 'submission_uncertain')
            job.update(phase='submitted', url=state['url'])
            self.save(run_id, sid, job)
        if job['phase'] == 'prepared':
            await progress({'phase': 'preparing', 'message': provider+' araştırma sekmesi hazırlanıyor.'})
            if not state.get('research_selected'):
                state = await bridge.request('select_research', provider, key)
            if not state.get('research_selected'):
                raise BrowserAttention('Native araştırma modu doğrulanamadı.', 'research_unavailable')
            packet = folder / 'input-packet.md'
            packet.write_text(full); packet.chmod(0o600)
            for _ in range(60):
                prepared=await bridge.request('fill', provider, key, text=full)
                if prepared.get('prepared'):break
                if not prepared.get('pending_upload'):
                    raise BrowserAttention('Tam görev paketi hazırlanamadı.')
                await asyncio.sleep(2)
            else:
                raise BrowserAttention('Tam paket dosyasının yüklenmesi tamamlanmadı; gönderilmedi.')
            # Uploads can finish after the editor becomes ready. The driver and send
            # readiness must both confirm before committing a submission attempt.
            for _ in range(45):
                state = await bridge.request('inspect', provider, key)
                check_state(state)
                if state.get('send_ready') and state.get('research_selected'):
                    break
                await asyncio.sleep(2)
            else:
                raise BrowserAttention('İstem veya dosya yüklemesi gönderime hazır değil.')
            job['phase'] = 'submitting'; self.save(run_id, sid, job)
            await bridge.request('submit', provider, key)
            job['phase'] = 'submit_unconfirmed'; self.save(run_id, sid, job)
            for _ in range(45):
                state = await bridge.request('inspect', provider, key)
                check_state(state)
                if state.get('marker_present'):
                    job.update(phase='submitted', url=state['url']); self.save(run_id, sid, job)
                    break
                await asyncio.sleep(2)
            if job['phase'] != 'submitted':
                raise BrowserAttention('Gönderim sağlayıcıda doğrulanamadı; otomatik tekrar yapılmadı.', 'submission_uncertain')
        await progress({'phase': job['phase'], 'url': job.get('url'), 'message': provider+' kaynakları araştırıyor.'})
        started = time.monotonic()
        deadline = started + self.timeout
        hard_deadline = started + self.max_watch_seconds
        previous = None; stable = 0
        while time.monotonic() < hard_deadline:
            if time.monotonic() >= deadline:
                # Renew observation only. Never refill, resend or restart a plan.
                # Unknown / unconfirmed conversations still require human review.
                if not self.conversation_url(provider, job.get('url') or ''):
                    break
                deadline = min(time.monotonic() + self.timeout, hard_deadline)
                await progress({'phase': 'monitoring', 'url': job['url'],
                                'message': provider+' araştırmasının mevcut konuşması izleniyor; yeni istek gönderilmedi.'})
            state = await bridge.request('inspect', provider, key)
            check_state(state)
            if state.get('sign_in_visible'):
                raise BrowserAttention('Araştırma sırasında sağlayıcı oturumu kapandı.', 'login_required')
            if state.get('marker_present') and self.conversation_url(provider, state['url']):
                if job.get('url') != state['url']:
                    job['url'] = state['url']; self.save(run_id, sid, job)
            if state.get('plan_visible') and not (job.get('plan_attempted') or job.get('research_started') or state.get('research_complete') or state.get('busy')):
                job.update(phase='plan_confirming', plan_attempted=True); self.save(run_id, sid, job)
                await bridge.request('start_plan', provider, key)
                await asyncio.sleep(2)
                state = await bridge.request('inspect', provider, key)
                check_state(state)
            if state.get('research_progress') or state.get('research_complete'):
                if not job['research_started']:
                    job.update(research_started=True, phase='researching'); self.save(run_id, sid, job)
                    await progress({'phase': 'researching', 'url': state['url'], 'message': provider+' araştırması sürüyor.'})
            result = await bridge.request('collect', provider, key, research_started=job['research_started'])
            report = result.get('report')
            if report:
                content = report_markdown(report['html'])
                content, external = report_sources(content, report.get('links', []))
                if not external:
                    raise BrowserAttention('Rapor görünüyor ancak kaynak bağlantıları alınamadı; tamamlandı sayılmadı.')
                current = digest(content)
                stable = stable + 1 if current == previous else 0
                previous = current
                if stable >= 2:
                    for filename, data in (('report.md', content), ('report.html', report['html'])):
                        path = folder / filename; path.write_text(data); path.chmod(0o600)
                    job.update(phase='completed', url=result['url'], finished_at=now(), report_sha256=current,
                               completion_evidence=report['completion'])
                    self.save(run_id, sid, job)
                    return {'content': content, 'url': result['url']}
            else:
                stable = 0; previous = None
            await asyncio.sleep(self.poll_seconds)
        raise BrowserAttention('İzleme süresi doldu. Araştırma yeniden gönderilmeden aynı sekmeden sürdürülebilir.', 'interrupted')
