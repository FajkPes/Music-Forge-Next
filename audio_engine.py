"""48 kHz stereo sampler/synth rendering, cached stems, sidechain and measured mastering."""
from pathlib import Path
import ctypes as C
import hashlib, json, math, os, subprocess, threading, time
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np
from scipy import signal
import soundfile as sf
import imageio_ffmpeg
from catalogue import ROOT
from composer import INSTRUMENTS

SR=48000
ENGINE_VERSION=5
SIDECHAIN_BASS_GENRES={'dance-pop','electropop','kpop','disco','afro-house','reggaeton','trap','phonk'}
_dll=None
_dll_dir=None
_dll_lock=threading.Lock()
CREATE_NO_WINDOW=0x08000000 if os.name=='nt' else 0

def ffmpeg(args,timeout=180):
    return subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-hide_banner','-nostdin',*map(str,args)],capture_output=True,
                          timeout=timeout,creationflags=CREATE_NO_WINDOW)

def fluid_library():
    global _dll,_dll_dir
    with _dll_lock:
        if _dll:return _dll
        path=next((ROOT/'runtime/fluidsynth').rglob('libfluidsynth-3.dll'))
        if os.name=='nt':_dll_dir=os.add_dll_directory(str(path.parent))
        lib=C.CDLL(str(path))
        specs={
          'new_fluid_settings':(C.c_void_p,[]),'delete_fluid_settings':(None,[C.c_void_p]),
          'fluid_settings_setnum':(C.c_int,[C.c_void_p,C.c_char_p,C.c_double]),
          'fluid_settings_setint':(C.c_int,[C.c_void_p,C.c_char_p,C.c_int]),
          'fluid_settings_setstr':(C.c_int,[C.c_void_p,C.c_char_p,C.c_char_p]),
          'new_fluid_synth':(C.c_void_p,[C.c_void_p]),'delete_fluid_synth':(None,[C.c_void_p]),
          'fluid_synth_sfload':(C.c_int,[C.c_void_p,C.c_char_p,C.c_int]),
          'fluid_synth_program_select':(C.c_int,[C.c_void_p,C.c_int,C.c_int,C.c_int,C.c_int]),
          'fluid_synth_set_gen':(C.c_int,[C.c_void_p,C.c_int,C.c_int,C.c_float]),
          'fluid_synth_cc':(C.c_int,[C.c_void_p,C.c_int,C.c_int,C.c_int]),
          'fluid_synth_all_sounds_off':(C.c_int,[C.c_void_p,C.c_int]),
          'fluid_synth_noteon':(C.c_int,[C.c_void_p,C.c_int,C.c_int,C.c_int]),
          'fluid_synth_noteoff':(C.c_int,[C.c_void_p,C.c_int,C.c_int]),
          'fluid_synth_write_float':(C.c_int,[C.c_void_p,C.c_int,C.c_void_p,C.c_int,C.c_int,C.c_void_p,C.c_int,C.c_int])}
        for name,(ret,args) in specs.items():
            f=getattr(lib,name);f.restype=ret;f.argtypes=args
        _dll=lib
        return lib

