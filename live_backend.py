"""Immutable single-track previews and encoding of the browser's exact live mix."""
import copy,json,math,struct,time,threading,shutil,hashlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as np
from audio_engine import render_stem,stem_fingerprint,ffmpeg,SR
from composer import normalize_settings,INSTRUMENTS,midi_bytes
from catalogue import ROOT

POOL=ThreadPoolExecutor(max_workers=2,thread_name_prefix='live-track')
LATEST={};LOCK=threading.Lock()

def prepare_track(project_directory,role,instrument,tone):
    if not (project_directory/'project.json').exists():raise ValueError('Pracovní data této skladby už nejsou dostupná. Ulož nastavení projektu a skladbu znovu vytvoř.')
    base=json.loads((project_directory/'project.json').read_text('utf-8'))
    plan=copy.deepcopy(base['plan']);track=next((t for t in plan['tracks'] if t['id']==role),None)
    if track is None:raise ValueError('Neznámá stopa.')
    clean=normalize_settings(dict(plan['settings'],instruments={role:instrument},tone={role:tone}))
    if role not in clean['instruments']:raise ValueError('Nástroj neodpovídá této stopě.')
    track['instrument']=clean['instruments'][role]
    # Envelopes are rendered; the other three controls remain in the live graph.
    track['tone']=dict(clean['tone'][role],brightness=.5,drive=0,space=0)
    # Legacy projects receive the section curve in the browser. A replacement
    # stem must use the same convention, otherwise that track gets it twice.
    plan['_skip_arrangement_gain']=not base['render'].get('arrangement_gain_baked',False)
    plan['_keep_legacy_tail_gap']=base['render'].get('arrangement_gain_baked',False) and not base['render'].get('tail_gain_fixed',False)
    digest=stem_fingerprint(track,plan)
    return plan,track,digest

def request_track(directory,role,instrument,tone,jobs,lock):
    plan,track,digest=prepare_track(directory,role,instrument,tone)
    key=(str(directory),role);jobid=hashlib.sha256((str(directory)+role+digest).encode()).hexdigest()
    # Selecting A again while A/B are pending must make A current even when
    # its existing job is reused. Never nest LOCK and the server state lock.
    with LOCK:LATEST[key]=jobid
    with lock:
        existing=jobs.get(jobid)
        if existing and (existing['state']=='running' or (existing['state']=='done' and (directory/'live'/digest/(role+'.npy')).exists())):return existing
        jobs[jobid]=dict(id=jobid,state='running',kind='track',progress=0,project=directory.name,role=role,message='Načítám zvuk stopy…')
    def work():
        try:
            with LOCK:
                if LATEST.get(key)!=jobid:
                    with lock:jobs[jobid].update(state='cancelled')
                    return
            target=directory/'live'/digest;target.mkdir(parents=True,exist_ok=True)
            render_stem(track,plan,target)
            with lock:jobs[jobid].update(state='done',progress=1,url=f'/stems/{directory.name}/{role}/{digest}.wav')
            # Bound disposable previews. Current buffers already live in browser RAM.
            files=[p for p in (directory/'live').glob('*/*.npy') if p.is_file()]
            total=sum(p.stat().st_size for p in files)
            for p in sorted(files,key=lambda p:p.stat().st_mtime):
                if total<=1.1*1024**3:break
                if p.parent==target or time.time()-p.stat().st_mtime<30:continue
                try:
                    size=p.stat().st_size
                    assert p.parent.resolve().is_relative_to((directory/'live').resolve())
                    shutil.rmtree(p.parent);total-=size
                except OSError:pass
        except Exception as error:
            with lock:jobs[jobid].update(state='error',message=str(error))
    POOL.submit(work)
    return jobs[jobid]

def wav_header(npy):
    with npy.open('rb') as f:
        version=np.lib.format.read_magic(f)
        reader=np.lib.format.read_array_header_1_0 if version==(1,0) else np.lib.format.read_array_header_2_0
        shape,fortran,dtype=reader(f)
        offset=f.tell()
    if dtype!=np.dtype('float32') or fortran or len(shape)!=2 or shape[1]!=2:raise ValueError('Neplatná stopa.')
    size=shape[0]*8
    header=struct.pack('<4sI4s4sIHHIIHH4sI',b'RIFF',36+size,b'WAVE',b'fmt ',16,3,2,SR,SR*8,8,32,b'data',size)
    return header,offset,size

