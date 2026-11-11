"""Procedural (but anatomical) creatures + imported animated GLB creatures.
Procedural: microbes / cyanobacteria, Ediacaran fronds + Dickinsonia, trilobites, Anomalocaris (swimming with its lateral
flaps rippling as a travelling wave), simple fish.  Imported: any GLB from blender/evo/assets (rigged + animated, e.g.
Sketchfab CC-BY) via load_glb(); stride-matched walking so feet never slide."""
import math, random, os
import bpy, bmesh
from mathutils import Vector, Matrix, Quaternion, noise
import terra as TR
import town as T
import lib

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')


def pmat(name, col, rough=.5, sss=0.0, coat=0.0, kws=None, scale=.3, spec_col=None):
    if kws and TR.PH:
        try:
            m = TR.simple_mat(name, kws, col, scale, tint=col, rough=rough)
            b = m.node_tree.nodes['Principled BSDF']
            if sss: b.inputs['Subsurface Weight'].default_value = sss
            if coat: b.inputs['Coat Weight'].default_value = coat
            return m
        except Exception: pass
    m = lib.mat(name, col, rough=rough, sss=sss, coat=coat)
    return m


def _obj(name, bm, mat, sub=2, smooth=True, parent=None):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = smooth
    me.materials.append(mat); o = bpy.data.objects.new(name, me); TR.coll().objects.link(o)
    if sub: md = o.modifiers.new('sub', 'SUBSURF'); md.levels = 1; md.render_levels = sub
    if parent: o.parent = parent
    return o


