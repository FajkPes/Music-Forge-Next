"""Additional acoustic multisamples. Only audio and upstream documentation are extracted."""
from fetch_assets import fetch,ROOT
import json,tarfile

def main():
    records=[]
    base='https://ftp.osuosl.org/pub/musescore/soundfont/MuseScore_General/'
    for name in ['MuseScore_General.sf2','MuseScore_General_License.md','MuseScore_General_Readme.md','MuseScore_General_Sample_Sources.csv']:
        records.append(fetch(base+name,'assets/musescore/'+name))
    # FreePats currently has an expired TLS certificate. Fetch only this non-executable
    # sample archive over the publisher's HTTP endpoint; preserve its hash/provenance.
    url='http://freepats.zenvoid.org/Piano/SalamanderGrandPiano/SalamanderGrandPiano-SF2-V3%2B20200602.tar.xz'
    records.append(fetch(url,'assets/salamander/source.tar.xz'))
    target=(ROOT/'assets/salamander').resolve()
    with tarfile.open(target/'source.tar.xz') as archive:
        for member in archive.getmembers():
            if member.isfile() and (member.name.lower().endswith(('.sf2','.txt','.md','.html'))):
                dest=target/Path(member.name).name
                with archive.extractfile(member) as src,dest.open('wb') as out:
                    import shutil
                    shutil.copyfileobj(src,out)
    manifest=json.loads((ROOT/'assets/sources.json').read_text('utf-8'))
    manifest=[r for r in manifest if r['file'] not in {v['file'] for v in records}]+records
    (ROOT/'assets/sources.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Additional acoustic banks ready',flush=True)

if __name__=='__main__':
    from pathlib import Path
    main()
