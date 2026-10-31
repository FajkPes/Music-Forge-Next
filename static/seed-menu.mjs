const $=id=>document.getElementById(id);
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export async function initSeedMenu({api,getSettings,getPlayed,applySettings,toast}){
 let library={seeds:[],capacity:50,can_undo:false};
 function render(){
  $('saved-seed-count').textContent=library.seeds.length+'/50';$('seed-library-count').textContent=library.seeds.length+' / 50 uložených';$('seed-undo').disabled=!library.can_undo;
  $('seed-save-played').disabled=!getPlayed();const query=$('seed-search').value.toLocaleLowerCase('cs');
  const visible=library.seeds.filter(item=>(item.name+' '+item.settings.seed+' '+item.settings.genre).toLocaleLowerCase('cs').includes(query));
  $('seed-list').innerHTML=visible.length?visible.map(item=>`<div class="saved-seed-row"><button class="saved-seed-load" data-load-seed="${item.id}"><strong>${esc(item.name)}</strong><small>Seed ${item.settings.seed} · ${esc(item.settings.genre)} · ${Math.floor(item.settings.duration/60)}:${String(item.settings.duration%60).padStart(2,'0')} · Vyplnit zadání →</small></button><button class="quiet" data-delete-seed="${item.id}" aria-label="Odstranit: ${esc(item.name)}">×</button></div>`).join(''):'<p class="hint">'+(query?'Žádný seed neodpovídá hledání.':'Zatím nemáš uložené seedy. Každá položka uchová seed i úplné nastavení skladby.')+'</p>';
 }
 async function refresh(){library=await api('/api/seeds');render();}
 async function save(played=false){try{const settings=played?getPlayed():getSettings();if(!settings)return;library=await api('/api/seeds',{settings,name:$('seed-name').value.trim()||settings.title});render();toast('Seed '+settings.seed+' a nastavení jsou uložené.');}catch(error){toast(error.message,true);}}
 $('open-seeds').addEventListener('click',async()=>{try{$('seed-name').value=$('title').value;await refresh();$('seed-library').showModal();}catch(error){toast(error.message,true);}});
 $('close-seeds').addEventListener('click',()=>$('seed-library').close());$('seed-save').addEventListener('click',()=>save());$('seed-save-played').addEventListener('click',()=>save(true));$('seed-search').addEventListener('input',render);
 $('seed-list').addEventListener('click',async event=>{
  const load=event.target.closest('[data-load-seed]'),remove=event.target.closest('[data-delete-seed]');
  if(load){const item=library.seeds.find(s=>s.id===load.dataset.loadSeed);applySettings(structuredClone(item.settings));$('seed-library').close();toast('Seed '+item.settings.seed+' a nastavení vyplněny. Klikni na Vytvořit skladbu.');}
  if(remove)try{library=await api('/api/seeds/delete',{id:remove.dataset.deleteSeed});render();toast('Položka odstraněna. Můžeš použít Vrátit odstranění.');}catch(error){toast(error.message,true);}
 });
 $('seed-undo').addEventListener('click',async()=>{try{library=await api('/api/seeds/undo',{});render();}catch(error){toast(error.message,true);}});
 try{await refresh();}catch(error){toast('Knihovna seedů: '+error.message,true);}
}
