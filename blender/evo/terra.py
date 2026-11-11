"""Realistic world toolkit for 'From Dinosaurs to Humans' (DAGAR CLIPS).
Terrain heightfields with slope/height blended Poly Haven PBR textures, dense instanced vegetation and rocks (Poly Haven CC0
models), volcanoes with flowing lava, smoke plumes, a real ocean surface, meteors, god rays.  Everything falls back to
procedural materials when Poly Haven is off (local tests)."""
import math, random, os
import bpy, bmesh
from mathutils import Vector, Matrix, noise
import town as T
import lib

PH = T.PH
_MAT = {}; _PHC = {}


def coll(name='World'):
    return T.coll(name)


# ------------------------------------------------------------------ noise
def fbm(x, y, s=1.0, octaves=5, seed=0, basis='PERLIN_ORIGINAL'):
    return noise.fractal(Vector((x * s + seed * 17.3, y * s - seed * 9.1, seed * .37)), 1.0, 2.0, octaves, noise_basis=basis)


def ridged(x, y, s=1.0, octaves=5, seed=0):
    return noise.ridged_multi_fractal(Vector((x * s + seed * 5.1, y * s + seed * 3.3, seed)), 1.0, 2.0, octaves, 1.0, 2.0)


def smooth01(u): u = max(0.0, min(1.0, u)); return u * u * (3 - 2 * u)


# ------------------------------------------------------------------ PBR texture layers
def _tex_paths(kws, aid=None, res='2k', avoid=()):
    if not PH: return None
    try:
        aid = aid or lib.ph_find('textures', *kws, avoid=avoid)
        return lib.ph_texture(aid, os.environ.get('PH_RES', res))
    except Exception as e:
        lib.log('terra tex fail', kws, e); return None


def layer(kws, col, scale=2.0, tint=None, aid=None, rough=.85, avoid=()):
    """one material layer: Poly Haven maps (or a flat colour + noise when PH is off)"""
    return dict(paths=_tex_paths(kws, aid, avoid=avoid), col=col, scale=scale, tint=tint, rough=rough)


def _layer_nodes(N, L, lay, vec):
    """returns (color_socket, rough_socket_or_value, height_socket_or_None)"""
    p = lay['paths']
    mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (1 / lay['scale'],) * 3; L.new(vec, mp.inputs['Vector'])
    def img(path, nc):
        t = N.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(path, check_existing=True); t.projection = 'BOX'; t.projection_blend = .35
        if nc: t.image.colorspace_settings.name = 'Non-Color'
        L.new(mp.outputs['Vector'], t.inputs['Vector']); return t
    if p and 'diff' in p:
        c = img(p['diff'], False).outputs['Color']
        if lay['tint']:
            mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs['Factor'].default_value = 1
            L.new(c, mx.inputs['A']); mx.inputs['B'].default_value = (*lib.lin(lay['tint']), 1); c = mx.outputs['Result']
        r = img(p['rough'], True).outputs['Color'] if 'rough' in p else lay['rough']
        h = img(p['disp'], True).outputs['Color'] if 'disp' in p else None
        return c, r, h
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 3.0; nz.inputs['Detail'].default_value = 8; L.new(mp.outputs['Vector'], nz.inputs['Vector'])
    cr = N.new('ShaderNodeValToRGB'); L.new(nz.outputs['Fac'], cr.inputs[0])
    base = lib.lin(lay['col']); cr.color_ramp.elements[0].color = (*[c * .7 for c in base], 1); cr.color_ramp.elements[1].color = (*[min(1, c * 1.2) for c in base], 1)
    return cr.outputs['Color'], lay['rough'], nz.outputs['Fac']


