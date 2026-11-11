import sys, os, math, bpy
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
bpy.ops.wm.read_factory_settings(use_empty=True)
import horse as HO
out = sys.argv[sys.argv.index('--') + 1]; view = sys.argv[sys.argv.index('--') + 2]
sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.samples = int(os.environ.get('S', 12)); sc.cycles.use_denoising = True
sc.render.resolution_x, sc.render.resolution_y = 400, 300; sc.view_settings.view_transform = 'AgX'
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True; w.node_tree.nodes['Background'].inputs[0].default_value = (.6, .65, .75, 1); w.node_tree.nodes['Background'].inputs[1].default_value = .8
l = bpy.data.lights.new('s', 'SUN'); l.energy = 4; o = bpy.data.objects.new('s', l); sc.collection.objects.link(o); o.rotation_euler = (.8, 0, .9)
bpy.ops.mesh.primitive_plane_add(size=40); g = bpy.context.active_object; m = bpy.data.materials.new('g'); m.use_nodes = True; m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (.4, .3, .2, 1); g.data.materials.append(m)
h = HO.Horse('h')
cam = bpy.data.cameras.new('c'); co = bpy.data.objects.new('c', cam); sc.collection.objects.link(co); sc.camera = co
from PIL import Image
ims = []
times = [0, .28, .56, .84]
for i, t in enumerate(times):
    h.update(t, (0, 0, 0), 0.0, 'walk', 1.5); bpy.context.view_layer.update()
    if view == 'side': co.location = (5.5, -.3, 1.2); tgt = (0, -.3, .95); cam.lens = 40
    elif view == 'head': co.location = (1.6, -2.4, 1.9); tgt = (0, -.9, 1.6); cam.lens = 45
    else: co.location = (3.0, -4.2, 1.6); tgt = (0, -.3, 1.0); cam.lens = 40
    co.rotation_euler = (Vector(tgt) - co.location).to_track_quat('-Z', 'Y').to_euler()
    p = f'/tmp/o/ht_{i}.png'; sc.render.filepath = p; bpy.ops.render.render(write_still=True); ims.append(Image.open(p).convert('RGB'))
W = Image.new('RGB', (800, 600))
for i, im in enumerate(ims): W.paste(im, ((i % 2) * 400, (i // 2) * 300))
W.save(out); print('OK')
