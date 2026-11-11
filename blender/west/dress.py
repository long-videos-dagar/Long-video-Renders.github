"""Street life for the town set: tied horses at the hitching rails, street lamps, telegraph line with sagging wires,
a festival banner across the street, flags, hay bales, a loaded wagon, a buckboard, a well with a pump, windmills
on the edge of town, store goods on the boardwalks.  Everything heavy is instanced so memory stays flat.

    import dress; dress.dress_street(-30, 60)
"""
import bpy, bmesh, math, os, random, re
from mathutils import Vector, Matrix
import town as T
from town import box, cyl, plain, wood, coll, put, STREET, WALK

HERE = os.path.dirname(os.path.abspath(__file__))
TEX = '/tmp/west_tex'


def _instancer(name, objs):
    """move objects into a hidden collection that can be instanced anywhere"""
    cn = 'PHM_' + name
    c = bpy.data.collections.get(cn)
    if c: return c
    c = bpy.data.collections.new(cn); bpy.context.scene.collection.children.link(c)
    for o in objs:
        for cc in list(o.users_collection): cc.objects.unlink(o)
        c.objects.link(o)
    bpy.context.view_layer.layer_collection.children[cn].exclude = True
    return c


def _inst(col, loc, rot=0.0, scale=(1, 1, 1), name=None):
    e = bpy.data.objects.new(name or (col.name + '_i'), None); e.instance_type = 'COLLECTION'; e.instance_collection = col
    e.location = loc; e.rotation_euler = (0, 0, rot); e.scale = scale; coll('Far').objects.link(e); return e


# ------------------------------------------------------------------ horses at the rails
def tied_horses(y0, y1, avoid=('sheriff', 'bank'), p=.75, keep_clear=()):
    try:
        import horse as HO
        h = HO.HorseGLB('tied', with_tack=True)
    except Exception as e:
        print('tied horses skipped:', e); return []
    h.body.data.materials[0] = coat_vary('tied_coat')
    h.update(0, (0, 0, 0), 0, speed=1.0); h.set_pose(3 / h.kps)
    if getattr(h, 'saddle', None): h._place_tack()
    bpy.context.view_layer.update()
    col = _instancer('tiedhorse', [h.root] + list(h.root.children_recursive))
    rng = random.Random(31); out = []
    for o in list(bpy.data.objects):
        m_ = re.match(r'(.+)_hr(\d)$', o.name)
        if not m_ or o.type != 'MESH' or m_.group(1) in avoid: continue
        x, y = o.location.x, o.location.y
        if not (y0 < y < y1) or rng.random() > p: continue
        if any(abs(y - cy) < 3.8 and x * cx > 0 for (cx, cy) in keep_clear): continue
        side = 1 if x > 0 else -1
        n = 1 if rng.random() < .55 else 2
        for k in range(n):
            py = y + (0 if n == 1 else (-.6 if k == 0 else .6)) + rng.uniform(-.15, .15)
            yaw = math.radians(side * 90 + rng.uniform(-14, 14))
            mir = -1 if rng.random() < .5 else 1
            out.append(_inst(col, (x - side * 1.22, py, 0), yaw, (mir, 1, 1), name=f'tied_{len(out)}'))
    return out