def blend_mat(name, base, rules, bump=.35):
    """terrain material: base layer + list of (layer, rule) painted on top.  rule = dict(slope=(a, b)) -> 0..1 as the surface
    normal z goes from a to b (steep rock: slope=(.8, .6)), height=(z0, z1), noise=scale (breaks the edge)"""
    if name in _MAT: return _MAT[name]
    m = bpy.data.materials.new(name); m.use_nodes = True; N, L = m.node_tree.nodes, m.node_tree.links; b = N['Principled BSDF']
    tc = N.new('ShaderNodeTexCoord'); vec = tc.outputs['Object']
    geo = N.new('ShaderNodeNewGeometry'); sep = N.new('ShaderNodeSeparateXYZ'); L.new(geo.outputs['Normal'], sep.inputs[0])
    psep = N.new('ShaderNodeSeparateXYZ'); L.new(geo.outputs['Position'], psep.inputs[0])
    col, rough, hgt = _layer_nodes(N, L, base, vec)
    for lay, rule in rules:
        c2, r2, h2 = _layer_nodes(N, L, lay, vec)
        fac = None
        def ramp(src, a, b_):
            mr = N.new('ShaderNodeMapRange'); L.new(src, mr.inputs[0]); mr.inputs[1].default_value = a; mr.inputs[2].default_value = b_; mr.clamp = True
            return mr.outputs[0]
        if 'slope' in rule: fac = ramp(sep.outputs['Z'], *rule['slope'])
        if 'height' in rule:
            hf = ramp(psep.outputs['Z'], *rule['height'])
            if fac is None: fac = hf
            else: mm = N.new('ShaderNodeMath'); mm.operation = 'MULTIPLY'; L.new(fac, mm.inputs[0]); L.new(hf, mm.inputs[1]); fac = mm.outputs[0]
        if rule.get('noise'):
            nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = rule['noise']; L.new(vec, nz.inputs['Vector'])
            nn = ramp(nz.outputs['Fac'], .42, .58)
            if fac is None: fac = nn
            else: mm = N.new('ShaderNodeMath'); mm.operation = 'MULTIPLY'; L.new(fac, mm.inputs[0]); L.new(nn, mm.inputs[1]); fac = mm.outputs[0]
        if fac is None: continue
        mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; L.new(fac, mx.inputs['Factor']); L.new(col, mx.inputs['A']); L.new(c2, mx.inputs['B']); col = mx.outputs['Result']
        if not isinstance(rough, float) or not isinstance(r2, float):
            mr = N.new('ShaderNodeMix'); mr.data_type = 'FLOAT'; L.new(fac, mr.inputs['Factor'])
            (L.new(rough, mr.inputs['A']) if not isinstance(rough, float) else setattr(mr.inputs['A'], 'default_value', rough))
            (L.new(r2, mr.inputs['B']) if not isinstance(r2, float) else setattr(mr.inputs['B'], 'default_value', r2))
            rough = mr.outputs['Result']
        if h2 is not None:
            if hgt is None: hgt = h2
            else: mh = N.new('ShaderNodeMix'); mh.data_type = 'FLOAT'; L.new(fac, mh.inputs['Factor']); L.new(hgt, mh.inputs['A']); L.new(h2, mh.inputs['B']); hgt = mh.outputs['Result']
    L.new(col, b.inputs['Base Color'])
    if isinstance(rough, float): b.inputs['Roughness'].default_value = rough
    else: L.new(rough, b.inputs['Roughness'])
    if hgt is not None and bump > 0:
        bp = N.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = bump; bp.inputs['Distance'].default_value = .05; L.new(hgt, bp.inputs['Height']); L.new(bp.outputs['Normal'], b.inputs['Normal'])
    _MAT[name] = m; return m


def simple_mat(name, kws, col, scale=1.0, tint=None, rough=.8, **kw):
    key = ('s', name)
    if key in _MAT: return _MAT[key]
    m = blend_mat(name, layer(kws, col, scale, tint, rough=rough, **kw), [])
    _MAT[key] = m; return m


# ------------------------------------------------------------------ terrain
class Terrain:
    """a heightfield: hfn(x, y) -> z.  Builds a grid mesh (denser in the middle where the camera is) and keeps the function
    for placing things on the ground"""
    def __init__(self, name, hfn, size=400.0, res=260, mat=None, center=(0, 0), inner=None):
        self.hfn, self.name = hfn, name
        cx, cy = center
        bm = bmesh.new()
        def ring(sz, rs, z_off=0.0):
            out = bmesh.ops.create_grid(bm, x_segments=rs, y_segments=rs, size=sz / 2)['verts']
            return out
        vs = ring(size, res)
        for v in vs:
            x, y = v.co.x + cx, v.co.y + cy; v.co = Vector((x, y, hfn(x, y)))
        if inner:                                      # a finer patch around the action (no seams: it sits 3 cm above)
            isz, ires = inner
            bm2 = bmesh.new(); vs2 = bmesh.ops.create_grid(bm2, x_segments=ires, y_segments=ires, size=isz / 2)['verts']
            for v in vs2:
                x, y = v.co.x + cx, v.co.y + cy; v.co = Vector((x, y, hfn(x, y) + .03))
            me2 = bpy.data.meshes.new(name + '_fine'); bm2.to_mesh(me2); bm2.free()
            for p in me2.polygons: p.use_smooth = True
            if mat: me2.materials.append(mat)
            o2 = bpy.data.objects.new(name + '_fine', me2); coll().objects.link(o2)
        me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
        for p in me.polygons: p.use_smooth = True
        if mat: me.materials.append(mat)
        self.obj = bpy.data.objects.new(name, me); coll().objects.link(self.obj)

    def z(self, x, y): return self.hfn(x, y)

    def normal(self, x, y, e=.5):
        dx = self.hfn(x + e, y) - self.hfn(x - e, y); dy = self.hfn(x, y + e) - self.hfn(x, y - e)
        return Vector((-dx, -dy, 2 * e)).normalized()


