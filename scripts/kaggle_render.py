"""GPU render worker for Kaggle (or any NVIDIA machine).

    python scripts/kaggle_render.py <gpu_index> <n_gpus>

Renders the shots listed in blender/evo/kaggle_job.json with exactly the same scene code and the same final settings
as the GitHub runners (only the device differs), encodes each chunk the same way, and uploads it as an asset of the
GitHub release 'evo-kaggle' so the join job picks it up.  Chunks already uploaded are skipped, so the notebook can be
re-run after a session ends and it simply continues.  Needs env GH_TOKEN (fine-grained, Contents: read & write)."""
import json, os, sys, subprocess, time, urllib.request, urllib.error, glob, shutil

REPO = os.environ.get('KAGGLE_REPO', 'chintudagar541-stack/wanderly'); TAG = 'evo-kaggle'
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); EVO = os.path.join(ROOT, 'blender', 'evo')
TOKEN = os.environ['GH_TOKEN']; GPU, NG = int(sys.argv[1]), int(sys.argv[2])
PY = os.environ.get('BPY_PYTHON', sys.executable)


def api(url, data=None, method=None, ctype='application/json', tries=5):
    for k in range(tries):
        try:
            req = urllib.request.Request(url, data=data, method=method, headers={'Authorization': f'Bearer {TOKEN}', 'Accept': 'application/vnd.github+json',
                                                                                 'Content-Type': ctype, 'User-Agent': 'evo-kaggle'})
            with urllib.request.urlopen(req, timeout=600) as r: return json.loads(r.read() or b'{}')
        except urllib.error.HTTPError as e:
            if e.code in (404, 422): raise
            time.sleep(5 * (k + 1))
        except Exception:
            time.sleep(5 * (k + 1))
    raise RuntimeError('api failed ' + url)


def release():
    try: return api(f'https://api.github.com/repos/{REPO}/releases/tags/{TAG}')
    except urllib.error.HTTPError:
        try:
            return api(f'https://api.github.com/repos/{REPO}/releases', json.dumps(dict(tag_name=TAG, target_commitish='claude/long-video', name='evo kaggle chunks',
                       body='GPU-rendered chunks for the evolution video (collected by the join job).', prerelease=True)).encode(), 'POST')
        except urllib.error.HTTPError:
            time.sleep(10); return api(f'https://api.github.com/repos/{REPO}/releases/tags/{TAG}')     # the other GPU created it


def uploaded(rel):
    names, page = set(), 1
    while True:
        a = api(f"https://api.github.com/repos/{REPO}/releases/{rel['id']}/assets?per_page=100&page={page}")
        names |= {x['name'] for x in a}
        if len(a) < 100: return names
        page += 1


def upload(rel, path):
    name = os.path.basename(path)
    api(f"https://uploads.github.com/repos/{REPO}/releases/{rel['id']}/assets?name={name}", open(path, 'rb').read(), 'POST', 'video/mp4')


job = json.load(open(os.path.join(EVO, 'kaggle_job.json'))); film = json.load(open(os.path.join(EVO, 'shots.json')))
fps = film['fps']; S = {s['id']: s for s in film['shots']}; step = job.get('chunk', 24); handle = job.get('handle', .25)
env = dict(os.environ, **{k: str(v) for k, v in job['env'].items()}, GPU='1', CUDA_VISIBLE_DEVICES=str(GPU), USE_PH='1')
done_gh = set(json.load(open(os.path.join(EVO, 'done_chunks.json')))) if os.path.exists(os.path.join(EVO, 'done_chunks.json')) else set()
chunks = []
for sid in job['shots']:                         # same chunking as the GitHub plan, so names (and frames) match exactly
    n = round((S[sid]['dur'] + handle) * fps); st = step
    if not any(k.startswith(sid + '_') for k in done_gh): st = job.get('chunk_by_world', {}).get(S[sid]['world'], step)
    chunks += [(sid, a, min(n, a + st - 1)) for a in range(1, n + 1, st) if f'{sid}_{a:04d}' not in done_gh]
chunks.reverse()                                 # GitHub renders from the start of the list, the GPU from the end
mine = [c for k, c in enumerate(chunks) if k % NG == GPU]
rel = release(); done = uploaded(rel)
print(f'GPU {GPU}: {len(mine)} chunks, {sum(1 for c in mine if f"chunk_{c[0]}_{c[1]:04d}.mp4" in done)} already uploaded', flush=True)
work = f'/tmp/evo_out{GPU}'
for sid, a, b in mine:
    name = f'chunk_{sid}_{a:04d}.mp4'
    if name in done: continue
    t0 = time.time(); fr = os.path.join(work, 'frames'); shutil.rmtree(fr, ignore_errors=True); os.makedirs(fr, exist_ok=True)
    r = subprocess.run([PY, 'story.py', '--', 'frames', sid, str(a), str(b), fr], cwd=EVO, env=env, capture_output=True, text=True)
    pngs = sorted(glob.glob(os.path.join(fr, 'f_*.png')))
    if len(pngs) != b - a + 1:
        print('FAILED', name, len(pngs), r.stdout[-1500:], r.stderr[-1500:], flush=True); continue
    s0 = int(os.path.basename(pngs[0])[2:7]); out = os.path.join(work, name)
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-framerate', str(fps), '-start_number', str(s0), '-i', os.path.join(fr, 'f_%05d.png'),
                    '-c:v', 'libx264', '-preset', 'slow', '-crf', '14', '-pix_fmt', 'yuv420p', out], check=True)
    upload(rel, out); os.remove(out)
    print(f'GPU {GPU} {name} {b - a + 1} frames {time.time() - t0:.0f}s ({(time.time() - t0) / (b - a + 1):.1f} s/frame)', flush=True)
print(f'GPU {GPU} finished', flush=True)