def segmented(name, n, length, width_fn, height_fn, mat, ring=14, parent=None, ridge=.0):
    """a body built from n segments along -Y (head first): width_fn(u), height_fn(u) give the cross-section; ridge adds the
    segment grooves trilobites/arthropods have"""
    bm = bmesh.new(); rings = []; steps = n * 3
    for k in range(steps + 1):
        u = k / steps; y = -length / 2 + u * length; w = width_fn(u); h = height_fn(u)
        g = 1 - ridge * (1 if k % 3 == 0 else 0)
        rr = []
        for j in range(ring):
            a = math.pi * j / (ring - 1)                       # half ellipse on top + flat belly
            rr.append(bm.verts.new((math.cos(a) * w / 2 * g, y, math.sin(a) * h * g)))
        rings.append(rr)
    for r0, r1 in zip(rings, rings[1:]):
        for j in range(ring - 1): bm.faces.new((r0[j], r0[j + 1], r1[j + 1], r1[j]))
        bm.faces.new((r0[-1], r0[0], r1[0], r1[-1]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _obj(name, bm, mat, 2, parent=parent)


# ------------------------------------------------------------------ microbes
def microbe(name, kind='rod', size=1.0, col='#7ac8a0', seed=0):
    """translucent single cell: rod (bacillus), coccus, or a chain (cyanobacteria filament)"""
    r = random.Random(seed); m = pmat(name + '_m', col, .25, sss=.6, coat=.6)
    b = m.node_tree.nodes['Principled BSDF']; b.inputs['Transmission Weight'].default_value = .35; b.inputs['Alpha'].default_value = .85
    root = bpy.data.objects.new(name, None); TR.coll().objects.link(root)
    if kind == 'rod':
        o = T.lib.sphere(name + '_b', .5 * size, (0, 0, 0), m, seg=24, rings=12); o.scale = (1, 2.6, 1); o.parent = root
        for k in range(6):                                     # flagella
            a = r.uniform(0, math.tau); pts = [Vector((0, 1.2 * size, 0))]
            for j in range(10): pts.append(pts[-1] + Vector((math.cos(a + j * .6) * .12 * size, .25 * size, math.sin(a + j * .6) * .12 * size)))
            T.lib.tube(f'{name}_fl{k}', pts, .025 * size, m=m).parent = root
    elif kind == 'coccus':
        o = T.lib.sphere(name + '_b', .55 * size, (0, 0, 0), m, seg=24, rings=12); o.parent = root
    else:
        for k in range(r.randint(6, 12)):
            o = T.lib.sphere(f'{name}_c{k}', .4 * size, (0, k * .75 * size, math.sin(k * .5) * .2 * size), m, seg=16, rings=8); o.scale = (1, 1.1, .95); o.parent = root
    return root


def stromatolite_field(ter, n=60, area=(-30, 30, 0, 60), seed=0):
    """cyanobacteria mats: lumpy domes of layered microbial mat in shallow water"""
    r = random.Random(seed); m = TR.blend_mat('stromat', TR.layer(('rock', 'mossy', 'moss'), '#5a6a3a', 1.2, tint='#7a8a4a'),
                                              [(TR.layer(('algae', 'moss'), '#3a6a2a', .8, tint='#4a7a2a'), dict(slope=(.6, .95), noise=.6))])
    out = []
    for k in range(n):
        x, y = r.uniform(*area[:2]), r.uniform(*area[2:]); s = r.uniform(.6, 2.4)
        o = T.lib.sphere(f'strom{k}', s, (x, y, ter.z(x, y) - s * .35), m, seg=24, rings=12); o.scale = (1, r.uniform(.8, 1.3), r.uniform(.45, .8))
        d = o.modifiers.new('disp', 'DISPLACE'); tx = bpy.data.textures.new(f'stromtx{k}', 'CLOUDS'); tx.noise_scale = .3; d.texture = tx; d.strength = .25 * s
        out.append(o)
    return out


# ------------------------------------------------------------------ Ediacaran / Cambrian animals
def dickinsonia(name, size=1.0):
    """'a pancake and a pillow had a baby': quilted oval"""
    m = pmat(name + '_m', '#c89a78', .55, sss=.3)
    return segmented(name, 22, 1.0 * size, lambda u: .75 * size * math.sin(math.pi * min(1, max(0, u))) ** .55 + .02, lambda u: .04 * size, m, ridge=.06)


def charnia(name, h=1.2):
    """frond on a stalk, swaying"""
    m = pmat(name + '_m', '#b08a6a', .5, sss=.4)
    bm = bmesh.new(); rows = 18
    for side in (-1, 1):
        prev = None
        for k in range(rows + 1):
            u = k / rows; z = u * h; w = .22 * h * math.sin(math.pi * u) ** .7
            row = [bm.verts.new((0, 0, z)), bm.verts.new((side * w, .02 * math.sin(k), z + .03 * h))]
            if prev: bm.faces.new((prev[0], prev[1], row[1], row[0]))
            prev = row
    o = _obj(name, bm, m, 1); so = o.modifiers.new('sol', 'SOLIDIFY'); so.thickness = .01; o.modifiers.move(1, 0)
    return o


def trilobite(name, size=1.0, col='#6a5440'):
    """trilobite: cephalon shield with genal spines + compound eyes, ringed thorax, pygidium; walking legs under it"""
    m = pmat(name + '_m', col, .45, coat=.4, kws=('rock', 'shell'), scale=.05)
    root = bpy.data.objects.new(name, None); TR.coll().objects.link(root)
    def wid(u):
        if u < .3: return (.62 + .25 * math.sin(math.pi * u / .3 * .5)) * size
        return (.85 - .55 * ((u - .3) / .7) ** 1.4) * size
    body = segmented(name + '_body', 14, 1.6 * size, wid, lambda u: (.16 + .08 * math.sin(math.pi * u)) * size, m, parent=root, ridge=.07)
    ax = segmented(name + '_axis', 14, 1.45 * size, lambda u: (.26 - .12 * u) * size, lambda u: (.27 + .03 * math.sin(math.pi * u)) * size, m, parent=root, ridge=.05)
    for sd in (-1, 1):
        sp = T.lib.tube(f'{name}_spine{sd}', [Vector((sd * .4 * size, -.55 * size, .05 * size)), Vector((sd * .55 * size, -.2 * size, .03 * size)), Vector((sd * .5 * size, .25 * size, .0))], .03 * size, m=m)
        sp.parent = root
        eye = T.lib.sphere(f'{name}_eye{sd}', .07 * size, (sd * .2 * size, -.55 * size, .24 * size), pmat('compoundeye', '#2a2620', .25, coat=1.0), seg=12, rings=8)
        eye.scale = (1, 1.4, .8); eye.parent = root
    legs = []
    for k in range(10):
        for sd in (-1, 1):
            l = T.cyl(f'{name}_leg{k}{sd}', .012 * size, .25 * size, (sd * .32 * size, -.5 * size + k * .11 * size, -.02 * size), m, rot=(0, sd * 1.1, 0), v=6); l.parent = root
            legs.append((l, k, sd))
    def walk(t, speed=1.0):
        for l, k, sd in legs: l.rotation_euler = (math.sin(t * 9 * speed - k * .7) * .35, sd * 1.1, 0)
    root['walk'] = 1
    return root, walk


def anomalocaris(name, size=1.0):
    """Anomalocaris canadensis: long segmented body, rows of lateral swimming flaps rippling as a travelling wave, tail fan,
    stalked eyes, a pair of spiny grasping frontal appendages, the round pineapple-ring mouth underneath"""
    m = pmat(name + '_m', '#a8603a', .45, sss=.25, coat=.3)
    root = bpy.data.objects.new(name, None); TR.coll().objects.link(root)
    L = 1.0 * size
    body = segmented(name + '_body', 13, L, lambda u: (.2 + .12 * math.sin(math.pi * min(1, u * 1.2))) * size, lambda u: .09 * size, m, parent=root, ridge=.04)
    flaps = []
    for k in range(11):
        for sd in (-1, 1):
            bm = bmesh.new(); w = (.17 - .006 * abs(k - 4)) * size; ln = .1 * size
            vs = [bm.verts.new(p) for p in ((0, 0, 0), (sd * w, -.02 * size, 0), (sd * w * .9, ln, 0), (0, ln * .9, 0))]; bm.faces.new(vs if sd > 0 else vs[::-1])
            f = _obj(f'{name}_flap{k}{sd}', bm, pmat(name + '_flap', '#c07848', .5, sss=.4), 1, parent=root)
            sol = f.modifiers.new('sol', 'SOLIDIFY'); sol.thickness = .006 * size
            f.location = (sd * (.16 + .1 * math.sin(math.pi * k / 11)) * size, -L / 2 + .14 * size + k * .075 * size, 0); flaps.append((f, k, sd))
    for j, a in enumerate((-.5, 0, .5)):                       # tail fan
        bm = bmesh.new(); vs = [bm.verts.new(p) for p in ((0, 0, 0), (-.03 * size, .22 * size, 0), (.03 * size, .22 * size, 0))]; bm.faces.new(vs)
        tf = _obj(f'{name}_tail{j}', bm, m, 1, parent=root); tf.location = (0, L / 2 - .02 * size, .02 * size); tf.rotation_euler = (0, 0, a); tf.modifiers.new('sol', 'SOLIDIFY').thickness = .005 * size
    for sd in (-1, 1):
        st = T.lib.tube(f'{name}_stalk{sd}', [Vector((sd * .08 * size, -L / 2 + .06 * size, .06 * size)), Vector((sd * .18 * size, -L / 2 + .02 * size, .12 * size))], .015 * size, m=m); st.parent = root
        e = T.lib.sphere(f'{name}_eye{sd}', .045 * size, (sd * .19 * size, -L / 2 + .02 * size, .13 * size), pmat('anoeye', '#151210', .2, coat=1.0), seg=12, rings=8); e.parent = root
    apps = []
    for sd in (-1, 1):
        segs = []
        for k in range(12):
            s_ = T.lib.sphere(f'{name}_app{sd}{k}', (.035 - .002 * k) * size, (0, 0, 0), m, seg=10, rings=6); s_.scale = (1, 1.4, 1); s_.parent = root; segs.append(s_)
            sp = T.cyl(f'{name}_spk{sd}{k}', .004 * size, .05 * size, (0, 0, 0), m, v=5); sp.parent = s_; sp.location = (0, 0, -.04 / max(.4, (1 - .05 * k)) if False else -.035 * size); sp.scale = (1, 1, 1)
        apps.append((sd, segs))
    def swim(t, speed=1.0, grab=0.0):
        for f, k, sd in flaps:                                 # metachronal wave, front to back
            f.rotation_euler = (0, sd * math.sin(t * 7 * speed - k * .55) * .55, 0)
        for sd, segs in apps:                                  # appendages curl (grab -> 1 closes them)
            p = Vector((sd * .06 * size, -L / 2 - .02 * size, -.02 * size)); a = -.3
            for k, s_ in enumerate(segs):
                curl = (.18 + .2 * grab + .05 * math.sin(t * 2 + k * .3)) * (1 if k > 2 else .3)
                a += curl; d = Vector((0, -math.cos(a), -math.sin(a))) * .06 * size
                s_.location = p; s_.rotation_euler = (a, 0, 0); p = p + d
        body.rotation_euler = (0, 0, math.sin(t * 1.4) * .04)
    return root, swim


def fish(name, size=1.0, col='#7a8a90', jaws=False):
    """early armoured fish (jawless) or the first jawed fish: fusiform body, fins, a tail that beats"""
    m = pmat(name + '_m', col, .3, coat=.7)
    root = bpy.data.objects.new(name, None); TR.coll().objects.link(root)
    body = segmented(name + '_body', 10, 1.0 * size, lambda u: (.22 * math.sin(math.pi * min(1, u * 1.1 + .05)) + .02) * size, lambda u: (.14 * math.sin(math.pi * min(1, u * 1.1 + .05)) + .015) * size, m, parent=root)
    body.scale = (1, 1, 1); bel = body.copy(); bel.data = body.data; bel.scale = (1, 1, -1); TR.coll().objects.link(bel); bel.parent = root
    bm = bmesh.new(); vs = [bm.verts.new(p) for p in ((0, 0, 0), (0, .25 * size, .16 * size), (0, .25 * size, -.16 * size))]; bm.faces.new(vs)
    tail = _obj(name + '_tail', bm, m, 1, parent=root); tail.location = (0, .48 * size, 0); tail.modifiers.new('sol', 'SOLIDIFY').thickness = .01 * size
    for sd in (-1, 1):
        e = T.lib.sphere(f'{name}_eye{sd}', .035 * size, (sd * .07 * size, -.36 * size, .04 * size), pmat('fisheye', '#101010', .1, coat=1), seg=10, rings=6); e.parent = root
    jaw = None
    if jaws:
        jaw = T.lib.sphere(name + '_jaw', .09 * size, (0, -.43 * size, -.04 * size), m, seg=12, rings=6); jaw.scale = (1, 1.2, .35); jaw.parent = root
    def swim(t, speed=1.0, bite=0.0):
        tail.rotation_euler = (0, 0, math.sin(t * 9 * speed) * .5); body.rotation_euler = (0, 0, math.sin(t * 9 * speed - 1) * .06); bel.rotation_euler = body.rotation_euler
        if jaw: jaw.rotation_euler = (bite * .5, 0, 0)
    return root, swim


# ------------------------------------------------------------------ imported animated models (GLB)
def load_glb(fname, name, height=None, length=None):
    """import a rigged, animated GLB; returns dict(root, arm, actions, size).  Scales it to a real-world height or length"""
    path = fname if os.path.isabs(fname) else os.path.join(ASSETS, fname)
    before = set(bpy.data.objects); acts0 = set(bpy.data.actions)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    root = bpy.data.objects.new(name, None); TR.coll().objects.link(root)
    for o in new:
        for c in list(o.users_collection): c.objects.unlink(o)
        TR.coll().objects.link(o)
        if o.parent is None: o.parent = root
    arm = next((o for o in new if o.type == 'ARMATURE'), None)
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ Vector(c) for o in new if o.type == 'MESH' for c in o.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))); hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    size = hi - lo; s = 1.0
    if height: s = height / max(1e-4, size.z)
    elif length: s = length / max(1e-4, max(size.x, size.y))
    root.scale = (s, s, s)
    acts = {a.name: a for a in bpy.data.actions if a not in acts0}
    return dict(root=root, arm=arm, actions=acts, size=size * s, objs=new)


