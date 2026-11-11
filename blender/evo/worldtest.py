"""python3 worldtest.py -- <world> <view> out.png   (CI/local set check, no actors)"""
import sys, os, math, time
H_ = os.path.dirname(os.path.abspath(__file__)); R_ = os.path.dirname(H_)
for d in (H_, os.path.join(R_, 'west'), os.path.join(R_, 'zombie'), os.path.join(R_, 'gta'), R_): sys.path.insert(0, d)
import bpy
from mathutils import Vector
import worlds as W, terra as TR
a = sys.argv[sys.argv.index('--') + 1:]; wname, view, out = a[0], int(a[1]), a[2]
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.samples = int(os.environ.get('SAMPLES', 32)); sc.cycles.use_denoising = True
sc.render.resolution_x = int(os.environ.get('RW', 1920)); sc.render.resolution_y = int(os.environ.get('RH', 1080))
sc.cycles.max_bounces = 6; sc.cycles.volume_bounces = 1; sc.cycles.volume_step_rate = 4.0 if os.environ.get('FASTVOL') else 1.0
t0 = time.time(); w = getattr(W, wname)(); import resource; print('BUILT', round(time.time() - t0, 1), 'MAXRSS', resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1024, 'MB', flush=True)
VIEWS = {'cave': [((0, -2, 1.6), (0, 18, 2.2), 22)], 'space': [((0, -22, 3), (0, 0, 0), 35)], 'coast': [((0, -20, 4), (0, 60, 2), 24)], 'impact': [((0, -10, 5), (0, 80, 30), 24)], 'livingroom': [((-.6, 1.0, 1.4), (-.6, 3.8, .8), 20)], 'city': [((0, -10, 2), (0, 60, 6), 24)], 'jurassic': [((0, -10, 6), (0, 80, 6), 24), ((-60, -40, 60), (0, 120, 0), 20), ((10, 30, 6), (40, 90, 8), 22)], 'cambrian': [((0, -5, -14), (0, 40, -16), 20), ((5, 20, -16.5), (0, 40, -17), 28)], 'microbes': [((0, -2, 0), (0, 8, 0), 35)], 'savanna': [((0, -10, 3), (0, 80, 4), 24)], 'cretaceous': [((0, -10, 5), (0, 80, 6), 24)], 'permian': [((0, -10, 5), (0, 80, 6), 24)], 'shallows': [((0, -5, -14), (0, 40, -16), 20)], 'ediacaran': [((0, 0, -16), (0, 30, -17.5), 26)], 'classroom': [((0, -3.7, 1.7), (0, 4.0, 1.4), 20), ((-3.5, 3.2, 2.2), (1.0, -2.0, .8), 18), ((0, 1.0, 1.55), (0, 4.5, 1.75), 30)], 'young_earth': [((0, -20, 30), (0, 260, 40), 24), ((-40, 60, 8), (10, 200, 20), 18), ((60, 150, 120), (-60, 330, 30), 20), ((-150, 80, 6), (-300, 260, 5), 22)]}
VIEWS.update({'jurassic_dn': None, 'triassic': [((0, -10, 4), (0, 80, 5), 24)], 'paleogene': [((0, -10, 4), (0, 80, 5), 24)], 'devonian_sea': [((0, -5, -14), (0, 40, -16), 20)],
              'coast_cretaceous': [((0, -20, 4), (0, 60, 2), 24)]})
if view == 9:
    fx, fy = (w['focus'].x, w['focus'].y) if isinstance(w, dict) and 'focus' in w else (0, 60); VIEWS[wname] = VIEWS.get(wname, []) + [None] * 10
    VIEWS[wname][9] = ((fx + 1, fy - 3, 3), (fx, fy, 0), 30)
p, tg, lens = VIEWS[wname][view]
ter = w.get('ter') if isinstance(w, dict) else None
if ter is not None and p[2] > -5:
    try:
        g = ter.z(p[0], p[1]); p = (p[0], p[1], max(p[2], g + 1.7)); print('CAMZ ground', round(g, 2), '->', round(p[2], 2))
    except Exception as e: print('camz fail', e)
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam; cam.data.clip_end = 20000
cam.location = p; cam.rotation_euler = (Vector(tg) - Vector(p)).to_track_quat('-Z', 'Y').to_euler(); cam.data.lens = lens
if os.environ.get('MATDBG'):
    for o in bpy.data.objects:
        if o.name.startswith('ground') and o.type == 'MESH':
            for m in o.data.materials:
                print('MAT', o.name, m.name, [(n.image.name, tuple(n.image.size), n.image.colorspace_settings.name, n.image.filepath[-50:]) for n in m.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image])
            break
tick = getattr(W, wname + '_tick', None)
if tick: tick(w, float(os.environ.get("T", 12.0)))
sc.render.filepath = out; t0 = time.time(); bpy.ops.render.render(write_still=True); import resource; print('RENDERED', wname, view, round(time.time() - t0, 1), 'MAXRSS', resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1024, 'MB')