# ------------------------------------------------------------------ Poly Haven models as collection instances
def phc(aid, res='1k'):
    """a Poly Haven model as a hidden collection (instanced everywhere: memory stays flat).  None when PH is off/missing"""
    if not PH or os.environ.get('NOPHPROPS'): return None
    if aid in _PHC: return _PHC[aid]
    _PHC[aid] = None
    try:
        m = lib.model([aid], res=os.environ.get('PH_MODEL_RES', res))
    except Exception as e:
        lib.log('phc fail', aid, e); m = None
    if not m: return None
    root, objs = m; cn = 'PHC_' + aid
    c = bpy.data.collections.new(cn); bpy.context.scene.collection.children.link(c)
    for o in [root] + list(objs):
        for cc in list(o.users_collection): cc.objects.unlink(o)
        c.objects.link(o)
    c.instance_offset = root.location.copy()
    bpy.context.view_layer.layer_collection.children[cn].exclude = True
    _PHC[aid] = c; return c


def inst(c, loc, rot=0.0, scale=1.0, tilt=(0.0, 0.0), name=None):
    e = bpy.data.objects.new(name or (c.name + '_i'), None); e.instance_type = 'COLLECTION'; e.instance_collection = c
    e.location = loc; e.rotation_euler = (tilt[0], tilt[1], rot); e.scale = scale if isinstance(scale, tuple) else (scale,) * 3
    coll().objects.link(e); return e


def scatter(ter, ids, n, area, seed=0, scale=(.8, 1.3), slope_min=.75, zrange=(-1e9, 1e9), avoid=(), sink=.05, align=0.0,
            fallback=None, density_fn=None):
    """instance a mix of models over the terrain.  area = (x0, x1, y0, y1); avoid = [(x, y, r)] kept clear;
    density_fn(x, y) -> 0..1 thins them out (forest edges, clearings)"""
    cs = [c for c in (phc(a) for a in ids) if c is not None]
    r = random.Random(seed); placed = []
    if not cs and fallback is None: return placed
    tries = 0
    while len(placed) < n and tries < n * 8:
        tries += 1
        x = r.uniform(area[0], area[1]); y = r.uniform(area[2], area[3])
        if any((x - ax) ** 2 + (y - ay) ** 2 < ar * ar for ax, ay, ar in avoid): continue
        if density_fn and r.random() > density_fn(x, y): continue
        nrm = ter.normal(x, y)
        if nrm.z < slope_min: continue
        z = ter.z(x, y)
        if not (zrange[0] < z < zrange[1]): continue
        s = r.uniform(*scale)
        tilt = (math.asin(max(-1, min(1, -nrm.y))) * align, math.asin(max(-1, min(1, nrm.x))) * align)
        if cs: placed.append(inst(r.choice(cs), (x, y, z - sink * s), r.uniform(0, math.tau), s, tilt))
        else: placed.append(fallback(x, y, z, s, r))
    return placed


# ------------------------------------------------------------------ fallback vegetation (local tests / missing models)
def fallback_tree(x, y, z, s, r):
    bark = simple_mat('fb_bark', ('bark',), '#4a3a2a', 1.0); leaf = simple_mat('fb_leaf', ('leaves', 'grass'), '#2f5a22', 1.0)
    t = T.cyl('fbtrunk', .2 * s, 3 * s, (x, y, z + 1.5 * s), bark, v=8)
    c = T.lib.sphere('fbcrown', 1.6 * s, (x, y, z + 3.6 * s), leaf, seg=10, rings=6); c.scale = (1, 1, .8)
    return c