class Fluid:
    def __init__(self,instrument,tone,role,space):
        self.lib=fluid_library();l=self.lib;self.settings=l.new_fluid_settings();self.synth=None
        for k,v in [('synth.sample-rate',SR),('synth.gain',.48),('synth.reverb.room-size',.62),
                    ('synth.reverb.damp',.55),('synth.reverb.width',70.),('synth.reverb.level',max(0,min(.42,space)))]:
            l.fluid_settings_setnum(self.settings,k.encode(),v)
        for k,v in [('synth.polyphony',192),('synth.cpu-cores',1),('synth.chorus.active',0),('synth.reverb.active',int(space>.001)),('synth.threadsafe-api',0)]:
            l.fluid_settings_setint(self.settings,k.encode(),v)
        self.synth=l.new_fluid_synth(self.settings)
        if not self.synth:raise RuntimeError('FluidSynth se nepodařilo inicializovat.')
        sfid=l.fluid_synth_sfload(self.synth,str(ROOT/instrument['sf_path']).encode('utf-8'),0)
        self.sfid=sfid
        if sfid<0:raise RuntimeError('Zvuková banka se nepodařila načíst.')
        self.channel=9 if role=='drums' else 0
        self.expressive=instrument['source'].startswith('MuseScore') and 'Expr.' in instrument['name']
        if l.fluid_synth_program_select(self.synth,self.channel,sfid,instrument['bank'],instrument['program'])<0:
            raise ValueError('Neplatný preset '+instrument['id'])
        if self.expressive:l.fluid_synth_cc(self.synth,self.channel,2,90)
        # SoundFont generator offsets: 1200 timecents = 2x the original time.
        l.fluid_synth_set_gen(self.synth,self.channel,34,(tone.get('attack',.5)-.5)*6000)
        l.fluid_synth_set_gen(self.synth,self.channel,38,(tone.get('release',.5)-.5)*4800)
        l.fluid_synth_set_gen(self.synth,self.channel,8,(tone.get('brightness',.5)-.5)*3200)
    def render(self,output,notes):
        events=[]
        for start,duration,note,velocity,*_ in notes:
            events.extend([(int(start*SR),1,note,velocity),(int((start+duration)*SR),0,note,0)])
        events.sort();position=0;size=len(output)
        for sample,kind,note,velocity in events+[(size,0,0,0)]:
            sample=min(size,max(position,sample))
            while position<sample:
                n=min(8192,sample-position)
                address=output.ctypes.data+position*8
                result=self.lib.fluid_synth_write_float(self.synth,n,address,0,2,address,1,2)
                if result<0:raise RuntimeError('FluidSynth render selhal.')
                position+=n
            if kind:
                if self.expressive:self.lib.fluid_synth_cc(self.synth,self.channel,2,velocity)
                self.lib.fluid_synth_noteon(self.synth,self.channel,note,velocity)
            else:self.lib.fluid_synth_noteoff(self.synth,self.channel,note)
    def close(self):
        if self.synth:self.lib.delete_fluid_synth(self.synth);self.synth=None
        if self.settings:self.lib.delete_fluid_settings(self.settings);self.settings=None

def oscillator(phase,freq,kind,colour):
    # A per-pitch harmonic-limited wavetable avoids the aliasing of raw saw/square waves.
    size=2048;angle=np.arange(size)*2*np.pi/size
    table=np.zeros(size)
    maximum=min(44,max(1,int(min(16000,SR*.44)/freq)))
    cutoff=2+colour*25
    for h in range(1,maximum+1):
        if kind=='pulse' and h%2==0:continue
        amplitude=(1/h)*math.exp(-h/cutoff)
        if kind in ['pad','pluck','bass']:amplitude*=math.exp(-h/(2+colour*10))
        if kind=='organ':amplitude=([1,.5,.65,.1,.25,.08,.04,.05][h-1] if h<=8 else 0)
        table+=np.sin(angle*h)*amplitude
    table/=max(1,np.max(np.abs(table)))
    idx=(phase*size)%(size)
    return np.interp(idx,np.arange(size+1),np.r_[table,table[0]]).astype(np.float32)

