"""python3 worldtest.py -- <world> <view> out.png   (CI/local set check, no actors)"""
import sys, os, math, time
H_ = os.path.dirname(os.path.abspath(__file__)); R_ = os.path.dirname(H_)
for d in (H_, os.path.join(R_, 'west'), os.path.join(R_, 'zombie'), R_): sys.path.insert(0, d)
import bpy
from mathutils import Vector
import worlds as W, terra as TR
a = sys.argv[sys.argv.index('--') + 1:]; wname, view, out = a[0], int(a[1]), a[2]
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.samples = int(os.environ.get('SAMPLES', 32)); sc.cycles.use_denoising = True
sc.render.resolution_x = int(os.environ.get('RW', 1920)); sc.render.resolution_y = int(os.environ.get('RH', 1080))
sc.cycles.max_bounces = 6; sc.cycles.volume_bounces = 1; sc.cycles.volume_step_rate = 4.0 if os.environ.get('FASTVOL') else 1.0
t0 = time.time(); w = getattr(W, wname)(); print('BUILT', round(time.time() - t0, 1), flush=True)
VIEWS = {'young_earth': [((0, -20, 30), (0, 260, 40), 24), ((-40, 60, 8), (10, 200, 20), 18), ((60, 150, 120), (-60, 330, 30), 20), ((-150, 80, 6), (-300, 260, 5), 22)]}
p, tg, lens = VIEWS[wname][view]
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam; cam.data.clip_end = 20000
cam.location = p; cam.rotation_euler = (Vector(tg) - Vector(p)).to_track_quat('-Z', 'Y').to_euler(); cam.data.lens = lens
tick = getattr(W, wname + '_tick', None)
if tick: tick(w, float(os.environ.get("T", 12.0)))
sc.render.filepath = out; t0 = time.time(); bpy.ops.render.render(write_still=True); print('RENDERED', wname, view, round(time.time() - t0, 1))
