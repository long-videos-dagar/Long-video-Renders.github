"""Dusty Wild West town set: main street running along +Y, building fronts on both sides (x = +-STREET),
boardwalks, porches, signs, props, distant mesas, sky. Interiors for the bank (vault) and the sheriff's office.

Every builder returns objects in the scene; all sizes in metres. Materials are procedural, with Poly Haven
PBR textures swapped in when USE_PH is set (CI)."""
import bpy, bmesh, math, os, random
from mathutils import Vector, Matrix
import sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'real'))
import lib
from realchar import hexc

STREET = 7.0          # half width of the street (building fronts at x = +-STREET)
WALK = 2.2            # boardwalk depth
PH = bool(os.environ.get('USE_PH'))
RNG = random.Random(7)
FRONTS = []
_M = {}


def coll(name):
    c = bpy.data.collections.get(name)
    if not c:
        c = bpy.data.collections.new(name); bpy.context.scene.collection.children.link(c)
    return c


def put(o, c='Town'):
    for cc in list(o.users_collection): cc.objects.unlink(o)
    coll(c).objects.link(o); return o


# ------------------------------------------------------------------ materials
def _nt(m):
    m.use_nodes = True; nt = m.node_tree; nt.nodes.clear(); o = nt.nodes.new('ShaderNodeOutputMaterial'); return nt.nodes, nt.links, o


