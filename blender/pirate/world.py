"""Storm sky, sun, sea material, rain, spray, oil film."""
import bpy, math, numpy as np
from mathutils import Vector, Matrix
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import lib
from lib import lin, mat, coll
from common_p import *
from lib import world_hdri

def _n(m): return m.node_tree.nodes, m.node_tree.links

def sky(mood='storm', strength=1.0, sun_dir=(.3, 1.0, .45), sun_energy=4.0, sun_col='#ffe9cf', gold=0.0, cloud_scale=2.2, seed=0.0):
    """mood storm: dark clouds. gold>0 blends toward sunset gold. returns sun object"""
    if os.environ.get('USE_PH'):
        try:
            kw = ('overcast', 'puresky', 'cloudy') if mood == 'storm' else ('sunset', 'puresky', 'dusk')
            world_hdri(*kw, strength=strength, rot=seed * 40 + (150 if mood == 'storm' else 200), avoid=('night', 'interior', 'studio', 'indoor', 'room', 'clear'), res='2k')
            wn = bpy.context.scene.world.node_tree; N2, L2 = wn.nodes, wn.links
            env = next(n for n in N2 if n.type == 'TEX_ENVIRONMENT'); bg2 = next(n for n in N2 if n.type == 'BACKGROUND')
            gr = N2.new('ShaderNodeMix'); gr.data_type = 'RGBA'; gr.blend_type = 'MULTIPLY'; gr.inputs['Factor'].default_value = 1.0
            gr.inputs['B'].default_value = ((.30, .36, .44, 1) if mood == 'storm' else (1.15, .9, .65, 1))
            if mood == 'storm':
                hs = N2.new('ShaderNodeHueSaturation'); hs.inputs['Saturation'].default_value = .08; hs.inputs['Value'].default_value = .85
                L2.new(env.outputs['Color'], hs.inputs['Color']); L2.new(hs.outputs['Color'], gr.inputs['A']); gr.inputs['B'].default_value = (.36, .40, .46, 1)
            else: L2.new(env.outputs['Color'], gr.inputs['A'])
            L2.new(gr.outputs['Result'], bg2.inputs['Color'])
            sun = bpy.data.lights.new('Sun', 'SUN'); sun.energy = sun_energy; sun.angle = math.radians(1.2); sun.color = lin(sun_col)
            so = bpy.data.objects.new('Sun', sun); bpy.context.scene.collection.objects.link(so)
            d = Vector(sun_dir).normalized(); so.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler(); return so
        except Exception as e: lib.log('PH hdri failed, procedural sky', e)
    w = bpy.data.worlds.new('W'); bpy.context.scene.world = w; w.use_nodes = True
    N, L = w.node_tree.nodes, w.node_tree.links
    for n in list(N): N.remove(n)
    out = N.new('ShaderNodeOutputWorld'); bg = N.new('ShaderNodeBackground'); tc = N.new('ShaderNodeTexCoord'); mp = N.new('ShaderNodeMapping')
    mp.inputs['Location'].default_value = (seed, 0, 0)
    sep = N.new('ShaderNodeSeparateXYZ'); no = N.new('ShaderNodeTexNoise'); no.inputs['Scale'].default_value = cloud_scale; no.inputs['Detail'].default_value = 8; no.inputs['Roughness'].default_value = .62; no.inputs['Distortion'].default_value = .6
    cr = N.new('ShaderNodeValToRGB')
    if mood == 'storm':
        cols = [(0.0, '#0d1217'), (.35, '#1b2530'), (.6, '#3a4552'), (.85, '#6a7480'), (1.0, '#8f98a2')]
    else:
        cols = [(0.0, '#2a2226'), (.35, '#6a5a52'), (.6, '#c9904a'), (.85, '#ffc470'), (1.0, '#fff0c8')]
    cr.color_ramp.elements[0].position = cols[0][0]; cr.color_ramp.elements[0].color = (*lin(cols[0][1]), 1)
    cr.color_ramp.elements[1].position = cols[-1][0]; cr.color_ramp.elements[1].color = (*lin(cols[-1][1]), 1)
    for p, c in cols[1:-1]:
        e = cr.color_ramp.elements.new(p); e.color = (*lin(c), 1)
    gr = N.new('ShaderNodeMath'); gr.operation = 'ADD'; gr.use_clamp = True
    gz = N.new('ShaderNodeMath'); gz.operation = 'MULTIPLY'; gz.inputs[1].default_value = .8
    L.new(tc.outputs['Generated'], mp.inputs['Vector']) if False else None
    L.new(tc.outputs['Window'], mp.inputs['Vector']) if False else None
    geo = N.new('ShaderNodeNewGeometry')
    L.new(geo.outputs['Normal'], sep.inputs['Vector']) if False else None
    # direction vector: use Texture Coordinate 'Generated' for world: it is the view direction for the world shader
    L.new(tc.outputs['Generated'], mp.inputs['Vector']); L.new(mp.outputs['Vector'], no.inputs['Vector']); L.new(mp.outputs['Vector'], sep.inputs['Vector'])
    sh = N.new('ShaderNodeMath'); sh.operation = 'MULTIPLY_ADD'; sh.inputs[1].default_value = 1.1; sh.inputs[2].default_value = .25      # sky height
    L.new(sep.outputs['Z'], sh.inputs[0])
    mx = N.new('ShaderNodeMath'); mx.operation = 'MULTIPLY_ADD'; mx.inputs[1].default_value = .65; mx.inputs[2].default_value = 0.0
    L.new(no.outputs['Fac'], mx.inputs[0])
    ad = N.new('ShaderNodeMath'); ad.operation = 'ADD'; ad.use_clamp = True; L.new(sh.outputs[0], ad.inputs[0]); L.new(mx.outputs[0], ad.inputs[1])
    L.new(ad.outputs[0], cr.inputs['Fac']); L.new(cr.outputs['Color'], bg.inputs['Color']); bg.inputs['Strength'].default_value = strength
    L.new(bg.outputs[0], out.inputs[0])
    sun = bpy.data.lights.new('Sun', 'SUN'); sun.energy = sun_energy; sun.angle = math.radians(1.2); sun.color = lin(sun_col)
    so = bpy.data.objects.new('Sun', sun); bpy.context.scene.collection.objects.link(so)
    d = Vector(sun_dir).normalized(); so.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
    return so

