import {curveEditor,paintCurveEditors,installCurveEditors,flatCurve} from './volume-curve.mjs';
import {LiveMixer,SECTION_COLOURS,exportBody} from './live-mixer.mjs';
import {installHoverReset} from './control-reset.mjs';
import {gainLimit,downloadName,generateTitle} from './mix-balance.mjs';
import {initSeedMenu} from './seed-menu.mjs';
import {TrackWaveViews} from './track-waves.mjs';
import {trackState} from './track-state.mjs';
'use strict';
history.scrollRestoration='manual';
const $=id=>document.getElementById(id);
const audio=new LiveMixer();
let catalog,project=null,current=null,busy=false,dirty=false,toastTimer,research=null,lastWasPreview=false,activeExportId=null,activeExportVersion=1,preparedUnclaimed=false,customTitle=false;
const exportCounts=new Map();
let generationToken=0,activeJob=null,exporting=false,stemsReady=false,liveRevision=0,waveSerial=0,waveTimer=null,waveRunning=false,cachedLive=null,sectionLevels={};
let waveRequested=false,waveChangeAt=0;
let quickWave=null,quickWaveQueued=false,pendingRecipe=null;
const trackTimers=new Map(),trackPromises=new Map();
const trackViews=new TrackWaveViews($('mixer'),audio,()=>syncTransport(),role=>trackTimers.has(role)||trackPromises.has(role));
let originalTracks=new Map();
const trackResetUndo=new Map();
let instrumentOverrides={},mixOverrides={},toneOverrides={},melodySeed=0,soundSeed=0;
const roles=[['drums','Bicí','#eab676'],['bass','Basa','#caa8ff'],['chords','Akordy','#64d5c1'],['lead','Hlavní melodie','#a5a2ff'],['counter','Odpovědi','#ed9fc0'],['pad','Atmosféra','#79b9e3'],['arp','Arpeggio','#b4ce7c'],['fx','Přechody','#d6b395']];
const familyNames={house:'HOUSE & DANCE',bass:'BASS MUSIC',dnb:'DRUM & BASS',retro:'RETRO & SYNTH',pop:'POP',rock:'ROCK',hiphop:'HIP HOP & BEATS',jazz:'JAZZ & FUNK',world:'WORLD & LATIN',acoustic:'AKUSTICKÁ HUDBA',classical:'KLASIKA & FILM',ambient:'AMBIENT & CHILL'};
const toneLabels=[['brightness','Jas','Tmavší ↔ otevřenější filtr'],['attack','Náběh','Krátký ↔ měkký začátek tónu'],['release','Doznění','Krátký ↔ delší konec tónu'],['drive','Sytost','Čistý ↔ jemně zkreslený zvuk'],['space','Prostor','Suchý ↔ více dozvuků']];
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const randomSeed=()=>crypto.getRandomValues(new Uint32Array(1))[0]%2147483647;
const time=seconds=>{seconds=Math.max(0,Math.floor(seconds||0));return `${Math.floor(seconds/60)}:${String(seconds%60).padStart(2,'0')}`;};
function toast(message,error=false){clearTimeout(toastTimer);$('toast').textContent=message;$('toast').classList.toggle('error',error);$('toast').hidden=false;toastTimer=setTimeout(()=>$('toast').hidden=true,error?9000:4500);}
async function api(path,body){const response=await fetch(path,body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:{});const data=await response.json();if(!response.ok)throw Error(data.error||`Chyba ${response.status}`);return data;}
function selectedGenre(){return catalog?.genres.find(g=>g.id===$('genre').value)||catalog?.genres[0];}
function nextExportVersion(seed,kind='audio'){const k=`${Math.trunc(Number(seed)||0)}:${kind}`,v=(exportCounts.get(k)||0)+1;exportCounts.set(k,v);return v;}
function peekExportVersion(seed,kind='audio'){return (exportCounts.get(`${Math.trunc(Number(seed)||0)}:${kind}`)||0)+1;}
function updateAutoTitle(force=false){
 if(!catalog||(customTitle&&!force))return;
 if(force)customTitle=false;
 const text=$('seed').value.trim(),num=Number(text),seedVal=(text&&Number.isInteger(num)&&num>=0&&num<=2147483647)?num:(catalog.startup_seed??catalog.default.seed);
 $('title').value=generateTitle(catalog,$('genre').value,$('mood').value,seedVal,Number($('energy').value)/100);
 syncDownloadLinks();
}
function syncMoodOptions(){
 if(!catalog)return;
 const currentMood=$('mood').value,rec=new Set(selectedGenre()?.recommended||[]);
 for(const opt of $('mood').options){const m=catalog.moods.find(x=>x.id===opt.value);if(m)opt.textContent=rec.has(m.id)?`${m.name} ★`:m.name;}
 if(currentMood)$('mood').value=currentMood;
}
function syncDownloadLinks(){
 if(!current||!project)return;
 const liveTitle=$('title').value.trim()||current.plan.title||'Nová skladba',seed=current.plan.settings.seed,qTitle=encodeURIComponent(liveTitle);
 const midVer=peekExportVersion(seed,'mid'),txtVer=peekExportVersion(seed,'txt');
 if(activeExportId){
  for(const [id,ext]of [['wav','wav'],['opus','opus'],['wav-top','wav'],['opus-top','opus']]){
   $(id).href=`/export/${project}/${activeExportId}.${ext}?title=${qTitle}&version=${activeExportVersion}`;
   $(id).download=downloadName(liveTitle,ext,seed,activeExportVersion);
  }
  $('midi').href=`/export/${project}/${activeExportId}.mid?title=${qTitle}&version=${midVer}`;
  $('midi').download=downloadName(liveTitle,'mid',seed,midVer);
  $('credits').href=`/export/${project}/${activeExportId}.txt?title=${qTitle}&version=${txtVer}`;
  $('credits').download=downloadName(liveTitle,'txt',seed,txtVer);
 }else{
  const audioVer=peekExportVersion(seed,'audio');
  for(const [id,file,ext,ver]of [['wav','master.wav','wav',audioVer],['opus','master.opus','opus',audioVer],['midi','composition.mid','mid',midVer],['credits','credits.txt','txt',txtVer]]){
   $(id).href=`/audio/${project}/${file}?download=1&title=${qTitle}&version=${ver}`;
   $(id).download=downloadName(liveTitle,ext,seed,ver);
  }
  $('wav-top').href=$('wav').href;$('wav-top').download=$('wav').download;
  $('opus-top').href=$('opus').href;$('opus-top').download=$('opus').download;
 }
}
function syncDurationUI(){
 const m=Number($('minutes').value),s=Number($('seconds').value),total=m*60+s;
 const valid=Number.isFinite(total)&&s>=0&&s<=59&&total>=20&&total<=600;
 document.querySelectorAll('[data-duration]').forEach(b=>b.classList.toggle('selected',valid&&Number(b.dataset.duration)===total));
 if(!current&&valid)$('total-time').textContent=time(total);
}
function markDirty(kind='composition'){
 dirty=true;
 if(kind==='audio'&&current){
  if(pendingRecipe){pendingRecipe=null;setBusy(busy);}
  preparedUnclaimed=false;liveRevision++;cachedLive=null;audio.setMix(mixOverrides,toneOverrides);audio.setLevels(sectionLevels);
  $('mix-status').textContent='Živý mix · změny slyšíš při přehrávání.';
  $('apply').textContent='Připravit export';$('apply').disabled=busy||exporting;
  waveChangeAt=performance.now();scheduleQuickWave();scheduleLiveWave(140);
  trackViews.refresh();
 }else{$('mix-status').textContent=current?'Zadání pro příští skladbu se změnilo.':'Nastav skladbu a spusť tvorbu.';}
}
function duration(){const n=Number($('minutes').value)*60+Number($('seconds').value);if(!Number.isFinite(n)||n<20||n>600)throw Error('Délka musí být mezi 0:20 a 10:00.');if(Number($('seconds').value)>59||Number($('seconds').value)<0)throw Error('Sekundy musí být mezi 0 a 59.');return n;}
function getSettings(){const seed=chosenSeed(),genre=$('genre').value,mood=$('mood').value,energy=Number($('energy').value)/100;return {genre,mood,duration:duration(),bpm:Number($('bpm').value),key:$('key').value,seed,title:$('title').value.trim()||generateTitle(catalog,genre,mood,seed,energy),melody_seed:melodySeed,sound_seed:soundSeed,...Object.fromEntries(['energy','complexity','variation','humanize','space'].map(id=>[id,Number($(id).value)/100])),instruments:structuredClone(pendingRecipe?.instruments??instrumentOverrides),mix:structuredClone(pendingRecipe?.mix??mixOverrides),tone:structuredClone(pendingRecipe?.tone??toneOverrides),section_levels:{...(pendingRecipe?.section_levels??sectionLevels)}};}
function setDuration(seconds){$('minutes').value=Math.floor(seconds/60);$('seconds').value=String(Math.floor(seconds%60)).padStart(2,'0');document.querySelectorAll('[data-duration]').forEach(b=>b.classList.toggle('selected',Number(b.dataset.duration)===seconds));if(!current)$('total-time').textContent=time(seconds);}
function ranges(){for(const id of ['energy','complexity','variation','humanize','space'])$(id+'-value').textContent=$(id).value+' %';}
function updateMoodChips(){
 $('mood-chips').innerHTML=['happy','sad','energetic','dark'].map(id=>{const m=catalog.moods.find(x=>x.id===id);return `<button class="mood-chip ${$('mood').value===id?'selected':''}" data-mood="${id}">${esc(m.name)}</button>`;}).join('');
}
function moodChanged(){const m=catalog.moods.find(m=>m.id===$('mood').value)||catalog.moods[0];$('energy').value=Math.round(m.energy*100);ranges();updateMoodChips();updateAutoTitle(true);markDirty();}
function genreChanged(){const g=selectedGenre();if(!g)return;$('bpm').value=g.bpm;$('genre-description').textContent=g.description;if(current)pendingRecipe={instruments:{},mix:{},tone:{},section_levels:{}};else{instrumentOverrides={};mixOverrides={};toneOverrides={};renderMixer();}soundSeed=0;melodySeed=0;syncMoodOptions();updateMoodChips();updateAutoTitle(true);markDirty();setBusy(busy);}
function setSettings(s){sectionLevels={...(s.section_levels||{})};$('genre').value=catalog.genres.some(g=>g.id===s.genre)?s.genre:catalog.default.genre;syncMoodOptions();$('mood').value=catalog.moods.some(m=>m.id===s.mood)?s.mood:catalog.default.mood;setDuration(Number(s.duration)||210);$('bpm').value=s.bpm||selectedGenre().bpm;$('key').value=s.key||'auto';$('seed').value=s.seed??431207;for(const id of ['energy','complexity','variation','humanize','space'])$(id).value=Math.round((s[id]??catalog.default[id])*100);const auto=generateTitle(catalog,$('genre').value,$('mood').value,$('seed').value,Number($('energy').value)/100);if(s.title&&s.title!=='Nová skladba'&&s.title!=='Neonový horizont'&&s.title!==auto){$('title').value=s.title;customTitle=true;}else{$('title').value=auto;customTitle=false;}instrumentOverrides=s.instruments||{};mixOverrides=s.mix||{};toneOverrides=s.tone||{};melodySeed=s.melody_seed||0;soundSeed=s.sound_seed||0;ranges();updateMoodChips();$('genre-description').textContent=selectedGenre().description;}
function setBusy(value){
 busy=value;for(const id of ['generate','generate-top','preview','load','reset','random-seed','open-seeds'])$(id).disabled=value||exporting;
 for(const id of ['new-melody','new-sounds'])$(id).disabled=value||exporting||!current||Boolean(pendingRecipe);
 $('apply').disabled=value||exporting||!current||!dirty;
 $('progress-box').hidden=!value&&!exporting;$('cancel').disabled=exporting;
 $('mixer').setAttribute('aria-busy',String((value&&!exporting)||!stemsReady));
 document.querySelectorAll('#mixer input,#mixer select,#mixer button').forEach(x=>x.disabled=(value&&!exporting)||!stemsReady||x.dataset.curveDisabled==='true');
 for(const id of ['wav','opus','wav-top','opus-top']){$(id).classList.toggle('disabled',!current||value||exporting);$(id).setAttribute('aria-disabled',String(!current||value||exporting));}
}
async function waitJob(job,token){
 let status;
 while(true){await new Promise(r=>setTimeout(r,250));status=await api('/api/status?job='+job);if(token!==generationToken)return null;
  $('progress').value=status.progress;$('progress-text').textContent=status.message;$('cancel').disabled=exporting||Boolean(status.committing);if(status.state!=='running')return status;}
}
async function generate(kind='new'){
 if(busy||exporting)return;
 try{audio.ensureContext();}catch{}
 const token=++generationToken;setBusy(true);activeJob=null;
 try{
  if(!customTitle)updateAutoTitle();
  const settings=getSettings();if(!Number.isFinite(settings.bpm)||settings.bpm<50||settings.bpm>200)throw Error('Tempo musí být mezi 50 a 200 BPM.');
  if(kind==='preview')settings.duration=30;
  if(kind==='melody')settings.melody_seed=melodySeed=randomSeed();
  if(kind==='sounds')settings.sound_seed=soundSeed=randomSeed();
  const request_id=crypto.randomUUID().replaceAll('-','');
  $('progress').value=0;$('progress-text').textContent='Skládám motivy a aranžmá…';
  const result=await api('/api/render',{settings,request_id});activeJob=result.job;
  const status=await waitJob(result.job,token);if(!status)return;
  if(status.state==='error')throw Error(status.message);
  if(status.state==='cancelled'){toast('Generování zrušeno. Předchozí skladba zůstala zachovaná.');return;}
  const data=await api('/api/result?job='+result.job);if(token!==generationToken)return;
  project=result.project;current=data;activeExportId=null;activeExportVersion=1;preparedUnclaimed=false;pendingRecipe=null;dirty=false;lastWasPreview=kind==='preview';liveRevision=0;cachedLive=null;
  loadResult();
  toast(kind==='preview'?'Hotový náhled 30 s. Hlavní tlačítko vytvoří celou délku.':'Skladba je připravená.');
 }catch(error){toast(error.message,true);}
 finally{if(token===generationToken){activeJob=null;setBusy(false);}}
}
function loadResult(){
 quickWave=null;
 trackViews.reset();trackResetUndo.clear();originalTracks=new Map(current.plan.tracks.map(t=>[t.id,trackState(t.seed_default||t)]));
 for(const timer of trackTimers.values())clearTimeout(timer);trackTimers.clear();trackPromises.clear();
 const p=current.plan,r=current.render;stemsReady=false;sectionLevels={...(p.settings.section_levels||{})};
 if(!customTitle&&p.title)$('title').value=p.title;
 $('empty-wave').hidden=true;$('play').disabled=false;$('seek').disabled=false;$('seek').value=0;
 audio.volume=Number($('volume').value)/100;$('total-time').textContent=time(p.duration);$('current-time').textContent='0:00';
 $('song-meta').textContent=`${p.genre} · ${catalog.moods.find(m=>m.id===p.settings.mood)?.name||''} · ${p.bpm} BPM · ${p.key} ${p.mode} · ${time(p.duration)} · seed ${p.settings.seed}`;
 $('render-meta').textContent=`Vytvořeno za ${r.render_seconds.toFixed(1)} s · ${r.master.peak_dbfs.toFixed(1)} dBFS peak`;
 $('structure-note').textContent=`${p.bars} taktů · ${p.sections.length} částí`;
 $('arrangement').classList.remove('empty');$('arrangement').innerHTML=p.sections.map((sec,i)=>`<button style="flex:${sec.bars};--section-colour:${SECTION_COLOURS[sec.kind]}" data-seek="${sec.start}" data-section="${i}" title="${esc(sec.name)} · ${time(sec.start)}">${esc(sec.name)}<small>${time(sec.start)}</small></button>`).join('');
 $('section-select').innerHTML=p.sections.map((sec,i)=>`<option value="${i}">${esc(sec.name)}</option>`).join('');$('section-level').disabled=false;showSectionLevel();
 $('chord-line').textContent='HARMONIE / '+p.harmony.slice(0,16).map(h=>h.name).join(' · ');
 syncDownloadLinks();
 instrumentOverrides={...(p.settings.instruments||{})};
 for(const t of p.tracks){mixOverrides[t.id]={gain:t.gain,pan:t.pan,mute:t.mute,solo:t.solo,curve:structuredClone(t.curve||flatCurve())};toneOverrides[t.id]={...t.tone};}
 renderMixer();drawWave();$('apply').textContent='Připravit export';$('apply').disabled=true;
 const loadingProject=project;
 audio.setProject(current,project,(done,total)=>{$('mix-status').textContent=`Načítám samostatné stopy ${done}/${total}…`;}).then(()=>{
  if(project!==loadingProject)return;stemsReady=true;audio.setMix(mixOverrides,toneOverrides);setBusy(busy);$('mix-status').textContent='Živý mix · hlasitost, panorama, mute a efekty reagují okamžitě.';
  waveChangeAt=performance.now();scheduleQuickWave();scheduleLiveWave(0);trackViews.refresh();
 }).catch(error=>{if(project===loadingProject){$('mix-status').textContent='Stopy se nepodařilo načíst. Zkus skladbu vytvořit znovu.';toast(error.message,true);}});
}
function instrumentOptions(role,selected){const entries=catalog.instruments.filter(i=>(i.bank===128)===(role==='drums'));let groups=new Map();for(const i of entries){const label=i.group+' · '+(i.engine==='synth'?'Forge':i.source.includes('MuseScore')?'MS':i.source.includes('Salamander')?'Salamander':'GS');if(!groups.has(label))groups.set(label,[]);groups.get(label).push(i);}return [...groups].map(([name,items])=>`<optgroup label="${esc(name)}">${items.map(i=>`<option value="${esc(i.id)}" ${i.id===selected?'selected':''}>${esc(i.name)}${role==='bass'&&['Dechy','Flétny','Žestě'].includes(i.group)?' · nevhodné pro basový rejstřík':''}</option>`).join('')}</optgroup>`).join('');}
function renderMixer(){
 if(!current){
  const planned=pendingRecipe?.instruments??instrumentOverrides;
  $('mixer').innerHTML=roles.map(([id,name,c])=>{const chosen=planned?.[id]&&catalog?.instruments.find(i=>i.id===planned[id]);return `<div class="empty-mixer-row"><span><b class="track-dot" style="--track-colour:${c}"></b>${name}</span><i></i><i></i><small>${chosen?esc(chosen.name):'Auto'}</small></div>`;}).join('');
  return;
 }
 const opened=new Set([...document.querySelectorAll('.tone-panel:not([hidden])')].map(el=>el.dataset.role));
 const openedCurves=new Set([...document.querySelectorAll('.volume-automation[open]')].map(el=>el.dataset.curveRole));
 $('mixer').innerHTML=current.plan.tracks.map(t=>{
  const recommended=trackDefaultGain(t.id),m=mixOverrides[t.id]||t,tone=toneOverrides[t.id]||t.tone;
  return `<div class="mixer-row" data-role="${t.id}"><div class="mixer-row-main"><div class="track-label"><span class="track-dot" style="--track-colour:${t.colour}"></span><div class="track-info"><span class="track-name">${esc(t.name)} <small>${t.notes.length?'':'pauza'}</small></span><select class="instrument-select" aria-label="Nástroj: ${esc(t.name)}">${instrumentOptions(t.id,instrumentOverrides[t.id]||t.instrument)}</select></div></div><div class="mix-gain"><input class="gain" type="range" min="0" max="150" title="Výchozí hlasitost: ${Math.round(recommended*100)} % · ručně lze zvýšit" value="${Math.round(m.gain*100)}" aria-label="Hlasitost: ${esc(t.name)}"><output>${Math.round(m.gain*100)}</output></div><div class="pan-control"><input class="pan" type="range" min="-100" max="100" value="${Math.round(m.pan*100)}" aria-label="Panorama: ${esc(t.name)}"><output>${panLabel(m.pan)}</output></div><div class="row-buttons"><button class="mute ${m.mute?'active':''}" aria-label="Ztlumit: ${esc(t.name)}" aria-pressed="${m.mute}">M</button><button class="solo ${m.solo?'active':''}" aria-label="Sólo: ${esc(t.name)}" aria-pressed="${m.solo}">S</button><button class="edit-tone ${opened.has(t.id)?'active':''}" aria-label="Upravit zvuk: ${esc(t.name)}" aria-expanded="${opened.has(t.id)}">☷</button></div></div><div class="tone-panel" data-role="${t.id}" ${opened.has(t.id)?'':'hidden'}><div class="tone-header"><span>${esc(t.name)} · zvuk nástroje</span><button class="reset-tone quiet">Obnovit zvuk presetu</button></div><div class="tone-controls">${toneLabels.map(([key,name,hint])=>{const value=Math.round((tone[key]??(['brightness','attack','release'].includes(key)?.5:0))*100);return `<div class="tone-control"><label for="${t.id}-${key}">${name}<output>${value} %</output></label><input id="${t.id}-${key}" data-tone="${key}" type="range" min="0" max="100" value="${value}"><p>${hint}${['attack','release'].includes(key)?' · 50 % = původní preset':''}</p></div>`;}).join('')}</div></div>${curveEditor(t.id,m.curve)}</div>`;
 }).join('');
 paintCurveEditors($('mixer'),role=>mixOverrides[role]?.curve,current.plan,SECTION_COLOURS);
 for(const el of $('mixer').querySelectorAll('.volume-automation'))el.open=openedCurves.has(el.dataset.curveRole);
 for(const row of $('mixer').querySelectorAll('.mixer-row')){const role=row.dataset.role;row.querySelector('.row-buttons').insertAdjacentHTML('beforeend',`<button class="reset-track" title="Obnovit původně vygenerovaný nástroj, jeho hlasitost, panorama, efekty a křivku" aria-label="Obnovit celou stopu: ${esc(current.plan.tracks.find(t=>t.id===role).name)}">↺</button><button class="undo-track-reset" ${trackResetUndo.has(role)?'':'hidden'} title="Vrátit poslední reset této stopy" aria-label="Vrátit reset stopy">Zpět</button>`);}
 trackViews.refresh();
}
function panLabel(value){return Math.abs(value)<.01?'Střed':`${value<0?'L':'R'} ${Math.round(Math.abs(value)*100)}`;}
function drawWave(){
 const canvas=$('waveform'),rect=canvas.getBoundingClientRect();if(!rect.width)return;const dpr=devicePixelRatio||1,w=rect.width,h=rect.height;
 if(canvas.width!==Math.round(w*dpr)||canvas.height!==Math.round(h*dpr)){canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr);}
 const c=canvas.getContext('2d');c.setTransform(dpr,0,0,dpr,0,0);c.clearRect(0,0,w,h);
 if(!current){c.strokeStyle='#35483b';c.beginPath();c.moveTo(0,h/2);c.lineTo(w,h/2);c.stroke();return;}
 const p=current.plan,stats=quickWave||current.render.master,data=stats.waveform||[],rms=stats.rms_waveform||[],position=audio.currentTime/p.duration,columns=Math.floor(w/3.5);
 for(const sec of p.sections){const x=sec.start/p.duration*w,sw=sec.duration/p.duration*w;c.fillStyle=SECTION_COLOURS[sec.kind];c.globalAlpha=.055;c.fillRect(x,0,sw,h);c.globalAlpha=.27;c.fillRect(x,0,1,h);}
 for(let i=0;i<columns;i++){
  const a=Math.floor(i*data.length/columns),b=Math.max(a+1,Math.floor((i+1)*data.length/columns));let peak=0,square=0;
  for(let j=a;j<b;j++){peak=Math.max(peak,data[j]||0);square+=(rms[j]??(data[j]||0)*.4)**2;}
  const at=i/columns*p.duration,sec=p.sections.find(s=>at>=s.start&&at<s.start+s.duration)||p.sections.at(-1);
  const ph=Math.max(1,Math.min(h*.92,peak*h*.92)),rh=Math.max(1,Math.min(ph,Math.sqrt(square/(b-a))*h*1.85));
  c.fillStyle=SECTION_COLOURS[sec.kind];if($('show-peaks').checked){c.globalAlpha=i/columns<=position?.44:.2;c.fillRect(i*w/columns,(h-ph)/2,2,ph);}
  c.globalAlpha=i/columns<=position?1:.72;c.fillRect(i*w/columns,(h-rh)/2,2,rh);
 }c.globalAlpha=1;c.fillStyle='#edfce8';c.fillRect(position*w,4,1,h-8);
}
function syncTransport(){const playing=!audio.paused;$('play').textContent=playing?'Ⅱ':'▶';$('play').classList.toggle('playing',playing);$('play').setAttribute('aria-label',playing?'Pozastavit':'Přehrát');$('current-time').textContent=time(audio.currentTime);if(current)$('seek').value=Math.round(audio.currentTime/current.plan.duration*1000);drawWave();trackViews.position();}
async function togglePlay(){if(!current)return;try{audio.ensureContext();if(audio.paused)await audio.play();else audio.pause();}catch{toast('Zvuk se nepodařilo načíst. Vytvoř skladbu znovu.',true);}}
async function showResearch(){
 $('studio-view').hidden=true;$('research-view').hidden=false;$('studio-tab').classList.remove('selected');$('research-tab').classList.add('selected');
 if(!research){try{research=await api('/api/research');const minutes=Math.round(research.tracks.reduce((n,t)=>n+t.duration,0)/60);$('research-summary').innerHTML=[[research.tracks.length,'skladeb · náhodný výběr'],[minutes+' min','zvuku v celkové analýze'],[research.tracks.length*3,'úseků s detekcí zvuků']].map(([n,label])=>`<div class="research-stat"><strong>${n}</strong><span>${label}</span></div>`).join('');renderResearch();}catch(error){toast(error.message,true);}}
}
function renderResearch(){if(!research)return;const query=$('research-search').value.toLocaleLowerCase('cs');$('research-tracks').innerHTML=research.tracks.filter(t=>t.name.toLocaleLowerCase('cs').includes(query)).map(t=>{const index=research.tracks.indexOf(t);return `<details class="research-track" data-index="${index}"><summary><strong>${esc(t.name)}</strong><span>${time(t.duration)} · ≈ ${t.tempo_bpm} BPM ＋</span></summary><div class="research-track-body"><canvas aria-label="Průběh energie nahrávky"></canvas><div class="research-metrics"><span>RMS ${t.rms_dbfs} dBFS</span><span>Crest ${t.crest_db} dB</span><span>Podíl basů ${Math.round(t.low_band_ratio*100)} %</span><span>Tónina ≈ ${esc(t.key_candidates[0].key)}</span></div><div>Odhady nástrojů / skóre modelu</div>${t.instrument_estimates.slice(0,7).map(tag=>`<span class="tag ${tag.score<.1?'weak':''}">${esc(tag.label)} · ${tag.score.toFixed(3)}${tag.score<.1?' · slabý odhad':''}</span>`).join('')}<p>CLAP · podobnost zvuku s popisem (pořadí hypotéz)</p>${(t.clap_instrument_ranking||[]).slice(0,6).map(tag=>`<span class="tag">${esc(tag.label)} · ${tag.cosine.toFixed(3)}</span>`).join('')}<p>Úseky detekce od ${t.tag_windows_seconds.map(time).join(', ')}. Změny struktury: ${t.section_candidates_seconds.slice(0,12).map(time).join(' · ')||'bez výrazného kandidáta'}.<br>SHA-256: ${t.sha256}</p></div></details>`;}).join('');}
function drawResearch(details){const t=research?.tracks[Number(details.dataset.index)],canvas=details.querySelector('canvas'),rect=canvas?.getBoundingClientRect();if(!t||!rect||!rect.width||!rect.height)return;const dpr=devicePixelRatio||1;canvas.width=Math.round(rect.width*dpr);canvas.height=Math.round(rect.height*dpr);const c=canvas.getContext('2d');c.setTransform(dpr,0,0,dpr,0,0);const max=Math.max(...t.energy_2s,1e-6);c.fillStyle='#6a956b';for(let i=0;i<t.energy_2s.length;i++){const h=t.energy_2s[i]/max*rect.height;c.fillRect(i*rect.width/t.energy_2s.length,rect.height-h,Math.max(1,rect.width/t.energy_2s.length-1),h);}c.strokeStyle='#e9cc7b';for(const sec of t.section_candidates_seconds){const x=sec/t.duration*rect.width;c.beginPath();c.moveTo(x,0);c.lineTo(x,rect.height);c.stroke();}}
function downloadJSON(){try{const body={app:'music-forge-next',version:1,settings:getSettings()},ver=nextExportVersion(body.settings.seed,'json'),blob=new Blob([JSON.stringify(body,null,2)],{type:'application/json'}),url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=downloadName(body.settings.title,'json',body.settings.seed,ver);a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);toast('Projekt uložený. Obsahuje nastavení a seed; zvuk se při otevření znovu vyrenderuje.');}catch(e){toast(e.message,true);}}
function validateProject(raw){if(raw.app!=='music-forge-next'||raw.version!==1||!raw.settings||typeof raw.settings!=='object')throw Error('Toto není podporovaný projekt Music Forge Next 1.');const s=raw.settings;if(!catalog.genres.some(g=>g.id===s.genre)||!catalog.moods.some(m=>m.id===s.mood))throw Error('Projekt obsahuje neznámý styl nebo náladu.');for(const key of ['duration','bpm','seed','energy','complexity','variation','humanize','space'])if(typeof s[key]!=='number'||!Number.isFinite(s[key]))throw Error('Projekt obsahuje neplatné nastavení: '+key);if(s.duration<20||s.duration>600||s.bpm<50||s.bpm>200)throw Error('Délka nebo tempo jsou mimo podporovaný rozsah.');return s;}