def wood(name, col='#8a6a48', weather=.5, scale=1.0, planks=True, paint=None):
    key = (name, col, paint)
    if key in _M: return _M[key]
    if PH:
        try:
            m = lib.mat_ph(name, 'wood', 'plank', scale=1.4 * scale, tint=paint or col, avoid=('floor', 'parquet', 'tile', 'herringbone'), bump=.7)
            _M[key] = m; return m
        except Exception as e: lib.log('PH wood failed', e)
    m = bpy.data.materials.new(name); N, L, out = _nt(m)
    b = N.new('ShaderNodeBsdfPrincipled'); L.new(b.outputs[0], out.inputs[0])
    tc = N.new('ShaderNodeTexCoord'); mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (1 * scale, 1 * scale, 14 * scale) if False else (scale, 14 * scale, scale); L.new(tc.outputs['Object'], mp.inputs['Vector'])
    gr = N.new('ShaderNodeTexWave'); gr.wave_type = 'RINGS'; gr.inputs['Scale'].default_value = 3.0; gr.inputs['Distortion'].default_value = 9; gr.inputs['Detail'].default_value = 6; L.new(mp.outputs[0], gr.inputs['Vector'])
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 6; nz.inputs['Detail'].default_value = 10; L.new(tc.outputs['Object'], nz.inputs['Vector'])
    c1 = hexc(col); c2 = tuple(x * .45 for x in c1[:3]) + (1,)
    ramp = N.new('ShaderNodeValToRGB'); ramp.color_ramp.elements[0].color = c2; ramp.color_ramp.elements[1].color = c1; L.new(gr.outputs['Fac'], ramp.inputs['Fac'])
    gray = N.new('ShaderNodeMix'); gray.data_type = 'RGBA'; gray.inputs['Factor'].default_value = weather * .6; L.new(ramp.outputs['Color'], gray.inputs['A']); gray.inputs['B'].default_value = (.32, .3, .28, 1)
    col_out = gray.outputs['Result']
    if paint:
        pm = N.new('ShaderNodeMix'); pm.data_type = 'RGBA'; pm.inputs['B'].default_value = hexc(paint)
        pr = N.new('ShaderNodeMapRange'); pr.inputs['From Min'].default_value = .38; pr.inputs['From Max'].default_value = .52; L.new(nz.outputs['Fac'], pr.inputs['Value']); L.new(pr.outputs[0], pm.inputs['Factor'])
        L.new(col_out, pm.inputs['A']); col_out = pm.outputs['Result']
    L.new(col_out, b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = .82
    if planks:
        pv = N.new('ShaderNodeTexWave'); pv.wave_type = 'BANDS'; pv.bands_direction = 'Z'; pv.wave_profile = 'SAW'; pv.inputs['Scale'].default_value = 4.5; L.new(tc.outputs['Object'], pv.inputs['Vector'])
        gap = N.new('ShaderNodeMapRange'); gap.inputs['From Min'].default_value = .0; gap.inputs['From Max'].default_value = .04; L.new(pv.outputs['Fac'], gap.inputs['Value'])
        mul = N.new('ShaderNodeMix'); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs['Factor'].default_value = 1; L.new(b.inputs['Base Color'].links[0].from_socket, mul.inputs['A']); L.new(gap.outputs[0], mul.inputs['B'])
        L.new(mul.outputs['Result'], b.inputs['Base Color'])
    bp = N.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = .5; bp.inputs['Distance'].default_value = .004; L.new(gr.outputs['Fac'], bp.inputs['Height']); L.new(bp.outputs[0], b.inputs['Normal'])
    _M[key] = m; return m


def ph_or(name, kws, fallback, scale=1.0, tint=None, avoid=(), bump=.6):
    """Poly Haven texture by keywords on CI, procedural fallback locally"""
    key = ('ph', name)
    if key in _M: return _M[key]
    m = None
    if PH:
        try:
            res = os.environ.get('PH_RES', '1k')
            if kws[0].startswith('@'): m = lib.mat_ph(name, aid=kws[0][1:], scale=scale, tint=tint, bump=bump, res=res)
            else: m = lib.mat_ph(name, *kws, scale=scale, tint=tint, avoid=avoid, bump=bump, res=res)
        except Exception as e: lib.log('PH', name, 'failed', e)
    if m is None: m = fallback()
    _M[key] = m; return m


def plain(name, col, rough=.8, metal=0.0, emit=None, strength=0.0, alpha=1.0, transmit=0.0):
    key = (name, col)
    if key in _M: return _M[key]
    m = bpy.data.materials.new(name); N, L, out = _nt(m)
    b = N.new('ShaderNodeBsdfPrincipled'); L.new(b.outputs[0], out.inputs[0])
    b.inputs['Base Color'].default_value = hexc(col); b.inputs['Roughness'].default_value = rough; b.inputs['Metallic'].default_value = metal
    if emit: b.inputs['Emission Color'].default_value = hexc(emit); b.inputs['Emission Strength'].default_value = strength
    if transmit: b.inputs['Transmission Weight'].default_value = transmit; b.inputs['IOR'].default_value = 1.5
    if alpha < 1: b.inputs['Alpha'].default_value = alpha
    _M[key] = m; return m


def dirt(name='dirt'):
    if name in _M: return _M[name]
    if PH:
        try:
            m = lib.mat_ph(name, 'dirt', 'ground', 'sand', scale=.25, avoid=('grass', 'moss', 'snow', 'forest', 'leaves', 'rock_wall'), bump=1.0); _M[name] = m; return m
        except Exception as e: lib.log('PH dirt failed', e)
    m = bpy.data.materials.new(name); N, L, out = _nt(m)
    b = N.new('ShaderNodeBsdfPrincipled'); L.new(b.outputs[0], out.inputs[0])
    tc = N.new('ShaderNodeTexCoord')
    n1 = N.new('ShaderNodeTexNoise'); n1.inputs['Scale'].default_value = .35; n1.inputs['Detail'].default_value = 8; L.new(tc.outputs['Object'], n1.inputs['Vector'])
    n2 = N.new('ShaderNodeTexNoise'); n2.inputs['Scale'].default_value = 9; n2.inputs['Detail'].default_value = 12; L.new(tc.outputs['Object'], n2.inputs['Vector'])
    v = N.new('ShaderNodeTexVoronoi'); v.inputs['Scale'].default_value = 45; L.new(tc.outputs['Object'], v.inputs['Vector'])
    ramp = N.new('ShaderNodeValToRGB'); ramp.color_ramp.elements[0].color = hexc('#6a5038'); ramp.color_ramp.elements[1].color = hexc('#a48460'); L.new(n1.outputs['Fac'], ramp.inputs['Fac'])
    mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs['Factor'].default_value = .35; L.new(ramp.outputs['Color'], mx.inputs['A']); L.new(n2.outputs['Color'], mx.inputs['B'])
    L.new(mx.outputs['Result'], b.inputs['Base Color']); b.inputs['Roughness'].default_value = .95
    h = N.new('ShaderNodeMath'); h.operation = 'ADD'; L.new(n2.outputs['Fac'], h.inputs[0]); L.new(v.outputs['Distance'], h.inputs[1])
    bp = N.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = .8; bp.inputs['Distance'].default_value = .02; L.new(h.outputs[0], bp.inputs['Height']); L.new(bp.outputs[0], b.inputs['Normal'])
    _M[name] = m; return m


# ------------------------------------------------------------------ primitives
_UNIT = {}


def _mesh_from(kind, segs=16):
    """shared unit meshes (cube / cylinder) built without bpy.ops: much faster for thousands of parts"""
    key = (kind, segs)
    if key in _UNIT: return _UNIT[key]
    me = bpy.data.meshes.new(f'unit_{kind}{segs}'); bm = bmesh.new()
    if kind == 'cube': bmesh.ops.create_cube(bm, size=1)
    else: bmesh.ops.create_cone(bm, cap_ends=True, segments=segs, radius1=1, radius2=1, depth=1)
    bm.to_mesh(me); bm.free(); _UNIT[key] = me; return me


def box(name, size, loc, m, rot=(0, 0, 0), bevel=.0, c='Town'):
    me = _mesh_from('cube').copy(); me.name = name
    me.transform(Matrix.Diagonal((*size, 1)))
    me.materials.append(m)
    o = bpy.data.objects.new(name, me); o.location = loc; o.rotation_euler = rot
    if bevel:
        bv = o.modifiers.new('bev', 'BEVEL'); bv.width = bevel; bv.segments = 2; bv.limit_method = 'ANGLE'
    coll(c).objects.link(o); return o


def cyl(name, r, h, loc, m, rot=(0, 0, 0), v=16, c='Town'):
    me = _mesh_from('cyl', v).copy(); me.name = name
    me.transform(Matrix.Diagonal((r, r, h, 1)))
    me.materials.append(m)
    for p in me.polygons: p.use_smooth = True
    o = bpy.data.objects.new(name, me); o.location = loc; o.rotation_euler = rot
    coll(c).objects.link(o); return o


def text(name, s, loc, size, m, rot=(math.pi / 2, 0, 0), extrude=.02, align='CENTER', c='Town', font='serif'):
    cu = bpy.data.curves.new(name, 'FONT'); cu.body = s; cu.size = size; cu.extrude = extrude; cu.align_x = align; cu.align_y = 'CENTER'
    for p in ('/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'):
        if os.path.exists(p): cu.font = bpy.data.fonts.load(p, check_existing=True); break
    o = bpy.data.objects.new(name, cu); o.location = loc; o.rotation_euler = rot; o.data.materials.append(m)
    return put(o, c)


# ------------------------------------------------------------------ building
def window(name, fx, y, z, w, h, side, tm, lit=False, curtain='#c8b89a'):
    """recessed sash window: frame, sill, lintel, glazing bars, glass with reflections, curtains + room glow behind"""
    o = []
    glass = plain('glass', '#a8b8c0', .02, transmit=.0)
    gb = glass.node_tree.nodes.get('Principled BSDF')
    if gb: gb.inputs['Specular IOR Level'].default_value = 1.0; gb.inputs['Base Color'].default_value = (.02, .025, .03, 1)
    inset = .1
    o.append(box(name + '_gl', (.01, w, h), (fx + side * inset, y, z), glass))
    room = plain('room_lit' if lit else 'room', '#3a2a1e', .9, emit='#ffb060' if lit else None, strength=1.5 if lit else 0)
    o.append(box(name + '_room', (.02, w + .2, h + .2), (fx + side * .28, y, z), room))
    cm = plain('curtain_' + curtain, curtain, .9)
    for sy in (-1, 1): o.append(box(name + '_cur', (.02, w * .28, h * .95), (fx + side * (inset + .06), y + sy * w * .36, z), cm))
    for dz in (-h / 2, h / 2):
        o.append(box(name + '_hf', (inset + .04, w + .1, .07), (fx + side * inset / 2, y, z + dz), tm))
    for dy in (-w / 2, w / 2):
        o.append(box(name + '_vf', (inset + .04, .07, h + .1), (fx + side * inset / 2, y + dy, z), tm))
    o.append(box(name + '_mull', (.03, .035, h), (fx + side * (inset - .01), y, z), tm))
    o.append(box(name + '_tr', (.03, w, .035), (fx + side * (inset - .01), y, z + h * .1), tm))
    o.append(box(name + '_sill', (.16, w + .25, .06), (fx - side * .05, y, z - h / 2 - .05), tm, bevel=.01))
    o.append(box(name + '_lint', (.1, w + .3, .14), (fx - side * .03, y, z + h / 2 + .1), tm, bevel=.01))
    return o


def gable_roof(name, cx, y0, depth, width, z0, pitch, m, side):
    """pitched roof running away from the street (ridge along x) with overhang"""
    rise = width / 2 * math.tan(math.radians(pitch))
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    x0, x1 = cx - depth / 2 - .3, cx + depth / 2 + .3; hw = width / 2 + .35
    vs = [bm.verts.new(p) for p in ((x0, y0 - hw, z0), (x1, y0 - hw, z0), (x1, y0, z0 + rise), (x0, y0, z0 + rise), (x0, y0 + hw, z0), (x1, y0 + hw, z0))]
    bm.faces.new((vs[0], vs[1], vs[2], vs[3])); bm.faces.new((vs[3], vs[2], vs[5], vs[4]))
    bm.to_mesh(me); bm.free(); o = bpy.data.objects.new(name, me); me.materials.append(m)
    s = o.modifiers.new('s', 'SOLIDIFY'); s.thickness = .05
    put(o)
    # gable triangles to close the ends
    wm = plain('gable', '#5a4a3a', .9)
    for xx in (cx - depth / 2, cx + depth / 2):
        me2 = bpy.data.meshes.new(name + 'g'); bm = bmesh.new()
        a_ = bm.verts.new((xx, y0 - width / 2, z0)); b_ = bm.verts.new((xx, y0 + width / 2, z0)); c_ = bm.verts.new((xx, y0, z0 + rise - .05)); bm.faces.new((a_, b_, c_))
        bm.to_mesh(me2); bm.free(); g = bpy.data.objects.new(name + 'g', me2); me2.materials.append(ph_or('boardraw', ('@weathered_brown_planks',), lambda: wood('rawboard', '#8a6a48', weather=.8, planks=False), scale=1.0)); put(g)
    fm = plain('fascia', '#3a2a1c', .8)
    for sy in (-1, 1): box(name + '_fascia', (x1 - x0, .04, .18), ((x0 + x1) / 2, y0 + sy * hw, z0 - .02), fm)
    return o, rise


def building(name, x0, y0, width, depth, height, side, sign, wall_col, trim_col, sign_col='#e8dcc0', floors=2, porch=True, false_front=True, door_open=False, kind='wood', balcony=None):
    """side=+1: building on +x side facing -x (towards the street); side=-1 faces +x"""
    objs = []
    rng = random.Random(hash(name) & 0xffff)
    fx = side * STREET                                  # front plane x
    cx = fx + side * depth / 2
    wm = wood(name + '_w', '#8a6a48', paint=wall_col); tm = ph_or('trim_' + trim_col, ('painted', 'wood'), lambda: wood(name + '_t', '#6a4a30', paint=trim_col, planks=False), tint=trim_col, scale=.6, avoid=('floor', 'parquet', 'tile'))
    if balcony is None: balcony = floors > 1 and rng.random() < .6
    FRONTS.append(dict(name=name, fx=side * STREET, y=y0, w=width, side=side, porch=porch, depth=depth))
    # body: sides/back
    if kind == 'brick':
        side_m = ph_or('brick', ('@brick_wall_005',), lambda: plain('brickp', '#8a4a32', .9), scale=1.0, avoid=('white', 'painted', 'floor'))
    elif kind == 'adobe':
        side_m = ph_or('adobe', ('@clay_plaster',), lambda: plain('adobep', '#c8a47a', .95), scale=1.0, tint=wall_col, avoid=('brick', 'tile', 'floor'))
    else:
        side_m = ph_or('wall_' + wall_col, ('@wood_plank_wall',), lambda: wm, scale=1.2, tint=wall_col, avoid=('floor', 'parquet', 'tile', 'herringbone', 'brick'))
    objs.append(box(name + '_body', (depth - 1.1, width - .7, height - .05), (cx, y0, height / 2), plain('core_dark', '#2a2018', .95)))
    objs.append(box(name + '_found', (depth + .1, width + .1, .4), (cx, y0, .1), ph_or('stonefound', ('@rustic_stone_wall_02',), lambda: plain('stone', '#7a7066', .9), scale=.8)))
    # side and back walls: real boards with cut-out windows/doors, frames, sills, curtains and lit rooms
    lit = rng.random() < .5
    wst = {} if kind == 'wood' else dict(style='panel', mat=side_m)
    for sy in (-1, 1):                                   # side walls (outward +-Y), running from the front back
        n_ = Vector((0, sy, 0)); L = depth; cxw = fx + side * depth / 2
        M = wall_frame(n_, Vector((cxw, y0 + sy * width / 2, 0)))
        spec = []
        nwin = max(1, int((L - 2.0) / 3.2))
        for k in range(nwin):
            u = -L / 2 + 1.6 + (k + .5) * (L - 2.4) / nwin
            uu = u * (-side * sy)                        # local Y runs along n x z
            spec.append(('win', uu, 1.6, .85, 1.25))
            if floors > 1: spec.append(('win', uu, 4.4, .8, 1.2))
        if rng.random() < .35 and nwin > 1: spec[0] = ('door', spec[0][1], 0, 1.0, 2.15)
        objs += dress_wall(f'{name}_s{sy}', M, L, height, wall_col, tm, spec, lit, rng, **wst)
    nb = Vector((side, 0, 0)); M = wall_frame(nb, Vector((fx + side * depth, y0, 0)))
    spec = [('door', -width * .25 if rng.random() < .5 else width * .25, 0, 1.0, 2.15)]
    for k in range(max(1, int(width / 3.0))):
        u = (k - (max(1, int(width / 3.0)) - 1) / 2) * 2.8
        if abs(u - spec[0][1]) < 1.3: continue
        spec.append(('win', u, 1.6, .85, 1.25))
        if floors > 1: spec.append(('win', u, 4.4, .8, 1.2))
    objs += dress_wall(f'{name}_b', M, width, height, wall_col, tm, spec, lit, rng, **wst)
    backyard(name, fx + side * depth, y0, width, side, floors, height, rng)
    # roof behind (visible from any angle above eye level)
    roof_m = ph_or('roofshingle', ('@roof_planks',), lambda: plain('shingle', '#4a3a30', .9), scale=.8, avoid=('tile_', 'clay', 'red'))
    if rng.random() < .4: roof_m = ph_or('corrugated', ('@corrugated_iron_02',), lambda: plain('tin', '#7a7470', .5, .7), scale=1.0)
    gable_roof(name + '_roof', cx + side * .2, y0, depth - .4, width, height, rng.uniform(22, 32), roof_m, side)
    # chimney / stovepipe
    if rng.random() < .6:
        cxx = cx + side * rng.uniform(1, depth / 2 - 1); cyy = y0 + rng.uniform(-width / 3, width / 3)
        if rng.random() < .5:
            box(name + '_chim', (.6, .6, 2.6), (cxx, cyy, height + 1.0), ph_or('brick', ('@brick_wall_005',), lambda: plain('brickp', '#8a4a32', .9), avoid=('white', 'painted', 'floor')))
        else:
            cyl(name + '_pipe', .09, 1.8, (cxx, cyy, height + 1.2), plain('iron', '#2a2826', .5, .8), v=12)
    # openings (doors/windows) cut through the facade
    ops_ = [(y0 - .66, y0 + .66, 0, 2.95)]
    for sy in (-1, 1): ops_.append((y0 + sy * width * .3 - .8, y0 + sy * width * .3 + .8, .55, 2.55))
    up = []
    if floors > 1:
        n = max(2, int(width / 2.6))
        for i in range(n):
            yy = y0 + (i - (n - 1) / 2) * width / n
            if balcony and i == n // 2: ops_.append((yy - .55, yy + .55, 3.2, 5.35)); continue
            up.append(yy); ops_.append((yy - .47, yy + .47, 3.68, 5.12))
    ff_h = height + (1.6 if false_front else 0)
    if kind == 'wood':
        objs += clapboard(name, fx, y0, width + (.3 if false_front else 0), ff_h, side, wall_col, ops_)
    else:
        objs += clapboard(name, fx, y0, width + .2, ff_h, side, wall_col, ops_, style='panel', mat=side_m)
        for sy in (-1, 1): objs.append(box(name + '_pil', (.18, .4, ff_h), (fx - side * .09, y0 + sy * (width / 2 - .1), ff_h / 2), ph_or('stonetrim', ('@plaster_stone_wall_01',), lambda: plain('stonet', '#b0a690', .8), scale=.6, avoid=('brick', 'moss'))))
    # the gap between facade and body (reveals) is closed by thin jamb boxes per opening
    jm = plain('jamb', '#3a2a1e', .9)
    for (a_, b_, z0_, z1_) in ops_:
        for yy in (a_, b_): objs.append(box(name + '_jb', (.3, .03, z1_ - z0_), (fx + side * .15, yy, (z0_ + z1_) / 2), jm))
        for zz in (z0_, z1_): objs.append(box(name + '_jh', (.3, b_ - a_, .03), (fx + side * .15, (a_ + b_) / 2, zz), jm))
    if false_front:
        objs.append(box(name + '_cap', (.4, width + .6, .2), (fx - side * .02, y0, ff_h + .1), tm, bevel=.02))
        objs.append(box(name + '_cornice', (.25, width + .4, .12), (fx - side * .05, y0, ff_h - .25), tm, bevel=.02))
        for k in range(int(width / .7)):                      # cornice brackets
            objs.append(box(name + f'_brk{k}', (.18, .08, .22), (fx - side * .08, y0 - width / 2 + .35 + k * .7, ff_h - .42), tm))
        objs.append(box(name + '_pedi', (.25, width * .35, .6), (fx + side * .02, y0, ff_h + .45), tm if kind != 'wood' else wm))
        objs.append(box(name + '_pedic', (.32, width * .4, .1), (fx - side * .02, y0, ff_h + .8), tm, bevel=.02))
    # sign: framed painted board, letters painted on (no mirroring: text faces the street)
    if sign:
        sw = min(width * .82, 1.0 + .42 * len(sign)); sz = height + (.65 if false_front else -.55)
        board = ph_or('signboard', ('painted', 'wood', 'planks'), lambda: plain('signboard_p', sign_col, .9), tint=sign_col, scale=.5, avoid=('floor', 'parquet', 'tile'))
        objs.append(box(name + '_sb', (.08, sw, 1.0), (fx - side * .06, y0, sz), board))
        for dz in (-.5, .5): objs.append(box(name + '_sbf', (.1, sw + .12, .07), (fx - side * .08, y0, sz + dz), tm))
        for dy in (-sw / 2, sw / 2): objs.append(box(name + '_sbv', (.1, .07, 1.07), (fx - side * .08, y0 + dy, sz), tm))
        ink = plain('signpaint', '#2a1a10', .6)
        rotz = -math.pi / 2 if side > 0 else math.pi / 2
        objs.append(text(name + '_sign', sign, (fx - side * .105, y0, sz - .02), .62 if len(sign) < 9 else .5, ink, rot=(math.pi / 2, 0, rotz), extrude=.004))
    # windows
    lit = rng.random() < .5
    for sy in (-1, 1): objs += window(f'{name}_w0{sy}', fx, y0 + sy * width * .3, 1.55, 1.5, 1.9, side, tm, lit, rng.choice(['#c8b89a', '#8a2a2a', '#5a6a4a']))
    for i, yy in enumerate(up):
        objs += window(f'{name}_w1{i}', fx, yy, 4.4, .85, 1.35, side, tm, rng.random() < .4, rng.choice(['#c8b89a', '#e8e0d0', '#8a2a2a']))
        for sy in (-1, 1): objs.append(box(f'{name}_sh{i}{sy}', (.05, .42, 1.4), (fx - side * .06, yy + sy * .66, 4.4), wood(name + '_shut', '#6a5038', paint=trim_col, planks=True)))
    # door (recessed, panelled, with transom); open doors show the dark interior
    dm = ph_or('door_' + trim_col, ('wood', 'door'), lambda: wood(name + '_door', '#5a3a22', paint=trim_col), tint=trim_col, scale=.5, avoid=('floor', 'parquet', 'tile'))
    if not door_open:
        objs.append(box(name + '_door', (.06, 1.25, 2.3), (fx + side * .14, y0, 1.33), dm))
        for dz in (.7, 1.6): objs.append(box(name + '_dpan', (.03, .9, .6), (fx + side * .1, y0, dz + .18), dm, bevel=.01))
        cyl(name + '_knob', .03, .06, (fx + side * .09, y0 + .45, 1.2), plain('brass', '#b8963a', .3, 1.0), rot=(0, math.pi / 2, 0), v=12)
    else:
        objs.append(box(name + '_dark', (.02, 1.4, 2.9), (fx + side * .28, y0, 1.45), plain('interior_dark', '#0a0806', .9)))
    objs.append(box(name + '_trans', (.02, 1.25, .35), (fx + side * .12, y0, 2.68), plain('glass_dark', '#151a1e', .05)))
    for dy in (-.68, .68): objs.append(box(name + '_dj', (.18, .12, 2.95), (fx + side * .05, y0 + dy, 1.62), tm))
    objs.append(box(name + '_dh', (.2, 1.5, .14), (fx + side * .04, y0, 3.12), tm, bevel=.01))
    # boardwalk (individual planks), steps, porch roof on posts with brackets, hitching rail
    if porch:
        objs += boardwalk(name, fx, y0, width + .02, side)
        roof_z = 3.05
        objs.append(corrugated(name + '_proof', (WALK + .35, width + .1), (fx - side * (WALK + .35) / 2, y0, roof_z + .05), side) if rng.random() < .55
                    else box(name + '_proof', (WALK + .35, width + .1, .08), (fx - side * (WALK + .35) / 2, y0, roof_z + .05), roof_m, rot=(0, side * math.radians(-6), 0)))
        objs.append(box(name + '_beam', (.14, width + .1, .2), (fx - side * (WALK - .12), y0, roof_z - .1), tm))
        npost = max(2, int(width / 3.2) + 1)
        for k in range(npost):
            py = y0 - width / 2 + .15 + k * (width - .3) / (npost - 1)
            objs.append(box(name + f'_post{k}', (.15, .15, roof_z), (fx - side * (WALK - .12), py, roof_z / 2 + .1), tm, bevel=.008))
            for sy in (-1, 1):
                if (k == 0 and sy < 0) or (k == npost - 1 and sy > 0): continue
                objs.append(box(name + f'_pb{k}{sy}', (.08, .5, .08), (fx - side * (WALK - .12), py + sy * .2, roof_z - .32), tm, rot=(sy * math.radians(40), 0, 0)))
        if balcony:
            objs.append(box(name + '_bdeck', (WALK + .1, width + .1, .1), (fx - side * (WALK + .1) / 2, y0, roof_z + .15), wood('balc', '#7a5a3a', weather=.6)))
            objs += railing(name + '_brail', fx - side * (WALK - .05), y0, width, roof_z + .2, tm)
            objs.append(box(name + '_bdoor', (.06, 1.1, 2.15), (fx + side * .12, y0, roof_z + 1.25), dm))
        for k, py in enumerate((y0 - width * .25, y0 + width * .25)):
            if rng.random() < .3: continue
            objs.append(box(name + f'_hr{k}', (.09, 2.2, .09), (fx - side * (WALK + .65), py, 1.0), tm, bevel=.01))
            for dy in (-1.0, 1.0): objs.append(box(name + f'_hp{k}{dy}', (.12, .12, 1.05), (fx - side * (WALK + .65), py + dy, .52), tm, bevel=.01))
        # hanging shingle sign under the porch for some shops
        if sign and rng.random() < .5:
            hs = box(name + '_hsign', (.04, .9, .45), (fx - side * (WALK - .3), y0 + width / 2 - .8, roof_z - .7), ph_or('signboard', ('painted', 'wood', 'planks'), lambda: plain('signboard_p', sign_col, .9), tint=sign_col, scale=.5, avoid=('floor',)))
            objs.append(hs)
    return objs


def wall_frame(n, c):
    """matrix taking the local wall frame (outward -X, along +Y, up Z, origin at the wall base centre) to the world"""
    n = Vector(n).normalized(); a = n.cross(Vector((0, 0, 1)))
    return Matrix(((-n.x, a.x, 0, c.x), (-n.y, a.y, 0, c.y), (0, 0, 1, c.z), (0, 0, 0, 1)))


def dress_wall(name, M, width, height, col, tm, spec, lit, rng, style='boards', mat=None):
    """spec: [(kind, u, z, w, h)] in wall coordinates (u along the wall, centred)"""
    ops = []; o = []
    for kind, u, z, w, h in spec:
        if kind == 'win': ops.append((u - w / 2 - .06, u + w / 2 + .06, z - h / 2 - .06, z + h / 2 + .06))
        else: ops.append((u - w / 2 - .06, u + w / 2 + .06, 0, h + .06))
    o += clapboard(name, 0, 0, width, height, 1, col, ops, style=style, mat=mat)
    dm = wood('backdoor', '#5a3a22', weather=.6)
    for kind, u, z, w, h in spec:
        if kind == 'win':
            o += window(f'{name}_w{u:.1f}_{z:.0f}', 0, u, z, w, h, 1, tm, lit and rng.random() < .6, rng.choice(['#c8b89a', '#e8e0d0', '#8a2a2a', '#5a6a4a']))
            if rng.random() < .3:
                for sy in (-1, 1): o.append(box(f'{name}_sh{u:.1f}{sy}', (.05, w * .52, h + .05), (-.06, u + sy * (w * .5 + w * .27), z), wood('shutter', '#6a5038', weather=.5)))
        else:
            o.append(box(f'{name}_d{u:.1f}', (.06, w, h), (.12, u, h / 2 + .03), dm))
            for dz in (.6, 1.45): o.append(box(f'{name}_dp{u:.1f}{dz}', (.03, w * .7, .55), (.08, u, dz), dm, bevel=.01))
            for dy in (-w / 2 - .05, w / 2 + .05): o.append(box(f'{name}_dj{u:.1f}{dy}', (.12, .1, h + .1), (-.02, u + dy, h / 2 + .03), tm))
            o.append(box(f'{name}_dh{u:.1f}', (.14, w + .3, .12), (-.03, u, h + .12), tm))
            o.append(box(f'{name}_step{u:.1f}', (.5, w + .4, .18), (-.25, u, .09), wood('step', '#6a5038', weather=.8)))
    jm = plain('jamb', '#3a2a1e', .9)
    for (a_, b_, z0_, z1_) in ops:
        for yy in (a_, b_): o.append(box(name + '_jb', (.36, .03, z1_ - z0_), (.18, yy, (z0_ + z1_) / 2), jm))
        for zz in (z0_, z1_): o.append(box(name + '_jh', (.36, b_ - a_, .03), (.18, (a_ + b_) / 2, zz), jm))
    for ob in o: ob.matrix_basis = M @ ob.matrix_basis
    return o


def backyard(name, bx, y0, width, side, floors, height, rng):
    """the lived-in back of a building: stairs, lean-to shed, woodpile, rain barrel, outhouse, fence, clothesline"""
    wd = wood('yardwood', '#7a5a3a', weather=.85); wd2 = wood('yardwood2', '#5a4a3a', weather=.9)
    out = lambda d: bx + side * d
    if floors > 1 and rng.random() < .8:                 # exterior stairs to the upper floor along the back wall
        n = 16; ys = y0 - width / 2 + .6
        for k in range(n):
            box(f'{name}_st{k}', (.9, .28, .05), (out(.55), ys + k * .26, .2 + k * .19), wd)
        for dx in (.12, .98): box(f'{name}_str{dx}', (.06, 4.3, .25), (out(dx), ys + 2.0, 1.7), wd, rot=(math.atan2(3.0, 4.1), 0, 0))
        box(f'{name}_land', (1.0, 1.3, .08), (out(.55), ys + 4.6, 3.25), wd)
        for k in range(6): box(f'{name}_rp{k}', (.05, .05, 1.0), (out(1.0), ys + k * .8, .7 + k * .55), wd)
    if rng.random() < .55:                               # lean-to shed
        sw, sd, sh = rng.uniform(2.0, 3.0), rng.uniform(1.6, 2.2), rng.uniform(2.0, 2.4)
        sy = y0 + rng.choice((-1, 1)) * (width / 2 - sw / 2 - .2)
        M = wall_frame(Vector((side, 0, 0)), Vector((out(sd), sy, 0)))
        dress_wall(f'{name}_shed', M, sw, sh, '#6a5038', wd2, [('door', 0, 0, .9, 1.9)], False, rng)
        for s2 in (-1, 1): box(f'{name}_shs{s2}', (sd, .05, sh), (out(sd / 2), sy + s2 * sw / 2, sh / 2), wd2)
        corrugated(f'{name}_shroof', (sd + .3, sw + .3), (out(sd / 2), sy, sh + .25), -side)
    if rng.random() < .7:                                # woodpile
        for k in range(rng.randint(12, 26)):
            r_ = rng.uniform(.06, .1); row = k // 7
            cyl(f'{name}_log{k}', r_, .7, (out(.4 + row * .02), y0 + width / 2 - 1.6 + (k % 7) * .2 + row * .1, .1 + row * .17), wood('logend', '#8a6a48', weather=.5, planks=False), rot=(0, math.pi / 2, 0), v=10)
    if rng.random() < .6: barrel(f'{name}_rb', (out(.45), y0 - width / 2 + .45, 0))
    if rng.random() < .35:                               # outhouse further back
        ox = out(rng.uniform(5, 8)); oy = y0 + rng.uniform(-width / 3, width / 3)
        M = wall_frame(Vector((-side, 0, 0)), Vector((ox, oy, 0)))
        dress_wall(f'{name}_oh', M, 1.2, 2.2, '#7a6048', wd2, [('door', 0, 0, .75, 1.9)], False, rng)
        for s2 in (-1, 1): box(f'{name}_ohs{s2}', (1.2, .04, 2.2), (ox + side * .6, oy + s2 * .6, 1.1), wd2)
        box(f'{name}_ohb', (.04, 1.2, 2.1), (ox + side * 1.2, oy, 1.05), wd2)
        box(f'{name}_ohr', (1.5, 1.5, .06), (ox + side * .6, oy, 2.3), wd2, rot=(0, side * math.radians(-10), 0))
    if rng.random() < .6:                                # picket / rail fence closing the yard
        fl = rng.uniform(6, 10); fy0 = y0 - width / 2
        for k in range(int(width / .35)):
            if rng.random() < .05: continue
            box(f'{name}_pk{k}', (.03, .09, 1.0 + rng.uniform(-.06, .03)), (out(fl), fy0 + k * .35, .5), wd, rot=(rng.gauss(0, .03), rng.gauss(0, .04), 0))
        for zz in (.3, .8): box(f'{name}_fr{zz}', (.04, width, .07), (out(fl - .04), y0, zz), wd)
    if rng.random() < .4:                                # clothesline with laundry
        a_ = Vector((out(3.0), y0 - width / 3, 0)); b_ = Vector((out(3.0), y0 + width / 3, 0))
        for p in (a_, b_): cyl(f'{name}_clp', .04, 2.2, (p.x, p.y, 1.1), wd, v=8)
        box(f'{name}_line', (.01, (b_ - a_).length, .01), ((a_.x + b_.x) / 2, (a_.y + b_.y) / 2, 2.05), plain('rope', '#c8b890', .9))
        for k in range(4):
            c = rng.choice(['#e8e0d0', '#8a2a2a', '#4a5a7a', '#d8c8a0'])
            box(f'{name}_cloth{k}', (.01, rng.uniform(.4, .7), rng.uniform(.5, .8)), (a_.x, a_.y + .5 + k * (b_ - a_).length / 5, 1.7), plain('cloth_' + c, c, .9))


def boardwalk(name, fx, y0, width, side):
    """individual planks laid across the walk on joists, with a step down to the street"""
    o = []
    bw = ph_or('boardwalk', ('@old_wooden_floor_02',), lambda: wood('boardwalk', '#7a5a3a', weather=.7, scale=1.0), scale=.8, avoid=('painted', 'parquet', 'tile', 'herringbone'))
    rng = random.Random(hash(name + 'bw') & 0xffff)
    me = bpy.data.meshes.new(name + '_planks'); bm = bmesh.new()
    y = y0 - width / 2; pw = .15
    while y < y0 + width / 2 - .01:
        dz = rng.uniform(-.006, .006); tl = rng.gauss(0, .004)
        mat = Matrix.Translation((fx - side * WALK / 2, y + pw / 2, .3 + dz)) @ Matrix.Rotation(tl, 4, 'Y') @ Matrix.Diagonal((WALK, pw - .012, .035, 1))
        bmesh.ops.create_cube(bm, size=1, matrix=mat); y += pw
    bm.to_mesh(me); bm.free(); p = bpy.data.objects.new(name + '_planks', me); me.materials.append(bw); put(p); o.append(p)
    o.append(box(name + '_joist', (WALK, width, .26), (fx - side * WALK / 2, y0, .14), plain('underwalk', '#2a2018', .95)))
    o.append(box(name + '_step', (.4, width * .4, .14), (fx - side * (WALK + .2), y0, .07), bw))
    return o


def railing(name, x, y0, width, z, tm):
    o = [box(name + '_top', (.08, width, .08), (x, y0, z + .95), tm, bevel=.01), box(name + '_bot', (.06, width, .06), (x, y0, z + .1), tm)]
    n = int(width / .16)
    me = bpy.data.meshes.new(name + '_bal'); bm = bmesh.new()
    for k in range(n):
        bmesh.ops.create_cube(bm, size=1, matrix=Matrix.Translation((x, y0 - width / 2 + .08 + k * width / n, z + .52)) @ Matrix.Diagonal((.035, .035, .82, 1)))
    bm.to_mesh(me); bm.free(); b = bpy.data.objects.new(name + '_bal', me); me.materials.append(tm); put(b); o.append(b)
    return o


def clapboard(name, fx, y0, width, height, side, col, openings=(), style='boards', mat=None):
    """overlapping horizontal boards with random wear, gaps and the odd tilted/missing board"""
    rng = random.Random(hash(name) & 0xffff); objs = []
    m = mat or ph_or('board_' + col, ('@distressed_painted_planks',), lambda: wood(name + '_cb', '#8a6a48', paint=col, planks=False), scale=1.0, tint=col, avoid=('floor', 'parquet', 'tile', 'herringbone', 'blue', 'green', 'red', 'yellow'))
    m2 = ph_or('boardraw', ('@weathered_brown_planks',), lambda: wood('rawboard', '#8a6a48', weather=.8, planks=False), scale=1.0, avoid=('floor', 'parquet', 'tile', 'herringbone'))
    boards = style == 'boards'
    bh = .2 if boards else .1; z = .25; i = 0
    me = bpy.data.meshes.new(name + '_boards'); bm = bmesh.new()
    while z < height:
        segs = [(-width / 2, width / 2)]
        if boards and rng.random() < .35:            # a butt joint somewhere along the row
            c = rng.uniform(-width * .3, width * .3); segs = [(-width / 2, c - .004), (c + .004, width / 2)]
        for (oy0, oy1, oz0, oz1) in openings:        # cut doors and windows out of the row
            if z + bh <= oz0 or z >= oz1: continue
            ns = []
            for a, b in segs:
                a2, b2 = oy0 - y0, oy1 - y0
                if b <= a2 or a >= b2: ns.append((a, b)); continue
                if a < a2: ns.append((a, a2))
                if b > b2: ns.append((b2, b))
            segs = ns
        for a, b in segs:
            if b - a < .02: continue
            if boards and rng.random() < .015: continue           # missing board
            tilt = (rng.gauss(0, .006) + (rng.random() < .03) * rng.uniform(-.05, .05)) if boards else 0.0
            th = .022 + rng.uniform(0, .006) if boards else .06
            mat = Matrix.Translation((fx - side * (th / 2 + .004), y0 + (a + b) / 2, z + bh / 2)) @ Matrix.Rotation(tilt, 4, 'X') @ Matrix.Rotation(side * (.06 if boards else 0), 4, 'Y') @ Matrix.Diagonal((th, b - a, bh + (.02 if boards else .0), 1))
            r = bmesh.ops.create_cube(bm, size=1, matrix=mat)
            mi = 1 if boards and rng.random() < .12 else 0
            for f in {f for v in r['verts'] for f in v.link_faces}: f.material_index = mi
        z += bh; i += 1
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name + '_boards', me); me.materials.append(m); me.materials.append(m2)
    bv = o.modifiers.new('bev', 'BEVEL'); bv.width = .004; bv.segments = 1
    put(o); objs.append(o)
    # corner trims
    tm = wood('trimwood', '#6a4a30', weather=.6, planks=False)
    for sy in (-1, 1): objs.append(box(name + '_ct', (.08, .12, height), (fx - side * .04, y0 + sy * width / 2, height / 2), tm))
    return objs


