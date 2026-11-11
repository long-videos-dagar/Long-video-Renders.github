import sys, os, math, bpy
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
bpy.ops.wm.read_factory_settings(use_empty=True)
import toon as TO
from lib import box
from common import solid
out = sys.argv[sys.argv.index('--') + 1]
sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.samples = int(os.environ.get('S', 12)); sc.cycles.use_denoising = True
RW, RH = int(os.environ.get('RW', 1400)), int(os.environ.get('RH', 560)); sc.render.resolution_x, sc.render.resolution_y = RW, RH
box('ground', (60, 60, .02), (0, 0, -.01), solid('#c8ae88', .9))
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True; w.node_tree.nodes['Background'].inputs[0].default_value = (.55, .62, .75, 1); w.node_tree.nodes['Background'].inputs[1].default_value = .8
l = bpy.data.lights.new('s', 'SUN'); l.energy = 3.5; l.angle = .1; lo = bpy.data.objects.new('s', l); sc.collection.objects.link(lo); lo.rotation_euler = (math.radians(50), 0, math.radians(-35))
sc.view_settings.view_transform = 'AgX'
ps = [('JACK', TO.JACK), ('SHER', TO.SHERIFF)] + [(f'T{i}', TO.crowd_preset(i)) for i in [int(x) for x in os.environ.get('IDS', '0,1,2,3,4,5,6,9').split(',')]]
n = len(ps); A = []
for k, (cid, p) in enumerate(ps):
    print('ROLE', cid, p['name'])
    c = TO.Toon(cid, p)
    A.append(TO.ToonActor(c, [TO.Act(0, '77_02', 2.0 + k * .4, 8, loc=(-(n - 1) * .55 + k * 1.1, 0, 0), yaw=float(os.environ.get('YAW', 0)), lock_root=True)],
                          face=[(0, ['determined', 'smirk', 'idle', 'chat', 'watch'][min(k, 4)])]))
cam = bpy.data.cameras.new('c'); co = bpy.data.objects.new('c', cam); sc.collection.objects.link(co); sc.camera = co; cam.lens = float(os.environ.get('LENS', 50))
co.location = (0, -13.5, 1.5); co.rotation_euler = (math.radians(87), 0, 0)
for a in A: a.apply(1.0)
sc.render.filepath = out; bpy.ops.render.render(write_still=True); print('OK')
