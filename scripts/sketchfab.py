"""Sketchfab helper (runs on CI; token from the SKETCHFAB_TOKEN secret, never printed).
  python scripts/sketchfab.py search queries.json out_dir   -> out_dir/candidates.json + thumbs + contact sheet
  python scripts/sketchfab.py download picks.json assets_dir -> downloads glTF/GLB, unzips, writes CREDITS lines
Only models whose license is CC Attribution or CC0 are kept (no NonCommercial / NoDerivs)."""
import json, os, sys, time, urllib.request, urllib.parse, zipfile, io, shutil
API = 'https://api.sketchfab.com/v3'
TOK = os.environ.get('SKETCHFAB_TOKEN', '')
OK_LIC = {'by', 'cc0'}


def get(url, auth=False, raw=False, tries=4):
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'dagar-clips-renders', **({'Authorization': f'Token {TOK}'} if auth and TOK else {})})
            d = urllib.request.urlopen(req, timeout=120).read()
            return d if raw else json.loads(d)
        except Exception as e:
            print('retry', url.split('?')[0], getattr(e, 'code', e), flush=True); time.sleep(3 + 4 * k)
    return None


def search(qfile, out):
    os.makedirs(out, exist_ok=True); Q = json.load(open(qfile)); res = {}
    for key, spec in Q.items():
        cands = []
        for q in spec['q']:
            p = dict(type='models', q=q, downloadable='true', sort_by='-likeCount', count=24)
            if spec.get('animated', True): p['animated'] = 'true'
            r = get(API + '/search?' + urllib.parse.urlencode(p))
            for m in (r or {}).get('results', []):
                if any(c['uid'] == m['uid'] for c in cands): continue
                cands.append(m)
        keep = []
        for m in cands[:30]:
            d = get(f"{API}/models/{m['uid']}") or {}
            lic = (d.get('license') or {}).get('slug', '')
            if lic not in OK_LIC: continue
            th = sorted((d.get('thumbnails') or {}).get('images', []), key=lambda i: abs(i.get('width', 0) - 512))
            keep.append(dict(uid=m['uid'], name=d.get('name'), author=(d.get('user') or {}).get('username'), license=lic, likes=d.get('likeCount'),
                             faces=d.get('faceCount'), anims=d.get('animationCount'), url=d.get('viewerUrl'), thumb=th[0]['url'] if th else None))
            if len(keep) >= spec.get('n', 8): break
        res[key] = keep; print(key, len(keep), flush=True)
        for j, k in enumerate(keep):
            if k['thumb']:
                b = get(k['thumb'], raw=True)
                if b: open(os.path.join(out, f'{key}_{j}.jpg'), 'wb').write(b)
    json.dump(res, open(os.path.join(out, 'candidates.json'), 'w'), indent=1)
    try:
        from PIL import Image, ImageDraw
        rows = [(k, v) for k, v in res.items()]; W = 220
        sheet = Image.new('RGB', (W * 8, (W + 40) * len(rows)), 'white'); dr = ImageDraw.Draw(sheet)
        for i, (k, v) in enumerate(rows):
            for j, m in enumerate(v[:8]):
                p = os.path.join(out, f'{k}_{j}.jpg')
                if os.path.exists(p):
                    im = Image.open(p).convert('RGB'); im.thumbnail((W, W)); sheet.paste(im, (j * W, i * (W + 40)))
                dr.text((j * W + 2, i * (W + 40) + W + 2), f"{k}_{j} {m['license']} a{m['anims']} f{(m['faces'] or 0) // 1000}k", fill='black')
                dr.text((j * W + 2, i * (W + 40) + W + 18), (m['name'] or '')[:32], fill='black')
        sheet.save(os.path.join(out, 'sheet.jpg'), quality=85)
    except Exception as e: print('sheet fail', e)


def download(pfile, adir):
    os.makedirs(adir, exist_ok=True); P = json.load(open(pfile)); cred = []
    for name, uid in P.items():
        d = get(f'{API}/models/{uid}/download', auth=True)
        if not d: print('NO DOWNLOAD', name, uid); continue
        info = get(f'{API}/models/{uid}') or {}
        lic = (info.get('license') or {}).get('slug', '')
        if lic not in OK_LIC: print('SKIP license', name, lic); continue
        if 'glb' in d: url = d['glb']['url']; b = get(url, raw=True); open(os.path.join(adir, name + '.glb'), 'wb').write(b)
        else:
            b = get(d['gltf']['url'], raw=True); z = zipfile.ZipFile(io.BytesIO(b)); tmp = f'/tmp/sf_{name}'; shutil.rmtree(tmp, ignore_errors=True); z.extractall(tmp)
            gl = [os.path.join(r, f) for r, _, fs in os.walk(tmp) for f in fs if f.endswith('.gltf')]
            if gl:                                             # pack the .gltf + textures into one .glb with Blender-free gltf-pipeline? keep folder instead
                dst = os.path.join(adir, name); shutil.rmtree(dst, ignore_errors=True); shutil.copytree(os.path.dirname(gl[0]), dst)
        cred.append(f"- {name}: \"{info.get('name')}\" ({info.get('viewerUrl')}) by {(info.get('user') or {}).get('displayName') or (info.get('user') or {}).get('username')}, "
                    f"{(info.get('license') or {}).get('label')}")
        print('OK', name, uid, flush=True)
    with open(os.path.join(adir, 'CREDITS.txt'), 'a') as f: f.write('\n'.join(cred) + '\n')


if __name__ == '__main__':
    {'search': search, 'download': download}[sys.argv[1]](*sys.argv[2:])