def corrugated(name, size, loc, side):
    m = ph_or('corrugated', ('@corrugated_iron_02',), lambda: plain('tin', '#7a7470', .5, .7), scale=1.0, avoid=('rust_coarse',))
    me = bpy.data.meshes.new(name); bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=8, y_segments=int(size[1] * 14), size=.5); bm.to_mesh(me); bm.free()
    me.transform(Matrix.Diagonal((size[0], size[1], 1, 1)))
    o = bpy.data.objects.new(name, me); o.location = loc; coll('Town').objects.link(o)
    for v in o.data.vertices: v.co.z += .018 * math.sin(v.co.y * math.tau * 7) - side * v.co.x * math.tan(math.radians(6))
    o.data.materials.append(m); s = o.modifiers.new('s', 'SOLIDIFY'); s.thickness = .004
    for p in o.data.polygons: p.use_smooth = True
    return put(o)


def barrel(name, loc, m=None, r=.32, h=.9, c='Town'):
    m = m or wood('barrel', '#7a5032', weather=.4, planks=False)
    me = bpy.data.meshes.new(name); bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, segments=24, radius1=r, radius2=r, depth=h)
    bmesh.ops.subdivide_edges(bm, edges=[e for e in bm.edges if abs(e.verts[0].co.z - e.verts[1].co.z) > h * .5], cuts=6)
    for v in bm.verts:
        u = v.co.z / (h / 2); v.co.x *= 1 + .12 * (1 - u * u); v.co.y *= 1 + .12 * (1 - u * u)
    iron = plain('iron', '#2a2826', .5, .8)
    for z in (.12, h - .12, h * .35, h * .65):
        u = (z - h / 2) / (h / 2); rr = r * (1 + .12 * (1 - u * u)) + .004
        res = bmesh.ops.create_cone(bm, cap_ends=False, segments=24, radius1=rr, radius2=rr, depth=.035, matrix=Matrix.Translation((0, 0, z - h / 2)))
        for f in {f for v in res['verts'] for f in v.link_faces}: f.material_index = 1
    bm.to_mesh(me); bm.free(); me.materials.append(m); me.materials.append(iron)
    for p in me.polygons: p.use_smooth = True
    o = bpy.data.objects.new(name, me); o.location = (loc[0], loc[1], loc[2] + h / 2); coll(c).objects.link(o)
    return o


