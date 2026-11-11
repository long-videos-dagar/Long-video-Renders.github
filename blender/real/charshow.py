"""python3 charshow.py -- out.png mode   (mode: lineup | face:jack | face:sheriff)"""
import sys, os, math, bpy
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import realchar as R
a = sys.argv[sys.argv.index('--') + 1:]; out, mode = a[0], a[1]
bpy.ops.wm.read_factory_settings(use_empty=True); R.init()
sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.samples = int(os.environ.get('S', 32)); sc.cycles.use_denoising = True
sc.render.resolution_x, sc.render.resolution_y = int(os.environ.get('RW', 720)), int(os.environ.get('RH', 960))
sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True; bg = w.node_tree.nodes['Background']; bg.inputs[0].default_value = (.55, .62, .75, 1); bg.inputs[1].default_value = .35
def light(kind, name, loc, e, col, size=1.0, rot=None):
    l = bpy.data.lights.new(name, kind); l.energy = e; l.color = col
    if kind == 'AREA': l.size = size
    if kind == 'SUN': l.angle = math.radians(2)
    o = bpy.data.objects.new(name, l); sc.collection.objects.link(o); o.location = loc
    o.rotation_euler = rot or (Vector((0, 0, 1.4)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler(); return o
light('SUN', 'sun', (0, 0, 10), 4.0, (1, .86, .68), rot=(math.radians(55), 0, math.radians(-35)))
light('AREA', 'fill', (2.5, -3, 1.8), 120, (.75, .85, 1), 3)
light('AREA', 'rim', (-1.5, 2.5, 2.5), 300, (1, .8, .6), 1.5)
bpy.ops.mesh.primitive_plane_add(size=40); g = bpy.context.active_object; g.data.materials.append(R.cloth_mat('dirt', '#9a7a58', rough=.95, weave=40, sheen=0, wear=.6))
bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 6, 0), rotation=(math.pi / 2, 0, 0)); g2 = bpy.context.active_object; g2.data.materials.append(R.cloth_mat('wall', '#8a6a4a', rough=.9, weave=12, wear=.5))
jack = R.Person('JACK', R.JACK); sher = R.Person('SHER', R.SHERIFF)
jack.rig.location = (-.45, 0, 0); jack.rig.rotation_euler = (0, 0, math.radians(15))
sher.rig.location = (.45, 0, 0); sher.rig.rotation_euler = (0, 0, math.radians(-15))
def relax(p, ex):
    for sd, s in (('Left', 1), ('Right', -1)):
        p.aim(sd + 'Arm', (s * .18, .05, -1)); p.aim(sd + 'ForeArm', (s * .1, -.25, -1))
    p.set_expression(ex)
relax(jack, {os.environ.get('EJ','determined'): 1.0}); relax(sher, {os.environ.get('ES','smirk'): 1.0})
bpy.context.view_layer.update()
def head(p): return p.rig.matrix_world @ p.rig.pose.bones['mixamorig:Head'].head
cam = bpy.data.cameras.new('c'); co = bpy.data.objects.new('c', cam); sc.collection.objects.link(co); sc.camera = co
if mode == 'lineup': co.location = (0, -4.4, 1.05); tgt = Vector((0, 0, .95)); cam.lens = 42
else:
    p = jack if mode.endswith('jack') else sher; hp = head(p) + Vector((0, 0, .09)); fw = p.rig.matrix_world.to_3x3() @ Vector((0, -1, 0))
    co.location = hp + fw * .9 + Vector((0, 0, .02)); tgt = hp; cam.lens = 75; cam.dof.use_dof = True; cam.dof.focus_distance = (co.location - hp).length; cam.dof.aperture_fstop = 2.8
co.rotation_euler = (tgt - co.location).to_track_quat('-Z', 'Y').to_euler()
sc.render.filepath = os.path.abspath(out); bpy.ops.render.render(write_still=True); print('RENDERED', out)