def coat_vary(name):
    """horse coat whose colour changes per instance (bay, chestnut, dark bay, black, grey, palomino)"""
    import horse as HO
    m = HO.glb_coat(name); N, L = m.node_tree.nodes, m.node_tree.links
    ramp = next(n for n in N if n.type == 'VALTORGB')
    oi = N.new('ShaderNodeObjectInfo')
    pal = N.new('ShaderNodeValToRGB'); pal.color_ramp.interpolation = 'CONSTANT'
    cols = ['#7a4424', '#8e4a1e', '#3e2414', '#1c1410', '#8a8682', '#b48c52']
    el = pal.color_ramp.elements
    el[0].position = 0.0; el[0].color = T.hexc(cols[0]) if hasattr(T, 'hexc') else (0, 0, 0, 1)
    el[1].position = 1 / len(cols); el[1].color = T.hexc(cols[1])
    for i, c in enumerate(cols[2:]):
        e = el.new((i + 2) / len(cols)); e.color = T.hexc(c)
    L.new(oi.outputs['Random'], pal.inputs['Fac'])
    # noise ramp becomes a light/dark modulation of the per-instance colour
    ramp.color_ramp.elements[0].color = (.62, .62, .62, 1); ramp.color_ramp.elements[1].color = (1.15, 1.15, 1.15, 1)
    mul = N.new('ShaderNodeMix'); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs['Factor'].default_value = 1.0
    mix = next(n for n in N if n.type == 'MIX' and n is not mul)
    L.new(ramp.outputs['Color'], mul.inputs['A']); L.new(pal.outputs['Color'], mul.inputs['B'])
    L.new(mul.outputs['Result'], mix.inputs['A'])
    return m


# ------------------------------------------------------------------ street furniture
def street_lamps(y0, y1):
    iron = plain('lampiron', '#1e1c1a', .45, .7)
    glass = bpy.data.materials.get('lamp_glass') or plain('lamp_glass', '#f0e0c0', .05, emit='#ffb050', strength=0.0, alpha=1.0, transmit=.4)
    wm = wood('lamppost', '#4a3828', weather=.8, planks=False)
    out = []
    for side in (-1, 1):
        y = y0 + (3 if side > 0 else 9)
        while y < y1:
            x = side * (STREET - WALK - .25)
            cyl(f'lp_post{side}{y:.0f}', .07, 3.4, (x, y, 1.7), wm, v=8)
            box(f'lp_base{side}{y:.0f}', (.22, .22, .3), (x, y, .15), wm)
            box(f'lp_arm{side}{y:.0f}', (.5, .05, .05), (x - side * .2, y, 3.3), iron)
            lx = x - side * .42
            box(f'lp_cap{side}{y:.0f}', (.24, .24, .05), (lx, y, 3.2), iron)
            cyl(f'lp_top{side}{y:.0f}', .1, .12, (lx, y, 3.28), iron, v=6)
            g = box(f'lp_glass{side}{y:.0f}', (.2, .2, .3), (lx, y, 3.02), glass)
            box(f'lp_bot{side}{y:.0f}', (.22, .22, .04), (lx, y, 2.86), iron)
            for dx in (-.1, .1):
                for dy in (-.1, .1): box('lp_bar', (.015, .015, .32), (lx + dx, y + dy, 3.02), iron)
            out.append(Vector((lx, y, 3.02)))
            y += 13.0
    return out


def _wire(name, a, b, sag=.5, r=.008, m=None, n=16):
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = r; cu.bevel_resolution = 1
    sp = cu.splines.new('POLY'); sp.points.add(n)
    for i in range(n + 1):
        u = i / n; p = a.lerp(b, u); p.z -= sag * 4 * u * (1 - u); sp.points[i].co = (*p, 1)
    o = bpy.data.objects.new(name, cu); cu.materials.append(m or plain('wire', '#121212', .5, .6)); return put(o)


