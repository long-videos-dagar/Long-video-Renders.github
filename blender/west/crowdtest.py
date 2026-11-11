import sys, os, math, bpy
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
bpy.ops.wm.read_factory_settings(use_empty=True)
import toon as TO
from lib import box
from common import solid
out = sys.argv[sys.argv.index('--') + 1]; times = [float(x) for x in sys.argv[sys.argv.index('--') + 2].split(',')]
clips = os.environ.get('CLIPS', '79_74,77_02,80_44,40_10,80_48,82_08').split(',')
sc = bpy.context.scene; sc.render.engine = 'BLENDER_EEVEE_NEXT' if 'BLENDER_EEVEE_NEXT' in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items] else 'BLENDER_EEVEE'
RW, RH = 1100, 520; sc.render.resolution_x, sc.render.resolution_y = RW, RH
box('ground', (40, 40, .02), (0, 0, -.01), solid('#c8b090', .9))
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True; w.node_tree.nodes['Background'].inputs[0].default_value = (.7, .75, .8, 1)
l = bpy.data.lights.new('s', 'SUN'); l.energy = 3; lo = bpy.data.objects.new('s', l); sc.collection.objects.link(lo); lo.rotation_euler = (.6, .2, .5)
A = []
for i, c in enumerate(clips):
    p = TO.Toon(f'T{i}', TO.crowd_preset(i))
    A.append(TO.ToonActor(p, [TO.Act(0, c, 1.0, 8, loc=(-3.2 + i * 1.3, 0, 0), yaw=0, lock_root=True)], face=[(0, ['idle','chat','watch'][i % 3])]))
cam = bpy.data.cameras.new('c'); co = bpy.data.objects.new('c', cam); sc.collection.objects.link(co); sc.camera = co; cam.lens = 30
co.location = (0, -7.5, 1.4); co.rotation_euler = (math.radians(88), 0, 0)
from PIL import Image
ims = []
for i, t in enumerate(times):
    for a in A: a.apply(t)
    bpy.context.view_layer.update()
    p = f'/tmp/o/ct_{i}.png'; sc.render.filepath = p; bpy.ops.render.render(write_still=True); ims.append(Image.open(p).convert('RGB'))
W = Image.new('RGB', (RW, RH * len(ims)))
for i, im in enumerate(ims): W.paste(im, (0, RH * i))
W.save(out); print('OK')
