export const flatCurve=()=>[[0,1],[1,1]];
export function cleanCurve(points){
 if(!Array.isArray(points)||points.length<2)return flatCurve();
 const sorted=points.slice(0,64).filter(p=>Array.isArray(p)&&p.length===2&&p.every(Number.isFinite)).map(([x,y])=>[Math.max(0,Math.min(1,x)),Math.max(0,Math.min(1.5,y))]).sort((a,b)=>a[0]-b[0]);
 const out=[];for(const p of sorted){if(out.length&&p[0]-out.at(-1)[0]<.0001)out[out.length-1]=p;else out.push(p);}
 if(!out.length)return flatCurve();if(out[0][0]>0)out.unshift([0,out[0][1]]);if(out.at(-1)[0]<1)out.push([1,out.at(-1)[1]]);if(out.length>64)out.splice(63,out.length-64);return out;
}
export function curveValue(points,x){const p=points?.length?points:flatCurve();if(x<=p[0][0])return p[0][1];for(let i=1;i<p.length;i++)if(x<=p[i][0])return p[i-1][1]+(p[i][1]-p[i-1][1])*(x-p[i-1][0])/Math.max(1e-9,p[i][0]-p[i-1][0]);return p.at(-1)[1];}
export function automateCurve(node,points,duration,position=0,offline=false,anchor){
 const p=cleanCurve(points),now=offline?0:(anchor??node.context.currentTime);node.gain.cancelScheduledValues(now);node.gain.setValueAtTime(curveValue(p,position/duration),now);
 for(let cycle=0;cycle<(offline?1:3);cycle++)for(const [x,y]of p){const dt=cycle*duration+x*duration-position;if(dt>0)node.gain.linearRampToValueAtTime(y,now+dt);}
}
const contexts=new WeakMap();
const escapeText=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function tools(svg,points,index){
 const editor=svg.closest('[data-curve-role]'),p=points[index],time=editor.querySelector('.curve-point-time'),level=editor.querySelector('.curve-point-level'),duration=contexts.get(svg)?.plan.duration||1;
 if(!time)return;const endpoint=!p||index===0||index===points.length-1,blocked=svg.closest('#mixer')?.getAttribute('aria-busy')==='true';for(const [control,disabled]of [[time,endpoint],[level,!p],[editor.querySelector('.curve-remove'),endpoint]]){control.dataset.curveDisabled=String(disabled);control.disabled=blocked||disabled;}
 if(document.activeElement!==time)time.value=p?(p[0]*duration).toFixed(2):'';
 if(document.activeElement!==level)level.value=p?Math.round(p[1]*100):'';
 time.max=duration;editor.querySelector('.curve-selection').textContent=p?`Bod ${index+1} / ${points.length}`:'Vyber bod pro přesné hodnoty';
}
function paint(svg,points,selected=-1){
 const p=cleanCurve(points),context=contexts.get(svg),sections=context?.plan.sections||[],duration=context?.plan.duration||1;
 const segment=(a,b)=>[[a,curveValue(p,a)],...p.filter(v=>v[0]>a&&v[0]<b),[b,curveValue(p,b)]].map(([x,y],i)=>`${i?'L':'M'}${20+x*960},${160-y/1.5*140}`).join(' ');
 const paths=sections.length?sections.map(sec=>`<path d="${segment(sec.start/duration,Math.min(1,(sec.start+sec.duration)/duration))}" stroke="${context.colours[sec.kind]||'#baf3a2'}" stroke-width="3" fill="none"/>`).join(''):`<path d="${segment(0,1)}" stroke="#baf3a2" stroke-width="3" fill="none"/>`;
 svg.querySelector('.curve-points').innerHTML=`<path d="M20 160H980 M20 66.67H980" stroke="#405044" fill="none"/><text x="22" y="61" fill="#91a68f" font-size="12">100 %</text>${paths}`+p.map(([x,y],i)=>`<circle tabindex="0" role="button" aria-label="Bod ${i+1}: ${Math.round(x*100)} %, hlasitost ${Math.round(y*100)} %" data-point="${i}" cx="${20+x*960}" cy="${160-y/1.5*140}" r="${i===selected?8:6}" fill="${i===selected?'#fff':'#d4ecc8'}" stroke="#1a251c" stroke-width="2"/>`).join('');
 tools(svg,p,selected);
}
export function curveEditor(role){return `<details class="volume-automation" data-curve-role="${role}"><summary>Hlasitostní křivka a průběh stopy <small>upravit hlasitost v čase</small></summary><svg class="volume-curve" viewBox="0 0 1000 180" preserveAspectRatio="none" tabindex="0" aria-label="Hlasitostní křivka stopy ${role}"><g class="curve-section-bands"></g><g class="curve-points"></g><line class="curve-playhead" x1="20" x2="20" y1="20" y2="160" stroke="#fff" opacity=".6" pointer-events="none"/></svg><div class="curve-tools"><span>Klik přidá bod · tažení upraví · šipky doladí · Delete / Backspace smaže</span><button class="curve-remove quiet" disabled>Odstranit bod</button><button class="curve-reset quiet">Rovná křivka</button></div><div class="curve-point-tools"><span class="curve-selection">Vyber bod pro přesné hodnoty</span><label>Čas <input class="curve-point-time" type="number" min="0" step="0.1" disabled aria-label="Čas vybraného bodu v sekundách"> s</label><label>Hlasitost <input class="curve-point-level" type="number" min="0" max="150" step="1" disabled aria-label="Hlasitost vybraného bodu v procentech"> %</label></div><div class="track-wave-heading"><span>PRŮBĚH TOHOTO NÁSTROJE <small>RMS · pevné měřítko · před masterem</small></span><output class="track-wave-status" aria-live="polite">Načítám stopu…</output></div><canvas class="track-waveform" tabindex="0" role="slider" aria-label="Pozice přehrávání v průběhu stopy ${role}" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0" title="Kliknutím přesuneš přehrávání. Šipky: ±5 sekund. Home / End: začátek / konec."></canvas><div class="track-wave-times"><span>0:00</span><span class="track-wave-duration"></span></div><div class="track-wave-legend"></div></details>`;}
export function paintCurveEditors(root,get,plan,colours={}){
 for(const svg of root.querySelectorAll('.volume-curve')){
  if(plan){contexts.set(svg,{plan,colours});svg.dataset.duration=plan.duration;svg.querySelector('.curve-section-bands').innerHTML=plan.sections.map(sec=>{const x=20+sec.start/plan.duration*960,w=sec.duration/plan.duration*960;return `<rect x="${x}" y="0" width="${w}" height="180" fill="${colours[sec.kind]}" opacity=".09"/><path d="M${x} 0V180" stroke="${colours[sec.kind]}" opacity=".25"/>${w>50?`<text x="${x+5}" y="14" font-size="10" fill="${colours[sec.kind]}">${escapeText(sec.name)}</text>`:''}`;}).join('');}
  paint(svg,get(svg.closest('[data-curve-role]').dataset.curveRole));
 }
}
export function installCurveEditors(root,get,set){
 let drag=null,selected=null;const selections=new WeakMap();
 const identify=el=>el.closest('[data-curve-role]');
 const blocked=()=>root.getAttribute('aria-busy')==='true';
 const position=(svg,event)=>{const p=new DOMPoint(event.clientX,event.clientY).matrixTransform(svg.getScreenCTM().inverse());return [Math.max(0,Math.min(1,(p.x-20)/960)),Math.max(0,Math.min(1.5,(160-p.y)/140*1.5))];};
 const remove=()=>{if(blocked()||!selected?.svg.isConnected)return;const {role,svg,index}=selected,p=cleanCurve(get(role));if(index<=0||index>=p.length-1)return;p.splice(index,1);set(role,p);selected=null;selections.delete(svg);paint(svg,p);};
 const update=(point)=>{if(blocked()||!selected?.svg.isConnected)return;const {role,svg,index}=selected,p=cleanCurve(get(role));point[0]=index===0?0:index===p.length-1?1:Math.max(p[index-1][0]+.0002,Math.min(p[index+1][0]-.0002,point[0]));point[1]=Math.max(0,Math.min(1.5,point[1]));p[index]=point;set(role,p);paint(svg,p,index);};
 root.addEventListener('pointerdown',event=>{const svg=event.target.closest('.volume-curve');if(!svg||blocked())return;event.preventDefault();svg.focus();const role=identify(svg).dataset.curveRole,p=cleanCurve(get(role));let index=event.target.dataset.point===undefined?-1:Number(event.target.dataset.point);
  if(index<0){const point=position(svg,event);index=p.findIndex(v=>Math.abs(v[0]-point[0])<.005);if(index<0&&p.length<64){p.push(point);p.sort((a,b)=>a[0]-b[0]);index=p.indexOf(point);set(role,p);}}
  if(index<0)return;drag=selected={role,svg,index};selections.set(svg,index);svg.setPointerCapture(event.pointerId);paint(svg,p,index);
 });
 root.addEventListener('pointermove',event=>{if(drag&&drag.svg.isConnected){selected=drag;update(position(drag.svg,event));}});
 root.addEventListener('pointerup',()=>drag=null);root.addEventListener('pointercancel',()=>drag=null);
 root.addEventListener('focusin',event=>{const editor=identify(event.target);if(!editor)return;const svg=editor.querySelector('svg'),role=editor.dataset.curveRole;if(event.target.matches('.volume-curve circle'))selections.set(svg,Number(event.target.dataset.point));selected=selections.has(svg)?{role,svg,index:selections.get(svg)}:null;tools(svg,cleanCurve(get(role)),selected?.index??-1);});
 root.addEventListener('keydown',event=>{const svg=event.target.closest('.volume-curve');if(!svg||blocked())return;if(selected?.svg!==svg)selected=selections.has(svg)?{role:identify(svg).dataset.curveRole,svg,index:selections.get(svg)}:null;
  if(['Delete','Backspace'].includes(event.key)){event.preventDefault();event.stopPropagation();remove();return;}
  if(selected&&['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(event.key)){event.preventDefault();event.stopPropagation();const p=[...cleanCurve(get(selected.role))[selected.index]],factor=event.shiftKey?10:1;if(event.key==='ArrowLeft')p[0]-=factor/(contexts.get(svg)?.plan.duration||1);if(event.key==='ArrowRight')p[0]+=factor/(contexts.get(svg)?.plan.duration||1);if(event.key==='ArrowUp')p[1]+=.01*factor;if(event.key==='ArrowDown')p[1]-=.01*factor;svg.focus();update(p);}
  if(event.key==='Escape'){selected=null;selections.delete(svg);paint(svg,get(identify(svg).dataset.curveRole));}
 });
 root.addEventListener('input',event=>{if(!event.target.matches('.curve-point-time,.curve-point-level')||selected?.role!==identify(event.target)?.dataset.curveRole)return;const value=Number(event.target.value);if(event.target.value===''||!Number.isFinite(value))return;const p=[...cleanCurve(get(selected.role))[selected.index]];if(event.target.classList.contains('curve-point-time'))p[0]=value/(contexts.get(selected.svg)?.plan.duration||1);else p[1]=value/100;update(p);});
 root.addEventListener('focusout',event=>{if(event.target.matches('.curve-point-time,.curve-point-level')&&selected?.svg.isConnected)tools(selected.svg,cleanCurve(get(selected.role)),selected.index);});
 root.addEventListener('click',event=>{const editor=identify(event.target);if(!editor||blocked())return;const role=editor.dataset.curveRole;if(event.target.closest('.curve-reset')){set(role,flatCurve());selected=null;selections.delete(editor.querySelector('svg'));paint(editor.querySelector('svg'),flatCurve());}if(event.target.closest('.curve-remove')&&selected?.role===role)remove();});
}
