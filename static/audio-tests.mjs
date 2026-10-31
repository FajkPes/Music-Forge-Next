import {curveEditor,paintCurveEditors,installCurveEditors} from './volume-curve.mjs';
import {trackState} from './track-state.mjs';
import {buildGraph,waveform,repairLegacyTail,renderTrackSnapshot,LiveMixer} from './live-mixer.mjs';
import {installHoverReset} from './control-reset.mjs';
import {WavePreview} from './wave-preview.mjs';
import {gainLimit,downloadName,generateTitle} from './mix-balance.mjs';
import {BufferCache,bufferKey} from './buffer-cache.mjs';
const output=document.getElementById('results');
const rms=(x,a=0,b=x.length)=>{let sum=0;for(let i=a;i<b;i++)sum+=x[i]*x[i];return Math.sqrt(sum/Math.max(1,b-a));};
const tone={brightness:.5,attack:.5,release:.5,drive:0,space:0};
async function render(change={},options={}){
 const ctx=new OfflineAudioContext(2,48000*3,48000),plan={family:'house',duration:3,sections:[{start:0,duration:1.5,kind:'intro'},{start:1.5,duration:1.5,kind:'chorus'}]};
 const t={id:'lead',gain:1,pan:0,mute:false,solo:false,tone:{...tone,...change.tone},...change};
 const tracks=[t];if(options.cancel)tracks.push({...t,id:'counter'});
 const graph=buildGraph(ctx,tracks,plan,0,options.levels||{},true,true,options.prune??true);
 for(const [j,track]of tracks.entries()){
  if(!graph.channels.has(track.id))continue;
  const buffer=ctx.createBuffer(2,48000*3,48000);
  for(let ch=0;ch<2;ch++){const x=buffer.getChannelData(ch);for(let i=0;i<x.length;i++){if(options.short&&i>14400)continue;const a=i/48000;x[i]=(j?-1:1)*(.07*Math.sin(a*2*Math.PI*220)+.06*Math.sin(a*2*Math.PI*4000));}}
  const source=ctx.createBufferSource();source.buffer=buffer;source.connect(graph.channels.get(track.id).input);source.start(0);
 }const buffer=await ctx.startRendering();graph.disconnect();return buffer;
}
function resetChecks(check){
 const area=document.createElement('div');area.innerHTML='<input id="reset-a" type="range" value="20"><input id="reset-b" type="range" value="10"><input id="reset-disabled" type="range" value="10" disabled><input id="reset-text" type="text" value="Neon"><select id="reset-select"><option value="a">A</option><option value="b" selected>B</option></select><input id="reset-check" type="checkbox" checked>';
 document.body.append(area);const a=area.querySelector('#reset-a'),b=area.querySelector('#reset-b');
 let inputs=0,changes=0;b.addEventListener('input',()=>inputs++);b.addEventListener('change',()=>changes++);
 const dispose=installHoverReset(document,el=>el.type==='checkbox'?false:el.tagName==='SELECT'?'a':67);
 const hover=el=>el.dispatchEvent(new PointerEvent('pointerover',{bubbles:true}));
 const backspace=options=>{const event=new KeyboardEvent('keydown',{key:'Backspace',bubbles:true,cancelable:true,...options});document.dispatchEvent(event);return event.defaultPrevented;};
 try{
  a.focus();hover(b);check('Backspace obnoví ovladač pod kurzorem',backspace()&&b.value==='67'&&a.value==='20'&&document.activeElement===a&&inputs===1&&changes===1,'jiný fokus, jeden input a change');
  b.value='12';hover(b);backspace({ctrlKey:true});check('Zkratka respektuje modifikátory',b.value==='12','Ctrl+Backspace beze změny');
  area.querySelector('#reset-text').focus();hover(b);check('Psaní textu zůstává nedotčené',!backspace()&&b.value==='12','název skladby ani hledání se neresetují');
  a.focus();const disabled=area.querySelector('#reset-disabled');hover(disabled);check('Zakázaný ovladač se neresetuje',!backspace()&&disabled.value==='10','během načítání a generování');
  hover(b);b.dispatchEvent(new PointerEvent('pointerout',{bubbles:true}));check('Opuštění ovladače vypne reset',!backspace()&&b.value==='12','bez závislosti na starém fokusu');
  const select=area.querySelector('#reset-select');hover(select);backspace();const box=area.querySelector('#reset-check');hover(box);backspace();check('Reset funguje i na výběrech a přepínačích',select.value==='a'&&!box.checked,'doporučená položka a výchozí stav');
 }finally{dispose();area.remove();}
}
async function monitorChecks(check){
 const buffer=new AudioBuffer({numberOfChannels:2,length:144000,sampleRate:48000});
 for(let ch=0;ch<2;ch++){const data=buffer.getChannelData(ch);for(let i=0;i<data.length;i++)data[i]=.05*Math.sin(i*2*Math.PI*220/48000)+.05*Math.sin(i*2*Math.PI*4000/48000);}
 const plan={family:'house',duration:3,sections:[{start:0,duration:1.5,kind:'intro',name:'Úvod'},{start:1.5,duration:1.5,kind:'chorus',name:'Vrchol'}]};
 const track={id:'lead',instrument:'syn:silk-pluck',gain:.8,pan:0,mute:false,solo:false,tone,curve:[[0,1],[1,1]]};
 const snapshot=(changes={},levels={})=>({plan,tracks:[{track:{...track,...changes},buffer}],levels,baked:true});
 const energy=wave=>Math.sqrt(wave.rms_waveform.reduce((n,v)=>n+v*v,0)/wave.rms_waveform.length);
 const full=await renderTrackSnapshot(snapshot(),'lead'),half=await renderTrackSnapshot(snapshot({gain:.4}),'lead');
 check('Průběh samostatné stopy zachovává skutečnou hlasitost',Math.abs(energy(half)/energy(full)-.5)<1e-5,'poloviční gain = poloviční RMS bez normalizace');
 const gated=await renderTrackSnapshot(snapshot({curve:[[0,0],[.45,0],[.55,1],[1,1]]}),'lead');
 check('Přesný průběh stopy respektuje body křivky',Math.max(...gated.rms_waveform.slice(0,200))===0&&Math.max(...gated.rms_waveform.slice(400))>0,'tichý začátek, slyšitelný konec');
 const solo=snapshot();solo.tracks.push({track:{...track,id:'bass',solo:true},buffer});
 check('Průběh respektuje sólo jiné stopy',energy(await renderTrackSnapshot(solo,'lead'))===0,'neslyšitelná stopa má nulový průběh');
 const sections=await renderTrackSnapshot(snapshot({}, {'0':0,'1':1}),'lead');
 check('Průběh stopy respektuje hlasitost částí',Math.max(...sections.rms_waveform.slice(0,200))===0&&energy(sections)>0,'úvod 0 %, vrchol 100 %');
 const filtered=await renderTrackSnapshot(snapshot({tone:{...tone,brightness:.02}}),'lead');
 check('Přesný průběh obsahuje efekty nástroje',energy(filtered)<energy(full)*.85,'energie po skutečném filtru');
 const record={track:{...track},buffer},preview=new WavePreview(plan,0,true,600,48,false);preview.setReference(full,[record],{});record.track.gain=.2;const quick=preview.render([record],{});
 check('Živý náhled stopy reaguje na čtvrtinovou hlasitost',Math.abs(energy(quick)/energy(full)-.25)<1e-5,'pevné měřítko, stejná textura průběhu');
 const originalBuffer=buffer,recordState={track:{...track,tone:{...tone}},buffer:originalBuffer,bufferKey:bufferKey(track)},fake={loadEpoch:1,records:new Map([['lead',recordState]]),bufferCache:new BufferCache(),paused:true,trackURL:async()=>{throw Error('Test selhání');}};
 let failed=false;try{await LiveMixer.prototype.replaceTrack.call(fake,'lead','failed',tone);}catch{failed=true;}
 check('Selhání výměny zachová původní zvuk',failed&&recordState.buffer===originalBuffer&&recordState.track.instrument===track.instrument,'přehrávání má stále původní buffer');
 let releaseOld;fake.trackURL=()=>new Promise(resolve=>releaseOld=resolve);fake.decode=async()=>originalBuffer;
 const oldRequest=LiveMixer.prototype.replaceTrack.call(fake,'lead','slow',tone),cached={...track,instrument:'cached',tone};fake.bufferCache.put(bufferKey(cached),originalBuffer);
 await LiveMixer.prototype.replaceTrack.call(fake,'lead','cached',tone);releaseOld('/test.wav');const obsolete=await oldRequest;
 check('Opožděný zvuk nepřepíše poslední výběr',obsolete===false&&recordState.track.instrument==='cached','nová volba z cache má přednost');
 const original=trackState(track);original.mix.curve[0][1]=0;original.tone.brightness=0;
 check('Výchozí stav resetu je nezávislý na dalších editacích',track.curve[0][1]===1&&track.tone.brightness===.5,'vlastní kopie křivky i zvukových parametrů');
 const root=document.createElement('div');root.innerHTML=curveEditor('lead');document.body.append(root);root.querySelector('details').open=true;let points=[[0,1],[.5,.8],[1,1]],writes=0;
 installCurveEditors(root,()=>points,(_,value)=>{points=value;writes++;});paintCurveEditors(root,()=>points,plan,{intro:'#123456',chorus:'#abcdef'});
 const svg=root.querySelector('svg');
 try{
  check('Editor používá barvy obou částí skladby',svg.querySelectorAll('.curve-section-bands rect').length===2&&svg.querySelector('.curve-section-bands rect').getAttribute('fill')==='#123456','stejná časová osa jako zvuk');
  svg.querySelector('[data-point="1"]').focus();svg.dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowDown',bubbles:true,cancelable:true}));
  check('Bod lze přesně doladit klávesnicí',Math.abs(points[1][1]-.79)<1e-7,'šipka upraví hlasitost o 1 %');
  svg.querySelector('[data-point="0"]').focus();svg.dispatchEvent(new KeyboardEvent('keydown',{key:'Delete',bubbles:true,cancelable:true}));
  check('Krajní bod nejde omylem odstranit',points.length===3&&points[0][0]===0,'zachovaný začátek skladby');
  root.setAttribute('aria-busy','true');const before=writes;svg.dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowUp',bubbles:true,cancelable:true}));
  check('Editor se během generování nemění',writes===before,'respektuje blokování mixu');root.setAttribute('aria-busy','false');
  root.insertAdjacentHTML('beforeend',curveEditor('bass'));root.querySelector('[data-curve-role="bass"]').open=true;paintCurveEditors(root,()=>points,plan,{intro:'#123456',chorus:'#abcdef'});
  svg.querySelector('[data-point="1"]').focus();const other=root.querySelector('[data-curve-role="bass"] svg');other.focus();other.dispatchEvent(new KeyboardEvent('keydown',{key:'Delete',bubbles:true,cancelable:true}));
  const level=root.querySelector('.curve-point-level');level.focus();level.value='35';level.dispatchEvent(new Event('input',{bubbles:true}));
  check('Body různých stop si drží vlastní výběr',points.length===3&&points[1][1]===.35,'Delete v druhé stopě nesmaže bod; číselná editace pokračuje v první');
 }finally{root.remove();}
}
async function benchmark(duration){
 const buffer=new AudioBuffer({numberOfChannels:2,length:48000*duration,sampleRate:48000});
 for(let ch=0;ch<2;ch++){const x=buffer.getChannelData(ch);for(let i=0;i<x.length;i++)x[i]=.04*Math.sin(i/48000*2*Math.PI*(220+ch*110));}
 const plan={family:'house',duration,sections:[{kind:'intro',start:0,duration:duration/2},{kind:'chorus',start:duration/2,duration:duration/2}]};
 const tracks=Array.from({length:8},(_,i)=>({id:'t'+i,gain:.3,pan:(i-4)/10,mute:false,solo:false,tone}));
 const monitorStart=performance.now(),trackWave=await renderTrackSnapshot({plan,tracks:tracks.map(track=>({track,buffer})),levels:{},baked:true},'t0'),trackWaveMs=performance.now()-monitorStart;
 const one=async prune=>{const start=performance.now(),ctx=new OfflineAudioContext(2,buffer.length,48000),graph=buildGraph(ctx,tracks,plan,0,{},true,true,prune);for(const t of tracks){const source=ctx.createBufferSource();source.buffer=buffer;source.connect(graph.channels.get(t.id).input);source.start();}const result=await ctx.startRendering();graph.disconnect();return {buffer:result,ms:performance.now()-start};};
 const full=await one(false),fast=await one(true);let difference=0;
 for(let ch=0;ch<2;ch++){const a=full.buffer.getChannelData(ch),b=fast.buffer.getChannelData(ch);for(let i=0;i<a.length;i++)difference=Math.max(difference,Math.abs(a[i]-b[i]));}
 const records=tracks.map(track=>({track:{...track},buffer})),exact=waveform(fast.buffer),preview=new WavePreview(plan,0,true),firstStart=performance.now();preview.setReference(exact,records,{});preview.render(records,{});const firstMs=performance.now()-firstStart;
 for(const r of records)r.track.gain*=.5;
 const quickStart=performance.now(),quick=preview.render(records,{}),quickMs=performance.now()-quickStart;
 let rmsError=0;for(let i=0;i<quick.rms_waveform.length;i++)rmsError=Math.max(rmsError,Math.abs(quick.rms_waveform[i]-exact.rms_waveform[i]*.5));
 for(const r of records)r.track.mute=true;const silent=preview.render(records,{}).rms_waveform.every(x=>x===0);
 return {duration,track_wave_ms:Math.round(trackWaveMs),track_wave_valid:trackWave.rms_waveform.length>=590&&trackWave.rms_waveform.every(Number.isFinite)&&trackWave.rms_waveform.some(v=>v>0),full_ms:Math.round(full.ms),fast_ms:Math.round(fast.ms),old_update_ms:Math.round(full.ms+650),new_exact_update_ms:Math.round(fast.ms+140),max_sample_difference:difference,preview_first_ms:Math.round(firstMs),preview_update_ms:Math.round(quickMs),preview_half_gain_max_rms_error:rmsError,preview_silence:silent};
}
async function tailCheck(){
 const raw={family:'house',duration:3,sections:[{kind:'outro',start:0,duration:2.5}]};
 const one=async repair=>{
  const plan=repair?repairLegacyTail(raw,{arrangement_gain_baked:true}):raw,ctx=new OfflineAudioContext(2,144000,48000),t={id:'lead',gain:1,pan:0,tone};
  const graph=buildGraph(ctx,[t],plan,0,{},true,true),buffer=ctx.createBuffer(2,144000,48000);
  for(let ch=0;ch<2;ch++){const data=buffer.getChannelData(ch);for(let i=0;i<data.length;i++)data[i]=.04*Math.sin(i/48000*2*Math.PI*440)*(i<120000?10**(-6/20):1);}
  const source=ctx.createBufferSource();source.buffer=buffer;source.connect(graph.channels.get('lead').input);source.start();const result=await ctx.startRendering();graph.disconnect();const x=result.getChannelData(0);return 20*Math.log10(rms(x,127200,136800)/rms(x,110400,117600));
 };return {before:await one(false),after:await one(true)};
}
document.getElementById('run').addEventListener('click',async()=>{
 document.getElementById('run').disabled=true;output.textContent='Kontroluji…\n';let passed=0;
 const check=(name,test,details)=>{if(!test)throw Error(name+' — '+details);passed++;output.textContent+=`✓ ${name} · ${details}\n`;};
 try{
  resetChecks(check);
  await monitorChecks(check);
  const cache=new BufferCache(32),cacheA={length:2,numberOfChannels:2},cacheB={length:3,numberOfChannels:2};cache.put('a',cacheA);const reused=cache.get('a')===cacheA;cache.put('b',cacheB);
  check('Cache vrací stejný dekódovaný zvuk a hlídá paměť',reused&&!cache.get('a')&&cache.get('b')===cacheB&&cache.bytes===24&&bufferKey({id:'lead',instrument:'a',tone})!==bufferKey({id:'lead',instrument:'a',tone:{...tone,attack:.7}}),'LRU, limit paměti, oddělené obálky');
  const catalogue=await(await fetch('/api/catalogue')).json(),instrument=id=>catalogue.instruments.find(i=>i.id===id);
  check('Výchozí hodnoty jasných presetů',gainLimit(instrument('syn:silk-pluck'),'lead')===.5&&gainLimit(instrument('syn:glass-pluck'),'lead')===.2&&gainLimit(instrument('syn:arp'),'arp')===.25&&gainLimit(instrument('sf:0:11'),'lead')===.5&&gainLimit(instrument('ms:0:34'),'bass')===.2,'Silk 50 %, Glass 20 %, Orbit 25 %, Vibraphone 50 %, Picked Bass 20 %');
  check('Název exportu se seedem',downloadName('Moje píseň','opus',123)==='Moje píseň (123).opus'&&downloadName('Moje píseň','opus',123,2)==='Moje píseň (123) v2.opus'&&downloadName('Moje píseň','opus',123,3)==='Moje píseň (123) v3.opus'&&generateTitle(catalogue,'melodic-house','uplifting',431207,.68).split(' ').length===2,'Unicode název, skutečný seed, v2/v3 a generátor názvů 20×20');
  const ending=await tailCheck();check('Oprava hlasitého konce starších skladeb',ending.before>5.9&&Math.abs(ending.after)<.05,`skok ${ending.before.toFixed(2)} dB → ${ending.after.toFixed(2)} dB`);
  const base=await render(),b=rms(base.getChannelData(0));
  const envelope=await render({curve:[[0,0],[.45,0],[.55,1],[1,1]]});check('Bodová křivka mění skutečný zvuk',rms(envelope.getChannelData(0),1000,50000)<1e-7&&rms(envelope.getChannelData(0),90000,135000)>b*.9,'tichý začátek, slyšitelný konec');
  const manual=await render({gain:1.2});check('Vyšší ruční hlasitost zůstává volná',Math.abs(rms(manual.getChannelData(0))/b-1.2)<.015,'120 % se nevrací na doporučenou hodnotu');
  const half=await render({gain:.5});const ratio=rms(half.getChannelData(0))/b;check('Hlasitost mění skutečné PCM',Math.abs(ratio-.5)<.015,ratio.toFixed(5));
  const mute=await render({mute:true});check('Mute zcela ztlumí stopu',rms(mute.getChannelData(0))<1e-8,'nulový signál');
  const pan=await render({pan:-1});check('Panorama vlevo',rms(pan.getChannelData(1))<1e-7&&rms(pan.getChannelData(0))>b,'pravý kanál tichý');
  const dark=await render({tone:{...tone,brightness:.05}});check('Jas ovlivňuje spektrum',rms(dark.getChannelData(0))<b*.85,'výšky potlačeny');
  const driven=await render({tone:{...tone,drive:.9}});let diff=0;const d=driven.getChannelData(0),x=base.getChannelData(0);for(let i=0;i<x.length;i++)diff+=(x[i]-d[i])**2;check('Sytost mění zvuk',Math.sqrt(diff/x.length)>.001,'nelineární zpracování');
  const space=await render({tone:{...tone,space:.9}},{short:true});check('Prostor vytváří skutečný dozvuk',rms(space.getChannelData(0),24000,36000)>1e-5,'energie za koncem tónu');
  const levels=await render({}, {levels:{'0':0,'1':1}});check('Hlasitost částí je automatizovaná',rms(levels.getChannelData(0),1000,50000)<1e-7&&rms(levels.getChannelData(0),85000,130000)>.01,'úvod 0 %, vrchol 100 %');
  const sync=await render({}, {cancel:true});check('Stopy jsou vzorkově synchronní',rms(sync.getChannelData(0))<1e-7,'opačné fáze se vyruší');
  for(const change of [{},{tone:{...tone,drive:.6}},{tone:{...tone,space:.7}},{tone:{...tone,brightness:.12,drive:.4,space:.3}}]){
   const full=await render(change,{prune:false}),fast=await render(change);let difference=0;
   for(let ch=0;ch<2;ch++){const x=full.getChannelData(ch),y=fast.getChannelData(ch);for(let i=0;i<x.length;i++)difference=Math.max(difference,Math.abs(x[i]-y[i]));}
   check('Rychlý výpočet zachovává zvuk',difference<1e-6,`max. rozdíl vzorku ${difference.toExponential(2)}`);
  }
  const timings=[];for(const duration of [30,210]){const result=await benchmark(duration);timings.push(result);check('Přesný průběh samostatné stopy '+duration+' s',result.track_wave_valid,`${result.track_wave_ms} ms, skutečné PCM po efektech`);check('Přesný průběh '+duration+' s / 8 stop',result.max_sample_difference<1e-6,`původní ${result.old_update_ms} ms → ${result.new_exact_update_ms} ms, PCM rozdíl ${result.max_sample_difference.toExponential(2)}`);check('Okamžitý průběh '+duration+' s / 8 stop',result.preview_half_gain_max_rms_error<1e-6,`${result.preview_update_ms} ms, poloviční gain odpovídá poloviční RMS`);check('Rychlý průběh po ztlumení',result.preview_silence,'nulový signál bez původního obrysu');}
  document.getElementById('timings').textContent=JSON.stringify(timings,null,2);
  output.textContent+=`\nHOTOVO: ${passed}/46 kontrol prošlo.`;document.body.dataset.result='passed';
 }catch(error){output.textContent+='\nCHYBA: '+error.message;document.body.dataset.result='failed';}
 finally{document.getElementById('run').disabled=false;}
});
