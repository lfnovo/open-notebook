'use strict';
const allowedHosts = new Set(['chatgpt.com', 'gemini.google.com', 'claude.ai']);
const button = document.getElementById('check');
const status = document.getElementById('status');
const result = document.getElementById('result');
document.getElementById('close').addEventListener('click', () => window.close());
async function connection(action) {
  const el=document.getElementById('connection');
  try {
    const value=await chrome.runtime.sendMessage({action});
    el.textContent=value?.connected?'Yerel bağlantı açık.':('Yerel bağlantı kapalı.'+(value?.error?' '+value.error:''));
  } catch { el.textContent='Yerel bağlantı hazır değil. Eklentiyi yeniden yükleyin.'; }
}
document.getElementById('connect').addEventListener('click',()=>connection('connect'));
document.getElementById('disconnect').addEventListener('click',()=>connection('disconnect'));
connection('status');
button.addEventListener('click', async () => {
  button.disabled = true;
  result.hidden = true;
  status.textContent = 'Seçili sekme kontrol ediliyor…';
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    const url = new URL(tab?.url || 'about:blank');
    if (url.protocol !== 'https:' || !allowedHosts.has(url.hostname)) {
      status.textContent = 'ChatGPT, Gemini veya Claude sayfasını açıp tekrar kontrol et. Giriş ve diğer web sayfalarında çalışmaz.';
      return;
    }
    const entries = await chrome.scripting.executeScript({
      target: { tabId: tab.id, allFrames: false },
      files: ['inspect-page.js'],
      world: 'ISOLATED'
    });
    const data = entries.find(entry => entry.frameId === 0)?.result;
    if (!data || data.error) throw new Error('not_readable');
    result.textContent = JSON.stringify(data, null, 2);
    result.hidden = false;
    if (data.security_challenge_visible) status.textContent = 'Güvenlik doğrulaması görünüyor. Kontrol burada durdu.';
    else if (data.sign_in_control_visible) status.textContent = 'Giriş seçeneği görünüyor; oturum açık kabul edilmedi.';
    else if (data.composer_visible) status.textContent = 'Yazma alanı okunabiliyor. Giriş ve gerçek araştırma erişimi ayrıca doğrulanmalı.';
    else status.textContent = 'Sayfa okunabildi; hazır sohbet alanı henüz doğrulanamadı.';
  } catch (_) {
    status.textContent = 'Bu sekme okunamadı. Sayfa yenilenmiş veya sekme izni sona ermiş olabilir. Sağlayıcı sayfasında tekrar dene.';
  } finally {
    button.disabled = false;
  }
});
