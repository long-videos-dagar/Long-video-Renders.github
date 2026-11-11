"""Shared helpers for the Blender preview scenes (Blender 4.2, Cycles).
Assets from Poly Haven (CC0) - https://polyhaven.com"""
import bpy, bmesh, math, os, json, urllib.request, random, time
from mathutils import Vector, Euler, Matrix

ROOT = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.join(ROOT, 'tex')
CACHE = os.environ.get('PH_CACHE', '/tmp/ph')
UA = {'User-Agent': 'animated-shorts-previews/1.0 (+https://github.com/chintudagar541-stack/wanderly)'}
DRAFT = os.environ.get('DRAFT', '0') == '1'
R = random.Random(7)

def log(*a): print('[lib]', *a, flush=True)

# ------------------------------------------------------------------ colour
def lin(c):
    if isinstance(c, str):
        c = c.lstrip('#')
        if len(c) == 3: c = ''.join(ch * 2 for ch in c)
        c = tuple(int(c[i:i + 2], 16) / 255 for i in (0, 2, 4))
    f = lambda v: v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    return tuple(f(v) for v in c[:3])

# ------------------------------------------------------------------ poly haven
def _get(url):
    for k in range(4):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90).read()
        except Exception as e:
            log('retry', url, e); time.sleep(2 + k * 3)
    raise RuntimeError('download failed ' + url)

def _json(url): return json.loads(_get(url))
def _dl(url, path):
    if os.path.exists(path) and os.path.getsize(path) > 0: return path
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, 'wb').write(_get(url)); return path

_ASSETS = {}
USED = set()
def ph_assets(t):
    if t not in _ASSETS: _ASSETS[t] = _json(f'https://api.polyhaven.com/assets?t={t}')
    return _ASSETS[t]

def ph_find(t, *kw, avoid=(), cats=()):
    kw = [k.lower() for k in kw]
    best, bs = None, 0
    for aid, a in ph_assets(t).items():
        text = ' '.join([aid, a.get('name', ''), ' '.join(a.get('tags', [])), ' '.join(a.get('categories', []))]).lower()
        if any(v in text for v in avoid): continue
        if cats and not any(c in a.get('categories', []) for c in cats): continue
        s = sum((4 if k in aid else (2 if k in a.get('name', '').lower() else (1 if k in text else 0))) for k in kw)
        s += min(a.get('download_count', 0), 2_000_000) / 4_000_000
        if s > bs: best, bs = aid, s
    log('ph_find', t, kw, '->', best)
    return best

def ph_texture(aid, res='2k'):
    USED.add(aid)
    f = _json(f'https://api.polyhaven.com/files/{aid}'); out = {}
    for key, short in (('Diffuse', 'diff'), ('Rough', 'rough'), ('Displacement', 'disp'), ('nor_gl', 'nor'), ('arm', 'arm'), ('AO', 'ao')):
        if key not in f: continue
        r = f[key].get(res) or f[key].get('2k') or f[key].get('1k') or next(iter(f[key].values()))
        fmt = r.get('jpg') or r.get('png') or next(iter(r.values()))
        out[short] = _dl(fmt['url'], f'{CACHE}/{aid}/{short}_{res}.{fmt["url"].rsplit(".", 1)[-1]}')
    return out

def ph_hdri(aid, res='2k'):
    USED.add(aid)
    f = _json(f'https://api.polyhaven.com/files/{aid}')
    r = f['hdri'].get(res) or f['hdri'].get('1k')
    return _dl(r['hdr']['url'], f'{CACHE}/{aid}/{aid}_{res}.hdr')

