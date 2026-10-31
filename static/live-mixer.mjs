import {automateCurve} from './volume-curve.mjs';
import {BufferCache,bufferKey} from './buffer-cache.mjs';
// One playback clock, independent stems, and the same graph for listening/export.
import {WavePreview} from './wave-preview.mjs';
export const SECTION_COLOURS={intro:'#8fada4',verse:'#72b6a8',verseB:'#8abccc',build:'#c2ad77',chorus:'#b5a0e3',final:'#c1a6ef',bridge:'#789ba8',outro:'#83988c'};
const DANCE={intro:-5,verse:-2.5,verseB:-2,build:-2,chorus:0,final:.3,bridge:-5.5,outro:-6};
const SOFT={intro:-2,verse:-.8,verseB:-.6,build:-.5,chorus:0,final:.3,bridge:-2.5,outro:-3};
const smooth=(p,value,ctx,offline=false)=>{if(offline)p.setValueAtTime(value,0);else p.setTargetAtTime(value,ctx.currentTime,.012);};
const curve=(fn)=>{const a=new Float32Array(32768);for(let i=0;i<a.length;i++)a[i]=fn(i/(a.length-1)*2-1);return a;};
const SAT=curve(Math.tanh),LIMIT=curve(x=>Math.max(-.79,Math.min(.79,x)));

function impulse(ctx){const b=ctx.createBuffer(2,Math.round(ctx.sampleRate*.9),ctx.sampleRate);let seed=113;
 for(let ch=0;ch<2;ch++){const x=b.getChannelData(ch);for(let i=0;i<x.length;i++){seed=(Math.imul(seed,1664525)+1013904223)|0;x[i]=(seed/2147483648)*Math.exp(-i/(ctx.sampleRate*.17));}}return b;}

export function setChannel(node,track,solo,offline=false){
 const c=node.ctx,t=track.tone||{},brightness=t.brightness??.5,drive=t.drive||0;
 smooth(node.gain.gain,track.mute||(solo&&!track.solo)?0:track.gain,c,offline);
 smooth(node.pan.pan,track.pan,c,offline);
 smooth(node.filter.frequency,Math.min(c.sampleRate*.47,800*2**(brightness*9.5)),c,offline);
 smooth(node.shelf.gain,Math.max(0,brightness-.5)*12,c,offline);
 if(node.pre)smooth(node.pre.gain,1+drive*5,c,offline);if(node.post)smooth(node.post.gain,1/(1+drive*5)**.55,c,offline);
 if(node.dry)smooth(node.dry.gain,drive>0?0:1,c,offline);if(node.wet)smooth(node.wet.gain,drive>0?1:0,c,offline);
 if(node.send)smooth(node.send.gain,(t.space||0)*.6,c,offline);
}

function sectionValue(plan,index,levels,baked){const sec=plan.sections[index];const db=(['house','bass','dnb','retro','pop','rock','hiphop','world'].includes(plan.family)?DANCE:SOFT)[sec.kind]||0;return (levels[String(index)]??1)*(baked?1:10**(db/20));}
export function repairLegacyTail(plan,render){
 const copy=structuredClone(plan),last=copy.sections.at(-1),end=Math.round((last.start+last.duration)*48000)/48000;
 if(render.arrangement_gain_baked&&!render.tail_gain_fixed&&end<copy.duration-1/48000){
  copy._legacyTail={start:end,gain:sectionValue(copy,copy.sections.length-1,{},false)};
 }return copy;
}
function automateTail(node,plan,position,offline,anchor){
 const tail=plan._legacyTail,now=offline?0:(anchor??node.context.currentTime);node.gain.cancelScheduledValues(now);
 node.gain.setValueAtTime(tail&&position>=tail.start?tail.gain:1,now);if(!tail)return;
 for(let cycle=0;cycle<(offline?1:3);cycle++){
  const at=cycle*plan.duration+tail.start-position,reset=(cycle+1)*plan.duration-position;
  if(at>0)node.gain.setValueAtTime(tail.gain,now+at);
  if(!offline&&reset>0)node.gain.setValueAtTime(1,now+reset);
 }
}
function automateSections(node,plan,levels,position,baked,offline){
 const c=node.context,now=offline?0:c.currentTime,duration=plan.duration;
 let index=plan.sections.findIndex(s=>position>=s.start&&position<s.start+s.duration);if(index<0)index=plan.sections.length-1;
 node.gain.cancelScheduledValues(now);if(offline)node.gain.setValueAtTime(sectionValue(plan,index,levels,baked),now);else node.gain.setTargetAtTime(sectionValue(plan,index,levels,baked),now,.012);
 for(let cycle=0;cycle<(offline?1:3);cycle++)for(let i=0;i<plan.sections.length;i++){
  const sec=plan.sections[i],relative=cycle*duration+sec.start-position;if(relative<=.055)continue;
  const prev=i?i-1:plan.sections.length-1;
  node.gain.setValueAtTime(sectionValue(plan,prev,levels,baked),now+relative-.045);
  node.gain.linearRampToValueAtTime(sectionValue(plan,i,levels,baked),now+relative+.045);
 }
}

