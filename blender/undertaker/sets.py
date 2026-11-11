"""Set pieces for THE UNDERTAKER'S BEST CUSTOMER: Boot Hill graveyard (a real hill with an open grave cut into it),
coffins (pine, short, velvet) with hinged lids, headstones with readable painted text, the undertaker's shop
interior, brass band instruments, paper props (complaint form, bill, sympathy card), funeral dressing."""
import bpy, bmesh, math, os, random
from mathutils import Vector, Matrix
import town as T
from town import box, cyl, plain, wood, coll, put

TEX = '/tmp/ut_tex'
G = Vector((0.0, 96.0, 0.0))        # Boot Hill centre
HILL_H = 1.6                          # hilltop height
PIT = (Vector((0.0, 96.0, 0)), 2.6, 1.3, 1.45)   # centre, length (along y), width, depth


def ground_z(x, y):
    """height of Boot Hill at (x, y) (0 off the hill)"""
    dx, dy = abs(x - G.x) / 17.0, abs(y - G.y) / 15.0
    r = max(dx, dy * .9, math.hypot(dx, dy) * .82)
    u = max(0.0, min(1.0, (1.0 - r) / .45))
    return HILL_H * u * u * (3 - 2 * u)


def _tex(name, size, draw):
    from PIL import Image, ImageDraw
    os.makedirs(TEX, exist_ok=True); p = os.path.join(TEX, name + '.png')
    im = Image.new('RGB', size, (200, 190, 170)); d = ImageDraw.Draw(im); draw(im, d); im.save(p)
    m = bpy.data.materials.new(name); m.use_nodes = True; N, L = m.node_tree.nodes, m.node_tree.links
    tx = N.new('ShaderNodeTexImage'); tx.image = bpy.data.images.load(p); tx.interpolation = 'Cubic'
    L.new(tx.outputs[0], N['Principled BSDF'].inputs['Base Color']); N['Principled BSDF'].inputs['Roughness'].default_value = .85
    return m


def _font(sz, bold=True, serif=True):
    from PIL import ImageFont
    f = '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf' if serif else '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
    return ImageFont.truetype(f, sz)


def plane_tex(name, w, h, loc, mat, rot=(0, 0, 0)):
    """vertical/flat textured quad with proper UVs (text reads correctly from the front, -Y side)"""
    me = bpy.data.meshes.new(name); bm = bmesh.new(); uv = bm.loops.layers.uv.new('UVMap')
    vs = [bm.verts.new(p) for p in ((-w / 2, 0, -h / 2), (w / 2, 0, -h / 2), (w / 2, 0, h / 2), (-w / 2, 0, h / 2))]
    f = bm.faces.new(vs)
    for lp, (a, c) in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))): lp[uv].uv = (a, c)
    bm.to_mesh(me); bm.free(); me.materials.append(mat)
    o = bpy.data.objects.new(name, me); o.location = loc; o.rotation_euler = rot; put(o); return o