def crate(name, loc, s=.6, rot=0.0, c='Town'):
    return box(name, (s, s, s), (loc[0], loc[1], loc[2] + s / 2), wood('crate', '#a07a50', weather=.3, scale=2.0), rot=(0, 0, rot), bevel=.01, c=c)


def mesas():
    """distant flat-topped mesas and buttes with layered cliffs, 1-4 km away, plus the desert floor"""
    m = ph_or('mesa', ('@cliff_side',), lambda: strata_mat(), scale=25.0, tint='#d08a60', avoid=('moss', 'snow', 'grass', 'ice'), bump=1.0)
    rng = random.Random(3)
    for i in range(22):
        a = i / 22 * math.tau + rng.uniform(-.12, .12)
        if abs(math.cos(a)) > .9 and rng.random() < .5: continue
        w = rng.uniform(150, 600); h = rng.uniform(60, 220); d = rng.uniform(1300, 3800)
        o = mesa_mesh('mesa%d' % i, seed=i)
        o.location = (math.cos(a) * d, math.sin(a) * d, -5); o.scale = (w, w * rng.uniform(.4, .75), h); o.rotation_euler = (0, 0, a + rng.uniform(-.5, .5))
        o.data.materials.append(m); o.data.materials.append(dirt('desert')); coll('Far').objects.link(o)
    me = bpy.data.meshes.new('desert'); bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=2, y_segments=2, size=6000); bm.to_mesh(me); bm.free()
    g = bpy.data.objects.new('desert', me); g.location = (0, 0, -.02); me.materials.append(ph_or('desertsand', ('@aerial_sand',), lambda: dirt('desert'), scale=3.0, avoid=('beach', 'wet', 'snow'))); coll('Far').objects.link(g)