def ph_model(aid, res='1k'):
    """Append all objects of a Poly Haven model; returns them as a parented group (an empty)."""
    USED.add(aid)
    f = _json(f'https://api.polyhaven.com/files/{aid}')
    b = f['blend'].get(res) or f['blend'].get('1k') or next(iter(f['blend'].values()))
    b = b['blend']; base = f'{CACHE}/{aid}/'
    path = _dl(b['url'], base + b['url'].rsplit('/', 1)[-1])
    for rel, inc in b.get('include', {}).items(): _dl(inc['url'], base + rel)
    with bpy.data.libraries.load(path, link=False) as (src, dst): dst.objects = src.objects
    root = bpy.data.objects.new(aid, None); bpy.context.scene.collection.objects.link(root)
    objs = [o for o in dst.objects if o is not None]
    for o in objs:
        bpy.context.scene.collection.objects.link(o)
        if o.parent is None: o.parent = root
    fix_images(base)
    return root, objs

def fix_images(base):
    for im in bpy.data.images:
        fp = im.filepath
        if not fp or os.path.exists(bpy.path.abspath(fp)): continue
        for cand in (base + fp.lstrip('/').lstrip('\\'), base + 'textures/' + os.path.basename(fp)):
            if os.path.exists(cand): im.filepath = cand; im.reload(); break

def ph_pick(t, cands, *kw, cats=(), avoid=()):
    a = ph_assets(t)
    for c in cands:
        if c in a: return c
    return ph_find(t, *kw, cats=cats, avoid=avoid) if kw else None

_MODELS = {}
def model(cands, *kw, res='1k', hide=True):
    """Load a Poly Haven model once (hidden original); returns (root, objs) or None."""
    key = tuple(cands) + kw
    if key in _MODELS: return _MODELS[key]
    try:
        aid = ph_pick('models', cands, *kw)
        if not aid: _MODELS[key] = None; return None
        root, objs = ph_model(aid, res)
        if hide:
            root.location = (0, 0, -500)
        _MODELS[key] = (root, objs); log('model', aid, len(objs))
    except Exception as e:
        log('model failed', cands, e); _MODELS[key] = None
    return _MODELS[key]

def place(m, loc, rot=0.0, scale=1.0):
    if not m: return None
    return ph_instance(m[0], m[1], loc, rot, scale)

def ph_instance(root, objs, loc, rot=0.0, scale=1.0):
    """Cheap copy of an appended model sharing mesh data."""
    nr = bpy.data.objects.new(root.name + '_i', None); bpy.context.scene.collection.objects.link(nr)
    m = {}
    for o in objs:
        c = o.copy(); bpy.context.scene.collection.objects.link(c); m[o] = c
    for o, c in m.items():
        c.parent = m.get(o.parent, nr)
    nr.location = loc; nr.rotation_euler = (0, 0, rot); nr.scale = (scale,) * 3
    return nr

# ------------------------------------------------------------------ scene
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    return bpy.context.scene

def setup(w=1440, h=2560, samples=160):
    sc = bpy.context.scene
    if DRAFT: w, h, samples = w // 2, h // 2, 24
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'
    sc.cycles.samples = samples; sc.cycles.use_adaptive_sampling = True; sc.cycles.adaptive_threshold = 0.015
    sc.cycles.use_denoising = True
    try: sc.cycles.denoiser = 'OPENIMAGEDENOISE'
    except Exception: pass
    sc.cycles.max_bounces = 8; sc.cycles.diffuse_bounces = 3; sc.cycles.glossy_bounces = 3
    sc.cycles.transmission_bounces = 8; sc.cycles.volume_bounces = 1; sc.cycles.transparent_max_bounces = 16
    sc.cycles.caustics_reflective = False; sc.cycles.caustics_refractive = False; sc.cycles.blur_glossy = 1.0
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = w, h, 100
    sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGB'
    sc.view_settings.view_transform = 'AgX'
    for look in ('AgX - Punchy', 'AgX - Medium High Contrast'):
        try: sc.view_settings.look = look; break
        except Exception: pass
    sc.render.threads_mode = 'AUTO'
    return sc