# ------------------------------------------------------------------ Boot Hill
def boot_hill():
    """the hill (grid mesh with an open grave cut into it), picket fence, gate arch, headstones, dead tree"""
    c, L_, W_, D_ = PIT
    me = bpy.data.meshes.new('boothill'); bm = bmesh.new(); step = .5; vs = {}
    xs = [G.x - 19 + k * step for k in range(int(38 / step) + 1)]; ys = [G.y - 17 + k * step for k in range(int(34 / step) + 1)]
    rng = random.Random(3)
    for i, x in enumerate(xs):
        for j, y in enumerate(ys):
            z = ground_z(x, y) + (rng.uniform(-.03, .03) if ground_z(x, y) > .05 else -.02)
            vs[i, j] = bm.verts.new((x, y, z))
    pit = lambda x, y: abs(x - c.x) < W_ / 2 - 1e-3 and abs(y - c.y) < L_ / 2 - 1e-3
    for i in range(len(xs) - 1):
        for j in range(len(ys) - 1):
            cx_, cy_ = (xs[i] + xs[i + 1]) / 2, (ys[j] + ys[j + 1]) / 2
            if abs(cx_ - c.x) < W_ / 2 and abs(cy_ - c.y) < L_ / 2: continue
            bm.faces.new((vs[i, j], vs[i + 1, j], vs[i + 1, j + 1], vs[i, j + 1]))
    bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    hill = bpy.data.objects.new('boothill', me); put(hill, 'Far')
    soil = T.ph_or('hill_ground', ('@dry_ground_01',), lambda: T.dirt('hilldirt'), scale=2.5, avoid=('snow', 'moss'))
    me.materials.append(soil)
    # pit walls + floor (dark damp earth)
    earth = plain('grave_earth', '#4a3a2c', .95)
    top = HILL_H; bot = top - D_
    for sx in (-1, 1):
        box(f'pitwall_x{sx}', (.08, L_, D_), (c.x + sx * W_ / 2, c.y, (top + bot) / 2 - .02), earth)
    for sy in (-1, 1):
        box(f'pitwall_y{sy}', (W_, .08, D_), (c.x, c.y + sy * L_ / 2, (top + bot) / 2 - .02), earth)
    box('pitfloor', (W_, L_, .06), (c.x, c.y, bot), earth)
    # dirt mound beside the grave + shovel
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=12, radius=1)
    for v in bm.verts:
        v.co.z = max(0, v.co.z) * .55; v.co.x *= 1.3; v.co.y *= 1.6
        v.co += Vector((rng.uniform(-.06, .06), rng.uniform(-.06, .06), rng.uniform(0, .05) if v.co.z > .05 else 0))
    mm = bpy.data.meshes.new('mound'); bm.to_mesh(mm); bm.free(); mm.materials.append(earth)
    for p in mm.polygons: p.use_smooth = True
    mo = bpy.data.objects.new('mound', mm); mo.location = (c.x + 2.1, c.y + .3, top - .05); put(mo)
    shovel(Vector((c.x + 1.3, c.y - 1.4, top)), 18)
    # picket fence around the plot with a gate arch facing town (-y)
    fw = wood('fence', '#8a7a62', weather=.9, planks=False)
    x0, x1, y0, y1 = G.x - 12, G.x + 12, G.y - 10, G.y + 10
    def fence_run(a, b):
        n = int((b - a).length / .32)
        for k in range(n + 1):
            p = a.lerp(b, k / max(1, n))
            if abs(p.x - G.x) < 1.6 and abs(p.y - y0) < .2: continue          # gate gap
            z = ground_z(p.x, p.y)
            box('picket', (.08, .08, 1.0 + .08 * (k % 2)), (p.x, p.y, z + .5), fw)
        for h_ in (.35, .8):
            d = b - a; mid = (a + b) / 2; zz = ground_z(mid.x, mid.y) + h_
            r = box('rail', (d.length if abs(d.x) > abs(d.y) else .05, d.length if abs(d.y) > abs(d.x) else .05, .06), (mid.x, mid.y, zz), fw)
    for a, b in ((Vector((x0, y0, 0)), Vector((x1, y0, 0))), (Vector((x1, y0, 0)), Vector((x1, y1, 0))), (Vector((x1, y1, 0)), Vector((x0, y1, 0))), (Vector((x0, y1, 0)), Vector((x0, y0, 0)))):
        fence_run(a, b)
    gz = ground_z(G.x, y0)
    for sx in (-1, 1): box('gatepost', (.2, .2, 3.4), (G.x + sx * 1.6, y0, gz + 1.7), fw)
    sign = _tex('boothill_sign', (1200, 260), lambda im, d: (d.rectangle([0, 0, 1200, 260], fill=(214, 200, 168)), d.rectangle([12, 12, 1188, 248], outline=(60, 40, 30), width=8),
                                                            d.text((600, 132), 'BOOT HILL', font=_font(170), fill=(52, 30, 22), anchor='mm')))
    box('gatebeam', (3.6, .14, .2), (G.x, y0, gz + 3.3), fw)
    plane_tex('gatesign', 3.0, .65, (G.x, y0 - .08, gz + 2.8), sign)
    plane_tex('gatesign_in', 3.0, .65, (G.x, y0 + .08, gz + 2.8), sign, rot=(0, 0, math.pi))
    # headstones in loose rows (names painted, readable), the four EZRA PIKE graves near the front
    rng = random.Random(11)
    names = ['J. MORGAN', 'ED "LUCKY" HART', 'OLD TOM', 'SALLY RAE', 'B. COLLINS', 'DOC WEBB', 'HANK DUBOIS', 'MAE LOWELL', 'ONE-EYED PETE', 'C. BRENNAN',
             'WM. STONE', 'LITTLE JOE', 'R. KANE', 'AMOS REED', 'NED FARRIS', 'ROSE ADAIR', 'I. MILLER', 'S. GRAVES']
    spots = []
    for row in range(3):
        for k in range(7):
            x = G.x - 9 + k * 3.0 + rng.uniform(-.4, .4); y = G.y + 2.8 + row * 2.6 + rng.uniform(-.3, .3)
            if abs(x - c.x) < 2.2 and abs(y - c.y) < 2.2: continue
            spots.append((x, y))
    for k, (x, y) in enumerate(spots[:len(names)]):
        headstone(f'hs{k}', (x, y), names[k], f'18{rng.randint(55, 79)}', kind=rng.choice(['cross', 'slab', 'slab', 'board']), tilt=rng.uniform(-8, 8))
    for k, (dt, x) in enumerate((('MAR 3', -6.0), ('APR 9', -3.6), ('MAY 21', 3.6), ('JUN 2', 6.0))):
        headstone(f'ezra{k}', (G.x + x, G.y - 4.2), 'EZRA PIKE', dt + ' 1880', kind='board', tilt=(k - 1.5) * 3, crossed=True)
        gm = bpy.data.objects.new(f'ezmound{k}', mm); gm.location = (G.x + x, G.y - 3.0, ground_z(G.x + x, G.y - 3.0) - .06); gm.scale = (.42, .62, .45); put(gm)
        flowers(f'ezfl{k}', (G.x + x + .05, G.y - 4.0, ground_z(G.x + x, G.y - 4.0)), n=3, spread=.15)
    dead_tree((G.x + 9.5, G.y + 8.5))
    dead_tree((G.x - 10.5, G.y + 6.0), s=.8)
    return hill