def mesa_mesh(name, seed=0, seg=128, rows=30):
    """eroded mesa: irregular outline with gullies and spurs, stepped cliff bands, a talus apron at the foot and a
    slightly uneven caprock.  Unit size (radius ~1, height 1); material 1 (talus) below the cliffs."""
    from mathutils import noise
    off = Vector((seed * 7.31, seed * 3.17, 0))
    def outline(th):
        p = Vector((math.cos(th), math.sin(th), 0)) * 1.3 + off
        return 1 + .22 * noise.noise(p * 1.0) + .1 * noise.noise(p * 3.3) + .04 * noise.noise(p * 9)
    bm = bmesh.new(); grid = []
    for j in range(rows + 1):
        u = j / rows; row = []
        for i in range(seg):
            th = i / seg * math.tau; r0 = outline(th)
            if u < .3:                                     # talus apron
                z = u / .3 * .32; r = r0 * (1 + .55 * (1 - u / .3) ** 1.6)
            else:
                v = (u - .3) / .7; z = .32 + v * .68
                band = .035 * math.floor(v * 5) / 5 + .02 * math.sin(v * 31 + th * 3)          # strata ledges
                r = r0 * (1 - .1 * v - band) + .05 * noise.noise(Vector((th * 4, v * 6, seed)))
            if j == rows: z += .015 * noise.noise(Vector((math.cos(th) * 3, math.sin(th) * 3, seed)))
            row.append(bm.verts.new((math.cos(th) * r, math.sin(th) * r, z)))
        grid.append(row)
    for j in range(rows):
        for i in range(seg):
            f = bm.faces.new((grid[j][i], grid[j][(i + 1) % seg], grid[j + 1][(i + 1) % seg], grid[j + 1][i]))
            f.material_index = 1 if j < rows * .3 else 0
    top = bm.faces.new(grid[rows]); top.material_index = 0
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    return bpy.data.objects.new(name, me)


def strata_mat():
    m = bpy.data.materials.new('strata'); N, L, out = _nt(m)
    b = N.new('ShaderNodeBsdfPrincipled'); L.new(b.outputs[0], out.inputs[0])
    tc = N.new('ShaderNodeTexCoord'); w = N.new('ShaderNodeTexWave'); w.bands_direction = 'Z'; w.inputs['Scale'].default_value = 6; w.inputs['Distortion'].default_value = 3; w.inputs['Detail'].default_value = 6
    L.new(tc.outputs['Object'], w.inputs['Vector'])
    r = N.new('ShaderNodeValToRGB'); r.color_ramp.elements[0].color = hexc('#9a4a2a'); r.color_ramp.elements[1].color = hexc('#d89a6a'); L.new(w.outputs['Fac'], r.inputs['Fac'])
    L.new(r.outputs['Color'], b.inputs['Base Color']); b.inputs['Roughness'].default_value = .95
    return m


def street(length=120):
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=60, y_subdivisions=200, size=1, location=(0, 20, 0)); g = bpy.context.active_object; g.name = 'street'
    g.scale = (STREET * 2 + 30, length, 1); bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    rng = random.Random(1)
    for v in g.data.vertices:   # ruts and mild bumps
        x = v.co.x
        v.co.z = .03 * math.sin(v.co.y * .7 + x) * .3 + (-.035 if abs(abs(x) - .8) < .25 else 0) + rng.uniform(0, .012)
    g.data.materials.append(ph_or('streetdirt', ('@dirt',), lambda: dirt('street'), scale=3.0, avoid=('grass', 'moss', 'snow', 'asphalt', 'leaves'), bump=1.0)); put(g)
    for p in g.data.polygons: p.use_smooth = True
    return g


def props_street(y0, y1):
    rng = random.Random(11)
    for side in (-1, 1):
        y = y0
        while y < y1:
            fx = side * (STREET - WALK)
            k = rng.random()
            if k < .35: barrel(f'bar{side}{y:.0f}', (fx - side * .5, y, .18))
            elif k < .55:
                crate(f'cr{side}{y:.0f}', (fx - side * .5, y, .18), rot=rng.uniform(0, .4))
                if rng.random() < .5: crate(f'cr2{side}{y:.0f}', (fx - side * .5, y, .78), .45, rot=rng.uniform(0, .6))
            elif k < .65: water_trough((fx - side * .9, y, 0))
            y += rng.uniform(3.5, 7.0)
    # wagon in the street, telegraph poles, water tower
    wagon((-3.5, 34, 0), .3)
    water_tower((-STREET - 10, 70, 0))


def water_trough(loc):
    m = wood('trough', '#6a5038', weather=.6)
    box('trough', (.6, 1.8, .45), (loc[0], loc[1], .4), m)
    box('trough_w', (.5, 1.7, .02), (loc[0], loc[1], .58), plain('water', '#30485a', .05, transmit=.3))
    for dy in (-.75, .75): box('trough_l', (.6, .08, .4), (loc[0], loc[1] + dy, .2), m)


def wagon(loc, rot=0.0):
    m = wood('wagon', '#7a5a3a', weather=.5)
    g = []
    g.append(box('wag_bed', (1.5, 3.2, .5), (loc[0], loc[1], 1.0), m))
    for sx in (-1, 1):
        for sy in (-1, 1):
            bpy.ops.mesh.primitive_torus_add(major_radius=.5, minor_radius=.04, location=(loc[0] + sx * .85, loc[1] + sy * 1.1, .55), rotation=(0, math.pi / 2, 0)); w = bpy.context.active_object; w.data.materials.append(plain('iron', '#2a2826', .5, .8)); put(w); g.append(w)
            for k in range(8):
                a = k / 8 * math.pi
                box('spoke', (.03, .95, .04), (loc[0] + sx * .85, loc[1] + sy * 1.1, .55), m, rot=(a, 0, 0))
    # canvas cover hoops
    cv = plain('canvas', '#d8ccb0', .9)
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=.9, depth=2.8, location=(loc[0], loc[1], 1.25), rotation=(math.pi / 2, 0, 0)); c = bpy.context.active_object
    me = c.data; bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.x < -.05 if False] + [v for v in bm.verts if (c.rotation_euler and v.co.y < -.1)], context='VERTS'); bm.to_mesh(me); bm.free()
    c.scale = (.85, 1, 1); c.data.materials.append(cv); s = c.modifiers.new('s', 'SOLIDIFY'); s.thickness = .01; put(c)


def water_tower(loc):
    m = wood('tower', '#6a5038', weather=.7)
    for sx in (-1, 1):
        for sy in (-1, 1): box('tw_leg', (.25, .25, 9), (loc[0] + sx * 1.6, loc[1] + sy * 1.6, 4.5), m)
    barrel('tw_tank', (loc[0], loc[1], 9), m, r=2.4, h=3.2)
    bpy.ops.mesh.primitive_cone_add(vertices=24, radius1=2.8, depth=1.2, location=(loc[0], loc[1], 12.8)); c = bpy.context.active_object; c.data.materials.append(wood('towerroof', '#4a3a2a', weather=.8)); put(c)


def cactus(loc, h=3.0, seed=0):
    rng = random.Random(seed); m = plain('cactus', '#4a6a3a', .7)
    cyl('cac', .22, h, (loc[0], loc[1], h / 2), m, v=12)
    for k in range(rng.randint(1, 3)):
        sd = rng.choice((-1, 1)); z = rng.uniform(h * .35, h * .6); L = rng.uniform(.6, 1.1)
        cyl('cac_a', .15, .7, (loc[0] + sd * .45, loc[1], z), m, rot=(0, math.pi / 2, 0), v=10)
        cyl('cac_b', .15, L, (loc[0] + sd * .8, loc[1], z + L / 2), m, v=10)


TOWN_BUILDINGS = [
    # (name, side, y, width, depth, height, sign, wall, trim, floors)
    ('saloon', 1, 10.0, 9.0, 12, 6.2, 'SALOON', '#8a4a32', '#e8d8b0', 2),
    ('bank', -1, 12.0, 8.0, 12, 5.6, 'BANK', '#c8b48a', '#3a4a3a', 2),
    ('sheriff', -1, -2.0, 7.0, 10, 4.2, 'SHERIFF', '#7a6a58', '#2a2a2a', 1),
    ('store', 1, 0.0, 8.0, 12, 5.4, 'GENERAL STORE', '#5a7a8a', '#e0d4b8', 2),
    ('hotel', 1, 22.0, 9.0, 12, 7.4, 'HOTEL', '#b88a5a', '#4a2a1a', 2),
    ('barber', -1, 22.5, 6.0, 9, 4.0, 'BARBER', '#d8d0c0', '#8a2a2a', 1),
    ('livery', -1, -12.5, 9.0, 12, 5.0, 'LIVERY', '#6a4a32', '#d8c8a8', 1),
    ('assay', 1, -10.5, 7.0, 10, 4.4, 'ASSAY OFFICE', '#9a8a6a', '#3a3a3a', 1),
    ('telegraph', 1, 31.5, 5.5, 9, 4.2, 'TELEGRAPH', '#a89070', '#2a3a4a', 1),
    ('church', -1, 34.0, 8.0, 14, 5.0, '', '#e8e0d0', '#5a4a3a', 1),
    ('hardware', -1, 1.0 + 0, 0.0, 0, 0, '', '', '', 0),
]


def build_town(detail=True, y_range=(-30, 50)):
    kinds = {'bank': 'brick', 'assay': 'adobe', 'church': 'adobe', 'telegraph': 'wood'}
    for (n, side, y, w, d, h, sign, wall, trim, fl) in TOWN_BUILDINGS:
        if w <= 0 or not (y_range[0] - 10 < y < y_range[1] + 10): continue
        building(n, 0, y, w, d, h, side, sign, wall, trim, floors=fl, door_open=(n == 'bank'), kind=kinds.get(n, 'wood'), false_front=(n != 'church'))
    # filler buildings so the street never has gaps
    rng = random.Random(5)
    for side in (-1, 1):
        y = -40
        while y < 70:
            free = all(not (s == side and abs(y - yy) < ww / 2 + 2.6) for (_, s, yy, ww, *_r) in TOWN_BUILDINGS if ww > 0)
            if free and not (y_range[0] - 15 < y < y_range[1] + 15 and False):
                w = rng.uniform(4.5, 6.5); h = rng.uniform(3.8, 6.8)
                building(f'fill{side}_{y:.0f}', 0, y, w, rng.uniform(8, 11), h, side, rng.choice(['', '', 'FEED & SEED', 'DRY GOODS', 'BOOTS', 'LAUNDRY', 'BAKERY']), rng.choice(['#8a6a48', '#a08060', '#6a5a4a', '#9a7a5a']), rng.choice(['#3a2a1a', '#e0d0b0', '#5a3a2a']), floors=2 if h > 6.0 else 1, false_front=rng.random() < .7, kind=rng.choice(['wood', 'wood', 'wood', 'adobe']))
            y += 5.2
    street()
    if detail: props_street(-30, 60)
    mesas()
    vegetation(float(os.environ.get('VEG', 1.0)))
    if not os.environ.get('NOPHPROPS'): ph_props()
    if detail and not os.environ.get('NODRESS'):
        import dress; dress.dress_street(y_range[0] - 5, y_range[1] + 15)
    for i in range(14):
        rng2 = random.Random(i)
        cactus((rng2.choice((-1, 1)) * rng2.uniform(26, 60), rng2.uniform(-60, 120), 0), rng2.uniform(2, 3.8), i)


