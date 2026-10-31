"""One-time source migration kept with this release for review."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/'static/app.js';s=p.read_text('utf-8')
if "from './live-mixer.mjs'" in s:raise SystemExit('Live mixer already installed; no files changed.')
s=s.replace("'use strict';", "import {LiveMixer,SECTION_COLOURS,exportBody} from './live-mixer.mjs';\n'use strict';")
s=s.replace("const audio=$('audio');", "const audio=new LiveMixer();")
s=s.replace("let instrumentOverrides=", "let generationToken=0,activeJob=null,exporting=false,stemsReady=false,liveRevision=0,waveSerial=0,waveTimer=null,waveRunning=false,cachedLive=null,sectionLevels={};\nconst trackTimers=new Map(),trackPromises=new Map();\nlet instrumentOverrides=")
def replace_function(name,next_name,body):
 global s
 a=s.index('function '+name+'(');b=s.index('function '+next_name+'(',a)
 if s[a-6:a]=='async ':a-=6
 if s[b-6:b]=='async ':b-=6
 s=s[:a]+body+'\n'+s[b:]
replace_function('markDirty','duration',r'''function markDirty(kind='composition'){
 dirty=true;
 if(kind==='audio'&&current){
  liveRevision++;cachedLive=null;audio.setMix(mixOverrides,toneOverrides);audio.setLevels(sectionLevels);
  $('mix-status').textContent='Živý mix · změny slyšíš při přehrávání.';
  $('apply').textContent='Připravit export';$('apply').disabled=busy||exporting;
  clearTimeout(waveTimer);waveTimer=setTimeout(refreshLiveWave,650);
  try{localStorage.setItem('music-forge-live',JSON.stringify({project,settings:liveSettings()}));}catch{}
 }else{$('mix-status').textContent=current?'Zadání pro příští skladbu se změnilo.':'Nastav skladbu a spusť tvorbu.';}
}''')
replace_function('updateMoodChips','moodChanged',r'''function updateMoodChips(){
 $('mood-chips').innerHTML=['happy','sad','energetic','dark'].map(id=>{const m=catalog.moods.find(x=>x.id===id);return `<button class="mood-chip ${$('mood').value===id?'selected':''}" data-mood="${id}">${esc(m.name)}</button>`;}).join('');
}''')
replace_function('setBusy','generate',r'''function setBusy(value){
 busy=value;for(const id of ['generate','generate-top','preview','load','reset'])$(id).disabled=value||exporting;
 for(const id of ['new-melody','new-sounds'])$(id).disabled=value||exporting||!current;
 $('apply').disabled=value||exporting||!current||!dirty;
 $('progress-box').hidden=!value&&!exporting;$('cancel').disabled=exporting;
 document.querySelectorAll('#mixer input,#mixer select,#mixer button').forEach(x=>x.disabled=(value&&!exporting)||!stemsReady);
 for(const id of ['wav','opus','wav-top','opus-top'])$(id).classList.toggle('disabled',!current||value||exporting);
}''')
replace_function('generate','loadResult',r'''async function waitJob(job,token){
 let status;
 while(true){await new Promise(r=>setTimeout(r,250));status=await api('/api/status?job='+job);if(token!==generationToken)return null;
  $('progress').value=status.progress;$('progress-text').textContent=status.message;$('cancel').disabled=exporting||Boolean(status.committing);if(status.state!=='running')return status;}
}
async function generate(kind='new'){
 if(busy||exporting)return;
 const token=++generationToken;setBusy(true);activeJob=null;
 try{
  const settings=getSettings();if(!Number.isFinite(settings.bpm)||settings.bpm<50||settings.bpm>200)throw Error('Tempo musí být mezi 50 a 200 BPM.');
  if((kind==='new'||kind==='preview')&&!$('lock-seed').checked){settings.seed=randomSeed();$('seed').value=settings.seed;settings.melody_seed=melodySeed=0;settings.sound_seed=soundSeed=0;}
  if(kind==='preview')settings.duration=30;
  if(kind==='melody')settings.melody_seed=melodySeed=randomSeed();
  if(kind==='sounds')settings.sound_seed=soundSeed=randomSeed();
  const request_id=crypto.randomUUID().replaceAll('-','');localStorage.setItem('music-forge-request',JSON.stringify({request_id}));
  $('progress').value=0;$('progress-text').textContent='Skládám motivy a aranžmá…';
  const result=await api('/api/render',{settings,request_id});activeJob=result.job;
  localStorage.setItem('music-forge-request',JSON.stringify({...result,request_id}));
  const status=await waitJob(result.job,token);if(!status)return;
  if(status.state==='error')throw Error(status.message);
  if(status.state==='cancelled'){toast('Generování zrušeno. Předchozí skladba zůstala zachovaná.');return;}
  const data=await api('/api/result?job='+result.job);if(token!==generationToken)return;
  project=result.project;current=data;dirty=false;lastWasPreview=kind==='preview';liveRevision=0;cachedLive=null;
  loadResult();localStorage.setItem('music-forge-settings',JSON.stringify(getSettings()));localStorage.setItem('music-forge-project',project);localStorage.setItem('music-forge-preview',String(lastWasPreview));localStorage.removeItem('music-forge-live');
  toast(kind==='preview'?'Hotový náhled 30 s. Hlavní tlačítko vytvoří celou délku.':'Skladba je připravená.');
 }catch(error){toast(error.message,true);}
 finally{if(token===generationToken){activeJob=null;setBusy(false);localStorage.removeItem('music-forge-request');}}
}''')
replace_function('loadResult','instrumentOptions',r'''function loadResult(){
 const p=current.plan,r=current.render;stemsReady=false;sectionLevels={...(p.settings.section_levels||{})};
 $('empty-wave').hidden=true;$('play').disabled=false;$('seek').disabled=false;$('seek').value=0;
 audio.volume=Number($('volume').value)/100;$('total-time').textContent=time(p.duration);$('current-time').textContent='0:00';
 $('song-meta').textContent=`${p.genre} · ${catalog.moods.find(m=>m.id===p.settings.mood)?.name||''} · ${p.bpm} BPM · ${p.key} ${p.mode} · ${time(p.duration)}`;
 $('render-meta').textContent=`Vytvořeno za ${r.render_seconds.toFixed(1)} s · ${r.master.peak_dbfs.toFixed(1)} dBFS peak`;
 $('structure-note').textContent=`${p.bars} taktů · ${p.sections.length} částí`;
 $('arrangement').classList.remove('empty');$('arrangement').innerHTML=p.sections.map((sec,i)=>`<button style="flex:${sec.bars};--section-colour:${SECTION_COLOURS[sec.kind]}" data-seek="${sec.start}" data-section="${i}" title="${esc(sec.name)} · ${time(sec.start)}">${esc(sec.name)}<small>${time(sec.start)}</small></button>`).join('');
 $('section-select').innerHTML=p.sections.map((sec,i)=>`<option value="${i}">${esc(sec.name)}</option>`).join('');$('section-level').disabled=false;showSectionLevel();
 $('chord-line').textContent='HARMONIE / '+p.harmony.slice(0,16).map(h=>h.name).join(' · ');
 for(const [id,file]of [['wav','master.wav'],['opus','master.opus'],['midi','composition.mid'],['credits','credits.txt']])$(id).href=`/audio/${project}/${file}?download=1`;
 for(const t of p.tracks){mixOverrides[t.id]={gain:t.gain,pan:t.pan,mute:t.mute,solo:t.solo};toneOverrides[t.id]={...t.tone};}
 $('wav-top').href=$('wav').href;$('opus-top').href=$('opus').href;
 renderMixer();drawWave();$('apply').textContent='Připravit export';$('apply').disabled=true;
 const loadingProject=project;
 audio.setProject(current,project,(done,total)=>{$('mix-status').textContent=`Načítám samostatné stopy ${done}/${total}…`;}).then(()=>{
  if(project!==loadingProject)return;stemsReady=true;setBusy(busy);$('mix-status').textContent='Živý mix · hlasitost, panorama, mute a efekty reagují okamžitě.';
  refreshLiveWave();
 }).catch(error=>{if(project===loadingProject)toast(error.message,true);});
}''')
replace_function('drawWave','syncTransport',r'''function drawWave(){
 const canvas=$('waveform'),rect=canvas.getBoundingClientRect();if(!rect.width)return;const dpr=devicePixelRatio||1,w=rect.width,h=rect.height;
 if(canvas.width!==Math.round(w*dpr)||canvas.height!==Math.round(h*dpr)){canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr);}
 const c=canvas.getContext('2d');c.setTransform(dpr,0,0,dpr,0,0);c.clearRect(0,0,w,h);
 if(!current){c.strokeStyle='#35483b';c.beginPath();c.moveTo(0,h/2);c.lineTo(w,h/2);c.stroke();return;}
 const p=current.plan,stats=current.render.master,data=stats.waveform||[],rms=stats.rms_waveform||[],position=audio.currentTime/p.duration,columns=Math.floor(w/3.5);
 for(const sec of p.sections){const x=sec.start/p.duration*w,sw=sec.duration/p.duration*w;c.fillStyle=SECTION_COLOURS[sec.kind];c.globalAlpha=.055;c.fillRect(x,0,sw,h);c.globalAlpha=.27;c.fillRect(x,0,1,h);}
 for(let i=0;i<columns;i++){
  const a=Math.floor(i*data.length/columns),b=Math.max(a+1,Math.floor((i+1)*data.length/columns));let peak=0,square=0;
  for(let j=a;j<b;j++){peak=Math.max(peak,data[j]||0);square+=(rms[j]??(data[j]||0)*.4)**2;}
  const at=i/columns*p.duration,sec=p.sections.find(s=>at>=s.start&&at<s.start+s.duration)||p.sections.at(-1);
  const ph=Math.max(1,Math.min(h*.92,peak*h*.92)),rh=Math.max(1,Math.min(ph,Math.sqrt(square/(b-a))*h*1.85));
  c.fillStyle=SECTION_COLOURS[sec.kind];c.globalAlpha=i/columns<=position?.44:.2;c.fillRect(i*w/columns,(h-ph)/2,2,ph);
  c.globalAlpha=i/columns<=position?1:.72;c.fillRect(i*w/columns,(h-rh)/2,2,rh);
 }c.globalAlpha=1;c.fillStyle='#edfce8';c.fillRect(position*w,4,1,h-8);
}''')
# Wire the existing mixer to the live engine, keeping composition edits explicit.
s=s.replace("$('apply').addEventListener('click',()=>generate('edit'));", "$('apply').addEventListener('click',()=>prepareExport());")
s=s.replace("api('/api/cancel',{})", "api('/api/cancel',{job:activeJob})")
s=s.replace("if(b&&current){audio.currentTime=Number(b.dataset.seek);syncTransport();}", "if(b&&current){audio.currentTime=Number(b.dataset.seek);$('section-select').value=b.dataset.section;showSectionLevel();syncTransport();}")
s=s.replace("if(e.code==='Space'&&!['INPUT','SELECT','TEXTAREA','BUTTON','SUMMARY'].includes(document.activeElement.tagName))", "if(e.code==='Space'&&(!['INPUT','SELECT','TEXTAREA','BUTTON','SUMMARY'].includes(document.activeElement.tagName)||['generate','generate-top','preview','apply','new-melody','new-sounds'].includes(document.activeElement.id)))")
s=s.replace("}else return;markDirty();});", "}else return;markDirty('audio');if(['attack','release'].includes(e.target.dataset.tone))queueTrack(role);});")
s=s.replace("instrumentOverrides[role]=e.target.value;markDirty();", "instrumentOverrides[role]=e.target.value;markDirty('audio');queueTrack(role);")
s=s.replace("renderMixer();markDirty();return;", "renderMixer();markDirty('audio');queueTrack(role);return;")
s=s.replace("button.setAttribute('aria-pressed',String(mixOverrides[role][type]));markDirty();", "button.setAttribute('aria-pressed',String(mixOverrides[role][type]));markDirty('audio');")
s=s.replace("if(current)renderMixer();markDirty();$('instrument-library').close();", "if(current)renderMixer();markDirty('audio');if(current)queueTrack(role);$('instrument-library').close();")
s=s.replace("const body={app:'music-forge-next',version:1,settings:getSettings()}", "const body={app:'music-forge-next',version:1,settings:current?liveSettings():getSettings()}")
s=s.replace("$('research-search').addEventListener('input',renderResearch);", """$('section-select').addEventListener('change',showSectionLevel);$('section-level').addEventListener('input',()=>{sectionLevels[$('section-select').value]=Number($('section-level').value)/100;showSectionLevel();markDirty('audio');});
 for(const id of ['wav','opus','wav-top','opus-top'])$(id).addEventListener('click',e=>{e.preventDefault();if(current&&!busy&&!exporting)prepareExport(id.startsWith('wav')?'wav':'opus');});
 setInterval(checkServerState,1200);checkServerState(true);
 $('research-search').addEventListener('input',renderResearch);""".replace('\n+ ','\n '))
# Extra live functions are module-local; no global callbacks or duplicate event binding.
position=s.rfind('\ninit();')
s=s[:position]+r'''
function liveSettings(){return {...structuredClone(current.plan.settings),title:$('title').value.trim()||current.plan.title,instruments:{...current.plan.settings.instruments,...instrumentOverrides},mix:structuredClone(mixOverrides),tone:structuredClone(toneOverrides),section_levels:{...sectionLevels}};}
function showSectionLevel(){const i=$('section-select').value,value=Math.round((sectionLevels[i]??1)*100);$('section-level').value=value;$('section-level-value').textContent=value+' %';}
function queueTrack(role){
 clearTimeout(trackTimers.get(role));const record=audio.records.get(role);if(record)record.version=(record.version||0)+1;
 const targetProject=project;
 trackTimers.set(role,setTimeout(()=>{if(project!==targetProject||busy)return;
  const t=current.plan.tracks.find(t=>t.id===role),instrument=instrumentOverrides[role]||t.instrument;
  $('mix-status').textContent=`Načítám nový zvuk: ${t.name}…`;document.querySelector(`.mixer-row[data-role="${role}"]`)?.classList.add('loading-track');
  const task=audio.replaceTrack(role,instrument,toneOverrides[role]).then(changed=>{if(changed&&project===targetProject){$('mix-status').textContent='Nový zvuk hraje ve stejném místě skladby.';clearTimeout(waveTimer);waveTimer=setTimeout(refreshLiveWave,200);}}).catch(e=>{if(project===targetProject)toast(e.message,true);}).finally(()=>{if(trackPromises.get(role)===task){trackPromises.delete(role);document.querySelector(`.mixer-row[data-role="${role}"]`)?.classList.remove('loading-track');}});
  trackPromises.set(role,task);trackTimers.delete(role);
 },230));
}
async function settleTracks(){while(trackTimers.size||trackPromises.size){await new Promise(r=>setTimeout(r,80));await Promise.all([...trackPromises.values()]);}}
async function refreshLiveWave(){
 if(!current||!stemsReady||busy||exporting)return;if(waveRunning){clearTimeout(waveTimer);waveTimer=setTimeout(refreshLiveWave,500);return;}
 const revision=liveRevision,identity=project,serial=++waveSerial;waveRunning=true;
 try{await settleTracks();const snapshot=await audio.snapshot();const rendered=await audio.renderSnapshot(snapshot);if(identity!==project||revision!==liveRevision||serial!==waveSerial)return;
  cachedLive={...rendered,revision,project:identity,snapshot};Object.assign(current.render.master,{waveform:rendered.waveform,rms_waveform:rendered.rms_waveform,peak_dbfs:rendered.peak_dbfs});drawWave();
 }catch(e){toast('Průběh mixu: '+e.message,true);}finally{waveRunning=false;}
}
async function prepareExport(format){
 if(!current||busy||exporting)return;exporting=true;setBusy(false);const identity=project,revision=liveRevision,token=++generationToken;
 try{
  $('progress-box').hidden=false;$('progress').value=.03;$('progress-text').textContent='Připravuji přesný aktuální mix…';await settleTracks();await audio.ready;
  const snapshot=await audio.snapshot();let rendered=cachedLive&&cachedLive.revision===revision&&cachedLive.project===identity?cachedLive:await audio.renderSnapshot(snapshot);
  const settings=liveSettings(),body=await exportBody(rendered.buffer,{settings});const request_id=crypto.randomUUID().replaceAll('-','');
  const response=await fetch(`/api/export?project=${identity}&request_id=${request_id}`,{method:'POST',body});const result=await response.json();if(!response.ok)throw Error(result.error);activeJob=result.job;
  const status=await waitJob(result.job,token);if(!status||status.state!=='done')throw Error(status?.message||'Export se nepodařil.');
  const exported=await api('/api/result?job='+result.job);if(identity!==project)return;
  for(const [id,ext]of [['wav','wav'],['opus','opus'],['wav-top','wav'],['opus-top','opus'],['midi','mid'],['credits','txt']])$(id).href=`/export/${identity}/${result.job}.${ext}`;
  if(liveRevision===revision){dirty=false;current.render.master=exported.render.master;$('apply').disabled=true;drawWave();}
  $('mix-status').textContent='WAV i Opus odpovídají aktuálnímu živému mixu.';
  if(format){const a=document.createElement('a');a.href=`/export/${identity}/${result.job}.${format}`;a.download='music-forge.'+format;a.click();}else toast('WAV i Opus jsou připravené v obou nabídkách exportu.');
 }catch(e){toast(e.message,true);}finally{exporting=false;activeJob=null;setBusy(false);}
}
let checkingState=false,externalBusy=false;
async function checkServerState(initial=false){
 if(checkingState||exporting||activeJob)return;checkingState=true;
 try{const state=await api('/api/state');
  if(state.active){
   let pending;try{pending=JSON.parse(localStorage.getItem('music-forge-request')||'null');}catch{}
   if(initial&&pending&&state.active.kind==='composition'&&pending.request_id===state.active.request_id){
    const token=++generationToken;activeJob=state.active.id;setBusy(true);const done=await waitJob(activeJob,token);
    if(done?.state==='done'){const data=await api('/api/result?job='+activeJob);if(token===generationToken){project=done.project;current=data;loadResult();localStorage.setItem('music-forge-project',project);}}
    activeJob=null;localStorage.removeItem('music-forge-request');setBusy(false);
   }else if(!busy){externalBusy=true;setBusy(true);$('progress-text').textContent='Probíhá úloha otevřená v jiné kartě…';}
  }else if(externalBusy){externalBusy=false;setBusy(false);}
 }catch{}finally{checkingState=false;}
}
''' .replace('\n+','\n')+s[position:]
p.write_text(s,encoding='utf-8')

p=ROOT/'static/index.html';s=p.read_text('utf-8').replace('<script src="/app.js" defer>','<script type="module" src="/app.js">')
s=s.replace('<button id="save" class="outline">','<a id="wav-top" class="export-link disabled" aria-disabled="true">WAV <small>24 bit</small> ↓</a><a id="opus-top" class="export-link disabled" aria-disabled="true">Opus <small>160 kb/s</small> ↓</a><button id="save" class="outline">')
s=s.replace('<div id="chord-line" class="chord-line"></div>', '<div id="chord-line" class="chord-line"></div><div class="section-mix"><label for="section-select">Hlasitost části</label><select id="section-select" aria-label="Část skladby"></select><input id="section-level" type="range" min="0" max="160" value="100" disabled aria-label="Hlasitost části"><output id="section-level-value">100 %</output><span>RMS uvnitř · špičky v obrysu</span></div>')
s=s.replace('Změnu uslyšíš po použití úprav v mixu.','Zvuk se načte samostatně a naváže na právě přehrávané místo.')
s=s.replace('Použít úpravy <span>→</span>','Připravit export <span>→</span>')
p.write_text(s,encoding='utf-8')
