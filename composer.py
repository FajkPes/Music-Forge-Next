"""Hierarchical, deterministic composition. Musical time is in beats; performance in seconds."""
import math, random
from catalogue import GENRE_MAP, GENRE_POOLS, MOOD_MAP, load_instruments, generate_title
from balance import gain_limit

VERSION=1
SCALES={'major':[0,2,4,5,7,9,11],'minor':[0,2,3,5,7,8,10],'dorian':[0,2,3,5,7,9,10],'phrygian':[0,1,3,5,7,8,10]}
KEYS=['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
ROLE_INFO=[('drums','Bicí','#eab676',-.0,.75),('bass','Basa','#caa8ff',0,.8),('chords','Akordy','#64d5c1',-.16,.52),
           ('lead','Hlavní melodie','#a5a2ff',.05,.68),('counter','Odpovědi','#ed9fc0',.22,.32),
           ('pad','Atmosféra','#79b9e3',-.12,.30),('arp','Arpeggio','#b4ce7c',.28,.28),('fx','Přechody','#d6b395',0,.28)]
INSTRUMENTS={x['id']:x for x in load_instruments()}

def bounded(value,default,low,high):
    try: n=float(value)
    except (TypeError,ValueError):n=default
    return max(low,min(high,n)) if math.isfinite(n) else default

def normalize_settings(raw):
    g=GENRE_MAP.get(raw.get('genre'),GENRE_MAP['melodic-house'])
    m=MOOD_MAP.get(raw.get('mood'),MOOD_MAP['uplifting'])
    key=raw.get('key','auto')
    if key not in ['auto']+KEYS:key='auto'
    seed_val=int(bounded(raw.get('seed'),431207,0,2147483647))
    energy_val=bounded(raw.get('energy'),m['energy'],0,1)
    raw_title=str(raw.get('title') or '').strip()[:100]
    if not raw_title or raw_title=='Nová skladba':
        raw_title=generate_title(g['id'],m['id'],seed_val,energy_val)
    out=dict(genre=g['id'],mood=m['id'],duration=bounded(raw.get('duration'),210,20,600),
      bpm=bounded(raw.get('bpm'),g['bpm'],50,200),key=key,
      seed=seed_val,
      melody_seed=int(bounded(raw.get('melody_seed'),0,0,2147483647)),
      sound_seed=int(bounded(raw.get('sound_seed'),0,0,2147483647)),
      energy=energy_val,
      complexity=bounded(raw.get('complexity'),.55,0,1),variation=bounded(raw.get('variation'),.65,0,1),
      humanize=bounded(raw.get('humanize'),.55,0,1),space=bounded(raw.get('space'),.35,0,1),
      title=raw_title,instruments={},mix={},tone={},section_levels={})
    levels=raw.get('section_levels',{})
    if isinstance(levels,dict):out['section_levels']={str(k):bounded(v,1,0,2) for k,v in levels.items() if str(k).isdigit() and int(k)<32}
    overrides=raw.get('instruments',{})
    if isinstance(overrides,dict):
        for role,*_ in ROLE_INFO:
            inst=overrides.get(role)
            if inst in INSTRUMENTS and ((INSTRUMENTS[inst].get('bank')==128)==(role=='drums')):
                out['instruments'][role]=inst
    mixes=raw.get('mix',{})
    if isinstance(mixes,dict):
        for role,_,_,pan,gain in ROLE_INFO:
            v=mixes.get(role)
            if isinstance(v,dict):out['mix'][role]=dict(gain=bounded(v.get('gain'),gain,0,1.5),pan=bounded(v.get('pan'),pan,-1,1),mute=bool(v.get('mute',False)),solo=bool(v.get('solo',False)))
            if isinstance(v,dict) and isinstance(v.get('curve'),list):
                points=[(bounded(p[0],0,0,1),bounded(p[1],1,0,1.5)) for p in v['curve'][:64] if isinstance(p,(list,tuple)) and len(p)==2]
                points=sorted(dict(points).items())
                if points:
                    if points[0][0]>0:points.insert(0,(0,points[0][1]))
                    if points[-1][0]<1:points.append((1,points[-1][1]))
                    if len(points)>64:points=points[:63]+[points[-1]]
                    out['mix'][role]['curve']=[list(p) for p in points]
    tones=raw.get('tone',{})
    if isinstance(tones,dict):
        for role,*_ in ROLE_INFO:
            v=tones.get(role,{})
            if isinstance(v,dict):out['tone'][role]={k:bounded(v.get(k),.5 if k in ['brightness','attack','release'] else 0,0,1) for k in ['brightness','attack','release','drive','space']}
    return out

def resolve_pool(items,role):
    out=[]
    for item in items:
        if item in INSTRUMENTS:out.append(item)
        elif item=='piano:0:0':
            for alt in ('ms:0:0','sf:0:0'):
                if alt in INSTRUMENTS and alt not in out:out.append(alt);break
        elif item.startswith('ms:'):
            alt=item.replace('ms:','sf:',1)
            if alt in INSTRUMENTS and alt not in out:out.append(alt)
    if not out:out=['sf:128:0' if role=='drums' else 'sf:0:0']
    return out

def choose_palette(g,s):
    rng=random.Random(s['sound_seed'] or s['seed']+809)
    base=g['palette']
    fallback={
      'drums':[f"sf:128:{g['kit']}"],
      'lead':[f'sf:0:{base[0]}',f'sf:0:{base[1]}'],
      'chords':[f'sf:0:{base[1]}',f'sf:0:{base[0]}'],
      'bass':[f'sf:0:{base[2]}'],
      'pad':[f'sf:0:{base[3]}'],
      'counter':[f'sf:0:{base[4]}'],
      'arp':[f'sf:0:{base[4]}'],
      'fx':['syn:noise-rise']}
    raw_pools=GENRE_POOLS.get(g['id'],fallback)
    # Assign primary musical voices first so accompaniment layers avoid duplicating the lead timbre.
    priority_order=['drums','bass','lead','chords','counter','pad','arp','fx']
    selected={};used=set()
    allow_shared=(g['id']=='piano')
    for role in priority_order:
        options=resolve_pool(raw_pools.get(role,fallback[role]),role)
        unique=options if allow_shared else [i for i in options if i not in used]
        choice=rng.choice(unique or options)
        selected[role]=choice
        if not allow_shared:used.add(choice)
    # Manual overrides are applied after the automatic palette. They must not
    # skip an RNG draw or change the automatic choices of unrelated roles.
    selected.update(s['instruments'])
    return selected

def arrangement(bars,family,rng):
    dance=family in ['house','bass','dnb','retro']
    if bars<24:
        spec=[('Úvod','intro',1,.35),('Téma','verse',2,.7),('Vrchol','chorus',3,1),('Závěr','outro',1,.35)]
    elif dance:
        spec=[('Úvod','intro',1,.35),('Téma A','verse',2,.68),('Gradace','build',1,.82),('Drop I','chorus',2,1),
              ('Nádech','bridge',1,.42),('Téma B','verseB',2,.7),('Gradace II','build',1,.86),('Drop II','final',2,1),('Závěr','outro',1,.35)]
    elif family in ['classical','ambient','acoustic','jazz']:
        spec=[('Předehra','intro',1,.4),('Téma A','verse',3,.72),('Rozvinutí','chorus',2,.9),('Téma B','bridge',2,.5),('Návrat','final',3,1),('Coda','outro',1,.4)]
    else:
        spec=[('Úvod','intro',1,.35),('Sloka I','verse',2,.6),('Předrefrén','build',1,.8),('Refrén I','chorus',2,1),
              ('Sloka II','verseB',2,.68),('Bridge','bridge',1,.42),('Refrén II','final',2,1),('Závěr','outro',1,.38)]
    unit=4 if bars>=len(spec)*4 else 1
    total=max(len(spec),bars//unit);weights=[x[2] for x in spec]
    counts=[1]*len(spec)
    for _ in range(total-len(spec)):
        k=max(range(len(spec)),key=lambda i:weights[i]/sum(weights)*total-counts[i]+rng.random()*.06)
        counts[k]+=1
    counts=[x*unit for x in counts];counts[-1]+=bars-sum(counts)
    result=[];start=0
    for (name,kind,_,energy),n in zip(spec,counts):
        result.append(dict(name=name,kind=kind,start_bar=start,bars=n,energy=energy));start+=n
    return result

def chord_symbol(root_pc,pcs):
    third=(pcs[1]-root_pc)%12
    fifth=(pcs[2]-root_pc)%12
    seventh=(pcs[3]-root_pc)%12 if len(pcs)>3 else None
    name=KEYS[root_pc]
    if third==3 and fifth==6:
        return name+('m7b5' if seventh==10 else ('dim7' if seventh==9 else 'dim'))
    if third==3:
        return name+('m(maj7)' if seventh==11 else ('m7' if seventh==10 else 'm'))
    if seventh==11:return name+'maj7'
    if seventh==10:return name+'7'
    return name

def voice_chord(pcs,previous,rng):
    unique_pcs=list(dict.fromkeys(pcs))
    choices=[]
    for inversion in range(len(unique_pcs)):
        base=sorted([48+p+12*(j<inversion) for j,p in enumerate(unique_pcs)])
        variants=[base]
        # Drop-2 / open spread keeps 4-note 7th chords clear of low-mid mud.
        if len(base)>=4:
            spread=sorted([base[0],base[2],base[3],base[1]+12])
            if len(set(spread))==len(spread):variants.append(spread)
        elif len(base)==3:
            open_triad=sorted([base[0],base[2],base[1]+12])
            if len(set(open_triad))==len(open_triad):variants.append(open_triad)
        for notes in variants:
            for octave in [0,12]:
                v=[n+octave for n in notes]
                if min(v)>=50 and max(v)<=79 and len(set(v))==len(v):
                    center=sum(v)/len(v)
                    score=sum(abs(a-b) for a,b in zip(v,previous)) if (previous and len(previous)==len(v)) else abs(center-62)*1.4
                    if previous and len(previous)!=len(v):score=abs(center-sum(previous)/len(previous))*2.5
                    # Penalize muddy narrow intervals in the lower register.
                    if v[1]-v[0]<3 and v[0]<59:score+=9
                    if len(v)>2 and v[2]-v[1]<3 and v[1]<57:score+=5
                    score+=max(0,8-(v[-1]-v[0]))*1.8
                    choices.append((score+rng.random()*.08,v))
    if not choices:
        fallback=sorted({52+p+12*(j//3) for j,p in enumerate(unique_pcs)})
        return fallback
    return min(choices,key=lambda x:x[0])[1]

def genre_progressions(g,mode):
    gid=g['id'];fam=g['family']
    if mode=='phrygian':
        return [[0,1,0,6],[0,0,1,6],[0,5,1,0],[0,6,1,0]]
    if gid in ['phonk','trap','tech-house','bass-house','dubstep','neurofunk','midtempo','psytrance','techno']:
        if mode=='major':return [[0,5,3,4],[0,3,5,4],[0,6,3,0]]
        return [[0,5,0,6],[0,0,5,6],[0,3,0,6],[0,5,2,6],[0,6,5,6]]
    if fam=='jazz' or gid=='bossa':
        if mode=='major':return [[1,4,0,5],[0,5,1,4],[2,5,1,4],[0,3,1,4]]
        return [[1,4,0,0],[0,5,1,4],[3,6,2,5],[1,4,0,5]]
    if fam=='classical':
        if mode=='major':return [[0,3,1,4],[0,4,5,3],[0,5,3,4],[0,2,3,4]]
        return [[0,3,4,0],[0,5,3,4],[0,2,5,4],[0,5,2,6]]
    if fam=='rock':
        if mode=='major':return [[0,4,5,3],[0,5,3,4],[3,0,4,5],[5,3,0,4]]
        return [[0,5,6,0],[0,5,2,6],[0,6,5,6],[0,3,5,6]]
    if mode=='major':
        return [[5,3,0,4],[0,4,5,3],[3,4,2,5],[0,5,3,4],[3,0,5,4],[0,2,5,3]]
    return [[0,5,2,6],[0,3,5,6],[5,6,0,0],[0,6,5,6],[0,5,3,6],[3,5,0,6]]

def compose(raw):
    s=normalize_settings(raw);g=GENRE_MAP[s['genre']];m=MOOD_MAP[s['mood']]
    rng=random.Random(s['seed']);mrng=random.Random(s['melody_seed'] or s['seed']+991)
    srng=random.Random(s['seed']+155)
    mode=g['mode']
    if mode in ['major','minor']:
        if m['valence']<.27:mode='minor'
        elif m['valence']>.83:mode='major'
    scale=SCALES[mode];tonic=rng.choice([0,2,3,5,7,9,10]) if s['key']=='auto' else KEYS.index(s['key'])
    beat=60/s['bpm'];bar_seconds=4*beat
    bars=max(4,int((s['duration']-.6)/bar_seconds));sections=arrangement(bars,g['family'],srng)
    palette=choose_palette(g,s)
    extended=bool(g.get('extended',False))
    progs=genre_progressions(g,mode)
    prog=rng.choice(progs);progB=rng.choice([p for p in progs if p!=prog] or progs)
    tracks={role:dict(id=role,name=name,colour=colour,instrument=palette[role],gain=s['mix'].get(role,{}).get('gain',gain),
          pan=s['mix'].get(role,{}).get('pan',pan),mute=s['mix'].get(role,{}).get('mute',False),solo=s['mix'].get(role,{}).get('solo',False),tone=s['tone'].get(role,{}),notes=[]) for role,name,colour,pan,gain in ROLE_INFO}
    # Every role has its own performance RNG: editing the melody cannot reshuffle the drums.
    prng={role:random.Random(s['seed']+i*1031) for i,(role,*_) in enumerate(ROLE_INFO)}
    def emit(role,b,d,n,v,art='normal'):
        if b<0 or b*beat>=s['duration']-1.2:return
        r=prng[role];amount=s['humanize'];jitter=(r.random()-.5)*.022*amount
        # Keep kick drum downbeats tight so sidechain and low-end punch stay phase-locked.
        if role=='drums' and n==36 and abs(b-round(b))<1e-4:jitter*=.25
        swing=g['swing']*(1 if (int(round(b*4))%4 in [2,3]) else 0)
        start=max(0,b*beat+jitter+swing*beat)
        duration=min(max(.035,d*beat),s['duration']-.6-start)
        if duration<=0:return
        vel=max(22,min(118,int(round(v*(1+(r.random()-.5)*.14*amount)))))
        tracks[role]['notes'].append([round(start,5),round(duration,5),max(0,min(127,int(n))),vel,art])

    # Precompute bar-by-bar harmony so basslines and cadences know the upcoming chord root.
    harmony=[];previous=None
    use_harmonic_dominant=(mode=='minor' and (g['family'] in ['classical','jazz'] or g['id'] in ['bossa','cinematic']))
    sub_heavy=g['id'] in ['trap','phonk','dubstep','chillstep','liquid-dnb','jungle','reggaeton','future-bass','afro-house']
    for sec in sections:
        kind=sec['kind']
        for local in range(sec['bars']):
            bar=sec['start_bar']+local
            progression=progB if kind in ['bridge','verseB'] else prog
            harmonic_rate=2 if g['family']=='ambient' else 1
            degree=progression[(local//harmonic_rate)%len(progression)]
            if kind=='outro' and local>=max(1,sec['bars']-2):degree=0
            pcs=[(tonic+scale[(degree+k)%7])%12 for k in ([0,2,4,6] if extended else [0,2,4])]
            if use_harmonic_dominant and degree==4 and len(pcs)>=3:
                pcs[1]=(tonic+11)%12
            chord=voice_chord(pcs,previous,rng);previous=chord
            root=36+(tonic+scale[degree])%12
            if sub_heavy and root>44:root-=12
            elif not sub_heavy and root>46:root-=12
            if root<33:root+=12
            harmony.append(dict(bar=bar,degree=degree,root=root,pcs=pcs,chord=chord,name=chord_symbol(pcs[0],pcs)))

    # Eight-bar themes share a rhythmic cell, contour, and cadence; B changes the response.
    rhythm_sets={
      'hook':[[0,.75,1.5,2.5,3],[0,.5,1.5,2.25,3],[.5,1,2,2.75,3.5],[0,1,1.75,2.5]],
      'sing':[[0,1,1.5,2.5],[.5,1.5,2,3],[0,.75,1.5,3],[0,1.5,2.5]],
      'flow':[[0,.5,1.5,2,2.5,3.5],[0,.75,1.5,2.25,3],[.5,1,2,2.5,3],[0,1,1.5,2.5,3.5]],
      'riff':[[0,.5,1,1.75,2.5,3],[0,.75,1.5,2,2.75],[0,.5,1.5,2,3,3.5],[0,1,1.5,2.25,3]],
      'sparse':[[0,2],[.5,2.5],[0,1.5,3],[1,2.5]],
      'classical':[[0,.5,1,2,3],[0,1,1.5,2,3],[0,.5,1.5,2.5,3],[0,1,2,3]]}
    patterns=rhythm_sets.get(g['lead'],rhythm_sets['hook'])
    restrained=s['mood'] in ['sad','calm','focused','mysterious','dreamy','relaxed','melancholic']
    low_register=s['mood'] in ['sad','dark','melancholic','nostalgic','mysterious']
    if restrained and g['lead'] not in ['classical','riff']:patterns=[[0,1.5,2.5],[.5,2],[0,1,2.5],[0,2]]
    if s['mood']=='playful' and g['lead']!='sparse':patterns=rhythm_sets['flow']
    chosen=mrng.sample(patterns,len(patterns))
    base_degree=mrng.choice([5,7,9] if low_register else [7,9,11])
    contour=mrng.choice([[0,1,2,1,0,-1,1,0],[0,2,1,3,2,1,-1,0],[0,-1,1,2,1,2,0,0],[0,1,3,2,1,0,-1,0]])
    if s['mood'] in ['sad','melancholic']:contour=[0,-1,0,-2,1,0,-1,-2]
    elif s['mood'] in ['nostalgic','romantic','bittersweet']:contour=[0,1,2,0,1,2,1,0]
    elif s['mood'] in ['dark','tense','aggressive']:contour=[0,0,-1,1,2,0,-1,0]
    motif=[]
    for mb in range(8):
        rhythm=chosen[mb%4][:]
        if mb%4==3:rhythm=rhythm[:max(2,len(rhythm)-1)]
        deg=base_degree+contour[mb]
        row=[];prev_step=0
        for j,pos in enumerate(rhythm):
            if j:
                # Gap-fill principle: after a leap, prefer stepping back smoothly.
                if prev_step>=2:step=mrng.choice([-2,-1,-1,0])
                elif prev_step<=-2:step=mrng.choice([0,1,1,2])
                else:step=mrng.choice([-2,-1,-1,0,1,1,2])
                deg+=step;prev_step=step
            deg=max(5,min(16,deg))
            # Phrase cadences: bar 3 opens on scale degree 2/5 (question), bar 7 resolves toward tonic/third (answer).
            if mb==3 and j==len(rhythm)-1:
                targets=[d for d in range(5,16) if d%7 in [1,4,2]]
                deg=min(targets,key=lambda x:abs(x-deg))
            elif mb==7 and j==len(rhythm)-1:
                targets=[d for d in range(5,16) if d%7 in [0,2]]
                deg=min(targets,key=lambda x:abs(x-deg))
            row.append((pos,deg))
        motif.append(row)

    counter_last=72
    for sec in sections:
      kind=sec['kind'];peak=kind in ['chorus','final'];section_energy=sec['energy']*(.52+.48*s['energy'])
      for local in range(sec['bars']):
        bar=sec['start_bar']+local;bt=bar*4
        phrase=local%8;phrase_end=local%4==3
        h=harmony[bar];degree=h['degree'];root=h['root'];pcs=h['pcs'];chord=h['chord']
        next_root=harmony[min(bars-1,bar+1)]['root']
        third_iv=(pcs[1]-pcs[0])%12
        fifth_iv=(pcs[2]-pcs[0])%12
        harmonic_rate=2 if g['family']=='ambient' else 1

        # 1. CHORDS & ACCOMPANIMENT GRAMMAR
        cp=g['chords'];chord_events=[]
        if cp=='piano_solo':
            # Expressive left-hand piano accompaniment evolving across sections.
            low_root=max(41,min(55,root+12))
            fifth_note=low_root+fifth_iv
            octave_note=low_root+12
            tenth_note=octave_note+third_iv
            if kind in ['intro','outro']:
                pattern=[(0,1.45,low_root,0),(1,1.3,fifth_note,-6),(2,1.35,tenth_note,-3)]
                if kind=='outro' and bar==bars-1:
                    dur=max(2.5,(s['duration']-.7)/beat-bt)
                    for j,n in enumerate([low_root,fifth_note,tenth_note]):
                        emit('chords',bt+j*.06,dur,n,48+section_energy*14)
                    pattern=[]
            elif peak:
                notes_lh=[low_root,fifth_note,octave_note,tenth_note,octave_note,fifth_note,octave_note,tenth_note]
                vels=[4,-7,-4,-1,-5,-8,-4,-6]
                pattern=[(k*.5,.62,notes_lh[k],vels[k]) for k in range(8)]
            else:
                notes_lh=[low_root,fifth_note,tenth_note,fifth_note]
                vels=[3,-7,-2,-8]
                pattern=[(k*1.0,.96,notes_lh[k],vels[k]) for k in range(4)]
            for pos,dur,n,vd in pattern:
                emit('chords',bt+pos,dur,n,48+section_energy*20+vd)
        elif cp=='alberti':
            if kind in ['intro','outro'] and local<sec['bars']:
                chord_events=[(0,3.6)]
            else:
                accents=[3,-6,-2,-6]*2
                for k in range(8):
                    if phrase_end and k>=6:
                        if k==6:
                            for n in chord[:3]:emit('chords',bt+3.0,.9,n,52+section_energy*18)
                        continue
                    n=chord[[0,2,1,2][k%4]%len(chord)]
                    emit('chords',bt+k*.5,.48,n,51+section_energy*19+accents[k])
        else:
            if cp=='long':chord_events=[(0,3.75*harmonic_rate)] if (local%harmonic_rate)==0 else []
            elif cp=='offbeat':chord_events=[(.5,.34),(1.5,.34),(2.5,.34),(3.5,.34)]
            elif cp=='house_piano':
                chord_events=[(0,.65),(.75,.45),(1.5,.75),(2.5,.65),(3.25,.5)] if peak else [(0,1.4),(1.5,.85),(2.5,1.2)]
            elif cp=='stab':
                chord_events=[(0,.34),(1.75,.3),(2.5,.38)] if bar%2==0 else [(0,.34),(1.5,.32),(2.75,.32),(3.5,.26)]
            elif cp=='future':
                chord_events=[(0,1.35),(1.5,1.35),(3.0,.88)] if peak else [(0,1.85),(2,1.85)]
            elif cp=='pulse':
                chord_events=[(0,.82),(1.5,.42),(2.5,.85)] if peak else [(0,1.6),(2,1.6)]
            elif cp=='comp':
                chord_events=[(0,.55),(1.5,.48),(2.75,.52)] if bar%2==0 else [(.5,.52),(2,.62),(3.5,.34)]
            elif cp=='bossa':
                chord_events=[(0,.85),(1.5,.72),(2.5,.8),(3.5,.38)] if bar%2==0 else [(.5,.78),(1.5,.68),(3.0,.82)]
            elif cp=='funk':
                chord_events=[(.5,.24),(1.25,.2),(1.75,.28),(2.5,.24),(3.25,.2),(3.5,.24)] if peak else [(.5,.26),(1.75,.28),(2.5,.26)]
            elif cp=='reggaeton':
                chord_events=[(.75,.35),(1.5,.42),(2.75,.35),(3.5,.42)] if peak else [(0,1.7),(2,1.7)]
            elif cp=='strum':
                chord_events=[(0,.72),(1,.38),(1.5,.44),(2,.72),(3,.38),(3.5,.44)] if peak else [(0,1.65),(2,1.65)]
            elif cp=='rock':
                chord_events=[(0,.9),(1,.42),(1.5,.95),(2.5,.65),(3,.42),(3.5,.42)] if peak else [(k*.5,.36) for k in range(8)]
            elif cp=='punk':
                chord_events=[(k*.5,.4) for k in range(8)]
            elif cp=='postrock':
                if peak:chord_events=[(k*.5,.48) for k in range(8)]
                else:
                    for k in range(4):emit('chords',bt+k,1.15,chord[k%len(chord)],46+section_energy*20)
                    chord_events=[]
            if kind in ['intro','bridge','outro'] and cp not in ['postrock','bossa']:
                chord_events=[(0,3.6*harmonic_rate)] if (local%harmonic_rate)==0 else []
            play_chord=[root+12,root+12+fifth_iv,root+24] if g['family']=='rock' and cp in ['rock','punk'] else chord
            strum_spread=.020 if cp in ['strum','bossa','rock'] else (.008 if cp=='house_piano' else .003)
            for idx,(pos,dur) in enumerate(chord_events):
                if kind=='outro' and bar==bars-1 and pos==0:dur=max(dur,(s['duration']-.7)/beat-bt)
                accent=5 if pos in [0,1.5,2.5] else -3
                for j,n in enumerate(play_chord):
                    emit('chords',bt+pos+j*strum_spread/beat,dur,n,50+section_energy*24+accent)

        # 2. BASSLINE GRAMMAR (harmonically locked to chord tones & next-bar approach)
        bass_mode=g['bass'];bass_events=[]
        approach=next_root-1 if abs((next_root-1)-root)<=5 and next_root!=root else (root+fifth_iv)
        if bass_mode=='root':
            bass_events=[(0,3.55,root)] if g['id']!='piano' else [(0,1.9,root),(2,1.8,root)]
        elif bass_mode=='offbeat':
            bass_events=[(.5,.36,root),(1.5,.36,root),(2.5,.36,root),(3.5,.36,root+(12 if local%4==3 else 0))]
        elif bass_mode in ['octave','eighth']:
            bass_events=[(k*.5,.39,root+(12 if bass_mode=='octave' and k%2 else 0)) for k in range(8)]
            if phrase_end:bass_events[-1]=(3.5,.38,approach if bass_mode=='eighth' else root+fifth_iv)
        elif bass_mode=='walk':
            step2=root+third_iv if bar%2==0 else root+fifth_iv
            step3=root+fifth_iv if bar%2==0 else root+third_iv
            if next_root>root+1:step4=next_root-1 if (next_root-1)%12 not in pcs else next_root-2
            elif next_root<root-1:step4=next_root+1 if (next_root+1)%12 not in pcs else next_root+2
            else:step4=root+fifth_iv
            step4=max(33,min(52,step4))
            bass_events=[(0,.9,root),(1,.9,step2),(2,.9,step3),(3,.9,step4)]
        elif bass_mode=='psy':
            bass_events=[(k*.25,.19,root) for k in range(16) if k%4!=0]
        elif bass_mode=='latin':
            bass_events=[(0,1.35,root),(1.5,.42,root+fifth_iv),(2,1.35,root),(3.5,.38,approach if phrase_end else root+fifth_iv)]
        elif bass_mode=='dembow':
            bass_events=[(0,1.38,root),(1.5,.45,root),(2,1.35,root),(3.5,.4,approach if phrase_end else root+fifth_iv)]
        elif bass_mode=='funk':
            bass_events=[(0,.36,root),(.75,.22,root+third_iv),(1.5,.36,root+12),(2.25,.22,root+fifth_iv),(2.75,.32,root),(3.5,.26,approach)]
        elif bass_mode=='slap':
            bass_events=[(0,.32,root),(.75,.28,root),(1.5,.35,root+12),(2.25,.26,root),(2.75,.32,root+fifth_iv),(3.5,.28,approach if phrase_end else root)]
        elif bass_mode=='808':
            bass_events=[(0,1.45,root),(1.5,1.15,root),(2.75,.68,root+(12 if phrase_end and root<=38 else 0)),(3.5,.42,approach if phrase_end else root)]
        elif bass_mode=='reese_bass':
            bass_events=[(0,2.38,root),(2.5,1.42,approach if phrase_end else root)]
        elif bass_mode=='wobble_bass':
            bass_events=[(0,.85,root),(1.0,.4,root),(1.5,.42,root+12),(2.5,.68,root),(3.25,.32,root+fifth_iv),(3.625,.3,approach)] if peak else [(0,1.8,root),(2,1.8,root)]
        elif bass_mode=='pop':
            bass_events=[(0,1.32,root),(1.5,.42,root),(2,.92,root),(3,.72,approach if phrase_end else root+fifth_iv)]
        else:
            bass_events=[(0,.82,root),(1.5,.44,root),(2.5,.72,root+fifth_iv),(3.5,.32,approach if phrase_end else root)]
        if kind in ['intro','bridge','outro'] and g['id']!='piano':
            bass_events=[(0,3.2,root)] if (local>=sec['bars']//2 or kind=='bridge') else []
        if kind=='build' and local>=sec['bars']-1:bass_events=[]
        for pos,dur,n in bass_events:
            if kind=='outro' and bar==bars-1 and pos==0:dur=max(dur,(s['duration']-.7)/beat-bt)
            bvel=72+section_energy*21+(4 if pos==0 else (-3 if pos%1 else 0))
            if g['id']=='piano':bvel=46+section_energy*18
            emit('bass',bt+pos,dur,n,bvel)

        # 3. LEAD MELODY (thematic recurrence, chord-tone accents, phrase-arch dynamics)
        lead_active=kind not in ['intro','build'] or (kind=='intro' and local>=max(1,sec['bars']-2)) or (kind=='build' and local<max(1,sec['bars']//2))
        if g['id']=='piano':lead_active=True
        elif kind=='bridge':lead_active=(local%2==0)
        elif kind=='outro':lead_active=local<max(1,sec['bars']//2)
        row=motif[phrase]
        if kind in ['verseB','bridge']:row=motif[(phrase+4)%8]
        last_pitch=None
        if lead_active:
            for j,(pos,deg) in enumerate(row):
                if not peak and j==len(row)-1 and phrase%2==1 and g['id']!='piano':continue
                if phrase_end and pos>=2.85:continue
                if kind=='final' and s['variation']>.3 and phrase>=4 and j==min(2,len(row)-1):deg+=2
                if kind=='verseB':deg+=(-1 if phrase%2 else 1)
                n=60+tonic+scale[deg%7]+12*(deg//7-1)
                low,high=(57,81) if low_register else (60,84)
                if g['family']=='rock':low,high=59,82
                while n>high:n-=12
                while n<low:n+=12
                # Strong rhythmic accents and phrase cadences land on a chord tone.
                if j==0 or (pos%1==0 and pos in [0,2]) or (phrase_end and j==len(row)-1):
                    candidates=[x for x in range(low,high+1) if x%12 in pcs]
                    if candidates:n=min(candidates,key=lambda x:abs(x-n))
                if last_pitch is not None and abs(n-last_pitch)>8:
                    n+=-12 if n>last_pitch else 12
                # Climax octave lift in the second half of the final chorus when comfortable.
                if kind=='final' and s['variation']>.45 and local>=sec['bars']//2 and n+12<=84 and g['lead'] in ['hook','sing']:
                    n+=12
                last_pitch=n
                next_pos=row[j+1][0] if j+1<len(row) else (3.1 if phrase_end else 3.85)
                dur=max(.18,(next_pos-pos)*(.86 if peak else .93))
                if phrase_end and j==len(row)-1:dur=max(dur,1.15)
                if s['mood'] in ['happy','playful'] and g['lead']!='classical':dur*=.84
                if restrained or g['id']=='piano':dur*=1.08
                if g['lead']=='sparse':dur*=1.28
                # Natural phrase-arch dynamics: swell toward the middle of the 4-bar phrase, taper at cadence.
                phrase_arch=math.sin(math.pi*((local%4)+(pos/4))/4)*7
                beat_accent=4 if pos in [0,2] else (-3 if pos%1 else 0)
                lvel=(62 if g['id']=='piano' else 69)+section_energy*24+phrase_arch+beat_accent
                emit('lead',bt+pos,dur,n,lvel)

        # 4. COUNTER-MELODY (voice-led answer in phrase breathing space, independent of melody_seed)
        counter_active=lead_active and phrase%2==1 and s['complexity']>.25 and kind not in ['outro'] and g['id']!='piano'
        if g['id']=='piano' and peak and phrase_end and s['complexity']>.65:counter_active=True
        if counter_active:
            slots=[2.75,3.25,3.625] if (phrase_end and s['complexity']>.72) else ([3.0,3.5] if phrase_end else [3.5])
            for j,pos in enumerate(slots):
                target_pc=pcs[(j+bar+1)%len(pcs)]
                candidates=[x for x in range(64,82) if x%12==target_pc]
                n=min(candidates,key=lambda x:abs(x-counter_last)) if candidates else 72
                counter_last=n
                emit('counter',bt+pos,.38 if j<len(slots)-1 else .46,n,51+section_energy*16-j*2)

        # 5. PAD / ATMOSPHERE (genre-appropriate harmonic bed)
        pad_min=g.get('pad_min',0.)
        pad_active=(g['id']!='piano' and s['complexity']>=pad_min and (peak or kind in ['intro','bridge','outro'] or s['complexity']>.72))
        if pad_active and local%2==0:
            pad_span=min(7.7,(sec['bars']-local)*4-.25)
            for n in chord[:3]:
                pn=n+12 if n<57 else (n-12 if n>77 else n)
                emit('pad',bt,max(1.8,pad_span),pn,41+section_energy*15)

        # 6. ARPEGGIO / OSTINATO (only in genres or complexity levels where idiomatic)
        arp_min=g.get('arp_min',.35)
        arp_active=(g['id']!='piano' and s['complexity']>arp_min and (
            peak or (kind in ['build','intro'] and (g['id'] in ['trance','psytrance','techno','synthwave','retrowave','darksynth','post-rock','cinematic','ambient'] or s['complexity']>.75))))
        if arp_active:
            fast_arp=g['id'] in ['trance','psytrance','techno','synthwave','retrowave','darksynth','colour-bass','future-bass','dance-dnb']
            step=.25 if fast_arp else .5
            arp_notes=sorted(chord)+[min(chord)+12]
            pattern_idx=[0,1,2,3,2,1,3,2] if g['family'] in ['classical','acoustic'] else [0,2,1,3,0,3,1,2]
            total_steps=round(4/step)
            for k in range(total_steps):
                if not fast_arp and g['family'] not in ['classical','acoustic','ambient'] and k%8 in [6,7]:continue
                if g['family']=='ambient' and k%2==1:continue
                n=arp_notes[pattern_idx[k%len(pattern_idx)]%len(arp_notes)]+(12 if max(arp_notes)<74 else 0)
                avel=43+section_energy*17+(4 if k%4==0 else -3)
                emit('arp',bt+k*step,step*(.82 if g['family'] in ['classical','acoustic','ambient'] else .64),min(n,88),avel)

        # 7. DRUM & PERCUSSION GRAMMARS (strictly silent when rhythm=='none')
        rhythm=g['rhythm']
        if rhythm=='none':
            drum_active=False
        elif rhythm=='cinematic':
            drum_active=kind not in ['intro','bridge','outro'] or (kind=='intro' and local>=max(1,sec['bars']-2))
        else:
            drum_active=kind not in ['bridge']
            if kind=='intro':drum_active=local>=max(1,sec['bars']//2)
            elif kind=='outro':drum_active=local<sec['bars']*.65

        if drum_active and rhythm=='cinematic':
            # Orchestral percussion only: concert bass drum (36), low timpani/toms (41,43,45), crash swell (49).
            emit('drums',bt,.45,36,78+section_energy*26)
            if peak:
                emit('drums',bt+2,.4,36,70+section_energy*22)
                for pos,tom in [(1.5,41),(3.0,43),(3.5,45)]:
                    emit('drums',bt+pos,.28,tom,58+section_energy*22)
            elif kind=='build':
                step=.5 if local<sec['bars']-1 else .25
                for k in range(int(4/step)):
                    emit('drums',bt+k*step,.2,41 if k%2==0 else 43,46+local/max(1,sec['bars'])*42)
            if phrase_end and s['variation']>.2:
                for k,tom in enumerate([41,43,45,41]):
                    emit('drums',bt+3+k*.25,.22,tom,60+k*6)
            if local==0 and peak:
                emit('drums',bt,1.2,49,66+section_energy*12)
        elif drum_active:
            kicks=[];snares=[];claps=[];rims=[]
            if rhythm in ['house','trance','four']:
                kicks=[0,1,2,3];snares=[1,3]
                if peak or rhythm=='house':claps=[1,3]
            elif rhythm=='retro':
                kicks=[0,1,2,3];snares=[1,3];claps=[1,3] if peak else []
            elif rhythm=='afro':
                kicks=[0,1,2,3];rims=[1,3] if not peak else [];snares=[1,3] if peak else []
            elif rhythm=='garage':
                kicks=[0,1.75,2.5] if bar%2==0 else [0,2.5,3.75];snares=[1,3];rims=[.75,2.25] if peak else []
            elif rhythm=='dembow':
                kicks=[0,1,2,3];snares=[.75,1.5,2.75,3.5]
            elif rhythm=='bossa':
                kicks=[0,1.5,2,3.5];rims=[0,1.5,3] if bar%2==0 else [1,2.5]
            elif rhythm in ['half','dubstep']:
                kicks=[0,1.5,3.25] if bar%2==0 else [0,.75,3.5];snares=[2];claps=[2] if peak else []
                if rhythm=='dubstep' and peak:kicks=[0,3.5] if bar%2==0 else [0,1.75,3.25]
            elif rhythm=='drumstep':
                kicks=[0,1.5,3.5] if bar%2==0 else [0,2.75];snares=[2];claps=[2]
            elif rhythm=='break':
                kicks=[0,2.5] if bar%4!=3 else [0,1.75,2.5];snares=[1,3]
            elif rhythm=='jungle':
                kicks=[0,2.5] if bar%2==0 else [0,1.5,2.75];snares=[1,3] if bar%2==0 else [1,2.5,3.25]
            elif rhythm=='trap':
                kicks=[0,1.75,2.5] if bar%2==0 else [0,.75,3.25];snares=[2];claps=[2]
            elif rhythm=='phonk':
                kicks=[0,1,2,3] if peak else [0,1.75,2.5];snares=[1,3] if peak else [2];claps=snares[:]
            elif rhythm=='hiphop':
                kicks=[0,1.75,2.5] if bar%2==0 else [0,2,3.5];snares=[1,3]
            elif rhythm=='lofi':
                kicks=[0,2.5] if bar%2==0 else [0,1.75,2.5];rims=[1,3] if not peak else [];snares=[1,3] if peak else []
            elif rhythm=='jazz':
                kicks=[0,2.5] if peak else [0];rims=[1.5,3.5] if bar%2==1 and s['variation']>.3 else []
            elif rhythm=='smooth_jazz':
                kicks=[0,2,2.5] if bar%2 else [0,2];rims=[1,3] if not peak else [];snares=[1,3] if peak else []
            elif rhythm=='funk':
                kicks=[0,.75,2,2.5,3.5] if bar%2==0 else [0,.75,2.25,3];snares=[1,3]
            elif rhythm=='rock':
                kicks=[0,1.5,2] if bar%2==0 else [0,2,2.5,3.5];snares=[1,3]
            elif rhythm=='punk':
                kicks=[0,1.5,2,3.5] if bar%2==0 else [0,.75,2,2.5,3.5];snares=[1,3]
            elif rhythm=='postrock':
                kicks=[0,2.5] if not peak else [0,1.5,2,3];rims=[1,3] if not peak else [];snares=[1,3] if peak else []
            elif rhythm=='soft':
                kicks=[0,2];rims=[1,3]
            else:
                # 'pop'
                kicks=[0,1.5,2.5] if bar%2==0 else [0,2,2.75];snares=[1,3];claps=[1,3] if peak else []

            if kind=='build':
                kicks=[0,1,2,3] if local<sec['bars']-1 else []
                claps=[]

            kick_vel=50+section_energy*14 if rhythm in ['jazz','bossa','soft','lofi'] else 86+section_energy*24
            for pos in kicks:emit('drums',bt+pos,.12,36,kick_vel)
            for pos in snares:
                snr_note=40 if rhythm=='retro' and peak else 38
                emit('drums',bt+pos,.14,snr_note,70+section_energy*26)
            for pos in claps:emit('drums',bt+pos,.13,39,48+section_energy*15)
            for pos in rims:emit('drums',bt+pos,.11,37,54+section_energy*18)

            # Cymbals, Hi-Hats & Idiomatic Top-End Groove
            if rhythm=='jazz':
                # Classic jazz ride pattern + hi-hat foot chick on beats 2 and 4 (positions 1 and 3).
                for pos,acc in [(0,6),(1,10),(1.5,0),(2,5),(3,10),(3.5,0)]:
                    if s['energy']<.28 and pos%1:continue
                    emit('drums',bt+pos,.16,51,50+section_energy*16+acc)
                for pos in [1,3]:emit('drums',bt+pos,.09,44,44+section_energy*12)
            else:
                subdivisions=16 if (rhythm in ['trap','drumstep','funk','jungle','break','trance','garage'] or (peak and rhythm in ['half','dubstep','phonk','afro'])) else 8
                if s['energy']<.35:subdivisions=4
                elif s['energy']>.85 and subdivisions==8 and rhythm not in ['bossa','soft','lofi','postrock','punk']:subdivisions=16
                for k in range(subdivisions):
                    pos=k*4/subdivisions
                    offbeat=abs((pos%1)-.5)<1e-4
                    if rhythm in ['house','trance'] and offbeat and (peak or kind in ['verse','verseB']):
                        n=46;hvel=56+section_energy*16
                    elif rhythm in ['rock','punk','postrock'] and peak:
                        n=51 if rhythm=='postrock' else 46
                        hvel=(60 if k%2==0 else 44)+section_energy*15
                    elif rhythm=='funk' and abs(pos-3.5)<1e-4:
                        n=46;hvel=60+section_energy*15
                    else:
                        n=42;hvel=(50 if k%2==0 else 34)+section_energy*14
                    emit('drums',bt+pos,.09,n,hvel)
                # Subtle shaker / tambourine air in energetic dance, pop, latin, and afro peaks.
                if peak and s['energy']>.45 and rhythm in ['house','afro','bossa','pop','funk']:
                    perc_note=54 if rhythm in ['pop','funk'] else 70
                    for pos in ([.5,1.5,2.5,3.5] if rhythm!='pop' else [1,3]):
                        emit('drums',bt+pos,.1,perc_note,40+section_energy*14)

            if rhythm=='afro':
                for pos,n in [(.5,64),(1.25,63),(1.75,62),(2.75,62),(3.5,64)]:
                    emit('drums',bt+pos,.14,n,56+section_energy*14)
            if rhythm=='phonk':
                for pos in ([0,.75,1.5,2.5,3.25] if peak else [0,1.5,3]):
                    emit('drums',bt+pos,.11,56,56+section_energy*18)
            if rhythm in ['jungle','break','hiphop','funk','garage'] and (bar%2==1 or rhythm in ['funk','jungle']):
                for pos in ([1.75,2.25,3.75] if rhythm in ['funk','jungle'] else [2.25,3.75]):
                    emit('drums',bt+pos,.07,38,33+section_energy*8)
            if rhythm in ['trap','phonk'] and (phrase_end or (peak and bar%2==1)):
                steps=6 if phrase_end else 4
                start_roll=3.25 if phrase_end else 1.5
                for k in range(steps):emit('drums',bt+start_roll+k*.125,.055,42,42+k*4)
            fill=(local%8==7 or local==sec['bars']-1) and s['variation']>.2 and rhythm not in ['bossa','soft','lofi']
            if fill:
                fill_notes=[48,47,45,43] if rhythm in ['retro','rock','punk','postrock'] else [38,38,47,45]
                for k in range(4):emit('drums',bt+3+k*.25,.14,fill_notes[k],60+k*5)
            if kind=='build' and local>=sec['bars']//2:
                step=.5 if local<sec['bars']-2 else .25
                for k in range(int(4/step)):emit('drums',bt+k*step,.08,38,44+local/max(1,sec['bars'])*42)
            if local==0 and peak and rhythm not in ['lofi','bossa','soft']:
                emit('drums',bt,1.0,49,60+section_energy*12)

        # 8. TRANSITIONS / FX
        if kind=='build' and local==max(0,sec['bars']-2) and g['family'] in ['house','bass','dnb','retro']:
            emit('fx',bt,min(7.7,(sec['bars']-local)*4-.15),72,68,'rise')
        if peak and local==0 and (g['family'] in ['house','bass','dnb','retro'] or g['id'] in ['dance-pop','kpop','electropop','trap','phonk']):
            emit('fx',bt,1.8,60,58,'fall')

    if g['id']=='piano':
        for role in ['drums','pad','fx','arp']:tracks[role]['notes']=[]
    # Keep the seed's automatic choice even when this render starts with a
    # manually selected patch or a mix loaded from a saved project.
    automatic_palette=choose_palette(g,dict(s,instruments={}))
    for t in tracks.values():
        t['notes'].sort(key=lambda n:n[0])
        base_gain=next(row[4] for row in ROLE_INFO if row[0]==t['id'])
        t['curve']=s['mix'].get(t['id'],{}).get('curve',[[0,1],[1,1]])
        t['gain_default']=min(base_gain,gain_limit(INSTRUMENTS[t['instrument']],t['id'],t['notes']))
        if t['id'] not in s['mix']:t['gain']=t['gain_default']
        default_instrument=automatic_palette[t['id']]
        t['seed_default']=dict(instrument=default_instrument,
            gain=min(base_gain,gain_limit(INSTRUMENTS[default_instrument],t['id'],t['notes'])),
            pan=next(row[3] for row in ROLE_INFO if row[0]==t['id']),mute=False,solo=False,
            tone=dict(brightness=.5,attack=.5,release=.5,drive=0,space=0),curve=[[0,1],[1,1]])
    timeline=[dict(x,start=round(x['start_bar']*bar_seconds,4),duration=round(x['bars']*bar_seconds,4)) for x in sections]
    timeline[-1]['duration']=round(s['duration']-timeline[-1]['start'],4)
    return dict(version=VERSION,settings=s,title=s['title'],genre=g['name'],family=g['family'],mode=mode,key=KEYS[tonic],
        bpm=s['bpm'],duration=s['duration'],bars=bars,sections=timeline,
        harmony=[{k:v for k,v in h.items() if k!='pcs'} for h in harmony],tracks=list(tracks.values()),note_count=sum(len(t['notes']) for t in tracks.values()))

def midi_bytes(plan):
    import struct
    def vlq(n):
        b=[n&127];n>>=7
        while n:b.insert(0,(n&127)|128);n>>=7
        return bytes(b)
    chunks=[];tpq=480;beat=60/plan['bpm']
    for i,t in enumerate(plan['tracks']):
        channel=9 if t['id']=='drums' else (i if i<9 else i+1)
        events=[]
        if i==0:events.append((0,b'\xff\x51\x03'+int(60000000/plan['bpm']).to_bytes(3,'big')))
        name=t['name'].encode('utf-8');events.append((0,b'\xff\x03'+vlq(len(name))+name))
        inst=INSTRUMENTS[t['instrument']]
        bank=inst.get('bank',0);program=inst.get('program',81)
        events.extend([(0,bytes([0xb0+channel,0,bank if bank<128 else 0])),(0,bytes([0xc0+channel,program]))])
        for start,duration,note,velocity,*_ in t['notes']:
            events.append((round(start/beat*tpq),bytes([0x90+channel,note,velocity])))
            events.append((round((start+duration)/beat*tpq),bytes([0x80+channel,note,0])))
        events.sort(key=lambda e:(e[0],e[1][0]>>4!=8))
        last=0;data=bytearray()
        for tick,msg in events:data+=vlq(tick-last)+msg;last=tick
        data+=b'\0\xff\x2f\0';chunks.append(b'MTrk'+struct.pack('>I',len(data))+data)
    return b'MThd'+struct.pack('>IHHH',6,1,len(chunks),tpq)+b''.join(chunks)
