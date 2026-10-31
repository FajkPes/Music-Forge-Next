"""Audibility scan of every shipped preset using the actual synthesis engine."""
from pathlib import Path
import sys,json,collections
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from catalogue import ROOT,load_instruments
from audio_engine import Fluid,SR,synth_note

def main():
 rows=[];banks=collections.defaultdict(list)
 for inst in load_instruments():
  if inst['engine']=='sample':banks[inst['sf_path']].append(inst)
  else:
   a=synth_note(inst,48 if inst['kind'] in ['bass','sub','reese','growl','acid'] else 69,1,100,{},120,'rise',1)
   rms=float(np.sqrt(np.mean(a.astype('float64')**2)));assert rms>1e-7,inst['id']
   rows.append(dict(id=inst['id'],name=inst['name'],rms=rms))
 for source,instruments in banks.items():
  f=Fluid(instruments[0],{},'lead',0)
  try:
   for inst in instruments:
    channel=9 if inst['bank']==128 else 0;f.channel=channel
    f.lib.fluid_synth_all_sounds_off(f.synth,0);f.lib.fluid_synth_all_sounds_off(f.synth,9)
    code=f.lib.fluid_synth_program_select(f.synth,channel,f.sfid,inst['bank'],inst['program']);assert code>=0,inst['id']
    f.lib.fluid_synth_cc(f.synth,channel,2,100 if 'Expr.' in inst['name'] else 0)
    notes=[36,38,42,49,60] if channel==9 else [36 if inst['group']=='Basy' else 60]
    for n in notes:f.lib.fluid_synth_noteon(f.synth,channel,n,100)
    a=np.zeros((SR*2,2),dtype='float32');f.lib.fluid_synth_write_float(f.synth,len(a),a.ctypes.data,0,2,a.ctypes.data,1,2)
    rms=float(np.sqrt(np.mean(a.astype('float64')**2)))
    row=dict(id=inst['id'],name=inst['name'],rms=round(rms,8));rows.append(row)
    if rms<1e-7:print('SILENT',inst['id'],inst['name'],flush=True)
  finally:f.close()
  print('Scanned',source,len(instruments),flush=True)
 path=ROOT/'research/preset-validation.json';path.write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
 print('TOTAL',len(rows),'SILENT',len([r for r in rows if r['rms']<1e-7]),flush=True)
 assert all(r['rms']>1e-7 for r in rows),'A shipped preset is silent'

if __name__=='__main__':main()