def fallback_fern(x, y, z, s, r):
    leaf = simple_mat('fb_fern', ('leaves', 'grass'), '#3a6a28', 1.0)
    o = T.lib.sphere('fbfern', .5 * s, (x, y, z + .2 * s), leaf, seg=8, rings=5); o.scale = (1, 1, .45); return o


def fallback_rock(x, y, z, s, r):
    rk = simple_mat('fb_rock', ('rock',), '#6a6460', 1.0)
    o = T.lib.sphere('fbrock', .6 * s, (x, y, z), rk, seg=8, rings=6); o.scale = (1, r.uniform(.6, 1.2), r.uniform(.4, .8)); return o


# ------------------------------------------------------------------ volcano, lava, smoke
def volcano_h(x, y, cx, cy, r, h, crater=.18, seed=0):
    """height contribution of a volcano cone with eroded gullies and a crater"""
    d = math.hypot(x - cx, y - cy) / r
    if d > 1.6: return 0.0
    a = math.atan2(y - cy, x - cx)
    cone = max(0.0, 1 - d) ** 1.4 * h + max(0.0, 1.6 - d) * .04 * h
    gully = (ridged(math.cos(a) * 3 + seed, math.sin(a) * 3, 1.0, 3, seed) - .8) * .05 * h * (1 - min(1, d))
    crat = -smooth01((crater - d) / crater) * h * .22 if d < crater else 0.0
    return cone + gully + crat


def lava_mat(name='lava', glow=7.0):
    if name in _MAT: return _MAT[name]
    m = bpy.data.materials.new(name); m.use_nodes = True; N, L = m.node_tree.nodes, m.node_tree.links; b = N['Principled BSDF']
    tc = N.new('ShaderNodeTexCoord'); mp = N.new('ShaderNodeMapping'); mp.name = 'flow'; L.new(tc.outputs['Object'], mp.inputs['Vector'])
    vor = N.new('ShaderNodeTexVoronoi'); vor.feature = 'DISTANCE_TO_EDGE'; vor.inputs['Scale'].default_value = 1.6; L.new(mp.outputs['Vector'], vor.inputs['Vector'])
    nz = N.new('ShaderNodeTexNoise'); nz.noise_dimensions = '4D'; nz.name = 'churn'; nz.inputs['Scale'].default_value = 2.2; nz.inputs['Detail'].default_value = 6; L.new(mp.outputs['Vector'], nz.inputs['Vector'])
    mm = N.new('ShaderNodeMath'); mm.operation = 'MULTIPLY'; L.new(vor.outputs['Distance'], mm.inputs[0]); mm.inputs[1].default_value = 6.0
    ad = N.new('ShaderNodeMath'); ad.operation = 'ADD'; L.new(mm.outputs[0], ad.inputs[0]); L.new(nz.outputs['Fac'], ad.inputs[1])
    crust = N.new('ShaderNodeMapRange'); L.new(ad.outputs[0], crust.inputs[0]); crust.inputs[1].default_value = .55; crust.inputs[2].default_value = 1.05
    cr = N.new('ShaderNodeValToRGB'); L.new(crust.outputs[0], cr.inputs[0]); e = cr.color_ramp.elements
    e[0].position = 0.0; e[0].color = (1.0, .9, .35, 1); e[1].position = 1.0; e[1].color = (.02, .015, .012, 1)
    ee = cr.color_ramp.elements.new(.25); ee.color = (1.0, .32, .02, 1); ee2 = cr.color_ramp.elements.new(.55); ee2.color = (.35, .04, .0, 1)
    L.new(cr.outputs['Color'], b.inputs['Base Color']); L.new(cr.outputs['Color'], b.inputs['Emission Color'])
    inv = N.new('ShaderNodeMath'); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0; L.new(crust.outputs[0], inv.inputs[1])
    pw = N.new('ShaderNodeMath'); pw.operation = 'POWER'; L.new(inv.outputs[0], pw.inputs[0]); pw.inputs[1].default_value = 2.2
    st = N.new('ShaderNodeMath'); st.operation = 'MULTIPLY'; L.new(pw.outputs[0], st.inputs[0]); st.inputs[1].default_value = glow
    L.new(st.outputs[0], b.inputs['Emission Strength']); b.inputs['Roughness'].default_value = .75
    _MAT[name] = m; return m


