"""python3 plan.py -> JSON job matrix (from job.json + shots.json)"""
import json, os
H = os.path.dirname(os.path.abspath(__file__))
job = json.load(open(os.path.join(H, 'job.json'))); film = json.load(open(os.path.join(H, 'shots.json'))); fps = film['fps']
mode = job.get('mode', 'tasks'); only = [s for s in job.get('only', '').split(',') if s]; out = []
if mode == 'tasks':
    out = job['tasks']
elif mode == 'compose':
    out = []
else:
    handle = job.get('handle', .25)
    for s in film['shots']:
        if only and s['id'] not in only: continue
        if mode == 'stills':
            for k, f in enumerate(job.get('at', [.5])):
                out.append(dict(id=f"{s['id']}_{k}", script='film.py', args=['still', s['id']], t=round(s['dur'] * f, 2), env={}))
        else:
            n = round((s['dur'] + handle) * fps); step = job.get('chunk', 12)
            skip = set(json.load(open(os.path.join(H, job['skip_file'])))) if job.get('skip_file') else set()
            for a in range(1, n + 1, step):
                if f"{s['id']}_{a:04d}" in skip: continue
                out.append(dict(id=f"{s['id']}_{a:04d}", shot=s['id'], a=a, b=min(n, a + step - 1)))
print(json.dumps(out))