export function buildGraph(ctx,tracks,plan,gainDb,levels={},baked=true,offline=false,prune=offline,monitor=false){
 const sum=ctx.createGain(),section=ctx.createGain(),tail=ctx.createGain(),master=ctx.createGain(),compressor=ctx.createDynamicsCompressor(),safety=ctx.createWaveShaper(),volume=ctx.createGain();
 master.gain.value=10**(gainDb/20);compressor.threshold.value=-3;compressor.knee.value=1;compressor.ratio.value=20;compressor.attack.value=.002;compressor.release.value=.09;
 safety.curve=LIMIT;safety.oversample='4x';sum.connect(section);section.connect(tail);if(monitor)tail.connect(ctx.destination);else{tail.connect(master);master.connect(compressor);compressor.connect(safety);safety.connect(volume);volume.connect(ctx.destination);}
 const channels=new Map(),solo=tracks.some(t=>t.solo),audible=tracks.filter(t=>!t.mute&&(!solo||t.solo)&&t.gain>0);
 let verb=null,highpass=null;
 if(!prune||audible.some(t=>(t.tone?.space||0)>0)){verb=ctx.createConvolver();verb.buffer=impulse(ctx);verb.connect(sum);highpass=ctx.createBiquadFilter();highpass.type='highpass';highpass.frequency.value=220;highpass.connect(verb);}
 for(const t of tracks){
  if(prune&&!audible.includes(t))continue;
  const input=ctx.createGain(),filter=ctx.createBiquadFilter(),shelf=ctx.createBiquadFilter(),gain=ctx.createGain(),curveGain=ctx.createGain(),pan=ctx.createStereoPanner();
  let dry=null,pre=null,shaper=null,post=null,wet=null,send=null;
  filter.type='lowpass';filter.Q.value=.6;shelf.type='highshelf';shelf.frequency.value=3500;
  input.connect(filter);filter.connect(shelf);
  if(!prune||(t.tone?.drive||0)===0){dry=ctx.createGain();shelf.connect(dry);dry.connect(gain);}
  if(!prune||(t.tone?.drive||0)>0){pre=ctx.createGain();shaper=ctx.createWaveShaper();post=ctx.createGain();wet=ctx.createGain();shaper.curve=SAT;shaper.oversample='2x';shelf.connect(pre);pre.connect(shaper);shaper.connect(post);post.connect(wet);wet.connect(gain);}
  gain.connect(curveGain);curveGain.connect(pan);pan.connect(sum);
  if(highpass&&(!prune||(t.tone?.space||0)>0)){send=ctx.createGain();pan.connect(send);send.connect(highpass);}
  const channel={ctx,input,filter,shelf,dry,pre,shaper,post,wet,gain,curveGain,pan,send};automateCurve(curveGain,t.curve,plan.duration,0,offline);setChannel(channel,t,solo,offline);channels.set(t.id,channel);
 }
 automateSections(section,plan,levels,0,baked,offline);
 automateTail(tail,plan,0,offline);
 return {channels,section,tail,volume,compressor,disconnect(){for(const n of [sum,section,tail,master,compressor,safety,volume,verb,highpass])n?.disconnect();for(const ch of channels.values())for(const n of Object.values(ch))if(n&&typeof n.disconnect==='function')n.disconnect();}};
}

