"""Small durable recipe library, stored atomically beside the local application."""
import hashlib,json,shutil,uuid
from datetime import datetime,timezone
from pathlib import Path
from composer import normalize_settings

class SeedLibrary:
    def __init__(self,path):self.path=Path(path)
    def read(self):
        if not self.path.exists():return {'version':1,'seeds':[]}
        data=json.loads(self.path.read_text('utf-8'))
        if data.get('version')!=1 or not isinstance(data.get('seeds'),list):raise ValueError('Knihovna seedů má neplatný formát. Původní soubor zůstal zachovaný.')
        return data
    def write(self,data):
        if self.path.exists():shutil.copy2(self.path,self.path.with_suffix('.backup.json'))
        temporary=self.path.with_suffix('.next.json');temporary.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8');temporary.replace(self.path)
    def save(self,settings,name):
        data=self.read();clean=normalize_settings(settings)
        digest=hashlib.sha256(json.dumps(clean,sort_keys=True).encode()).hexdigest()
        existing=next((s for s in data['seeds'] if s['fingerprint']==digest),None)
        if not existing:
            if len(data['seeds'])>=50:raise ValueError('Knihovna je plná (50/50). Nejdřív odstraň některou uloženou položku.')
            existing={'id':uuid.uuid4().hex,'settings':clean,'fingerprint':digest};data['seeds'].append(existing)
        existing.update(name=str(name or clean['title']).strip()[:100] or 'Uložený seed',saved_at=datetime.now(timezone.utc).isoformat())
        self.write(data);return existing
    def delete(self,identity):
        data=self.read();item=next((s for s in data['seeds'] if s['id']==identity),None)
        if not item:raise ValueError('Uložený seed neexistuje.')
        data['seeds'].remove(item);data['last_removed']=item;self.write(data)
    def undo(self):
        data=self.read();item=data.pop('last_removed',None)
        if not item:raise ValueError('Není co obnovit.')
        if len(data['seeds'])>=50:raise ValueError('Knihovna je plná.')
        data['seeds'].append(item);self.write(data)