def export_mix(raw,metadata,directory,export_id,progress):
    start=time.monotonic();base=json.loads((directory/'project.json').read_text('utf-8'));plan=copy.deepcopy(base['plan'])
    supplied=normalize_settings(dict(plan['settings'],**{k:metadata.get('settings',{}).get(k,{}) for k in ['instruments','mix','tone','section_levels']}))
    plan['title']=str(metadata.get('settings',{}).get('title',plan['title'])).strip()[:100] or 'Nová skladba'
    plan['settings']['title']=plan['title']
    for key in ['instruments','mix','tone','section_levels']:plan['settings'][key]=supplied[key]
    for t in plan['tracks']:
        if t['id'] in supplied['instruments']:t['instrument']=supplied['instruments'][t['id']]
        t['tone']=supplied['tone'][t['id']]
        if t['id'] in supplied['mix']:t.update(supplied['mix'][t['id']])
    count=round(plan['duration']*SR)
    if raw.stat().st_size!=count*8:raise ValueError('Nesouhlasí délka živého mixu.')
    output=directory/'exports';output.mkdir(exist_ok=True)
    count_path=output/'.export_count'
    try:prev_count=int(count_path.read_text('utf-8').strip()) if count_path.exists() else 0
    except ValueError:prev_count=0
    supplied_ver=metadata.get('version')
    export_version=max(prev_count+1,int(supplied_ver)) if isinstance(supplied_ver,(int,float)) and supplied_ver>=1 else prev_count+1
    count_path.write_text(str(export_version),encoding='utf-8')
    wav=output/(export_id+'.wav');opus=output/(export_id+'.opus')
    progress(.25,'Zapisuji přesný živý mix do WAV…')
    result=ffmpeg(['-v','error','-y','-f','f32le','-ar',SR,'-ac',2,'-i',raw,'-c:a','pcm_s24le',wav])
    if result.returncode:raise RuntimeError(result.stderr.decode(errors='replace')[-1000:])
    progress(.6,'Kóduji Opus 160 kb/s…')
    result=ffmpeg(['-v','error','-y','-i',wav,'-c:a','libopus','-b:a','160k','-vbr','off','-application','audio',opus])
    if result.returncode:raise RuntimeError(result.stderr.decode(errors='replace')[-1000:])
    data=np.memmap(raw,mode='r',dtype='<f4',shape=(count,2));wave=[];rms=[]
    for a in range(0,count,max(1,round(count/1200))):
        b=data[a:a+max(1,round(count/1200))]
        wave.append(round(float(np.max(np.abs(b))),6));rms.append(round(float(np.sqrt(np.mean(b.astype('float64')**2))),6))
    peak=max(wave,default=0);del b,data
    stats=dict(waveform=wave,rms_waveform=rms,peak_dbfs=round(20*math.log10(max(peak,1e-12)),3),sample_rate=SR,bits=24,opus_bitrate=160000,normalization_type='exact_live_graph')
    (output/(export_id+'.mid')).write_bytes(midi_bytes(plan))
    credits='Music Forge Next · '+plan['title']+'\n\n'+ '\n'.join(sorted({INSTRUMENTS[t['instrument']]['source'] for t in plan['tracks'] if t['notes']}))+'\n\n'
    credits+='Salamander Grand Piano by Alexander Holm; SF2 adaptation Roberto / FreePats. CC BY 3.0. https://freepats.zenvoid.org/Piano/acoustic-grand-piano.html\n\n'
    credits+=(ROOT/'assets/musescore/MuseScore_General_License.md').read_text('utf-8')
    (output/(export_id+'.txt')).write_text(credits,encoding='utf-8')
    result=dict(plan=plan,render=dict(base['render'],master=stats),export_id=export_id,export_version=export_version,seconds=round(time.monotonic()-start,2))
    (output/(export_id+'.json')).write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8')
    raw.unlink(missing_ok=True)
    # Keep two complete exports; generated audio elsewhere is never touched.
    previous=sorted(output.glob('*.json'),key=lambda p:p.stat().st_mtime,reverse=True)
    for p in previous[2:]:
        for ext in ['.json','.wav','.opus','.mid','.txt']:
            try:p.with_suffix(ext).unlink(missing_ok=True)
            except OSError:pass  # A Windows player may still have an old export open.
    progress(1,'Export je připravený.')
    return result
