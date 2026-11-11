import sys, os, math, bpy
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import realchar as R, mocap as M
a = sys.argv[sys.argv.index('--') + 1:]; clip, out = a[0], a[1]; times = [float(x) for x in a[2].split(',')]
bpy.ops.wm.read_factory_settings(use_empty=True); R.init()
sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.samples = 8; sc.cycles.use_denoising = True
sc.render.resolution_x, sc.render.resolution_y = 300, 400
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True; w.node_tree.nodes['Background'].inputs[1].default_value = 1.0
l = bpy.data.lights.new('s', 'SUN'); l.energy = 3; o = bpy.data.objects.new('s', l); sc.collection.objects.link(o); o.rotation_euler = (.8, 0, .6)
bpy.ops.mesh.primitive_plane_add(size=60)
p = R.Person('J', R.JACK); rt = M.Retarget(p.rig); src = M.BVH.load(clip)
print('clip', clip, src.dur, 'fps', 1 / src.dt)
cam = bpy.data.cameras.new('c'); co = bpy.data.objects.new('c', cam); sc.collection.objects.link(co); sc.camera = co; cam.lens = float(os.environ.get('LENS', 30))
from PIL import Image
ims = []
for i, t in enumerate(times):
    rots, hips = rt.pose(src, t, place=(0, 0, 0), yaw=0, t0=times[0]); rt.apply(rots, hips); M.relax_fingers(p.rig); bpy.context.view_layer.update()
    hp = p.rig.matrix_world @ p.rig.pose.bones['mixamorig:Hips'].head
    co.location = hp + Vector(tuple(float(x) for x in os.environ.get('CAMOFF','2.2,-2.2,.2').split(','))); co.rotation_euler = (hp + Vector((0, 0, -.05)) - co.location).to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = f'/tmp/o/mt_{i}.png'; bpy.ops.render.render(write_still=True); ims.append(Image.open(f'/tmp/o/mt_{i}.png').convert('RGB'))
W = Image.new('RGB', (300 * len(ims), 400))
for i, im in enumerate(ims): W.paste(im, (300 * i, 0))
W.save(out)