def lava_tick(t, speed=.25):
    """animate every lava material (call from a per-frame update)"""
    for m in bpy.data.materials:
        if not m.name.startswith('lava') or not m.node_tree: continue
        n = m.node_tree.nodes.get('churn'); f = m.node_tree.nodes.get('flow')
        if n: n.inputs['W'].default_value = t * .15
        if f: f.inputs['Location'].default_value = (0, -t * speed, 0)


def lava_river(name, ter, start, steps=160, step=1.2, width=2.5, seed=0, mat=None):
    """a lava flow running downhill from start (follows the steepest descent of the terrain, with a little wander)"""
    r = random.Random(seed); p = Vector((start[0], start[1])); pts = []
    for k in range(steps):
        z = ter.z(p.x, p.y); pts.append(Vector((p.x, p.y, z)))
        g = Vector((ter.z(p.x + .5, p.y) - ter.z(p.x - .5, p.y), ter.z(p.x, p.y + .5) - ter.z(p.x, p.y - .5)))
        if g.length < 1e-4: break
        d = -g.normalized(); a = r.uniform(-.25, .25); d = Vector((d.x * math.cos(a) - d.y * math.sin(a), d.x * math.sin(a) + d.y * math.cos(a)))
        p += d * step
    bm = bmesh.new(); prev = None
    for k, c in enumerate(pts):
        if k + 1 < len(pts): tg = (pts[k + 1] - c)
        else: tg = (c - pts[k - 1])
        tg.z = 0; tg = tg.normalized() if tg.length > 1e-5 else Vector((1, 0, 0)); sd = Vector((-tg.y, tg.x, 0))
        w = width * (1 + .35 * math.sin(k * .7 + seed)) * (1 - .4 * k / len(pts))
        row = []
        for j in range(5):
            u = -1 + j / 2; q = c + sd * (u * w / 2)
            row.append(bm.verts.new((q.x, q.y, ter.z(q.x, q.y) + .08 + .06 * (1 - u * u))))
        if prev:
            for j in range(4): bm.faces.new((prev[j], prev[j + 1], row[j + 1], row[j]))
        prev = row
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for f_ in me.polygons: f_.use_smooth = True
    me.materials.append(mat or lava_mat())
    o = bpy.data.objects.new(name, me); coll().objects.link(o)
    return o, pts


def smoke_plume(name, base, height=120.0, radius=18.0, density=.35, col=(.08, .07, .07), glow=None, seed=0):
    """volumetric ash column: a cylinder volume with a noise density that thins out with height"""
    me = bpy.data.meshes.new(name); bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, segments=24, radius1=radius * .5, radius2=radius * 1.6, depth=height)
    bm.to_mesh(me); bm.free(); o = bpy.data.objects.new(name, me); coll().objects.link(o); o.location = (base[0], base[1], base[2] + height / 2)
    m = bpy.data.materials.new(name + '_vol'); m.use_nodes = True; N, L = m.node_tree.nodes, m.node_tree.links
    out = N['Material Output']; N.remove(N['Principled BSDF'])
    pv = N.new('ShaderNodeVolumePrincipled'); pv.inputs['Color'].default_value = (*col, 1); pv.inputs['Anisotropy'].default_value = .2
    tc = N.new('ShaderNodeTexCoord'); mp = N.new('ShaderNodeMapping'); mp.name = 'rise'; L.new(tc.outputs['Object'], mp.inputs['Vector'])
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = .06 * 18 / radius; nz.inputs['Detail'].default_value = 7; nz.inputs['Roughness'].default_value = .62
    L.new(mp.outputs['Vector'], nz.inputs['Vector'])
    gr = N.new('ShaderNodeMapRange'); L.new(nz.outputs['Fac'], gr.inputs[0]); gr.inputs[1].default_value = .45; gr.inputs[2].default_value = .75
    sep = N.new('ShaderNodeSeparateXYZ'); L.new(tc.outputs['Generated'], sep.inputs[0])
    fall = N.new('ShaderNodeMapRange'); L.new(sep.outputs['Z'], fall.inputs[0]); fall.inputs[1].default_value = 1.0; fall.inputs[2].default_value = .2
    mul = N.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; L.new(gr.outputs[0], mul.inputs[0]); L.new(fall.outputs[0], mul.inputs[1])
    # soft edges: fade out towards the cone wall (radial distance in generated coords) so it reads as a billowing column
    gx = N.new('ShaderNodeMath'); gx.operation = 'SUBTRACT'; L.new(sep.outputs['X'], gx.inputs[0]); gx.inputs[1].default_value = .5
    gy = N.new('ShaderNodeMath'); gy.operation = 'SUBTRACT'; L.new(sep.outputs['Y'], gy.inputs[0]); gy.inputs[1].default_value = .5
    cv = N.new('ShaderNodeCombineXYZ'); L.new(gx.outputs[0], cv.inputs[0]); L.new(gy.outputs[0], cv.inputs[1])
    ln = N.new('ShaderNodeVectorMath'); ln.operation = 'LENGTH'; L.new(cv.outputs[0], ln.inputs[0])
    rad = N.new('ShaderNodeMapRange'); L.new(ln.outputs['Value'], rad.inputs[0]); rad.inputs[1].default_value = .5; rad.inputs[2].default_value = .12
    mr = N.new('ShaderNodeMath'); mr.operation = 'MULTIPLY'; L.new(mul.outputs[0], mr.inputs[0]); L.new(rad.outputs[0], mr.inputs[1])
    mul2 = N.new('ShaderNodeMath'); mul2.operation = 'MULTIPLY'; L.new(mr.outputs[0], mul2.inputs[0]); mul2.inputs[1].default_value = density
    L.new(mul2.outputs[0], pv.inputs['Density'])
    if glow:
        gl = N.new('ShaderNodeMapRange'); L.new(sep.outputs['Z'], gl.inputs[0]); gl.inputs[1].default_value = .25; gl.inputs[2].default_value = 0.0
        gm = N.new('ShaderNodeMath'); gm.operation = 'MULTIPLY'; L.new(gl.outputs[0], gm.inputs[0]); gm.inputs[1].default_value = glow
        L.new(gm.outputs[0], pv.inputs['Emission Strength']); pv.inputs['Emission Color'].default_value = (1, .35, .08, 1)
    L.new(pv.outputs[0], out.inputs['Volume']); me.materials.append(m)
    return o