def sea_mat(name='sea', col='#0f3a40', deep='#04161c', foam_col='#cfd9dc', rough=.12, fog=(0, '#8c98a4'), fine=1.0):
    m = bpy.data.materials.new(name); m.use_nodes = True; N, L = _n(m); b = N['Principled BSDF']
    at = N.new('ShaderNodeAttribute'); at.attribute_name = 'foam'; at.attribute_type = 'GEOMETRY'
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 1.1 * fine; nz.inputs['Detail'].default_value = 5; tc = N.new('ShaderNodeTexCoord')
    nz2 = N.new('ShaderNodeTexNoise'); nz2.inputs['Scale'].default_value = 22.0 * fine; nz2.inputs['Detail'].default_value = 4
    L.new(tc.outputs['Object'], nz.inputs['Vector']); L.new(tc.outputs['Object'], nz2.inputs['Vector'])
    bump = N.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = .35; bump.inputs['Distance'].default_value = .3; L.new(nz2.outputs['Fac'], bump.inputs['Height']); L.new(bump.outputs['Normal'], b.inputs['Normal'])
    # foam amount with noise breakup
    mul = N.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; L.new(at.outputs['Fac'], mul.inputs[0]); 
    nzr = N.new('ShaderNodeMapRange'); nzr.inputs['From Min'].default_value = .38; nzr.inputs['From Max'].default_value = .74; nzr.inputs['To Max'].default_value = 1.6; L.new(nz.outputs['Fac'], nzr.inputs['Value'])
    nz3 = N.new('ShaderNodeTexNoise'); nz3.inputs['Scale'].default_value = 9.0 * fine; nz3.inputs['Detail'].default_value = 6; L.new(tc.outputs['Object'], nz3.inputs['Vector'])
    nzr3 = N.new('ShaderNodeMapRange'); nzr3.inputs['From Min'].default_value = .36; nzr3.inputs['From Max'].default_value = .62; nzr3.inputs['To Min'].default_value = .15; nzr3.inputs['To Max'].default_value = 1.3; L.new(nz3.outputs['Fac'], nzr3.inputs['Value'])
    m3 = N.new('ShaderNodeMath'); m3.operation = 'MULTIPLY'; L.new(nzr.outputs['Result'], m3.inputs[0]); L.new(nzr3.outputs['Result'], m3.inputs[1])
    L.new(m3.outputs[0], mul.inputs[1])
    fa = N.new('ShaderNodeMath'); fa.operation = 'ADD'; fa.use_clamp = True; fa.inputs[1].default_value = 0.0
    sm = N.new('ShaderNodeMath'); sm.operation = 'MULTIPLY'; sm.inputs[1].default_value = 0.0; L.new(at.outputs['Fac'], sm.inputs[0])
    L.new(mul.outputs[0], fa.inputs[0]); mx = N.new('ShaderNodeMath'); mx.operation = 'MAXIMUM'; mx.use_clamp = True
    L.new(fa.outputs[0], mx.inputs[0]); L.new(sm.outputs[0], mx.inputs[1])
    cm = N.new('ShaderNodeMix'); cm.data_type = 'RGBA'; cm.inputs['A'].default_value = (*lin(col), 1); cm.inputs['B'].default_value = (*lin(foam_col), 1)
    # darker deep colour in troughs / lighter in crests
    L.new(mx.outputs[0], cm.inputs['Factor']); L.new(cm.outputs['Result'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = rough; b.inputs['Specular IOR Level'].default_value = .65
    b.inputs['Subsurface Weight'].default_value = .15; b.inputs['Subsurface Radius'].default_value = (.4, .9, 1.0)
    rr = N.new('ShaderNodeMath'); rr.operation = 'MULTIPLY_ADD'; rr.inputs[1].default_value = .55; rr.inputs[2].default_value = rough
    L.new(mx.outputs[0], rr.inputs[0]); L.new(rr.outputs[0], b.inputs['Roughness'])
    # slick (oil film) tint is handled by Patch attribute 'oil' if present
    return m

def oil_film_mat(name='oil'):
    """thin-film iridescence faked from view angle + noise; semi transparent"""
    m = bpy.data.materials.new(name); m.use_nodes = True; N, L = _n(m)
    for n in list(N): N.remove(n)
    out = N.new('ShaderNodeOutputMaterial'); mix = N.new('ShaderNodeMixShader'); tr = N.new('ShaderNodeBsdfTransparent'); gl = N.new('ShaderNodeBsdfGlossy')
    lw = N.new('ShaderNodeLayerWeight'); lw.inputs['Blend'].default_value = .35
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 3.0; nz.inputs['Detail'].default_value = 6; tc = N.new('ShaderNodeTexCoord'); L.new(tc.outputs['Object'], nz.inputs['Vector'])
    add = N.new('ShaderNodeMath'); add.operation = 'ADD'; L.new(lw.outputs['Facing'], add.inputs[0]); L.new(nz.outputs['Fac'], add.inputs[1])
    cr = N.new('ShaderNodeValToRGB'); ce = cr.color_ramp
    ce.elements[0].position = .2; ce.elements[0].color = (.9, .55, .1, 1); ce.elements[1].position = 1.4 if False else 1.0; ce.elements[1].color = (.1, .5, .9, 1)
    e2 = ce.elements.new(.5); e2.color = (.8, .2, .6, 1); e3 = ce.elements.new(.75); e3.color = (.2, .8, .4, 1)
    L.new(add.outputs[0], cr.inputs['Fac']); L.new(cr.outputs['Color'], gl.inputs['Color']); gl.inputs['Roughness'].default_value = .04
    mix.inputs['Fac'].default_value = .55; L.new(tr.outputs[0], mix.inputs[1]); L.new(gl.outputs[0], mix.inputs[2]); L.new(mix.outputs[0], out.inputs['Surface'])
    return m

class Rain:
    def __init__(self, n=900, size=(40, 40, 22), mat_=None):
        me = bpy.data.meshes.new('rain'); self.n = n; me.vertices.add(n * 4); me.loops.add(n * 4); me.polygons.add(n)
        me.polygons.foreach_set('loop_start', (np.arange(n) * 4).astype(np.int32)); me.polygons.foreach_set('loop_total', np.full(n, 4, np.int32))
        me.loops.foreach_set('vertex_index', np.arange(n * 4, dtype=np.int32)); me.update()
        self.o = bpy.data.objects.new('rain', me); bpy.context.scene.collection.objects.link(self.o); self.size = size
        m = mat_ or self.mat(); me.materials.append(m)
        self.o.visible_shadow = False; self.o.visible_diffuse = False; self.o.visible_glossy = False
    @staticmethod
    def mat():
        m = bpy.data.materials.new('rainm'); m.use_nodes = True; N, L = _n(m)
        for n in list(N): N.remove(n)
        out = N.new('ShaderNodeOutputMaterial'); mx = N.new('ShaderNodeMixShader'); tr = N.new('ShaderNodeBsdfTransparent'); em = N.new('ShaderNodeEmission')
        em.inputs['Color'].default_value = (.75, .82, .9, 1); em.inputs['Strength'].default_value = 1.4; mx.inputs['Fac'].default_value = .22
        L.new(tr.outputs[0], mx.inputs[1]); L.new(em.outputs[0], mx.inputs[2]); L.new(mx.outputs[0], out.inputs['Surface']); return m
    def update(self, t, cam_loc, wind=(5, 3), fall=16.0, length=.9, width=.012, seed=0):
        sx, sy, sz = self.size
        rnd = np.random.RandomState(1234 + seed)
        px = rnd.uniform(-sx / 2, sx / 2, self.n); py = rnd.uniform(-sy / 2, sy / 2, self.n); pz = rnd.uniform(0, sz, self.n); sp = rnd.uniform(.8, 1.2, self.n)
        zz = (pz - t * fall * sp) % sz
        xx = (px + t * wind[0] * 0.0 + (sz - zz) * wind[0] / fall) % sx - sx / 2 + cam_loc[0]; yy = (py + (sz - zz) * wind[1] / fall) % sy - sy / 2 + cam_loc[1]
        zz = zz - 2 + cam_loc[2]
        d = np.array([wind[0], wind[1], -fall]); d = d / np.linalg.norm(d); a = np.stack([xx, yy, zz], 1); b = a - d * length
        # billboard width perpendicular to the camera direction (approx: along x/y mix)
        wv = np.array([-d[1], d[0], 0.0]); wv = wv / (np.linalg.norm(wv) + 1e-6) * width
        V = np.zeros((self.n, 4, 3), np.float32); V[:, 0] = a - wv; V[:, 1] = a + wv; V[:, 2] = b + wv; V[:, 3] = b - wv
        self.o.data.vertices.foreach_set('co', V.reshape(-1)); self.o.data.update()


def add_fog(m, dist, col):
    """haze: mix the surface with a flat colour by camera distance (cheap, no volume)"""
    if not m.use_nodes or m.get('fogged'): return
    N, L = m.node_tree.nodes, m.node_tree.links
    outs = [n for n in N if n.type == 'OUTPUT_MATERIAL']
    if not outs: return
    o = outs[0]; sock = o.inputs['Surface']
    if not sock.links: return
    src = sock.links[0].from_socket
    cd = N.new('ShaderNodeCameraData'); mp = N.new('ShaderNodeMath'); mp.operation = 'DIVIDE'; mp.inputs[1].default_value = dist
    ex = N.new('ShaderNodeMath'); ex.operation = 'MULTIPLY'; ex.inputs[1].default_value = -1.0
    e2 = N.new('ShaderNodeMath'); e2.operation = 'EXPONENT'
    om = N.new('ShaderNodeMath'); om.operation = 'SUBTRACT'; om.inputs[0].default_value = 1.0; om.use_clamp = True
    L.new(cd.outputs['View Distance'], mp.inputs[0]); L.new(mp.outputs[0], ex.inputs[0]); L.new(ex.outputs[0], e2.inputs[0]); L.new(e2.outputs[0], om.inputs[1])
    em = N.new('ShaderNodeEmission'); em.inputs['Color'].default_value = (*lin(col), 1); em.inputs['Strength'].default_value = 1.0
    mx = N.new('ShaderNodeMixShader'); L.new(om.outputs[0], mx.inputs['Fac']); L.new(src, mx.inputs[1]); L.new(em.outputs[0], mx.inputs[2]); L.new(mx.outputs[0], sock)
    m['fogged'] = 1

def oil_film_mat2(name='oilfilm'):
    m = bpy.data.materials.new(name); m.use_nodes = True; N, L = _n(m)
    for n in list(N): N.remove(n)
    out = N.new('ShaderNodeOutputMaterial'); mix = N.new('ShaderNodeMixShader'); tr = N.new('ShaderNodeBsdfTransparent'); gl = N.new('ShaderNodeBsdfGlossy')
    tc = N.new('ShaderNodeTexCoord'); vs = N.new('ShaderNodeValue'); vs.name = 'cx'; vy = N.new('ShaderNodeValue'); vy.name = 'cy'; vr = N.new('ShaderNodeValue'); vr.name = 'R'
    sp = N.new('ShaderNodeSeparateXYZ'); L.new(tc.outputs['Object'], sp.inputs['Vector'])
    dx = N.new('ShaderNodeMath'); dx.operation = 'SUBTRACT'; L.new(sp.outputs['X'], dx.inputs[0]); L.new(vs.outputs[0], dx.inputs[1])
    dy = N.new('ShaderNodeMath'); dy.operation = 'SUBTRACT'; L.new(sp.outputs['Y'], dy.inputs[0]); L.new(vy.outputs[0], dy.inputs[1])
    x2 = N.new('ShaderNodeMath'); x2.operation = 'POWER'; x2.inputs[1].default_value = 2.0; L.new(dx.outputs[0], x2.inputs[0])
    y2 = N.new('ShaderNodeMath'); y2.operation = 'POWER'; y2.inputs[1].default_value = 2.0; L.new(dy.outputs[0], y2.inputs[0])
    ad = N.new('ShaderNodeMath'); ad.operation = 'ADD'; L.new(x2.outputs[0], ad.inputs[0]); L.new(y2.outputs[0], ad.inputs[1])
    sq = N.new('ShaderNodeMath'); sq.operation = 'SQRT'; L.new(ad.outputs[0], sq.inputs[0])
    # noisy edge
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = .9; nz.inputs['Detail'].default_value = 5; L.new(tc.outputs['Object'], nz.inputs['Vector'])
    rn = N.new('ShaderNodeMath'); rn.operation = 'MULTIPLY_ADD'; rn.inputs[1].default_value = .35; L.new(nz.outputs['Fac'], rn.inputs[0]); rn.inputs[2].default_value = .82
    rr = N.new('ShaderNodeMath'); rr.operation = 'MULTIPLY'; L.new(vr.outputs[0], rr.inputs[0]); L.new(rn.outputs[0], rr.inputs[1])
    dv = N.new('ShaderNodeMath'); dv.operation = 'DIVIDE'; L.new(sq.outputs[0], dv.inputs[0]); L.new(rr.outputs[0], dv.inputs[1])
    mk = N.new('ShaderNodeMapRange'); mk.inputs['From Min'].default_value = .75; mk.inputs['From Max'].default_value = 1.0; mk.inputs['To Min'].default_value = 1.0; mk.inputs['To Max'].default_value = 0.0; mk.clamp = True
    L.new(dv.outputs[0], mk.inputs['Value'])
    # iridescence ring from radial position + noise
    lw = N.new('ShaderNodeLayerWeight'); lw.inputs['Blend'].default_value = .4
    ad2 = N.new('ShaderNodeMath'); ad2.operation = 'ADD'; L.new(lw.outputs['Facing'], ad2.inputs[0]); L.new(nz.outputs['Fac'], ad2.inputs[1])
    cr = N.new('ShaderNodeValToRGB'); ce = cr.color_ramp
    ce.elements[0].position = .25; ce.elements[0].color = (.95, .62, .12, 1); ce.elements[1].position = 1.0; ce.elements[1].color = (.12, .45, .95, 1)
    e2 = ce.elements.new(.5); e2.color = (.85, .2, .6, 1); e3 = ce.elements.new(.75); e3.color = (.2, .85, .45, 1)
    L.new(ad2.outputs[0], cr.inputs['Fac']); L.new(cr.outputs['Color'], gl.inputs['Color']); gl.inputs['Roughness'].default_value = .03
    ms = N.new('ShaderNodeMath'); ms.operation = 'MULTIPLY'; ms.inputs[1].default_value = .62; L.new(mk.outputs['Result'], ms.inputs[0])
    L.new(ms.outputs[0], mix.inputs['Fac']); L.new(tr.outputs[0], mix.inputs[1]); L.new(gl.outputs[0], mix.inputs[2]); L.new(mix.outputs[0], out.inputs['Surface'])
    return m