def play(model, action_key, t, speed=1.0, loop=True):
    """pose the armature at time t of an action whose name contains action_key"""
    arm = model['arm']
    if arm is None: return
    act = next((a for k, a in model['actions'].items() if action_key.lower() in k.lower()), None)
    if act is None: return
    if arm.animation_data is None: arm.animation_data_create()
    arm.animation_data.action = act
    f0, f1 = act.frame_range; fps = bpy.context.scene.render.fps
    fr = f0 + (t * speed * fps)
    if loop: fr = f0 + ((fr - f0) % max(1, f1 - f0))
    else: fr = min(f1, fr)
    arm.pose.bones and None
    bpy.context.scene.frame_set(int(fr), subframe=fr - int(fr))


def stride_speed(model, action_key, foot_hint=('foot', 'toe', 'ankle')):
    """measure how far a foot bone travels backwards during one cycle (in-place walk) -> body speed in m/s that keeps
    feet planted.  Falls back to 1.0"""
    arm = model['arm']
    if arm is None: return 1.0
    act = next((a for k, a in model['actions'].items() if action_key.lower() in k.lower()), None)
    bones = [b for b in arm.pose.bones if any(h in b.name.lower() for h in foot_hint)]
    if act is None or not bones: return 1.0
    arm.animation_data_create(); arm.animation_data.action = act
    f0, f1 = act.frame_range; ys = []
    for f in range(int(f0), int(f1) + 1):
        bpy.context.scene.frame_set(f); ys.append((arm.matrix_world @ bones[0].head).y)
    dur = (f1 - f0) / bpy.context.scene.render.fps
    return abs(max(ys) - min(ys)) * 2 / max(1e-3, dur) if dur > 0 else 1.0