def headstone(name, xy, who, date, kind='slab', tilt=0.0, crossed=False):
    x, y = xy; z = ground_z(x, y)
    def draw(im, d):
        W, H = im.size
        if kind == 'slab': d.rectangle([0, 0, W, H], fill=(150, 148, 140))
        else: d.rectangle([0, 0, W, H], fill=(176, 150, 112))
        f1 = _font(int(W * .13)); f2 = _font(int(W * .09))
        d.text((W / 2, H * .22), 'R.I.P.', font=f2, fill=(40, 34, 30), anchor='mm')
        d.text((W / 2, H * .45), who, font=f1 if len(who) < 11 else _font(int(W * .1)), fill=(30, 24, 20), anchor='mm')
        d.text((W / 2, H * .66), date, font=f2, fill=(40, 34, 30), anchor='mm')
        if crossed:
            d.line([(W * .1, H * .32), (W * .9, H * .58)], fill=(170, 30, 30), width=int(W * .035))
            d.text((W / 2, H * .86), 'NOT DEAD', font=_font(int(W * .1), serif=False), fill=(170, 30, 30), anchor='mm')
    m = _tex(name + '_t', (520, 640), draw)
    if kind == 'cross':
        w = wood(name + 'w', '#6a5440', weather=.9, planks=False)
        box(name + '_v', (.14, .1, 1.3), (x, y, z + .65), w, rot=(0, math.radians(tilt), 0)); box(name + '_h', (.75, .1, .14), (x, y, z + 1.0), w, rot=(0, math.radians(tilt), 0))
        return
    w, h = (.62, .78) if kind == 'slab' else (.58, .72)
    stone = plain(name + '_s', '#8f8c84', .85) if kind == 'slab' else wood(name + 'w', '#8a6a48', weather=.9, planks=False)
    body = box(name, (w, .12, h), (x, y, z + h / 2), stone, rot=(math.radians(-4), math.radians(tilt), 0), bevel=.03 if kind == 'slab' else 0)
    face = plane_tex(name + '_face', w * .9, h * .85, (0, -.065, 0), m)
    face.parent = body; face.location = (0, -.062, 0)


