"""Local-only HTTP application. No cloud account, uploads or runtime network calls."""
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse,parse_qs,unquote,quote
import urllib.request
import argparse, json, mimetypes, os, re, shutil, threading, time, traceback, uuid, webbrowser,struct,socket,unicodedata,secrets
import numpy as np
from catalogue import ROOT,catalogue
from composer import compose,midi_bytes
from audio_engine import render
from seed_library import SeedLibrary

OUTPUTS=ROOT/'outputs'
JOBS={};REQUESTS={};STATE_LOCK=threading.RLock();ACTIVE=None
CATALOGUE=catalogue()
CATALOGUE.update(session_id=uuid.uuid4().hex,startup_seed=secrets.randbelow(2147483648))
ID=re.compile(r'^[a-f0-9]{32}$')
SEEDS=SeedLibrary(ROOT/'saved-seeds.json')

def export_filename(title,extension,seed,version=1):
    clean=re.sub(r'[<>:"/\\|?*\x00-\x1f]','',unicodedata.normalize('NFC',str(title))).strip().rstrip('. ')[:100] or 'Nová skladba'
    if re.match(r'^(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)',clean,re.I):clean='_'+clean
    v=int(version or 1)
    suffix=f' v{v}' if v>1 else ''
    return f'{clean} ({int(seed)}){suffix}.{extension}'

class LocalHTTPServer(ThreadingHTTPServer):
    # Windows SO_REUSEADDR can bind two servers to one port. Exclusive binding
    # keeps browser requests on one process and one generation queue.
    allow_reuse_address=os.name!='nt'
    def server_bind(self):
        if os.name=='nt':self.socket.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1)
        super().server_bind()

class Cancelled(Exception):pass

def project_dir(project):
    if not isinstance(project,str) or not ID.fullmatch(project):raise ValueError('Neplatné ID projektu.')
    return OUTPUTS/project

def write_json(path,data):
    temporary=path.with_suffix('.next.json')
    temporary.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8');temporary.replace(path)

def trim_cache(current,required):
    candidates=[p for p in OUTPUTS.iterdir() if p.is_dir() and ID.fullmatch(p.name) and (p/'.generated').exists() and p.name!=current]
    sizes={p:sum(f.stat().st_size for f in p.rglob('*') if f.is_file()) for p in candidates}
    total=sum(sizes.values())+required
    for p in sorted(candidates,key=lambda x:(x/'.access').stat().st_mtime if (x/'.access').exists() else x.stat().st_mtime):
        if total<=2.2*1024**3:break
        # Only this application's marked render cache, always strictly inside OUTPUTS.
        if p.resolve().is_relative_to(OUTPUTS.resolve()):shutil.rmtree(p);total-=sizes[p]

def run_job(job_id,settings,project):
    global ACTIVE
    job=JOBS[job_id];directory=project_dir(project)
    try:
        def progress(value,message):
            if job.get('cancel') and not job.get('committing'):raise Cancelled()
            with STATE_LOCK:job.update(progress=value,message=message,committing=value>=.9)
        plan=compose(settings)
        trim_cache(project,plan['duration']*48000*8*8+plan['duration']*300000)
        directory.mkdir(parents=True,exist_ok=True);(directory/'.generated').touch()
        result=render(plan,directory,progress)
        snapshot=dict(plan=plan,render=result)
        write_json(directory/'project.json',snapshot)
        write_json(directory/('result-'+job_id+'.json'),snapshot)
        (directory/'composition.mid').write_bytes(midi_bytes(plan))
        sources=sorted({next(i['source'] for i in CATALOGUE['instruments'] if i['id']==t['instrument']) for t in plan['tracks'] if t['notes']})
        credits='Music Forge Next · procedural composition\n'+plan['title']+'\n\nSound sources:\n'+'\n'.join(sources)+'\n\nGeneralUser GS by S. Christian Collins: https://www.schristiancollins.com/generaluser.php\nSalamander Grand Piano by Alexander Holm; SF2 adaptation Roberto / FreePats. CC BY 3.0: https://creativecommons.org/licenses/by/3.0/\nhttps://freepats.zenvoid.org/Piano/acoustic-grand-piano.html\n\n'
        if any('MuseScore' in source for source in sources):credits+=(ROOT/'assets/musescore/MuseScore_General_License.md').read_text('utf-8')+'\n\n'
        credits+='See assets/ for complete original sound bank licenses. No source song audio is used in generated music.\n'
        (directory/'credits.txt').write_text(credits,encoding='utf-8')
        with STATE_LOCK:
            job.update(state='done',progress=1,message='Hotovo',project=project)
            if ACTIVE==job_id:ACTIVE=None
    except Cancelled:
        with STATE_LOCK:job.update(state='cancelled',message='Generování bylo zrušeno.')
    except Exception as error:
        traceback.print_exc()
        with STATE_LOCK:job.update(state='error',message=str(error))
    finally:
        with STATE_LOCK:
            if ACTIVE==job_id:ACTIVE=None

