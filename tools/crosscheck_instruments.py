"""Independent CLAP text/audio retrieval check; cosine similarity is NOT a probability."""
from pathlib import Path
import os,sys,json,time
ROOT=Path(__file__).resolve().parents[1]
os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
sys.path.insert(0,str(ROOT/'tools'))
from analyze_library import decode,SR
import numpy as np
from scipy.signal import resample_poly
import torch
from transformers import ClapModel,ClapProcessor

LABELS=[
 ('Akustický klavír','acoustic piano'),('Elektrické piano / Rhodes','electric piano or Rhodes keyboard'),
 ('Akustická kytara','acoustic guitar'),('Elektrická kytara','electric guitar'),('Zkreslená kytara','distorted electric guitar'),
 ('Živá bicí sada','acoustic drum kit'),('Elektronické bicí','electronic drum machine'),('Perkuse','hand percussion and shaker'),
 ('Elektrická basa','electric bass guitar'),('Subbasa / synth basa','deep electronic synthesizer bass'),
 ('Synth lead','electronic synthesizer lead melody'),('Synth pad','ambient synthesizer pads'),
 ('Pluck / arpeggio','plucked synthesizer arpeggio'),('Zvony / mallety','bells or marimba'),
 ('Smyčce','orchestral string ensemble'),('Housle','solo violin'),('Žestě','brass section and trumpet'),
 ('Saxofon','saxophone'),('Flétna','flute'),('Varhany','organ keyboard'),
 ('Ženský zpěv','female singing vocals'),('Mužský zpěv','male singing vocals'),('Rap','rapping vocals'),
 ('Sbor','choir singing'),('Orchestr','symphony orchestra'),('Efekty / přechody','electronic sound effects and risers')]

def vector(value):
 if isinstance(value,torch.Tensor):return value
 if hasattr(value,'pooler_output'):return value.pooler_output
 return value[0]

def main():
 torch.set_num_threads(min(6,os.cpu_count() or 2))
 processor=ClapProcessor.from_pretrained(ROOT/'research/clap',local_files_only=True)
 model=ClapModel.from_pretrained(ROOT/'research/clap',local_files_only=True).eval()
 texts=[f'The sound of {description} playing music.' for _,description in LABELS]
 with torch.inference_mode():
  text=vector(model.get_text_features(**processor(text=texts,return_tensors='pt',padding=True)))
  text=torch.nn.functional.normalize(text,dim=-1)
 path=ROOT/'research/analysis.json';report=json.loads(path.read_text('utf-8'))
 started=time.monotonic()
 for i,track in enumerate(report['tracks']):
  if 'clap_instrument_ranking' in track:continue
  mono=decode(track['file']).mean(axis=1);clips=[]
  for start in track['tag_windows_seconds']:
   x=mono[round(start*SR):round(start*SR)+10*SR]
   clips.append(resample_poly(x,3,1).astype('float32'))
  inputs=processor(audio=clips,sampling_rate=48000,return_tensors='pt')
  with torch.inference_mode():
   embedding=vector(model.get_audio_features(**inputs));embedding=torch.nn.functional.normalize(embedding,dim=-1)
   similarity=(embedding@text.T).numpy()
  means=similarity.mean(axis=0)
  track['clap_instrument_ranking']=[dict(label=LABELS[int(j)][0],cosine=round(float(means[j]),4),windows=[round(float(x),4) for x in similarity[:,j]]) for j in np.argsort(means)[::-1][:8]]
  report['instrument_crosscheck']={'model':'laion/clap-htsat-unfused','method':'26 fixed instrument descriptions, normalized text/audio cosine, 3 x 10 second windows at 48 kHz. Ranked hypotheses only; no calibrated probabilities or source isolation.','completed':sum('clap_instrument_ranking'in t for t in report['tracks']),'seconds':round(time.monotonic()-started,2)}
  tmp=path.with_suffix('.next.json');tmp.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');tmp.replace(path)
  print(f"{i+1}/60 | {track['name'][:65]} | "+', '.join(t['label']+':'+str(t['cosine']) for t in track['clap_instrument_ranking'][:4]),flush=True)
 print('CLAP crosscheck complete',flush=True)

if __name__=='__main__':main()
