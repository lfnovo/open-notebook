"""Durable, UI-only native Deep Research jobs in the dedicated browser.

Two invariants govern this module:

1. A research submission is never replayed blindly. The durable journal is written
   immediately before the send click and never before, so a crash during preparation
   costs nothing while a crash after the click is always recoverable by reconciling
   against the provider's own conversation list.
2. An ordinary chat answer is never accepted as research. The research mode must be
   observably selected before sending, and a report must carry provider completion
   evidence plus external sources before it counts as done.
"""
from __future__ import annotations
import asyncio
import json
import os
from pathlib import Path
import re
import time
from urllib.parse import urlparse
from markdownify import markdownify
from browser_runtime import BrowserAttention, PROVIDERS, RESEARCH_LABELS
from workflow import citations, digest, now

TOOL_MENUS = {
    'ChatGPT': ('Tools', 'Araçlar', 'Add files and more', 'Dosya ve daha fazlasını ekle',
                'Add files and tools', 'Dosya ve araç ekle'),
    'Gemini': ('Tools', 'Araçlar', 'Add files', 'Dosya ekle', 'More', 'Daha fazla'),
    'Claude': ('Search and tools', 'Search & tools', 'Ara ve araçlar', 'Araçlar', 'Tools',
               'Open tools menu', 'Araç menüsünü aç'),
}
PLAN_NAMES = ('Start research', 'Start researching', 'Begin research', 'Araştırmayı başlat',
              'Araştırmaya başla')
SEND_NAMES = ('Send', 'Send message', 'Submit', 'Gönder', 'Mesaj gönder', 'İleti gönder')
SOURCE_NAMES = ('Sources', 'Kaynaklar', 'View sources', 'Kaynakları görüntüle')
COMPLETION = re.compile(r'(research (is )?(complete|completed|finished)|completed (the )?research|'
                        r'araştırma tamamlandı|araştırmayı tamamladım|araştırma bitti|'
                        r'researched .{0,40} sources|kaynak incelendi)', re.I)
PROGRESS = re.compile(r'(researching|conducting research|gathering sources|reading sources|'
                      r'araştırılıyor|araştırma yapılıyor|kaynaklar inceleniyor)', re.I)
ASSISTANT_SELECTORS = {
    'ChatGPT': '[data-message-author-role="assistant"]',
    'Gemini': 'deep-research-report, [data-test-id="deep-research-report"], .research-report, '
              '.canvas-content, model-response',
    'Claude': '[data-testid="assistant-message"], .font-claude-response',
}
USER_SELECTORS = {
    'ChatGPT': '[data-message-author-role="user"]',
    'Gemini': 'user-query, [data-test-id="user-query"]',
    'Claude': '[data-testid="user-message"]',
}
COMPOSER_SCOPES = {
    'ChatGPT': 'form, [data-testid="composer"], [class*="composer"]',
    'Gemini': 'input-container, .input-area, form',
    'Claude': 'fieldset, form, [class*="composer"]',
}
STOP_SELECTOR = ('button[data-testid="stop-button"], button[aria-label="Stop response"], '
                 'button[aria-label="Stop generating"], button[aria-label="Yanıtı durdur"], '
                 'button[aria-label="Stop streaming"]')