def world_hdri(*kw, strength=1.0, rot=0.0, aid=None, res='2k', avoid=()):
    aid = aid or ph_find('hdris', *kw, avoid=avoid)
    path = ph_hdri(aid, res)
    w = bpy.data.worlds.new('World'); bpy.context.scene.world = w; w.use_nodes = True
    N, L = w.node_tree.nodes, w.node_tree.links
    bg = N['Background']; env = N.new('ShaderNodeTexEnvironment'); env.image = bpy.data.images.load(path)
    tc = N.new('ShaderNodeTexCoord'); mp = N.new('ShaderNodeMapping'); mp.inputs['Rotation'].default_value[2] = math.radians(rot)
    L.new(tc.outputs['Generated'], mp.inputs['Vector']); L.new(mp.outputs['Vector'], env.inputs['Vector'])
    L.new(env.outputs['Color'], bg.inputs['Color']); bg.inputs['Strength'].default_value = strength
    return aid

def world_color(col, strength=1.0):
    w = bpy.data.worlds.new('World'); bpy.context.scene.world = w; w.use_nodes = True
    bg = w.node_tree.nodes['Background']; bg.inputs['Color'].default_value = (*lin(col), 1); bg.inputs['Strength'].default_value = strength

def sun(az, el, energy=3.0, angle=1.5, color='#fff4e4'):
    """az: 0 = light comes from behind the camera (camera at -Y looking +Y), 90 = from screen right."""
    l = bpy.data.lights.new('Sun', 'SUN'); l.energy = energy; l.angle = math.radians(angle); l.color = lin(color)
    o = bpy.data.objects.new('Sun', l); bpy.context.scene.collection.objects.link(o)
    o.rotation_euler = Euler((math.radians(90 - el), 0, math.radians(az)), 'XYZ'); return o

def point(loc, energy=200, color='#ffd9a0', radius=.1):
    l = bpy.data.lights.new('Pt', 'POINT'); l.energy = energy; l.color = lin(color); l.shadow_soft_size = radius
    o = bpy.data.objects.new('Pt', l); bpy.context.scene.collection.objects.link(o); o.location = loc; return o

def area(loc, look, size=2, energy=300, color='#ffffff'):
    l = bpy.data.lights.new('Area', 'AREA'); l.energy = energy; l.size = size; l.color = lin(color)
    o = bpy.data.objects.new('Area', l); bpy.context.scene.collection.objects.link(o); o.location = loc
    o.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler(); return o

def camera(loc, look, lens=30, focus=None, fstop=None):
    cd = bpy.data.cameras.new('Cam'); cd.lens = lens; cd.sensor_width = 36; cd.sensor_fit = 'AUTO'; cd.clip_end = 3000
    o = bpy.data.objects.new('Cam', cd); bpy.context.scene.collection.objects.link(o)
    o.location = loc; o.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    bpy.context.scene.camera = o
    if fstop:
        cd.dof.use_dof = True; cd.dof.aperture_fstop = fstop
        cd.dof.focus_distance = (Vector(focus or look) - Vector(loc)).length
    return o

def render(path):
    sc = bpy.context.scene; sc.render.filepath = path
    t = time.time(); bpy.ops.render.render(write_still=True); log('rendered', path, f'{time.time() - t:.0f}s')
    jp = path.rsplit('.', 1)[0] + '.jpg'
    st = sc.render.image_settings; st.file_format = 'JPEG'; st.quality = 92
    bpy.data.images['Render Result'].save_render(jp, scene=sc); log('saved', jp)

# ------------------------------------------------------------------ materials
def mat(name, color='#cccccc', rough=.5, metal=0.0, emit=None, emit_strength=0.0, coat=0.0, sss=0.0, alpha=1.0, trans=0.0, spec=.5):
    m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*lin(color), 1); b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    try: b.inputs['Specular IOR Level'].default_value = spec
    except Exception: pass
    if emit: b.inputs['Emission Color'].default_value = (*lin(emit), 1); b.inputs['Emission Strength'].default_value = emit_strength
    if coat: b.inputs['Coat Weight'].default_value = coat
    if sss: b.inputs['Subsurface Weight'].default_value = sss; b.inputs['Subsurface Radius'].default_value = (1, .4, .2)
    if trans: b.inputs['Transmission Weight'].default_value = trans
    if alpha < 1: b.inputs['Alpha'].default_value = alpha
    return m

