"""python3 zootest.py -- <kinds,comma> <view> out.png : creatures in a row on a jurassic ground, facing -Y (CI check)"""
import sys, os, math
H_ = os.path.dirname(os.path.abspath(__file__)); R_ = os.path.dirname(H_)
for d in (H_, os.path.join(R_, 'west'), os.path.join(R_, 'zombie'), os.path.join(R_, 'gta'), R_): sys.path.insert(0, d)
import bpy
from mathutils import Vector
import worlds as W, terra as TR, creatures as CR
a = sys.argv[sys.argv.index('--') + 1:]; kinds, view, out = a[0].split(','), int(a[1]), a[2]
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.samples = 24; sc.cycles.use_denoising = True; sc.render.fps = 24
sc.render.resolution_x = int(os.environ.get('RW', 1280)); sc.render.resolution_y = int(os.environ.get('RH', 720))
W.world_sky('day'); TR.sun_light(160, 40, 4.0, (1, .95, .85), 2)
g = bpy.data.meshes.new('g'); g.from_pydata([(-400, -400, 0), (400, -400, 0), (400, 400, 0), (-400, 400, 0)], [], [(0, 1, 2, 3)])
go = bpy.data.objects.new('ground', g); sc.collection.objects.link(go); go.data.materials.append(TR.simple_mat('gnd', ('ground',), '#7a7a60'))
class S: pass
sh = S(); sh.updates = []; sh.t0 = 0; sh.dur = 10
xs = []; x = 0.0; bs = []
for k in kinds:
    b = CR.beast(sh, k, k, clip=next(iter(CR.SPEC[k]['clips'] or {'x': None})) if CR.SPEC[k]['clips'] else None)
    w = max(b.size.x, .4); x += w / 2; b.root.location = (x, 0, 0); xs.append((k, x, b)); x += w / 2 + .3 * w + .3; bs.append(b)
    print('BEAST', k, [round(v, 2) for v in b.size], 'stride', round(CR.beast_stride(b, CR.clip_of(b, 'walk')), 2) if 'walk' in CR.SPEC[k]['clips'] else '-', flush=True)
    b.root.location = (x - w / 2 - .3 * w - .3, 0, 0)
t = float(os.environ.get('T', 1.0))
for u in sh.updates: u(t)
for k, x0, b in xs: b.root.location = (x0, 0, 0)
span = x; hmax = max(b.size.z for b in bs)
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam
d = max(span * .9, hmax * 2.2)
p = Vector((span / 2, -d, hmax * .7)) if view == 0 else Vector((span / 2 + d * .7, d * .6, hmax * .9))
cam.location = p; cam.rotation_euler = (Vector((span / 2, 0, hmax * .4)) - p).to_track_quat('-Z', 'Y').to_euler(); cam.data.lens = 35; cam.data.clip_end = 5000
sc.render.filepath = out; bpy.ops.render.render(write_still=True); print('RENDERED')