class Handler(BaseHTTPRequestHandler):
    protocol_version='HTTP/1.1'
    server_version='MusicForge/1.1'
    def log_message(self,*args):pass
    def handle(self):
        try:super().handle()
        except (ConnectionAbortedError,ConnectionResetError,BrokenPipeError):pass
    def common(self):
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('Cache-Control','no-store')
        self.send_header('Content-Security-Policy',"default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; img-src 'self' data:; media-src 'self' blob:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
    def json_response(self,value,status=200):
        data=json.dumps(value,ensure_ascii=False).encode('utf-8')
        self.send_response(status);self.common();self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(data)));self.end_headers()
        if self.command!='HEAD':self.wfile.write(data)
    def allowed(self):
        host=self.headers.get('Host','').split(':')[0].lower()
        if host not in ['127.0.0.1','localhost']:return False
        origin=self.headers.get('Origin')
        return not origin or origin in [f'http://127.0.0.1:{self.server.server_port}',f'http://localhost:{self.server.server_port}']
    def file(self,path,mime=None,download=None):
        if not path.is_file():self.json_response({'error':'Soubor neexistuje.'},404);return
        size=path.stat().st_size;start=0;end=size-1;status=200
        requested=self.headers.get('Range')
        if requested:
            match=re.fullmatch(r'bytes=(\d*)-(\d*)',requested)
            if not match or not any(match.groups()):self.json_response({'error':'Neplatný rozsah.'},416);return
            a,b=match.groups()
            if a:start=int(a);end=min(end,int(b)) if b else end
            else:start=max(0,size-int(b))
            if start>=size or end<start:
                self.send_response(416);self.send_header('Content-Range',f'bytes */{size}');self.send_header('Content-Length','0');self.end_headers();return
            status=206
        length=max(0,end-start+1)
        self.send_response(status);self.common();self.send_header('Content-Type',mime or mimetypes.guess_type(path.name)[0] or 'application/octet-stream')
        self.send_header('Accept-Ranges','bytes');self.send_header('Content-Length',str(length))
        if status==206:self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
        if download:
            fallback=unicodedata.normalize('NFKD',download).encode('ascii','ignore').decode().replace('"','').replace('\\','')
            self.send_header('Content-Disposition',f"attachment; filename=\"{fallback}\"; filename*=UTF-8''{quote(download,safe='')}")
        self.end_headers()
        if self.command!='HEAD':
            try:
                with path.open('rb') as source:
                    source.seek(start);remaining=length
                    while remaining:
                        block=source.read(min(256*1024,remaining))
                        if not block:break
                        self.wfile.write(block);remaining-=len(block)
            except (BrokenPipeError,ConnectionResetError):pass
    def do_HEAD(self):self.do_GET()
    def do_GET(self):
        if not self.allowed():self.json_response({'error':'Povolen je pouze místní přístup.'},403);return
        url=urlparse(self.path);path=url.path;query=parse_qs(url.query)
        try:
            if path=='/api/catalogue':self.json_response(CATALOGUE)
            elif path=='/api/health':self.json_response({'ok':True,'version':'1.1','instruments':len(CATALOGUE['instruments']),'genres':len(CATALOGUE['genres'])})
            elif path=='/api/status':
                with STATE_LOCK:job=JOBS.get(query.get('job',[''])[0])
                self.json_response(job or {'error':'Úloha neexistuje.'},200 if job else 404)
            elif path=='/api/state':
                with STATE_LOCK:active=dict(JOBS[ACTIVE]) if ACTIVE else None
                self.json_response(dict(active=active))
            elif path=='/api/seeds':
                with STATE_LOCK:data=SEEDS.read()
                self.json_response(dict(seeds=data['seeds'],capacity=50,can_undo=bool(data.get('last_removed'))))
            elif path=='/api/result':
                with STATE_LOCK:job=JOBS.get(query.get('job',[''])[0])
                if not job or job['state']!='done':self.json_response({'error':'Výsledek zatím není připravený.'},409);return
                if job.get('kind')=='export':self.file(project_dir(job['project'])/'exports'/(job['id']+'.json'),'application/json; charset=utf-8')
                else:self.file(project_dir(job['project'])/('result-'+job['id']+'.json'),'application/json; charset=utf-8')
            elif path=='/api/research':
                p=ROOT/'research/analysis.json';self.file(p,'application/json; charset=utf-8')
            elif path=='/api/project':
                directory=project_dir(query.get('id',[''])[0]);
                if directory.exists():(directory/'.access').touch()
                self.file(directory/'project.json','application/json; charset=utf-8')
            elif path.startswith('/stems/'):
                from live_backend import wav_header
                parts=path.strip('/').split('/')
                if len(parts)!=4:raise ValueError('Neplatná cesta stopy.')
                _,project,role,version=parts;directory=project_dir(project)
                if directory.exists():(directory/'.access').touch()
                if role not in ['drums','bass','chords','lead','counter','pad','arp','fx']:raise ValueError('Neplatná stopa.')
                digest=version.removesuffix('.wav')
                if digest=='base':target=directory/(role+'.npy')
                elif re.fullmatch('[a-f0-9]{64}',digest):target=directory/'live'/digest/(role+'.npy')
                else:raise ValueError('Neplatná verze stopy.')
                if not target.exists():self.json_response({'error':'Stopa není dostupná.'},404);return
                header,offset,size=wav_header(target)
                self.send_response(200);self.common();self.send_header('Content-Type','audio/wav');self.send_header('Content-Length',str(len(header)+size));self.end_headers()
                if self.command!='HEAD':
                    self.wfile.write(header)
                    with target.open('rb') as source:
                        source.seek(offset)
                        while chunk:=source.read(256*1024):self.wfile.write(chunk)
            elif path.startswith('/audio/'):
                parts=path.strip('/').split('/')
                if len(parts)!=3:raise ValueError('Neplatná cesta.')
                directory=project_dir(parts[1]);name=parts[2]
                names={'master.wav':('audio/wav','music-forge.wav'),'master.opus':('audio/ogg','music-forge.opus'),
                       'composition.mid':('audio/midi','music-forge.mid'),'credits.txt':('text/plain; charset=utf-8','music-forge-credits.txt')}
                if name not in names:raise ValueError('Soubor není přístupný.')
                mime,filename=names[name]
                if 'download' in query and (directory/'project.json').exists():
                    plan=json.loads((directory/'project.json').read_text('utf-8'))['plan']
                    custom_title=query.get('title',[''])[0].strip()
                    req_ver=query.get('version',[''])[0].strip()
                    if req_ver.isdigit():ver=int(req_ver)
                    else:
                        with STATE_LOCK:
                            dl_path=directory/f'.dl_{name}'
                            ver=(int(dl_path.read_text('utf-8')) if dl_path.exists() else 0)+1
                            dl_path.write_text(str(ver),encoding='utf-8')
                    filename=export_filename(custom_title or plan['title'],Path(name).suffix.lstrip('.'),plan['settings']['seed'],ver)
                self.file(directory/name,mime,filename if 'download' in query else None)
            elif path.startswith('/export/'):
                parts=path.strip('/').split('/')
                if len(parts)!=3:raise ValueError('Neplatná cesta exportu.')
                directory=project_dir(parts[1]);name=parts[2]
                if not re.fullmatch(r'[a-f0-9]{32}\.(wav|opus|mid|txt)',name):raise ValueError('Neplatný export.')
                metadata=json.loads((directory/'exports'/(Path(name).stem+'.json')).read_text('utf-8'))
                custom_title=query.get('title',[''])[0].strip()
                req_ver=query.get('version',[''])[0].strip()
                ver=int(req_ver) if req_ver.isdigit() else int(metadata.get('export_version',1))
                self.file(directory/'exports'/name,download=export_filename(custom_title or metadata['plan']['title'],Path(name).suffix.lstrip('.'),metadata['plan']['settings']['seed'],ver))
            else:
                relative=unquote(path.lstrip('/')) or 'index.html';root=(ROOT/'static').resolve();target=(root/relative).resolve()
                if not target.is_relative_to(root):raise ValueError('Neplatná cesta.')
                self.file(target)
        except (ValueError,KeyError) as e:self.json_response({'error':str(e)},400)
        except (ConnectionResetError,BrokenPipeError):pass
    def do_POST(self):
        global ACTIVE
        if not self.allowed():self.json_response({'error':'Povolen je pouze místní přístup.'},403);return
        try:
            if self.path.startswith('/api/export?'):
                self.upload_export();return
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<=2*1024**2:raise ValueError('Neplatná velikost požadavku.')
            data=json.loads(self.rfile.read(size))
            if not isinstance(data,dict):raise ValueError('Očekáván objekt JSON.')
            if self.path in ['/api/seeds','/api/seeds/delete','/api/seeds/undo']:
                with STATE_LOCK:
                    if self.path=='/api/seeds':
                        if not isinstance(data.get('settings'),dict):raise ValueError('Chybí nastavení seedu.')
                        SEEDS.save(data['settings'],data.get('name',''))
                    elif self.path.endswith('/delete'):SEEDS.delete(data.get('id'))
                    else:SEEDS.undo()
                    saved=SEEDS.read()
                self.json_response(dict(seeds=saved['seeds'],capacity=50,can_undo=bool(saved.get('last_removed'))));return
            if self.path=='/api/render':
                settings=data.get('settings',{})
                if not isinstance(settings,dict):raise ValueError('Neplatné nastavení.')
                # Validate before accepting a background job.
                from composer import normalize_settings
                settings=normalize_settings(settings)
                with STATE_LOCK:
                    request_id=data.get('request_id') or uuid.uuid4().hex
                    if not isinstance(request_id,str) or not ID.fullmatch(request_id):raise ValueError('Neplatné ID požadavku.')
                    if request_id in REQUESTS:
                        old=JOBS[REQUESTS[request_id]];self.json_response({'job':old['id'],'project':old['project']},202);return
                    if ACTIVE:self.json_response({'error':'Právě se generuje skladba. Počkejte nebo ji zrušte.'},409);return
                    project=data.get('project') or uuid.uuid4().hex
                    project_dir(project)
                    job_id=uuid.uuid4().hex;ACTIVE=job_id
                    JOBS[job_id]=dict(id=job_id,state='running',kind='composition',request_id=request_id,progress=0,message='Skládám…',project=project)
                    REQUESTS[request_id]=job_id
                    while len(REQUESTS)>100:
                        oldest=next(iter(REQUESTS));REQUESTS.pop(oldest)
                threading.Thread(target=run_job,args=(job_id,settings,project),daemon=True).start()
                self.json_response({'job':job_id,'project':project},202)
            elif self.path=='/api/track':
                from live_backend import request_track
                directory=project_dir(data.get('project',''))
                result=request_track(directory,data.get('role'),data.get('instrument'),data.get('tone',{}),JOBS,STATE_LOCK)
                self.json_response(dict(result),202)
            elif self.path=='/api/cancel':
                with STATE_LOCK:
                    if ACTIVE and data.get('job') not in [None,ACTIVE]:raise ValueError('Úloha už není aktuální.')
                    if ACTIVE and not JOBS[ACTIVE].get('committing'):JOBS[ACTIVE]['cancel']=True
                self.json_response({'ok':True})
            else:self.json_response({'error':'Neznámá akce.'},404)
        except (ValueError,TypeError,KeyError,json.JSONDecodeError) as error:self.json_response({'error':str(error)},400)

    def upload_export(self):
        global ACTIVE
        from live_backend import export_mix
        query=parse_qs(urlparse(self.path).query);project=query.get('project',[''])[0];directory=project_dir(project)
        jobid=query.get('request_id',[''])[0]
        if not ID.fullmatch(jobid):raise ValueError('Neplatné ID exportu.')
        total=int(self.headers.get('Content-Length','0'))
        if total<8 or total>600*48000*8+65540:raise ValueError('Neplatná velikost exportu.')
        with STATE_LOCK:
            if ACTIVE or jobid in JOBS:
                self.close_connection=True;self.json_response({'error':'Jiná úloha už běží.'},409);return
            ACTIVE=jobid;JOBS[jobid]=dict(id=jobid,kind='export',project=project,state='running',progress=0,message='Přijímám živý mix…',committing=True)
        raw=directory/('export-'+jobid+'.f32')
        try:
            length=struct.unpack('<I',self.rfile.read(4))[0]
            if not 0<length<=65536:raise ValueError('Neplatná metadata exportu.')
            metadata=json.loads(self.rfile.read(length));remaining=total-length-4
            base=json.loads((directory/'project.json').read_text('utf-8'))
            if remaining!=round(base['plan']['duration']*48000)*8:raise ValueError('Nesouhlasí délka exportu.')
            with raw.open('wb') as out:
                while remaining:
                    chunk=self.rfile.read(min(1024*1024,remaining))
                    if not chunk:raise ValueError('Přenos mixu byl přerušen.')
                    out.write(chunk);remaining-=len(chunk)
            samples=np.memmap(raw,mode='r',dtype='<f4')
            valid=np.isfinite(samples).all() and float(np.max(np.abs(samples)))<=2;del samples
            if not valid:raise ValueError('Mix obsahuje neplatné nebo přebuzené vzorky.')
        except Exception:
            raw.unlink(missing_ok=True)
            with STATE_LOCK:
                JOBS[jobid].update(state='error',message='Přenos exportu selhal.')
                if ACTIVE==jobid:ACTIVE=None
            raise
        def work():
            global ACTIVE
            try:
                def progress(value,message):
                    with STATE_LOCK:JOBS[jobid].update(progress=value,message=message)
                res=export_mix(raw,metadata,directory,jobid,progress)
                with STATE_LOCK:JOBS[jobid].update(state='done',progress=1,export_version=res['export_version'])
            except Exception as error:
                with STATE_LOCK:JOBS[jobid].update(state='error',message=str(error))
            finally:
                try:raw.unlink(missing_ok=True)
                except OSError:pass
                with STATE_LOCK:
                    if ACTIVE==jobid:ACTIVE=None
        threading.Thread(target=work,daemon=True).start();self.json_response({'job':jobid,'project':project},202)