# Reads the *selected* state of a control. Three rules matter here:
#  - a control that is not visible proves nothing, in either direction;
#  - an explicit "not selected" (aria-pressed="false", data-state="off", …) is a veto,
#    never merely the absence of a positive;
#  - the presence of the label alone is never evidence of anything.
SELECTED_JS = """(labels)=>{
  const visible=el=>{
    if(!el.getClientRects().length) return false;
    const s=getComputedStyle(el);
    return s.visibility!=='hidden' && s.display!=='none' && s.opacity!=='0';
  };
  const norm=s=>(s||'').trim();
  const matches=el=>{
    const t=norm(el.innerText)||norm(el.getAttribute('aria-label'))||norm(el.getAttribute('title'));
    return labels.some(l=>t===l||t.startsWith(l+'\\n'));
  };
  const POS=['on','active','checked','selected','true'];
  const NEG=['off','inactive','unchecked','false'];
  const sel='button,[role=button],[role=menuitemradio],[role=menuitemcheckbox],[role=option],'+
            '[role=radio],[role=switch],[role=tab],[data-state],[aria-pressed],[aria-checked],[aria-selected]';
  let negative=false,positive='';
  for(const el of document.querySelectorAll(sel)){
    if(!matches(el)||!visible(el)) continue;
    const ds=(el.getAttribute('data-state')||'').toLowerCase();
    const flags=[el.getAttribute('aria-pressed'),el.getAttribute('aria-checked'),el.getAttribute('aria-selected')];
    if(flags.indexOf('true')>=0) positive=positive||'aria';
    else if(POS.indexOf(ds)>=0) positive=positive||'data-state';
    else if(flags.indexOf('false')>=0||NEG.indexOf(ds)>=0) negative=true;
  }
  return JSON.stringify({positive:positive,negative:negative});
}"""
# A selected tool is rendered as a visible pill carrying its own remove control. The
# label on its own is not a chip, and a control that says it is off is not a chip either.
CHIP_JS = """(args)=>{
  const labels=args[0],scope=args[1];
  const visible=el=>{
    if(!el.getClientRects().length) return false;
    const s=getComputedStyle(el);
    return s.visibility!=='hidden' && s.display!=='none' && s.opacity!=='0';
  };
  const REMOVE=/(remove|clear|dismiss|kaldır|kaldir|sil|temizle|close|kapat|×|✕)/i;
  const NEG=['off','inactive','unchecked'];
  for(const root of document.querySelectorAll(scope)){
    for(const el of root.querySelectorAll('*')){
      if(el.children.length>2||!visible(el)) continue;
      const t=(el.innerText||'').trim();
      if(!labels.some(l=>t===l)) continue;
      const owner=el.closest('button,[role=button],[aria-pressed],[aria-checked],[data-state]')||el;
      const ds=(owner.getAttribute('data-state')||'').toLowerCase();
      if(owner.getAttribute('aria-pressed')==='false'||owner.getAttribute('aria-checked')==='false'||NEG.indexOf(ds)>=0) continue;
      const host=el.closest('[class*=chip],[class*=pill],[class*=badge],[data-testid]')||el.parentElement||el;
      const controls=Array.prototype.slice.call(host.querySelectorAll('button,[role=button]'));
      if(controls.some(c=>REMOVE.test((c.getAttribute('aria-label')||'')+' '+(c.getAttribute('title')||'')+' '+(c.innerText||'')))) return true;
    }
  }
  return false;
}"""