def shovel(p, ang=15):
    st = wood('shovelh', '#8a6a48', planks=False); steel = plain('shovelsteel', '#5a5a5c', .45, .8)
    cyl('shovel_h', .022, 1.3, p + Vector((0, 0, .75)), st, rot=(math.radians(ang), 0, 0), v=8)
    box('shovel_b', (.24, .03, .3), p + Vector((0, -.18, .12)), steel, rot=(math.radians(ang), 0, 0))


def dead_tree(xy, s=1.0):
    x, y = xy; z = ground_z(x, y); bark = plain('deadbark', '#3a3028', .95)
    rng = random.Random(int(x * 10 + y))
    def branch(p, d, l, r, depth):
        e = p + d * l; mid = (p + e) / 2
        o = cyl('tb', r, l, mid, bark, v=8); o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = d.to_track_quat('Z', 'Y')
        if depth == 0: return
        for _ in range(2 if depth < 3 else 3):
            nd = (d + Vector((rng.uniform(-.8, .8), rng.uniform(-.8, .8), rng.uniform(-.1, .5)))).normalized()
            branch(e, nd, l * rng.uniform(.55, .75), r * .62, depth - 1)
    branch(Vector((x, y, z - .1)), Vector((0, 0, 1)), 2.6 * s, .2 * s, 4)


# ------------------------------------------------------------------ coffins
def coffin_mesh(name, length=2.15, w_sh=.82, w_head=.56, w_foot=.46, h=.5, inner=False):
    """toe-pinch coffin outline (widest at the shoulders), extruded; origin at the head end centre, bottom.
    The coffin runs along +Y from the head (y=0) to the foot (y=length)."""
    sh_y = length * .26
    pts = [(-w_head / 2, 0), (-w_sh / 2, sh_y), (-w_foot / 2, length), (w_foot / 2, length), (w_sh / 2, sh_y), (w_head / 2, 0)]
    bm = bmesh.new(); bot = [bm.verts.new((x, y, 0)) for x, y in pts]; topv = [bm.verts.new((x, y, h)) for x, y in pts]
    bm.faces.new(list(reversed(bot)))
    for i in range(6):
        j = (i + 1) % 6; bm.faces.new((bot[i], bot[j], topv[j], topv[i]))
    if not inner: bm.faces.new(topv)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); return me, pts


