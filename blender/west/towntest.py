import sys, os, math, bpy
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
bpy.ops.wm.read_factory_settings(use_empty=True)
import town as T
_a = sys.argv[sys.argv.index('--') + 1:]; out = next(x for x in _a if x.endswith('.png')); view = next((x for x in _a if x and not x.endswith('.png')), 'street')
sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.samples = int(os.environ.get('S', 16)); sc.cycles.use_denoising = True
sc.render.resolution_x, sc.render.resolution_y = int(os.environ.get('RW', 360)), int(os.environ.get('RH', 640))
T.build_town(); T.sky(os.environ.get('MOOD', 'sunset'), sun_elev=float(os.environ.get('ELEV', 12)), sun_az=float(os.environ.get('AZ', 200))); T.haze()
cam = bpy.data.cameras.new('c'); co = bpy.data.objects.new('c', cam); sc.collection.objects.link(co); sc.camera = co; cam.clip_end = 5000
V = {'street': ((1.5, -22, 1.7), (0, 15, 2.5), 24), 'edge': ((26, -34, 1.6), (6, 2, 3.0), 26), 'back': ((28, 4, 1.7), (S_ := 19, 10, 2.6), 30), 'field': ((-30, -40, 1.6), (-8, 5, 3.0), 26), 'bank': ((3.5, 4, 1.6), (-7, 13, 2.8), 22), 'aerial': ((25, -45, 30), (0, 10, 0), 22)}[view]
co.location = V[0]; co.rotation_euler = (Vector(V[1]) - Vector(V[0])).to_track_quat('-Z', 'Y').to_euler(); cam.lens = V[2]
sc.render.filepath = os.path.abspath(out); bpy.ops.render.render(write_still=True); print('RENDERED')