class BrowserResearch:
    def __init__(self, runtime, root, timeout=7200, poll_seconds=8, confirm_seconds=60,
                 upload_seconds=180):
        self.runtime = runtime
        self.root = Path(root) / 'browser_jobs'
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.timeout = timeout
        self.poll_seconds = poll_seconds
        # How long a send may take to identify its conversation before it is treated as
        # uncertain, and how long an attachment may take to finish processing.
        self.confirm_seconds = confirm_seconds
        self.upload_seconds = upload_seconds

    # ---- durable journal -------------------------------------------------
    def folder(self, run_id, stage_id):
        if not re.fullmatch(r'[a-f0-9]{32}', run_id) or not re.fullmatch(r'[a-z_]+', stage_id):
            raise BrowserAttention('Geçersiz araştırma iş kimliği.')
        path = self.root / run_id / stage_id
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
        return path

    def load(self, run_id, stage_id):
        path = self.folder(run_id, stage_id) / 'job.json'
        return json.loads(path.read_text()) if path.exists() else None

    def save(self, run_id, stage_id, job):
        folder = self.folder(run_id, stage_id)
        target = folder / 'job.json'
        temp = folder / 'job.json.tmp'
        with temp.open('w') as out:
            os.chmod(temp, 0o600)
            out.write(json.dumps(job, ensure_ascii=False, indent=2))
            out.flush()
            os.fsync(out.fileno())
        temp.replace(target)

    def can_resume(self, run_id, stage_id):
        job = self.load(run_id, stage_id)
        return bool(job and job.get('phase') not in ('failed',))

    async def close(self):
        await self.runtime.close()

    def artifacts(self, run_id, stage_id):
        """Files this job produced, for export and backup."""
        folder = self.folder(run_id, stage_id)
        return [p for p in (folder / 'report.md', folder / 'report.html',
                            folder / 'input-packet.md', folder / 'job.json') if p.is_file()]

    # ---- small UI helpers ------------------------------------------------
    async def click_named(self, page, names, roles=('button', 'menuitem', 'menuitemcheckbox',
                                                    'menuitemradio', 'option'), required=None):
        for name in names:
            for role in roles:
                loc = page.get_by_role(role, name=name, exact=True)
                for i in range(min(await loc.count(), 6)):
                    item = loc.nth(i)
                    try:
                        if await item.is_visible() and await item.is_enabled():
                            await item.click()
                            return True
                    except Exception:
                        continue
        if required:
            raise BrowserAttention(required, 'browser_changed')
        return False

    async def scoped_text(self, page, selector):
        loc = page.locator(selector)
        if not await loc.count():
            return ''
        return '\n'.join(await loc.all_text_contents())

    async def is_busy(self, page):
        loc = page.locator(STOP_SELECTOR)
        for i in range(min(await loc.count(), 4)):
            try:
                if await loc.nth(i).is_visible():
                    return True
            except Exception:
                continue
        return False

    # ---- research mode ---------------------------------------------------
    async def research_selected(self, page, provider):
        labels = list(RESEARCH_LABELS)
        negative = False
        try:
            state = json.loads(await page.evaluate(SELECTED_JS, labels) or '{}')
            if state.get('positive'):
                return True
            negative = bool(state.get('negative'))
        except Exception:
            pass
        if negative:
            # The provider itself reports the mode as not engaged. A chip-shaped element
            # must never be allowed to overrule that.
            return False
        try:
            return bool(await page.evaluate(CHIP_JS, [labels, COMPOSER_SCOPES[provider]]))
        except Exception:
            return False

    async def enable_research(self, page, provider):
        """Engage the provider's real research mode, or stop. Never falls back to chat."""
        entry = await self.runtime.research_entry(page, provider)
        if entry is None:
            await self.click_named(page, TOOL_MENUS[provider])
            await page.wait_for_timeout(500)
            entry = await self.runtime.research_entry(page, provider)
        if entry is None:
            raise BrowserAttention(
                provider + ' arayüzünde Deep Research modu bulunamadı. Hesabın bu moda erişimi '
                'veya kalan kotası olmayabilir. Normal sohbet başlatılmadı.', 'research_unavailable')
        await entry.click()
        await page.wait_for_timeout(800)
        if not await self.research_selected(page, provider):
            # Closing a leftover menu can reveal the composer chip that proves selection.
            await page.keyboard.press('Escape')
            await page.wait_for_timeout(600)
            if not await self.research_selected(page, provider):
                raise BrowserAttention(
                    provider + ' için araştırma modunun seçili olduğu doğrulanamadı. Soru '
                    'gönderilmedi; normal sohbete düşülmedi.', 'browser_changed')

    # ---- submission ------------------------------------------------------
    async def prepare(self, page, provider, text, folder):
        """Fill the composer. Nothing here can start a research run."""
        editor = page.locator(PROVIDERS[provider]['editor']).first
        await editor.wait_for(state='visible', timeout=15000)
        if len(text) <= 18000:
            await editor.fill(text)
            return
        packet = folder / 'input-packet.md'
        packet.write_text(text)
        packet.chmod(0o600)
        upload = page.locator('input[type="file"]')
        if not await upload.count():
            await self.click_named(page, ('Add files and more', 'Add files and tools', 'Add files',
                                          'Dosya ekle', 'Upload', 'Yükle', 'Attach files',
                                          'Dosya ekleyin'))
            upload = page.locator('input[type="file"]')
        if not await upload.count():
            raise BrowserAttention('Tam veri paketi için dosya yükleme alanı bulunamadı. '
                                   'Metin kısaltılmadı.', 'browser_changed')
        await upload.first.set_input_files(str(packet))
        name_shown = page.get_by_text('input-packet.md', exact=False)
        try:
            await name_shown.first.wait_for(state='visible', timeout=90000)
        except Exception:
            raise BrowserAttention('Tam veri paketinin yüklendiği doğrulanamadı. Araştırma '
                                   'gönderilmedi.', 'browser_changed')
        # A visible filename only proves the pick. Wait for the upload to finish processing:
        # providers keep the send control disabled and show a progress indicator until then.
        deadline = time.monotonic() + self.upload_seconds
        while time.monotonic() < deadline:
            busy = page.locator('[role="progressbar"], [data-testid*="uploading"], '
                                '[aria-label*="Uploading"], [aria-label*="Yükleniyor"]')
            still = False
            for i in range(min(await busy.count(), 4)):
                try:
                    still = still or await busy.nth(i).is_visible()
                except Exception:
                    continue
            if not still and await self.send_control(page) is not None:
                break
            await asyncio.sleep(2)
        else:
            raise BrowserAttention('Yüklenen veri paketinin işlenmesi tamamlanmadı. Araştırma '
                                   'gönderilmedi.', 'browser_changed')
        await editor.fill(
            'Ekli input-packet.md dosyasındaki görevi ve önceki raporların tamamını kullan. '
            'Dosyayı tamamen inceleyerek seçili Deep Research modunda araştırmayı yap. '
            'Soru sorma; gerekli makul varsayımları raporda belirt.')

    async def send_control(self, page):
        """The enabled send control, or None when the composer is not ready to submit."""
        loc = page.locator('[data-testid="send-button"], button[aria-label="Send prompt"], '
                           'button[aria-label="Send Message"], button[type="submit"]')
        for i in range(min(await loc.count(), 4)):
            item = loc.nth(i)
            try:
                if await item.is_visible() and await item.is_enabled():
                    return item
            except Exception:
                continue
        for name in SEND_NAMES:
            loc = page.get_by_role('button', name=name, exact=True)
            for i in range(min(await loc.count(), 4)):
                item = loc.nth(i)
                try:
                    if await item.is_visible() and await item.is_enabled():
                        return item
                except Exception:
                    continue
        return None

    @staticmethod
    def conversation_url(provider, url):
        parsed = urlparse(url)
        if parsed.hostname not in PROVIDERS[provider]['hosts']:
            return False
        if provider == 'ChatGPT':
            return '/c/' in parsed.path
        if provider == 'Gemini':
            return bool(re.fullmatch(r'/app/[a-zA-Z0-9_-]+', parsed.path))
        return '/chat/' in parsed.path

    async def marker_present(self, page, provider, marker):
        """True when our own submitted question is visible in the transcript."""
        return marker in await self.scoped_text(page, USER_SELECTORS[provider])

    async def reconcile(self, page, provider, marker):
        """Find an already-submitted run instead of sending the same research twice."""
        if await self.marker_present(page, provider, marker):
            return page.url
        try:
            await page.goto(PROVIDERS[provider]['url'], wait_until='domcontentloaded', timeout=60000)
            await page.wait_for_timeout(3000)
        except Exception:
            return None
        links = await page.locator('nav a[href], aside a[href]').evaluate_all(
            '(els)=>els.map(a=>a.href).slice(0,40)')
        seen = []
        for href in links:
            if not self.conversation_url(provider, href) or href in seen:
                continue
            seen.append(href)
            if len(seen) > 8:
                break
            try:
                await page.goto(href, wait_until='domcontentloaded', timeout=60000)
                await page.wait_for_timeout(2500)
            except Exception:
                continue
            if await self.marker_present(page, provider, marker):
                return page.url
        return None

    # ---- completion ------------------------------------------------------
    async def collect(self, page, provider, job):
        candidates = page.locator(ASSISTANT_SELECTORS[provider])
        if not await candidates.count():
            return None
        candidate = candidates.last
        if not await candidate.is_visible():
            return None
        text = await candidate.inner_text()
        if len(text) < 1200:
            return None
        if await self.is_busy(page):
            return None
        # Scope progress and completion wording to the assistant's own output. The page
        # body also contains our prompt, and matching that would fake a completion.
        assistant = await self.scoped_text(page, ASSISTANT_SELECTORS[provider])
        if PROGRESS.search(assistant[-5000:]) and not COMPLETION.search(assistant[-12000:]):
            return None
        explicit_complete = bool(COMPLETION.search(assistant))
        export_control = None
        for name in ('Share & export', 'Share and export', 'Paylaş ve dışa aktar', 'Export report',
                     'Download report', 'Raporu indir', 'Open report', 'Raporu aç'):
            loc = page.get_by_role('button', name=name, exact=True)
            for i in range(min(await loc.count(), 4)):
                try:
                    if await loc.nth(i).is_visible():
                        export_control = True
                except Exception:
                    continue
        if not explicit_complete and not (job.get('research_started') and export_control):
            return None
        html = await candidate.inner_html()
        content = markdownify(html, heading_style='ATX', strip=['button', 'script', 'style', 'svg', 'nav'])
        links = citations(content)
        external = [u for u in links if urlparse(u).hostname not in PROVIDERS[provider]['hosts']]
        if not external:
            if await self.click_named(page, SOURCE_NAMES):
                panel = page.locator('[role="dialog"], [data-testid*="source"], [data-testid*="citation"]')
                hrefs = await panel.locator('a[href^="http"]').evaluate_all(
                    '(els)=>els.map(a=>({title:a.innerText,url:a.href}))')
                for item in hrefs:
                    if urlparse(item['url']).hostname not in PROVIDERS[provider]['hosts']:
                        content += '\n\n- [' + (item['title'] or item['url']) + '](' + item['url'] + ')'
                        external.append(item['url'])
                await page.keyboard.press('Escape')
        if not external:
            raise BrowserAttention('Araştırma sonucu görünüyor ancak kaynak bağlantıları alınamadı. '
                                   'Eksik rapor tamamlandı sayılmadı.', 'browser_changed')
        return {'content': content.strip(), 'html': html, 'url': page.url}

    # ---- the job ---------------------------------------------------------
    async def research(self, run_id, stage, prompt, progress):
        sid = stage['id']
        provider = stage['provider']
        folder = self.folder(run_id, sid)
        job = self.load(run_id, sid)
        if job and job.get('phase') == 'completed':
            report = folder / 'report.md'
            if not report.is_file() or digest(report.read_text()) != job['report_sha256']:
                raise BrowserAttention('Saklanan araştırma raporunun bütünlüğü doğrulanamadı.')
            return {'content': report.read_text(), 'url': job['url']}
        if not job:
            job = {'phase': 'prepared', 'provider': provider, 'prompt_sha256': digest(prompt),
                   'created_at': now(), 'marker': 'ON-' + run_id[:12] + '-' + sid,
                   'url': None, 'research_started': False}
            self.save(run_id, sid, job)
        elif job['prompt_sha256'] != digest(prompt):
            raise BrowserAttention('Bu araştırmanın girdi paketi değişmiş; önceki gönderim '
                                   'otomatik tekrarlanmadı.', 'submission_uncertain')
        page = await self.runtime.page(run_id + ':' + sid, provider, job.get('url'))
        await self.runtime.check(page, provider)
        full = prompt + ('\n\nKullanıcıdan ek soru isteme. Eksik kapsamı makul varsayımlarla '
                         'tamamla ve varsayımları raporda belirt. Görev kimliği: ') + job['marker']

        if job['phase'] in ('submitting', 'submit_unconfirmed') and not job.get('url'):
            # A send may or may not have landed. Look for it before considering a resend.
            found = await self.reconcile(page, provider, job['marker'])
            if not found:
                raise BrowserAttention(
                    'Önceki gönderimin sonucu belirsiz ve sağlayıcıda eşleşen bir araştırma '
                    'bulunamadı. Aynı araştırma kendiliğinden tekrarlanmadı; bu aşamayı elle '
                    'inceleyin.', 'submission_uncertain')
            job['url'] = found
            job['phase'] = 'submitted'
            self.save(run_id, sid, job)

        if job['phase'] == 'prepared':
            await progress({'phase': 'preparing', 'message': provider + ' Deep Research modu hazırlanıyor.'})
            await self.enable_research(page, provider)
            await self.prepare(page, provider, full, folder)
            control = await self.send_control(page)
            if control is None:
                raise BrowserAttention('Gönderme düğmesi etkin değil. Araştırma gönderilmedi.',
                                       'browser_changed')
            # Everything that could fail without submitting has now succeeded. Commit the
            # journal immediately before the click so an uncertain send is never replayed.
            job['phase'] = 'submitting'
            self.save(run_id, sid, job)
            await control.click()
            job['phase'] = 'submit_unconfirmed'
            self.save(run_id, sid, job)
            for _ in range(self.confirm_seconds):
                if self.conversation_url(provider, page.url):
                    job['url'] = page.url
                    job['phase'] = 'submitted'
                    self.save(run_id, sid, job)
                    break
                if await self.marker_present(page, provider, job['marker']):
                    job['phase'] = 'submitted'
                    self.save(run_id, sid, job)
                    break
                await asyncio.sleep(1)
            if job['phase'] != 'submitted':
                found = await self.reconcile(page, provider, job['marker'])
                if not found:
                    raise BrowserAttention('Gönderimin sonucu doğrulanamadı. Aynı araştırma tekrar '
                                           'gönderilmedi.', 'submission_uncertain')
                job['url'] = found
                job['phase'] = 'submitted'
                self.save(run_id, sid, job)

        await progress({'phase': job['phase'], 'message': provider + ' web araştırması bekleniyor.',
                        'url': job.get('url')})
        deadline = time.monotonic() + self.timeout
        last_hash = None
        stable = 0
        while time.monotonic() < deadline:
            await self.runtime.check(page, provider)
            if not job.get('url') and self.conversation_url(provider, page.url):
                job['url'] = page.url
                self.save(run_id, sid, job)
            assistant = await self.scoped_text(page, ASSISTANT_SELECTORS[provider])
            if not job.get('research_started'):
                plan = None
                for name in PLAN_NAMES:
                    loc = page.get_by_role('button', name=name, exact=True)
                    for i in range(min(await loc.count(), 4)):
                        item = loc.nth(i)
                        try:
                            if await item.is_visible() and await item.is_enabled():
                                plan = item
                                break
                        except Exception:
                            continue
                    if plan is not None:
                        break
                if plan is not None:
                    job['phase'] = 'plan_confirming'
                    self.save(run_id, sid, job)
                    await plan.click()
                    await page.wait_for_timeout(2000)
                    # Reconcile the click against the UI instead of assuming it landed.
                    if await self.is_busy(page) or PROGRESS.search(
                            await self.scoped_text(page, ASSISTANT_SELECTORS[provider])):
                        job['research_started'] = True
                        job['phase'] = 'researching'
                        self.save(run_id, sid, job)
                        await progress({'phase': 'researching', 'url': page.url,
                                        'message': 'Araştırma planı onaylandı; ' + provider +
                                                   ' kaynakları inceliyor.'})
                elif PROGRESS.search(assistant) or COMPLETION.search(assistant) or await self.is_busy(page):
                    job['research_started'] = True
                    job['phase'] = 'researching'
                    self.save(run_id, sid, job)
            result = await self.collect(page, provider, job)
            if result:
                current = digest(result['content'])
                stable = stable + 1 if current == last_hash else 1
                last_hash = current
                if stable >= 3:
                    (folder / 'report.md').write_text(result['content'])
                    (folder / 'report.md').chmod(0o600)
                    (folder / 'report.html').write_text(result['html'])
                    (folder / 'report.html').chmod(0o600)
                    job.update(phase='completed', url=result['url'], report_sha256=current,
                               finished_at=now())
                    self.save(run_id, sid, job)
                    return result
            await asyncio.sleep(self.poll_seconds)
        raise BrowserAttention('Web araştırması izleme süresi doldu. Konuşma adresi korundu; '
                               'devam edildiğinde aynı araştırma kontrol edilir.', 'interrupted')
