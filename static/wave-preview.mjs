import {curveValue} from './volume-curve.mjs';
// A small, deterministic sample of the actual stems gives immediate mix feedback.
// An exact Web Audio render replaces this display estimate after interaction.
const DANCE={intro:-5,verse:-2.5,verseB:-2,build:-2,chorus:0,final:.3,bridge:-5.5,outro:-6};
const SOFT={intro:-2,verse:-.8,verseB:-.6,build:-.5,chorus:0,final:.3,bridge:-2.5,outro:-3};
export class WavePreview{
 constructor(plan,gainDb,baked,bins=1200,samples=96,limit=true){this.plan=plan;this.gain=10**(gainDb/20);this.baked=baked;this.bins=bins;this.samples=samples;this.limit=limit;this.banks=new WeakMap();this.reference=null;}
 bank(buffer){
  let bank=this.banks.get(buffer);if(bank)return bank;
  const left=buffer.getChannelData(0),right=buffer.getChannelData(1),n=this.bins*this.samples;bank={left:new Float32Array(n),right:new Float32Array(n)};
  for(let b=0;b<this.bins;b++){const start=Math.floor(b*buffer.length/this.bins),end=Math.max(start+1,Math.floor((b+1)*buffer.length/this.bins));
   for(let j=0;j<this.samples;j++){
    // Jitter inside each stratum avoids aliasing a periodic note or drum loop.
    let h=(Math.imul(b+1,73856093)^Math.imul(j+1,19349663))>>>0;h=Math.imul(h^(h>>>16),0x45d9f3b)>>>0;
    const position=Math.min(buffer.length-1,start+Math.floor((j+(h>>>0)/4294967296)/this.samples*(end-start))),k=b*this.samples+j;
    bank.left[k]=left[position];bank.right[k]=right[position];
   }
  }this.banks.set(buffer,bank);return bank;
 }
 estimate(records,levels){
  const solo=records.some(r=>r.track.solo),channels=[];
  for(const {track:t,buffer}of records){if(!buffer||t.mute||(solo&&!t.solo)||!t.gain)continue;
   const pan=Math.max(-1,Math.min(1,t.pan||0)),x=pan<=0?pan+1:pan,c=Math.cos(x*Math.PI/2),s=Math.sin(x*Math.PI/2);
   channels.push({curve:t.curve,...this.bank(buffer),ll:t.gain*(pan<=0?1:c),lr:t.gain*(pan<=0?c:0),rl:t.gain*(pan<=0?0:s),rr:t.gain*(pan<=0?s:1)});
  }
  const rms=[],peaks=[],profile=['house','bass','dnb','retro','pop','rock','hiphop','world'].includes(this.plan.family)?DANCE:SOFT;
  let section=0,maximum=0;
  for(let b=0;b<this.bins;b++){
   const time=(b+.5)*this.plan.duration/this.bins;
   while(section<this.plan.sections.length-1&&time>=this.plan.sections[section+1].start)section++;
   const gain=this.gain*(levels[String(section)]??1)*(this.baked?1:10**((profile[this.plan.sections[section].kind]||0)/20))*(this.plan._legacyTail&&time>=this.plan._legacyTail.start?this.plan._legacyTail.gain:1);
   for(const ch of channels)ch.curveScale=curveValue(ch.curve,time/this.plan.duration);
   let square=0,peak=0;
   for(let j=0;j<this.samples;j++){const k=b*this.samples+j;let l=0,r=0;
    for(const ch of channels){const a=ch.left[k],z=ch.right[k];l+=(a*ch.ll+z*ch.lr)*ch.curveScale;r+=(a*ch.rl+z*ch.rr)*ch.curveScale;}
    l*=gain;r*=gain;if(this.limit){l=Math.max(-.79,Math.min(.79,l));r=Math.max(-.79,Math.min(.79,r));}square+=l*l+r*r;peak=Math.max(peak,Math.abs(l),Math.abs(r));
   }rms.push(Math.sqrt(square/(2*this.samples)));peaks.push(peak);maximum=Math.max(maximum,peak);
  }
  return {rms_waveform:rms,waveform:peaks,peak_dbfs:20*Math.log10(Math.max(maximum,1e-12))};
 }
 setReference(rendered,records,levels){this.reference={exact:rendered,estimate:this.estimate(records,levels)};}
 render(records,levels){
  const estimate=this.estimate(records,levels),ref=this.reference;if(!ref)return estimate;
  // Keep the exact curve's texture; only project the current mix change. This
  // prevents random sampling noise from making the waveform jump on each drag.
  for(const key of ['rms_waveform','waveform'])estimate[key]=estimate[key].map((value,i)=>{
   const index=Math.min(ref.exact[key].length-1,Math.floor(i*ref.exact[key].length/this.bins)),base=ref.estimate[key][i];
   const projected=base>1e-8?ref.exact[key][index]*value/base:value;return this.limit?Math.min(.79,projected):projected;
  });
  return estimate;
 }
}