class Coffin:
    """coffin with a lid hinged on its left edge (lid.rotation_euler.y opens it) or lifted free (lid_free)."""
    def __init__(self, name, loc, yaw=0.0, kind='pine', length=2.15, scale=1.0):
        self.name = name
        self.root = bpy.data.objects.new(name, None); self.root.location = loc; self.root.rotation_euler = (0, 0, math.radians(yaw)); put(self.root)
        self.root.scale = (scale, scale, scale)
        woodm = {'pine': wood('coffin_pine', '#a4774a', weather=.35), 'dark': wood('coffin_dark', '#4a2a1c', weather=.1),
                 'velvet': wood('coffin_rose', '#3a1c14', weather=.05)}[kind]
        h = .5
        me, pts = coffin_mesh(name + '_box', length, h=h, inner=True)
        me.materials.append(woodm); box_o = bpy.data.objects.new(name + '_box', me); put(box_o); box_o.parent = self.root
        s = box_o.modifiers.new('th', 'SOLIDIFY'); s.thickness = .045; s.offset = -1
        lining = plain(name + '_lining', '#8a2c78', .95, emit='#5a1650', strength=.5) if kind == 'velvet' else plain(name + '_lining', '#e8e0d0' if kind == 'pine' else '#c8b8a0', .95)
        if kind == 'velvet':
            lining.node_tree.nodes['Principled BSDF'].inputs['Sheen Weight'].default_value = 1.0
            lining.node_tree.nodes['Principled BSDF'].inputs['Sheen Tint'].default_value = (1, .6, .9, 1)
        lm, _ = coffin_mesh(name + '_lin', length - .08, .74, .5, .4, .06); lm.materials.append(lining)
        lo = bpy.data.objects.new(name + '_lin', lm); lo.location = (0, .04, .06); put(lo); lo.parent = self.root
        pil = cyl(name + '_pillow', .2, .14, (0, .25, .14), lining, rot=(0, math.pi / 2, 0), v=16); pil.scale = (1, 1, 1.6); pil.parent = self.root
        # handles
        gold = plain('coffin_brass', '#c8a040', .3, 1.0) if kind == 'velvet' else plain('coffin_iron', '#3a3a3a', .5, .8)
        for k in (.5, 1.05, 1.6):
            for sx in (-1, 1):
                wx = (.82 if k < .8 else .7) / 2 + .03
                bar = cyl(name + '_hdl', .018, .22, (sx * wx, k * length / 2.15, .25), gold, rot=(math.pi / 2, 0, 0), v=8); bar.parent = self.root
        # lid: hinged along the left edge (x = -w/2) -> pivot empty
        self.hinge = bpy.data.objects.new(name + '_hinge', None); self.hinge.location = (-.41, 0, h); put(self.hinge); self.hinge.parent = self.root
        lmesh, _ = coffin_mesh(name + '_lid', length, h=.07); lmesh.materials.append(woodm)
        self.lid = bpy.data.objects.new(name + '_lid', lmesh); self.lid.location = (.41, 0, 0); put(self.lid); self.lid.parent = self.hinge
        if kind != 'pine':
            cr = plain('lidcross', '#c8a040', .3, 1.0)
            box(name + '_lc1', (.06, .7, .02), (0, length * .45, .08), cr).parent = self.lid; box(name + '_lc2', (.34, .06, .02), (0, length * .32, .08), cr).parent = self.lid
            for o in list(self.lid.children): o.location.x += 0
        self.length = length

    def open(self, a):            # 0 closed .. 1 fully open (lid swung over to the left side)
        self.hinge.rotation_euler = (0, -math.radians(115) * a, 0)

    def world(self, p):           # from loc/rot/scale directly: matrix_world is stale until the next depsgraph update
        r = self.root
        return Matrix.LocRotScale(r.location, r.rotation_euler, r.scale) @ Vector(p)


