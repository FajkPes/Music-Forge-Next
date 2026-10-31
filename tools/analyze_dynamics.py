"""Read-only loudness-envelope comparison; RMS dynamics are explicitly not LUFS."""
from pathlib import Path
import json,sys
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from analyze_library import ROOT,decode,SR

def measure(path):
 x=decode(path);n=len(x);hop=SR//2;window=SR*3
 rms=np.array([np.sqrt(np.mean(x[i:min(i+window,n)].astype('float64')**2)+1e-15) for i in range(0,max(1,n-window+1),hop)])
 db=20*np.log10(rms+1e-12);active=db[db>max(db)-35]
 p10,p50,p90=np.quantile(active,[.1,.5,.9]);rel=db-p90
 return dict(duration=n/SR,p10_dbfs=round(float(p10),2),median_dbfs=round(float(p50),2),p90_dbfs=round(float(p90),2),
   contrast_p90_p10_db=round(float(p90-p10),2),quiet_to_loud_db=round(float(np.quantile(active,.95)-np.quantile(active,.2)),2),
   intro_relative_db=round(float(np.median(rel[:max(1,len(rel)//12)])),2),
   rms_3s_relative_db=[round(float(v),2) for v in rel],hop_seconds=.5,window_seconds=3)

def main():
 src=json.loads((ROOT/'research/analysis.json').read_text('utf-8'));rows=[]
 for t in src['tracks']:
  rows.append(dict(name=t['name'],**measure(t['file'])))
 generated=[]
 for p in (ROOT/'outputs').glob('*/project.json'):
  meta=json.loads(p.read_text('utf-8'));wav=p.parent/'master.wav'
  if wav.exists():generated.append(dict(project=p.parent.name,genre=meta['plan']['genre'],**measure(wav)))
 report=dict(method='3-second full-track stereo RMS, 0.5-second hop, gate 35 dB below the loudest window. No local normalization. These are RMS dynamics, not LUFS or manually annotated drops.',tracks=rows,generated_before=generated,
   reference_contrast_median_db=round(float(np.median([r['contrast_p90_p10_db'] for r in rows])),2),reference_intro_median_db=round(float(np.median([r['intro_relative_db'] for r in rows])),2))
 (ROOT/'research/dynamics.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({k:v for k,v in report.items() if k not in ['tracks','generated_before']}),flush=True)
 print('Generated before:',[(r['genre'],r['contrast_p90_p10_db'],r['intro_relative_db']) for r in generated],flush=True)

if __name__=='__main__':main()
