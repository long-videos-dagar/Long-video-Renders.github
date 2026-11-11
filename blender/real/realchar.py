"""Realistic human characters for the pirate film.

Body: MakeHuman base mesh via MPFB2 (CC0 assets), macro shape (age, muscle, weight, ethnicity), Mixamo-named rig with
skin weights (so motion-capture clips drive it directly). Face: 34 MakeHuman facial action units loaded as shape keys
and mixed into named expressions. Eyes, hair, beard, eyebrows (Cycles particle hair), clothes (fitted shells cut from
the body mesh, skinned to the same rig) and hats are built here. No assets with branding are used.

Usage inside a Blender python session:
    import realchar as R
    R.init()
    cap = R.Person('CAP', R.CAPTAIN)
    cap.rig.location = ...; cap.set_expression({'angry': 1.0})
"""
import bpy, bmesh, addon_utils, importlib, math, os, random
from mathutils import Vector, Matrix

_MPFB = 'bl_ext.user_default.mpfb'
HS = TS = None
UNITS = None


def init():
    """enable the MPFB extension (installed under the user extension dir) and import its services"""
    global HS, TS, UNITS
    if HS: return
    try: addon_utils.enable(_MPFB, default_set=True, persistent=True)
    except Exception as e: print('mpfb enable:', e)
    M = lambda p: importlib.import_module(_MPFB + '.' + p)
    HS = M('services.humanservice').HumanService; TS = M('services.targetservice').TargetService
    import bl_ext.user_default.mpfb as mp
    UNITS = os.path.join(os.path.dirname(mp.__file__), 'data', 'targets', 'expression', 'units', 'caucasian')


def hexc(h, a=1.0):
    h = h.lstrip('#'); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple((x / 12.92 if x <= .04045 else ((x + .055) / 1.055) ** 2.4) for x in c) + (a,)


# ------------------------------------------------------------------ materials
def _nodes(m):
    m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial'); return nt, nt.nodes, nt.links, out


def skin_mat(name, tone, red=.25, rough=.42, weather=.0):
    """layered skin: SSS base, blotchy redness, freckles/weathering, pores bump, oily roughness variation"""
    m = bpy.data.materials.new(name); nt, N, L, out = _nodes(m)
    b = N.new('ShaderNodeBsdfPrincipled'); L.new(b.outputs[0], out.inputs[0])
    tc = N.new('ShaderNodeTexCoord')
    n1 = N.new('ShaderNodeTexNoise'); n1.inputs['Scale'].default_value = 18; n1.inputs['Detail'].default_value = 6; L.new(tc.outputs['Object'], n1.inputs['Vector'])
    n2 = N.new('ShaderNodeTexNoise'); n2.inputs['Scale'].default_value = 140; n2.inputs['Detail'].default_value = 3; L.new(tc.outputs['Object'], n2.inputs['Vector'])
    base = N.new('ShaderNodeRGB'); base.outputs[0].default_value = hexc(tone)
    redc = N.new('ShaderNodeRGB'); redc.outputs[0].default_value = (.55, .12, .09, 1)
    mr = N.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = .45; mr.inputs['From Max'].default_value = .7; mr.inputs['To Max'].default_value = red; L.new(n1.outputs['Fac'], mr.inputs['Value'])
    mix = N.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'; L.new(mr.outputs[0], mix.inputs['Factor']); L.new(base.outputs[0], mix.inputs['A']); L.new(redc.outputs[0], mix.inputs['B'])
    fr = N.new('ShaderNodeMapRange'); fr.inputs['From Min'].default_value = .62; fr.inputs['From Max'].default_value = .75; fr.inputs['To Max'].default_value = .18 + weather; L.new(n2.outputs['Fac'], fr.inputs['Value'])
    dk = N.new('ShaderNodeMix'); dk.data_type = 'RGBA'; dk.blend_type = 'MULTIPLY'; L.new(fr.outputs[0], dk.inputs['Factor']); L.new(mix.outputs['Result'], dk.inputs['A']); dk.inputs['B'].default_value = (.45, .3, .22, 1)
    L.new(dk.outputs['Result'], b.inputs['Base Color'])
    b.inputs['Subsurface Weight'].default_value = .5; b.inputs['Subsurface Radius'].default_value = (1.0, .35, .18); b.inputs['Subsurface Scale'].default_value = .012
    rr = N.new('ShaderNodeMapRange'); rr.inputs['To Min'].default_value = rough + .0; rr.inputs['To Max'].default_value = rough + .2; L.new(n1.outputs['Fac'], rr.inputs['Value']); L.new(rr.outputs[0], b.inputs['Roughness'])
    b.inputs['Specular IOR Level'].default_value = .45; b.inputs['Coat Weight'].default_value = .04; b.inputs['Coat Roughness'].default_value = .45
    pv = N.new('ShaderNodeTexVoronoi'); pv.inputs['Scale'].default_value = 900; pv.feature = 'DISTANCE_TO_EDGE'; L.new(tc.outputs['Object'], pv.inputs['Vector'])
    bump = N.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = .12; bump.inputs['Distance'].default_value = .0004; L.new(pv.outputs['Distance'], bump.inputs['Height'])
    b2 = N.new('ShaderNodeBump'); b2.inputs['Strength'].default_value = .25 + weather; b2.inputs['Distance'].default_value = .001; L.new(n2.outputs['Fac'], b2.inputs['Height']); L.new(bump.outputs[0], b2.inputs['Normal'])
    L.new(b2.outputs[0], b.inputs['Normal'])
    return m