# ------------------------------------------------------------------ Poly Haven props (CI)
def ph_props(y0=-35, y1=60):
    if not PH: return
    def M(*ids):
        m = lib.model(list(ids), res=os.environ.get('PH_MODEL_RES', '1k'))
        if not m: return None
        root, objs = m
        cn = 'PHM_' + root.name
        if cn not in bpy.data.collections:                  # one evaluated copy, instanced everywhere (memory stays flat)
            c = bpy.data.collections.new(cn); bpy.context.scene.collection.children.link(c)
            for o in [root] + list(objs):
                for cc in list(o.users_collection): cc.objects.unlink(o)
                c.objects.link(o)
            c.instance_offset = root.location.copy()
            bpy.context.view_layer.layer_collection.children[cn].exclude = True
        return bpy.data.collections[cn]
    def place(col, loc, rot=0.0, scale=1.0):
        if col is None: return None
        e = bpy.data.objects.new(col.name + '_i', None); e.instance_type = 'COLLECTION'; e.instance_collection = col
        e.location = loc; e.rotation_euler = (0, 0, rot); e.scale = (scale,) * 3; coll('Far').objects.link(e); return e
    barrels = [m for m in (M('Barrel_01'), M('Barrel_02'), M('barrel_03'), M('wine_barrel_01')) if m]
    crates = [m for m in (M('wooden_crate_01'), M('wooden_crate_02'), M('wooden_military_crate')) if m]
    seats = [m for m in (M('Rockingchair_01'), M('WoodenChair_01'), M('painted_wooden_bench'), M('folding_wooden_stool'), M('wooden_stool_01')) if m]
    small = [m for m in (M('wooden_bucket_01'), M('wooden_bucket_02'), M('wicker_basket_01'), M('watering_can_metal_01')) if m]
    lantern = M('Lantern_01'); grassm = [m for m in (M('grass_medium_01'), M('grass_medium_02')) if m]
    shrubs = [m for m in (M('shrub_01'), M('shrub_02'), M('shrub_03'), M('wild_rooibos_bush'), M('searsia_burchellii')) if m]
    rocks = [m for m in (M('namaqualand_boulder_02'), M('namaqualand_boulder_04'), M('rock_07'), M('rock_09'), M('stone_01')) if m]
    trees = [m for m in (M('dead_tree_trunk'), M('dead_tree_trunk_02'), M('dead_quiver_trunk'), M('tree_stump_01')) if m]
    rng = random.Random(77)
    for f in FRONTS:
        if not (y0 < f['y'] < y1) or not f['porch']: continue
        s = f['side']; wx = f['fx'] - s * .55
        for k in range(rng.randint(1, 3)):
            yy = f['y'] + rng.uniform(-f['w'] / 2 + .6, f['w'] / 2 - .6)
            if abs(yy - f['y']) < 1.0: continue
            pool = rng.choice([barrels, crates, seats, seats, small])
            if pool: place(rng.choice(pool), (wx - s * rng.uniform(0, .9), yy, .32), rot=rng.uniform(0, math.tau) if pool is not seats else math.radians(90 if s < 0 else -90) + rng.uniform(-.4, .4), scale=1.0)
        if lantern and rng.random() < .6: place(lantern, (f['fx'] - s * .35, f['y'] + .95, 2.15), rot=0, scale=1.0)
        for k in range(4):
            if grassm: place(rng.choice(grassm), (f['fx'] - s * (T_W := WALK) - s * rng.uniform(.0, .3), f['y'] + rng.uniform(-f['w'] / 2, f['w'] / 2), 0), rot=rng.uniform(0, math.tau), scale=rng.uniform(.6, 1.1))
    for k in range(70):
        x = rng.choice((-1, 1)) * rng.uniform(STREET + 9, 80); y = rng.uniform(-70, 130)
        pool = rng.choice([shrubs, shrubs, rocks, trees, grassm])
        if pool: place(rng.choice(pool), (x, y, 0), rot=rng.uniform(0, math.tau), scale=rng.uniform(.7, 1.4))
    for k in range(24):     # in the street margins: stones, odd tufts
        x = rng.choice((-1, 1)) * rng.uniform(STREET - WALK - 1.2, STREET - WALK - .3); y = rng.uniform(y0, y1)
        pool = rng.choice([rocks, grassm, grassm])
        if pool: place(rng.choice(pool), (x, y, 0), rot=rng.uniform(0, math.tau), scale=rng.uniform(.3, .6))


# ------------------------------------------------------------------ vegetation
def grass_mat():
    if 'grass' in _M: return _M['grass']
    m = bpy.data.materials.new('grass'); N, L, out = _nt(m)
    b = N.new('ShaderNodeBsdfPrincipled'); L.new(b.outputs[0], out.inputs[0])
    hi = N.new('ShaderNodeHairInfo'); ob = N.new('ShaderNodeObjectInfo')
    ramp = N.new('ShaderNodeValToRGB'); cr = ramp.color_ramp
    cols = [(0, '#3e4a1e'), (.3, '#6a6a2a'), (.55, '#9a8440'), (.8, '#5a6a2a'), (1, '#a89050')]
    cr.elements[0].position, cr.elements[0].color = cols[0][0], hexc(cols[0][1]); cr.elements[1].position, cr.elements[1].color = cols[-1][0], hexc(cols[-1][1])
    for p, c in cols[1:-1]: e = cr.elements.new(p); e.color = hexc(c)
    L.new(hi.outputs['Random'], ramp.inputs['Fac'])
    tip = N.new('ShaderNodeMix'); tip.data_type = 'RGBA'; L.new(hi.outputs['Intercept'], tip.inputs['Factor']); L.new(ramp.outputs['Color'], tip.inputs['A']); tip.inputs['B'].default_value = hexc('#b8a468')
    L.new(tip.outputs['Result'], b.inputs['Base Color']); b.inputs['Roughness'].default_value = .65
    b.inputs['Subsurface Weight'].default_value = .2; b.inputs['Subsurface Radius'].default_value = (.4, .4, .1)
    _M['grass'] = m; return m


def grass_field(area=(-70, 70, -70, 120), count=120000, children=0, length=.45, clear=None, name='grass'):
    """hair-particle grass over a ground grid, kept off the street, boardwalks and building footprints"""
    clear = clear or []
    x0, x1, y0, y1 = area
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=140, y_subdivisions=190, size=1, location=((x0 + x1) / 2, (y0 + y1) / 2, .0)); g = bpy.context.active_object; g.name = name + '_ground'
    g.scale = (x1 - x0, y1 - y0, 1); bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    rng = random.Random(4)
    for v in g.data.vertices: v.co.z = .02 + rng.uniform(0, .03)
    g.data.materials.append(ph_or('meadow_ground', ('@dry_ground_01',), lambda: dirt('meadowdirt'), scale=2.5, avoid=('snow', 'moss', 'leaves')))
    g.data.materials.append(grass_mat())
    put(g, 'Far')
    vg = g.vertex_groups.new(name='dens'); nz = random.Random(9)
    for v in g.data.vertices:
        x, y = v.co.x + (x0 + x1) / 2, v.co.y + (y0 + y1) / 2
        w = 1.0
        if abs(x) < STREET - WALK + .2: w = max(0.0, (abs(x) - (STREET - WALK - 2.5)) / 2.5) * .35          # sparse tufts at the street edges only
        for (cx, cy, hx, hy) in clear:
            if abs(x - cx) < hx and abs(y - cy) < hy: w = 0.0
        w *= .55 + .45 * (math.sin(x * .21 + nz.random()) * math.sin(y * .17) * .5 + .5)                 # patchy
        if w > 0: vg.add([v.index], min(1.0, w), 'REPLACE')
    tufts = [grass_tuft(k) for k in range(4)]
    tc = coll('GrassTufts'); tc.hide_render = False; tc.instance_offset = (0, 0, -500)
    for tu in tufts:
        for cc in list(tu.users_collection): cc.objects.unlink(tu)
        tc.objects.link(tu); tu.location = (0, 0, -500)
    mod = g.modifiers.new('grass', 'PARTICLE_SYSTEM'); ps = mod.particle_system; st = ps.settings
    st.type = 'EMITTER'; st.count = count; st.frame_start = st.frame_end = -100; st.lifetime = 100000; st.physics_type = 'NO'; st.render_type = 'COLLECTION'; st.instance_collection = tc; st.normal_factor = 0
    st.use_collection_pick_random = True; st.particle_size = 1.0; st.size_random = .5
    st.emit_from = 'FACE'; st.use_emit_random = True; st.use_even_distribution = True
    st.use_rotations = True; st.rotation_mode = 'NOR'; st.phase_factor_random = 2.0; st.rotation_factor_random = .04
    st.use_rotation_instance = True; st.use_scale_instance = True; st.use_global_instance = False
    ps.vertex_group_density = 'dens'
    return g


def grass_tuft(seed, blades=60):
    """one clump of grass blades: curved tapered ribbons with per-blade colour variation"""
    rng = random.Random(seed); me = bpy.data.meshes.new(f'tuft{seed}'); bm = bmesh.new()
    col = bm.loops.layers.color.new('col') if hasattr(bm.loops.layers, 'color') else None
    for b in range(blades):
        a = rng.uniform(0, math.tau); r0 = rng.uniform(0, .07); h = rng.uniform(.18, .6) * (1 if rng.random() > .15 else .5)
        lean = rng.uniform(.1, .6); w = rng.uniform(.004, .009); twist = rng.uniform(0, math.pi)
        bx, by = math.cos(a) * r0, math.sin(a) * r0; dx, dy = math.cos(a), math.sin(a)
        shade = rng.random(); seg = 4; prev = None
        for k in range(seg + 1):
            u = k / seg; z = h * u; off = lean * h * u * u * .6
            px, py = bx + dx * off, by + dy * off; ww = w * (1 - u * .9)
            nx, ny = -math.sin(a + twist) * ww, math.cos(a + twist) * ww
            v1 = bm.verts.new((px + nx, py + ny, z)); v2 = bm.verts.new((px - nx, py - ny, z))
            if prev:
                f = bm.faces.new((prev[0], prev[1], v2, v1))
                if col:
                    for lp in f.loops: lp[col] = (shade, lp.vert.co.z / max(h, 1e-3), 0, 1)
            prev = (v1, v2)
    bm.to_mesh(me); bm.free(); me.transform(Matrix.Rotation(math.pi / 2, 4, 'Y'))   # particles align the instance X axis to the ground normal
    o = bpy.data.objects.new(f'tuft{seed}', me); bpy.context.scene.collection.objects.link(o)
    me.materials.append(tuft_mat())
    for p in me.polygons: p.use_smooth = True
    return o


def tuft_mat():
    if 'tuft' in _M: return _M['tuft']
    m = bpy.data.materials.new('tuft'); N, L, out = _nt(m)
    b = N.new('ShaderNodeBsdfPrincipled'); L.new(b.outputs[0], out.inputs[0])
    at = N.new('ShaderNodeVertexColor'); at.layer_name = 'col'; sp = N.new('ShaderNodeSeparateColor'); L.new(at.outputs['Color'], sp.inputs[0])
    oi = N.new('ShaderNodeObjectInfo'); mx = N.new('ShaderNodeMath'); mx.operation = 'ADD'; L.new(sp.outputs[0], mx.inputs[0]); L.new(oi.outputs['Random'], mx.inputs[1])
    fr = N.new('ShaderNodeMath'); fr.operation = 'FRACT'; L.new(mx.outputs[0], fr.inputs[0])
    ramp = N.new('ShaderNodeValToRGB'); cr = ramp.color_ramp
    cols = [(0, '#2e4214'), (.2, '#4a5e1e'), (.4, '#6e7a2e'), (.6, '#9a8a48'), (.8, '#b49a62'), (1, '#5a6a24')]
    cr.elements[0].position, cr.elements[0].color = cols[0][0], hexc(cols[0][1]); cr.elements[1].position, cr.elements[1].color = cols[-1][0], hexc(cols[-1][1])
    for p, c in cols[1:-1]: e = cr.elements.new(p); e.color = hexc(c)
    L.new(fr.outputs[0], ramp.inputs['Fac'])
    tip = N.new('ShaderNodeMix'); tip.data_type = 'RGBA'; L.new(sp.outputs[1], tip.inputs['Factor']); L.new(ramp.outputs['Color'], tip.inputs['A']); tip.inputs['B'].default_value = hexc('#c0a870')
    dk = N.new('ShaderNodeMix'); dk.data_type = 'RGBA'; dk.blend_type = 'MULTIPLY'; L.new(sp.outputs[1], dk.inputs['Factor']); dk.inputs['Factor'].default_value = 1.0
    root = N.new('ShaderNodeMapRange'); L.new(sp.outputs[1], root.inputs['Value']); root.inputs['To Min'].default_value = .35; root.inputs['From Max'].default_value = .35
    L.new(tip.outputs['Result'], dk.inputs['A']); cmb = N.new('ShaderNodeCombineColor'); L.new(root.outputs[0], cmb.inputs[0]); L.new(root.outputs[0], cmb.inputs[1]); L.new(root.outputs[0], cmb.inputs[2]); L.new(cmb.outputs[0], dk.inputs['B'])
    L.new(dk.outputs['Result'], b.inputs['Base Color']); b.inputs['Roughness'].default_value = .6
    b.inputs['Transmission Weight'].default_value = .0; b.inputs['Subsurface Weight'].default_value = .25; b.inputs['Subsurface Radius'].default_value = (.3, .4, .1); b.inputs['Subsurface Scale'].default_value = .01
    _M['tuft'] = m; return m