# ------------------------------------------------------------------ the undertaker's shop (interior set)
def shop_interior(at=Vector((-40.0, -60.0, 0)), lamp=True):
    """plank room 7 x 9 m: coffins standing along the walls, a half-built coffin on sawhorses, a counter with a ledger
    and a price board, a window with daylight, hanging lantern."""
    x0, y0 = at.x, at.y; W, D, H = 7.0, 9.0, 3.6
    floor = wood('shop_floor', '#5a4030', weather=.6); wall = wood('shop_wall', '#6a5240', weather=.7); dark = plain('shop_dark', '#2a2420', .9)
    box('s_floor', (W, D, .1), (x0, y0, -.05), floor); box('s_ceil', (W, D, .1), (x0, y0, H), wall)
    box('s_back', (W, .15, H), (x0, y0 + D / 2, H / 2), wall); box('s_left', (.15, D, H), (x0 - W / 2, y0, H / 2), wall)
    box('s_right_a', (.15, D * .3, H), (x0 + W / 2, y0 - D * .35, H / 2), wall); box('s_right_b', (.15, D * .3, H), (x0 + W / 2, y0 + D * .35, H / 2), wall)
    box('s_right_top', (.15, D * .4, .9), (x0 + W / 2, y0, H - .45), wall); box('s_right_bot', (.15, D * .4, 1.0), (x0 + W / 2, y0, .5), wall)
    gl = plain('s_glass', '#d8e4ee', .05, transmit=.9); box('s_window', (.04, D * .4, H - 1.9), (x0 + W / 2, y0, 1.0 + (H - 1.9) / 2), gl)
    for k in range(-3, 4): box('s_beam', (W, .14, .16), (x0, y0 + k * 1.3, H - .1), dark)
    # coffins standing against the back and left walls
    for k in range(4):
        cf = Coffin(f's_cof{k}', (x0 - 2.4 + k * 1.25, y0 + D / 2 - .45, .05), yaw=0, kind=['pine', 'dark', 'pine', 'dark'][k], length=2.0)
        cf.root.rotation_euler = (math.radians(-80), 0, math.pi)
        cf.root.location = (x0 - 2.4 + k * 1.25, y0 + D / 2 - .5, 2.05)
    for k in range(3):
        cf = Coffin(f's_cofl{k}', (x0 - W / 2 + .45, y0 - 2.2 + k * 1.3, 2.05), yaw=0, kind='pine', length=2.0)
        cf.root.rotation_euler = (math.radians(-80), 0, math.radians(-90))
    # sawhorses + half-built coffin, planks, saw
    for sy in (-1, 1):
        for sx in (-1, 1):
            box('sawleg', (.06, .06, .8), (x0 + 1.0 + sx * .35, y0 + 1.6 + sy * .7, .4), floor, rot=(0, math.radians(sx * 10), 0))
        box('sawtop', (.9, .1, .1), (x0 + 1.0, y0 + 1.6 + sy * .7, .8), floor)
    cf = Coffin('s_build', (x0 + 1.0, y0 + .55, .85), yaw=0, kind='pine', length=2.0); cf.open(1.0); cf.lid.hide_render = True
    for k in range(5): box('plank', (.22, 2.2, .04), (x0 + 2.6, y0 - 2.6 + k * .01, .06 + k * .045), floor, rot=(0, 0, math.radians(k * 3)))
    # counter, ledger, price board
    ctr = wood('s_counter', '#3a2a1e', weather=.3)
    box('s_counter', (3.0, .8, 1.05), (x0 - 1.2, y0 - 2.6, .52), ctr); box('s_ctop', (3.2, .95, .06), (x0 - 1.2, y0 - 2.6, 1.07), ctr)
    def price(im, d):
        W_, H_ = im.size; d.rectangle([0, 0, W_, H_], fill=(30, 26, 22)); f = _font(64); f2 = _font(52)
        d.text((W_ / 2, 70), 'PRICES', font=f, fill=(230, 220, 190), anchor='mm')
        for k, (a, b) in enumerate((('PINE BOX', '$20'), ('OAK', '$40'), ('VELVET', '$200'), ('CRYING', '$1 EACH'))):
            d.text((60, 170 + k * 95), a, font=f2, fill=(230, 220, 190), anchor='lm'); d.text((W_ - 60, 170 + k * 95), b, font=f2, fill=(230, 200, 120), anchor='rm')
    plane_tex('s_priceboard', 1.6, 1.25, (x0 - 1.2, y0 + D / 2 - .1, 2.9), _tex('priceboard', (800, 620), price))
    ledger = plain('s_ledger', '#5a2a22', .7); box('s_ledger', (.5, .36, .05), (x0 - .8, y0 - 2.6, 1.125), ledger)
    if lamp:
        l = bpy.data.lights.new('s_lamp', 'POINT'); l.energy = 260; l.color = (1, .72, .42); l.shadow_soft_size = .15
        lo = bpy.data.objects.new('s_lamp', l); lo.location = (x0 - .4, y0 - 1.0, 2.8); put(lo)
        T.lantern('s_lantern', (x0 - .4, y0 - 1.0, 2.75), energy=40)
    sun_ = bpy.data.lights.new('s_window_l', 'AREA'); sun_.energy = 1100; sun_.size = 3.0; sun_.color = (1, .9, .78)
    so = bpy.data.objects.new('s_window_l', sun_); so.location = (x0 + W / 2 + .8, y0, 2.0); so.rotation_euler = (0, math.radians(-90), 0); put(so)
    fill = bpy.data.lights.new('s_fill', 'AREA'); fill.energy = 220; fill.size = 4; fill.color = (.8, .85, 1.0)
    fo = bpy.data.objects.new('s_fill', fill); fo.location = (x0 - 1.0, y0 - 3.5, 3.2); fo.rotation_euler = (math.radians(30), 0, 0); put(fo)
    return dict(origin=at, counter=Vector((x0 - 1.2, y0 - 2.6, 1.1)))


