import unittest,sys,json,math,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from catalogue import GENRES,MOODS,load_instruments
from composer import compose,normalize_settings,midi_bytes

class MusicTests(unittest.TestCase):
 def test_legacy_live_preview_preserves_section_gain_convention(self):
  import tempfile
  from live_backend import prepare_track
  from audio_engine import stem_fingerprint
  p=compose(dict(genre='melodic-house',duration=20,seed=951))
  lead=next(t for t in p['tracks'] if t['id']=='lead')
  with tempfile.TemporaryDirectory() as root:
   folder=Path(root)
   for baked in [False,True]:
    (folder/'project.json').write_text(json.dumps(dict(plan=p,render={'arrangement_gain_baked':baked})),encoding='utf-8')
    plan,track,digest=prepare_track(folder,'lead',lead['instrument'],lead['tone'])
    self.assertEqual(plan['_skip_arrangement_gain'],not baked)
    self.assertEqual(track['notes'],lead['notes'])
    normal=dict(plan);normal.pop('_skip_arrangement_gain')
    self.assertEqual(digest==stem_fingerprint(track,normal),baked)
 def test_all_profiles_and_boundaries(self):
  for g in GENRES:
   self.assertEqual(len(g['recommended']),5)
   for length,seed in [(20,0),(61,19),(210,431207),(600,2147483647)]:
    for mood in ['happy','sad','dark']:
     p=compose(dict(genre=g['id'],duration=length,seed=seed,mood=mood))
     self.assertEqual(p['duration'],length)
     self.assertEqual(sum(s['bars'] for s in p['sections']),p['bars'])
     self.assertTrue(all(s['start']+s['duration']<=length+.001 for s in p['sections']))
     self.assertGreater(p['note_count'],10)
     self.assertEqual(len(p['harmony']),p['bars'])
     for t in p['tracks']:
      self.assertIn(t['instrument'],{i['id'] for i in load_instruments()})
      for n in t['notes']:
       self.assertGreaterEqual(n[0],0)
       self.assertGreater(n[1],0)
       self.assertLessEqual(n[0]+n[1],length+.001)
       self.assertTrue(0<=n[2]<=127)
       self.assertTrue(0<n[3]<=127)
  print('Validated',len(GENRES)*12,'complete musical plans',flush=True)
 def test_determinism_and_seed_diversity(self):
  for genre in ['melodic-house','piano','rock','jazz','trap','liquid-dnb']:
   s=dict(genre=genre,seed=901,duration=61)
   self.assertEqual(compose(s),compose(s))
   themes=[]
   for seed in range(20):
    p=compose(dict(s,seed=seed));notes=next(t['notes'] for t in p['tracks'] if t['id']=='lead')
    themes.append(tuple((round(n[0],1),n[2]) for n in notes))
   self.assertEqual(len(set(themes)),20)
 def test_independent_variants(self):
  a=compose({'genre':'synthwave','seed':12,'duration':61})
  b=compose(dict(a['settings'],melody_seed=912))
  self.assertEqual(a['sections'],b['sections']);self.assertEqual(a['harmony'],b['harmony'])
  for ta,tb in zip(a['tracks'],b['tracks']):
   if ta['id']!='lead':self.assertEqual(ta['notes'],tb['notes'])
  self.assertNotEqual(a['tracks'][3]['notes'],b['tracks'][3]['notes'])
  c=compose(dict(a['settings'],sound_seed=77))
  self.assertTrue(any(ta['instrument']!=tc['instrument'] for ta,tc in zip(a['tracks'],c['tracks'])))
  for ta,tc in zip(a['tracks'],c['tracks']):self.assertEqual(ta['notes'],tc['notes'])
  d=compose(dict(a['settings'],instruments={'lead':'syn:glass-pluck'}))
  for ta,td in zip(a['tracks'],d['tracks']):
   self.assertEqual(ta['notes'],td['notes'])
   if ta['id']!='lead':self.assertEqual(ta['instrument'],td['instrument'])
 def test_controls_have_musical_effect(self):
  for setting,role in [('complexity','counter'),('energy','drums'),('variation','drums'),('humanize','lead')]:
   a=compose({'genre':'future-bass','duration':61,'seed':18,setting:0})
   b=compose(dict(a['settings'],**{setting:1}))
   self.assertNotEqual(next(t['notes'] for t in a['tracks'] if t['id']==role),next(t['notes'] for t in b['tracks'] if t['id']==role),setting)
 def test_harmony_and_midi(self):
  for g in GENRES:
   p=compose({'genre':g['id'],'seed':10,'duration':61})
   for h in p['harmony']:
    self.assertTrue(all(a<b for a,b in zip(h['chord'],h['chord'][1:])))
   data=midi_bytes(p);self.assertEqual(data[:4],b'MThd');self.assertEqual(data.count(b'MTrk'),8)
 def test_input_validation(self):
  s=normalize_settings(dict(duration=float('nan'),bpm=float('inf'),seed=-42,instruments={'drums':'syn:sub','lead':'sf:128:0'},mix={'lead':{'gain':999,'pan':-4}}))
  self.assertEqual(s['duration'],210);self.assertEqual(s['bpm'],124);self.assertEqual(s['seed'],0)
  self.assertEqual(s['instruments'],{});self.assertEqual(s['mix']['lead']['gain'],1.5)
  p=compose({'genre':'ambient','duration':20,'bpm':50})
  self.assertTrue(all(s['start']+s['duration']<=20.001 for s in p['sections']))
 def test_read_only_research(self):
  r=json.loads((Path(__file__).resolve().parents[1]/'research/analysis.json').read_text('utf-8'))
  self.assertGreaterEqual(len(r['tracks']),50)
  self.assertEqual(len({t['sha256'] for t in r['tracks']}),len(r['tracks']))
  for t in r['tracks']:
   self.assertEqual(len(t['tag_windows_seconds']),3)
   self.assertGreater(t['duration'],45)

if __name__=='__main__':unittest.main(verbosity=2)