def telegraph(y0=-70, y1=130, x=STREET + 21.0):
    tm = wood('pole', '#5a4a3a', weather=.8, planks=False); ins = plain('insulator', '#5a7a6a', .2, transmit=.3)
    tops = []
    for i, yy in enumerate(range(int(y0), int(y1), 26)):
        xx = x + (i % 2) * .4
        cyl(f'tpole{i}', .13, 8.5, (xx, yy, 4.25), tm, v=10)
        box(f'tcross{i}', (2.0, .12, .12), (xx, yy, 7.9), tm)
        tops.append([Vector((xx + dx, yy, 8.02)) for dx in (-.85, -.3, .3, .85)])
        for dx in (-.85, -.3, .3, .85): cyl('tins', .035, .1, (xx + dx, yy, 8.0), ins, v=8)
    for i in range(len(tops) - 1):
        for k in range(4): _wire(f'tw{i}_{k}', tops[i][k], tops[i + 1][k], sag=.55 + k * .04, r=.007)
    # drop line from the street into the telegraph office (it gets its own pole at the boardwalk)
    tel = next((f for f in T.FRONTS if f['name'] == 'telegraph'), None)
    if tel:
        px, py = tel['fx'] - tel['side'] * (WALK + .6), tel['y'] - 2.0
        cyl('tpole_off', .1, 6.2, (px, py, 3.1), tm, v=10); box('tcross_off', (.9, .1, .1), (px, py, 6.0), tm)
        near = min((t[1] for t in tops), key=lambda p: (p - Vector((px, py, 0))).length)
        _wire('tw_off', Vector((px, py, 6.1)), near, sag=.8)
        _wire('tw_off2', Vector((px, py, 6.1)), Vector((tel['fx'] + tel['side'] * .2, tel['y'] - 1.5, 4.0)), sag=.25)


def banner(y, text='TOWN FAIR  SATURDAY', z=5.6, span=STREET - WALK + .3):
    from PIL import Image, ImageDraw, ImageFont
    os.makedirs(TEX, exist_ok=True); p = os.path.join(TEX, 'banner.png')
    W, H = 2400, 300
    im = Image.new('RGB', (W, H), (226, 214, 188)); d = ImageDraw.Draw(im)
    for k in range(3): d.rectangle([0, 18 + k * 0, W, 30], fill=(150, 40, 34)); d.rectangle([0, H - 30, W, H - 18], fill=(150, 40, 34))
    d.rectangle([0, 0, W, 14], fill=(40, 60, 110)); d.rectangle([0, H - 14, W, H], fill=(40, 60, 110))
    f = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf', 170)
    bb = d.textbbox((0, 0), text, font=f); d.text(((W - bb[2]) / 2, (H - bb[3]) / 2 - 18), text, font=f, fill=(46, 32, 24))
    im.save(p)
    m = bpy.data.materials.new('banner'); m.use_nodes = True; N, L = m.node_tree.nodes, m.node_tree.links; b = N['Principled BSDF']
    tx = N.new('ShaderNodeTexImage'); tx.image = bpy.data.images.load(p); L.new(tx.outputs[0], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = .9; b.inputs['Sheen Weight'].default_value = .3
    try: b.inputs['Transmission Weight'].default_value = .0; b.inputs['Subsurface Weight'].default_value = .05
    except Exception: pass
    L_ = span * 2; Hm = L_ * H / W
    bm = bmesh.new(); uv = bm.loops.layers.uv.new('UVMap'); nx, nz = 48, 4; vs = {}
    for i in range(nx + 1):
        for j in range(nz + 1):
            u, v = i / nx, j / nz; x = -span + u * L_
            sag = .45 * 4 * u * (1 - u); wav = .06 * math.sin(u * 19 + 1.3) * math.sin(u * math.pi)
            vs[i, j] = bm.verts.new((x, wav + (1 - v) * .05 * math.sin(u * math.pi), z - Hm / 2 + v * Hm - sag))
    for i in range(nx):
        for j in range(nz):
            f_ = bm.faces.new((vs[i, j], vs[i + 1, j], vs[i + 1, j + 1], vs[i, j + 1]))
            for lp, (a, c) in zip(f_.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))): lp[uv].uv = (a / nx, c / nz)
    me = bpy.data.meshes.new('banner'); bm.to_mesh(me); bm.free(); me.materials.append(m)
    for p_ in me.polygons: p_.use_smooth = True
    o = bpy.data.objects.new('banner', me); o.location = (0, y, 0); put(o)
    s = o.modifiers.new('th', 'SOLIDIFY'); s.thickness = .01
    rope = plain('rope', '#8a7454', .9)
    for sd in (-1, 1):
        _wire(f'banrope{sd}', Vector((sd * span, y, z + Hm / 2)), Vector((sd * (STREET - WALK + .1), y, 3.1 + .2)), sag=.02, r=.012, m=rope)
        _wire(f'banrope_b{sd}', Vector((sd * span, y, z - Hm / 2)), Vector((sd * (STREET - WALK + .1), y + .3, 3.0)), sag=.02, r=.012, m=rope)
    return o