def cloth_mat(name, col, rough=.85, weave=420.0, sheen=.3, wear=.25, leather=False):
    m = bpy.data.materials.new(name); nt, N, L, out = _nodes(m)
    b = N.new('ShaderNodeBsdfPrincipled'); L.new(b.outputs[0], out.inputs[0])
    tc = N.new('ShaderNodeTexCoord')
    n = N.new('ShaderNodeTexNoise'); n.inputs['Scale'].default_value = 7; n.inputs['Detail'].default_value = 8; L.new(tc.outputs['Object'], n.inputs['Vector'])
    c = N.new('ShaderNodeMix'); c.data_type = 'RGBA'; c.blend_type = 'MULTIPLY'; c.inputs['A'].default_value = hexc(col)
    mr = N.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = .4; mr.inputs['From Max'].default_value = .65; mr.inputs['To Max'].default_value = wear; L.new(n.outputs['Fac'], mr.inputs['Value']); L.new(mr.outputs[0], c.inputs['Factor'])
    c.inputs['B'].default_value = (.35, .3, .25, 1); L.new(c.outputs['Result'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = rough
    if leather:
        b.inputs['Coat Weight'].default_value = .25; b.inputs['Coat Roughness'].default_value = .3
        v = N.new('ShaderNodeTexVoronoi'); v.inputs['Scale'].default_value = 260; L.new(tc.outputs['Object'], v.inputs['Vector']); h = v.outputs['Distance']
    else:
        b.inputs['Sheen Weight'].default_value = sheen; b.inputs['Sheen Tint'].default_value = hexc(col)
        w = N.new('ShaderNodeTexWave'); w.wave_type = 'BANDS'; w.inputs['Scale'].default_value = weave; w.inputs['Distortion'].default_value = 1.5; L.new(tc.outputs['Object'], w.inputs['Vector'])
        w2 = N.new('ShaderNodeTexWave'); w2.wave_type = 'BANDS'; w2.bands_direction = 'Y'; w2.inputs['Scale'].default_value = weave; L.new(tc.outputs['Object'], w2.inputs['Vector'])
        a = N.new('ShaderNodeMath'); a.operation = 'MULTIPLY'; L.new(w.outputs['Fac'], a.inputs[0]); L.new(w2.outputs['Fac'], a.inputs[1]); h = a.outputs[0]
    bp = N.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = .35; bp.inputs['Distance'].default_value = .0008; L.new(h, bp.inputs['Height'])
    bp2 = N.new('ShaderNodeBump'); bp2.inputs['Strength'].default_value = .4; bp2.inputs['Distance'].default_value = .004; L.new(n.outputs['Fac'], bp2.inputs['Height']); L.new(bp.outputs[0], bp2.inputs['Normal'])
    L.new(bp2.outputs[0], b.inputs['Normal'])
    return m


def metal_mat(name, col, rough=.3):
    m = bpy.data.materials.new(name); nt, N, L, out = _nodes(m)
    b = N.new('ShaderNodeBsdfPrincipled'); L.new(b.outputs[0], out.inputs[0]); b.inputs['Base Color'].default_value = hexc(col); b.inputs['Metallic'].default_value = 1; b.inputs['Roughness'].default_value = rough
    return m


def eye_mat(name, iris, radius=1.0):
    """eyeball in object space: -Y is the gaze. sclera with veins -> limbal ring -> iris fibres -> pupil; glossy wet coat"""
    m = bpy.data.materials.new(name); nt, N, L, out = _nodes(m)
    b = N.new('ShaderNodeBsdfPrincipled'); L.new(b.outputs[0], out.inputs[0])
    tc = N.new('ShaderNodeTexCoord'); scl = N.new('ShaderNodeVectorMath'); scl.operation = 'SCALE'; scl.inputs['Scale'].default_value = 1.0 / radius; L.new(tc.outputs['Object'], scl.inputs[0])
    sep = N.new('ShaderNodeSeparateXYZ'); L.new(scl.outputs[0], sep.inputs[0])
    # radial distance from the gaze axis (x,z)
    vx = N.new('ShaderNodeCombineXYZ'); L.new(sep.outputs['X'], vx.inputs['X']); L.new(sep.outputs['Z'], vx.inputs['Y'])
    ln = N.new('ShaderNodeVectorMath'); ln.operation = 'LENGTH'; L.new(vx.outputs[0], ln.inputs[0])
    front = N.new('ShaderNodeMath'); front.operation = 'LESS_THAN'; L.new(sep.outputs['Y'], front.inputs[0]); front.inputs[1].default_value = 0.0
    r = N.new('ShaderNodeMath'); r.operation = 'ADD'; L.new(ln.outputs['Value'], r.inputs[0])
    inv = N.new('ShaderNodeMath'); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0; L.new(front.outputs[0], inv.inputs[1])
    big = N.new('ShaderNodeMath'); big.operation = 'MULTIPLY'; L.new(inv.outputs[0], big.inputs[0]); big.inputs[1].default_value = 10.0
    L.new(big.outputs[0], r.inputs[1])
    ramp = N.new('ShaderNodeValToRGB'); L.new(r.outputs[0], ramp.inputs['Fac'])
    cr = ramp.color_ramp; cr.interpolation = 'LINEAR'
    ic = hexc(iris); dk = tuple(x * .35 for x in ic[:3]) + (1,)
    stops = [(0.0, (0.01, 0.01, 0.01, 1)), (.17, (0.01, 0.01, 0.01, 1)), (.19, dk), (.33, ic), (.43, dk), (.46, (.05, .04, .04, 1)), (.5, (.75, .7, .66, 1)), (1.0, (.85, .78, .74, 1))]
    cr.elements[0].position, cr.elements[0].color = stops[0]; cr.elements[1].position, cr.elements[1].color = stops[-1]
    for p, c in stops[1:-1]: e = cr.elements.new(p); e.color = c
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 60; nz.inputs['Detail'].default_value = 4; L.new(tc.outputs['Object'], nz.inputs['Vector'])
    mm = N.new('ShaderNodeMix'); mm.data_type = 'RGBA'; mm.blend_type = 'OVERLAY'; mm.inputs['Factor'].default_value = .35; L.new(ramp.outputs['Color'], mm.inputs['A']); L.new(nz.outputs['Color'], mm.inputs['B'])
    L.new(mm.outputs['Result'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = .4; b.inputs['Coat Weight'].default_value = 1.0; b.inputs['Coat Roughness'].default_value = .02; b.inputs['Coat IOR'].default_value = 1.38
    b.inputs['Subsurface Weight'].default_value = .1; b.inputs['Subsurface Radius'].default_value = (.8, .4, .3); b.inputs['Subsurface Scale'].default_value = .002
    return m


def hair_mat(name, melanin=.8, red=.25, grey=0.0, rough=.35):
    m = bpy.data.materials.new(name); nt, N, L, out = _nodes(m)
    h = N.new('ShaderNodeBsdfHairPrincipled'); L.new(h.outputs[0], out.inputs[0])
    try: h.parametrization = 'MELANIN'
    except Exception: pass
    h.inputs['Melanin'].default_value = melanin * (1 - grey * .9); h.inputs['Melanin Redness'].default_value = red
    h.inputs['Roughness'].default_value = rough; h.inputs['Random Roughness'].default_value = .3
    if 'Random Color' in h.inputs: h.inputs['Random Color'].default_value = .15
    return m


# ------------------------------------------------------------------ cast presets (Wild West)
JACK = dict(gender=1.0, age=.5, muscle=.72, weight=.45, height=.6, race=dict(caucasian=.8, african=.05, asian=.15), skin='#c99070', weather=.12,
            iris='#4a6a78', hair=dict(melanin=.75, red=.35, grey=0.0), scalp=.035, beard=.004, brows=.009,
            outfit=dict(shirt='#a8b4bc', vest='#5a3a22', trousers='#3c4656', boots='#4a2c18', neckerchief='#8a2a20', belt='#3a2414', hat='cowboy', hatcol='#8a6a48'))
SHERIFF = dict(gender=1.0, age=.78, muscle=.55, weight=.7, height=.55, race=dict(caucasian=.9, african=.05, asian=.05), skin='#d49a7c', weather=.1,
               iris='#3a2a1a', hair=dict(melanin=.85, red=.2, grey=.35), scalp=.02, beard=.0, brows=.012, moustache=.03,
               outfit=dict(shirt='#d8cdb6', vest='#1e1c20', trousers='#4a4036', boots='#1e140c', neckerchief=None, belt='#2a1a10', hat='cowboy', hatcol='#1a1816', badge=True))
TOWNSMAN = dict(gender=1.0, age=.6, muscle=.5, weight=.6, height=.5, race=dict(caucasian=.6, african=.25, asian=.15), skin='#b07c5a', weather=.08,
                iris='#3a2a1a', hair=dict(melanin=.9, red=.1, grey=.2), scalp=.02, beard=.012, brows=.01,
                outfit=dict(shirt='#d8d0bc', vest='#3a3a40', trousers='#2e2a26', boots='#2a1c12', belt='#2a1a10', hat='bowler', hatcol='#2a2622'))
TOWNSWOMAN = dict(gender=0.0, age=.5, muscle=.4, weight=.5, height=.45, race=dict(caucasian=.7, african=.15, asian=.15), skin='#d8a888', weather=.0,
                  iris='#4a5a3a', hair=dict(melanin=.6, red=.6, grey=0.0), scalp=.06, beard=.0, brows=.007,
                  outfit=dict(shirt='#6a3a4a', trousers='#6a3a4a', boots='#2a1c12', dress=True, hat=None))

# facial action units -> named expressions (weights 0..1)
EXPRESSIONS = {
    'neutral': {},
    'smile': {'mouth-corner-puller': .8, 'mouth-upward-retraction': .25, 'eye-left-slit': .25, 'eye-right-slit': .25},
    'grin': {'mouth-corner-puller': 1.0, 'mouth-upward-retraction': .7, 'mouth-open': .2, 'eye-left-slit': .4, 'eye-right-slit': .4},
    'smirk': {'mouth-corner-puller': .55, 'mouth-compression': .3, 'eyebrows-left-down': .3, 'eye-right-slit': .2},
    'angry': {'eyebrows-left-down': 1.0, 'eyebrows-right-down': 1.0, 'eye-left-slit': .45, 'eye-right-slit': .45, 'mouth-compression': .5, 'nose-left-elevation': .4, 'nose-right-elevation': .4},
    'shout': {'eyebrows-left-down': .9, 'eyebrows-right-down': .9, 'mouth-open': .9, 'mouth-upward-retraction': .6, 'mouth-retraction': .4, 'nose-left-elevation': .6, 'nose-right-elevation': .6, 'neck-platysma': .5},
    'fear': {'eyebrows-left-inner-up': 1.0, 'eyebrows-right-inner-up': 1.0, 'eyebrows-left-up': .5, 'eyebrows-right-up': .5, 'eye-left-opened-up': .9, 'eye-right-opened-up': .9, 'mouth-open': .35, 'mouth-retraction': .5, 'neck-platysma': .6},
    'shock': {'eyebrows-left-up': 1.0, 'eyebrows-right-up': 1.0, 'eye-left-opened-up': 1.0, 'eye-right-opened-up': 1.0, 'mouth-open': .7},
    'worry': {'eyebrows-left-inner-up': .9, 'eyebrows-right-inner-up': .9, 'mouth-depression': .4, 'mouth-compression': .3},
    'strain': {'eyebrows-left-down': .8, 'eyebrows-right-down': .8, 'eye-left-closure': .55, 'eye-right-closure': .55, 'mouth-retraction': .8, 'mouth-upward-retraction': .5, 'mouth-open': .15, 'nose-left-elevation': .6, 'nose-right-elevation': .6, 'neck-platysma': .8},
    'determined': {'eyebrows-left-down': .6, 'eyebrows-right-down': .6, 'eye-left-slit': .3, 'eye-right-slit': .3, 'mouth-compression': .7},
    'sad': {'eyebrows-left-inner-up': .7, 'eyebrows-right-inner-up': .7, 'mouth-depression': .7, 'eye-left-slit': .2, 'eye-right-slit': .2},
    'relief': {'eyebrows-left-inner-up': .4, 'eyebrows-right-inner-up': .4, 'mouth-corner-puller': .5, 'eye-left-closure': .4, 'eye-right-closure': .4, 'mouth-open': .15},
    'laugh': {'mouth-corner-puller': 1.0, 'mouth-upward-retraction': .8, 'mouth-open': .6, 'eye-left-closure': .6, 'eye-right-closure': .6, 'eyebrows-left-up': .3, 'eyebrows-right-up': .3},
    'suspicious': {'eyebrows-left-down': .7, 'eyebrows-right-up': .5, 'eye-left-slit': .6, 'eye-right-slit': .3, 'mouth-compression': .4},
    'blink': {'eye-left-closure': 1.0, 'eye-right-closure': 1.0},
}


# ------------------------------------------------------------------ helpers
def _link(o, col=None):
    (col or bpy.context.scene.collection).objects.link(o); return o


def _bone_parent(o, rig, bone):
    bpy.context.view_layer.update(); mw = o.matrix_world.copy(); o.parent = rig; o.parent_type = 'BONE'; o.parent_bone = bone
    bpy.context.view_layer.update(); o.matrix_world = mw


def _vg_weights(obj):
    """vertex index -> {group name: weight}"""
    names = {g.index: g.name for g in obj.vertex_groups}; out = []
    for v in obj.data.vertices: out.append({names[g.group]: g.weight for g in v.groups})
    return out


class Person:
    def __init__(self, cid, p, coll_name='Characters'):
        init()
        self.cid, self.p = cid, p
        col = bpy.data.collections.get(coll_name) or bpy.data.collections.new(coll_name)
        if col.name not in bpy.context.scene.collection.children: bpy.context.scene.collection.children.link(col)
        self.col = col
        mac = TS.get_default_macro_info_dict()
        for k in ('gender', 'age', 'muscle', 'weight', 'height'): mac[k] = p[k]
        mac['race'] = dict(p['race'])
        h = HS.create_human(mask_helpers=True, detailed_helpers=True, extra_vertex_groups=True, feet_on_ground=True, scale=0.1, macro_detail_dict=mac)
        TS.bake_targets(h)
        h.name = cid + '_body'
        self.rig = HS.add_builtin_rig(h, 'mixamo', import_weights=True); self.rig.name = cid + '_rig'
        self.body = h
        for o in (h, self.rig):
            for c in list(o.users_collection): c.objects.unlink(o)
            col.objects.link(o)
        self._measure()
        self._skin(); self._eyes()
        self._clothes()
        if not os.environ.get('NOHAIR'): self._hair()
        else: self.hair_sys = []
        self._expressions()
        sd = h.modifiers.new('subd', 'SUBSURF'); sd.levels = 0; sd.render_levels = 1
        self.rest = {b.name: b.matrix_local.copy() for b in self.rig.data.bones}

    # --- landmarks from MakeHuman joint groups (rest pose, world = object space here)
    def _measure(self):
        h = self.body; vw = _vg_weights(h); pts = {}
        for i, d in enumerate(vw):
            for g in d:
                if g.startswith('joint-') or g.startswith('helper-l-eye') or g.startswith('helper-r-eye') or g in ('body', 'lips'): pts.setdefault(g, []).append(h.data.vertices[i].co)
        self.J = {g: sum(v, Vector()) / len(v) for g, v in pts.items() if g != 'body'}
        print('MOUTH/EYE', self.J.get('lips'), self.J.get('joint-mouth'), (self.J['helper-l-eye'] + self.J['helper-r-eye']) / 2)
        self.vw = vw
        le, re_ = self.J['helper-l-eye'], self.J['helper-r-eye']
        self.eye_c = (le + re_) / 2
        self.eye_r = max((v - le).length for v in pts['helper-l-eye'])
        self.mouth = self.J['lips'] if 'lips' in self.J else self.J.get('joint-mouth', self.eye_c + Vector((0, -.02, -.07)))
        self.lips_w = max(abs(v.x) for v in pts['lips']) if 'lips' in pts else .025
        self.head_top = max(v.z for v in pts['body'])
        self.body_vs = set(i for i, d in enumerate(vw) if 'body' in d)

    def _skin(self):
        h = self.body; h.data.materials.clear()
        h.data.materials.append(skin_mat(self.cid + '_skin', self.p['skin'], weather=self.p.get('weather', 0)))
        for poly in h.data.polygons: poly.use_smooth = True

    def _eyes(self):
        em = eye_mat(self.cid + '_eye', self.p['iris'], self.eye_r * .98)
        self.eyes = []
        for g in ('helper-l-eye', 'helper-r-eye'):
            c = self.J[g]; r = self.eye_r * .98
            bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=r, location=c)
            e = bpy.context.active_object; e.name = self.cid + '_' + g; e.rotation_euler = (math.pi / 2, 0, 0)
            bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
            e.data.materials.append(em)
            for poly in e.data.polygons: poly.use_smooth = True
            for c_ in list(e.users_collection): c_.objects.unlink(e)
            self.col.objects.link(e); _bone_parent(e, self.rig, 'mixamorig:Head'); self.eyes.append(e)

    # --- region masks
    def _region(self, test):
        h = self.body; return [i for i in self.body_vs if test(h.data.vertices[i].co, self.vw[i])]

    def _shell(self, name, idx, offset, mat, thick=.004, solid=True, smooth_n=2, flare=None, noise=.004, edge_relax=25, blob=0, blob_z=None):
        """duplicate the selected body faces as a skinned cloth shell pushed out along the normals"""
        h = self.body; keep = set(idx)
        me = h.data.copy(); o = bpy.data.objects.new(self.cid + '_' + name, me); self.col.objects.link(o)
        o.matrix_world = h.matrix_world
        if me.shape_keys:
            o.shape_key_clear()
        bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table()
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.index not in keep], context='VERTS')
        # drop slivers (verts with a single face) and relax the cut edge into a clean curve
        for _ in range(2):
            lone = [v for v in bm.verts if len(v.link_faces) <= 1]
            if lone: bmesh.ops.delete(bm, geom=lone, context='VERTS')
        bd = [v for v in bm.verts if v.is_boundary]
        nbm = {v: [e.other_vert(v) for e in v.link_edges if e.is_boundary] for v in bd}
        for it in range(edge_relax * 2):                    # Taubin smoothing: clean curve without shrinking
            lam = .5 if it % 2 == 0 else -.53; new_ = {}
            for v, nb in nbm.items():
                if len(nb) == 2: new_[v] = v.co + ((nb[0].co + nb[1].co) * .5 - v.co) * lam
            for v, c in new_.items(): v.co = c
        bm.normal_update()
        for v in bm.verts:
            off = offset(v.co) if callable(offset) else offset
            v.co += v.normal * off
        bm.to_mesh(me); bm.free()
        me.materials.clear(); me.materials.append(mat)
        for poly in me.polygons: poly.use_smooth = True
        for gname in [g.name for g in o.vertex_groups]:
            if gname.startswith(('joint-', 'helper', 'Joint')): o.vertex_groups.remove(o.vertex_groups[gname])
        o.modifiers.clear()
        if smooth_n:
            sm = o.modifiers.new('relax', 'CORRECTIVE_SMOOTH'); sm.iterations = 6; sm.smooth_type = 'LENGTH_WEIGHTED'; sm.rest_source = 'ORCO' if False else 'ORCO'
        if noise:
            tex = bpy.data.textures.new(self.cid + name + '_wr', 'CLOUDS'); tex.noise_scale = .06; tex.noise_depth = 2
            d = o.modifiers.new('wrinkle', 'DISPLACE'); d.texture = tex; d.strength = noise; d.mid_level = .5; d.texture_coords = 'LOCAL'
        if blob:
            bz = blob_z if blob_z is not None else 9.0
            gb = o.vertex_groups.new(name='blob'); gb.add([v.index for v in me.vertices if v.co.z < bz], 1.0, 'REPLACE')
            sm2 = o.modifiers.new('blob', 'LAPLACIANSMOOTH'); sm2.iterations = blob; sm2.lambda_factor = 1.0; sm2.use_volume_preserve = True; sm2.vertex_group = 'blob'
            o.modifiers.move(len(o.modifiers) - 1, 0)
        arm = o.modifiers.new('Armature', 'ARMATURE'); arm.object = self.rig
        if solid:
            s = o.modifiers.new('thick', 'SOLIDIFY'); s.thickness = thick; s.offset = 1.0
        sd = o.modifiers.new('subd', 'SUBSURF'); sd.levels = 0; sd.render_levels = 1
        o.parent = self.rig; o.matrix_parent_inverse = self.rig.matrix_world.inverted()
        return o

    def _dom(self, i):
        d = self.vw[i]; best, bw = '', 0.0
        for g, w in d.items():
            if g.startswith('mixamorig:') and w > bw: best, bw = g[10:], w
        return best

    def _clothes(self):
        P, J, h = self.p['outfit'], self.J, self.body
        ank = (J['joint-l-ankle'].z + J['joint-r-ankle'].z) / 2; knee = (J['joint-l-knee'].z + J['joint-r-knee'].z) / 2
        neck = J.get('joint-neck', self.eye_c - Vector((0, 0, .15))).z
        hip = J.get('joint-pelvis', Vector((0, 0, knee + .42))).z
        D = {i: self._dom(i) for i in self.body_vs}
        V = lambda i: h.data.vertices[i].co
        has = lambda i, *ks: any(k in D[i] for k in ks)
        covered = set()
        shirt_idx = [i for i in self.body_vs if (has(i, 'Spine', 'Shoulder', 'Arm') and not has(i, 'Hand')) or (has(i, 'Hips') and V(i).z > hip - .06) or (has(i, 'Neck') and V(i).z < neck - .02)]
        self.shirt = self._shell('shirt', shirt_idx, .005, cloth_mat(self.cid + '_shirt', P['shirt'], weave=520), thick=.003); covered |= set(shirt_idx)
        boot_top = knee - .1 if not P.get('shoes') else ank + .075      # shoes: low sneakers / loafers instead of boots
        trou_idx = [i for i in self.body_vs if (has(i, 'UpLeg', 'Leg') and not has(i, 'Foot', 'Toe') and V(i).z > boot_top - .03) or (has(i, 'Hips') and V(i).z < hip + .04)]
        self.trousers = self._shell('trousers', trou_idx, lambda c: .012 + .008 * max(0.0, min(1.0, (hip - c.z) / .3)), cloth_mat(self.cid + '_trou', P['trousers'], weave=380, wear=.35), thick=.003); covered |= set(trou_idx)
        boot_idx = [i for i in self.body_vs if has(i, 'Foot', 'Toe') or (has(i, 'Leg') and not has(i, 'UpLeg') and V(i).z < boot_top)]
        self.boots = self._shell('boots', boot_idx, lambda c: .016 if c.z > ank + .04 else .013, cloth_mat(self.cid + '_boot', P['boots'], rough=.45, leather=True, wear=.3), thick=.005, noise=.0015, blob=40, blob_z=ank + .03); covered |= set(boot_idx)
        if P.get('vest'):
            v_idx = [i for i in self.body_vs if ((has(i, 'Spine') and V(i).z < neck - .06) or (has(i, 'Hips') and V(i).z > hip - .02) or (has(i, 'Shoulder') and V(i).z < neck - .03) or (has(i, 'Arm') and not has(i, 'Fore') and V(i).z < neck - .1 and abs(V(i).x) < .17 and V(i).z > hip + .15))
                     and not (V(i).y < 0 and abs(V(i).x) < .018 + .035 * max(0.0, (V(i).z - (hip + .2)) / (neck - hip - .2)))]
            self.vest = self._shell('vest', v_idx, .013, cloth_mat(self.cid + '_vest', P['vest'], rough=.55, leather=True, wear=.35), thick=.005, noise=.002)
        if P.get('dress') or P.get('duster'):
            self._skirt(hip, knee, ank, P)
        if P.get('coat'):
            c_idx = [i for i in self.body_vs if ((has(i, 'Spine', 'Shoulder') or (has(i, 'Arm') and not has(i, 'Hand'))) and V(i).z < neck - .02) or (has(i, 'Hips') and V(i).z > hip - .08)]
            self.coat = self._shell('coat', c_idx, .022, cloth_mat(self.cid + '_coat', P['coat'], rough=.75, weave=300, sheen=.4, wear=.3), thick=.006, noise=.004)
        self.hip_z, self.neck_z = hip, neck
        cm = cloth_mat(self.cid + '_collar', P['shirt'], weave=520, wear=.1)
        c, rx, ry = self._ring_at(neck - .035, .006)
        bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=1, depth=.03, location=c + Vector((0, 0, .012))); cl = bpy.context.active_object; cl.scale = (rx, ry, 1)
        me = cl.data; bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.delete(bm, geom=[f for f in bm.faces if abs(f.normal.z) > .9], context='FACES_ONLY'); bm.to_mesh(me); bm.free()
        for v in me.vertices:
            if v.co.z > 0 and v.co.y < -.5: v.co.z -= .4 * (-v.co.y - .5) / .5     # open V at the front
        cl.data.materials.append(cm); s = cl.modifiers.new('sol', 'SOLIDIFY'); s.thickness = .004; s2 = cl.modifiers.new('sd', 'SUBSURF'); s2.render_levels = 2
        for p_ in me.polygons: p_.use_smooth = True
        self._own(cl, 'Neck')
        if P.get('belt'): self._belt(hip, P)
        if P.get('neckerchief'): self._neckerchief(neck, P['neckerchief'])
        if P.get('badge'): self._badge(neck)
        # hide the skin under the clothes so it can never poke through
        nbr = {}
        for e in h.data.edges:
            a_, b_ = e.vertices; nbr.setdefault(a_, []).append(b_); nbr.setdefault(b_, []).append(a_)
        for _ in range(3):                                   # erode: never hide skin near a garment's edge
            covered = {i for i in covered if all(j in covered for j in nbr.get(i, ()))}
        g = h.vertex_groups.new(name='covered'); g.add(list(covered), 1.0, 'REPLACE')
        mk = h.modifiers.new('hide_covered', 'MASK'); mk.vertex_group = 'covered'; mk.invert_vertex_group = True
        # keep the armature first
        while h.modifiers.find('hide_covered') > 1: bpy.context.view_layer.objects.active = h; bpy.ops.object.modifier_move_up(modifier='hide_covered')

    def _skirt(self, hip, knee, ank, P):
        """long skirt (dress) or duster coat tails: a flared tube from the waist, rigid on the hips"""
        dress = bool(P.get('dress'))
        col = P.get('dresscol', P['shirt']) if dress else P['duster']
        c, rx, ry = self._ring_at(hip + (.06 if dress else .02), .025)
        bot = ank + (.03 if dress else .2)
        bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=1, depth=1, end_fill_type='NOTHING', location=(0, c.y, 0)); s = bpy.context.active_object
        top_z = c.z
        for v in s.data.vertices:
            u = v.co.z + .5          # 0 bottom .. 1 top
            z = bot + (top_z - bot) * u; fl = (1 - u) ** 1.3
            sx = rx + fl * (.22 if dress else .16); sy = ry + fl * (.2 if dress else .12)
            a = math.atan2(v.co.y, v.co.x)
            wav = 1 + .035 * math.sin(a * 9) * (1 - u)
            v.co.x, v.co.y, v.co.z = math.cos(a) * sx * wav, math.sin(a) * sy * wav, z
        if not dress:   # open front
            me = s.data; bm = bmesh.new(); bm.from_mesh(me)
            bmesh.ops.delete(bm, geom=[f for f in bm.faces if all(v.co.y < -ry * .6 and abs(v.co.x) < rx * .45 for v in f.verts) and f.calc_center_median().z < hip - .05], context='FACES'); bm.to_mesh(me); bm.free()
        s.data.materials.append(cloth_mat(self.cid + '_skirt', col, rough=.85, weave=400 if dress else 300, sheen=.4, wear=.25))
        for p_ in s.data.polygons: p_.use_smooth = True
        so = s.modifiers.new('sol', 'SOLIDIFY'); so.thickness = .005; sd = s.modifiers.new('sd', 'SUBSURF'); sd.render_levels = 1
        self._own(s, 'Hips'); self.skirt = s

    def _bonnet(self, hc, col):
        m = cloth_mat(self.cid + '_bonnet', col, weave=700, wear=.1)
        bpy.ops.mesh.primitive_uv_sphere_add(segments=40, ring_count=20, radius=1, location=(0, hc.y + .015, self.head_top - .07)); b = bpy.context.active_object
        b.scale = (.108, .125, .12)
        me = b.data; bm = bmesh.new(); bm.from_mesh(me)
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.y < -.15 and v.co.z < .55 or v.co.z < -.25], context='VERTS'); bm.to_mesh(me); bm.free()
        for v in me.vertices:
            if v.co.y < -.3: v.co.y -= .25 * (v.co.z + .3)       # brim pokes forward
        b.data.materials.append(m)
        for p_ in me.polygons: p_.use_smooth = True
        so = b.modifiers.new('sol', 'SOLIDIFY'); so.thickness = .005
        self.hat = [self._own(b, 'Head')]

    def _own(self, o, bone):
        for c_ in list(o.users_collection): c_.objects.unlink(o)
        self.col.objects.link(o); _bone_parent(o, self.rig, 'mixamorig:' + bone); return o

    def _ring_at(self, z, pad):
        """ellipse fitted to the body cross-section at height z"""
        h = self.body; xs = [h.data.vertices[i].co for i in self.body_vs if abs(h.data.vertices[i].co.z - z) < .012 and abs(h.data.vertices[i].co.x) < .2]
        if not xs: return Vector((0, 0, z)), .15, .11
        cx = 0.0; cy = (max(v.y for v in xs) + min(v.y for v in xs)) / 2
        return Vector((cx, cy, z)), max(abs(v.x) for v in xs) + pad, (max(v.y for v in xs) - min(v.y for v in xs)) / 2 + pad

    def _belt(self, hip, P):
        lm = cloth_mat(self.cid + '_belt', P['belt'], rough=.45, leather=True, wear=.35)
        c, rx, ry = self._ring_at(hip + .05, .022)
        bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=1, depth=.045, location=c); b = bpy.context.active_object; b.scale = (rx, ry, 1)
        b.data.materials.append(lm); s = b.modifiers.new('sol', 'SOLIDIFY'); s.thickness = .006
        bpy.ops.object.mode_set(mode='OBJECT')
        me = b.data; bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.delete(bm, geom=[f for f in bm.faces if abs(f.normal.z) > .9], context='FACES_ONLY'); bm.to_mesh(me); bm.free()
        self._own(b, 'Hips')
        gm = metal_mat(self.cid + '_buckle', '#b8a070', .35)
        bpy.ops.mesh.primitive_cube_add(size=1, location=(0, c.y - ry - .004, hip + .05)); bk = bpy.context.active_object; bk.scale = (.055, .008, .045); bk.data.materials.append(gm)
        bv = bk.modifiers.new('bev', 'BEVEL'); bv.width = .004; bv.segments = 2; self._own(bk, 'Hips')
        # holster + revolver on the right hip
        side = -1
        hx = side * (rx - .005)
        bpy.ops.mesh.primitive_cube_add(size=1, location=(hx, c.y + .01, hip - .04)); hs = bpy.context.active_object; hs.scale = (.03, .07, .17); hs.rotation_euler = (math.radians(-8), 0, 0)
        hs.data.materials.append(lm); bv = hs.modifiers.new('bev', 'BEVEL'); bv.width = .012; bv.segments = 3; self._own(hs, 'Hips')
        self.gun = self.revolver((hx + side * .005, c.y + .0, hip + .08), grip_up=True); self._own(self.gun, 'Hips')
        self.holster = hs

    def revolver(self, loc, grip_up=False):
        """simple six-shooter: barrel, cylinder, frame, wooden grip (single joined object; origin at the grip)"""
        steel = metal_mat(self.cid + '_steel', '#3a3c40', .32); wood = cloth_mat(self.cid + '_grip', '#5a321a', rough=.4, leather=True, wear=.2)
        parts = []
        bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=.0085, depth=.17, location=(0, -.11, .0), rotation=(math.pi / 2, 0, 0)); parts.append((bpy.context.active_object, steel))
        bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=.021, depth=.045, location=(0, -.02, -.004), rotation=(math.pi / 2, 0, 0)); parts.append((bpy.context.active_object, steel))
        bpy.ops.mesh.primitive_cube_add(size=1, location=(0, .015, -.01)); f = bpy.context.active_object; f.scale = (.016, .05, .04); parts.append((f, steel))
        bpy.ops.mesh.primitive_cube_add(size=1, location=(0, .045, -.055)); g = bpy.context.active_object; g.scale = (.02, .03, .08); g.rotation_euler = (math.radians(-20), 0, 0); parts.append((g, wood))
        for o, m in parts:
            o.data.materials.append(m); bv = o.modifiers.new('bev', 'BEVEL'); bv.width = .003; bv.segments = 2
            bpy.context.view_layer.objects.active = o; bpy.ops.object.modifier_apply(modifier='bev')
        bpy.ops.object.select_all(action='DESELECT')
        for o, m in parts: o.select_set(True)
        bpy.context.view_layer.objects.active = parts[0][0]; bpy.ops.object.join(); gun = bpy.context.active_object; gun.name = self.cid + '_revolver'
        for p_ in gun.data.polygons: p_.use_smooth = False
        gun.location = loc
        if grip_up: gun.rotation_euler = (math.radians(95), 0, 0)
        return gun

    def _neckerchief(self, neck, col):
        m = cloth_mat(self.cid + '_nk', col, weave=800, wear=.15)
        c, rx, ry = self._ring_at(neck - .025, .012)
        bpy.ops.mesh.primitive_torus_add(major_radius=1, minor_radius=.018, location=c); t_ = bpy.context.active_object; t_.scale = (rx, ry, 1); t_.data.materials.append(m)
        self._own(t_, 'Neck')
        bpy.ops.mesh.primitive_cone_add(vertices=3, radius1=.07, depth=.006, location=(0, c.y - ry - .008, neck - .075), rotation=(math.pi / 2, 0, math.pi)); tr = bpy.context.active_object
        tr.data.materials.append(m); s = tr.modifiers.new('sd', 'SUBSURF'); s.levels = 1; s.render_levels = 2; self._own(tr, 'Spine2')

    def _badge(self, neck):
        gm = metal_mat(self.cid + '_star', '#d8b860', .22)
        z = neck - .15; x = .085
        bpy.ops.mesh.primitive_circle_add(vertices=10, radius=.035, fill_type='TRIFAN', location=(0, 0, 0)); s = bpy.context.active_object
        for i, v in enumerate(s.data.vertices):
            if v.co.length > 1e-4 and i % 2 == 1: v.co *= .45
        s.rotation_euler = (math.pi / 2, 0, 0); s.location = (x, self._front_y(x, z) - .03, z)
        s.data.materials.append(gm); so = s.modifiers.new('sol', 'SOLIDIFY'); so.thickness = .004; bv = s.modifiers.new('bev', 'BEVEL'); bv.width = .0015
        self._own(s, 'Spine2'); self.badge = s

    def _front_y(self, x, z):
        h = self.body; best = 0.0; bd = 9
        for i in self.body_vs:
            v = h.data.vertices[i].co
            d = abs(v.x - x) + abs(v.z - z) * 1.5
            if d < bd and v.y < 0: bd, best = d, v.y
        return best

    def _hair(self):
        P = self.p; h = self.body; ec, er = self.eye_c, self.eye_r
        hc = Vector((0, ec.y + .045, ec.z + .01))     # skull centre
        def grp(name, idx):
            g = h.vertex_groups.new(name=name); g.add(idx, 1.0, 'REPLACE'); return g
        head = self._region(lambda v, d: (v - hc).length < .16 and v.z > ec.z - .14)
        scalp = [i for i in head if h.data.vertices[i].co.z > ec.z + .035 and (h.data.vertices[i].co.y > ec.y + .03 or h.data.vertices[i].co.z > ec.z + .075) and abs(h.data.vertices[i].co.x) < .085 or (h.data.vertices[i].co.y > ec.y + .07 and h.data.vertices[i].co.z > ec.z - .06 and h.data.vertices[i].co.z > ec.z + .03 - 0)]
        mo = self.mouth
        beard = [i for i in head if (lambda v: v.z < ec.z - .045 and v.y < hc.y + .03 and v.z > mo.z - .085 and not (abs(v.x) < self.lips_w + .004 and abs(v.z - mo.z) < .013) and (v.z < mo.z + .03 or abs(v.x) > .035 or v.z < ec.z - .055))(h.data.vertices[i].co)]
        brows = [i for i in head if (lambda v: ec.z + .018 < v.z < ec.z + .032 + .006 * (1 - abs(abs(v.x) - .04) / .03) and .012 < abs(v.x) < .068 and v.y < ec.y + .01)(h.data.vertices[i].co)]
        hm = hair_mat(self.cid + '_hair', **P['hair'])
        h.data.materials.append(hm); slot = len(h.data.materials)
        self.hair_sys = []
        def ps(name, idx, length, count, children, rough=.0, clump=0.0, tang=0.0, phase=0.0, kink=0.0, width=1.0, normal=1.0, down=0.0):
            if not idx or length <= 0: return
            g = grp(name, idx)
            mod = h.modifiers.new(name, 'PARTICLE_SYSTEM'); s = mod.particle_system; st = s.settings
            st.type = 'HAIR'; st.count = count; st.hair_length = length; st.use_advanced_hair = True
            st.emit_from = 'FACE'; st.use_emit_random = True; st.use_even_distribution = True
            L_ = length / 4.0 / math.sqrt(normal ** 2 + tang ** 2 + down ** 2); st.normal_factor = normal * L_; st.tangent_factor = tang * L_; st.tangent_phase = phase; st.object_align_factor = (0, 0, -down * L_)
            hatted = bool(P['outfit'].get('hat')) and name == 'scalp_hair'
            if hatted: count = int(count * .45)
            st.child_type = 'INTERPOLATED'; st.child_percent = 1; st.rendered_child_count = max(4, int(children * (.5 if hatted else .7))); st.child_length = 1.0; st.display_percentage = 10
            st.roughness_1 = rough; st.roughness_1_size = .05; st.roughness_endpoint = rough * .6; st.clump_factor = clump
            st.kink = 'CURL' if kink else 'NO'; st.kink_amplitude = kink; st.kink_frequency = 6
            st.material_slot = hm.name if hasattr(st, 'material_slot') else st.material_slot
            st.root_radius = 1.0 * width; st.tip_radius = .15 * width; st.radius_scale = .00012; st.use_close_tip = True
            st.display_step = 3; st.render_step = 3
            s.vertex_group_density = name
            self.hair_sys.append(mod)
        ps('scalp_hair', scalp, P['scalp'], 6000, 40, rough=.0015, clump=.15, tang=.9, phase=0.0, down=.35, normal=.12)
        ps('beard_hair', beard, P['beard'], 2600 if P['beard'] < .008 else 7000, 6 if P['beard'] < .008 else 20, rough=.004, clump=.25, kink=.002, tang=.3, down=.8)
        if P.get('moustache'):
            mous = [i for i in head if (lambda v: mo.z + .012 < v.z < mo.z + .022 and abs(v.x) < self.lips_w + .006 and v.y < mo.y + .012)(h.data.vertices[i].co)]
            ps('moustache', mous, P['moustache'] * .6, 2200, 20, rough=.0012, clump=.35, tang=.7, phase=.5, down=.45, normal=.5)
        ps('brow_hair', brows, P['brows'] * .8, 900, 5, rough=.0006, clump=.05, tang=1.0, phase=.25, normal=.25, width=.7)
        # move the particle systems before the subdivision and after the mask so hair follows the skin
        if P['outfit'].get('bandana'):
            band = [i for i in head if h.data.vertices[i].co.z > ec.z + .04 and (h.data.vertices[i].co.y > ec.y + .02 or h.data.vertices[i].co.z > ec.z + .045)]
            self.bandana = self._shell('bandana', band, .012, cloth_mat(self.cid + '_band', P['outfit']['bandana'], weave=700, wear=.2), thick=.003, noise=.002)
        if P['outfit'].get('hat') == 'bonnet':
            self._bonnet(hc, P['outfit'].get('hatcol', '#d8ccb0'))
        if P['outfit'].get('hat') in ('cowboy', 'bowler'):
            self._hat(hc, P['outfit']['hat'], P['outfit'].get('hatcol', '#5a4030'))

    def _hat(self, hc, kind, col):
        top = self.head_top
        m = cloth_mat(self.cid + '_felt', col, rough=.92, weave=1100, sheen=.55, wear=.3)
        crown_h = .13 if kind == 'cowboy' else .11
        bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=1, location=(0, hc.y, top - .045)); cr = bpy.context.active_object
        for v in cr.data.vertices:
            if v.co.z < 0: v.co.z = 0
            if kind == 'cowboy':
                v.co.z = min(v.co.z, .92) ; 
                if v.co.z > .55: v.co.z -= .25 * max(0.0, 1 - abs(v.co.x) * 2.5) * (v.co.z - .55) / .37 * (1 if abs(v.co.y) < .7 else .5)   # center crease
                if v.co.z > .7 and v.co.y < -.5: v.co.x *= .8                     # front pinch
        cr.scale = (.105, .12, crown_h)
        bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=1, depth=.01, location=(0, hc.y, top - .045)); br = bpy.context.active_object
        R = .26 if kind == 'cowboy' else .155; br.scale = (R, R * 1.06, 1)
        for v in br.data.vertices:
            rr = math.hypot(v.co.x, v.co.y)
            if rr > .45:
                u = (rr - .45) / .55
                if kind == 'cowboy': v.co.z += (u ** 2) * (abs(v.co.x) ** 1.5) * .07 - (u ** 2) * max(0.0, -v.co.y) * .015   # sides curl up, front dips
                else: v.co.z += u * u * .012
        bpy.ops.mesh.primitive_torus_add(major_radius=1, minor_radius=.08, location=(0, hc.y, top - .03)); band = bpy.context.active_object; band.scale = (.107, .122, .14)
        band.data.materials.append(cloth_mat(self.cid + '_band', '#2a1a12', rough=.5, leather=True))
        for o in (cr, br):
            o.data.materials.append(m)
            for p_ in o.data.polygons: p_.use_smooth = True
            sm = o.modifiers.new('sd', 'SUBSURF'); sm.levels = 1; sm.render_levels = 2
        so = br.modifiers.new('sol', 'SOLIDIFY'); so.thickness = .006
        self.hat = [self._own(o, 'Head') for o in (cr, br, band)]

    # --- face
    def _expressions(self):
        h = self.body; self.units = []
        if not h.data.shape_keys: h.shape_key_add(name='Basis')
        for f in sorted(os.listdir(UNITS)):
            if not f.endswith('.target.gz'): continue
            try:
                TS.load_target(h, os.path.join(UNITS, f), weight=0.0, name=f.replace('.target.gz', ''))
            except TypeError:
                TS.load_target(h, os.path.join(UNITS, f), weight=0.0)
            self.units.append(f.replace('.target.gz', ''))
        self.keys = {k.name: k for k in h.data.shape_keys.key_blocks}

    def _key(self, unit):
        for n, k in self.keys.items():
            if unit in n: return k
        return None

    def set_expression(self, mix, blink=0.0):
        """mix: {expression name: weight}"""
        tot = {}
        for e, w in mix.items():
            for u, a in EXPRESSIONS[e].items(): tot[u] = tot.get(u, 0.0) + a * w
        for u, a in EXPRESSIONS['blink'].items(): tot[u] = max(tot.get(u, 0.0), a * blink)
        for u in self.units:
            k = self._key(u)
            if k: k.value = min(1.0, tot.get(u, 0.0))

    # --- posing helpers
    def aim(self, name, d):
        """rotate pose bone so its Y axis points along d (armature space), keeping its current roll as far as possible"""
        bpy.context.view_layer.update()
        pb = self.rig.pose.bones['mixamorig:' + name]; M = pb.matrix.copy(); y = M.to_3x3().col[1].normalized()
        q = y.rotation_difference(Vector(d).normalized()); R3 = q.to_matrix() @ M.to_3x3()
        N = R3.to_4x4(); N.translation = M.translation; pb.matrix = N
        bpy.context.view_layer.update()

    def pose_bone(self, name, rot_xyz_deg):
        pb = self.rig.pose.bones['mixamorig:' + name]; pb.rotation_mode = 'XYZ'; pb.rotation_euler = tuple(math.radians(a) for a in rot_xyz_deg)