def smoke_tick(t, speed=4.0):
    for m in bpy.data.materials:
        if m.node_tree and m.name.endswith('_vol'):
            r = m.node_tree.nodes.get('rise')
            if r: r.inputs['Location'].default_value = (0, 0, -t * speed)


# ------------------------------------------------------------------ ocean + sky helpers
def ocean(name, size=600.0, loc=(0, 0, 0), wave=1.2, choppy=1.2, res=12, col='#0e3a48', murk='#1a3a30', foam=True):
    me = bpy.data.meshes.new(name); o = bpy.data.objects.new(name, me); coll().objects.link(o); o.location = loc
    md = o.modifiers.new('ocean', 'OCEAN'); md.geometry_mode = 'GENERATE'; md.size = size / 60; md.spatial_size = int(size / md.size) if False else 60
    md.repeat_x = md.repeat_y = 1; md.resolution = res; md.wave_scale = wave; md.choppiness = choppy; md.wind_velocity = 18; md.random_seed = 7
    if foam: md.use_foam = True; md.foam_layer_name = 'foam'; md.foam_coverage = .2
    o.scale = (size / 60 / md.size,) * 2 + (1,)
    m = bpy.data.materials.new(name + '_water'); m.use_nodes = True; N, L = m.node_tree.nodes, m.node_tree.links; b = N['Principled BSDF']
    b.inputs['Base Color'].default_value = (*lib.lin(col), 1); b.inputs['Roughness'].default_value = .04; b.inputs['IOR'].default_value = 1.333
    b.inputs['Transmission Weight'].default_value = .85
    if foam:
        at = N.new('ShaderNodeAttribute'); at.attribute_name = 'foam'; fr = N.new('ShaderNodeMapRange'); L.new(at.outputs['Fac'], fr.inputs[0]); fr.inputs[1].default_value = .4; fr.inputs[2].default_value = .9
        mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; L.new(fr.outputs[0], mx.inputs['Factor']); mx.inputs['A'].default_value = (*lib.lin(col), 1); mx.inputs['B'].default_value = (.85, .85, .82, 1)
        L.new(mx.outputs['Result'], b.inputs['Base Color'])
        tw = N.new('ShaderNodeMath'); tw.operation = 'SUBTRACT'; tw.inputs[0].default_value = .85; L.new(fr.outputs[0], tw.inputs[1]); L.new(tw.outputs[0], b.inputs['Transmission Weight'])
    vol = N.new('ShaderNodeVolumeAbsorption'); vol.inputs['Color'].default_value = (*lib.lin(murk), 1); vol.inputs['Density'].default_value = .12
    L.new(vol.outputs[0], N['Material Output'].inputs['Volume'])
    me.materials.append(m)
    return o