def mat_ph(name, *kw, aid=None, scale=1.0, tint=None, rough=None, bump=.5, res='2k', coords='Object', avoid=(), rough_mul=1.0, metal=None):
    aid = aid or ph_find('textures', *kw, avoid=avoid)
    f = ph_texture(aid, res)
    m = bpy.data.materials.new(name); m.use_nodes = True
    N, L = m.node_tree.nodes, m.node_tree.links; b = N['Principled BSDF']
    tc = N.new('ShaderNodeTexCoord'); mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (1 / scale,) * 3
    L.new(tc.outputs[coords], mp.inputs['Vector'])
    def img(path, nc):
        t = N.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(path, check_existing=True)
        if nc: t.image.colorspace_settings.name = 'Non-Color'
        t.projection = 'BOX'; t.projection_blend = .3
        L.new(mp.outputs['Vector'], t.inputs['Vector']); return t
    if 'diff' in f:
        out = img(f['diff'], False).outputs['Color']
        if tint:
            mx = N.new('ShaderNodeMixRGB'); mx.blend_type = 'MULTIPLY'; mx.inputs['Fac'].default_value = 1
            mx.inputs['Color2'].default_value = (*lin(tint), 1); L.new(out, mx.inputs['Color1']); out = mx.outputs['Color']
        L.new(out, b.inputs['Base Color'])
    if 'rough' in f:
        ro = img(f['rough'], True).outputs['Color']
        if rough_mul != 1:
            mm = N.new('ShaderNodeMath'); mm.operation = 'MULTIPLY'; mm.inputs[1].default_value = rough_mul; L.new(ro, mm.inputs[0]); ro = mm.outputs[0]
        L.new(ro, b.inputs['Roughness'])
    elif 'arm' in f:
        sp = N.new('ShaderNodeSeparateColor'); L.new(img(f['arm'], True).outputs['Color'], sp.inputs['Color'])
        L.new(sp.outputs[1], b.inputs['Roughness']); L.new(sp.outputs[2], b.inputs['Metallic'])
    if rough is not None and 'rough' not in f: b.inputs['Roughness'].default_value = rough
    if metal is not None: b.inputs['Metallic'].default_value = metal
    if bump > 0 and 'disp' in f:
        bp = N.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = bump; bp.inputs['Distance'].default_value = .03 * scale
        L.new(img(f['disp'], True).outputs['Color'], bp.inputs['Height']); L.new(bp.outputs['Normal'], b.inputs['Normal'])
    m['ph'] = aid
    return m

