import sys, os, math, bpy
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
bpy.ops.wm.read_factory_settings(use_empty=True)
os.environ.setdefault('VEG', '.2')
import town as T
import toon as TO
from common import ink_setup
out = sys.argv[sys.argv.index('--') + 1]; times = [float(x) for x in sys.argv[sys.argv.index('--') + 2].split(',')]
sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.samples = int(os.environ.get('S', 12)); sc.cycles.use_denoising = True
RW, RH = int(os.environ.get('RW', 360)), int(os.environ.get('RH', 640)); sc.render.resolution_x, sc.render.resolution_y = RW, RH
T.build_town(); T.sky('day', 30, 150)
jack = TO.Toon('JACK', TO.JACK); sher = TO.Toon('SHER', TO.SHERIFF)
ppl = [TO.Toon(f'T{i}', TO.crowd_preset(i)) for i in range(4)]
A = [TO.ToonActor(jack, [TO.Act(0, '82_09', 6.6, 4, loc=(.6, -1, 0), yaw=180)], face=[(0, 'determined'), (1.0, 'suspicious')]),
     TO.ToonActor(sher, [TO.Act(0, '80_48', 1.0, 6, loc=(-1.0, 6, 0), yaw=200, lock_root=True)], face=[(0, 'smirk')], talk=[(0, 3, 1)])]
for i, p in enumerate(ppl):
    A.append(TO.ToonActor(p, [TO.Act(0, ['79_74', '77_02', '80_44', '40_10'][i], 1.5 + i, 6, loc=(-3.5 + i * 2.2, 8 + (i % 2), 0), yaw=180 + (i - 1.5) * 15, lock_root=True)], face=[(0, ['shock', 'laugh', 'worry', 'angry'][i])], look=lambda t: (.6, 1, 1.6)))
cam = bpy.data.cameras.new('c'); co = bpy.data.objects.new('c', cam); sc.collection.objects.link(co); sc.camera = co; cam.lens = 28
#ink_setup(RW, 1.0, 5.0, 2.0)
fs = bpy.context.view_layer.freestyle_settings
for ls in list(fs.linesets):
    if ls.name == 'props': fs.linesets.remove(ls)
from PIL import Image
ims = []
for i, t in enumerate(times):
    for a in A: a.apply(t)
    bpy.context.view_layer.update()
    co.location = (2.2, 9.5, 1.5); co.rotation_euler = (Vector((0, 2, 1.2)) - co.location).to_track_quat('-Z', 'Y').to_euler()
    p = f'/tmp/o/tt_{i}.png'; sc.render.filepath = p; bpy.ops.render.render(write_still=True); ims.append(Image.open(p).convert('RGB'))
W = Image.new('RGB', (RW * len(ims), RH))
for i, im in enumerate(ims): W.paste(im, (RW * i, 0))
W.save(out); print('OK')