def flag(loc, h=4.0, name='flag'):
    from PIL import Image, ImageDraw
    os.makedirs(TEX, exist_ok=True); p = os.path.join(TEX, 'flag.png')
    if not os.path.exists(p):
        W, H = 760, 400; im = Image.new('RGB', (W, H), (236, 230, 220)); d = ImageDraw.Draw(im)
        for k in range(13):
            if k % 2 == 0: d.rectangle([0, k * H / 13, W, (k + 1) * H / 13], fill=(168, 36, 40))
        d.rectangle([0, 0, W * .4, H * 7 / 13], fill=(40, 52, 104))
        for r_ in range(5):
            for c_ in range(7):
                cx, cy = 18 + c_ * 41 + (r_ % 2) * 8, 20 + r_ * 40
                d.ellipse([cx - 6, cy - 6, cx + 6, cy + 6], fill=(240, 236, 226))
        im.save(p)
    m = bpy.data.materials.get('flagm')
    if not m:
        m = bpy.data.materials.new('flagm'); m.use_nodes = True; N, L = m.node_tree.nodes, m.node_tree.links
        tx = N.new('ShaderNodeTexImage'); tx.image = bpy.data.images.load(p); L.new(tx.outputs[0], N['Principled BSDF'].inputs['Base Color'])
        N['Principled BSDF'].inputs['Roughness'].default_value = .85
    pole = plain('flagpole', '#d8d4cc', .4)
    cyl(name + '_pole', .04, h, (loc[0], loc[1], loc[2] + h / 2), pole, v=8)
    T.lib.sphere(name + '_ball', .07, (loc[0], loc[1], loc[2] + h + .05), plain('brass', '#b8963a', .3, 1.0)) if hasattr(T.lib, 'sphere') else None
    bm = bmesh.new(); uv = bm.loops.layers.uv.new('UVMap'); nx, nz = 24, 6; vs = {}; fw, fh = 1.7, .9
    for i in range(nx + 1):
        for j in range(nz + 1):
            u, v = i / nx, j / nz
            vs[i, j] = bm.verts.new((u * fw * .97, .16 * math.sin(u * 7 + v * .8) * u, -v * fh - .04 * u * u))
    for i in range(nx):
        for j in range(nz):
            f_ = bm.faces.new((vs[i, j], vs[i, j + 1], vs[i + 1, j + 1], vs[i + 1, j]))
            for lp, (a, c) in zip(f_.loops, ((i, j), (i, j + 1), (i + 1, j + 1), (i + 1, j))): lp[uv].uv = (a / nx, 1 - c / nz)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); me.materials.append(m)
    for p_ in me.polygons: p_.use_smooth = True
    o = bpy.data.objects.new(name, me); o.location = (loc[0], loc[1], loc[2] + h - .05); o.rotation_euler = (0, 0, math.radians(110)); put(o)
    return o


def hay_mat():
    m = bpy.data.materials.get('hay')
    if m: return m
    m = bpy.data.materials.new('hay'); m.use_nodes = True; N, L = m.node_tree.nodes, m.node_tree.links; b = N['Principled BSDF']
    tc = N.new('ShaderNodeTexCoord'); mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (60, 60, 4); L.new(tc.outputs['Object'], mp.inputs[0])
    w = N.new('ShaderNodeTexWave'); w.wave_type = 'BANDS'; w.inputs['Scale'].default_value = 1.0; w.inputs['Distortion'].default_value = 12; w.inputs['Detail'].default_value = 6
    L.new(mp.outputs[0], w.inputs['Vector'])
    r = N.new('ShaderNodeValToRGB'); r.color_ramp.elements[0].color = T.hexc('#8a7038'); r.color_ramp.elements[1].color = T.hexc('#d8bc72'); L.new(w.outputs['Fac'], r.inputs['Fac'])
    L.new(r.outputs[0], b.inputs['Base Color']); b.inputs['Roughness'].default_value = .95
    bp = N.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = .5; L.new(w.outputs['Fac'], bp.inputs['Height']); L.new(bp.outputs[0], b.inputs['Normal'])
    return m