export function waveform(buffer,bins=1200){const l=buffer.getChannelData(0),r=buffer.getChannelData(1),step=Math.max(1,Math.ceil(l.length/bins)),peaks=[],rms=[];let maximum=0;
 for(let a=0;a<l.length;a+=step){let p=0,sq=0;const end=Math.min(l.length,a+step);for(let i=a;i<end;i++){p=Math.max(p,Math.abs(l[i]),Math.abs(r[i]));sq+=l[i]*l[i]+r[i]*r[i];}maximum=Math.max(maximum,p);peaks.push(p);rms.push(Math.sqrt(sq/(2*(end-a))));}
 return {waveform:peaks,rms_waveform:rms,peak_dbfs:20*Math.log10(Math.max(maximum,1e-12))};
}

// Isolate the contribution before the shared master, with the real track graph.
// Other soloed tracks still silence this track, just as they do during playback.
export function monitoredRecord(records,role){const r=records.find(r=>r.track.id===role);if(!r)return null;return {...r,track:{...r.track,mute:r.track.mute||(records.some(x=>x.track.solo)&&!r.track.solo),solo:false}};}
export async function renderTrackSnapshot(snapshot,role){
 const r=monitoredRecord(snapshot.tracks,role);if(!r?.buffer||r.track.mute||r.track.gain===0)return {waveform:Array(600).fill(0),rms_waveform:Array(600).fill(0),peak_dbfs:-240};
 const ctx=new OfflineAudioContext(2,Math.round(snapshot.plan.duration*48000),48000),graph=buildGraph(ctx,[r.track],snapshot.plan,0,snapshot.levels,snapshot.baked,true,true,true);
 try{const source=ctx.createBufferSource();source.buffer=r.buffer;source.connect(graph.channels.get(role).input);source.start(0);return waveform(await ctx.startRendering(),600);}finally{graph.disconnect();}
}

