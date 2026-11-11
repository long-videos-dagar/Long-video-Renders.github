"""python3 plan.py -> JSON job matrix from blender/pirate/film.json + job.json"""
import json, os
H = os.path.dirname(os.path.abspath(__file__))
film = json.load(open(os.path.join(H, 'film.json'))); job = json.load(open(os.path.join(H, 'job.json')))
only = job.get('only', ''); fps = film['fps']; out = []
for s in film['shots']:
    if only and s['id'] not in only.split(','): continue
    n = round(s['dur'] * fps)
    if job['mode'] == 'stills': out.append(dict(id=s['id'], shot=s['id'], a=0, b=0)); continue
    step = job.get('chunk', 15)
    for a in range(1, n + 1, step): out.append(dict(id=f"{s['id']}_{a:04d}", shot=s['id'], a=a, b=min(n, a + step - 1)))
print(json.dumps(out))