def ocean_tick(objs, t):
    for o in objs:
        md = o.modifiers.get('ocean')
        if md: md.time = 1.0 + t


def meteor(name, start, end, t0, dur, size=3.0):
    """a burning space rock streaking across the sky: glowing head + stretched tail; returns update fn(t)"""
    hm = bpy.data.materials.new(name + '_m'); hm.use_nodes = True; b = hm.node_tree.nodes['Principled BSDF']
    b.inputs['Emission Color'].default_value = (1, .55, .2, 1); b.inputs['Emission Strength'].default_value = 60; b.inputs['Base Color'].default_value = (1, .5, .2, 1)
    head = T.lib.sphere(name, size, (0, 0, -5000), hm, seg=12, rings=8)
    tail = T.cyl(name + '_tail', size * .8, size * 22, (0, 0, -5000), hm, v=10)
    s, e = Vector(start), Vector(end); d = (e - s).normalized()
    def u(t):
        k = (t - t0) / dur
        if not (0 <= k <= 1.05): head.location = tail.location = (0, 0, -5000); return
        p = s.lerp(e, min(1.0, k)); head.location = p; tail.location = p - d * size * 11
        tail.rotation_mode = 'QUATERNION'; tail.rotation_quaternion = d.to_track_quat('Z', 'Y')
    return u


def sun_light(az, el, energy=4.0, col=(1, .95, .88), angle=.8):
    l = bpy.data.lights.new('sun', 'SUN'); l.energy = energy; l.color = col; l.angle = math.radians(angle)
    o = bpy.data.objects.new('sun', l); bpy.context.scene.collection.objects.link(o)
    o.rotation_euler = (math.radians(90 - el), 0, math.radians(az)); return o


def fog(density=.002, col=(.9, .75, .6), anis=.3, size=(3000, 3000, 600), center=(0, 0, 0)):
    """aerial haze as a bounded volume box (a world volume would swallow the sky): distant hills fade, sun rays read"""
    o = T.box('haze', size, (center[0], center[1], center[2] + size[2] / 2 - 20), None)
    m = bpy.data.materials.new('haze_vol'); m.use_nodes = True; N = m.node_tree.nodes; N.remove(N['Principled BSDF'])
    pv = N.new('ShaderNodeVolumePrincipled'); pv.inputs['Color'].default_value = (*col, 1); pv.inputs['Density'].default_value = density; pv.inputs['Anisotropy'].default_value = anis
    m.node_tree.links.new(pv.outputs[0], N['Material Output'].inputs['Volume'])
    o.data.materials.clear(); o.data.materials.append(m); o.visible_shadow = False
    return o