export class LiveMixer extends EventTarget {
 constructor(){super();this.ctx=null;this.graph=null;this.records=new Map();this.offset=0;this.anchor=0;this.playRequested=false;this.clockRunning=false;this.epoch=0;this.loadEpoch=0;this._volume=.8;this._loop=false;this.levels={};this.ready=Promise.resolve();this.lastPosition=0;this.timer=setInterval(()=>{if(!this.paused){const p=this.currentTime;if(!this._loop&&this.clockRunning&&p>=this.duration){this.pause();this.offset=this.duration;this.dispatchEvent(new Event('ended'));return;}if(p<this.lastPosition&&this._loop)this.setLevels(this.levels);this.lastPosition=p;this.dispatchEvent(new Event('timeupdate'));}},75);}
 get paused(){return !this.playRequested;}get duration(){return this.plan?.duration||0;}
 get currentTime(){if(this.paused||!this.ctx||!this.clockRunning)return this.offset;const n=Math.max(0,this.ctx.currentTime-this.anchor)+this.offset;return this._loop&&this.duration?n%this.duration:Math.min(this.duration,n);}
 set currentTime(n){n=Math.max(0,Math.min(this.duration,Number(n)||0));const playing=!this.paused;this.stopSources();this.offset=n;if(playing&&n<this.duration)this.startSources();else if(playing){this.playRequested=false;this.dispatchEvent(new Event('pause'));}this.dispatchEvent(new Event('seeked'));}
 get volume(){return this._volume;}set volume(n){this._volume=n;if(this.graph)smooth(this.graph.volume.gain,n,this.ctx);}
 get loop(){return this._loop;}set loop(n){this._loop=Boolean(n);for(const r of this.records.values())if(r.source)r.source.loop=this._loop;}
 ensureContext(){if(!this.ctx)this.ctx=new AudioContext({sampleRate:48000,latencyHint:'interactive'});return this.ctx;}
 async decode(url){const response=await fetch(url);if(!response.ok)throw Error('Stopu nelze načíst.');return this.ensureContext().decodeAudioData(await response.arrayBuffer());}
 setProject(data,project,onProgress=()=>{}){
  this.pause();this.stopSources();if(this.graph)this.graph.disconnect();this.graph=null;this.records.clear();this.bufferCache=new BufferCache();this.plan=repairLegacyTail(data.plan,data.render);this.project=project;this.baked=Boolean(data.render.arrangement_gain_baked);this.levels={...(data.plan.settings.section_levels||{})};this.offset=0;
  const stats=data.render.master;this.gainDb=stats.linear_gain_db??Math.max(-6,Math.min(9,Number(stats.output_i||-14)-Number(stats.input_i||-14)));
  this.preview=new WavePreview(this.plan,this.gainDb,this.baked);
  const ctx=this.ensureContext(),epoch=++this.loadEpoch,tracks=data.plan.tracks.map(t=>structuredClone(t));
  this.graph=buildGraph(ctx,tracks,this.plan,this.gainDb,this.levels,this.baked);this.graph.volume.gain.value=this._volume;
  for(const t of tracks)this.records.set(t.id,{track:t,buffer:null,source:null,fade:null});
  let index=0,done=0;const active=tracks.filter(t=>t.notes.length);
  const worker=async()=>{while(index<active.length){const track=active[index++];let url=`/stems/${project}/${track.id}/base.wav`;
   if((track.tone.brightness??.5)!==.5||(track.tone.drive||0)!==0||(track.tone.space||0)!==0){url=await this.trackURL(track);}
   const buffer=await this.decode(url);if(epoch!==this.loadEpoch)return;const record=this.records.get(track.id);record.buffer=buffer;record.bufferKey=bufferKey(track);onProgress(++done,active.length);
  }};
  this.ready=Promise.all([worker(),worker()]).then(()=>{if(epoch===this.loadEpoch)this.dispatchEvent(new Event('ready'));});return this.ready;
 }
 async trackURL(track){const response=await fetch('/api/track',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({project:this.project,role:track.id,instrument:track.instrument,tone:track.tone})});const job=await response.json();if(!response.ok)throw Error(job.error);let state=job;while(state.state==='running'){await new Promise(r=>setTimeout(r,35));const r=await fetch('/api/status?job='+job.id);state=await r.json();}if(state.state!=='done')throw Error(state.message||'Změna nástroje byla nahrazena novější.');return state.url;}
 setMix(mix={},tones={}){const list=[];for(const [id,r]of this.records){Object.assign(r.track,mix[id]||{});r.track.tone={...r.track.tone,...tones[id]};list.push(r.track);}const solo=list.some(t=>t.solo);if(this.graph)for(const t of list){const ch=this.graph.channels.get(t.id);setChannel(ch,t,solo);automateCurve(ch.curveGain,t.curve,this.duration,this.currentTime,false);}}
 setLevels(levels){this.levels={...levels};if(this.graph){automateSections(this.graph.section,this.plan,this.levels,this.currentTime,this.baked,false);automateTail(this.graph.tail,this.plan,this.currentTime,false);for(const r of this.records.values())automateCurve(this.graph.channels.get(r.track.id).curveGain,r.track.curve,this.duration,this.currentTime,false);}}
 async replaceTrack(role,instrument,tone){const epoch=this.loadEpoch,r=this.records.get(role);if(!r)return;const version=(r.version||0)+1;r.version=version;const next={...r.track,instrument,tone:{...r.track.tone,...tone}};
  const key=bufferKey(next),cache=this.bufferCache;cache.put(r.bufferKey,r.buffer);
  let buffer=cache.get(key);
  if(!buffer){try{const url=await this.trackURL(next);if(epoch!==this.loadEpoch||r.version!==version)return false;buffer=await this.decode(url);cache.put(key,buffer);}catch(error){if(epoch!==this.loadEpoch||r.version!==version)return false;throw error;}}
  if(epoch!==this.loadEpoch||r.version!==version)return false;
  r.track.instrument=instrument;r.track.tone={...r.track.tone,attack:next.tone.attack,release:next.tone.release};r.buffer=buffer;r.bufferKey=key;
  if(!this.paused){const now=this.ctx.currentTime,start=now+.015,pos=this._loop?(this.currentTime+.015)%this.duration:Math.min(this.duration-.00001,this.currentTime+.015),oldSource=r.source,oldFade=r.fade;this.startRecord(r,start,pos,true);if(oldFade){oldFade.gain.cancelScheduledValues(now);oldFade.gain.setValueAtTime(oldFade.gain.value,now);oldFade.gain.linearRampToValueAtTime(0,start+.035);}if(oldSource){oldSource.onended=null;oldSource.stop(start+.04);setTimeout(()=>{oldSource.disconnect();oldFade?.disconnect();},100);}}
  return true;
 }
 startRecord(record,start,position,crossfade=false){if(!record.buffer)return;const source=this.ctx.createBufferSource(),fade=this.ctx.createGain();source.buffer=record.buffer;source.loop=this._loop;source.connect(fade);fade.connect(this.graph.channels.get(record.track.id).input);fade.gain.setValueAtTime(crossfade?0:1,start);if(crossfade)fade.gain.linearRampToValueAtTime(1,start+.035);source.start(start,Math.min(position,source.buffer.duration-.00001));record.source=source;record.fade=fade;}
 stopSources(){this.clockRunning=false;this.epoch++;for(const r of this.records.values()){if(r.source){r.source.onended=null;try{r.source.stop();}catch{}r.source.disconnect();r.fade.disconnect();r.source=null;r.fade=null;}}}
 startSources(){const start=this.ctx.currentTime+.015;this.anchor=start;this.clockRunning=true;for(const r of this.records.values())this.startRecord(r,start,this.offset);const epoch=this.epoch;const first=[...this.records.values()].find(r=>r.source);if(first)first.source.onended=()=>{if(epoch===this.epoch&&!this._loop&&this.playRequested){this.offset=this.duration;this.playRequested=false;this.stopSources();this.dispatchEvent(new Event('ended'));}};automateSections(this.graph.section,this.plan,this.levels,this.offset,this.baked,false);automateTail(this.graph.tail,this.plan,this.offset,false,start);for(const r of this.records.values())automateCurve(this.graph.channels.get(r.track.id).curveGain,r.track.curve,this.duration,this.offset,false,start);}
 async play(){if(this.playRequested)return;if(this.offset>=this.duration)this.offset=0;this.playRequested=true;const epoch=this.loadEpoch,resume=this.ensureContext().resume();this.dispatchEvent(new Event('play'));try{await Promise.all([this.ready,resume]);if(this.playRequested&&epoch===this.loadEpoch&&!this.clockRunning)this.startSources();}catch(e){if(epoch===this.loadEpoch){this.playRequested=false;this.dispatchEvent(new Event('pause'));}throw e;}}
 pause(){const p=this.currentTime;this.playRequested=false;this.stopSources();this.offset=p;this.dispatchEvent(new Event('pause'));}
 async snapshot(){await this.ready;return {plan:structuredClone(this.plan),tracks:[...this.records.values()].map(r=>({track:structuredClone(r.track),buffer:r.buffer})),gainDb:this.gainDb,levels:{...this.levels},baked:this.baked};}
 quickWaveform(){return this.preview?.render([...this.records.values()],this.levels);}
 rememberWaveform(rendered,snapshot){this.preview?.setReference(rendered,snapshot.tracks,snapshot.levels);}
 async renderSnapshot(snapshot){const s=snapshot||await this.snapshot(),ctx=new OfflineAudioContext(2,Math.round(s.plan.duration*48000),48000);const graph=buildGraph(ctx,s.tracks.map(r=>r.track),s.plan,s.gainDb,s.levels,s.baked,true);for(const r of s.tracks)if(r.buffer&&graph.channels.has(r.track.id)){const source=ctx.createBufferSource();source.buffer=r.buffer;source.connect(graph.channels.get(r.track.id).input);source.start(0);}const buffer=await ctx.startRendering();graph.disconnect();return {buffer,...waveform(buffer)};}
}

export async function exportBody(buffer,metadata){const encoded=new TextEncoder().encode(JSON.stringify(metadata)),size=new ArrayBuffer(4);new DataView(size).setUint32(0,encoded.length,true);const parts=[size,encoded],left=buffer.getChannelData(0),right=buffer.getChannelData(1),step=48000;
 for(let a=0;a<left.length;a+=step){const n=Math.min(step,left.length-a),interleaved=new Float32Array(n*2);for(let i=0;i<n;i++){interleaved[i*2]=left[a+i];interleaved[i*2+1]=right[a+i];}parts.push(interleaved);if(a%(step*20)===0)await new Promise(r=>setTimeout(r,0));}return new Blob(parts,{type:'application/octet-stream'});}