def hay_bale(name, loc, rot=0.0, s=1.0):
    o = box(name, (1.0 * s, .5 * s, .42 * s), (loc[0], loc[1], loc[2] + .21 * s), hay_mat(), rot=(0, 0, rot), bevel=.06)
    tw = plain('twine', '#5a4a30', .9)
    for dx in (-.28, .28):
        b = box(name + '_tw', (.02, .51 * s, .43 * s), (0, 0, 0), tw); b.parent = o; b.location = (dx * s, 0, 0)
        b.scale = (1 / 1.0, 1, 1)
    return o


def hay_stack(x, y, side, rng):
    k = 0
    for lay in range(3):
        for i in range(3 - lay):
            hay_bale(f'hay{x:.0f}_{y:.0f}_{k}', (x, y + (i - (2 - lay) / 2) * .55, lay * .42), rot=math.radians(90 + rng.uniform(-6, 6))); k += 1


def buckboard(loc, rot=0.0, load='barrels'):
    m = wood('buckboard', '#6a4a30', weather=.6); iron = plain('iron', '#2a2826', .5, .8)
    e = bpy.data.objects.new('buckboard', None); e.location = loc; e.rotation_euler = (0, 0, rot); coll('Town').objects.link(e)
    parts = [box('bb_bed', (1.4, 2.8, .1), (0, 0, .9), m), box('bb_sl', (.06, 2.8, .35), (-.7, 0, 1.1), m), box('bb_sr', (.06, 2.8, .35), (.7, 0, 1.1), m),
             box('bb_back', (1.4, .06, .35), (0, 1.4, 1.1), m), box('bb_front', (1.4, .06, .5), (0, -1.4, 1.15), m),
             box('bb_seat', (1.3, .4, .08), (0, -1.15, 1.45), m), box('bb_tongue', (.1, 2.4, .1), (0, -2.6, .7), m, rot=(math.radians(-8), 0, 0))]
    for sx in (-1, 1):
        for sy, r in ((-1, .42), (1, .55)):
            bpy.ops.mesh.primitive_torus_add(major_radius=r, minor_radius=.035, location=(sx * .82, sy * 1.0, r), rotation=(0, math.pi / 2, 0))
            w = bpy.context.active_object; w.data.materials.append(iron); put(w); parts.append(w)
            parts.append(cyl('bb_hub', .08, .2, (sx * .82, sy * 1.0, r), m, rot=(0, math.pi / 2, 0), v=10))
            for k in range(10): parts.append(box('bb_spoke', (.03, r * 1.9, .035), (sx * .82, sy * 1.0, r), m, rot=(k / 10 * math.pi, 0, 0)))
        parts.append(box('bb_axle', (1.7, .07, .07), (0, sx * 1.0, .45), iron))
    if load == 'barrels':
        for i, (dx, dy) in enumerate(((-.35, -.7), (.35, -.7), (-.35, .2), (.35, .2))): parts.append(T.barrel(f'bb_bar{i}', (dx, dy, 1.33), r=.27, h=.75))
        for i in range(3): parts.append(T.crate(f'bb_cr{i}', (-.3 + i * .3, 1.0, 1.2), .45, rot=.2 * i))
    else:
        for i in range(4): parts.append(hay_bale(f'bb_hay{i}', (0, -.9 + i * .58, .95), rot=math.radians(90)))
        for i in range(2): parts.append(hay_bale(f'bb_hay2{i}', (0, -.6 + i * .7, 1.37), rot=math.radians(92)))
    for p in parts:
        if p.parent is None: p.parent = e
    return e


