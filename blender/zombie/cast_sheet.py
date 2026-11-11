"""render the DAGAR CLIPS ink cast bible: every recurring toon in a lineup with name labels"""
import sys, os, math
sys.path.insert(0, '' + os.path.join(os.path.dirname(os.path.abspath(__file__)), '..') + '/zombie'); sys.argv = ['story.py', '--', 'none']
import story as Z
import importlib.util
spec = importlib.util.spec_from_file_location('ustory', '' + os.path.join(os.path.dirname(os.path.abspath(__file__)), '..') + '/undertaker/story.py'); U = importlib.util.module_from_spec(spec); spec.loader.exec_module(U)
TO = Z.TO; F = Z.F
import bpy
from mathutils import Vector
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.samples = int(os.environ.get('S', 24)); sc.cycles.use_denoising = True
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True; w.node_tree.nodes['Background'].inputs[0].default_value = (1, 1, 1, 1); w.node_tree.nodes['Background'].inputs[1].default_value = .9
sc.render.film_transparent = True; sc.view_settings.view_transform = 'Standard'
l = bpy.data.lights.new('sun', 'SUN'); l.energy = 2.5; o = bpy.data.objects.new('sun', l); sc.collection.objects.link(o); o.rotation_euler = (math.radians(50), 0, math.radians(-25))
rows = [[('JACK', TO.JACK, 'Jack (cowboy hero)'), ('SHER', TO.SHERIFF, 'The Sheriff'), ('EZRA', U.EZ, 'Ezra Pike'), ('MORT', U.MORT, 'Mortimer (undertaker)'),
         ('JOE', U.JOE, 'Father Joe'), ('W0', U.widow(0), 'Widow'), ('B0', U.bandsman(0), 'Bandsman')],
        [('WALT', Z.WALT, 'Grandpa Walt'), ('MAYOR', Z.MAYOR, 'The Mayor'), ('DOC', Z.DOC, 'The Doctor'), ('COP0', Z.COP(0), 'Police officer'),
         ('JOG', Z.JOG, 'Jogger'), ('ANCHOR', Z.ANCHOR, 'News anchor'), ('BARISTA', Z.BARISTA, 'Barista')]]
from PIL import Image, ImageDraw, ImageFont
f = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 22)
sheets = []
for r, row in enumerate(rows):
    for ob in list(bpy.data.objects):
        if ob.type != 'LIGHT': bpy.data.objects.remove(ob)
    acts = []
    for k, (cid, pre, name) in enumerate(row):
        ch = TO.Toon(cid, pre)
        a = TO.ToonActor(ch, [TO.Act(0, '77_02', 1.0 + k * .3, 6, loc=((k - 3) * 1.15, 0, 0), yaw=0, lock_root=True)], face=[(0, ['smile', 'smirk', 'smug', 'deadpan', 'idle', 'sad', 'happy'][k])])
        acts.append(a)
    for a in acts: a.apply(1.0)
    bpy.context.view_layer.update()
    cam = bpy.data.cameras.new('c'); co = bpy.data.objects.new('c', cam); sc.collection.objects.link(co); sc.camera = co; cam.lens = 50
    co.location = (0, -12.5, 1.15); co.rotation_euler = (Vector((0, 0, .95)) - co.location).to_track_quat('-Z', 'Y').to_euler()
    sc.render.resolution_x, sc.render.resolution_y = 1800, 700; p = f'/tmp/castrow{r}.png'; sc.render.filepath = p; bpy.ops.render.render(write_still=True)
    im = Image.open(p).convert('RGBA'); bg = Image.new('RGBA', im.size, (255, 255, 255, 255)); bg.alpha_composite(im); d = ImageDraw.Draw(bg)
    for k, (cid, pre, name) in enumerate(row): d.text((1800 / 2 + (k - 3) * 1.15 * 1800 / (12.5 * 36 / 50) , 660), name, font=f, fill=(20, 20, 20), anchor='mm')
    sheets.append(bg.convert('RGB'))
W = Image.new('RGB', (1800, 1400 + 80), 'white'); d = ImageDraw.Draw(W)
d.text((900, 40), 'DAGAR CLIPS - INK CAST (original characters)', font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 36), fill='black', anchor='mm')
for r, s in enumerate(sheets): W.paste(s, (0, 80 + r * 700))
W.save('/tmp/ink_cast.jpg', quality=90); print('OK')
