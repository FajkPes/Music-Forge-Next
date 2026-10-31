"""Opt-in integration tests: RUN_HTTP_TESTS=1 python -m unittest discover -s tests."""
import os,sys,unittest,tempfile,threading,json,time,urllib.request,urllib.error,hashlib
from urllib.parse import quote,unquote
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

@unittest.skipUnless(os.environ.get('RUN_HTTP_TESTS')=='1','Local HTTP tests are opt-in')
class HttpTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  import server
  cls.app=server;cls.original_outputs=server.OUTPUTS
  cls.temp=tempfile.TemporaryDirectory(prefix='http-test-',dir=server.OUTPUTS)
  assert Path(cls.temp.name).resolve().is_relative_to(server.OUTPUTS.resolve())
  server.OUTPUTS=Path(cls.temp.name)
  cls.http=server.LocalHTTPServer(('127.0.0.1',0),server.Handler)
  cls.thread=threading.Thread(target=cls.http.serve_forever,daemon=True);cls.thread.start()
  cls.base='http://127.0.0.1:'+str(cls.http.server_port)
 @classmethod
 def tearDownClass(cls):
  cls.http.shutdown();cls.http.server_close();cls.thread.join();cls.app.OUTPUTS=cls.original_outputs;cls.temp.cleanup()
 def request(self,path,body=None,headers=None):
  req=urllib.request.Request(self.base+path,data=json.dumps(body).encode() if body is not None else None,headers=headers or {})
  try:r=urllib.request.urlopen(req,timeout=10)
  except urllib.error.HTTPError as e:r=e
  with r:return r.status,dict(r.headers),r.read()
 def wait_job(self,id):
  deadline=time.monotonic()+90
  while time.monotonic()<deadline:
   status,_,data=self.request('/api/status?job='+id);job=json.loads(data)
   if job['state']!='running':return job
   time.sleep(.2)
  self.fail('Render did not finish')
 def test_access_and_invalid_input(self):
  self.assertEqual(self.request('/api/health')[0],200)
  self.assertEqual(json.loads(self.request('/api/health')[2])['version'],'1.1')
  self.assertEqual(self.request('/api/catalogue',headers={'Origin':'https://untrusted.example'})[0],403)
  self.assertEqual(self.request('/api/health',headers={'Host':'untrusted.example'})[0],403)
  self.assertEqual(self.request('/%2e%2e/server.py')[0],400)
  self.assertEqual(self.request('/api/project?id=../../server.py')[0],400)
  self.assertEqual(self.request('/api/render',[])[0],400)
  self.assertEqual(self.request('/api/render',{'settings':[]})[0],400)
 def test_only_one_server_can_own_a_port(self):
  with self.assertRaises(OSError):
   extra=self.app.LocalHTTPServer(('127.0.0.1',self.http.server_port),self.app.Handler)
   extra.server_close()
 def test_generation_edit_ranges_and_cancel(self):
  status,_,data=self.request('/api/render',{'settings':{'duration':20,'genre':'melodic-house','seed':951,'title':'Zkouška exportu'}})
  self.assertEqual(status,202);job=json.loads(data)
  self.assertEqual(self.request('/api/render',{'settings':{}})[0],409)
  done=self.wait_job(job['job']);self.assertEqual(done['state'],'done',done)
  status,_,data=self.request('/api/project?id='+job['project']);self.assertEqual(status,200);p=json.loads(data)
  audio='/audio/'+job['project']+'/master.opus'
  status,headers,bytes_=self.request(audio,headers={'Range':'bytes=0-63'})
  self.assertEqual(status,206);self.assertEqual(len(bytes_),64);self.assertIn('OpusHead',bytes_.decode('latin1'))
  self.assertEqual(self.request(audio,headers={'Range':'bytes=999999999-'})[0],416)
  status,headers,_=self.request(audio+'?download=1');self.assertIn('filename*=',headers['Content-Disposition'])
  status,headers,_=self.request('/audio/'+job['project']+'/composition.mid?download=1&title='+quote('Přejmenovaný MIDI'))
  self.assertEqual(status,200);self.assertIn('Přejmenovaný MIDI (951).mid',unquote(headers['Content-Disposition']))
  status,headers,_=self.request('/audio/'+job['project']+'/composition.mid?download=1&title='+quote('Přejmenovaný MIDI'))
  self.assertEqual(status,200);self.assertIn('Přejmenovaný MIDI (951) v2.mid',unquote(headers['Content-Disposition']))
  status,headers,_=self.request('/audio/'+job['project']+'/composition.mid?download=1&title='+quote('Přejmenovaný MIDI'))
  self.assertEqual(status,200);self.assertIn('Přejmenovaný MIDI (951) v3.mid',unquote(headers['Content-Disposition']))
  s=p['plan']['settings'];s['instruments']={'lead':'syn:glass-pluck'}
  _,_,data=self.request('/api/render',{'settings':s,'project':job['project']});edited=json.loads(data)
  self.assertEqual(self.wait_job(edited['job'])['state'],'done')
  _,_,data=self.request('/api/project?id='+job['project']);q=json.loads(data)
  self.assertEqual(len(q['render']['reused_stems']),7)
  for a,b in zip(p['plan']['tracks'],q['plan']['tracks']):self.assertEqual(a['notes'],b['notes'])
  before=hashlib.sha256(self.request(audio)[2]).hexdigest()
  s['duration']=61
  _,_,data=self.request('/api/render',{'settings':s,'project':job['project']});cancelled=json.loads(data)
  self.request('/api/cancel',{})
  self.assertEqual(self.wait_job(cancelled['job'])['state'],'cancelled')
  after=hashlib.sha256(self.request(audio)[2]).hexdigest();self.assertEqual(before,after)
 def test_idempotency_and_immutable_results(self):
  import uuid
  request_id=uuid.uuid4().hex
  body={'request_id':request_id,'settings':{'duration':20,'seed':191}}
  _,_,a=self.request('/api/render',body);a=json.loads(a)
  _,_,b=self.request('/api/render',body);b=json.loads(b);self.assertEqual(a,b)
  self.assertEqual(self.wait_job(a['job'])['state'],'done')
  _,_,again=self.request('/api/render',body);self.assertEqual(json.loads(again),a)
  _,_,new=self.request('/api/render',{'settings':{'duration':20,'seed':192}});new=json.loads(new)
  self.assertNotEqual(new['project'],a['project']);self.assertEqual(self.wait_job(new['job'])['state'],'done')
  _,_,snapshot=self.request('/api/result?job='+a['job']);self.assertEqual(json.loads(snapshot)['plan']['settings']['seed'],191)
 def test_track_preview_and_exact_export(self):
  import numpy as np,struct,uuid,io,soundfile as sf
  _,_,data=self.request('/api/render',{'settings':{'duration':20,'seed':118}});job=json.loads(data);self.assertEqual(self.wait_job(job['job'])['state'],'done')
  project=job['project'];directory=self.app.OUTPUTS/project
  before=hashlib.sha256((directory/'project.json').read_bytes()).hexdigest()
  _,_,data=self.request('/api/track',{'project':project,'role':'lead','instrument':'syn:glass-pluck','tone':{'attack':.7,'release':.6}});track=json.loads(data)
  done=self.wait_job(track['id']);self.assertEqual(done['state'],'done',done)
  code,_,wave=self.request(done['url']);self.assertEqual(code,200);self.assertEqual(wave[:4],b'RIFF');self.assertEqual(len(wave),44+20*48000*8)
  self.assertEqual(hashlib.sha256((directory/'project.json').read_bytes()).hexdigest(),before)
  # A -> B -> A while queued must play A; reuse must not leave B current.
  from unittest.mock import patch
  import live_backend
  queued=[]
  class PendingPool:
   def submit(self,work):queued.append(work)
  with patch.object(live_backend,'POOL',PendingPool()):
   previews=[]
   for instrument in ['syn:arp','syn:silk-pluck','syn:arp']:
    _,_,data=self.request('/api/track',{'project':project,'role':'lead','instrument':instrument,'tone':{}});previews.append(json.loads(data))
   self.assertEqual(previews[0]['id'],previews[2]['id']);self.assertEqual(len(queued),2)
   for work in queued:work()
   self.assertEqual(self.wait_job(previews[0]['id'])['state'],'done')
   self.assertEqual(self.wait_job(previews[1]['id'])['state'],'cancelled')
  x=np.sin(np.arange(20*48000)*2*np.pi*440/48000).astype('float32')*.1;pcm=np.column_stack((x,x)).astype('<f4')
  curve=[[0,.2],[.5,1],[1,0]]
  meta=json.dumps({'settings':{'title':'Můj nový název','mix':{'lead':{'gain':1.2,'curve':curve}}}}).encode();payload=struct.pack('<I',len(meta))+meta+pcm.tobytes();eid=uuid.uuid4().hex
  request=urllib.request.Request(self.base+f'/api/export?project={project}&request_id={eid}',data=payload,headers={'Content-Type':'application/octet-stream'})
  with urllib.request.urlopen(request) as response:self.assertEqual(response.status,202)
  done=self.wait_job(eid);self.assertEqual(done['state'],'done',done)
  saved=json.loads((directory/'exports'/(eid+'.json')).read_text('utf-8'))
  lead=next(t for t in saved['plan']['tracks'] if t['id']=='lead')
  self.assertEqual(lead['gain'],1.2);self.assertEqual(lead['curve'],curve)
  code,headers,wav=self.request(f'/export/{project}/{eid}.wav');self.assertEqual(code,200)
  self.assertIn('Můj nový název (118).wav',unquote(headers['Content-Disposition']))
  decoded,rate=sf.read(io.BytesIO(wav),dtype='float32');self.assertEqual(rate,48000);self.assertEqual(decoded.shape,pcm.shape)
  self.assertLess(float(np.max(np.abs(decoded-pcm))),1.3e-7)
  eid2=uuid.uuid4().hex
  request2=urllib.request.Request(self.base+f'/api/export?project={project}&request_id={eid2}',data=payload,headers={'Content-Type':'application/octet-stream'})
  with urllib.request.urlopen(request2) as response:self.assertEqual(response.status,202)
  done2=self.wait_job(eid2);self.assertEqual(done2['state'],'done',done2)
  self.assertEqual(done2['export_version'],2)
  code2,headers2,_=self.request(f'/export/{project}/{eid2}.wav');self.assertEqual(code2,200)
  self.assertIn('Můj nový název (118) v2.wav',unquote(headers2['Content-Disposition']))
  eid3=uuid.uuid4().hex
  request3=urllib.request.Request(self.base+f'/api/export?project={project}&request_id={eid3}',data=payload,headers={'Content-Type':'application/octet-stream'})
  with urllib.request.urlopen(request3) as response:self.assertEqual(response.status,202)
  done3=self.wait_job(eid3);self.assertEqual(done3['state'],'done',done3)
  self.assertEqual(done3['export_version'],3)
  code3,headers3,_=self.request(f'/export/{project}/{eid3}.wav');self.assertEqual(code3,200)
  self.assertIn('Můj nový název (118) v3.wav',unquote(headers3['Content-Disposition']))

if __name__=='__main__':unittest.main(verbosity=2)