def mat_image(name, path, rough=.6, extension='EXTEND', sss=0.0, alpha=False, emit=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    N, L = m.node_tree.nodes, m.node_tree.links; b = N['Principled BSDF']
    t = N.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(path, check_existing=True); t.extension = extension
    L.new(t.outputs['Color'], b.inputs['Base Color']); b.inputs['Roughness'].default_value = rough
    if alpha: L.new(t.outputs['Alpha'], b.inputs['Alpha'])
    if sss: b.inputs['Subsurface Weight'].default_value = sss
    if emit: L.new(t.outputs['Color'], b.inputs['Emission Color']); b.inputs['Emission Strength'].default_value = emit
    return m

def mat_windows(name, wall='#8a4a3a', glass='#1c2733', lit='#ffcf88', lit_ratio=.35, cols=1.0, rows=.32, emit=2.0):
    """Facade with a grid of windows from the brick texture node (for distant buildings)."""
    m = bpy.data.materials.new(name); m.use_nodes = True
    N, L = m.node_tree.nodes, m.node_tree.links; b = N['Principled BSDF']
    tc = N.new('ShaderNodeTexCoord'); br = N.new('ShaderNodeTexBrick')
    br.offset = 0; br.squash = 1; br.inputs['Scale'].default_value = 1
    br.inputs['Brick Width'].default_value = cols; br.inputs['Row Height'].default_value = rows
    br.inputs['Mortar Size'].default_value = .45; br.inputs['Mortar Smooth'].default_value = 0
    br.inputs['Color1'].default_value = (*lin(glass), 1); br.inputs['Color2'].default_value = (*lin(glass), 1)
    br.inputs['Mortar'].default_value = (*lin(wall), 1)
    L.new(tc.outputs['Object'], br.inputs['Vector'])
    L.new(br.outputs['Color'], b.inputs['Base Color'])
    rr = N.new('ShaderNodeMapRange'); L.new(br.outputs['Fac'], rr.inputs['Value']); rr.inputs[3].default_value = .08; rr.inputs[4].default_value = .85
    L.new(rr.outputs[0], b.inputs['Roughness'])
    # some windows lit: noise per brick cell
    ns = N.new('ShaderNodeTexWhiteNoise'); ns.noise_dimensions = '3D'
    fl = N.new('ShaderNodeVectorMath'); fl.operation = 'SNAP'; fl.inputs[1].default_value = (cols, cols, rows)
    L.new(tc.outputs['Object'], fl.inputs[0]); L.new(fl.outputs[0], ns.inputs['Vector'])
    gt = N.new('ShaderNodeMath'); gt.operation = 'LESS_THAN'; gt.inputs[1].default_value = lit_ratio; L.new(ns.outputs['Value'], gt.inputs[0])
    inv = N.new('ShaderNodeMath'); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1; L.new(br.outputs['Fac'], inv.inputs[1])
    mu = N.new('ShaderNodeMath'); mu.operation = 'MULTIPLY'; L.new(gt.outputs[0], mu.inputs[0]); L.new(inv.outputs[0], mu.inputs[1])
    em = N.new('ShaderNodeMath'); em.operation = 'MULTIPLY'; em.inputs[1].default_value = emit; L.new(mu.outputs[0], em.inputs[0])
    b.inputs['Emission Color'].default_value = (*lin(lit), 1); L.new(em.outputs[0], b.inputs['Emission Strength'])
    return m

# ------------------------------------------------------------------ geometry
def coll(name):
    c = bpy.data.collections.get(name)
    if not c: c = bpy.data.collections.new(name); bpy.context.scene.collection.children.link(c)
    return c

def obj_from_bm(name, bm, m=None, c=None, smooth=False):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); (c or bpy.context.scene.collection).objects.link(o)
    if m: me.materials.append(m)
    if smooth:
        for p in me.polygons: p.use_smooth = True
    return o

def box(name, size, loc=(0, 0, 0), m=None, rot=(0, 0, 0), bevel=0.0, c=None, seg=2):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts: v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2]))
    o = obj_from_bm(name, bm, m, c); o.location = loc; o.rotation_euler = rot
    if bevel:
        md = o.modifiers.new('bev', 'BEVEL'); md.width = bevel; md.segments = seg; md.limit_method = 'ANGLE'
        for p in o.data.polygons: p.use_smooth = True
        try: o.data.shade_smooth_by_angle() if hasattr(o.data, 'shade_smooth_by_angle') else None
        except Exception: pass
    return o

def cyl(name, r, h, loc=(0, 0, 0), m=None, seg=24, rot=(0, 0, 0), r2=None, cap=True, c=None, smooth=True):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=cap, cap_tris=False, segments=seg, radius1=r, radius2=r if r2 is None else r2, depth=h)
    o = obj_from_bm(name, bm, m, c, smooth=False); o.location = loc; o.rotation_euler = rot
    if smooth:
        for p in o.data.polygons: p.use_smooth = abs(p.normal.z) < .7
    return o

def sphere(name, r, loc=(0, 0, 0), m=None, seg=32, rings=16, scale=(1, 1, 1), c=None, rot=(0, 0, 0)):
    bm = bmesh.new(); bm.loops.layers.uv.new('UVMap'); bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=r, calc_uvs=True)
    for v in bm.verts: v.co = Vector((v.co.x * scale[0], v.co.y * scale[1], v.co.z * scale[2]))
    o = obj_from_bm(name, bm, m, c, smooth=True); o.location = loc; o.rotation_euler = rot; return o