async function init(){
 // Reset native browser form restoration as well as application state.
 for(const input of document.querySelectorAll('input')){input.autocomplete='off';if(input.type==='checkbox')input.checked=input.defaultChecked;else if(input.type!=='file')input.value=input.defaultValue;}
 try{
  catalog=await api('/api/catalogue');
  $('genre-count').textContent=catalog.genres.length+' stylů';$('instrument-count').textContent=catalog.instruments.length+' zvuků';$('instrument-count').setAttribute('role','button');$('instrument-count').tabIndex=0;$('instrument-count').title='Prohledat knihovnu nástrojů';
  $('genre').innerHTML=Object.entries(familyNames).map(([family,name])=>`<optgroup label="${name}">${catalog.genres.filter(g=>g.family===family).map(g=>`<option value="${g.id}">${esc(g.name)}</option>`).join('')}</optgroup>`).join('');
  $('mood').innerHTML=catalog.moods.map(m=>`<option value="${m.id}">${esc(m.name)}</option>`).join('');
  $('key').insertAdjacentHTML('beforeend',['C','C#','D','D#','E','F','F#','G','G#','A','A#','B'].map(k=>`<option value="${k}">${k}</option>`).join(''));
  setSettings(catalog.default);renderMixer();drawWave();
  $('bank-summary').textContent=`${catalog.genres.length} stylů · ${catalog.moods.length} nálad · ${catalog.instruments.length} nástrojů, sad a presetů`;
  $('seed').value=randomSeed();
  updateAutoTitle(true);
  window.scrollTo(0,0);
 }catch(error){toast('Nelze načíst zvukovou knihovnu: '+error.message,true);return;}
 $('random-seed').addEventListener('click',()=>{$('seed').value=randomSeed();melodySeed=soundSeed=0;updateAutoTitle(true);markDirty();toast('Vybraný nový seed: '+$('seed').value);});$('seed').addEventListener('change',()=>{melodySeed=soundSeed=0;updateAutoTitle(true);});
 initSeedMenu({api,getSettings,getPlayed:()=>current?liveSettings():null,applySettings:applySavedSeed,toast});
 $('genre').addEventListener('change',genreChanged);$('mood').addEventListener('change',moodChanged);
 $('mood-chips').addEventListener('click',e=>{const b=e.target.closest('[data-mood]');if(b){$('mood').value=b.dataset.mood;moodChanged();}});
 document.querySelectorAll('[data-duration]').forEach(b=>b.addEventListener('click',()=>{lastWasPreview=false;setDuration(Number(b.dataset.duration));markDirty();}));
 for(const id of ['energy','complexity','variation','humanize','space'])$(id).addEventListener('input',()=>{ranges();if(id==='energy')updateAutoTitle();markDirty();});
 for(const id of ['minutes','seconds','bpm','key','seed','title'])$(id).addEventListener('change',()=>{if(id==='minutes'||id==='seconds'){lastWasPreview=false;syncDurationUI();}if(id==='title')syncDownloadLinks();markDirty();});
 for(const id of ['minutes','seconds'])$(id).addEventListener('input',()=>{lastWasPreview=false;syncDurationUI();markDirty();});
 $('bpm').addEventListener('input',()=>markDirty());
 $('seed').addEventListener('input',()=>{melodySeed=soundSeed=0;updateAutoTitle(true);markDirty();});
 $('title').addEventListener('input',()=>{customTitle=Boolean($('title').value.trim());syncDownloadLinks();markDirty();});
 $('generate').addEventListener('click',()=>generate('new'));$('generate-top').addEventListener('click',()=>generate('new'));$('preview').addEventListener('click',()=>generate('preview'));$('apply').addEventListener('click',()=>prepareExport());$('new-melody').addEventListener('click',()=>generate('melody'));$('new-sounds').addEventListener('click',()=>generate('sounds'));
 $('cancel').addEventListener('click',async()=>{try{await api('/api/cancel',{job:activeJob});$('cancel').disabled=true;$('progress-text').textContent='Dokončuji rozpracované stopy a ruším úlohu…';}catch(e){toast(e.message,true);}});
 $('play').addEventListener('click',togglePlay);$('stop').addEventListener('click',()=>{audio.pause();audio.currentTime=0;syncTransport();});$('back').addEventListener('click',()=>{audio.currentTime=Math.max(0,audio.currentTime-15);});$('forward').addEventListener('click',()=>{if(current)audio.currentTime=Math.min(current.plan.duration,audio.currentTime+15);});
 $('seek').addEventListener('input',()=>{if(current)audio.currentTime=Number($('seek').value)/1000*current.plan.duration;syncTransport();});$('volume').addEventListener('input',()=>audio.volume=Number($('volume').value)/100);
 $('arrangement').addEventListener('click',e=>{const b=e.target.closest('[data-seek]');if(b&&current){audio.currentTime=Number(b.dataset.seek);$('section-select').value=b.dataset.section;showSectionLevel();syncTransport();}});
 $('loop').addEventListener('click',()=>{audio.loop=!audio.loop;$('loop').classList.toggle('active',audio.loop);$('loop').setAttribute('aria-pressed',String(audio.loop));});
 for(const event of ['play','pause','timeupdate','ended','seeked'])audio.addEventListener(event,syncTransport);
 document.addEventListener('keydown',e=>{if(e.code==='Space'&&(!['INPUT','SELECT','TEXTAREA','BUTTON','SUMMARY'].includes(document.activeElement.tagName)||['generate','generate-top','preview','apply','new-melody','new-sounds'].includes(document.activeElement.id))){e.preventDefault();togglePlay();}});
 installCurveEditors($('mixer'),role=>mixOverrides[role]?.curve,(role,curve)=>{clearTrackUndo(role);mixOverrides[role].curve=curve;markDirty('audio');});
 $('mixer').addEventListener('input',e=>{const row=e.target.closest('.mixer-row');if(!row)return;const role=row.dataset.role,t=current.plan.tracks.find(t=>t.id===role);const m=mixOverrides[role]||(mixOverrides[role]={gain:t.gain,pan:t.pan,mute:t.mute,solo:t.solo});if(e.target.classList.contains('gain')){m.gain=Number(e.target.value)/100;e.target.nextElementSibling.textContent=e.target.value;}else if(e.target.classList.contains('pan')){m.pan=Number(e.target.value)/100;e.target.nextElementSibling.textContent=panLabel(m.pan);}else if(e.target.dataset.tone){const tone=toneOverrides[role]||(toneOverrides[role]={...t.tone});tone[e.target.dataset.tone]=Number(e.target.value)/100;e.target.previousElementSibling.querySelector('output').textContent=e.target.value+' %';}else return;clearTrackUndo(role);markDirty('audio');if(['attack','release'].includes(e.target.dataset.tone))queueTrack(role);});
 $('mixer').addEventListener('change',e=>{if(e.target.classList.contains('instrument-select')){const role=e.target.closest('.mixer-row').dataset.role;clearTrackUndo(role);instrumentOverrides[role]=e.target.value;trackDefaultGain(role,true);renderMixer();markDirty('audio');queueTrack(role);}});
 $('mixer').addEventListener('click',e=>{const row=e.target.closest('.mixer-row');if(!row||busy)return;const role=row.dataset.role,button=e.target.closest('button');if(!button)return;if(button.classList.contains('reset-track')){restoreTrack(role);return;}if(button.classList.contains('undo-track-reset')){restoreTrack(role,true);return;}if(button.classList.contains('edit-tone')){const p=row.querySelector('.tone-panel');p.hidden=!p.hidden;button.classList.toggle('active',!p.hidden);button.setAttribute('aria-expanded',String(!p.hidden));return;}if(button.classList.contains('reset-tone')){clearTrackUndo(role);toneOverrides[role]={brightness:.5,attack:.5,release:.5,drive:0,space:0};renderMixer();markDirty('audio');queueTrack(role);return;}for(const type of ['mute','solo'])if(button.classList.contains(type)){clearTrackUndo(role);mixOverrides[role][type]=!mixOverrides[role][type];button.classList.toggle('active',mixOverrides[role][type]);button.setAttribute('aria-pressed',String(mixOverrides[role][type]));markDirty('audio');}});
 $('save').addEventListener('click',downloadJSON);$('load').addEventListener('click',()=>$('project-file').click());$('project-file').addEventListener('change',async e=>{try{const file=e.target.files[0];if(!file)return;if(file.size>2*1024**2)throw Error('Projekt je příliš velký.');const s=validateProject(JSON.parse(await file.text()));applySavedSeed(s);$('lock-seed').checked=true;toast('Projekt načtený. Klikni na Vytvořit skladbu pro obnovu zvuku.');}catch(error){toast(error.message,true);}finally{e.target.value='';}});
 $('reset').addEventListener('click',()=>{const g=selectedGenre(),genre=g.id;customTitle=false;applySavedSeed({...catalog.default,genre,bpm:g.bpm});updateAutoTitle(true);toast('Doporučené nastavení obnovené.');});
 $('more-export').addEventListener('click',()=>{if(!current){toast('Nejdřív vytvoř skladbu.');return;}$('extra-exports').hidden=!$('extra-exports').hidden;});
 $('midi').addEventListener('click',()=>{if(!current)return;nextExportVersion(current.plan.settings.seed,'mid');queueMicrotask(syncDownloadLinks);});
 $('credits').addEventListener('click',()=>{if(!current)return;nextExportVersion(current.plan.settings.seed,'txt');queueMicrotask(syncDownloadLinks);});
 $('research-tab').addEventListener('click',showResearch);$('studio-tab').addEventListener('click',()=>{$('studio-view').hidden=false;$('research-view').hidden=true;$('studio-tab').classList.add('selected');$('research-tab').classList.remove('selected');drawWave();});
 $('instrument-count').addEventListener('click',openLibrary);$('instrument-count').addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();openLibrary();}});$('close-library').addEventListener('click',()=>$('instrument-library').close());$('library-role').innerHTML=roles.map(([id,name])=>`<option value="${id}">${name}</option>`).join('');$('library-role').value='lead';$('library-group').insertAdjacentHTML('beforeend',[...new Set(catalog.instruments.map(i=>i.group))].sort((a,b)=>a.localeCompare(b,'cs')).map(g=>`<option value="${esc(g)}">${esc(g)}</option>`).join(''));for(const id of ['library-role','library-group'])$(id).addEventListener('change',renderLibrary);$('library-search').addEventListener('input',renderLibrary);$('library-results').addEventListener('click',e=>{const b=e.target.closest('[data-instrument]');if(!b||busy)return;const role=$('library-role').value;clearTrackUndo(role);instrumentOverrides[role]=b.dataset.instrument;if(!current&&pendingRecipe)pendingRecipe.instruments[role]=b.dataset.instrument;if(current)trackDefaultGain(role,true);renderMixer();markDirty('audio');if(current)queueTrack(role);$('instrument-library').close();toast('Vybraný nástroj: '+catalog.instruments.find(i=>i.id===b.dataset.instrument).name);});
 for(const id of ['seed-library','instrument-library'])$(id).addEventListener('pointerdown',e=>{if(e.target!==e.currentTarget)return;const r=e.currentTarget.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)e.currentTarget.close();});
 $('section-select').addEventListener('change',showSectionLevel);$('section-level').addEventListener('input',()=>{sectionLevels[$('section-select').value]=Number($('section-level').value)/100;showSectionLevel();markDirty('audio');});
 $('show-peaks').addEventListener('change',drawWave);
 installHoverReset(document,resetDefault,control=>toast('Obnoveno: '+(control.getAttribute('aria-label')||control.labels?.[0]?.textContent?.trim()||'výchozí hodnota')));
 for(const id of ['wav','opus','wav-top','opus-top'])$(id).addEventListener('click',e=>{e.preventDefault();if(current&&!busy&&!exporting)prepareExport(id.startsWith('wav')?'wav':'opus');});
 setInterval(checkServerState,1200);checkServerState(true);
 $('research-search').addEventListener('input',renderResearch);$('research-tracks').addEventListener('toggle',e=>{if(e.target.matches('details[open]'))drawResearch(e.target);},true);
 new ResizeObserver(drawWave).observe($('waveform'));
}
function openLibrary(){if(busy)return;renderLibrary();$('instrument-library').showModal();$('library-search').focus();}
function renderLibrary(){
 const role=$('library-role').value,query=$('library-search').value.toLocaleLowerCase('cs').trim(),group=$('library-group').value;
 const selected=(!current&&pendingRecipe?.instruments?.[role])||instrumentOverrides[role]||current?.plan.tracks.find(t=>t.id===role)?.instrument;
 const matches=catalog.instruments.filter(i=>(i.bank===128)===(role==='drums')&&(group==='all'||i.group===group)&&(!query||(i.name+' '+i.group+' '+i.source).toLocaleLowerCase('cs').includes(query)));
 function priority(i){if(i.id===selected)return 10;if(role==='bass'&&(i.group==='Basy'||['bass','sub','growl','reese','acid'].includes(i.kind)))return 5;if(role==='pad'&&(i.group==='Synth pad'||i.kind==='pad'||i.group==='Ensemble'))return 5;if(role==='arp'&&(i.group==='Chromatické perkuse'||i.kind==='pluck'))return 5;if(role==='fx'&&(i.group==='Efekty'||i.kind==='noise'))return 5;if(['lead','chords','counter'].includes(role)&&['Piano','Kytary','Smyčce','Moderní syntéza'].includes(i.group))return 3;return 0;}
 matches.sort((a,b)=>priority(b)-priority(a)||a.name.localeCompare(b.name));
 $('library-results').innerHTML=matches.length?matches.map(i=>`<button class="library-sound ${i.id===selected?'selected':''}" data-instrument="${esc(i.id)}"><span><strong>${esc(i.name)}</strong><small>${esc(i.group)} · ${esc(i.source)}</small></span><span>${i.id===selected?'Vybraný':'Vybrat →'}</span></button>`).join(''):'<p class="muted">Tomuto hledání neodpovídá žádný nástroj v této kategorii.</p>';
}

