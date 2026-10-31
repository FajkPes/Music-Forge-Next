const SELECTOR='input[type="range"],input[type="number"],input[type="checkbox"],select,button[aria-pressed]';
const writing=element=>element?.isContentEditable||element?.closest('textarea,input:not([type="range"]):not([type="number"]):not([type="checkbox"]):not([type="button"])');

// Delegation also covers instrument controls recreated after loading a song.
export function installHoverReset(root,defaultValue,onReset=()=>{}){
 let hovered=null;
 const over=event=>{
  hovered=event.target.closest?.(SELECTOR)||null;
  if(hovered&&defaultValue(hovered)!==undefined&&!hovered.dataset.resetHint){
   hovered.title=[hovered.title,'Backspace pod kurzorem: obnovit výchozí hodnotu'].filter(Boolean).join('\n');
   hovered.dataset.resetHint='true';
  }
 };
 const out=event=>{if(hovered===event.target&&!hovered.contains(event.relatedTarget))hovered=null;};
 const key=event=>{
  if(event.key!=='Backspace'||event.repeat||event.ctrlKey||event.altKey||event.metaKey||event.shiftKey||event.defaultPrevented||writing(root.activeElement))return;
  const control=hovered;
  if(!control?.isConnected||control.disabled||control.closest('[hidden],:disabled'))return;
  const value=defaultValue(control);if(value===undefined)return;
  event.preventDefault();event.stopPropagation();
  if(control.tagName==='BUTTON'){
   if((control.getAttribute('aria-pressed')==='true')!==Boolean(value))control.click();
  }else{
   if(control.type==='checkbox')control.checked=Boolean(value);else control.value=String(value);
   control.dispatchEvent(new Event('input',{bubbles:true}));
   control.dispatchEvent(new Event('change',{bubbles:true}));
  }
  onReset(control,value);
 };
 root.addEventListener('pointerover',over);root.addEventListener('pointerout',out);root.addEventListener('keydown',key);
 return ()=>{root.removeEventListener('pointerover',over);root.removeEventListener('pointerout',out);root.removeEventListener('keydown',key);};
}