# ------------------------------------------------------------------ creatures as actors: NLA-timed clips, stride-matched travel, ground following
FPS = 24


def _bounds(objs):
    dg = bpy.context.evaluated_depsgraph_get(); pts = []
    for o in objs:
        if o.type != 'MESH' or o.hide_render: continue
        oe = o.evaluated_get(dg)
        pts += [oe.matrix_world @ Vector(c) for c in oe.bound_box]
    if not pts: return Vector(), Vector((1, 1, 1))
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))); hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


class Beast:
    """an imported animated creature.  clip: substring of an action name.  The model is normalised so that its root sits
    on the ground at the origin, facing -Y (like everything else here), and scaled to a real-world length/height."""
    def __init__(self, sh, glb, name, length=None, height=None, clip='walk', speed=1.0, phase=0.0, face_axis='auto', hide=('Icosphere',)):
        self.sh = sh; self.name = name
        self.m = load_glb(glb, name)
        for o in self.m['objs']:
            if any(o.name.startswith(h) for h in hide): o.hide_render = True
        self.root = self.m['root']; self.arm = self.m['arm']; self.root.scale = (1, 1, 1)
        bpy.context.view_layer.update(); lo, hi = _bounds(self.m['objs']); sz = hi - lo
        long_axis = 'y' if sz.y >= sz.x else 'x'
        s = 1.0
        if length: s = length / max(1e-4, max(sz.x, sz.y))
        elif height: s = height / max(1e-4, sz.z)
        # inner pivot: rotates the model so its head points -Y, scales it, drops its feet to z=0
        self.pivot = bpy.data.objects.new(name + '_pivot', None); TR.coll().objects.link(self.pivot)
        for o in self.m['objs']:
            if o.parent is None or o.parent == self.root: o.parent = self.pivot
        self.root.parent = None; bpy.data.objects.remove(self.root); self.root = bpy.data.objects.new(name + '_root', None); TR.coll().objects.link(self.root)
        self.pivot.parent = self.root
        self.pivot.scale = (s, s, s); self.pivot.location = (0, 0, 0)
        self.yaw_fix = 0.0
        if face_axis != 'auto':
            self.yaw_fix = {'-y': 0, '+y': math.pi, '+x': math.pi / 2, '-x': -math.pi / 2}[face_axis]
        elif long_axis == 'x': self.yaw_fix = -math.pi / 2
        self.pivot.rotation_euler = (0, 0, self.yaw_fix)
        bpy.context.view_layer.update(); lo, hi = _bounds(self.m['objs'])
        self.pivot.location = (-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z)
        self.size = (hi - lo); self.clips = {}
        self.track = None; self.set_clip(clip, speed, phase)
        self.path = None; self.ground = None
        sh.updates.insert(0, self._tick)

    def action(self, key):
        return next((a for k, a in self.m['actions'].items() if key.lower() in k.lower()), None) or (next(iter(self.m['actions'].values())) if self.m['actions'] else None)

    def set_clip(self, key, speed=1.0, phase=0.0, at=0.0):
        """play clip `key` (looping) from shot time `at`; earlier clips stay until then"""
        if self.arm is None: return
        act = self.action(key)
        if act is None: return
        ad = self.arm.animation_data or self.arm.animation_data_create(); ad.action = None
        tr = ad.nla_tracks.new(); f0, f1 = act.frame_range
        start = 1 + (self.sh.t0 + at) * FPS * 0 + at * FPS - phase * FPS
        st = tr.strips.new(f'{key}_{len(ad.nla_tracks)}', int(start), act); st.scale = 1.0 / max(.05, speed); st.repeat = 200
        st.frame_start = start; st.blend_type = 'REPLACE'; st.extrapolation = 'HOLD' if len(self.clips) == 0 else 'HOLD_FORWARD'
        self.clips[key] = (act, speed)

    def move(self, fn):
        """fn(t) -> (x, y, yaw_degrees); z comes from the ground"""
        self.path = fn; return self

    def on(self, ter, lift=0.0):
        self.ground = ter; self.lift = lift; return self

    def _tick(self, t):
        bpy.context.scene.frame_set(int(t * FPS) + 1, subframe=(t * FPS) % 1.0)
        if self.path:
            x, y, yaw = self.path(t)
            z = self.ground.z(x, y) + getattr(self, 'lift', 0) if self.ground else self.root.location.z
            self.root.location = (x, y, z); self.root.rotation_euler = (0, 0, math.radians(yaw))

    def head(self):
        """world position of the head (highest-forward point estimate)"""
        bpy.context.view_layer.update(); lo, hi = _bounds(self.m['objs'])
        f = self.root.matrix_world.to_3x3() @ Vector((0, -1, 0))
        c = (lo + hi) / 2
        return c + f * (self.size.y * .42) + Vector((0, 0, self.size.z * .3))