def well(loc):
    st = plain('wellstone_p', '#8a8070', .9)
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=.85, depth=.8, location=(loc[0], loc[1], .4)); w = bpy.context.active_object; w.name = 'well'
    w.data.materials.append(st); s = w.modifiers.new('th', 'SOLIDIFY'); s.thickness = .18; put(w)
    bm = bmesh.new(); bm.from_mesh(w.data); bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.normal.z > .9], context='FACES'); bm.to_mesh(w.data); bm.free()
    cyl('well_water', .7, .02, (loc[0], loc[1], .2), plain('wellwater', '#101818', .03))
    m = wood('wellwood', '#5a4430', weather=.7)
    for sx in (-1, 1): box('well_post', (.12, .12, 2.0), (loc[0] + sx * .8, loc[1], 1.2), m)
    box('well_beam', (1.8, .12, .12), (loc[0], loc[1], 2.1), m)
    cyl('well_axle', .08, 1.5, (loc[0], loc[1], 1.75), m, rot=(0, math.pi / 2, 0), v=10)
    for sx in (-1, 1):
        box('well_roof', (2.2, 1.25, .06), (loc[0], loc[1] + sx * .5, 2.45), wood('wellroof', '#4a3a2a', weather=.8), rot=(sx * math.radians(38), 0, 0))
    _wire('well_rope', Vector((loc[0], loc[1], 1.7)), Vector((loc[0], loc[1], .9)), sag=0, r=.012, m=plain('rope', '#8a7454', .9), n=2)
    T.barrel('well_bucket', (loc[0], loc[1], .9), r=.14, h=.26)
    # hand pump and trough beside it
    iron = plain('pumpiron', '#2e3a36', .5, .7)
    cyl('pump', .07, 1.0, (loc[0] + 1.6, loc[1], .5), iron, v=10); cyl('pump_sp', .03, .3, (loc[0] + 1.6, loc[1] - .15, .85), iron, rot=(math.radians(70), 0, 0), v=8)
    box('pump_h', (.04, .6, .04), (loc[0] + 1.6, loc[1] + .25, 1.1), iron, rot=(math.radians(-25), 0, 0))
    T.water_trough((loc[0] + 1.6, loc[1] - 1.3, 0))


def windmill(loc, h=9.0, name='wmill'):
    m = wood('wmill', '#6a5a48', weather=.85, planks=False); iron = plain('wm_iron', '#4a4844', .6, .5)
    for sx in (-1, 1):
        for sy in (-1, 1):
            a = Vector((loc[0] + sx * 1.4, loc[1] + sy * 1.4, 0)); b = Vector((loc[0] + sx * .3, loc[1] + sy * .3, h))
            d = b - a; mid = (a + b) / 2
            o = cyl(name + '_leg', .07, d.length, mid, m, v=6); o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = d.to_track_quat('Z', 'Y')
    for k in range(5):
        z = 1.2 + k * (h - 1.5) / 5; w = 1.4 - (1.1 * z / h)
        for r in range(4):
            box(name + '_br', (w * 2, .06, .06), (loc[0], loc[1], z), m, rot=(0, 0, r * math.pi / 2)).location = (loc[0] + (w if r == 1 else -w if r == 3 else 0), loc[1] + (w if r == 0 else -w if r == 2 else 0), z)
    hub = Vector((loc[0], loc[1] - .5, h + .3))
    cyl(name + '_hub', .15, .3, hub, iron, rot=(math.pi / 2, 0, 0), v=12)
    for k in range(18):
        a = k / 18 * math.tau
        bl = box(name + '_bl', (.24, .02, 1.5), (hub.x + math.cos(a) * 1.1, hub.y - .05, hub.z + math.sin(a) * 1.1), iron, rot=(0, -a + math.pi / 2, 0))
        bl.rotation_euler = (math.radians(15), -a + math.pi / 2, 0)
    bpy.ops.mesh.primitive_torus_add(major_radius=1.85, minor_radius=.025, location=hub - Vector((0, .05, 0)), rotation=(math.pi / 2, 0, 0))
    t = bpy.context.active_object; t.data.materials.append(iron); put(t)
    box(name + '_tailb', (.06, 2.2, .06), (loc[0], loc[1] + .8, h + .3), iron)
    box(name + '_vane', (.02, 1.2, .8), (loc[0], loc[1] + 1.9, h + .4), plain('wm_vane', '#a8a49a', .7))
    T.water_trough((loc[0] + 2.2, loc[1], 0))


