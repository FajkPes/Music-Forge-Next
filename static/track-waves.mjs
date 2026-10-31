import {WavePreview} from './wave-preview.mjs';
import {SECTION_COLOURS,monitoredRecord,renderTrackSnapshot} from './live-mixer.mjs';
const time=n=>`${Math.floor(n/60)}:${String(Math.floor(n%60)).padStart(2,'0')}`;
const escapeText=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export class TrackWaveViews {
 constructor(root,audio,onSeek=()=>{},pending=()=>false){this.root=root;this.audio=audio;this.onSeek=onSeek;this.pending=pending;this.states=new Map();this.epoch=0;this.running=false;
  new ResizeObserver(()=>this.position()).observe(root);
  root.addEventListener('toggle',event=>{if(event.target.matches('.volume-automation[open]'))this.refresh();},true);
  root.addEventListener('pointerdown',event=>{const canvas=event.target.closest('.track-waveform');if(!canvas||root.getAttribute('aria-busy')==='true'||!audio.duration)return;event.preventDefault();const r=canvas.getBoundingClientRect(),x=Math.max(0,Math.min(1,((event.clientX-r.left)/r.width-.02)/.96));audio.currentTime=x*audio.duration;canvas.focus();this.position();onSeek();});
  root.addEventListener('keydown',event=>{if(!event.target.matches('.track-waveform')||root.getAttribute('aria-busy')==='true')return;const values={ArrowLeft:audio.currentTime-5,ArrowRight:audio.currentTime+5,Home:0,End:audio.duration};if(event.key in values){event.preventDefault();event.stopPropagation();audio.currentTime=values[event.key];this.position();onSeek();}});
 }
 reset(){this.epoch++;clearTimeout(this.timer);this.states.clear();}
 opened(){return [...this.root.querySelectorAll('.volume-automation[open]')];}
 key(record){return JSON.stringify([record.track,this.audio.levels]);}
 refresh(){
  if(!this.audio.plan||this.root.getAttribute('aria-busy')==='true')return;const records=[...this.audio.records.values()];let changed=false;
  for(const editor of this.opened()){
   const role=editor.dataset.curveRole,r=monitoredRecord(records,role);if(!r)continue;
   let state=this.states.get(role);if(!state||state.preview.plan!==this.audio.plan){state={preview:new WavePreview(this.audio.plan,0,this.audio.baked,600,48,false)};this.states.set(role,state);}
   const key=this.key(r);if(state.key!==key||state.buffer!==r.buffer){if(state.buffer!==r.buffer)state.preview.reference=null;state.key=key;state.buffer=r.buffer;state.exact=false;state.failed=false;state.wave=state.preview.render([r],this.audio.levels);changed=true;}
   const status=editor.querySelector('.track-wave-status');status.textContent=this.pending(role)?'Načítám nový nástroj…':!r.buffer?(r.track.notes?.length?'Načítám zvuk…':'Stopa v této skladbě nehraje'):state.exact?'Přesný průběh':'Živý náhled · zpřesňuji…';
   editor.querySelector('.track-wave-duration').textContent=time(this.audio.duration);
   const legend=editor.querySelector('.track-wave-legend');if(!legend.childElementCount)legend.innerHTML=this.audio.plan.sections.map(sec=>`<span style="--section-colour:${SECTION_COLOURS[sec.kind]}">${escapeText(sec.name)} <small>${time(sec.start)}</small></span>`).join('');
   this.draw(editor,state);
  }
  if(changed||this.opened().some(e=>!this.states.get(e.dataset.curveRole)?.exact)){clearTimeout(this.timer);this.timer=setTimeout(()=>this.refine(),180);}
 }
 async refine(){
  if(this.running||this.root.getAttribute('aria-busy')==='true')return;this.running=true;const epoch=this.epoch;
  try{
   for(const editor of this.opened()){
    const role=editor.dataset.curveRole,state=this.states.get(role);if(!state||state.exact||this.pending(role)||!state.buffer)continue;
    const snapshot=await this.audio.snapshot(),r=monitoredRecord(snapshot.tracks,role),key=JSON.stringify([r.track,snapshot.levels]),buffer=r.buffer;
    const wave=await renderTrackSnapshot(snapshot,role);
    if(epoch!==this.epoch)return;
    if(state.key!==key||state.buffer!==buffer)continue;
    state.preview.setReference(wave,[r],snapshot.levels);state.wave=wave;state.exact=true;
    const current=this.root.querySelector(`[data-curve-role="${role}"]`);if(current?.open){current.querySelector('.track-wave-status').textContent='Přesný průběh';this.draw(current,state);}
   }
  }catch(error){for(const editor of this.opened()){const state=this.states.get(editor.dataset.curveRole);if(state&&!state.exact){state.failed=true;editor.querySelector('.track-wave-status').textContent='Živý náhled · přesný výpočet se nezdařil';}}console.error('Průběh stopy:',error);}
  finally{this.running=false;if(this.opened().some(e=>{const s=this.states.get(e.dataset.curveRole);return s?.buffer&&!s.exact&&!s.failed&&!this.pending(e.dataset.curveRole);}))this.timer=setTimeout(()=>this.refine(),180);}
 }
 position(){for(const editor of this.opened()){const state=this.states.get(editor.dataset.curveRole);if(state)this.draw(editor,state);}}
 draw(editor,state){
  const canvas=editor.querySelector('.track-waveform'),rect=canvas.getBoundingClientRect();if(!rect.width||!rect.height)return;const dpr=devicePixelRatio||1,w=rect.width,h=rect.height;
  if(canvas.width!==Math.round(w*dpr)||canvas.height!==Math.round(h*dpr)){canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr);}
  const c=canvas.getContext('2d');c.setTransform(dpr,0,0,dpr,0,0);c.clearRect(0,0,w,h);const plan=this.audio.plan,duration=plan.duration,left=w*.02,width=w*.96;
  for(const sec of plan.sections){const x=left+sec.start/duration*width,sw=sec.duration/duration*width;c.fillStyle=SECTION_COLOURS[sec.kind];c.globalAlpha=.09;c.fillRect(x,0,sw,h);c.globalAlpha=.3;c.fillRect(x,0,1,h);}
  const values=state.wave?.rms_waveform||[],columns=Math.max(1,Math.floor(width/3));c.globalAlpha=1;
  for(let i=0;i<columns;i++){const a=Math.floor(i*values.length/columns),b=Math.max(a+1,Math.floor((i+1)*values.length/columns));let square=0;for(let j=a;j<b;j++)square+=(values[j]||0)**2;const rms=Math.sqrt(square/(b-a)),height=Math.min(h*.92,rms*h*6),at=(i+.5)/columns*duration,sec=plan.sections.find(s=>at>=s.start&&at<s.start+s.duration)||plan.sections.at(-1);c.fillStyle=SECTION_COLOURS[sec.kind];if(height>0)c.fillRect(left+i/columns*width,(h-height)/2,2,Math.max(.5,height));}
  c.strokeStyle='#48604d';c.globalAlpha=.5;c.beginPath();c.moveTo(left,h/2);c.lineTo(left+width,h/2);c.stroke();c.globalAlpha=1;
  const position=Math.max(0,Math.min(1,this.audio.currentTime/duration)),x=left+position*width;c.fillStyle='#f1ffe8';c.fillRect(x,0,1,h);
  const line=editor.querySelector('.curve-playhead');line.setAttribute('x1',20+position*960);line.setAttribute('x2',20+position*960);
  canvas.setAttribute('aria-valuenow',Math.round(position*100));canvas.setAttribute('aria-valuetext',`${time(this.audio.currentTime)} z ${time(duration)}`);canvas.dataset.waveQuality=state.exact?'exact':'preview';canvas.dataset.waveEnergy=String(values.reduce((n,v)=>n+v*v,0));
 }
}
