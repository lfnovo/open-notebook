const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const test=require('node:test');
const assert=require('node:assert/strict');
const script=fs.readFileSync(path.join(__dirname,'../../browser-extension/worker.js'),'utf8');
function setup(){
  const storage={}; const tabs=new Map();let creates=0,clicks=0;
  const noop={addListener(){}};
  const chrome={runtime:{id:'test',getURL:p=>'chrome-extension://test/'+p,onMessage:noop,onStartup:noop},alarms:{onAlarm:noop,create(){}},
    windows:{async create({tabId,focused}){assert.equal(focused,false);tabs.get(tabId).windowId=100+tabId;return {id:100+tabId};}},
    storage:{local:{async get(k){return {[k]:storage[k]};},async set(v){Object.assign(storage,v);},async remove(k){delete storage[k];}}},
    tabs:{async create({url}){const t={id:++creates,url};tabs.set(t.id,t);return t;},async get(id){if(!tabs.has(id))throw Error('gone');return tabs.get(id);},async remove(id){tabs.delete(id);}},
    scripting:{async executeScript(args){if(args.files)return [];clicks++;return [{frameId:0,result:{clicked:true}}];}}};
  function load(){
    const context=vm.createContext({chrome,URL,Date,Set,Map,Promise,Error,TextEncoder,console,setTimeout,setInterval,clearInterval});
    vm.runInContext(script+'\nglobalThis.executeTest=execute;',context);
    return context.executeTest;
  }
  return {execute:load(),restart:load,storage,tabs,counts:()=>({creates,clicks})};
}
function cmd(op,params={}){return {id:'a'.repeat(32),job:'probe:Gemini',provider:'Gemini',op,params,expires_at:Date.now()/1000+60};}
test('only provider URLs, exact job ownership, and no arbitrary operations',async()=>{
  const s=setup();
  await assert.rejects(s.execute(cmd('open',{url:'https://gemini.google.com.evil.example/'})));
  await assert.rejects(s.execute(cmd('eval')));
  await s.execute(cmd('open'));
  s.tabs.get(1).url='https://example.com/';
  await assert.rejects(s.execute(cmd('inspect')));
  assert.equal(s.counts().clicks,0);
});
test('submission is durable and never repeated even after a simulated worker restart',async()=>{
  const s=setup();await s.execute(cmd('open',{marker:'ON-test'}));
  await s.execute(cmd('submit'));
  assert.equal(s.storage['job:probe:Gemini'].submitAttempted,true);
  s.execute=s.restart();
  await assert.rejects(s.execute(cmd('submit')),e=>e.kind==='submission_uncertain');
  await assert.rejects(s.execute(cmd('fill',{text:'hello ON-test'})),e=>e.kind==='submission_uncertain');
  assert.equal(s.counts().clicks,1);
});
test('expired actions and missing submitted tab never cause a new submission',async()=>{
  const s=setup();await assert.rejects(s.execute({...cmd('open'),expires_at:1}));
  await s.execute(cmd('open',{marker:'ON-test'}));await s.execute(cmd('submit'));s.tabs.delete(1);
  await assert.rejects(s.execute(cmd('open')),e=>e.kind==='submission_uncertain');
  assert.equal(s.counts().creates,1);
});
test('blank and whitespace markers cannot write or submit, even before DOM checks',async()=>{
  for(const marker of ['', '   ']){
    const s=setup();await s.execute(cmd('open',{marker}));
    for(const op of ['fill','submit','start_plan']) await assert.rejects(s.execute(cmd(op,{text:'unrelated'})),e=>e.kind==='submission_uncertain');
    assert.equal(s.counts().clicks,0);
    assert.equal(s.storage['job:probe:Gemini'].submitAttempted,undefined);
  }
});
test('UTF-8 serialized command limits apply before UI and accept large ASCII packets',async()=>{
  const s=setup();await s.execute(cmd('open',{marker:'ON-test'}));
  await assert.rejects(s.execute(cmd('fill',{text:'ş'.repeat(500000)+' ON-test'})),e=>e.kind==='context_limit');
  assert.equal(s.counts().clicks,0);
  await s.execute(cmd('fill',{text:'a'.repeat(600000)+' ON-test'}));
  assert.equal(s.counts().clicks,1);
});
