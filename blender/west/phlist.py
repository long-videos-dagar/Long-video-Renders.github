"""dump Poly Haven asset index (ids, tags, categories) next to the output path"""
import sys, json, urllib.request
out = sys.argv[sys.argv.index('--') + 1]
res = {}
for t in ('textures', 'models', 'hdris'):
    req = urllib.request.Request(f'https://api.polyhaven.com/assets?t={t}', headers={'User-Agent': 'dagar-clips-render'})
    d = json.load(urllib.request.urlopen(req, timeout=60))
    res[t] = {k: dict(tags=v.get('tags', []), cats=v.get('categories', [])) for k, v in d.items()}
json.dump(res, open(out.replace('.png', '.json'), 'w'))
print('assets', {k: len(v) for k, v in res.items()})