# ------------------------------------------------------------------ crowd
SKIN = ['#e0b49a', '#d49a7c', '#c08a66', '#a8714f', '#8a5a3c', '#6a4430', '#f0c8b0']
CLOTH_M = ['#d8d0bc', '#b8b0a0', '#8a7a68', '#5a6a7a', '#7a4a3a', '#a89a7a', '#4a4a50', '#e8e0cc', '#6a7a5a']
TROU = ['#3a3d42', '#4a4036', '#2e2a26', '#5a4a3a', '#3a3a30', '#2a2e36']
VEST = ['#2a2420', '#4a3626', '#3a3a40', '#5a4030', '#2e3d4c', None, None]
DRESS = ['#6a3a4a', '#3a4a6a', '#5a6a4a', '#8a6a4a', '#4a3a5a', '#7a5a5a', '#a89880']


def crowd_preset(i):
    """deterministic random townsperson i"""
    r = random.Random(1000 + i * 7)
    woman = r.random() < .35
    race = dict(caucasian=r.uniform(.3, 1), african=r.uniform(0, .5), asian=r.uniform(0, .4))
    p = dict(gender=0.0 if woman else 1.0, age=r.uniform(.3, .95), muscle=r.uniform(.35, .75), weight=r.uniform(.35, .8), height=r.uniform(.35, .65), race=race,
             skin=r.choice(SKIN), weather=r.uniform(0, .12) if not woman else 0.0, iris=r.choice(['#3a2a1a', '#4a6a78', '#4a5a3a', '#2a1a10']),
             hair=dict(melanin=r.uniform(.3, .98), red=r.uniform(0, .5), grey=max(0.0, r.uniform(-.3, 1.0))),
             scalp=r.uniform(.07, .14) if woman else r.uniform(.008, .04), beard=0.0 if woman else r.choice([0, 0, .004, .012, .02, .03]), brows=.007 if woman else .01,
             moustache=0.0 if woman else r.choice([0, 0, 0, .02]))
    o = dict(shirt=r.choice(CLOTH_M), trousers=r.choice(TROU), boots=r.choice(['#2a1c12', '#1e140c', '#3a2414']), belt=None if woman else r.choice([None, '#3a2414']))
    if woman:
        o.update(dress=True, dresscol=r.choice(DRESS), hat=r.choice(['bonnet', None, None]), hatcol=r.choice(['#d8ccb0', '#e8e0d0', '#5a4a3a']))
        o['shirt'] = o['dresscol']
    else:
        o.update(vest=r.choice(VEST), hat=r.choice(['cowboy', 'cowboy', 'bowler', None]), hatcol=r.choice(['#5a4030', '#2a2622', '#8a6a48', '#3a3028', '#a08a6a']))
        if r.random() < .25: o['duster'] = r.choice(['#6a5a48', '#3a3028', '#7a6a50'])
        if r.random() < .3: o['neckerchief'] = r.choice(['#8a2a20', '#2a4a6a', '#d8c8a0'])
    p['outfit'] = o
    return p
