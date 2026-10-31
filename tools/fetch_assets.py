"""Download pinned upstream assets into this checkout, never into system directories."""
from pathlib import Path
import hashlib, json, urllib.request, zipfile

ROOT = Path(__file__).resolve().parents[1]
REV = '684543d5e5efaef08d02be50dcda8d552478fa60'

def fetch(url, dest):
    dest = ROOT / dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        tmp = dest.with_suffix(dest.suffix + '.part')
        print('Downloading', dest.name, flush=True)
        with urllib.request.urlopen(url, timeout=120) as src, tmp.open('wb') as out:
            while block := src.read(1024 * 1024):
                out.write(block)
        tmp.replace(dest)
    return {'file':str(dest.relative_to(ROOT)), 'url':url, 'bytes':dest.stat().st_size,
            'sha256':hashlib.file_digest(dest.open('rb'), 'sha256').hexdigest()}

def main():
    manifest = []
    base = f'https://raw.githubusercontent.com/mrbumpy409/GeneralUser-GS/{REV}/'
    manifest.append(fetch(base + 'GeneralUser-GS.sf2', 'assets/GeneralUser-GS.sf2'))
    for name in ['LICENSE.txt', 'README.md', 'CHANGELOG.md']:
        manifest.append(fetch(base + 'documentation/' + name, 'assets/generaluser/' + name))
    manifest.append(fetch('https://github.com/FluidSynth/fluidsynth/releases/download/v2.6.1/fluidsynth-v2.6.1-win10-x64-cpp11.zip', 'runtime/fluidsynth.zip'))
    with zipfile.ZipFile(ROOT / 'runtime/fluidsynth.zip') as archive:
        target = (ROOT / 'runtime/fluidsynth').resolve()
        for member in archive.infolist():
            if not (target / member.filename).resolve().is_relative_to(target):
                raise ValueError('Unsafe archive entry')
        archive.extractall(target)
    model_base = 'https://huggingface.co/MIT/ast-finetuned-audioset-10-10-0.4593/resolve/f826b80d28226a62986cc218e5cec390b1096902/'
    # Resolve the model revision once, save it alongside the exact downloaded hashes.
    with urllib.request.urlopen('https://huggingface.co/api/models/MIT/ast-finetuned-audioset-10-10-0.4593') as r:
        revision = json.load(r)['sha']
    model_base = f'https://huggingface.co/MIT/ast-finetuned-audioset-10-10-0.4593/resolve/{revision}/'
    for name in ['config.json', 'preprocessor_config.json', 'model.safetensors', 'README.md']:
        manifest.append(fetch(model_base + name, 'research/model/' + name))
    (ROOT / 'assets/sources.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Assets ready', sum(x['bytes'] for x in manifest), flush=True)

if __name__ == '__main__':
    main()
