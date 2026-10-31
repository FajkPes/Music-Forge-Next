"""Render real presets and measure level/spectrum; this is not a listening score."""
import json,sys,math
from pathlib import Path
import numpy as np
import soundfile as sf
from scipy import signal
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from catalogue import ROOT
from composer import compose,INSTRUMENTS
from audio_engine import render_stem,SR,ffmpeg
from balance import gain_limit

def loudness(path):
    result=ffmpeg(['-v','info','-i',path,'-af','loudnorm=I=-14:TP=-1.5:LRA=12:print_format=json','-f','null','-'])
    if result.returncode:raise RuntimeError(result.stderr.decode(errors='replace')[-1000:])
    text=result.stderr.decode(errors='replace');data=json.loads(text[text.rfind('{'):text.rfind('}')+1]);return float(data['input_i'])

def main():
    rows=[];directory=ROOT/'outputs/balance-validation';directory.mkdir(exist_ok=True)
    cases=[('syn:silk-pluck','lead',.65),('syn:glass-pluck','lead',.65),('syn:arp','arp',.30),('sf:0:11','lead',1.5),('ms:0:11','lead',1.5),('ms:17:71','bass',.8),('syn:supersaw','lead',.65),('syn:retro-lead','counter',.32)]
    for identity,role,before_gain in cases:
        plan=compose(dict(duration=20,genre='melodic-house',seed=951,space=0))
        track=next(t for t in plan['tracks'] if t['id']==role);track['instrument']=identity
        pitches=[36,43,40,45] if role=='bass' else [72,76,79,83]
        track['notes']=[[round(i*.25,4),.19,pitches[i%4],85,'normal'] for i in range(72)]
        folder=directory/(identity.replace(':','-')+'-'+role);folder.mkdir(exist_ok=True);render_stem(track,plan,folder)
        stem=np.load(folder/(role+'.npy'));old=stem*before_gain;limit=gain_limit(INSTRUMENTS[identity],role,track['notes']);gain=min(before_gain,limit);new=stem*gain
        old_path=folder/'before.wav';new_path=folder/'balanced.wav';sf.write(old_path,old,SR,subtype='PCM_24');sf.write(new_path,new,SR,subtype='PCM_24')
        frequencies,power=signal.welch(stem.mean(axis=1),SR,nperseg=4096)
        band=float(np.sum(power[(frequencies>=2000)&(frequencies<=6000)])/max(np.sum(power),1e-12))
        before=loudness(old_path);after=loudness(new_path)
        row=dict(instrument=identity,name=INSTRUMENTS[identity]['name'],role=role,notes_unchanged=True,old_slider=round(before_gain*100),new_slider=round(gain*100),input_lufs_before=before,input_lufs_after=after,change_db=round(after-before,2),energy_2_6khz_ratio=round(band,4));rows.append(row);print(json.dumps(row,ensure_ascii=False),flush=True)
    report=dict(method='Real 48 kHz stereo preset renders, repeated eighth-note pattern, BS.1770 measurement through FFmpeg loudnorm input_i. Band energy from Welch PSD. Does not estimate preference, annoyance, or listening safety.',tracks=rows)
    (ROOT/'research/balance-analysis.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__':main()