def bush_proto():
    """sagebrush: a hair ball of grey-green twigs on a small hidden emitter"""
    if 'bush' in _M: return _M['bush']
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=.18, location=(0, 0, -100)); b = bpy.context.active_object; b.name = 'bush_proto'
    m = bpy.data.materials.new('sage'); N, L, out = _nt(m); bs = N.new('ShaderNodeBsdfPrincipled'); L.new(bs.outputs[0], out.inputs[0])
    hi = N.new('ShaderNodeHairInfo'); ramp = N.new('ShaderNodeValToRGB'); ramp.color_ramp.elements[0].color = hexc('#5a6a50'); ramp.color_ramp.elements[1].color = hexc('#9aa088')
    L.new(hi.outputs['Random'], ramp.inputs['Fac']); L.new(ramp.outputs['Color'], bs.inputs['Base Color']); bs.inputs['Roughness'].default_value = .8
    b.data.materials.append(m)
    mod = b.modifiers.new('tw', 'PARTICLE_SYSTEM'); st = mod.particle_system.settings
    st.type = 'HAIR'; st.count = 160; st.use_advanced_hair = True; st.hair_length = .5; st.normal_factor = .14; st.factor_random = .08
    st.child_type = 'INTERPOLATED'; st.child_percent = 8; st.rendered_child_count = 8; st.clump_factor = .5; st.roughness_1 = .1; st.roughness_2 = .25; st.roughness_2_size = .25; st.roughness_endpoint = .06
    st.kink = 'CURL'; st.kink_amplitude = .02; st.kink_frequency = 3
    st.root_radius = 1; st.tip_radius = .2; st.radius_scale = .004; st.render_step = 3
    b.show_instancer_for_render = False
    put(b, 'Far'); _M['bush'] = b; return b


def scatter(proto, points, scale=(.7, 1.6), coll_='Far'):
    rng = random.Random(len(points))
    for i, p in enumerate(points):
        o = proto.copy(); o.data = proto.data
        for md in o.modifiers: pass
        o.location = p; o.rotation_euler = (0, 0, rng.uniform(0, math.tau)); s = rng.uniform(*scale); o.scale = (s, s, s * rng.uniform(.6, 1.0))
        coll(coll_).objects.link(o)


def rock(name, loc, r, seed):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=r, location=loc); o = bpy.context.active_object; o.name = name
    rng = random.Random(seed)
    for v in o.data.vertices: v.co *= 1 + rng.uniform(-.18, .18); v.co.z *= .6
    d = o.modifiers.new('d', 'DISPLACE'); tx = bpy.data.textures.new(name, 'VORONOI'); tx.noise_scale = r * .8; d.texture = tx; d.strength = r * .25
    o.data.materials.append(ph_or('rockmat', ('@dry_riverbed_rock',), lambda: plain('rockp', '#8a7a6a', .9), scale=.5, avoid=('moss', 'snow', 'cliff_side')))
    for p in o.data.polygons: p.use_smooth = True
    return put(o, 'Far')


def vegetation(detail=1.0):
    clear = []
    for (n, side, y, w, d, h, *_r) in TOWN_BUILDINGS:
        if w > 0: clear.append((side * (STREET + d / 2), y, d / 2 + .6, w / 2 + .6))
    for side in (-1, 1): clear.append((side * (STREET + 6), 15, 6.5, 55))          # behind the fronts (fillers) keep tidy-ish
    clear.append((side * 0, 0, 0, 0))
    grass_field(count=int(45000 * detail), clear=clear[:-1])
    rng = random.Random(21); pts = []
    for i in range(int(160 * detail)):
        x = rng.choice((-1, 1)) * rng.uniform(STREET + 1.0, 60); y = rng.uniform(-60, 110)
        if any(abs(x - cx) < hx and abs(y - cy) < hy for (cx, cy, hx, hy) in clear[:len(TOWN_BUILDINGS)]): continue
        pts.append((x, y, .02))
    scatter(bush_proto(), pts)
    for i in range(40):
        x = rng.choice((-1, 1)) * rng.uniform(STREET + 2, 70); y = rng.uniform(-60, 120)
        rock(f'rock{i}', (x, y, 0), rng.uniform(.15, .9), i)