def synth_note(inst,note,duration,velocity,tone,bpm,art,seed):
    kind=inst['kind'];pid=inst['id'];colour=max(0,min(1,inst['colour']+(tone.get('brightness',.5)-.5)*.7))
    attack_base=.24 if kind=='pad' else (.026 if pid=='syn:brass' else (.014 if kind in ['saw','pulse','organ'] else .004))
    release_base=.78 if kind=='pad' else (.30 if kind in ['bell','fm'] else .095)
    attack=attack_base*2**((tone.get('attack',.5)-.5)*6)
    release=release_base*2**((tone.get('release',.5)-.5)*4)
    count=max(1,int((duration+release)*SR));t=np.arange(count,dtype=np.float32)/SR
    freq=440*2**((note-69)/12);phase=t*freq
    width=inst.get('width',.2)
    if kind=='noise':
        rng=np.random.default_rng(seed);noise_l=rng.standard_normal(count).astype(np.float32);noise_r=rng.standard_normal(count).astype(np.float32)
        # Crossfade several filtered noise bands, then shape the transition.
        low_l=signal.sosfilt(signal.butter(2,480,fs=SR,output='sos'),noise_l).astype(np.float32)
        mid_l=signal.sosfilt(signal.butter(2,[480,3200],fs=SR,btype='bandpass',output='sos'),noise_l).astype(np.float32)
        high_l=signal.sosfilt(signal.butter(2,7800,fs=SR,output='sos'),noise_l).astype(np.float32)
        low_r=signal.sosfilt(signal.butter(2,480,fs=SR,output='sos'),noise_r).astype(np.float32)
        mid_r=signal.sosfilt(signal.butter(2,[480,3200],fs=SR,btype='bandpass',output='sos'),noise_r).astype(np.float32)
        high_r=signal.sosfilt(signal.butter(2,7800,fs=SR,output='sos'),noise_r).astype(np.float32)
        curve=np.linspace(0,1,count,dtype=np.float32)
        if art=='fall':curve=curve[::-1]
        sweep=curve**1.6
        left=(low_l*(1-sweep)+mid_l*(.65*sweep*(1-.4*sweep))+high_l*(sweep**2))*curve*.2
        right=(low_r*(1-sweep)+mid_r*(.65*sweep*(1-.4*sweep))+high_r*(sweep**2))*curve*.2
    elif kind=='sub':
        punch_phase=phase+(freq*.22*.016)*(1-np.exp(-t/.016))
        left=(np.sin(2*np.pi*punch_phase)+.13*np.sin(4*np.pi*punch_phase)+.035*np.sin(6*np.pi*punch_phase)).astype(np.float32)
        right=left.copy()
    elif kind in ['fm','bell']:
        if pid=='syn:rhodes':
            mod=np.sin(2*np.pi*phase)*(.35+colour*.85)*np.exp(-t/(.35+duration*.5))
            tine=np.sin(2*np.pi*phase*7)*(.16+colour*.22)*np.exp(-t/.065)
            body=np.sin(2*np.pi*phase+mod)*.76+tine
            trem=.06*width*np.sin(2*np.pi*t*4.2)
            left=(body*(1+trem)).astype(np.float32);right=(body*(1-trem)).astype(np.float32)
        elif pid=='syn:tropical':
            strike=np.sin(2*np.pi*phase*4)*(.42+colour*.5)*np.exp(-t/.032)
            body=np.sin(2*np.pi*phase+strike)*.8+.14*np.sin(2*np.pi*phase*2)*np.exp(-t/.14)
            left=body.astype(np.float32);right=np.roll(left,min(count-1,19)) if count>20 else left.copy()
        elif pid=='syn:fm-bass':
            idx=(1.1+colour*2.8)*np.exp(-t/.075)+.18
            body=np.sin(2*np.pi*phase+idx*np.sin(2*np.pi*phase*2))*.78+.24*np.sin(2*np.pi*phase)
            left=np.tanh(body*1.25).astype(np.float32)*.82;right=left.copy()
        elif pid=='syn:shimmer':
            idx=(.22+colour*1.4)*(1-.45*np.exp(-t/.18))
            l_car=np.sin(2*np.pi*phase*.998+idx*np.sin(2*np.pi*phase*2.002))*.62+.22*np.sin(2*np.pi*phase*2.003+.4)
            r_car=np.sin(2*np.pi*phase*1.002+idx*np.sin(2*np.pi*phase*1.998)+.3)*.62+.22*np.sin(2*np.pi*phase*1.997+1.1)
            left=l_car.astype(np.float32);right=r_car.astype(np.float32)
        else:
            ratio=2.0 if kind=='fm' else (3.0 if pid=='syn:music-box' else 2.756)
            index=(.25+colour*2.8)*np.exp(-t/(.14+duration*.42))
            base_l=np.sin(2*np.pi*phase*(1-.0012*width)+index*np.sin(2*np.pi*phase*ratio))*.72
            base_r=np.sin(2*np.pi*phase*(1+.0012*width)+.12*width+index*np.sin(2*np.pi*phase*ratio))*.72
            overtone=.12*np.sin(2*np.pi*phase*(3.01 if kind=='bell' else 2))*np.exp(-t/.55)
            left=(base_l+overtone).astype(np.float32);right=(base_r+overtone).astype(np.float32)
    elif kind in ['growl','reese','acid']:
        if kind=='reese':
            l_raw=(oscillator(phase*.994,freq,'saw',colour)+oscillator(phase,freq,'saw',colour)*.8+oscillator(phase*1.006+.21,freq,'saw',colour)*.65)/2.1
            r_raw=(oscillator(phase*1.006+.13,freq,'saw',colour)+oscillator(phase,freq,'saw',colour)*.8+oscillator(phase*.994+.47,freq,'saw',colour)*.65)/2.1
            sub=np.sin(2*np.pi*phase).astype(np.float32)*.32
            left=l_raw+sub;right=r_raw+sub
        elif kind=='growl':
            left=oscillator(phase*.997,freq,'saw',colour);right=oscillator(phase*1.003+.18,freq,'saw',colour)
            motion=.5+.5*np.sin(2*np.pi*t*bpm/60*2)
            left=np.tanh((left+.5*np.sin(2*np.pi*phase))*(1+motion*3))*.65
            right=np.tanh((right+.5*np.sin(2*np.pi*phase))*(1+motion*3))*.65
        else:
            raw=oscillator(phase,freq,'saw',min(1,colour+.2))
            low=signal.sosfilt(signal.butter(2,min(SR*.42,max(140,freq*2.2)),fs=SR,output='sos'),raw).astype(np.float32)
            res_center=min(SR*.4,max(320,freq*(3.2+colour*5.5)))
            res_bw=max(90,res_center*.28)
            peak=signal.sosfilt(signal.butter(2,[max(80,res_center-res_bw),min(SR*.44,res_center+res_bw)],fs=SR,btype='bandpass',output='sos'),raw).astype(np.float32)
            sweep=np.exp(-t*7.2).astype(np.float32)
            left=np.tanh((low*(.55+.45*(1-sweep))+raw*(.42*sweep)+peak*(1.35*sweep*(.35+colour)))*1.35)*.72
            right=left.copy()
    else:
        p_phase=phase
        if pid=='syn:slap-bass':
            p_phase=phase+(freq*.48*.018)*(1-np.exp(-t/.018))
        if kind in ['pluck','bass'] or pid in ['syn:chord-stab','syn:brass']:
            hi_c=min(1,colour+.34);lo_c=max(.04,colour*.52)
            l_hi=oscillator(p_phase*(1-.0035*width),freq,kind,hi_c);r_hi=oscillator(p_phase*(1+.0035*width)+.11*width,freq,kind,hi_c)
            l_lo=oscillator(p_phase*(1-.0035*width),freq,kind,lo_c);r_lo=oscillator(p_phase*(1+.0035*width)+.11*width,freq,kind,lo_c)
            if pid=='syn:brass':
                f_env=np.minimum(1,t/.045)*np.exp(-np.maximum(0,t-.045)/(.35+duration*.6))
            else:
                f_decay=.085 if pid=='syn:slap-bass' else (.11+duration*.22 if kind=='pluck' else .14+duration*.28)
                f_env=np.exp(-t/f_decay)
            f_env=f_env.astype(np.float32)
            left=l_lo*(1-f_env)+l_hi*f_env;right=r_lo*(1-f_env)+r_hi*f_env
            if pid in ['syn:chord-stab','syn:brass']:
                left=(left+oscillator(p_phase*1.0055+.31,freq,kind,colour)*.48)/1.4
                right=(right+oscillator(p_phase*.9945+.67,freq,kind,colour)*.48)/1.4
        elif kind in ['saw','pad']:
            d1=.0042*max(.15,width);d2=.0078*max(.15,width)
            left=(oscillator(p_phase*(1-d1),freq,kind,colour)+oscillator(p_phase*(1+d1*.5)+.23,freq,kind,colour)*.58+oscillator(p_phase*(1-d2)+.51,freq,kind,colour)*.42)/1.68
            right=(oscillator(p_phase*(1+d1)+.11*width,freq,kind,colour)+oscillator(p_phase*(1-d1*.5)+.61,freq,kind,colour)*.58+oscillator(p_phase*(1+d2)+.83,freq,kind,colour)*.42)/1.68
            if pid=='syn:choir-pad':
                form1=signal.sosfilt(signal.butter(2,[520,1050],fs=SR,btype='bandpass',output='sos'),left).astype(np.float32)
                form2=signal.sosfilt(signal.butter(2,[520,1050],fs=SR,btype='bandpass',output='sos'),right).astype(np.float32)
                left=left*.62+form1*.75;right=right*.62+form2*.75
        else:
            left=oscillator(p_phase*(1-.0035*width),freq,kind,colour)
            right=oscillator(p_phase*(1+.0035*width)+.11*width,freq,kind,colour)
    envelope=np.minimum(1,t/max(attack,.001))
    if kind in ['pluck','fm','bell','bass','acid'] and pid!='syn:shimmer':
        decay=.16+duration*.32 if pid=='syn:slap-bass' else (.22+duration*.45 if kind=='pluck' else .3+duration*.7)
        sustain=.22 if kind in ['bass','fm'] and pid!='syn:slap-bass' else (.08 if pid=='syn:slap-bass' else .04)
        envelope*=np.exp(-t/decay)*(1-sustain)+sustain
    if kind=='pad':envelope*=.93+.07*np.sin(2*np.pi*t*.35)
    envelope*=np.minimum(1,np.maximum(0,(duration+release-t)/max(.01,release)))**1.7
    if pid=='syn:wobble-pad':envelope*=.58+.42*np.sin(2*np.pi*t*bpm/60*2)**2
    amplitude=(velocity/127)**1.35*.22
    return np.column_stack((left*envelope*amplitude,right*envelope*amplitude)).astype(np.float32)

