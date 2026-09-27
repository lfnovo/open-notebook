/* Only ChatGPT's own Deep Research app frame, never login/security frames. */
if(location.origin==='https://connector-openai-deep-research.web-sandbox.oaiusercontent.com'){
  globalThis.__openNotebookResearchFrame=async function(command){
    if(!(command.expires_at*1000>Date.now()))return {error:{kind:'interrupted',message:'Görev süresi doldu.'}};
    let doc=document;const nested=document.querySelector('iframe');
    try{if(nested?.contentDocument?.body)doc=nested.contentDocument;}catch{}
    const visible=el=>{if(!el?.getClientRects().length)return false;for(let n=el;n;n=n.parentElement){const s=getComputedStyle(n);if(s.display==='none'||s.visibility==='hidden'||s.opacity==='0')return false;}return true;};
    const text=el=>(el?.innerText||el?.textContent||'').trim();
    const label=el=>(el.getAttribute('aria-label')||text(el)).trim();
    const controls=[...doc.querySelectorAll('button,a,[role=button]')].filter(visible);
    const find=names=>controls.find(el=>names.includes(label(el))&&!el.disabled&&el.getAttribute('aria-disabled')!=='true');
    const stop=find(['Stop research','Araştırmayı durdur']);
    const start=find(['Start research','Begin research','Araştırmayı başlat']);
    const body=text(doc.body);
    const quota=/out of research|research limit reached|no research left|araştırma sınırına ulaştınız/i.test(body);
    const exportButton=find(['Export','Dışa aktar']);
    const expand=find(['Expand','Genişlet']);
    const report=controls.find(el=>el.tagName==='DIV'&&el.getAttribute('role')==='button'&&text(el).length>1200&&el.querySelector('h1,h2'));
    const completed=!!exportButton&&!!expand&&!!report&&!stop&&!start;
    const state={frame:true,busy:!!stop,research_progress:!!stop,plan_visible:!!start,quota_visible:quota,research_complete:completed,report:null};
    if(command.op==='diagnose')return {...state,text:body.slice(-8000),controls:controls.map(el=>({tag:el.tagName,label:label(el).slice(0,180),disabled:!!el.disabled,href:el.tagName==='A'?el.href:undefined}))};
    if(command.op==='start_plan'&&start){start.click();return {...state,clicked:true};}
    if(command.op==='collect'&&completed){
      const clone=report.cloneNode(true);clone.querySelectorAll('script,style,button,svg,nav,input,textarea').forEach(el=>el.remove());
      const links=[...report.querySelectorAll('a[href]')].map(a=>({title:text(a),url:a.href})).filter(a=>/^https?:\/\//.test(a.url));
      state.report={html:clone.innerHTML,text:text(report),links,completion:{provider:'chatgpt_deep_research_app',export_visible:true,expand_visible:true}};
    }
    return state;
  };
}
void 0;