def goods(y0, y1):
    """brooms, shovels, a barrel of apples, sacks and a bench on store boardwalks"""
    rng = random.Random(91)
    straw = plain('broomstraw', '#c8a860', .9); stick = wood('handle', '#8a6a48', planks=False); steel = plain('shovel', '#5a5a58', .5, .8)
    apple = plain('apple', '#9a2418', .45); sack = plain('sackm', '#9a8460', .95)
    for f in T.FRONTS:
        if not (y0 < f['y'] < y1) or not f['porch'] or rng.random() < .35: continue
        s = f['side']; wx = f['fx'] - s * .35
        y = f['y'] + rng.choice((-1, 1)) * rng.uniform(1.3, f['w'] / 2 - .5)
        kind = rng.choice(['tools', 'apples', 'sacks', 'tools', 'sacks'])
        if kind == 'tools':
            for k in range(rng.randint(2, 4)):
                yy = y + k * .22; tilt = math.radians(rng.uniform(8, 14))
                cyl('br_st', .016, 1.3, (wx - s * .1, yy, .34 + .65), stick, rot=(0, s * tilt, 0), v=6)
                if k % 2 == 0: cyl('br_hd', .09, .35, (wx - s * .02, yy, .34 + .1), straw, rot=(0, s * tilt, 0), v=8)
                else: box('sh_bl', (.03, .22, .28), (wx - s * .0, yy, .34 + .12), steel, rot=(0, s * tilt, 0))
        elif kind == 'apples':
            T.barrel(f'ab{f["name"]}', (wx - s * .2, y, .34), r=.28, h=.7)
            for k in range(14):
                a = rng.uniform(0, math.tau); r = rng.uniform(0, .2)
                cyl('apl', .045, .08, (wx - s * .2 + math.cos(a) * r, y + math.sin(a) * r, .34 + .72 + rng.uniform(0, .05)), apple, v=8)
        else:
            for k in range(rng.randint(2, 4)):
                o = T.lib.sphere('sack', .28, (wx - s * .25, y + k * .45, .34 + .2), sack, seg=12, rings=8, scale=(1, .8, .75)) if hasattr(T.lib, 'sphere') else None
                if o: put(o)


def dress_street(y0=-35, y1=65):
    """everything that makes the street feel lived in"""
    out = {}
    WAG = ((3.3, 38.0), (-3.3, 27.5))
    try: out['horses'] = tied_horses(y0, y1, keep_clear=WAG + ((-4, -16.0),))
    except Exception as e: print('tied horses failed', e)
    out['lamps'] = street_lamps(y0, y1)
    telegraph()
    banner(17.2)
    for (x, y) in ((STREET + 3.5, 22.0), (-STREET - 3.0, 12.0)):
        flag((x, y, 7.4 if y == 22.0 else 5.6))
    rng = random.Random(4)
    hay_stack(-STREET + WALK + 1.0, -16.0, -1, rng)
    hay_bale('hay_l1', (-STREET + WALK + 1.1, -14.2, 0), rot=.3)
    buckboard((WAG[0][0], WAG[0][1], 0), math.radians(4), 'barrels')
    buckboard((WAG[1][0], WAG[1][1], 0), math.radians(178), 'hay')
    well((-1.8, 44.0))
    windmill((-24.0, 58.0)); windmill((30.0, -34.0), h=8.0, name='wmill2')
    goods(y0, y1)
    return out