function chosenSeed(){const text=$('seed').value.trim(),value=Number(text);if(!text||!Number.isInteger(value)||value<0||value>2147483647)throw Error('Seed musí být celé číslo od 0 do 2147483647.');return value;}
function applySavedSeed(settings){const playing=current?{instruments:instrumentOverrides,mix:mixOverrides,tone:toneOverrides,levels:sectionLevels}:null;setSettings(settings);pendingRecipe={instruments:structuredClone(settings.instruments||{}),mix:structuredClone(settings.mix||{}),tone:structuredClone(settings.tone||{}),section_levels:{...(settings.section_levels||{})}};if(playing){instrumentOverrides=playing.instruments;mixOverrides=playing.mix;toneOverrides=playing.tone;sectionLevels=playing.levels;}else renderMixer();markDirty();setBusy(busy);}
function currentTrackState(role){const t=current.plan.tracks.find(t=>t.id===role);return {instrument:instrumentOverrides[role]||t.instrument,mix:structuredClone(mixOverrides[role]),tone:structuredClone(toneOverrides[role])};}
function clearTrackUndo(role){trackResetUndo.delete(role);const button=document.querySelector(`.mixer-row[data-role="${role}"] .undo-track-reset`);if(button)button.hidden=true;}
function restoreTrack(role,undo=false){
 if(busy||!stemsReady)return;const target=undo?trackResetUndo.get(role):originalTracks.get(role);if(!target)return;
 const previous=currentTrackState(role);if(JSON.stringify(previous)===JSON.stringify(target)){toast('Stopa už odpovídá původnímu nastavení.');return;}
 if(undo)trackResetUndo.delete(role);else trackResetUndo.set(role,previous);
 const next=structuredClone(target);instrumentOverrides[role]=next.instrument;mixOverrides[role]=next.mix;toneOverrides[role]=next.tone;
 renderMixer();markDirty('audio');queueTrack(role);toast(undo?'Reset stopy vrácen.':'Celá stopa obnovená podle původně vygenerované skladby. Tlačítkem Zpět můžeš reset vrátit.');
}
function trackDefaultGain(role,apply=false){const track=current?.plan.tracks.find(t=>t.id===role);if(!track)return 1;const instrument=catalog.instruments.find(i=>i.id===(instrumentOverrides[role]||track.instrument)),base={drums:.75,bass:.8,chords:.54,lead:.65,counter:.32,pad:.31,arp:.3,fx:.28}[role],recommended=Math.min(base,gainLimit(instrument,role,track.notes));if(apply){const mix=mixOverrides[role]||(mixOverrides[role]={gain:track.gain,pan:track.pan,mute:track.mute,solo:track.solo});mix.gain=recommended;}return recommended;}
function liveSettings(){return {...structuredClone(current.plan.settings),title:$('title').value.trim()||current.plan.title,instruments:{...current.plan.settings.instruments,...instrumentOverrides},mix:structuredClone(mixOverrides),tone:structuredClone(toneOverrides),section_levels:{...sectionLevels}};}
function resetDefault(control){
 const row=control.closest('.mixer-row'),track=row&&current?.plan.tracks.find(t=>t.id===row.dataset.role);
 if(track){
  if(control.classList.contains('gain'))return Math.round(trackDefaultGain(track.id)*100);
  if(control.classList.contains('pan'))return Math.round((track.seed_default?.pan??track.pan)*100);
  if(control.dataset.tone)return ['brightness','attack','release'].includes(control.dataset.tone)?50:0;
  if(control.classList.contains('instrument-select'))return track.seed_default?.instrument??track.instrument;
  if(control.classList.contains('mute')||control.classList.contains('solo'))return false;
 }
 const fixed={minutes:3,seconds:30,volume:80,seek:0,'section-level':100,'section-select':'0',key:'auto','lock-seed':false,'show-peaks':false,loop:false,'library-role':'lead','library-group':'all'};
 if(Object.hasOwn(fixed,control.id))return fixed[control.id];
 if(control.id==='title'){customTitle=false;return generateTitle(catalog,$('genre').value,$('mood').value,Number($('seed').value)||catalog.default.seed,Number($('energy').value)/100);}
 if(control.id==='bpm')return selectedGenre().bpm;
 if(control.id==='energy')return Math.round((catalog.moods.find(m=>m.id===$('mood').value)||catalog.moods[0]).energy*100);
 if(['complexity','variation','humanize','space'].includes(control.id))return Math.round(catalog.default[control.id]*100);
 if(control.id==='seed')return catalog.startup_seed??catalog.default.seed;if(['genre','mood'].includes(control.id))return catalog.default[control.id];
}
function showSectionLevel(){const i=$('section-select').value,value=Math.round((sectionLevels[i]??1)*100);$('section-level').value=value;$('section-level-value').textContent=value+' %';}
function queueTrack(role){
 clearTimeout(trackTimers.get(role));const record=audio.records.get(role);if(record)record.version=(record.version||0)+1;
 const targetProject=project;
 trackTimers.set(role,setTimeout(()=>{trackTimers.delete(role);if(project!==targetProject||busy)return;
  const t=current.plan.tracks.find(t=>t.id===role),instrument=instrumentOverrides[role]||t.instrument;
  $('mix-status').textContent=`Načítám nový zvuk: ${t.name}…`;document.querySelector(`.mixer-row[data-role="${role}"]`)?.classList.add('loading-track');
  const task=audio.replaceTrack(role,instrument,toneOverrides[role]).then(changed=>{if(changed&&project===targetProject){$('mix-status').textContent='Nový zvuk hraje ve stejném místě skladby.';liveRevision++;cachedLive=null;waveChangeAt=performance.now();scheduleQuickWave();scheduleLiveWave(0);trackViews.refresh();}}).catch(e=>{if(project===targetProject&&trackPromises.get(role)===task){const record=audio.records.get(role);if(record){instrumentOverrides[role]=record.track.instrument;if(record.bufferKey){const key=JSON.parse(record.bufferKey);toneOverrides[role].attack=key[2];toneOverrides[role].release=key[3];}renderMixer();markDirty('audio');}$('mix-status').textContent='Změna se nepodařila. Hraje předchozí zvuk stopy.';toast(e.message,true);}}).finally(()=>{if(trackPromises.get(role)===task){trackPromises.delete(role);document.querySelector(`.mixer-row[data-role="${role}"]`)?.classList.remove('loading-track');trackViews.refresh();}});
  trackPromises.set(role,task);trackTimers.delete(role);
 },35));
}
async function settleTracks(){while(trackTimers.size||trackPromises.size){await new Promise(r=>setTimeout(r,80));await Promise.all([...trackPromises.values()]);}}
function scheduleLiveWave(delay=32){waveRequested=true;clearTimeout(waveTimer);waveTimer=setTimeout(refreshLiveWave,delay);}
function scheduleQuickWave(){
 if(quickWaveQueued||!stemsReady||!current)return;quickWaveQueued=true;const identity=project;
 queueMicrotask(()=>{quickWaveQueued=false;if(identity!==project||!stemsReady)return;const start=performance.now();quickWave=audio.quickWaveform();drawWave();$('waveform').dataset.waveQuality='preview';$('waveform').dataset.previewRevision=String(liveRevision);$('waveform').dataset.previewLatencyMs=String(Math.round(performance.now()-waveChangeAt));$('waveform').dataset.previewComputeMs=String(Math.round(performance.now()-start));});
}
async function refreshLiveWave(){
 if(!current||!stemsReady||busy||exporting||waveRunning)return;waveRequested=false;
 if(trackTimers.size||trackPromises.size){waveRequested=true;return;}
 const revision=liveRevision,identity=project,serial=++waveSerial;waveRunning=true;
 try{const snapshot=await audio.snapshot();const rendered=await audio.renderSnapshot(snapshot);if(identity!==project||revision!==liveRevision||serial!==waveSerial)return;
  cachedLive={...rendered,revision,project:identity,snapshot};audio.rememberWaveform(rendered,snapshot);quickWave=null;Object.assign(current.render.master,{waveform:rendered.waveform,rms_waveform:rendered.rms_waveform,peak_dbfs:rendered.peak_dbfs});$('render-meta').textContent=`${current.render.render_seconds.toFixed(1)} s tvorby · ${rendered.peak_dbfs<-100?'ticho':rendered.peak_dbfs.toFixed(1)+' dBFS peak'}`;drawWave();$('waveform').dataset.waveQuality='exact';
  $('waveform').dataset.waveRevision=String(revision);$('waveform').dataset.waveLatencyMs=String(Math.round(waveChangeAt?performance.now()-waveChangeAt:0));
 }catch(e){toast('Průběh mixu: '+e.message,true);}finally{waveRunning=false;if(waveRequested&&!busy&&!exporting)scheduleLiveWave(0);}
}
async function prepareExport(format){
 if(!current||busy||exporting)return;
 if(format&&activeExportId&&!dirty&&preparedUnclaimed){
  preparedUnclaimed=false;
  const liveTitle=$('title').value.trim()||current.plan.title||'Nová skladba',seed=current.plan.settings.seed;
  const a=document.createElement('a');a.href=`/export/${project}/${activeExportId}.${format}?title=${encodeURIComponent(liveTitle)}&version=${activeExportVersion}`;a.download=downloadName(liveTitle,format,seed,activeExportVersion);a.click();
  return;
 }
 exporting=true;setBusy(false);const identity=project,token=++generationToken;let revision=liveRevision;
 try{
  $('progress-box').hidden=false;$('progress').value=.03;$('progress-text').textContent='Připravuji přesný aktuální mix…';await audio.ready;await settleTracks();
  const snapshot=await audio.snapshot();revision=liveRevision;const frozenSettings={...structuredClone(current.plan.settings),title:$('title').value.trim()||current.plan.title||'Nová skladba',instruments:Object.fromEntries(snapshot.tracks.map(r=>[r.track.id,r.track.instrument])),mix:Object.fromEntries(snapshot.tracks.map(r=>[r.track.id,{gain:r.track.gain,pan:r.track.pan,mute:r.track.mute,solo:r.track.solo,curve:r.track.curve||flatCurve()}])),tone:Object.fromEntries(snapshot.tracks.map(r=>[r.track.id,r.track.tone])),section_levels:snapshot.levels};
  const ver=nextExportVersion(frozenSettings.seed,'audio');
  let rendered=cachedLive&&cachedLive.revision===revision&&cachedLive.project===identity?cachedLive:await audio.renderSnapshot(snapshot);
  const body=await exportBody(rendered.buffer,{settings:frozenSettings,version:ver});const request_id=crypto.randomUUID().replaceAll('-','');
  const response=await fetch(`/api/export?project=${identity}&request_id=${request_id}`,{method:'POST',body});const result=await response.json();if(!response.ok)throw Error(result.error);activeJob=result.job;
  const status=await waitJob(result.job,token);if(!status||status.state!=='done')throw Error(status?.message||'Export se nepodařil.');
  const exported=await api('/api/result?job='+result.job);if(identity!==project)return;
  activeExportId=result.job;activeExportVersion=exported.export_version||ver;preparedUnclaimed=!format;syncDownloadLinks();
  if(liveRevision===revision){dirty=false;quickWave=null;audio.rememberWaveform(rendered,snapshot);current.render.master=exported.render.master;$('apply').disabled=true;drawWave();}
  $('mix-status').textContent=liveRevision===revision?'WAV i Opus odpovídají aktuálnímu živému mixu.':'Export je hotový. Živý mix mezitím obsahuje další změny.';
  if(format){const a=document.createElement('a');a.href=`/export/${identity}/${result.job}.${format}?title=${encodeURIComponent(frozenSettings.title)}&version=${activeExportVersion}`;a.download=downloadName(frozenSettings.title,format,frozenSettings.seed,activeExportVersion);a.click();}else toast('WAV i Opus jsou připravené v obou nabídkách exportu.');
 }catch(e){toast(e.message,true);}finally{exporting=false;activeJob=null;setBusy(false);if(waveRequested)scheduleLiveWave(0);}
}
let checkingState=false,externalBusy=false;
async function checkServerState(){
 if(checkingState||exporting||activeJob)return;checkingState=true;
 try{const state=await api('/api/state');if(state.active&&!busy){externalBusy=true;setBusy(true);$('progress-text').textContent='Probíhá úloha otevřená v jiné kartě…';}else if(!state.active&&externalBusy){externalBusy=false;setBusy(false);}}catch{}finally{checkingState=false;}
}

init();
