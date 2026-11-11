"""python3 runp.py -- still <shot> <out.png> [frame] | frames <shot> <from> <to> <outdir>   (RW,RH,SAMPLES env; NOINK=1)"""
import sys, os, time, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'dagar')); sys.path.insert(0, HERE)
import bpy
import lib
from common import ink_setup
a = sys.argv[sys.argv.index('--') + 1:]; mode, shot = a[0], a[1]
cfg = json.load(open(os.path.join(HERE, 'film.json'))); row = next(r for r in cfg['shots'] if r['id'] == shot); fps = cfg['fps']; n = round(row['dur'] * fps)
W, H = int(os.environ.get('RW', cfg['w'])), int(os.environ.get('RH', cfg['h']))
lib.reset(); sc = lib.setup(W, H, int(os.environ.get('SAMPLES', cfg['samples']))); lib.DRAFT = False
sc.render.fps = fps
sc.cycles.max_bounces = 6; sc.cycles.diffuse_bounces = 3; sc.cycles.glossy_bounces = 2; sc.cycles.transmission_bounces = 6; sc.cycles.volume_bounces = 1
sc.cycles.use_adaptive_sampling = True; sc.cycles.adaptive_threshold = .02
import shots
t = time.time(); shots.SHOTS[shot](n, row['t0']); lib.log('built', shot, n, 'frames', f'{time.time() - t:.0f}s', len(bpy.data.objects), 'objects')
ik = row.get('ink', [7.0, 3.2])
if not os.environ.get('NOINK'): ink_setup(W, float(os.environ.get('OUTLINE', 1.0)), ik[0], ik[1])
if mode == 'still':
    f = int(a[3]) if len(a) > 3 else max(1, n // 2); sc.frame_set(f); sc.frame_set(f); lib.render(os.path.abspath(a[2]))
else:
    f0, f1, out = int(a[2]), int(a[3]), os.path.abspath(a[4]); os.makedirs(out, exist_ok=True); g0 = round(row['t0'] * fps)
    sc.render.image_settings.file_format = 'PNG'
    for f in range(f0, f1 + 1):
        t = time.time(); sc.frame_set(f); sc.render.filepath = os.path.join(out, f'f_{g0 + f:05d}.png'); bpy.ops.render.render(write_still=True); lib.log('frame', g0 + f, f'{time.time() - t:.1f}s')
