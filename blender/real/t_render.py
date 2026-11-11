import sys, bpy, math, os
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath=sys.argv[sys.argv.index('--')+1])
out = sys.argv[sys.argv.index('--')+2]; mode = sys.argv[sys.argv.index('--')+3]
sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.samples = int(os.environ.get('S', 32)); sc.cycles.use_denoising = True
sc.render.resolution_x, sc.render.resolution_y = (600, 800)
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True; w.node_tree.nodes['Background'].inputs[0].default_value = (.25, .3, .38, 1); w.node_tree.nodes['Background'].inputs[1].default_value = .6
def light(name, loc, e, size, col):
    l = bpy.data.lights.new(name, 'AREA'); l.energy = e; l.size = size; l.color = col; o = bpy.data.objects.new(name, l); sc.collection.objects.link(o); o.location = loc
    d = Vector((0, 0, 1.5)) - Vector(loc); o.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
light('key', (-1.5, -2.2, 2.4), 300, 1.5, (1, .92, .82)); light('rim', (1.6, 1.8, 2.2), 250, 1, (.7, .8, 1)); light('fill', (2, -2, 1.2), 80, 2, (.8, .85, 1))
h = next(o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith('Human'))
top = max((h.matrix_world @ v.co).z for v in h.data.vertices)
cam = bpy.data.cameras.new('c'); co = bpy.data.objects.new('c', cam); sc.collection.objects.link(co); sc.camera = co
if mode == 'face': co.location = (0, -.85, top - .12); tgt = Vector((0, 0, top - .13)); cam.lens = 85
else: co.location = (0, -4.6, 1.0); tgt = Vector((0, 0, .92)); cam.lens = 45
co.rotation_euler = (tgt - co.location).to_track_quat('-Z', 'Y').to_euler()
sc.render.filepath = out; bpy.ops.render.render(write_still=True)
