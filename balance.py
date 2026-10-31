"""Suggested starting gains only. Explicit mixer values always take precedence."""
import statistics

PRESET_LIMITS={'syn:silk-pluck':.50,'syn:glass-pluck':.20,'syn:arp':.25,'ms:0:34':.20,'sf:0:34':.20}
PIERCING_NAMES=('music box','glockenspiel','xylophone','tubular','bell','celest','piccolo','whistle','bagpipe','agogo','kalimba','steel drum','harpsichord')
BRIGHT_GROUPS={'Chromatické perkuse','Synth lead','Žestě','Flétny','Dechy'}
BRIGHT_KINDS={'pluck','bell','pulse','saw'}

def instrument_limits(instrument):
    limits={}
    name_cf=instrument['name'].casefold()
    if instrument['id'] in PRESET_LIMITS:
        limits={r:PRESET_LIMITS[instrument['id']] for r in ['bass','chords','lead','counter','pad','arp','fx']}
    elif 'picked bass' in name_cf or 'pick bass' in name_cf:
        limits={r:.20 for r in ['bass','chords','lead','counter','pad','arp','fx']}
    elif 'vibraphone' in name_cf:
        limits={r:.50 for r in ['bass','chords','lead','counter','pad','arp','fx']}
    elif any(token in name_cf for token in PIERCING_NAMES):
        limits=dict(lead=.48,chords=.42,counter=.26,pad=.28,arp=.24,bass=.28,fx=.26)
    elif instrument.get('group') in BRIGHT_GROUPS or instrument.get('kind') in BRIGHT_KINDS:
        limits=dict(lead=.60,chords=.52,counter=.32,pad=.36,arp=.28,bass=.35,fx=.30)
    elif instrument.get('group')=='Kytary' and any(k in name_cf for k in ('distortion','overdrive','feedback')):
        limits=dict(lead=.58,chords=.50,counter=.32,pad=.30,arp=.26,bass=.35,fx=.28)
    if 'Expr.' in instrument['name'] and instrument.get('group') in {'Žestě','Flétny','Dechy'}:
        limits.update(bass=.20,arp=.25,counter=.28,pad=.32,lead=.50)
    return limits

def gain_limit(instrument,role,notes=()):
    limit=instrument.get('gain_limits',instrument_limits(instrument)).get(role,1.5)
    if role in ['lead','arp','counter','chords'] and len(notes)>4:
        starts=sorted({n[0] for n in notes});gaps=[b-a for a,b in zip(starts,starts[1:]) if b-a>.015]
        if gaps and statistics.median(gaps)<=.25 and statistics.median(n[2] for n in notes)>=76:
            limit=min(limit,{'lead':.50,'arp':.25,'counter':.28,'chords':.50}[role])
    return limit
