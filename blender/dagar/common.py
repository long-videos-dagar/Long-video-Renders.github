"""Shared helpers for DAGAR CLIPS: keyframe tracks, ink outline, procedural materials."""
import bpy, math, sys, os
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import lib
from lib import lin, mat, coll

def ease(u): u = max(0.0, min(1.0, u)); return u * u * (3 - 2 * u)

def K(keys):
    """Track over time. keys: [(t, value)], value float or tuple. Smoothstep between keys, hold outside."""
    keys = sorted(keys, key=lambda k: k[0])
    def f(t):
        if t <= keys[0][0]: return keys[0][1]
        if t >= keys[-1][0]: return keys[-1][1]
        for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
            if t0 <= t <= t1:
                u = ease((t - t0) / max(1e-6, t1 - t0))
                if isinstance(v0, (tuple, list)): return tuple(a + (b - a) * u for a, b in zip(v0, v1))
                return v0 + (v1 - v0) * u
    return f

def LK(keys):
    """Linear interpolation track."""
    keys = sorted(keys, key=lambda k: k[0])
    def f(t):
        if t <= keys[0][0]: return keys[0][1]
        if t >= keys[-1][0]: return keys[-1][1]
        for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
            if t0 <= t <= t1:
                u = (t - t0) / max(1e-6, t1 - t0)
                if isinstance(v0, (tuple, list)): return tuple(a + (b - a) * u for a, b in zip(v0, v1))
                return v0 + (v1 - v0) * u
    return f

def solid(color, rough=.55, **kw): return mat('s_' + str(color), color, rough=rough, **kw)

def ink_mat():
    m = bpy.data.materials.get('inkblack')
    if m: return m
    m = bpy.data.materials.new('inkblack'); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']; b.inputs['Base Color'].default_value = (.008, .007, .01, 1); b.inputs['Roughness'].default_value = .5
    return m

_OUT = []
def hull_outward():
    """Does Solidify(thickness<0, offset 1, flip) give outward-pointing shell normals in this Blender version? (4.2 vs 5.x differ)"""
    if _OUT: return _OUT[0]
    me = bpy.data.meshes.new('_t'); o = bpy.data.objects.new('_t', me); bpy.context.scene.collection.objects.link(o)
    import bmesh
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0); bm.to_mesh(me); bm.free()
    me.materials.append(None); me.materials.append(None)
    md = o.modifiers.new('hull', 'SOLIDIFY'); md.thickness = -.05; md.offset = 1.0; md.use_flip_normals = True; md.use_rim = False; md.material_offset = 1
    ev = o.evaluated_get(bpy.context.evaluated_depsgraph_get()); em = ev.to_mesh()
    d = 0; k = 0
    for p in em.polygons:
        if p.material_index == 1: d += p.normal.dot(p.center); k += 1
    ev.to_mesh_clear(); bpy.data.objects.remove(o); bpy.data.meshes.remove(me)
    res = d > 0 if k else True
    lib.log('hull shell normals outward:', res, 'faces', k); _OUT.append(res); return res

def hull_mat():
    m = bpy.data.materials.get('hullink')
    if m: return m
    outward = hull_outward() if not os.environ.get('HULLFLIP') else (os.environ['HULLFLIP'] == '1')
    m = bpy.data.materials.new('hullink'); m.use_nodes = True; N = m.node_tree.nodes; L = m.node_tree.links
    N.remove(N['Principled BSDF']); out = N['Material Output']
    geo = N.new('ShaderNodeNewGeometry'); tr = N.new('ShaderNodeBsdfTransparent'); em = N.new('ShaderNodeEmission')
    em.inputs['Color'].default_value = (0.006, 0.005, 0.008, 1); em.inputs['Strength'].default_value = 1.0
    mx = N.new('ShaderNodeMixShader'); L.new(geo.outputs['Backfacing'], mx.inputs['Fac'])
    # outward shell normals: far faces (seen from inside) are back-facing -> ink. Inward normals: the opposite.
    L.new(tr.outputs[0], mx.inputs[1 if outward else 2]); L.new(em.outputs[0], mx.inputs[2 if outward else 1]); L.new(mx.outputs[0], out.inputs['Surface'])
    return m