# ------------------------------------------------------------------ particle smoke (buoyant puffs -> volume), deterministic per frame
def _points_volume_group(name, voxel=1.0):
    ng = bpy.data.node_groups.new(name, 'GeometryNodeTree')
    ng.interface.new_socket('Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
    ng.interface.new_socket('Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    N, L = ng.nodes, ng.links; gi = N.new('NodeGroupInput'); go = N.new('NodeGroupOutput')
    mp = N.new('GeometryNodeMeshToPoints'); L.new(gi.outputs[0], mp.inputs['Mesh'])
    ra = N.new('GeometryNodeInputNamedAttribute'); ra.data_type = 'FLOAT'; ra.inputs['Name'].default_value = 'rad'; L.new(ra.outputs['Attribute'], mp.inputs['Radius'])
    pv = N.new('GeometryNodePointsToVolume'); L.new(mp.outputs['Points'], pv.inputs['Points'])
    pv.inputs['Resolution Mode'].default_value = 'Size' if False else pv.inputs['Resolution Mode'].default_value
    try: pv.resolution_mode = 'VOXEL_SIZE'
    except Exception: pass
    try: pv.inputs['Voxel Size'].default_value = voxel
    except Exception: pass
    pv.inputs['Density'].default_value = 1.0
    rr = N.new('GeometryNodeInputRadius'); L.new(rr.outputs[0], pv.inputs['Radius'])
    L.new(pv.outputs[0], go.inputs[0])
    return ng


def smoke_column(name, base, rate=6.0, life=14.0, rise=7.0, spread=.55, r0=3.0, r1=16.0, wind=(2.5, 0.0), turb=6.0, col=(.06, .055, .05),
                 density=.6, glow=0.0, voxel=1.2, seed=0, t_end=60.0):
    """volcanic ash / steam column from buoyant puffs: each puff is born at the vent, rises (slowing as it cools), drifts with
    the wind, wanders on smooth turbulence and expands.  Positions are a pure function of time, so any frame renders alone.
    returns update(t)"""
    r = random.Random(seed); n = int(rate * life) + 1
    births = [k / rate for k in range(int(rate * (t_end + life)))]
    jit = [(r.uniform(-1, 1), r.uniform(-1, 1), r.uniform(.7, 1.3), r.uniform(0, 100)) for _ in births]
    me = bpy.data.meshes.new(name); o = bpy.data.objects.new(name, me); coll().objects.link(o); o.location = base
    me.vertices.add(n); me.attributes.new('rad', 'FLOAT', 'POINT')
    md = o.modifiers.new('vol', 'NODES'); md.node_group = _points_volume_group(name + '_gn', voxel)
    m = bpy.data.materials.new(name + '_smoke'); m.use_nodes = True; N, L = m.node_tree.nodes, m.node_tree.links; out = N['Material Output']; N.remove(N['Principled BSDF'])
    pv = N.new('ShaderNodeVolumePrincipled'); pv.inputs['Color'].default_value = (*col, 1); pv.inputs['Anisotropy'].default_value = .3
    tc = N.new('ShaderNodeTexCoord'); nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = .08; nz.inputs['Detail'].default_value = 8; nz.inputs['Roughness'].default_value = .65
    L.new(tc.outputs['Object'], nz.inputs['Vector'])
    at = N.new('ShaderNodeAttribute'); at.attribute_name = 'density'; at.attribute_type = 'GEOMETRY'
    nr = N.new('ShaderNodeMapRange'); L.new(nz.outputs['Fac'], nr.inputs[0]); nr.inputs[1].default_value = .35; nr.inputs[2].default_value = .7
    mu = N.new('ShaderNodeMath'); mu.operation = 'MULTIPLY'; L.new(at.outputs['Fac'], mu.inputs[0]); L.new(nr.outputs[0], mu.inputs[1])
    mu2 = N.new('ShaderNodeMath'); mu2.operation = 'MULTIPLY'; L.new(mu.outputs[0], mu2.inputs[0]); mu2.inputs[1].default_value = density
    L.new(mu2.outputs[0], pv.inputs['Density'])
    if glow:
        sp = N.new('ShaderNodeSeparateXYZ'); L.new(tc.outputs['Object'], sp.inputs[0])
        gz = N.new('ShaderNodeMapRange'); L.new(sp.outputs['Z'], gz.inputs[0]); gz.inputs[1].default_value = 25; gz.inputs[2].default_value = 0
        gm = N.new('ShaderNodeMath'); gm.operation = 'MULTIPLY'; L.new(gz.outputs[0], gm.inputs[0]); gm.inputs[1].default_value = glow
        L.new(gm.outputs[0], pv.inputs['Emission Strength']); pv.inputs['Emission Color'].default_value = (1, .32, .06, 1)
    L.new(pv.outputs[0], out.inputs['Volume']); me.materials.append(m)
    def u(t):
        alive = [(b, j) for b, j in zip(births, jit) if 0 <= t - b < life][-n:]
        co = []; rad = []
        for b, (jx, jy, js, ph) in alive:
            a = t - b; k = a / life
            h = rise * life * .45 * (1 - math.exp(-a / (life * .45))) * js                     # buoyant rise, slowing as it cools
            drift = Vector((wind[0], wind[1], 0)) * (a ** 1.25) * .35
            w = noise.turbulence_vector(Vector((ph, h * .03, a * .15)), 2, False) * turb * min(1.0, a / 3)
            x = jx * spread * r0 + drift.x + w.x * (1 + k * 2); y = jy * spread * r0 + drift.y + w.y * (1 + k * 2)
            co += [x, y, h + w.z * .5]; rad.append(r0 + (r1 - r0) * smooth01(k * 1.3))
        cnt = len(rad)
        co += [0, 0, 0] * (n - cnt); rad += [0.0] * (n - cnt)
        me.vertices.foreach_set('co', co); me.attributes['rad'].data.foreach_set('value', rad); me.update()
    return u
