import sys, os, math, bpy
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'real'))
bpy.ops.wm.read_factory_settings(use_empty=True)
import horse as HO, cast as CA
out = sys.argv[sys.argv.index('--') + 1]
sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.samples = 12; sc.cycles.use_denoising = True
sc.render.resolution_x, sc.render.resolution_y = 400, 400; sc.view_settings.view_transform = 'AgX'
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True; w.node_tree.nodes['Background'].inputs[0].default_value = (.6, .65, .75, 1); w.node_tree.nodes['Background'].inputs[1].default_value = .8
l = bpy.data.lights.new('s', 'SUN'); l.energy = 4; o = bpy.data.objects.new('s', l); sc.collection.objects.link(o); o.rotation_euler = (.8, 0, .9)
bpy.ops.mesh.primitive_plane_add(size=40)
h = HO.HorseGLB('h'); jack = CA.load('/tmp/cast.blend', ['JACK'])['JACK']
cam = bpy.data.cameras.new('c'); co = bpy.data.objects.new('c', cam); sc.collection.objects.link(co); sc.camera = co
from PIL import Image
ims = []
for i, (t, off) in enumerate([(0, (3.2, -2.2, .8)), (.4, (4.0, .3, .5)), (.8, (-2.4, -3.0, 1.2)), (1.2, (1.4, -1.6, 1.0))]):
    h.update(t, (0, -1.1 * t, 0), 0.0, speed=1.1); bpy.context.view_layer.update()
    S = h.seat(); CA.ride(jack, S, t, face={'determined': 1.0}); bpy.context.view_layer.update()
    c = S.translation + Vector((0, 0, -.2))
    co.location = c + Vector(off); cam.lens = 35
    co.rotation_euler = (c - co.location).to_track_quat('-Z', 'Y').to_euler()
    p = f'/tmp/o/rd_{i}.png'; sc.render.filepath = p; bpy.ops.render.render(write_still=True); ims.append(Image.open(p).convert('RGB'))
W = Image.new('RGB', (800, 800))
for i, im in enumerate(ims): W.paste(im, ((i % 2) * 400, (i // 2) * 400))
W.save(out); print('OK')
