import sys, os, math, bpy
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import realchar as R, mocap as M
a = sys.argv[sys.argv.index('--') + 1:]; out = a[0]; ids = [int(x) for x in a[1].split(',')]
bpy.ops.wm.read_factory_settings(use_empty=True); R.init()
sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.samples = int(os.environ.get('S', 16)); sc.cycles.use_denoising = True
sc.render.resolution_x, sc.render.resolution_y = int(os.environ.get('RW', 1200)), int(os.environ.get('RH', 600))
sc.view_settings.view_transform = 'AgX'
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True; w.node_tree.nodes['Background'].inputs[0].default_value = (.6, .65, .75, 1); w.node_tree.nodes['Background'].inputs[1].default_value = .5
l = bpy.data.lights.new('s', 'SUN'); l.energy = 4; l.color = (1, .9, .78); o = bpy.data.objects.new('s', l); sc.collection.objects.link(o); o.rotation_euler = (.9, 0, -.5)
bpy.ops.mesh.primitive_plane_add(size=60); bpy.context.active_object.data.materials.append(R.cloth_mat('g', '#a08060', rough=.95, weave=30, wear=.5))
src = M.BVH.load('40_10')
for k, i in enumerate(ids):
    p = R.Person(f'P{i}', R.crowd_preset(i)); x = (k - (len(ids) - 1) / 2) * .85
    rt = M.Retarget(p.rig); rots, hips = rt.pose(src, 2.0 + k * 1.3, place=(x, 0, 0), yaw=0, t0=2.0 + k * 1.3); rt.apply(rots, hips); M.relax_fingers(p.rig)
    p.set_expression({['smile', 'neutral', 'worry', 'suspicious', 'smirk', 'angry'][k % 6]: .8})
cam = bpy.data.cameras.new('c'); co = bpy.data.objects.new('c', cam); sc.collection.objects.link(co); sc.camera = co
co.location = (0, -7.5, 1.1); co.rotation_euler = (Vector((0, 0, .95)) - co.location).to_track_quat('-Z', 'Y').to_euler(); cam.lens = 38
sc.render.filepath = os.path.abspath(out); bpy.ops.render.render(write_still=True); print('RENDERED')
