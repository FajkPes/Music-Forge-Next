"""End-to-end regression renders, actual codec metadata and post-encode clipping checks."""
from pathlib import Path
import sys,json,time,argparse,copy
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import soundfile as sf
from composer import compose
from catalogue import ROOT,GENRES
from audio_engine import render,ffmpeg,SR,render_stem,INSTRUMENTS

def inspect(directory,duration):
 info=sf.info(directory/'master.wav');assert info.samplerate==SR and info.channels==2 and info.subtype=='PCM_24'
 assert info.frames==round(duration*SR),(info.frames,duration)
 peak=0;count=0;squares=0
 with sf.SoundFile(directory/'master.wav') as f:
  for b in f.blocks(blocksize=SR*5):
   assert np.isfinite(b).all();peak=max(peak,float(np.max(np.abs(b))));count+=len(b);squares+=float(np.sum(b*b))
 assert .001<peak<.93,peak
 decoded=ffmpeg(['-v','error','-i',directory/'master.opus','-f','f32le','-ar',SR,'-ac','2','-'])
 assert decoded.returncode==0
 x=np.frombuffer(decoded.stdout,dtype='<f4')
 assert abs(len(x)//2-round(duration*SR))<10
 opus_peak=float(np.max(np.abs(x)));assert opus_peak<1,opus_peak
 header=(directory/'master.opus').read_bytes();assert b'OpusHead' in header[:128]
 bitrate=(directory/'master.opus').stat().st_size*8/duration
 assert 159000<bitrate<170000,bitrate
 return dict(duration=duration,wav_peak_dbfs=round(20*np.log10(peak),2),opus_peak_dbfs=round(20*np.log10(opus_peak),2),opus_container_bitrate=round(bitrate),wav_frames=count,rms_dbfs=round(10*np.log10(squares/(count*2)),2))

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--all',action='store_true');args=parser.parse_args()
 directory=ROOT/'outputs/audio-validation';directory.mkdir(exist_ok=True)
 report=[]
 genres=[g['id'] for g in GENRES] if args.all else ['melodic-house','future-bass','liquid-dnb','synthwave','pop','kpop','rock','lofi','jazz','acoustic','piano','classical','ambient']
 for genre in genres:
  p=compose({'genre':genre,'duration':30,'seed':431207})
  r=render(p,directory)
  item=dict(genre=genre,render_seconds=r['render_seconds'],**inspect(directory,30));report.append(item)
  print(json.dumps(item),flush=True)
 # A real default-length song, then a gain-only edit must reuse every audio stem.
 p=compose({'genre':'melodic-house','duration':210,'seed':431207})
 r=render(p,directory);report.append(dict(genre='default-210',render_seconds=r['render_seconds'],**inspect(directory,210)))
 q=copy.deepcopy(p);q['tracks'][3]['gain']*=.8
 cached=render(q,directory,previous=r);assert len(cached['reused_stems'])==8,cached['reused_stems']
 report.append(dict(genre='gain-only-edit-210',render_seconds=cached['render_seconds'],reused=len(cached['reused_stems']),**inspect(directory,210)))
 # Changing a single instrument must preserve all other rendered stems.
 q['tracks'][3]['instrument']='syn:glass-pluck'
 changed=render(q,directory,previous=cached);assert len(changed['reused_stems'])==7,changed['reused_stems']
 report.append(dict(genre='one-instrument-edit-210',render_seconds=changed['render_seconds'],reused=len(changed['reused_stems']),**inspect(directory,210)))
 # Test every macro against actual PCM on a sample, synth, bass and a drum kit.
 macros=[]
 for role,instrument in [('lead','sf:0:73'),('lead','syn:warm-pluck'),('bass','syn:round-bass'),('drums','sf:128:25')]:
  plan=compose({'duration':20,'genre':'melodic-house','seed':14,'space':0})
  t=next(t for t in plan['tracks'] if t['id']==role)
  t['instrument']=instrument;t['notes']=[[.2,.8,60 if role!='bass' else 36,90,'normal']]
  if role=='drums':t['notes']=[[.2,.8,38,100,'normal']]
  t['tone']={'attack':.5,'release':.5,'brightness':.5,'drive':0,'space':0}
  render_stem(t,plan,directory);baseline=np.load(directory/(role+'.npy')).copy()
  for macro in t['tone']:
   altered=copy.deepcopy(t);altered['tone'][macro]=.9 if macro!='brightness' else .05
   render_stem(altered,plan,directory);after=np.load(directory/(role+'.npy'))
   difference=float(np.sqrt(np.mean((baseline-after)**2)))
   assert difference>1e-6,(instrument,macro,difference)
   macros.append(dict(instrument=instrument,macro=macro,pcm_rms_difference=difference))
 (ROOT/'research/audio-validation.json').write_text(json.dumps(dict(renders=report,macros=macros),indent=2),encoding='utf-8')
 print('All audio checks passed',len(report),'renders and',len(macros),'macro checks',flush=True)

if __name__=='__main__':main()