# ------------------------------------------------------------------ paper props
def paper(name, kind, loc, rot=(0, 0, 0), w=.32, h=.42):
    def complaint(im, d):
        W_, H_ = im.size; d.rectangle([0, 0, W_, H_], fill=(236, 226, 200)); f = _font(56); f2 = _font(34, serif=False); f3 = _font(30)
        d.text((W_ / 2, 70), 'COMPLAINT', font=f, fill=(40, 30, 24), anchor='mm')
        d.line([(40, 115), (W_ - 40, 115)], fill=(40, 30, 24), width=4)
        rows = [('SERVICE:', 'TERRIBLE'), ('COFFIN:', 'TOO SMALL'), ('MOURNERS:', 'NONE'), ('PRIEST:', 'BORING')]
        for k, (a, b) in enumerate(rows):
            d.text((40, 180 + k * 80), a, font=f2, fill=(60, 50, 40), anchor='lm'); d.text((290, 180 + k * 80), b, font=f3, fill=(30, 40, 120), anchor='lm')
        d.text((W_ / 2, H_ - 70), 'SIGNED: EZRA PIKE', font=f3, fill=(30, 40, 120), anchor='mm')
    def bill(im, d):
        W_, H_ = im.size; d.rectangle([0, 0, W_, H_], fill=(240, 234, 214)); f = _font(50); f2 = _font(36)
        d.text((W_ / 2, 70), 'INVOICE', font=f, fill=(40, 30, 24), anchor='mm')
        d.text((40, 170), 'FUNERAL ....... $20', font=f2, fill=(40, 30, 24), anchor='lm')
        d.text((40, 240), 'REPEAT ........ x2', font=f2, fill=(40, 30, 24), anchor='lm')
        d.text((40, 330), 'TOTAL ......... $40', font=f2, fill=(40, 30, 24), anchor='lm')
        d.rectangle([150, 380, 450, 470], outline=(180, 30, 30), width=8); d.text((300, 425), 'DOUBLE', font=_font(54, serif=False), fill=(180, 30, 30), anchor='mm')
    def card(im, d):
        W_, H_ = im.size; d.rectangle([0, 0, W_, H_], fill=(232, 236, 240)); d.rectangle([14, 14, W_ - 14, H_ - 14], outline=(90, 90, 110), width=5)
        d.text((W_ / 2, H_ * .3), 'SORRY FOR', font=_font(54), fill=(40, 40, 60), anchor='mm'); d.text((W_ / 2, H_ * .45), 'YOUR LOSS', font=_font(54), fill=(40, 40, 60), anchor='mm')
        d.text((W_ / 2, H_ * .62), '(AGAIN)', font=_font(46), fill=(150, 40, 40), anchor='mm'); d.text((W_ / 2, H_ * .82), '- FATHER JOE', font=_font(34), fill=(60, 60, 80), anchor='mm')
    draw = {'complaint': complaint, 'bill': bill, 'card': card}[kind]
    size = (600, 800) if kind != 'card' else (640, 480)
    m = _tex(f'paper_{kind}', size, draw)
    return plane_tex(name, w, h, loc, m, rot)


