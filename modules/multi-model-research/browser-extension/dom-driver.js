/* Fixed DOM operations in the extension's isolated world; no eval or page API calls. */
globalThis.__openNotebookResearchDriver = async function(command) {
  'use strict';
  const specs={
    ChatGPT:{host:'chatgpt.com',editor:'#prompt-textarea[contenteditable="true"],textarea#prompt-textarea',assistant:'[data-message-author-role="assistant"]',user:'[data-message-author-role="user"]',menus:['Add files and more','Add files and tools','Tools','Dosya ve daha fazlasını ekle','Dosya ve araç ekle','Araçlar']},
    Gemini:{host:'gemini.google.com',editor:'.ql-editor[contenteditable="true"],rich-textarea [contenteditable="true"]',assistant:'deep-research-report,[data-test-id="deep-research-report"],.research-report,.canvas-content,model-response',user:'user-query,[data-test-id="user-query"]',menus:['Yükleme ve araçlar','Upload & tools','Add files','Tools','Dosya ekle','Araçlar']},
    Claude:{host:'claude.ai',editor:'[contenteditable="true"].ProseMirror,[contenteditable="true"][role="textbox"]',assistant:'[data-testid="assistant-message"],.font-claude-response',user:'[data-testid="user-message"]',menus:['Add files, connectors, and more','Search and tools','Search & tools','Open tools menu','Araçlar']}
  };
  const spec=specs[command.provider];
  const fail=(message,kind='browser_changed')=>{throw Object.assign(new Error(message),{kind});};
  const visible=el=>{
    if(!el?.getClientRects().length) return false;
    for(let p=el;p;p=p.parentElement){const s=getComputedStyle(p);if(s.display==='none'||s.visibility==='hidden'||s.visibility==='collapse'||Number(s.opacity)===0)return false;}
    return true;
  };
  const text=el=>(el?.innerText||el?.textContent||'').trim();
  const normalize=value=>(value||'').replace(/\s+/g,' ').trim();
  const label=el=>{
    const references=(el.getAttribute('aria-labelledby')||'').split(/\s+/).filter(Boolean).map(id=>text(document.getElementById(id))).join(' ');
    const clone=el.cloneNode(true);clone.querySelectorAll('[aria-hidden="true"],svg').forEach(node=>node.remove());
    return (el.getAttribute('aria-label')||references||el.getAttribute('title')||text(clone)).replace(/[\uE000-\uF8FF]/g,'').replace(/\s+/g,' ').trim();
  };
  const controls=()=>[...document.querySelectorAll('button,a,[role="button"],[role="menuitem"],[role="menuitemradio"],[role="menuitemcheckbox"],[role="option"],[role="switch"],[role="checkbox"]')].filter(visible);
  const enabled=el=>!!el&&!el.disabled&&el.getAttribute('aria-disabled')!=='true';
  const editor=()=>[...document.querySelectorAll(spec.editor)].find(visible);
  const findControl=names=>controls().find(el=>names.includes(label(el))&&enabled(el));
  const researchNames=['Deep research','Deep Research','Derin araştırma','Derin Araştırma','Research','Araştırma','Research mode'];
  const wait=async ms=>{await new Promise(resolve=>setTimeout(resolve,ms));if(command.expires_at*1000<=Date.now())fail('Sayfa işlemi teslim süresini aştı; gönderim yapılmadı.','interrupted');};
  const openMenu=el=>{
    if(el.getAttribute('aria-expanded')==='true')return;
    if(command.provider==='ChatGPT'){
      el.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true,button:0,pointerType:'mouse',isPrimary:true}));
      el.dispatchEvent(new PointerEvent('pointerup',{bubbles:true,button:0,pointerType:'mouse',isPrimary:true}));
    }
    el.click();
  };
  const composerRoot=()=>{
    const ed=editor();
    return ed?.closest('input-container,fieldset,form')||ed?.parentElement?.parentElement?.parentElement||ed?.parentElement;
  };
  const settleToolAnimations=()=>{
    // Covered Chrome windows can pause short entrance fades. Finish only finite
    // animations in the task composer / Gemini research surface. Static hidden
    // elements and infinite activity spinners remain hidden / active.
    const roots=new Set([composerRoot()]);
    if(command.provider==='Gemini'){
      document.querySelectorAll('.ng-animating,input-container,deep-research-immersive-panel').forEach(el=>roots.add(el));
    }
    for(const root of roots){
      for(const animation of root?.getAnimations({subtree:true})||[]){
        const timing=animation.effect?.getComputedTiming();
        if(timing&&Number.isFinite(timing.endTime)&&timing.endTime<=2000&&animation.playState!=='finished'){
          try{animation.finish();}catch{}
        }
      }
    }
  };
  const attachmentVisible=()=>{
    const root=composerRoot();
    if(!root||root.querySelector('[aria-busy="true"],[role="progressbar"]'))return false;
    return [...root.querySelectorAll('[title],[aria-label],span,div,p,button')].some(el=>{
      if(!visible(el)||el.closest(spec.assistant+','+spec.user+',nav,aside'))return false;
      // Card titles / accessible names survive filename wrapping and nested spans.
      const name=el.getAttribute('title')||el.getAttribute('aria-label')||(el.children.length===0?text(el):'');
      return /^input-packet(?:\.md)?$/i.test(name.trim());
    });
  };
  const modeSelected=()=>{
    const matches=controls().filter(el=>researchNames.includes(label(el)));
    for(const el of matches){
      const flags=['aria-pressed','aria-checked','aria-selected'].map(a=>el.getAttribute(a));
      const ds=el.getAttribute('data-state');
      if(flags.includes('false')||['off','inactive','unchecked'].includes(ds)) continue;
      if(flags.includes('true')||['on','active','checked','selected'].includes(ds)) return true;
    }
    if(matches.some(el=>['aria-pressed','aria-checked','aria-selected'].some(a=>el.getAttribute(a)==='false')||['off','inactive','unchecked'].includes(el.getAttribute('data-state'))))return false;
    if(command.provider==='Gemini')return controls().some(el=>/^(?:(?:Remove|Deselect|Unselect) Deep Research|Deep Research öğesinin seçimini kaldır)$/i.test(label(el)));
    if(command.provider==='ChatGPT'){
      const tabs=[...document.querySelectorAll('[role="tablist"]')].find(el=>visible(el)&&/deep research/i.test(el.getAttribute('aria-label')||''));
      const chip=editor()&&[...editor().querySelectorAll('[contenteditable="false"]')].some(el=>visible(el)&&/^deep research$/i.test(text(el)));
      return !!tabs&&!!chip;
    }
    return false;
  };
  const sendControl=()=>{
    const selectors='button[data-testid="send-button"],button[aria-label="Send prompt"],button[aria-label="Send Message"],button[aria-label="Send message"],button[aria-label="Submit"],button[aria-label="Gönder"],button[type="submit"]';
    return [...document.querySelectorAll(selectors)].find(el=>visible(el)&&enabled(el))||findControl(['Send','Send prompt','Send message','Submit','Gönder','Mesaj gönder','İleti gönder']);
  };
  const busy=()=>!![...document.querySelectorAll('button[data-testid="stop-button"],button[aria-label*="Stop"],button[aria-label*="Durdur"],button[aria-label*="durdur"]')].find(visible);
  const assistantRoots=()=>{
    const panel=command.provider==='Gemini'&&[...document.querySelectorAll('deep-research-immersive-panel')].find(visible);
    if(panel)return [panel];
    const roots=[...document.querySelectorAll(spec.assistant)].filter(visible);
    return roots.filter(el=>!roots.some(other=>other!==el&&other.contains(el)));
  };
  const assistantText=()=>assistantRoots().map(text).join('\n');
  const progressRegex=/(researching|conducting research|gathering sources|reading sources|araştırılıyor|araştırma yapılıyor|kaynaklar inceleniyor)/i;
  const completeRegex=/(research (?:is )?(?:complete|completed|finished)|completed (?:the |your )?research|araştırma tamamlandı|araştırmayı tamamladım|araştırma bitti|researched .{0,40} sources|kaynak incelendi)/i;
  const planControl=()=>findControl(['Start research','Start researching','Begin research','Araştırmayı başlat','Araştırmayı başlatın','Araştırmaya başla']);
  function inspect(){
    const signIn=controls().some(el=>/^(log in|login|sign in|sign up|giriş yap|oturum aç|kaydol|üye ol)$/i.test(label(el)));
    const notices=[...document.querySelectorAll('h1,h2,[role="alert"],[role="dialog"]')].filter(visible).map(text).join('\n');
    const challenge=/just a moment|verify you are human|security verification|checking your browser|bir dakika/i.test(document.title)||/verify you are human|performing security verification|insan olduğunuzu doğrulayın|güvenlik doğrulaması yapılıyor/i.test(notices);
    // Quota notices also live inside tool menus/popovers, not just alerts.
    // Never inspect report bodies: their prose may mention quotas as evidence.
    const quotaText=notices+'\n'+[...document.querySelectorAll('[role="menu"],[role="tooltip"],[data-radix-popper-content-wrapper]')].filter(visible).map(text).join('\n');
    const quota=/usage limit reached|limitine ulaştın|limitinize ulaştınız|research limit|araştırma sınırına|out of research|no research left|you(?:’|')ve (?:used|reached).{0,50}(?:research|limit)|0 (?:deep research|research|araştırma).{0,20}(?:remaining|left|kaldı)|araştırma.{0,35}(?:hakkınız kalmadı|kotası doldu|limit.{0,15}ulaşt)/i.test(quotaText);
    const assistant=assistantText();
    const complete=completeRegex.test(assistant)||(command.provider==='Gemini'&&!![...document.querySelectorAll('deep-research-immersive-panel')].find(el=>visible(el)&&el.querySelector('deep-research-source-lists'))&&!!findControl(['Paylaş ve dışa aktar','Share & export','Share and export']));
    const user=[...document.querySelectorAll(spec.user)].filter(visible).map(text).join('\n');
    return {driver_version:'2026-09-24-background-readiness',url:location.href,sign_in_visible:signIn,challenge_visible:challenge,quota_visible:quota,
      research_frame:!!document.querySelector('iframe[src^="https://connector-openai-deep-research.web-sandbox.oaiusercontent.com"]'),composer_visible:!!editor(),tools_ready:!!findControl(spec.menus)||modeSelected(),research_selected:modeSelected(),send_ready:!!sendControl(),busy:busy(),
      marker_present:!!command.marker&&user.includes(command.marker),plan_visible:!complete&&!!planControl(),
      research_progress:progressRegex.test(assistant)||controls().some(el=>/sources and counting.*Open research panel/i.test(label(el))),research_complete:complete,
      assistant_chars:assistant.length};
  }
  const assertReady=()=>{
    const state=inspect();
    if(state.challenge_visible)fail('Sağlayıcı güvenlik doğrulaması bekliyor. Bu görev sekmesinde doğrulamayı tamamlayın.','verification_required');
    if(state.sign_in_visible||/\/(?:signin|login|auth\/login)(?:\/|$)/.test(location.pathname))fail('Bu Chrome profilinde sağlayıcı hesabına giriş gerekli.','login_required');
    if(state.quota_visible)fail('Sağlayıcının araştırma kotası doldu.','quota_wait');
    return state;
  };
  try{
    if(!spec||location.protocol!=='https:'||location.hostname!==spec.host)fail('İzin verilmeyen sağlayıcı sayfası.','login_required');
    if(!(command.expires_at*1000>Date.now()))fail('Görev süresi doldu.','interrupted');
    settleToolAnimations();
    if(command.op==='inspect')return inspect();
    if(command.op==='diagnose'){
      const ed=editor();
      const candidates=[...document.querySelectorAll('button,span,div')].filter(el=>el.children.length===0&&/^(Deep research|Deep Research|Research|Derin araştırma|Araştırmayı başlatın|Araştırmayı başlat|Start research)$/.test(text(el))).slice(0,15).map(el=>({tag:el.tagName,visible:visible(el),classes:el.className,hiddenBy:(()=>{const out=[];for(let n=el;n;n=n.parentElement){const s=getComputedStyle(n);if(s.display==='none'||s.visibility==='hidden'||s.opacity==='0')out.push({tag:n.tagName,classes:n.className,display:s.display,visibility:s.visibility,opacity:s.opacity});}return out;})(),parent:el.parentElement?.outerHTML.slice(0,1800)}));
      return {state:inspect(),uploadInputs:[...document.querySelectorAll('input[type=file]')].map(el=>({accept:el.accept,files:[...el.files].map(f=>({name:f.name,size:f.size})),id:el.id})),attachmentLabels:[...document.querySelectorAll('button,span,p,div')].filter(el=>el.children.length===0&&/input-packet/i.test(text(el))).slice(0,12).map(el=>({text:text(el).slice(0,100),visible:visible(el),parent:el.parentElement?.outerHTML.slice(0,1600)})),researchElements:[...document.querySelectorAll('*')].filter(el=>/research/i.test(el.tagName)).slice(0,12).map(el=>({tag:el.tagName,visible:visible(el),text:text(el).slice(0,800)})),pageNotice:{title:document.title,headings:[...document.querySelectorAll('h1,h2,[role=alert]')].map(text).slice(0,15),mainTail:inspect().marker_present?text(document.querySelector('main')||document.querySelector('[role=main]')).slice(-1200):null},frames:[...document.querySelectorAll('iframe')].map(x=>({title:x.title,src:x.getAttribute('src')?.slice(0,200)})),rawAssistant:inspect().marker_present?assistantRoots().map(x=>(x.textContent||'').trim()).join('\n').slice(-3000):null,taskSurface:inspect().marker_present?text(document.querySelector('main')||document.querySelector('[role=main]')).slice(-4500):null,responsePreview:inspect().marker_present?{start:assistantText().slice(0,700),end:assistantText().slice(-700)}:null,visibility:document.visibilityState,candidates,composerControls:[...(ed?.closest('input-container,fieldset,form')||ed?.parentElement?.parentElement?.parentElement||document.createElement('div')).querySelectorAll('button')].slice(0,20).map(el=>({label:label(el).slice(0,100),visible:visible(el),disabled:!enabled(el),classes:el.className,hiddenBy:(()=>{const out=[];for(let n=el;n;n=n.parentElement){const s=getComputedStyle(n);if(s.display==='none'||s.visibility==='hidden'||s.opacity==='0')out.push({tag:n.tagName,classes:n.className,display:s.display,visibility:s.visibility,opacity:s.opacity});}return out;})()})),controls:controls().filter(el=>/research|araştır|araç|tools|send|gönder|sources|kaynak|export|report|add files|dosya/i.test(label(el))).slice(0,40).map(el=>({tag:el.tagName,label:label(el).slice(0,140),role:el.getAttribute('role'),pressed:el.getAttribute('aria-pressed'),checked:el.getAttribute('aria-checked'),state:el.getAttribute('data-state'),testid:el.getAttribute('data-testid')})),editor:ed?{tag:ed.tagName,id:ed.id,role:ed.getAttribute('role'),length:(ed.value||text(ed)).length,markerInEditor:!!command.marker&&(ed.value||text(ed)).includes(command.marker),normalizedFullMatch:!!command.params.expected&&(ed.value||text(ed)).replace(/\s+/g,' ').includes(command.params.expected.replace(/\s+/g,' ')),draftChars:(()=>{const c=ed.cloneNode(true);c.querySelectorAll('[contenteditable="false"]').forEach(x=>x.remove());return text(c).length;})(),noneditable:[...ed.querySelectorAll('[contenteditable="false"]')].map(el=>({tag:el.tagName,text:/^deep research$/i.test(text(el))?text(el):'[other]',type:el.getAttribute('data-type')}))}:null};
    }
    assertReady();
    if(command.op==='select_research'){
      settleToolAnimations();await wait(50);
      if(command.provider==='ChatGPT'){
        const chat=[...document.querySelectorAll('[role="radio"]')].find(el=>visible(el)&&label(el)==='Chat');
        if(chat&&chat.getAttribute('aria-checked')==='false'){chat.click();await wait(700);}
      }
      if(modeSelected())return inspect();
      const menu=findControl(spec.menus);
      if(menu){openMenu(menu);await wait(450);}
      let option=findControl(researchNames);
      if(!option&&command.provider==='ChatGPT'){
        // Current ChatGPT tools use text nodes in selectable container rows.
        const candidates=[...document.querySelectorAll('[role="menu"] *,[cmdk-item] *,[data-radix-popper-content-wrapper] *,[class*="popover"] *,[class*="dropdown"] *')];
        option=candidates.find(el=>visible(el)&&el.children.length===0&&/^(Deep research|Deep Research|Derin araştırma)$/.test(text(el)));
      }
      assertReady();
      if(!option)fail('Gerçek araştırma modu bu sayfada bulunamadı. Normal sohbet gönderilmedi.','research_unavailable');
      option.click();await wait(700);
      if(!modeSelected())fail('Araştırma modunun seçimi doğrulanamadı; soru gönderilmedi.');
      return inspect();
    }
    if(command.op==='fill'){
      settleToolAnimations();await wait(50);
      if(!modeSelected())fail('Araştırma modu seçili değil; metin yazılmadı.');
      const full=command.params.text;
      if(typeof full!=='string'||new TextEncoder().encode(full).length>900000||!command.marker?.trim()||!full.includes(command.marker))fail('Tam görev paketi geçersiz veya UTF-8 bayt sınırını aşıyor.');
      let ed=editor();if(!ed)fail('İstem yazma alanı bulunamadı.');
      const short='Ekli input-packet.md dosyasındaki görevi ve önceki raporların tamamını kullan. Dosyayı tamamen inceleyerek seçili araştırma modunda çalış. Soru sorma; makul varsayımları belirt. Görev kimliği: '+command.marker;
      const input=full.length>18000?short:full;
      if(normalize(ed.value||text(ed)).endsWith(normalize(input))){
        if(full.length>18000&&!attachmentVisible())fail('Görev metni var ancak tam paket dosyası doğrulanamadı.');
        return {...inspect(),prepared:true};
      }
      const draft=ed.cloneNode(true);
      draft.querySelectorAll('[contenteditable="false"][data-id="plugin:connector_openai_deep_research"],[contenteditable="false"]').forEach(node=>{if(/^deep research$/i.test(text(node)))node.remove();});
      if(text(draft)&&!/^deep research$/i.test(text(draft)))fail('Görev sekmesindeki mevcut taslak değiştirilmedi.');
      if(full.length>18000&&!attachmentVisible()){
        if(globalThis.__openNotebookPendingPacket===command.marker)return {...inspect(),prepared:false,pending_upload:true};
        let upload=document.querySelector('input[type="file"]');
        if(!upload){const menu=findControl(spec.menus);if(menu){menu.click();await wait(250);}upload=document.querySelector('input[type="file"]');}
        if(!upload)fail('Tam paket için dosya yükleme alanı bulunamadı; metin kesilmedi.');
        const dt=new DataTransfer();dt.items.add(new File([full],'input-packet.md',{type:'text/markdown'}));
        globalThis.__openNotebookPendingPacket=command.marker;
        upload.files=dt.files;upload.dispatchEvent(new Event('change',{bubbles:true}));
        // Poll from the local service, never wait in a hidden page timer: Chrome
        // can throttle those timers to a minute and strand the command queue.
        return {...inspect(),prepared:false,pending_upload:true};
      }
      ed=editor();ed.focus();
      if(ed.tagName==='TEXTAREA'||ed.tagName==='INPUT'){
        const proto=ed.tagName==='TEXTAREA'?HTMLTextAreaElement.prototype:HTMLInputElement.prototype;
        Object.getOwnPropertyDescriptor(proto,'value').set.call(ed,input);
        ed.dispatchEvent(new InputEvent('input',{bubbles:true,inputType:'insertText',data:input}));
      }else{
        // Append after an existing provider-owned research chip; never erase it.
        const range=document.createRange();range.selectNodeContents(ed);range.collapse(false);
        const selection=getSelection();selection.removeAllRanges();selection.addRange(range);
        if(!document.execCommand('insertText',false,input))fail('İstem editörü metni kabul etmedi.');
      }
      await wait(250);settleToolAnimations();
      // Rich text editors render paragraph boundaries as different newline counts.
      // Compare every non-whitespace character while retaining the exact input file.
      if(!normalize(ed.value||text(ed)).includes(normalize(input)))fail('Tam istem metni editörde doğrulanamadı.');
      if(!modeSelected())fail('Metin yazıldıktan sonra araştırma seçimi kayboldu; gönderilmedi.');
      const attachmentReady=full.length<=18000||attachmentVisible();
      if(!attachmentReady)fail('Tam paket dosyasının yüklenmesi doğrulanamadı; gönderilmedi.');
      return {...inspect(),prepared:true};
    }
    if(command.op==='submit'){
      if(!modeSelected())fail('Gönderim öncesinde araştırma seçimi doğrulanamadı.');
      if(!command.marker||!(editor()?.value||text(editor())).includes(command.marker))fail('Gönderilecek istem görev kimliğiyle eşleşmiyor.');
      const send=sendControl();if(!send)fail('Gönderme düğmesi hazır değil.');
      send.click();return {url:location.href,clicked:true};
    }
    if(command.op==='start_plan'){
      if(!command.marker||![...document.querySelectorAll(spec.user)].filter(visible).some(el=>text(el).includes(command.marker)))fail('Araştırma planı görev kimliğiyle eşleştirilemedi.','submission_uncertain');
      const state=inspect();
      if(state.research_complete||state.busy)return {...state,clicked:false};
      const plan=planControl();if(!plan)return {...state,clicked:false};
      plan.click();return {url:location.href,clicked:true};
    }
    if(command.op==='collect'){
      settleToolAnimations();await wait(50);
      const state=inspect();
      if(!state.marker_present||state.busy)return {...state,report:null};
      const roots=assistantRoots();const last=roots.at(-1);
      if(!last||text(last).length<1200)return {...state,report:null};
      const exportVisible=!!findControl(['Share & export','Share and export','Paylaş ve dışa aktar','Export report','Download report','Raporu indir','Open report','Raporu aç']);
      if(!state.research_complete&&!(command.params.research_started&&exportVisible))return {...state,report:null};
      const clone=last.cloneNode(true);clone.querySelectorAll('script,style,button,svg,nav,input,textarea').forEach(el=>el.remove());
      const links=[...last.querySelectorAll('a[href]')].map(a=>({title:text(a),url:a.href})).filter(x=>{
        try{const u=new URL(x.url);return ['http:','https:'].includes(u.protocol)&&u.hostname!==spec.host;}catch{return false;}
      });
      return {...state,report:{html:clone.innerHTML,text:text(last),links,completion:{explicit:state.research_complete,export_visible:exportVisible}}};
    }
    fail('Bilinmeyen DOM işlemi.');
  }catch(error){return {error:{kind:error.kind||'browser_changed',message:error.kind?error.message:'Araştırma sayfası beklenen işlemi desteklemiyor.'}};}
};
void 0;