def torus(name, R1, r, loc=(0, 0, 0), m=None, rot=(0, 0, 0), seg=32, mseg=10, c=None, arc=math.tau):
    bm = bmesh.new()
    rings = []
    for i in range(seg + (0 if arc >= math.tau - 1e-6 else 1)):
        a = arc * i / seg
        ring = []
        for j in range(mseg):
            b = math.tau * j / mseg
            x = (R1 + r * math.cos(b)) * math.cos(a); y = (R1 + r * math.cos(b)) * math.sin(a); z = r * math.sin(b)
            ring.append(bm.verts.new((x, y, z)))
        rings.append(ring)
    closed = arc >= math.tau - 1e-6
    for i in range(len(rings) - (0 if closed else 1)):
        A, Bq = rings[i], rings[(i + 1) % len(rings)]
        for j in range(mseg): bm.faces.new((A[j], A[(j + 1) % mseg], Bq[(j + 1) % mseg], Bq[j]))
    o = obj_from_bm(name, bm, m, c, smooth=True); o.location = loc; o.rotation_euler = rot; return o

def plane(name, sx, sy, loc=(0, 0, 0), m=None, rot=(0, 0, 0), c=None, sub=0):
    bm = bmesh.new(); bm.loops.layers.uv.new('UVMap'); bmesh.ops.create_grid(bm, x_segments=max(1, sub), y_segments=max(1, sub), size=.5, calc_uvs=True)
    for v in bm.verts: v.co = Vector((v.co.x * sx, v.co.y * sy, 0))
    o = obj_from_bm(name, bm, m, c); o.location = loc; o.rotation_euler = rot; return o

def tube(name, pts, r, m=None, c=None, res=8):
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = r; cu.bevel_resolution = 3
    cu.use_fill_caps = True
    sp = cu.splines.new('POLY'); sp.points.add(len(pts) - 1)
    for i, p in enumerate(pts): sp.points[i].co = (p[0], p[1], p[2], 1)
    o = bpy.data.objects.new(name, cu); (c or bpy.context.scene.collection).objects.link(o)
    if m: cu.materials.append(m)
    return o

def smooth_tube(name, pts, r, m=None, c=None):
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = r; cu.bevel_resolution = 4; cu.use_fill_caps = True
    sp = cu.splines.new('BEZIER'); sp.bezier_points.add(len(pts) - 1)
    for i, p in enumerate(pts):
        bp = sp.bezier_points[i]; bp.co = p; bp.handle_left_type = bp.handle_right_type = 'AUTO'
    o = bpy.data.objects.new(name, cu); (c or bpy.context.scene.collection).objects.link(o)
    if m: cu.materials.append(m)
    return o

def lathe(name, prof, seg=40, m=None, c=None, sy=1.0):
    """prof: list of (r, z) from bottom to top. r = 0 closes the end."""
    bm = bmesh.new(); rings = []
    for (r, z) in prof:
        if r < 1e-4: rings.append([bm.verts.new((0, 0, z))]); continue
        rings.append([bm.verts.new((r * math.cos(math.tau * i / seg), r * sy * math.sin(math.tau * i / seg), z)) for i in range(seg)])
    rings = [r for i, r in enumerate(rings) if not (len(r) == 1 and i > 0 and len(rings[i - 1]) == 1)]
    for A, Bq in zip(rings, rings[1:]):
        if len(A) == 1 and len(Bq) == 1: continue
        if len(A) == 1:
            for i in range(seg): bm.faces.new((A[0], Bq[(i + 1) % seg], Bq[i]))
        elif len(Bq) == 1:
            for i in range(seg): bm.faces.new((A[i], A[(i + 1) % seg], Bq[0]))
        else:
            for i in range(seg): bm.faces.new((A[i], A[(i + 1) % seg], Bq[(i + 1) % seg], Bq[i]))
    bm.normal_update()
    return obj_from_bm(name, bm, m, c, smooth=True)

