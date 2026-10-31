"""Reproducible full-track DSP + sampled AST AudioSet tagging. Originals are read only."""
from pathlib import Path
import os
ROOT = Path(__file__).resolve().parents[1]
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
os.environ['NUMBA_CACHE_DIR'] = str(ROOT / 'research/numba-cache')
import argparse, hashlib, json, random, subprocess, time
import numpy as np
from scipy import signal, ndimage
import imageio_ffmpeg

SR = 16000
HOP = 512
NOTES = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']

def decode(path):
    p = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-v','error','-i',str(path),'-vn',
                        '-ac','2','-ar',str(SR),'-f','f32le','-'], capture_output=True, check=True)
    return np.frombuffer(p.stdout, dtype='<f4').reshape(-1,2)

def features(stereo):
    y = stereo.mean(axis=1)
    duration = len(y)/SR
    _, _, z = signal.stft(y, SR, nperseg=2048, noverlap=2048-HOP, boundary=None)
    mag = np.abs(z)
    power = mag**2
    frequencies = np.fft.rfftfreq(2048,1/SR)
    flux = np.maximum(0,np.diff(np.log1p(mag*500),axis=1)).mean(axis=0)
    onset = flux - ndimage.uniform_filter1d(flux,size=31)
    ac = signal.fftconvolve(onset, onset[::-1],mode='full')[len(onset)-1:]
    lags = np.arange(max(1,round(SR/HOP*60/190)),round(SR/HOP*60/65))
    scores = ac[lags] * np.exp(-.5*((60*SR/HOP/lags-120)/65)**2)
    order = np.argsort(scores)[::-1]
    bpm = 60*SR/HOP/lags[order[0]]
    frame_rms = np.sqrt(power.sum(axis=0))
    centroid = (mag*frequencies[:,None]).sum(axis=0)/(mag.sum(axis=0)+1e-9)
    midi = np.rint(69+12*np.log2(np.maximum(frequencies,1)/440)).astype(int)
    chroma = np.zeros((12,mag.shape[1]))
    for pc in range(12):
        mask = ((midi%12)==pc)&(frequencies>=65)&(frequencies<4000)
        chroma[pc] = mag[mask].sum(axis=0)
    profile = chroma.mean(axis=1)
    major = np.array([6.35,2.23,3.48,2.33,4.38,4.09,2.52,5.19,2.39,3.66,2.29,2.88])
    minor = np.array([6.33,2.68,3.52,5.38,2.6,3.53,2.54,4.75,3.98,2.69,3.34,3.17])
    keys = [(float(np.corrcoef(profile,np.roll(p,k))[0,1]),NOTES[k]+' '+mode)
            for mode,p in [('major',major),('minor',minor)] for k in range(12)]
    keys.sort(reverse=True)
    block = max(1,round(2*SR/HOP))
    descriptors=[]; energy=[]
    for start in range(0,mag.shape[1],block):
        sl=slice(start,start+block)
        c=chroma[:,sl].mean(axis=1); c=c/(np.linalg.norm(c)+1e-9)
        bands=np.array([power[(frequencies>=a)&(frequencies<b),sl].sum() for a,b in [(20,150),(150,800),(800,3000),(3000,8001)]])
        bands/=bands.sum()+1e-9
        energy.append(float(np.sqrt(np.mean(y[round(start*HOP):min(len(y),round((start+block)*HOP))]**2)+1e-12)))
        descriptors.append(np.r_[c,bands])
    desc=np.array(descriptors)
    novelty=np.linalg.norm(np.diff(ndimage.gaussian_filter1d(desc,1,axis=0),axis=0),axis=1)
    peaks,_=signal.find_peaks(novelty,distance=6,prominence=max(.035,float(np.std(novelty))*.7))
    # Recurrence is measured at >= 16 seconds: adjacent blocks are trivially similar.
    norm=desc/(np.linalg.norm(desc,axis=1,keepdims=True)+1e-9)
    similarity=norm@norm.T
    mask=np.abs(np.arange(len(desc))[:,None]-np.arange(len(desc)))>=8
    rms=float(np.sqrt(np.mean(stereo**2)))
    peak=float(np.max(np.abs(stereo)))
    bands_total=power.sum(axis=1)
    return dict(duration=round(duration,3), tempo_bpm=round(float(bpm),1),
      tempo_alternative=round(float(bpm/2 if bpm>120 else bpm*2),1),
      key_candidates=[{'key':k,'correlation':round(c,3)} for c,k in keys[:3]],
      rms_dbfs=round(20*np.log10(rms+1e-12),2),peak_dbfs=round(20*np.log10(peak+1e-12),2),
      crest_db=round(20*np.log10((peak+1e-9)/(rms+1e-9)),2),
      stereo_correlation=round(float(np.corrcoef(stereo.T)[0,1]),3),
      centroid_hz=round(float(np.median(centroid))),
      low_band_ratio=round(float(bands_total[(frequencies>=20)&(frequencies<150)].sum()/(bands_total.sum()+1e-12)),3),
      energy_2s=[round(e,5) for e in energy],
      section_candidates_seconds=[round(float((p+1)*block*HOP/SR),2) for p in peaks],
      long_range_similarity=round(float(similarity[mask].mean()),3) if mask.any() else 0,
      onset_density=round(float(len(signal.find_peaks(flux,prominence=max(.001,float(np.std(flux))*.5))[0])/duration),2))

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--count',type=int,default=60);parser.add_argument('--seed',type=int,default=20261030)
    args=parser.parse_args()
    import torch
    from transformers import ASTFeatureExtractor, ASTForAudioClassification
    torch.set_num_threads(min(6,os.cpu_count() or 2))
    extractor=ASTFeatureExtractor.from_pretrained(ROOT/'research/model',local_files_only=True)
    model=ASTForAudioClassification.from_pretrained(ROOT/'research/model',local_files_only=True).eval()
    all_files=[]
    for i in range(1,5):
        all_files.extend(p for p in Path(f'X:/_MUSIC/_2026/BEST OF THE BEST PART {i}').rglob('*') if p.suffix.lower() in {'.ogg','.opus','.mp3','.wav','.flac','.m4a'})
    all_files.sort(key=lambda p:str(p).lower()); random.Random(args.seed).shuffle(all_files)
    report_path=ROOT/'research/analysis.json'
    report=json.loads(report_path.read_text('utf-8')) if report_path.exists() else {'seed':args.seed,'population':len(all_files),'method':
      'Full-track 16 kHz stereo DSP. AST AudioSet sigmoid scores on 3 x 10 s at 18%, 50%, 80%; no source separation. Tempo/key/section boundaries are estimates, not ground truth. Scores are not calibrated probabilities. Selection: shuffled sorted audio paths, reject duplicate SHA-256 and tracks <45 s.', 'model':'MIT/ast-finetuned-audioset-10-10-0.4593','tracks':[]}
    seen={t['sha256'] for t in report['tracks']}
    instrument_words=('guitar','piano','keyboard','synthesizer','drum','bass','percussion','cymbal','hi-hat','snare','violin','string','cello','flute','brass','trumpet','saxophone','organ','harp','accordion','bell','xylophone','marimba','singing','rapping','choir','vocal','sampler','scratching','orchestra','wind instrument','trombone','clarinet','banjo','mandolin','ukulele')
    exclude={'Drum and bass','Computer keyboard','Bird vocalization, bird call, bird song','Whale vocalization','Singing bowl','Doorbell','Jingle bell','Bicycle bell','Church bell'}
    started=time.monotonic()
    for path in all_files:
        if len(report['tracks'])>=args.count: break
        digest=hashlib.file_digest(path.open('rb'),'sha256').hexdigest()
        if digest in seen: continue
        try:
            y=decode(path)
            if len(y)<45*SR: continue
            result=features(y)
            clips=[]; starts=[]
            mono=y.mean(axis=1)
            for pos in [.18,.5,.8]:
                start=min(len(mono)-10*SR,max(0,int(len(mono)*pos)))
                starts.append(round(start/SR,2));clips.append(mono[start:start+10*SR].copy())
            inputs=extractor(clips,sampling_rate=SR,return_tensors='pt')
            with torch.inference_mode():
                scores=model(**inputs).logits.sigmoid().numpy()
            means=scores.mean(axis=0)
            tags=[{'label':model.config.id2label[int(j)],'score':round(float(means[j]),4),'windows':[round(float(s),4) for s in scores[:,j]]}
                  for j in np.argsort(means)[::-1] if model.config.id2label[int(j)] not in exclude and any(w in model.config.id2label[int(j)].lower() for w in instrument_words)][:12]
            for tag in tags:tag['confidence']='weak' if tag['score']<.1 else ('moderate' if tag['score']<.4 else 'strong')
            general=[{'label':model.config.id2label[int(j)],'score':round(float(means[j]),4)} for j in np.argsort(means)[::-1][:12]]
            result.update(file=str(path),name=path.stem,sha256=digest,bytes=path.stat().st_size,tag_windows_seconds=starts,instrument_estimates=tags,audio_tags=general)
            report['tracks'].append(result);seen.add(digest)
            report['completed']=len(report['tracks']);report['processing_seconds']=round(time.monotonic()-started,1)
            report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
            print(f"{len(report['tracks'])}/{args.count} | {result['tempo_bpm']} BPM | {path.stem[:90]} | "+', '.join(t['label'] for t in tags[:4]),flush=True)
        except Exception as e:
            print('ERROR',str(path),repr(e),flush=True)
    print('Completed',len(report['tracks']),flush=True)
    if len(report['tracks'])<args.count: raise RuntimeError('Not enough successfully analyzed tracks')

if __name__=='__main__': main()
