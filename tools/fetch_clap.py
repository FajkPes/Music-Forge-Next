from fetch_assets import fetch,ROOT
import json,urllib.request

if __name__=='__main__':
 with urllib.request.urlopen('https://huggingface.co/api/models/laion/clap-htsat-unfused') as r:meta=json.load(r)
 revision=meta['sha'];available={s['rfilename'] for s in meta['siblings']}
 wanted=['config.json','preprocessor_config.json','tokenizer_config.json','tokenizer.json','special_tokens_map.json','vocab.json','merges.txt','README.md','model.safetensors']
 if 'model.safetensors' not in available:wanted[-1]='pytorch_model.bin'
 records=[]
 for name in wanted:
  if name in available:records.append(fetch(f'https://huggingface.co/laion/clap-htsat-unfused/resolve/{revision}/{name}','research/clap/'+name))
 (ROOT/'research/clap/sources.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
 print('CLAP assets ready',flush=True)