def walker(sh, glb, name, start, yaw, speed_mps, clip='walk', ter=None, anim_speed=1.0, phase=0.0, **kw):
    """a creature walking in a straight line at speed_mps (pick it so the feet do not slide: see stride_speed)"""
    b = Beast(sh, glb, name, clip=clip, speed=anim_speed, phase=phase, **kw)
    d = Vector((math.sin(math.radians(yaw)), -math.cos(math.radians(yaw))))
    b.move(lambda t: (start[0] + d.x * speed_mps * t, start[1] + d.y * speed_mps * t, yaw))
    if ter: b.on(ter)
    return b


def beast_stride(b, clip, anim_speed=1.0):
    """ground speed (m/s) that keeps the feet planted: how fast a planted foot slides backwards in the in-place clip"""
    if b.arm is None: return 1.0
    feet = [pb for pb in b.arm.pose.bones if any(k in pb.name.lower() for k in ('foot', 'toe', 'ankle', 'ball'))]
    if not feet: feet = [pb for pb in b.arm.pose.bones if 'leg' in pb.name.lower()][-2:]
    if not feet: return 1.0
    act = b.action(clip); f0, f1 = act.frame_range; sc = bpy.context.scene
    b.root.location = (0, 0, 0); b.root.rotation_euler = (0, 0, 0)
    tracks = {pb.name: [] for pb in feet}
    n = int(min(f1 - f0, 96)); step = 1
    for k in range(0, n, step):
        sc.frame_set(int(1 + k * max(.05, anim_speed))); bpy.context.view_layer.update()
        for pb in feet: tracks[pb.name].append(b.arm.matrix_world @ pb.head)
    best = []
    for nm, ps in tracks.items():
        zs = [p.z for p in ps]; zmin = min(zs); thr = zmin + (max(zs) - zmin) * .15
        for a, c in zip(ps, ps[1:]):
            if a.z < thr and c.z < thr: best.append(((c - a).xy).length * FPS / step)
    if not best: return 1.0
    best.sort(); return best[len(best) // 2]
