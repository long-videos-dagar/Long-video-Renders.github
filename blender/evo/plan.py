"""python3 plan.py -> JSON job matrix (from job.json + shots.json)"""
import json, os
H = os.path.dirname(os.path.abspath(__file__))
job = json.load(open(os.path.join(H, 'job.json'))); film = json.load(open(os.path.join(H, 'shots.json'))); fps = film['fps']
mode = job.get('mode', 'tasks'); only = [s for s in job.get('only', '').split(',') if s]; out = []
if mode == 'idle':
    out = []                       # nothing to render
elif mode == 'tasks':
    out = job['tasks']
elif mode == 'compose':
    out = []
else:
    handle = job.get('handle', .25)
    for s in film['shots']:
        if only and s['id'] not in only: continue
        if s.get('render') is False: continue
        if mode == 'stills':
            for k, f in enumerate(job.get('at', [.5])):
                out.append(dict(id=f"{s['id']}_{k}", script='story.py', args=['still', s['id']], t=round(s['dur'] * f, 2), env={}))
        else:
            n = round((s['dur'] + handle) * fps)
            skip = set(json.load(open(os.path.join(H, job['skip_file'])))) if job.get('skip_file') else set()
            # heavy worlds (volumes) get short chunks so a job never hits the 6 h limit; a shot that already has finished
            # 24-frame chunks keeps that size so the pieces still tile exactly
            step = job.get('chunk', 12)
            if not any(k.startswith(s['id'] + '_') for k in skip): step = job.get('chunk_by_world', {}).get(s['world'], step)
            for a in range(1, n + 1, step):
                if f"{s['id']}_{a:04d}" in skip: continue
                out.append(dict(id=f"{s['id']}_{a:04d}", shot=s['id'], a=a, b=min(n, a + step - 1)))
print(json.dumps(out))