def needs_kick_sidechain(role,plan):
    if plan['family'] in ['house','bass','dnb','retro'] and role in ['bass','chords','pad','arp']:return True
    return role=='bass' and plan['settings']['genre'] in SIDECHAIN_BASS_GENRES

def active_ratio(notes,total_duration):
    if not notes or total_duration<=0:return 0.
    spans=sorted((max(0.,float(n[0])),min(float(total_duration),float(n[0])+min(float(n[1])+.15,3.))) for n in notes)
    covered=0.;cur_s,cur_e=spans[0]
    for s,e in spans[1:]:
        if s<=cur_e:cur_e=max(cur_e,e)
        else:covered+=max(0.,cur_e-cur_s);cur_s,cur_e=s,e
    covered+=max(0.,cur_e-cur_s)
    return min(1.,covered/float(total_duration))

def process_stem(data,track,plan):
    role=track['id'];tone=track['tone'];brightness=tone.get('brightness',.5)
    cutoff=16000 if brightness>=.5 else 1800*2**(brightness*5.8)
    lowcut=27 if role=='bass' else (24 if role=='drums' else (140 if role in ['pad','arp','counter','fx'] else 95))
    if role=='chords' and plan['settings']['genre']=='piano':lowcut=45
    for start in range(0,len(data),SR*30):
        # Filters are applied continuously below, chunking is reserved for nonlinear processing.
        block=data[start:start+SR*30]
        if tone.get('drive',0)>.001:
            drive=1+tone['drive']*5;block[:]=np.tanh(block*drive)/drive**.55
    if role=='drums' and abs(tone.get('release',.5)-.5)>.001:
        # One-shot drum samples ignore MIDI note-off. Shape their decay on the bus
        # instead of exposing an envelope control that does nothing.
        hits=sorted({min(len(data),round(n[0]*SR)) for n in track['notes']})+[len(data)]
        amount=(tone.get('release',.5)-.5)*16
        for start,end in zip(hits,hits[1:]):
            if end>start:
                tail=np.exp(np.clip(np.arange(end-start,dtype=np.float32)/SR*amount,-4,.59))
                data[start:end]*=tail[:,None]
    data[:]=signal.sosfilt(signal.butter(2,lowcut,fs=SR,btype='highpass',output='sos'),data,axis=0)
    if cutoff<15000:data[:]=signal.sosfilt(signal.butter(2,cutoff,fs=SR,output='sos'),data,axis=0)
    if role=='drums':
        inst_name=INSTRUMENTS.get(track.get('instrument',''),{}).get('name','').lower()
        if 'power' in inst_name or track.get('instrument') in {'sf:128:16','ms:128:16','ms:128:17','ms:128:18','ms:128:19'}:
            w0=2*np.pi*3800/SR;alpha=np.sin(w0)/(2*1.2);A=10**(-5./40.)
            b0=1+alpha*A;b1=-2*np.cos(w0);b2=1-alpha*A;a0=1+alpha/A;a1=-2*np.cos(w0);a2=1-alpha/A
            b_p=np.array([b0/a0,b1/a0,b2/a0],dtype=np.float32);a_p=np.array([1.,a1/a0,a2/a0],dtype=np.float32)
            data[:]=signal.lfilter(b_p,a_p,data,axis=0)
            data[:]=signal.sosfilt(signal.butter(2,11000,fs=SR,btype='lowpass',output='sos'),data,axis=0)
    if role=='bass':
        # Keep deep bass centered; low frequencies should survive mono playback.
        mono=data.mean(axis=1);data[:,0]=mono;data[:,1]=mono
    if needs_kick_sidechain(role,plan):
        env=np.ones(len(data),dtype=np.float32)
        kicks=next(t['notes'] for t in plan['tracks'] if t['id']=='drums')
        electronic=plan['family'] in ['house','bass','dnb','retro']
        depth=(.42 if role=='bass' else .30) if electronic else .28
        length=int(.19*SR);attack_n=max(1,int(.0045*SR))
        drop=depth*np.exp(-np.arange(length,dtype=np.float32)/(.055*SR))
        drop[:attack_n]*=.5-.5*np.cos(np.pi*np.arange(attack_n,dtype=np.float32)/attack_n)
        curve=1.-drop
        for start,_,note,*_ in kicks:
            if note!=36:continue
            p=int(start*SR);n=min(length,len(env)-p)
            if n>0:env[p:p+n]=np.minimum(env[p:p+n],curve[:n])
        data[:]*=env[:,None]
    # Modest tempo-synced stereo delay; space at zero still preserves each patch's dry sound.
    space=(plan['settings']['space']*.16+tone.get('space',0)*.35)
    if role in ['lead','counter','arp'] and space>.001:
        dry=data.copy();delay=round(60/plan['bpm']*.75*SR)
        for tap in range(1,4):
            shift=delay*tap
            if shift>=len(data):break
            data[shift:]+=dry[:-shift,::-1]*(space*.52**(tap-1))
    if track['instrument'].startswith('syn:') and role not in ['bass','drums','fx'] and space>.001:
        dry=data.copy()
        for seconds,level in [(.043,.16),(.071,.13),(.113,.1),(.173,.07),(.241,.05),(.347,.04)]:
            shift=int(seconds*SR)
            if shift<len(data):data[shift:]+=dry[:-shift,::-1]*level*space
    if role in ['bass','drums'] and tone.get('space',0)>.001:
        wet=signal.sosfilt(signal.butter(2,220,fs=SR,btype='highpass',output='sos'),data,axis=0).astype(np.float32)
        for seconds,level in [(.053,.2),(.097,.13),(.163,.08),(.239,.05)]:
            shift=int(seconds*SR)
            if shift<len(data):data[shift:]+=wet[:-shift,::-1]*level*tone['space']
    # Instrument-specific calibration prevents a loud GM preset from dominating a synth layer.
    probe=np.asarray(data[::4],dtype=np.float64)
    rms=float(np.sqrt(np.mean(probe**2)))
    if len(probe)>16 and rms>1e-7:
        ear_band=signal.sosfilt(signal.butter(2,[1600,5200],fs=SR/4,btype='bandpass',output='sos'),probe,axis=0)
        ear_rms=float(np.sqrt(np.mean(ear_band**2)+.85*np.mean(probe**2)))
    else:ear_rms=rms
    target={'drums':.096,'bass':.118,'chords':.068,'lead':.086,'counter':.054,'pad':.046,'arp':.048,'fx':.044}[role]
    # Scale by active proportion: sparse responses must not get excessive gain from silence.
    active=active_ratio(track['notes'],plan['duration'])
    target*=min(1,math.sqrt(max(.03,active/.72)))
    calibration=min(4,max(.12,target/max(ear_rms,1e-8))) if ear_rms>1e-7 else 1
    data[:]*=calibration
    from dynamics import section_db
    # Apply after calibration so role balancing cannot remove section contrast.
    if not plan.get('_skip_arrangement_gain',False):
        # The tail after the last complete bar still belongs to the outro.
        # Previously it reverted to unity, creating a sudden +6 dB at the end.
        tail=1 if plan.get('_keep_legacy_tail_gap') else 10**(section_db(plan,plan['sections'][-1])/20)
        envelope=np.full(len(data),tail,dtype=np.float32)
        for section in plan['sections']:
            a=round(section['start']*SR);b=min(len(data),round((section['start']+section['duration'])*SR))
            if b>a:envelope[a:b]=10**(section_db(plan,section)/20)
        # Short crossfades remove discontinuities at arrangement boundaries.
        radius=round(.055*SR)
        for section in plan['sections'][1:]:
            p=round(section['start']*SR);a=max(0,p-radius);b=min(len(data),p+radius)
            if b>a:envelope[a:b]=np.linspace(envelope[a],envelope[b-1],b-a)
        data[:]*=envelope[:,None]
    fade=min(int(.03*SR),len(data));data[:fade]*=np.linspace(0,1,fade)[:,None]
    fade=min(int(1.35*SR),len(data));data[-fade:]*=np.linspace(1,0,fade)[:,None]**1.4
    return dict(rms_dbfs=round(20*math.log10(max(rms*calibration,1e-9)),2),calibration=round(calibration,4),peak=round(float(np.max(np.abs(data))),4))