def main():
    global SEEDS
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8877);parser.add_argument('--open',action='store_true');parser.add_argument('--seed-library',type=Path,default=ROOT/'saved-seeds.json');args=parser.parse_args()
    SEEDS=SeedLibrary(args.seed_library)
    OUTPUTS.mkdir(exist_ok=True)
    if not SEEDS.path.exists():SEEDS.write({'version':1,'seeds':[]})
    try:server=LocalHTTPServer(('127.0.0.1',args.port),Handler)
    except OSError:
        try:
            with urllib.request.urlopen(f'http://127.0.0.1:{args.port}/api/health',timeout=2) as response:existing=json.load(response)
            if existing.get('ok') and existing.get('genres'):
                if args.open:webbrowser.open(f'http://localhost:{args.port}/')
                print('Music Forge už běží.',flush=True);return
        except Exception:pass
        print(f'Port {args.port} je obsazený. Pokud Music Forge již běží, otevřete http://127.0.0.1:{args.port}/. Jinak použijte --port 8878.',flush=True);raise SystemExit(1)
    print(f'Music Forge Next · http://127.0.0.1:{args.port}/',flush=True)
    if args.open:webbrowser.open(f'http://localhost:{args.port}/')
    try:server.serve_forever(poll_interval=.3)
    except KeyboardInterrupt:pass
    finally:server.server_close()

if __name__=='__main__':main()
