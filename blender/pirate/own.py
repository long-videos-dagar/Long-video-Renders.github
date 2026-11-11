"""Own-built characters: skin-modifier body + modelled head, auto-weighted to the mocap skeleton."""
import bpy, bmesh, math, os, sys, numpy as np
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import lib
from lib import mat, coll

R = dict(Hips=(.165, .105), Spine=(.15, .10), Spine1=(.165, .105), Spine2=(.185, .115), Neck=(.052, .055),
         Shoulder=(.055, .055), Arm=(.047, .047), ForeArm=(.037, .037), Hand=(.036, .016), UpLeg=(.088, .088), Leg=(.058, .058), Foot=(.042, .05), Toe=(.04, .025))

def body_mesh(arm, name, skin_mat, build=1.0):
    B = arm.data.bones; verts = []; idx = {}
    def add(key, p, r):
        idx[key] = len(verts); verts.append((Vector(p), (r[0] * build, r[1] * build)))
    H = lambda n: B[n].head_local; T = lambda n: B[n].tail_local
    add('Hips', H('Hips'), R['Hips']); add('Spine', H('Spine'), R['Spine']); add('Spine1', H('Spine1'), R['Spine1']); add('Spine2', H('Spine2'), R['Spine2'])
    add('Neck', H('Neck'), R['Neck']); add('NeckTop', T('Neck'), (.048, .05))
    edges = [('Hips', 'Spine'), ('Spine', 'Spine1'), ('Spine1', 'Spine2'), ('Spine2', 'Neck'), ('Neck', 'NeckTop')]
    for s in ('Left', 'Right'):
        for n, r in (('Shoulder', 'Shoulder'), ('Arm', 'Arm'), ('ForeArm', 'ForeArm'), ('Hand', 'Hand')): add(s + n, H(s + n), R[r])
        add(s + 'HandEnd', T(s + 'Hand'), (.03, .012))
        add(s + 'UpLeg', H(s + 'UpLeg'), R['UpLeg']); add(s + 'Leg', H(s + 'Leg'), R['Leg']); add(s + 'Foot', H(s + 'Foot'), R['Foot']); add(s + 'Toe', H(s + 'ToeBase'), R['Toe']); add(s + 'ToeEnd', T(s + 'ToeBase'), (.03, .02))
        edges += [('Spine2', s + 'Shoulder'), (s + 'Shoulder', s + 'Arm'), (s + 'Arm', s + 'ForeArm'), (s + 'ForeArm', s + 'Hand'), (s + 'Hand', s + 'HandEnd'),
                  ('Hips', s + 'UpLeg'), (s + 'UpLeg', s + 'Leg'), (s + 'Leg', s + 'Foot'), (s + 'Foot', s + 'Toe'), (s + 'Toe', s + 'ToeEnd')]
    me = bpy.data.meshes.new(name); bm = bmesh.new(); sk = bm.verts.layers.skin.verify()
    bv = []
    for p, r in verts:
        v = bm.verts.new(p); v[sk].radius = r; bv.append(v)
    for a, b in edges: bm.edges.new((bv[idx[a]], bv[idx[b]]))
    bv[idx['Hips']][sk].use_root = True
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); coll('Humans').objects.link(ob)
    m1 = ob.modifiers.new('skin', 'SKIN'); m1.use_smooth_shade = True; m1.branch_smoothing = 1.0
    m2 = ob.modifiers.new('sub', 'SUBSURF'); m2.levels = 2; m2.render_levels = 2
    dg = bpy.context.evaluated_depsgraph_get(); ev = ob.evaluated_get(dg); me2 = bpy.data.meshes.new_from_object(ev)
    ob.modifiers.clear(); ob.data = me2
    for p in me2.polygons: p.use_smooth = True
    me2.materials.append(skin_mat)
    return ob

def rig(ob, arm):
    bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True); arm.select_set(True); bpy.context.view_layer.objects.active = arm
    bpy.ops.object.parent_set(type='ARMATURE_AUTO')