# ------------------------------------------------------------------ interiors
def bank_interior(c='Interior'):
    """bank hall behind the bank front: x in [-STREET-12, -STREET], y around 12. vault on the back wall."""
    x0 = -STREET; y0 = 12.0; D = 11.5; W = 7.8; H = 3.6
    floor = wood('bankfloor', '#7a5a3a', weather=.2, scale=1.5)
    box('b_floor', (D, W, .05), (x0 - D / 2, y0, .2), floor, c=c)
    wallm = wood('bankwall', '#c8b48a', weather=.3, paint='#8a6a4a')
    box('b_ceiling', (D, W, .1), (x0 - D / 2, y0, H + .2), plain('ceil', '#5a4a3a', .9), c=c)
    for sy in (-1, 1): box('b_side', (D, .12, H), (x0 - D / 2, y0 + sy * W / 2, H / 2 + .2), wallm, c=c)
    bw = box('b_back', (.15, W, H), (x0 - D + .08, y0, H / 2 + .2), plain('bankback', '#3a3a3c', .4, .6), c=c)
    hole = cyl('b_hole', 1.22, 1.0, (x0 - D + .08, y0 + .8, 1.65), None, rot=(0, math.pi / 2, 0), v=48, c=c); hole.hide_render = True; hole.hide_viewport = True
    bo = bw.modifiers.new('hole', 'BOOLEAN'); bo.operation = 'DIFFERENCE'; bo.object = hole
    # the strong room behind the door: stone-dark walls, shelves (the gold bars below sit on them)
    vr = plain('vaultroom', '#4a4440', .7)
    box('v_floor', (2.6, 3.0, .05), (x0 - D - 1.3, y0 + .8, .2), vr, c=c); box('v_ceil', (2.6, 3.0, .05), (x0 - D - 1.3, y0 + .8, 3.0), vr, c=c)
    box('v_back', (.1, 3.0, 2.9), (x0 - D - 2.6, y0 + .8, 1.6), vr, c=c)
    for sy in (-1, 1): box('v_side', (2.6, .1, 2.9), (x0 - D - 1.3, y0 + .8 + sy * 1.5, 1.6), vr, c=c)
    shelf = wood('vshelf', '#5a3a22', weather=.2)
    for r in range(4): box('v_shelf', (.62, 1.4, .04), (x0 - D - .55 + .25, y0 + .9, .84 + r * .38), shelf, c=c)
    # counter with teller bars
    cm = wood('counter', '#5a3a22', weather=.1)
    box('b_counter', (.7, W - 2.2, 1.1), (x0 - 5.2, y0 - 1.0, .75), cm, bevel=.02, c=c)
    brass = plain('brass', '#b8963a', .3, 1.0)
    for k in range(18): cyl('b_bar', .012, 1.0, (x0 - 5.2, y0 - 3.7 + k * .3, 1.8), brass, v=8, c=c)
    # vault: round steel door, open
    steel = plain('steel', '#a4a6ac', .42, .75)
    vx = x0 - D + .2
    bpy.ops.mesh.primitive_torus_add(major_radius=1.33, minor_radius=.13, major_segments=64, minor_segments=12, location=(vx + .02, y0 + .8, 1.65), rotation=(0, math.pi / 2, 0))
    fr = bpy.context.active_object; fr.name = 'vault_frame'; fr.data.materials.append(steel); fr.scale = (1, 1, 1.6)
    for cc in list(fr.users_collection): cc.objects.unlink(fr)
    coll(c).objects.link(fr)
    for p in fr.data.polygons: p.use_smooth = True
    vd = cyl('vault_door', 1.25, .45, (vx + .6, y0 + .8, 1.65), steel, rot=(0, math.pi / 2, 0), v=48, c=c)
    for p in vd.data.polygons: p.use_smooth = abs(p.normal.z) < .5
    bv = vd.modifiers.new('bev', 'BEVEL'); bv.width = .04; bv.segments = 3; bv.limit_method = 'ANGLE'
    for k in range(3):                                           # machined rings on the door face
        rg = torus_ring = None
        bpy.ops.mesh.primitive_torus_add(major_radius=.45 + k * .3, minor_radius=.018, major_segments=48, minor_segments=6, location=(vx + .835, y0 + .8, 1.65), rotation=(0, math.pi / 2, 0))
        rg = bpy.context.active_object; rg.data.materials.append(steel)
        for cc in list(rg.users_collection): cc.objects.unlink(rg)
        coll(c).objects.link(rg); rg.parent = vd; rg.matrix_parent_inverse = vd.matrix_world.inverted()
    hub = cyl('vault_hub', .18, .2, (vx + .9, y0 + .8, 1.65), brass, rot=(0, math.pi / 2, 0), c=c); hub.parent = vd; hub.matrix_parent_inverse = vd.matrix_world.inverted()
    for k in range(3):
        a = k / 3 * math.pi
        sp = box('vault_spoke', (.06, .9, .06), (vx + .95, y0 + .8, 1.65), brass, rot=(a, 0, 0), c=c); sp.parent = vd; sp.matrix_parent_inverse = vd.matrix_world.inverted()
    for k in range(6):
        a = k / 6 * math.tau
        bt = cyl('vault_bolt', .06, .3, (vx + .85, y0 + .8 + math.cos(a) * 1.0, 1.65 + math.sin(a) * 1.0), steel, rot=(0, math.pi / 2, 0), c=c); bt.parent = vd; bt.matrix_parent_inverse = vd.matrix_world.inverted()
    # inside the vault: gold bars on shelves + warm glow
    gold = plain('gold', '#e8b040', .22, 1.0)
    for r in range(4):
        for k in range(10):
            box('goldbar', (.24, .1, .07), (vx - .62 - (k % 2) * .26, y0 + .35 + (k // 2) * .26, .9 + r * .38), gold, bevel=.01, c=c)
    lamp = bpy.data.lights.new('vault_glow', 'POINT'); lamp.energy = 900; lamp.color = (1, .7, .35); lamp.shadow_soft_size = .3
    lo = bpy.data.objects.new('vault_glow', lamp); lo.location = (vx - 1.2, y0 + .8, 2.4); coll(c).objects.link(lo)
    for k, yy in enumerate((y0 - 2.5, y0 + 2.5)):          # moonlight through the front windows + soft bounce
        l = bpy.data.lights.new(f'b_moon{k}', 'AREA'); l.energy = 260; l.size = 1.6; l.color = (.55, .65, 1.0)
        lo = bpy.data.objects.new(f'b_moon{k}', l); lo.location = (x0 - .4, yy, 2.0); lo.rotation_euler = (0, math.radians(-75), 0); coll(c).objects.link(lo)
    l = bpy.data.lights.new('b_fill', 'AREA'); l.energy = 650; l.size = 4; l.color = (1, .8, .6); lo = bpy.data.objects.new('b_fill', l); lo.location = (x0 - D / 2, y0, H); coll(c).objects.link(lo)
    return dict(vault_door=vd, vault_center=Vector((vx + .6, y0 + .8, 1.65)), hall=Vector((x0 - 4, y0, 0.2)))


def sheriff_interior(c='Interior'):
    x0 = -STREET; y0 = -2.0; D = 9.5; W = 6.8; H = 3.4
    box('s_floor', (D, W, .05), (x0 - D / 2, y0, .2), wood('sfloor', '#6a4a30', weather=.4, scale=1.5), c=c)
    wm = wood('swall', '#7a6a58', weather=.6)
    for sy in (-1, 1): box('s_side', (D, .12, H), (x0 - D / 2, y0 + sy * W / 2, H / 2 + .2), wm, c=c)
    box('s_back', (.15, W, H), (x0 - D + .08, y0, H / 2 + .2), wm, c=c)
    box('s_ceiling', (D, W, .1), (x0 - D / 2, y0, H + .2), plain('sceil', '#4a3a2a', .9), c=c)
    dm = wood('desk', '#5a3a22', weather=.2)
    box('s_desk', (1.0, 1.9, .08), (x0 - 4.5, y0 + .6, 1.0), dm, bevel=.01, c=c)
    for sx in (-1, 1):
        for sy in (-1, 1): box('s_dleg', (.08, .08, .8), (x0 - 4.5 + sx * .42, y0 + .6 + sy * .85, .6), dm, c=c)
    # jail cell bars on the left wall
    iron = plain('iron', '#2a2826', .5, .8)
    for k in range(16): cyl('cellbar', .02, H - .2, (x0 - 7.6 + k * .14, y0 - 1.7, H / 2 + .2), iron, v=8, c=c)
    # wanted board with posters
    box('s_board', (.04, 2.0, 1.2), (x0 - .4, y0 + 2.5, 1.9), wood('cork', '#9a7a50', planks=False), c=c)
    lamp = bpy.data.lights.new('s_lamp', 'POINT'); lamp.energy = 220; lamp.color = (1, .68, .35); lamp.shadow_soft_size = .1
    lo = bpy.data.objects.new('s_lamp', lamp); lo.location = (x0 - 4.5, y0 + 1.2, 1.35); coll(c).objects.link(lo)
    glass = plain('lampglass', '#ffd8a0', .05, emit='#ffb860', strength=6)
    cyl('s_lampglass', .07, .2, (x0 - 4.5, y0 + 1.2, 1.2), glass, c=c)
    l = bpy.data.lights.new('s_window', 'AREA'); l.energy = 900; l.size = 1.8; l.color = (1, .92, .8)
    lo = bpy.data.objects.new('s_window', l); lo.location = (x0 - .3, y0 - 1.9, 1.7); lo.rotation_euler = (0, math.radians(-80), math.radians(20)); coll(c).objects.link(lo)
    l = bpy.data.lights.new('s_fill', 'AREA'); l.energy = 150; l.size = 4; lo = bpy.data.objects.new('s_fill', l); lo.location = (x0 - D / 2, y0, H); coll(c).objects.link(lo)
    return dict(desk=Vector((x0 - 4.5, y0 + .6, 1.04)), chair=Vector((x0 - 5.4, y0 + .6, .2)), board=Vector((x0 - .42, y0 + 2.5, 1.9)))


# ------------------------------------------------------------------ sky + light
def sky(mood='day', sun_elev=35.0, sun_az=140.0, strength=1.0):
    sc = bpy.context.scene
    if PH:
        try:
            aid = {'day': 'kloofendal_48d_partly_cloudy_puresky', 'sunset': 'plains_sunset', 'dawn': 'kiara_1_dawn', 'night': 'qwantani_dusk_2_puresky'}[mood]
            lib.world_hdri(aid=aid, strength=strength * (.25 if mood == 'night' else 1.0), rot=0.0, res='2k')
            sun_elev = _align_hdri_sun(sun_az, sun_elev)
        except Exception as e:
            lib.log('PH sky failed', e); _nishita(sun_elev, sun_az, strength, mood)
    else: _nishita(sun_elev, sun_az, strength, mood)
    l = bpy.data.lights.new('sun', 'SUN'); l.angle = math.radians(.6)
    l.energy = {'day': 3.6, 'sunset': 2.6, 'dawn': 2.2, 'night': .25}[mood] * strength
    l.color = {'day': (1, .95, .88), 'sunset': (1, .7, .45), 'dawn': (1, .78, .6), 'night': (.55, .65, 1.0)}[mood]
    o = bpy.data.objects.new('sun', l); sc.collection.objects.link(o)
    o.rotation_euler = (math.radians(90 - sun_elev), 0, math.radians(sun_az))
    sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'; sc.view_settings.exposure = {'day': -.7, 'sunset': -.3, 'dawn': -.3, 'night': 0.0}[mood]
    return o


def _align_hdri_sun(az, elev_fallback):
    """find the sun in the HDRI (brightest region) and rotate the HDRI so it sits at azimuth az; returns its elevation"""
    import numpy as np
    w = bpy.context.scene.world; N = w.node_tree.nodes
    env = next(n for n in N if n.type == 'TEX_ENVIRONMENT'); mp = next(n for n in N if n.type == 'MAPPING')
    im = env.image; W, H = im.size
    px = np.empty(W * H * 4, dtype=np.float32); im.pixels.foreach_get(px); px = px.reshape(H, W, 4)[..., :3].sum(-1)
    s = 8; small = px[:H - H % s, :W - W % s].reshape(H // s, s, W // s, s).mean((1, 3))
    small[: small.shape[0] // 2 - 1] = 0                       # sky half only (row 0 is the bottom in Blender images)
    j, i = np.unravel_index(np.argmax(small), small.shape)
    u = (i + .5) / small.shape[1]; v = (j + .5) / small.shape[0]
    phi_env = (u - .5) * 2 * math.pi                          # Blender equirect: u = atan2(y, -x) / 2pi + .5
    env_xy_ang = math.atan2(math.sin(phi_env), -math.cos(phi_env))
    elev = math.degrees((v - .5) * math.pi)
    phi_world = math.radians(az - 90)
    mp.inputs['Rotation'].default_value[2] = env_xy_ang - phi_world
    lib.log('hdri sun', round(math.degrees(env_xy_ang)), 'elev', round(elev, 1), '-> az', az)
    return elev if 1 < elev < 85 else elev_fallback


def _nishita(elev, az, strength, mood):
    sc = bpy.context.scene; w = bpy.data.worlds.new('sky'); sc.world = w; w.use_nodes = True
    N, L = w.node_tree.nodes, w.node_tree.links; bg = N['Background']
    sk = N.new('ShaderNodeTexSky')
    for t in ('NISHITA', 'MULTIPLE_SCATTERING', 'SINGLE_SCATTERING'):
        try: sk.sky_type = t; break
        except Exception: pass
    try:
        sk.sun_elevation = math.radians(max(1.5, elev if mood != 'night' else 10)); sk.sun_rotation = math.radians(az); sk.altitude = 1200; sk.air_density = 1.4; sk.dust_density = 3.0 if mood != 'night' else 1.0
        sk.sun_disc = False
    except Exception: pass
    # cumulus layer: noise on the view direction projected onto a cloud plane
    tc = N.new('ShaderNodeTexCoord'); sep = N.new('ShaderNodeSeparateXYZ'); L.new(tc.outputs['Generated'], sep.inputs[0])
    dv = N.new('ShaderNodeVectorMath'); dv.operation = 'DIVIDE'; L.new(tc.outputs['Generated'], dv.inputs[0])
    zc = N.new('ShaderNodeMath'); zc.operation = 'MAXIMUM'; L.new(sep.outputs['Z'], zc.inputs[0]); zc.inputs[1].default_value = .04
    cz = N.new('ShaderNodeCombineXYZ'); L.new(zc.outputs[0], cz.inputs['X']); L.new(zc.outputs[0], cz.inputs['Y']); L.new(zc.outputs[0], cz.inputs['Z']); L.new(cz.outputs[0], dv.inputs[1])
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 1.6; nz.inputs['Detail'].default_value = 12; nz.inputs['Roughness'].default_value = .62; L.new(dv.outputs[0], nz.inputs['Vector'])
    cov = N.new('ShaderNodeMapRange'); cov.inputs['From Min'].default_value = .5; cov.inputs['From Max'].default_value = .68; L.new(nz.outputs['Fac'], cov.inputs['Value'])
    hz = N.new('ShaderNodeMapRange'); hz.inputs['From Min'].default_value = .02; hz.inputs['From Max'].default_value = .12; L.new(sep.outputs['Z'], hz.inputs['Value'])
    cm = N.new('ShaderNodeMath'); cm.operation = 'MULTIPLY'; L.new(cov.outputs[0], cm.inputs[0]); L.new(hz.outputs[0], cm.inputs[1])
    ccol = {'day': (1, 1, 1, 1), 'sunset': (1.0, .86, .74, 1), 'dawn': (1, .9, .82, 1), 'night': (.05, .06, .1, 1)}[mood]
    shade = N.new('ShaderNodeMix'); shade.data_type = 'RGBA'; L.new(nz.outputs['Fac'], shade.inputs['Factor']); shade.inputs['A'].default_value = ccol; shade.inputs['B'].default_value = tuple(c * .55 for c in ccol[:3]) + (1,)
    mixc = N.new('ShaderNodeMix'); mixc.data_type = 'RGBA'; L.new(cm.outputs[0], mixc.inputs['Factor']); L.new(sk.outputs[0], mixc.inputs['A']); L.new(shade.outputs['Result'], mixc.inputs['B'])
    L.new(mixc.outputs['Result'], bg.inputs[0]); bg.inputs[1].default_value = strength * (.03 if mood == 'night' else .22)
    if mood == 'night':
        tint = N.new('ShaderNodeMix'); tint.data_type = 'RGBA'; tint.blend_type = 'MULTIPLY'; tint.inputs['Factor'].default_value = 1; tint.inputs['B'].default_value = (.25, .35, .8, 1)
        L.new(mixc.outputs['Result'], tint.inputs['A']); L.new(tint.outputs['Result'], bg.inputs[0])


def haze(density=.0012, col=(1, .85, .65)):
    """thin volumetric dust over the street"""
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 20, 6)); v = bpy.context.active_object; v.name = 'dust'; v.scale = (60, 160, 12)
    m = bpy.data.materials.new('dust'); N, L, out = _nt(m)
    vs = N.new('ShaderNodeVolumePrincipled'); vs.inputs['Density'].default_value = density; vs.inputs['Color'].default_value = (*col, 1); vs.inputs['Anisotropy'].default_value = .5
    L.new(vs.outputs[0], out.inputs['Volume']); v.data.materials.append(m); put(v, 'Far')
    return v


def lantern(name, loc, c='Town', energy=40):
    glass = plain('lanternglass', '#ffd8a0', .05, emit='#ffb050', strength=8)
    iron = plain('iron', '#2a2826', .5, .8)
    cyl(name + '_g', .07, .2, (loc[0], loc[1], loc[2]), glass, c=c); cyl(name + '_t', .09, .03, (loc[0], loc[1], loc[2] + .12), iron, c=c)
    l = bpy.data.lights.new(name, 'POINT'); l.energy = energy; l.color = (1, .68, .35); l.shadow_soft_size = .08
    o = bpy.data.objects.new(name, l); o.location = loc; coll(c).objects.link(o); return o