def stem_fingerprint(track,plan):
    payload={k:track[k] for k in ['id','instrument','tone','notes']}
    payload['engine_version']=ENGINE_VERSION
    if plan.get('_skip_arrangement_gain',False):payload['skip_arrangement_gain']=True
    if plan.get('_keep_legacy_tail_gap',False):payload['legacy_tail_gap']=True
    if track['instrument'].startswith('ms:') and 'Expr.' in INSTRUMENTS[track['instrument']]['name']:payload['cc2_expression_version']=1
    payload.update(duration=plan['duration'],bpm=plan['bpm'],space=plan['settings']['space'],family=plan['family'],genre=plan['settings']['genre'])
    if needs_kick_sidechain(track['id'],plan):payload['kicks']=[n[0] for n in plan['tracks'][0]['notes'] if n[2]==36]
    return hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()

def render_stem(track,plan,directory,previous=None):
    fingerprint=stem_fingerprint(track,plan)
    path=directory/(track['id']+'.npy')
    stamp_path=directory/(track['id']+'.cache.json')
    stamp=json.loads(stamp_path.read_text('utf-8')) if stamp_path.exists() else {}
    if stamp.get('hash')==fingerprint and path.exists():
        return track['id'],fingerprint,stamp['stats'],True
    count=round(plan['duration']*SR)
    tmp_path=directory/(track['id']+'.next.npy')
    output=np.lib.format.open_memmap(tmp_path,mode='w+',dtype='float32',shape=(count,2));output[:]=0
    inst=INSTRUMENTS[track['instrument']]
    if track['notes']:
        if inst['engine']=='sample':
            space=(plan['settings']['space']*.18+track['tone'].get('space',0)*.32) if track['id'] not in ['bass','drums'] else 0
            synth=Fluid(inst,track['tone'],track['id'],space)
            try:synth.render(output,track['notes'])
            finally:synth.close()
        else:
            cache={};cache_bytes=0
            for i,(start,duration,note,velocity,art) in enumerate(track['notes']):
                key=(note,round(duration,2),velocity//6,art)
                wave=cache.get(key)
                if wave is None:
                    wave=synth_note(inst,note,round(duration,2),velocity,track['tone'],plan['bpm'],art,plan['settings']['seed']+i)
                    if cache_bytes<24*1024**2:cache[key]=wave;cache_bytes+=wave.nbytes
                p=int(start*SR);n=min(len(wave),count-p)
                if n>0:output[p:p+n]+=wave[:n]
        stats=process_stem(output,track,plan)
    else:stats=dict(rms_dbfs=-180,peak=0,calibration=1)
    output.flush();del output
    tmp_path.replace(path)
    stamp_path.write_text(json.dumps(dict(hash=fingerprint,stats=stats)),encoding='utf-8')
    return track['id'],fingerprint,stats,False

def master_mix(plan,directory,progress):
    count=round(plan['duration']*SR);raw_path=directory/'mix.f32'
    mix=np.memmap(raw_path,dtype='float32',mode='w+',shape=(count,2));mix[:]=0
    solo=any(t['solo'] for t in plan['tracks'])
    for track in plan['tracks']:
        if track['mute'] or (solo and not track['solo']):continue
        stem=np.load(directory/(track['id']+'.npy'),mmap_mode='r')
        pan=track['pan'];left=math.sqrt(1-max(0,pan));right=math.sqrt(1+min(0,pan))
        for start in range(0,count,SR*20):
            block=stem[start:start+SR*20];points=track.get('curve',[[0,1],[1,1]])
            envelope=np.interp(np.arange(start,start+len(block))/max(1,count-1),[p[0] for p in points],[p[1] for p in points]).astype(np.float32)
            mix[start:start+SR*20]+=block*np.array([left,right],dtype=np.float32)*track['gain']*envelope[:,None]
        del stem
    # Remove DC and reserve headroom before the measured final master.
    mix[:]-=mix.mean(axis=0);mix.flush()
    if not np.isfinite(mix).all():raise RuntimeError('Render obsahuje neplatné vzorky.')
    peak=float(np.max(np.abs(mix)))
    if peak<1e-8:
        target=-16;stats={'input_i':-99,'input_tp':-99,'input_lra':0,'silent':True}
        filt='anull'
    else:
        progress(.83,'Měřím hlasitost a výstupní špičky…')
        target=-16 if plan['family'] in ['classical','ambient','acoustic','jazz'] else -14
        base=['-v','info','-f','f32le','-ar',SR,'-ac',2,'-i',raw_path]
        measured=ffmpeg([*base,'-af',f'loudnorm=I={target}:TP=-1.5:LRA=12:print_format=json','-f','null','-'])
        if measured.returncode:raise RuntimeError(measured.stderr.decode(errors='replace')[-2000:])
        text=measured.stderr.decode(errors='replace');stats=json.loads(text[text.rfind('{'):text.rfind('}')+1])
        if stats['input_i']=='-inf':filt='anull'
        else:
            gain_db=min(12,target-float(stats['input_i']))
            stats['linear_gain_db']=round(gain_db,5)
            # Constant gain plus a peak limiter preserves quiet sections. The
            # adaptive loudnorm mode previously raised these sections over time.
            filt=f'volume={gain_db}dB,aresample=192000,alimiter=limit=0.841395:attack=5:release=80:level=false:latency=true,aresample=48000'
            stats['normalization_type']='constant_gain_peak_limiter'
    progress(.9,'Zapisuji WAV 24 bit a Opus 160 kb/s…')
    wav_tmp=directory/'master-next.wav';opus_tmp=directory/'master-next.opus'
    result=ffmpeg(['-v','info','-y','-f','f32le','-ar',SR,'-ac',2,'-i',raw_path,'-af',filt,'-ar',SR,'-c:a','pcm_s24le',wav_tmp])
    if result.returncode:raise RuntimeError(result.stderr.decode(errors='replace')[-1500:])
    measured_output=result.stderr.decode(errors='replace')
    if measured_output.rfind('{')>=0:
        actual=json.loads(measured_output[measured_output.rfind('{'):measured_output.rfind('}')+1])
        stats.update(output_i=actual['output_i'],output_tp=actual['output_tp'],output_lra=actual['output_lra'],normalization_type=actual['normalization_type'])
    result=ffmpeg(['-v','error','-y','-i',wav_tmp,'-c:a','libopus','-b:a','160k','-vbr','off','-application','audio',opus_tmp])
    if result.returncode:raise RuntimeError(result.stderr.decode(errors='replace')[-1500:])
    # Atomic replacement means a failed export never replaces the last playable master.
    wav_tmp.replace(directory/'master.wav');opus_tmp.replace(directory/'master.opus')
    with sf.SoundFile(directory/'master.wav') as f:
        waveform=[];rms_waveform=[];sum_sq=0.;max_peak=0.;frames=0
        for block in f.blocks(blocksize=max(1,round(count/1000)),dtype='float32'):
            waveform.append(round(float(np.max(np.abs(block))),5));rms_waveform.append(round(float(np.sqrt(np.mean(block.astype(np.float64)**2))),5));sum_sq+=float(np.sum(block.astype(np.float64)**2));frames+=len(block);max_peak=max(max_peak,float(np.max(np.abs(block))))
    stats.update(target_lufs=target,peak_dbfs=round(20*math.log10(max(max_peak,1e-12)),3),
        rms_dbfs=round(10*math.log10(max(sum_sq/(frames*2),1e-15)),2),waveform=waveform,rms_waveform=rms_waveform,sample_rate=SR,bits=24,opus_bitrate=160000)
    del mix
    raw_path.unlink(missing_ok=True)
    return stats

def render(plan,directory,progress=lambda *a:None,previous=None):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True);start=time.monotonic();hashes={};stats={};reused=[]
    progress(.03,'Připravuji nástroje a partituru…')
    workers=min(4,max(1,(os.cpu_count() or 4)//2))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures=[pool.submit(render_stem,t,plan,directory,previous) for t in plan['tracks']]
        for i,future in enumerate(as_completed(futures)):
            role,digest,details,cached=future.result();hashes[role]=digest;stats[role]=details
            if cached:reused.append(role)
            progress(.08+(i+1)/len(futures)*.7,f"Hotová stopa: {next(t['name'] for t in plan['tracks'] if t['id']==role)}")
    master=master_mix(plan,directory,progress)
    result=dict(hashes=hashes,stem_stats=stats,master=master,render_seconds=round(time.monotonic()-start,2),reused_stems=reused,arrangement_gain_baked=True,tail_gain_fixed=True)
    (directory/'render.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    progress(1,'Skladba je připravená.')
    return result
