'use strict';
const HOST = 'com.open_notebook.research';
const EXPECTED_EXTENSION_ID = 'diheppcpeakdedliglnjfgegpoakeanb';
const MAX_COMMAND_BYTES = 900000;
const SITES = {
  ChatGPT: {host:'chatgpt.com', url:'https://chatgpt.com/'},
  Gemini: {host:'gemini.google.com', url:'https://gemini.google.com/deepresearch?redirect=home'},
  Claude: {host:'claude.ai', url:'https://claude.ai/new'}
};
const OPS = new Set(['open','inspect','select_research','fill','submit','start_plan','collect','close','diagnose']);
let nativePort = null;
let heartbeatTimer = null;
let connectionError = '';
const queues = new Map();

function failure(message,kind='browser_changed') { return Object.assign(new Error(message),{kind}); }
function allowedUrl(url,provider) {
  try { const u=new URL(url); return u.protocol==='https:' && u.hostname===SITES[provider]?.host; }
  catch { return false; }
}
function validate(command) {
  if(!command || !/^[a-f0-9]{32}$/.test(command.id||'') || !OPS.has(command.op) || !SITES[command.provider]) throw failure('Geçersiz yerel görev.');
  if(!/^(?:[a-f0-9]{32}:[a-z_]+|connection:(?:ChatGPT|Gemini|Claude)|probe:(?:ChatGPT|Gemini|Claude))$/.test(command.job||'')) throw failure('Geçersiz görev kimliği.');
  if(!(command.expires_at*1000>Date.now())) throw failure('Görev teslim süresi doldu.','interrupted');
  if(new TextEncoder().encode(JSON.stringify(command)).length>MAX_COMMAND_BYTES) throw failure('Tam paket 900.000 UTF-8 bayt aktarım sınırını aşıyor; metin kesilmedi.','context_limit');
}
const sleep = ms => new Promise(resolve=>setTimeout(resolve,ms));
async function jobGet(key) { return (await chrome.storage.local.get('job:'+key))['job:'+key]; }
async function jobSet(key,value) { await chrome.storage.local.set({['job:'+key]:value}); }
async function ownedTab(command) {
  const job=await jobGet(command.job);
  if(!job || job.provider!==command.provider) throw failure('Bu göreve ait araştırma sekmesi bulunamadı.','browser_unavailable');
  let tab;
  try { tab=await chrome.tabs.get(job.tabId); } catch { throw failure('Araştırma sekmesi kapatılmış.','browser_unavailable'); }
  if(!allowedUrl(tab.url,command.provider)) throw failure('Araştırma sekmesi sağlayıcı dışına yönlendi; giriş gerekebilir.','login_required');
  return {job,tab};
}
async function taskWindow(tab,job) {
  if(job.windowId!==undefined&&job.windowId===tab.windowId)return job;
  // The provider must be an active tab to render research controls. Its own
  // unfocused window lets it render without selecting a tab in the user's window.
  const win=await chrome.windows.create({tabId:tab.id,focused:false,type:'normal',width:1100,height:820});
  return {...job,windowId:win.id};
}
async function dom(tabId,command,job) {
  // Recheck the host inside the injected function as navigation can race the tabs check.
  await chrome.scripting.executeScript({target:{tabId,allFrames:false},world:'ISOLATED',files:['dom-driver.js']});
  const results=await chrome.scripting.executeScript({target:{tabId,allFrames:false},world:'ISOLATED',
    func: value => globalThis.__openNotebookResearchDriver(value),
    args:[{op:command.op,provider:command.provider,params:command.params||{},marker:job.marker||'',expires_at:command.expires_at}]});
  const result=results.find(x=>x.frameId===0)?.result;
  if(!result) throw failure('Araştırma sayfasından yanıt alınamadı.');
  if(result.error) throw failure(result.error.message,result.error.kind);
  const state=result.state||result;
  if(command.provider==='ChatGPT'&&state.marker_present&&state.research_frame&&['inspect','diagnose','collect','start_plan'].includes(command.op)){
    await chrome.scripting.executeScript({target:{tabId,allFrames:true},world:'ISOLATED',files:['research-frame.js']});
    const frames=await chrome.scripting.executeScript({target:{tabId,allFrames:true},world:'ISOLATED',
      func:value=>globalThis.__openNotebookResearchFrame?.(value)||null,
      args:[{op:command.op,params:command.params||{},expires_at:command.expires_at}]});
    const app=frames.map(item=>item.result).find(item=>item?.frame)||null;
    if(command.op==='diagnose')result.researchApp=app;
    else if(app){
      for(const name of ['busy','research_progress','plan_visible','quota_visible','research_complete'])result[name]=!!app[name]||!!result[name];
      if(app.report)result.report=app.report;
      if(app.clicked)result.clicked=true;
    }
  }
  return result;
}
async function execute(command) {
  validate(command);
  const params=command.params||{};
  if(command.op==='open') {
    let previous=await jobGet(command.job);
    if(previous && previous.provider!==command.provider) throw failure('Görev sağlayıcısı değiştirilemez.');
    if(previous) {
      try {
        const tab=await chrome.tabs.get(previous.tabId);
        if(!allowedUrl(tab.url,command.provider)) throw failure('Araştırma sekmesi başka bir adreste; otomatik yönlendirilmedi.','login_required');
        previous=await taskWindow(tab,previous);await jobSet(command.job,previous);
        return {url:tab.url,tab_id:tab.id,reused:true};
      } catch(error) {
        if(error.kind) throw error;
        if(previous.submitAttempted && !params.url) throw failure('Gönderilmiş işin sekmesi kapalı ve konuşma adresi bilinmiyor.','submission_uncertain');
      }
    }
    const url=params.url||SITES[command.provider].url;
    if(!allowedUrl(url,command.provider)) throw failure('İzin verilmeyen araştırma adresi.');
    const tab=await chrome.tabs.create({url,active:false});
    const job=await taskWindow(tab,{...previous,tabId:tab.id,provider:command.provider,createdAt:Date.now(),marker:params.marker||previous?.marker||''});
    await jobSet(command.job,job);
    // tabs.create returns before the first navigation, sometimes with an empty URL.
    for(let i=0;i<100;i++){
      const current=await chrome.tabs.get(tab.id);
      if(allowedUrl(current.url,command.provider))break;
      if(current.url&&current.url!=='about:blank'&&!allowedUrl(current.pendingUrl,command.provider))break;
      await sleep(200);
    }
    return {url,tab_id:tab.id,reused:false};
  }
  const {job,tab}=await ownedTab(command);
  if(['fill','submit','start_plan'].includes(command.op) && (typeof job.marker!=='string'||!job.marker.trim())) throw failure('Görev işareti boş; metin yazma ve gönderme engellendi.','submission_uncertain');
  if(command.op==='close') {
    // Only this extension's task tab, never the whole browser or other user tabs.
    await chrome.tabs.remove(tab.id); await chrome.storage.local.remove('job:'+command.job);
    return {closed:true};
  }
  if(command.op==='fill') {
    if(job.submitAttempted) throw failure('Gönderim denenen işe tekrar metin yazılmaz.','submission_uncertain');
    if(typeof params.text!=='string') throw failure('Tam görev paketi geçersiz.');
    // An empty marker makes includes() vacuously true and silently drops this guarantee.
    // The page driver also refuses it; this keeps the worker from forwarding it at all.
    if(!job.marker || !job.marker.trim()) throw failure('Görev kimliği olmayan işe metin yazılmaz.');
    if(!params.text.includes(job.marker)) throw failure('Görev paketi bu işin kimliğini taşımıyor.');
  }
  if(command.op==='submit') {
    if(job.submitAttempted) throw failure('Bu görev için gönderim zaten denendi; otomatik tekrar engellendi.','submission_uncertain');
    // Persist BEFORE the DOM click. Ambiguous failures remain stopped across restarts.
    await jobSet(command.job,{...job,submitAttempted:true,submitAttemptedAt:Date.now()});
  }
  return await dom(tab.id,command,job);
}
function connect() {
  if(nativePort) return;
  if(chrome.runtime.id!==EXPECTED_EXTENSION_ID){connectionError='Eklenti kimliği yerel kurulumla eşleşmiyor. Kurulu eklenti klasörünü taşımayın; yerel host kaydını kontrol edin.';return;}
  connectionError='';
  nativePort=chrome.runtime.connectNative(HOST);
  const port=nativePort;
  const beat=()=>{try{port.postMessage({type:'heartbeat'});}catch{}};
  beat(); heartbeatTimer=setInterval(beat,15000);
  port.onMessage.addListener(command=>{
    const key=command?.job||'invalid';
    const task=(queues.get(key)||Promise.resolve()).catch(()=>{}).then(async()=>{
      let message;
      try { message={id:command.id,result:await execute(command)}; }
      catch(error) { message={id:command?.id,error:{kind:error.kind||'browser_changed',message:error.kind?error.message:'Chrome işlemi tamamlanamadı; sayfa veya eklenti izni değişmiş olabilir.'}}; }
      try{port.postMessage(message);}catch{}
    });
    queues.set(key,task);
    task.finally(()=>{if(queues.get(key)===task) queues.delete(key);});
  });
  port.onDisconnect.addListener(()=>{
    connectionError=chrome.runtime.lastError?.message||'Yerel bağlantı kapandı.';
    clearInterval(heartbeatTimer);heartbeatTimer=null;
    if(nativePort===port) nativePort=null;
  });
}
chrome.runtime.onMessage.addListener((message,sender,reply)=>{
  // Only our own popup can start/stop the native connection; no website messages.
  if(sender.id!==chrome.runtime.id || sender.url!==chrome.runtime.getURL('popup.html')) return false;
  (async()=>{
    if(message.action==='connect') { await chrome.storage.local.set({enabled:true});connect();await sleep(300); }
    if(message.action==='disconnect') { await chrome.storage.local.set({enabled:false});nativePort?.disconnect(); }
    reply({connected:!!nativePort,error:connectionError});
  })().catch(()=>reply({connected:false,error:'Yerel bağlantı başlatılamadı.'}));
  return true;
});
chrome.runtime.onStartup.addListener(async()=>{if((await chrome.storage.local.get('enabled')).enabled) connect();});
chrome.alarms.onAlarm.addListener(async alarm=>{if(alarm.name==='research-reconnect' && (await chrome.storage.local.get('enabled')).enabled) connect();});
chrome.alarms.create('research-reconnect',{periodInMinutes:1});
chrome.storage.local.get('enabled').then(value=>{if(value.enabled) connect();});
