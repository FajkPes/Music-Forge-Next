import json,math,tempfile,unittest
from pathlib import Path
import numpy as np
from catalogue import ROOT,GENRES,GENRE_POOLS
from composer import compose,normalize_settings,INSTRUMENTS
from balance import gain_limit
from audio_engine import process_stem,active_ratio,SR
from seed_library import SeedLibrary

class BalanceAndSeedTests(unittest.TestCase):
 def test_seed_reset_ignores_loaded_or_manual_mix(self):
  for genre in ['melodic-house','piano','rock']:
   settings=dict(genre=genre,duration=30,seed=431207,sound_seed=177)
   automatic=compose(settings)
   edited=compose(dict(settings,instruments={'lead':'syn:glass-pluck'},mix={'lead':{'gain':1.2,'pan':-1,'mute':True,'curve':[[0,0],[1,1]]}},tone={'lead':{'attack':1,'brightness':0}}))
   a=next(t for t in automatic['tracks'] if t['id']=='lead');b=next(t for t in edited['tracks'] if t['id']=='lead')
   self.assertEqual(b['instrument'],'syn:glass-pluck');self.assertEqual(b['gain'],1.2)
   self.assertEqual(b['seed_default']['instrument'],a['instrument']);self.assertEqual(b['seed_default']['gain'],a['gain'])
   self.assertEqual(b['seed_default']['tone'],a['tone']);self.assertEqual(b['seed_default']['curve'],[[0,1],[1,1]])
   self.assertFalse(b['seed_default']['mute']);self.assertEqual(b['seed_default']['pan'],a['pan'])
 def test_curve_roundtrip_keeps_manual_gain_and_endpoints(self):
  raw=dict(seed=177,mix={'lead':{'gain':1.2,'curve':[[.8,.3],[.2,.7],[.5,1.1]]}})
  settings=normalize_settings(raw)
  self.assertEqual(normalize_settings(settings),settings)
  track=next(t for t in compose(settings)['tracks'] if t['id']=='lead')
  self.assertEqual(track['gain'],1.2)
  self.assertEqual(track['curve'],[[0,.7],[.2,.7],[.5,1.1],[.8,.3],[1,.3]])
  with tempfile.TemporaryDirectory() as folder:
   library=SeedLibrary(Path(folder)/'seeds.json');library.save(settings,'Křivka')
   self.assertEqual(library.read()['seeds'][0]['settings']['mix'],settings['mix'])
  many=normalize_settings(dict(mix={'lead':{'curve':[[i/65,.5] for i in range(1,65)]}}))['mix']['lead']['curve']
  self.assertEqual(len(many),64);self.assertEqual(many[0][0],0);self.assertEqual(many[-1][0],1)
 def test_user_limits_and_dense_high_register(self):
  for instrument,expected in [('syn:silk-pluck',.5),('syn:glass-pluck',.2),('syn:arp',.25),('sf:0:11',.5),('ms:0:11',.5),('ms:0:34',.2),('sf:0:34',.2)]:
   for role in ['lead','chords','arp','counter','bass']:
    p=compose(dict(duration=30,seed=197,instruments={role:instrument}))
    t=next(t for t in p['tracks'] if t['id']==role)
    self.assertLessEqual(t['gain'],expected);self.assertLessEqual(t['gain_default'],expected)
    manual=compose(dict(duration=30,seed=197,instruments={role:instrument},mix={role:{'gain':1.2}}))
    self.assertEqual(next(x for x in manual['tracks'] if x['id']==role)['gain'],1.2)
  self.assertEqual(gain_limit(INSTRUMENTS['ms:17:71'],'bass'),.2)
  notes=[[i*.125,.1,85,100] for i in range(40)]
  self.assertLessEqual(gain_limit(INSTRUMENTS['sf:0:73'],'lead',notes),.5)
 def test_balancing_keeps_every_note(self):
  for genre in GENRES:
   for seed in [19,431207]:
    settings=dict(genre=genre['id'],seed=seed,duration=61)
    a=compose(settings)
    b=compose(dict(settings,instruments={'lead':'syn:glass-pluck','bass':'syn:sub'},
                   mix={'lead':{'gain':1.15,'pan':-.3,'curve':[[0,.4],[.5,1],[1,.6]]},'drums':{'gain':.9}},
                   tone={'lead':{'brightness':.2,'space':.6}},section_levels={'0':.7}))
    for x,y in zip(a['tracks'],b['tracks']):self.assertEqual(x['notes'],y['notes'])
    self.assertAlmostEqual(b['sections'][-1]['start']+b['sections'][-1]['duration'],b['duration'],places=3)
 def test_genre_pools_and_instrument_selection_hygiene(self):
  solo_winds={i for i,inst in INSTRUMENTS.items() if inst.get('group') in {'Dechy','Flétny'} or any(k in inst['name'].lower() for k in ['sax','flute','oboe','clarinet','bassoon','piccolo','recorder','whistle','ocarina','bagpipe'])}
  for genre in GENRES:
   gid=genre['id'];self.assertIn(gid,GENRE_POOLS)
   for role,choices in GENRE_POOLS[gid].items():
    self.assertTrue(choices,f'{gid}:{role}')
    for cid in choices:self.assertIn(cid,INSTRUMENTS)
   for seed in [7,431207]:
    p=compose(dict(genre=gid,seed=seed,duration=45))
    tracks={t['id']:t for t in p['tracks']}
    if genre['rhythm']=='none':self.assertEqual(len(tracks['drums']['notes']),0,gid)
    else:self.assertGreater(len(tracks['drums']['notes']),0,gid)
    if gid=='cinematic':
     self.assertFalse(any(n[2] in {42,46} for n in tracks['drums']['notes']))
    if gid!='piano':
     self.assertNotIn(tracks['bass']['instrument'],solo_winds,gid)
     self.assertNotIn(tracks['pad']['instrument'],solo_winds,gid)
 def test_active_ratio_and_click_free_sidechain(self):
  chord_notes=[[0,1.85,60,90,'normal'],[0,1.85,64,90,'normal'],[0,1.85,67,90,'normal'],[0,1.85,71,90,'normal']]
  mono_notes=[[0,1.85,72,95,'normal']]
  self.assertAlmostEqual(active_ratio(chord_notes,4.0),active_ratio(mono_notes,4.0),places=6)
  plan=compose(dict(duration=20,genre='melodic-house',space=0))
  drums=next(t for t in plan['tracks'] if t['id']=='drums');drums['notes']=[[1.0,.15,36,110,'normal']]
  bass=next(t for t in plan['tracks'] if t['id']=='bass');bass['notes']=[[.5,2.5,36,100,'normal']]
  data=np.column_stack([np.sin(np.arange(20*SR)*2*np.pi*55/SR)*.08]*2).astype('float32')
  process_stem(data,bass,plan)
  k=SR
  step_jump=float(abs(data[k,0]-data[k-1,0]))
  self.assertLess(step_jump,.015)
 def test_outro_gain_never_returns_to_unity_after_last_bar(self):
  plan=compose(dict(duration=20,genre='melodic-house',space=0));plan['sections']=[dict(kind='outro',start=0,duration=18.5)]
  t=next(t for t in plan['tracks'] if t['id']=='lead');t['notes']=[[0,19.4,69,100,'normal']]
  data=np.column_stack([np.sin(np.arange(20*SR)*2*np.pi*440/SR)*.05]*2).astype('float32')
  old=data.copy();broken=dict(plan,_keep_legacy_tail_gap=True);process_stem(old,t,broken)
  fixed=data.copy();process_stem(fixed,t,plan)
  rms=lambda a,start,end:float(np.sqrt(np.mean(a[round(start*SR):round(end*SR)].astype('float64')**2)))
  jump_old=20*math.log10(rms(old,18.51,18.61)/rms(old,18.2,18.3));jump_new=20*math.log10(rms(fixed,18.51,18.61)/rms(fixed,18.2,18.3))
  self.assertGreater(jump_old,5.9);self.assertLess(abs(jump_new),.05)
 def test_library_capacity_roundtrip_and_undo(self):
  with tempfile.TemporaryDirectory() as folder:
   library=SeedLibrary(Path(folder)/'seeds.json')
   recipe=compose(dict(seed=777,genre='synthwave',instruments={'lead':'syn:glass-pluck'},mix={'lead':{'gain':.2}}))['settings']
   item=library.save(recipe,'Moje skladba');self.assertEqual(library.read()['seeds'][0]['settings'],recipe)
   library.save(recipe,'Přejmenováno');self.assertEqual(len(library.read()['seeds']),1)
   for seed in range(49):library.save(dict(seed=seed),'Seed '+str(seed))
   with self.assertRaisesRegex(ValueError,'50/50'):library.save(dict(seed=987654),'Padesátý první')
   library.delete(item['id']);self.assertEqual(len(library.read()['seeds']),49);library.undo();self.assertEqual(len(library.read()['seeds']),50)
   self.assertTrue(library.path.with_suffix('.backup.json').exists())
 def test_export_names_and_title_generator(self):
  from server import export_filename
  from catalogue import MOODS,TITLE_BANKS,MOOD_WORDS,generate_title
  self.assertEqual(export_filename('Můj horizont','opus',777),'Můj horizont (777).opus')
  self.assertEqual(export_filename('Můj horizont','opus',777,1),'Můj horizont (777).opus')
  self.assertEqual(export_filename('Můj horizont','opus',777,2),'Můj horizont (777) v2.opus')
  self.assertEqual(export_filename('Můj horizont','opus',777,3),'Můj horizont (777) v3.opus')
  self.assertEqual(export_filename('A<>:"/\\|?*\n','wav',7),'A (7).wav')
  self.assertEqual(export_filename('CON','mid',1),'_CON (1).mid')
  for genre in GENRES:
   gid=genre['id'];self.assertIn(gid,TITLE_BANKS)
   first,second=TITLE_BANKS[gid]['first'],TITLE_BANKS[gid]['second']
   self.assertEqual(len(first),20,gid);self.assertEqual(len(second),20,gid)
   self.assertEqual(len(set(first)),20,gid);self.assertEqual(len(set(second)),20,gid)
   t1=generate_title(gid,'uplifting',431207,.68)
   self.assertEqual(t1,generate_title(gid,'uplifting',431207,.68))
   seed_variants={generate_title(gid,'uplifting',431207+k,.68) for k in range(8)}
   mood_variants={generate_title(gid,m['id'],431207,.68) for m in MOODS[:8]}
   self.assertGreaterEqual(len(seed_variants),6,gid)
   self.assertGreaterEqual(len(mood_variants),6,gid)
  for mood in MOODS:
   mid=mood['id'];self.assertIn(mid,MOOD_WORDS)
   self.assertGreaterEqual(len(MOOD_WORDS[mid]['first']),6,mid)
   self.assertGreaterEqual(len(MOOD_WORDS[mid]['second']),6,mid)
  auto=normalize_settings(dict(genre='synthwave',mood='nostalgic',seed=431207,energy=.62))
  self.assertEqual(auto['title'],generate_title('synthwave','nostalgic',431207,.62))
  manual=normalize_settings(dict(genre='synthwave',mood='nostalgic',seed=431207,title='Vlastní jméno'))
  self.assertEqual(manual['title'],'Vlastní jméno')

if __name__=='__main__':unittest.main(verbosity=2)