def outline(o, width=0):
    """Outlines are drawn by Freestyle (see ink_setup); objects in the Characters / Props collections are inked."""
    return o

def ink_setup(W, k=1.0, char_px=7.0, prop_px=3.2):
    """Freestyle ink lines: thick for characters, thinner for props. Pixel widths are given for 1080 px wide frames."""
    import math
    sc = bpy.context.scene; f = W / 1080.0 * k
    sc.render.use_freestyle = True; sc.render.line_thickness_mode = 'ABSOLUTE'
    vl = bpy.context.view_layer; vl.use_freestyle = True
    fs = vl.freestyle_settings; fs.mode = 'EDITOR'; fs.crease_angle = math.radians(115); fs.use_culling = True
    for ls in list(fs.linesets): fs.linesets.remove(ls)
    for name, px, crease in (('chars', char_px, False), ('props', prop_px, True)):
        c = bpy.data.collections.get('Characters' if name == 'chars' else 'Props')
        if not c: continue
        ls = fs.linesets.new(name); ls.select_by_visibility = True; ls.visibility = 'VISIBLE'
        ls.select_by_edge_types = True; ls.select_by_collection = True; ls.collection = c
        ls.select_silhouette = True; ls.select_border = True; ls.select_contour = True; ls.select_external_contour = True; ls.select_crease = crease
        st = ls.linestyle; st.color = (0.01, 0.008, 0.012); st.thickness = px * f; st.thickness_position = 'CENTER'; st.caps = 'ROUND'
        st.use_chaining = True; st.chaining = 'PLAIN'
        try:
            n = st.thickness_modifiers.new('wobble', 'NOISE'); n.amplitude = px * f * .3; n.period = 40
        except Exception: pass

def smooth(o):
    if o.type == 'MESH':
        for p in o.data.polygons: p.use_smooth = True
    return o

# ---- procedural textures -----------------------------------------------------------------------
def _nodes(m):
    m.use_nodes = True; return m.node_tree.nodes, m.node_tree.links, m.node_tree.nodes['Principled BSDF']

def tile_mat(name, c1='#e9e2d0', c2='#d4ccb6', grout='#8c8473', scale=6.0, rough=.35, rot=0.0):
    m = bpy.data.materials.new(name); N, L, b = _nodes(m)
    tc = N.new('ShaderNodeTexCoord'); mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (scale, scale, scale)
    mp.inputs['Rotation'].default_value[2] = rot
    br = N.new('ShaderNodeTexChecker'); br.inputs['Scale'].default_value = 1.0
    br.inputs['Color1'].default_value = (*lin(c1), 1); br.inputs['Color2'].default_value = (*lin(c2), 1)
    bk = N.new('ShaderNodeTexBrick'); bk.inputs['Scale'].default_value = 1.0; bk.offset = 0.0; bk.inputs['Brick Width'].default_value = 1.0; bk.inputs['Row Height'].default_value = 1.0
    bk.inputs['Mortar Size'].default_value = .035; bk.inputs['Color1'].default_value = (*lin(c1), 1); bk.inputs['Color2'].default_value = (*lin(c2), 1); bk.inputs['Mortar'].default_value = (*lin(grout), 1)
    L.new(tc.outputs['Object'], mp.inputs['Vector']); L.new(mp.outputs['Vector'], bk.inputs['Vector'])
    L.new(bk.outputs['Color'], b.inputs['Base Color']); b.inputs['Roughness'].default_value = rough
    bump = N.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = .25; L.new(bk.outputs['Fac'], bump.inputs['Height']); L.new(bump.outputs['Normal'], b.inputs['Normal'])
    return m