def front_uv(o, x0, x1, z0, z1, back=(0.01, 0.99), only_front=True):
    me = o.data
    if not me.uv_layers: me.uv_layers.new(name='UVMap')
    uv = me.uv_layers.active.data
    for poly in me.polygons:
        for li in poly.loop_indices:
            v = me.vertices[me.loops[li].vertex_index].co
            if only_front and v.y > 0.02: uv[li].uv = back
            else: uv[li].uv = ((v.x - x0) / (x1 - x0), (v.z - z0) / (z1 - z0))

def link_dup(o, loc, rot=(0, 0, 0), c=None):
    d = o.copy(); (c or bpy.context.scene.collection).objects.link(d); d.location = loc; d.rotation_euler = rot; return d

def look_rot(src, dst):
    return (Vector(dst) - Vector(src)).to_track_quat('-Y', 'Z').to_euler()

# ------------------------------------------------------------------ ink outlines (Freestyle)
def ink(collection, thickness=5.0, crease=False):
    sc = bpy.context.scene
    sc.render.use_freestyle = True; sc.render.line_thickness_mode = 'ABSOLUTE'
    if DRAFT: thickness *= .5
    vl = bpy.context.view_layer; vl.use_freestyle = True
    fs = vl.freestyle_settings; fs.mode = 'EDITOR'; fs.crease_angle = math.radians(120); fs.use_culling = True
    for ls in list(fs.linesets): fs.linesets.remove(ls)
    ls = fs.linesets.new('ink')
    ls.select_by_visibility = True; ls.visibility = 'VISIBLE'
    ls.select_by_edge_types = True; ls.select_by_collection = True; ls.collection = collection
    ls.select_silhouette = True; ls.select_border = True; ls.select_contour = True; ls.select_external_contour = True
    ls.select_crease = crease; ls.select_material_boundary = False
    st = ls.linestyle; st.color = (0.012, 0.009, 0.014); st.thickness = thickness; st.thickness_position = 'CENTER'; st.caps = 'ROUND'
    st.use_chaining = True; st.chaining = 'PLAIN'; st.use_same_object = True
    try:
        n = st.thickness_modifiers.new('wobble', 'NOISE'); n.amplitude = thickness * .35; n.period = 30
    except Exception as e: log('noise mod', e)
    try:
        g = st.geometry_modifiers.new('hand', 'PERLIN_NOISE_1D'); g.frequency = 6; g.amplitude = .6; g.octaves = 2
    except Exception as e: log('geom mod', e)
    return ls


def hull_outline(collection, width=.014):
    """Cheap ink outline without Freestyle: an inverted shell that is black only where we see its inside."""
    m = bpy.data.materials.new('hullink'); m.use_nodes = True; N = m.node_tree.nodes; L = m.node_tree.links
    N.remove(N['Principled BSDF']); out = N['Material Output']
    geo = N.new('ShaderNodeNewGeometry'); tr = N.new('ShaderNodeBsdfTransparent'); em = N.new('ShaderNodeEmission')
    em.inputs['Color'].default_value = (0.012, 0.009, 0.014, 1); em.inputs['Strength'].default_value = 1.0
    mx = N.new('ShaderNodeMixShader'); L.new(geo.outputs['Backfacing'], mx.inputs['Fac'])
    L.new(tr.outputs[0], mx.inputs[1]); L.new(em.outputs[0], mx.inputs[2]); L.new(mx.outputs[0], out.inputs['Surface'])
    for o in collection.objects:
        if o.type != 'MESH': continue
        o.data.materials.append(m)
        md = o.modifiers.new('hull', 'SOLIDIFY'); md.thickness = -width; md.offset = 1.0
        md.use_flip_normals = True; md.use_rim = False; md.material_offset = len(o.data.materials) - 1
