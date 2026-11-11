"""python3 portraits.py -- <outdir> : front portraits of the toon Jack and Sheriff for the wanted posters"""
import sys, os, math, bpy
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from mathutils import Vector
import toon as TO
out = sys.argv[sys.argv.index('--') + 1]; os.makedirs(out, exist_ok=True)
for cid, who, face, p in (('JACK', 'jack', 'determined', TO.JACK), ('SHER', 'sher', 'smirk', TO.SHERIFF)):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.samples = 32; sc.cycles.use_denoising = True; sc.render.resolution_x, sc.render.resolution_y = 560, 620
    sc.view_settings.view_transform = 'Standard'
    w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True; w.node_tree.nodes['Background'].inputs[0].default_value = (.85, .82, .75, 1); w.node_tree.nodes['Background'].inputs[1].default_value = 1.0
    ch = TO.Toon(cid, p)
    ch.fn = lambda t, face=face: dict(loc=(0, 0, 0), yaw=0, head=[0, 0, 0], face=dict(TO.EXPR[face]))
    ch.apply(0.0); bpy.context.view_layer.update()
    h = ch.head.matrix_world @ Vector((0, 0, ch.cz)) + Vector((0, 0, -.06))
    l = bpy.data.lights.new('k', 'AREA'); l.energy = 60; l.size = 1.2; lo = bpy.data.objects.new('k', l); sc.collection.objects.link(lo); lo.location = h + Vector((-.6, -1.2, .5)); lo.rotation_euler = (h - lo.location).to_track_quat('-Z', 'Y').to_euler()
    cam = bpy.data.cameras.new('c'); co = bpy.data.objects.new('c', cam); sc.collection.objects.link(co); sc.camera = co; cam.lens = 85
    co.location = h + Vector((0, -2.6, .02)); co.rotation_euler = (h - co.location).to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = os.path.join(out, f'{who}_face.png'); bpy.ops.render.render(write_still=True); print('portrait', who)