def wood_mat(name, c1='#8a5a34', c2='#5a361c', scale=3.0, rough=.5, stretch=(1, 14, 1), planks=False):
    m = bpy.data.materials.new(name); N, L, b = _nodes(m)
    tc = N.new('ShaderNodeTexCoord'); mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (scale * stretch[0], scale * stretch[1], scale * stretch[2])
    wv = N.new('ShaderNodeTexWave'); wv.wave_type = 'BANDS'; wv.inputs['Scale'].default_value = 3; wv.inputs['Distortion'].default_value = 1.2; wv.inputs['Detail'].default_value = 1
    ns = N.new('ShaderNodeTexNoise'); ns.inputs['Scale'].default_value = 5
    ramp = N.new('ShaderNodeValToRGB'); ramp.color_ramp.elements[0].color = (*lin(c2), 1); ramp.color_ramp.elements[1].color = (*lin(c1), 1)
    L.new(tc.outputs['Object'], mp.inputs['Vector']); L.new(mp.outputs['Vector'], wv.inputs['Vector']); L.new(wv.outputs['Fac'], ramp.inputs['Fac'])
    L.new(ramp.outputs['Color'], b.inputs['Base Color']); b.inputs['Roughness'].default_value = rough
    bump = N.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = .15; L.new(wv.outputs['Fac'], bump.inputs['Height']); L.new(bump.outputs['Normal'], b.inputs['Normal'])
    return m

def plaster_mat(name, col='#d9c7a3', rough=.9, scale=40.0, bumpv=.08):
    m = bpy.data.materials.new(name); N, L, b = _nodes(m)
    b.inputs['Base Color'].default_value = (*lin(col), 1); b.inputs['Roughness'].default_value = rough
    tc = N.new('ShaderNodeTexCoord'); ns = N.new('ShaderNodeTexNoise'); ns.inputs['Scale'].default_value = scale; ns.inputs['Detail'].default_value = 6
    bump = N.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = bumpv
    L.new(tc.outputs['Object'], ns.inputs['Vector']); L.new(ns.outputs['Fac'], bump.inputs['Height']); L.new(bump.outputs['Normal'], b.inputs['Normal'])
    return m

def stripe_mat(name, c1, c2, scale=12.0, rough=.9, axis='X'):
    m = bpy.data.materials.new(name); N, L, b = _nodes(m)
    tc = N.new('ShaderNodeTexCoord'); sep = N.new('ShaderNodeSeparateXYZ'); L.new(tc.outputs['Object'], sep.inputs['Vector'])
    mm = N.new('ShaderNodeMath'); mm.operation = 'MULTIPLY'; mm.inputs[1].default_value = scale; L.new(sep.outputs[axis], mm.inputs[0])
    fr = N.new('ShaderNodeMath'); fr.operation = 'FRACT'; L.new(mm.outputs[0], fr.inputs[0])
    st = N.new('ShaderNodeMath'); st.operation = 'GREATER_THAN'; st.inputs[1].default_value = .5; L.new(fr.outputs[0], st.inputs[0])
    mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.inputs['A'].default_value = (*lin(c1), 1); mx.inputs['B'].default_value = (*lin(c2), 1)
    L.new(st.outputs[0], mx.inputs['Factor']); L.new(mx.outputs['Result'], b.inputs['Base Color']); b.inputs['Roughness'].default_value = rough
    return m

def glass_mat(name, col='#cfe8ff', rough=0.03, ior=1.45, trans=1.0):
    m = bpy.data.materials.new(name); N, L, b = _nodes(m)
    b.inputs['Base Color'].default_value = (*lin(col), 1); b.inputs['Roughness'].default_value = rough
    b.inputs['Transmission Weight'].default_value = trans; b.inputs['IOR'].default_value = ior
    return m

def water_mat(name='water'):
    m = bpy.data.materials.new(name); N, L, b = _nodes(m)
    b.inputs['Base Color'].default_value = (*lin('#bfe6ff'), 1); b.inputs['Roughness'].default_value = .02
    b.inputs['Transmission Weight'].default_value = 1.0; b.inputs['IOR'].default_value = 1.333
    return m