# ------------------------------------------------------------------ brass band instruments (held in a toon's hands)
def instrument(name, kind):
    brass = plain('band_brass', '#d4a83c', .25, 1.0)
    e = bpy.data.objects.new(name, None); put(e)
    if kind == 'tuba':
        bpy.ops.mesh.primitive_torus_add(major_radius=.22, minor_radius=.06, major_segments=32, minor_segments=10); t = bpy.context.active_object; put(t); t.data.materials.append(brass); t.parent = e; t.rotation_euler = (0, math.pi / 2, 0)
        bell = cyl(name + '_bell', .26, .3, (0, 0, .42), brass, v=24); bell.parent = e
        bm = bell.data; [setattr(v.co, 'x', v.co.x * (1.0 if v.co.z > 0 else .35)) or setattr(v.co, 'y', v.co.y * (1.0 if v.co.z > 0 else .35)) for v in bm.vertices]
        cyl(name + '_pipe', .05, .5, (0, .1, .1), brass, v=10).parent = e
    elif kind == 'trumpet':
        p = cyl(name + '_tube', .022, .5, (0, -.2, 0), brass, rot=(math.pi / 2, 0, 0), v=10); p.parent = e
        bell = cyl(name + '_bell', .08, .14, (0, -.5, 0), brass, rot=(math.pi / 2, 0, 0), v=20); bell.parent = e
        for v in bell.data.vertices:
            k = .3 if v.co.z < 0 else 1.0; v.co.x *= k; v.co.y *= k
        for dx in (-.03, 0, .03): cyl(name + '_valve', .012, .1, (dx, -.15, .05), brass, v=8).parent = e
    else:   # bass drum
        dr = cyl(name + '_drum', .3, .26, (0, 0, 0), plain('drumskin', '#ece4d4', .7), rot=(0, math.pi / 2, 0), v=28); dr.parent = e
        for sx in (-1, 1): cyl(name + '_rim', .31, .04, (sx * .14, 0, 0), plain('drumrim', '#8a2a24', .5), rot=(0, math.pi / 2, 0), v=28).parent = e
    return e


def bench(name, loc, yaw=0, length=2.4):
    w = wood('bench', '#7a5a40', weather=.7)
    e = bpy.data.objects.new(name, None); e.location = loc; e.rotation_euler = (0, 0, math.radians(yaw)); put(e)
    box(name + '_seat', (length, .38, .06), (0, 0, .46), w).parent = e
    for sx in (-1, 1): box(name + '_leg', (.06, .34, .46), (sx * (length / 2 - .2), 0, .23), w).parent = e
    return e


def wreath(name, loc, r=.35):
    bpy.ops.mesh.primitive_torus_add(major_radius=r, minor_radius=r * .22, major_segments=28, minor_segments=8, location=loc, rotation=(math.pi / 2, 0, 0))
    o = bpy.context.active_object; o.name = name; put(o); o.data.materials.append(plain('wreath', '#2e4a2a', .8))
    fl = plain('flowers', '#d8d0c8', .7); rng = random.Random(len(name))
    for k in range(10):
        a = k / 10 * math.tau
        T.lib.sphere(name + '_f', .055, (loc[0] + math.cos(a) * r, loc[1] - .05, loc[2] + math.sin(a) * r), fl if k % 3 else plain('flower_red', '#a02030', .7)) if hasattr(T.lib, 'sphere') else None
    return o


def flowers(name, loc, n=9, spread=.4):
    cols = ['#e8e0d4', '#b02838', '#e8c050', '#c87090']; rng = random.Random(len(name) * 7)
    stem = plain('stem', '#3a5a2a', .8)
    for k in range(n):
        p = Vector(loc) + Vector((rng.uniform(-spread, spread), rng.uniform(-spread * .4, spread * .4), 0))
        cyl(name + '_st', .008, .45, p + Vector((0, 0, .22)), stem, v=6)
        if hasattr(T.lib, 'sphere'): T.lib.sphere(name + '_fl', .05, p + Vector((0, 0, .46)), plain('fl' + cols[k % 4], cols[k % 4], .7))
