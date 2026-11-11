"""A modern downtown for the zombie parody (DAGAR CLIPS): one long avenue running along +Y.

    y -75 .. -58   City Hall (columns, steps, dome) facing north, up the avenue
    y -55 .. 75    downtown: shops with awnings and signs on the ground floor, office towers, a cross street at y 20
    y 75 .. 260    the outskirts: low houses, trees, a bus stop (y 140), open lots, the retirement home (y 245)
Road x in [-6, 6] (4 lanes), sidewalks x in +-[6, 10], building fronts at x = +-10.  Everything is built from primitives with
Poly Haven textures on CI (procedural fallbacks locally), plus window-grid facades for the towers and a skyline behind."""
import math, random, os
import bpy, bmesh
from mathutils import Vector, Matrix
import town as T
import lib
from town import box, cyl, plain, text, put

ROAD = 6.0; WALK = 4.0; FRONT = ROAD + WALK          # building fronts at x = +-FRONT
CURB = .15
CITYHALL_Y = -62.0
BUS_Y = 140.0; CART_Y = 104.0; HOME_Y = 246.0
_M = {}


def ph(name, kws, fallback_col, scale=1.0, tint=None, rough=.85):
    key = ('cph', name)
    if key in _M: return _M[key]
    m = None
    if T.PH:
        try: m = lib.mat_ph(name, *kws, scale=scale, tint=tint, bump=.5, res=os.environ.get('PH_RES', '1k'))
        except Exception as e: lib.log('city PH', name, 'failed', e)
    if m is None: m = plain(name, fallback_col, rough)
    _M[key] = m; return m


def asphalt(): return ph('asphalt', ('asphalt', 'road'), '#3a3a3e', scale=.25)
def concrete(): return ph('sidewalk', ('concrete', 'pavement', 'floor'), '#a8a49c', scale=.5)
def brick(col='#8a4a3a'): return ph('brick_' + col, ('brick', 'wall'), col, scale=.6, tint=col)
def stone(): return ph('stone', ('plaster', 'concrete', 'wall'), '#d8d2c4', scale=.5)


def windows(name, wall, glass='#22303c', lit=.12, cols=2.2, rows=3.4, emit=1.2):
    key = ('win', name)
    if key not in _M: _M[key] = lib.mat_windows(name, wall=wall, glass=glass, lit='#ffd9a0', lit_ratio=lit, cols=cols, rows=rows, emit=emit)
    return _M[key]


# ------------------------------------------------------------------ street
def street(y0=-90, y1=270):
    L = y1 - y0; yc = (y0 + y1) / 2
    box('road', (2 * ROAD, L, .1), (0, yc, -.05), asphalt())
    lane = plain('laneline', '#e8e2c8', .6); yel = plain('yellowline', '#e8b830', .6)
    for x in (-.12, .12): box(f'cline{x}', (.1, L, .012), (x, yc, .006), yel)
    y = y0
    while y < y1:
        for x in (-3.0, 3.0): box(f'dash{x}_{y:.0f}', (.12, 3.0, .012), (x, y + 1.5, .006), lane)
        y += 9.0
    for s in (-1, 1):
        box(f'walk{s}', (WALK, L, CURB), (s * (ROAD + WALK / 2), yc, CURB / 2), concrete())
        box(f'curb{s}', (.18, L, CURB + .02), (s * (ROAD + .09), yc, (CURB + .02) / 2), plain('curb', '#b8b4ac', .8))
    gm = ph('ground', ('grass', 'lawn', 'meadow'), '#6a7a48', scale=.3)
    for s in (-1, 1): box(f'lot{s}', (400, L + 200, .1), (s * (FRONT + 200), yc, -.04), gm)
    box('farground', (1600, 1600, .1), (0, yc, -.3), gm)


def crosswalk(y):
    w = plain('zebra', '#ecead8', .6)
    for k in range(9): box(f'zebra{y:.0f}_{k}', (1.0, 3.0, .014), (-5.2 + k * 1.3, y, .008), w)


def lamp(name, x, y, night=False):
    pole = plain('lamppole', '#2a2e33', .45, .6)
    s = 1 if x > 0 else -1
    cyl(name + '_p', .07, 6.0, (x, y, 3.0 + CURB), pole, v=10)
    box(name + '_a', (1.6, .1, .1), (x - s * .8, y, 6.0), pole)
    head = plain('lamphead', '#fff2d0', .2, emit='#ffd890', strength=6 if night else .4)
    box(name + '_h', (.6, .28, .14), (x - s * 1.5, y, 5.92), head)
    if night:
        l = bpy.data.lights.new(name, 'SPOT'); l.energy = 900; l.spot_size = math.radians(110); l.color = (1, .82, .55)
        o = bpy.data.objects.new(name, l); o.location = (x - s * 1.5, y, 5.8); T.coll('Town').objects.link(o)


def tree(name, x, y, h=None, seed=0):
    r = random.Random(seed); h = h or r.uniform(4.5, 6.5)
    cyl(name + '_t', .14, h * .55, (x, y, h * .27 + CURB), plain('bark', '#4a3626', .9), v=8)
    leaf = plain('leaf' + str(seed % 3), ['#4a7a3a', '#5a8a3e', '#3e6a34'][seed % 3], .85)
    for k in range(3):
        o = T.lib.sphere(f'{name}_c{k}', 1.0, (x + r.uniform(-.5, .5), y + r.uniform(-.5, .5), h * .72 + k * .45), leaf)
        sc = r.uniform(1.2, 1.7); o.scale = (sc, sc, sc * .85)
    box(name + '_pit', (1.2, 1.2, .05), (x, y, CURB + .02), plain('soil', '#3a2c20', .95))


def car(name, x, y, yaw=0.0, col=None, seed=0):
    r = random.Random(seed); col = col or r.choice(['#c8302a', '#2a5a9a', '#e8e4dc', '#2a2a2e', '#d8a020', '#4a8a5a', '#8a8a90', '#6a2a6a'])
    root = bpy.data.objects.new(name, None); T.coll('Town').objects.link(root); root.location = (x, y, 0); root.rotation_euler = (0, 0, math.radians(yaw))
    paint = plain('carpaint' + col, col, .25, .3); glass = plain('carglass', '#1c2630', .05, .2); tire = plain('tire', '#141416', .9); chrome = plain('chrome', '#d0d0d4', .15, 1.0)
    parts = [box(name + '_b', (1.8, 4.2, .75), (0, 0, .62), paint, bevel=.12),
             box(name + '_c', (1.6, 2.2, .62), (0, .25, 1.25), glass, bevel=.1),
             box(name + '_r', (1.62, 2.0, .06), (0, .25, 1.57), paint, bevel=.02)]
    for sx in (-.86, .86):
        for sy in (-1.35, 1.35): parts.append(cyl(f'{name}_w{sx}{sy}', .34, .26, (sx, sy, .34), tire, rot=(0, math.pi / 2, 0), v=16))
    for sx in (-.6, .6):
        parts.append(box(f'{name}_hl{sx}', (.32, .05, .14), (sx, -2.1, .78), plain('headlight', '#fff8e0', .1, emit='#fff0c0', strength=.5)))
        parts.append(box(f'{name}_tl{sx}', (.32, .05, .12), (sx, 2.1, .8), plain('taillight', '#c01010', .2, emit='#ff2010', strength=.4)))
    parts.append(box(name + '_bump', (1.85, .12, .14), (0, -2.12, .4), chrome)); parts.append(box(name + '_bump2', (1.85, .12, .14), (0, 2.12, .4), chrome))
    for p in parts: p.parent = root
    return root


def hydrant(name, x, y):
    red = plain('hydrant', '#c8281e', .4)
    cyl(name, .12, .6, (x, y, .3 + CURB), red, v=12); T.lib.sphere(name + '_top', .13, (x, y, .62 + CURB), red)
    cyl(name + '_n', .05, .32, (x, y, .4 + CURB), red, rot=(0, math.pi / 2, 0), v=8)


def bin_(name, x, y):
    cyl(name, .28, .9, (x, y, .45 + CURB), plain('bin', '#2a4a3a', .6, .3), v=14)


def bench(name, x, y, yaw):
    w = T.wood('benchwood', '#8a5a3a', weather=.3); iron = plain('iron2', '#202224', .5, .6)
    root = bpy.data.objects.new(name, None); T.coll('Town').objects.link(root); root.location = (x, y, CURB); root.rotation_euler = (0, 0, math.radians(yaw))
    for p in (box(name + '_s', (1.6, .45, .06), (0, 0, .45), w), box(name + '_b', (1.6, .06, .4), (0, .22, .75), w),
              box(name + '_l1', (.06, .45, .45), (-.7, 0, .22), iron), box(name + '_l2', (.06, .45, .45), (.7, 0, .22), iron)): p.parent = root
    return root


# ------------------------------------------------------------------ signs
def sign_mat(name, txt, bg='#1e2a3a', fg='#f4e8c8', size=(1024, 256), font_scale=.62, serif=False, border=None, font=None, wght=None):
    from PIL import Image, ImageDraw, ImageFont
    os.makedirs('/tmp/citytex', exist_ok=True); p = f'/tmp/citytex/{name}.png'
    im = Image.new('RGB', size, bg); d = ImageDraw.Draw(im)
    f = '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf' if serif else '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
    lines = txt.split('\n'); fs = int(size[1] * font_scale / len(lines))
    if font: f = font
    def mk(fs):
        ft_ = ImageFont.truetype(f, fs)
        if wght:
            try: ft_.set_variation_by_axes([wght])
            except Exception: pass
        return ft_
    ft = mk(fs)
    while max(d.textlength(l, font=ft) for l in lines) > size[0] * .9 and fs > 10: fs -= 2; ft = mk(fs)
    for k, l in enumerate(lines): d.text((size[0] / 2, size[1] * (k + .5) / len(lines)), l, font=ft, fill=fg, anchor='mm')
    if border: d.rectangle([6, 6, size[0] - 7, size[1] - 7], outline=border, width=8)
    im.save(p)
    m = bpy.data.materials.new(name); m.use_nodes = True; N, L = m.node_tree.nodes, m.node_tree.links
    tx = N.new('ShaderNodeTexImage'); tx.image = bpy.data.images.load(p); tx.interpolation = 'Cubic'
    b = N['Principled BSDF']; L.new(tx.outputs[0], b.inputs['Base Color']); b.inputs['Roughness'].default_value = .6
    L.new(tx.outputs[0], b.inputs['Emission Color']); b.inputs['Emission Strength'].default_value = .15
    return m


def sign(name, txt, w, h, loc, facing=(0, -1), **kw):
    """flat sign reading correctly from the side it faces (facing = horizontal direction of its front)"""
    me = bpy.data.meshes.new(name); bm = bmesh.new(); uv = bm.loops.layers.uv.new('UVMap')
    vs = [bm.verts.new(p) for p in ((-w / 2, 0, -h / 2), (w / 2, 0, -h / 2), (w / 2, 0, h / 2), (-w / 2, 0, h / 2))]
    f = bm.faces.new(vs)
    for lp, (a, c) in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))): lp[uv].uv = (a, c)
    bm.to_mesh(me); bm.free(); me.materials.append(sign_mat(name, txt, **kw))
    o = bpy.data.objects.new(name, me); o.location = loc
    o.rotation_euler = (0, 0, math.atan2(facing[0], -facing[1]))
    T.coll('Town').objects.link(o); return o


# ------------------------------------------------------------------ buildings
SHOPS = ['COFFEE', 'PHARMACY', 'PIZZA', 'BOOKS', 'DELI', 'LAUNDRY', 'GYM', 'BAKERY', 'TOYS', 'HARDWARE', 'FLOWERS', 'SUSHI', 'BARBER', 'MART',
         'DONUTS', 'SHOES', 'PHONES', 'TACOS', 'DINER', 'MUSIC']
AWN = ['#c8302a', '#2a6a4a', '#2a4a8a', '#d89a20', '#6a2a5a', '#e8e4dc', '#3a3a3e', '#c86a2a']
WALLS = ['#8a4a3a', '#a86a4a', '#6a6a70', '#c8b89a', '#4a5a6a', '#9a8a70', '#7a3a32', '#b8b4a8']


def building(name, side, y, w, d, h, shop=None, wall='#8a4a3a', awn='#c8302a', tower=False, boarded=False, night=False):
    """a city building whose street front is at x = side*FRONT; ground-floor shop with glass, awning and sign"""
    xf = side * FRONT; xc = side * (FRONT + d / 2)
    facade = windows(f'win_{wall}_{tower}', wall, glass='#2a3a4a' if tower else '#24303a', lit=.35 if night else .08, cols=1.6 if tower else 2.4, rows=3.4)
    box(name, (d, w, h - 4.2), (xc, y, 4.2 + (h - 4.2) / 2), facade)
    base = brick(wall) if not tower else stone()
    box(name + '_gf', (d, w, 4.2), (xc, y, 2.1), base)
    box(name + '_cor', (d + .3, w + .3, .35), (xc, y, h + .17), plain('cornice', '#d8d0c0' if not tower else '#8a9098', .7))
    box(name + '_band', (.25, w, .3), (xf + side * .1, y, 4.25), plain('cornice', '#d8d0c0', .7))
    if shop:
        glass = plain('shopglass', '#3a4a52', .05, .1, emit='#ffe0b0', strength=.9 if night else .25)
        box(name + '_win', (.08, w * .78, 2.4), (xf - side * .02, y, CURB + 1.5), glass)
        box(name + '_door', (.1, 1.1, 2.4), (xf - side * .03, y + w * .32, CURB + 1.2), plain('door', '#2a2420', .6))
        awm = plain('awning' + awn, awn, .7)
        a = box(name + '_awn', (1.6, w * .9, .08), (xf - side * .75, y, 3.45), awm, rot=(0, math.radians(-16 * side), 0))
        sign(name + '_sign', shop, min(w * .8, 6.5), .9, (xf - side * .06, y, 3.85), facing=(-side, 0), bg=random.Random(name).choice(['#1e2a3a', '#2a1e1a', '#f0e8d8', '#14301e', '#3a1414']),
             fg=random.Random(name + 'f').choice(['#f4e8c8', '#ffd060', '#ffffff']))
        if boarded:
            ply = T.wood('plywood', '#c8a878', weather=.2, planks=False)
            for k in range(3): box(f'{name}_ply{k}', (.05, w * .78 / 3 - .05, 2.4), (xf - side * .08, y - w * .78 / 2 + w * .78 / 6 * (2 * k + 1), CURB + 1.5), ply, rot=(math.radians(k * 2 - 2), 0, 0))
    return name


def downtown(boarded=False, night=False, y0=-52, y1=75):
    r = random.Random(11)
    for side in (-1, 1):
        y = y0; k = 0
        while y < y1:
            if 14 < y < 26: y = 26.0; continue                     # cross street
            w = r.uniform(9, 15); h = r.choice([9, 12, 14, 18, 24, 32, 42]) if abs(y) < 60 else r.choice([8, 10, 12]); d = r.uniform(12, 18)
            tower = h > 20
            building(f'bld{side}_{k}', side, y + w / 2, w - .2, d, h, shop=SHOPS[(k * 3 + (side > 0) * 7) % len(SHOPS)], wall=r.choice(WALLS), awn=r.choice(AWN),
                     tower=tower, boarded=boarded, night=night)
            y += w; k += 1
    # cross street at y 20
    box('xroad', (300, 10, .1), (0, 20, -.049), asphalt())
    crosswalk(13.6); crosswalk(26.4)
    for s in (-1, 1):
        for yy in (14.2, 25.8):
            pole = plain('lamppole', '#2a2e33', .45, .6)
            cyl(f'tl{s}{yy}', .08, 3.6, (s * 6.4, yy, 1.8 + CURB), pole, v=8)
            box(f'tlh{s}{yy}', (.3, .3, .9), (s * 6.4, yy, 3.9), plain('tlbox', '#1a1c1e', .5))
            for j, c in enumerate(('#ff3020', '#ffb020', '#30e060')):
                T.lib.sphere(f'tll{s}{yy}{j}', .09, (s * 6.4, yy - .16 * (1 if yy < 20 else -1), 4.15 - j * .27), plain('tl' + c, c, .3, emit=c, strength=3 if j == 2 else .2))


def skyline():
    r = random.Random(3)
    for k in range(70):
        side = r.choice((-1, 1)); x = side * r.uniform(40, 140); y = r.uniform(-160, 160); w = r.uniform(12, 30); h = r.uniform(30, 120)
        wall = r.choice(['#5a6470', '#7a8088', '#8a8478', '#4a5058', '#a09a90'])
        box(f'sky{k}', (w, w * r.uniform(.8, 1.3), h), (x, y, h / 2), windows(f'skywin{wall}', wall, glass='#2c3a48', lit=.15, cols=1.4, rows=3.2))
    for k in range(10):                      # a few towers behind City Hall
        x = r.uniform(-60, 60); y = r.uniform(-220, -120); w = r.uniform(16, 28); h = r.uniform(60, 140)
        box(f'skys{k}', (w, w, h), (x, y, h / 2), windows('skywinS', '#6a7480', glass='#2c3a48', lit=.15, cols=1.4, rows=3.2))


def city_hall():
    y = CITYHALL_Y; st = stone()
    box('ch_body', (40, 16, 14), (0, y - 8, 7), st)
    box('ch_cor', (41, 17, .8), (0, y - 8, 14.3), plain('cornice', '#d8d0c0', .7))
    for k in range(5): box(f'ch_step{k}', (24 - k * .6, 1.0, .25), (0, y + 4.6 - k * .9, .12 + k * .25), st)        # steps up to the portico
    for k in range(8):
        x = -10.5 + k * 3.0
        cyl(f'ch_col{k}', .55, 10.5, (x, y + 1.0, 1.25 + 5.25), plain('column', '#ece6da', .6), v=20)
    pt = bpy.data.meshes.new('ch_ped'); bm = bmesh.new()
    vs = [bm.verts.new(p) for p in ((-12.5, 0, 0), (12.5, 0, 0), (0, 0, 3.6))]; bm.faces.new(vs); bm.to_mesh(pt); bm.free()
    o = bpy.data.objects.new('ch_ped', pt); o.location = (0, y + 1.6, 11.75); pt.materials.append(plain('column', '#ece6da', .6)); s = o.modifiers.new('s', 'SOLIDIFY'); s.thickness = 3.5; T.coll('Town').objects.link(o)
    box('ch_ent', (24, 3.2, .5), (0, y + 1.0, 11.6), plain('column', '#ece6da', .6))
    T.lib.sphere('ch_dome', 6.0, (0, y - 8, 15.5), plain('dome', '#5a8a7a', .4, .5)).scale = (1, 1, .85)
    cyl('ch_drum', 6.2, 3.0, (0, y - 8, 15.0), st, v=40)
    sign('ch_sign', 'CITY HALL', 9.0, 1.2, (0, y + 1.75, 10.6), facing=(0, 1), bg='#ece6da', fg='#2a2a2e', serif=True)
    box('ch_door', (3.0, .2, 4.0), (0, y + .05, 3.25), plain('door', '#3a2a1e', .5))
    for x in (-5, 5): cyl(f'ch_flag{x}', .06, 9.0, (x * 2.6, y + 6.5, 4.5), plain('lamppole', '#2a2e33', .45, .6), v=8)
    for x in (-13, 13): box(f'ch_flg{x}', (.04, 1.6, 1.0), (x, y + 7.3, 8.2), plain('flag', '#2a4a8a', .7))
    box('ch_plaza', (40, 14, .16), (0, y + 11, .08), concrete())


def outskirts(night=False):
    r = random.Random(21)
    roofm = plain('roof', '#5a3a32', .8)
    for side in (-1, 1):
        y = 82
        while y < 236:
            if abs(y - BUS_Y) < 9 or abs(y - CART_Y) < 6: y += 12; continue
            if r.random() < .75:
                w = r.uniform(8, 12); d = r.uniform(8, 10); h = r.uniform(3.5, 6.5); x = side * (FRONT + 6 + d / 2)
                col = r.choice(['#e8dcc8', '#c8d8e0', '#e0c8a8', '#d0d8c0', '#f0e8e0', '#b8c0c8'])
                box(f'house{side}_{y:.0f}', (d, w, h), (x, y, h / 2), windows(f'hw{col}', col, glass='#2a3440', lit=.4 if night else .05, cols=1.8, rows=2.8, emit=.8))
                rf = box(f'roof{side}_{y:.0f}', (d + .8, w + .6, 1.6), (x, y, h + .5), roofm); rf.scale = (1, 1, 1)
                box(f'fence{side}_{y:.0f}', (.08, w, .9), (side * (FRONT + 1.0), y, .45), plain('picket', '#f0ece4', .7))
            for k in range(2): tree(f'otree{side}_{y:.0f}_{k}', side * (FRONT + 2.5 + r.uniform(0, 3)), y + r.uniform(-4, 4), seed=int(y) + k)
            y += r.uniform(12, 16)
    # the retirement home at the far end
    y = HOME_Y; col = '#e8dcc0'
    box('home', (34, 12, 9), (0, y + 12, 4.5), windows('homewin', col, glass='#2a3440', lit=.3, cols=2.0, rows=3.0))
    box('home_roof', (35, 13, .6), (0, y + 12, 9.3), plain('roof', '#5a3a32', .8))
    box('home_porch', (12, 3, .3), (0, y + 4.6, .15), stone())
    sign('home_sign', 'SUNSET ACRES\nRETIREMENT HOME', 8.0, 2.2, (0, y + 5.95, 6.4), facing=(0, -1), bg='#f4ecd8', fg='#3a5a3a', serif=True, size=(1024, 300), border='#3a5a3a')
    sign('home_wifi', 'FREE WI-FI*\n*NOT REALLY', 2.6, 1.0, (8.5, y + 5.95, 2.6), facing=(0, -1), bg='#ffffff', fg='#a02020', size=(700, 270))


def bus_stop(y=BUS_Y, side=1):
    x = side * (ROAD + 2.6); glass = plain('busglass', '#a8c0c8', .05, transmit=.6); frame = plain('busframe', '#2a3a4a', .4, .6)
    box('bus_roof', (1.8, 4.0, .12), (x, y, 2.6), frame)
    box('bus_back', (.06, 4.0, 2.2), (x + side * .85, y, 1.35 + CURB), glass)
    for dy in (-1.95, 1.95): box(f'bus_side{dy}', (1.7, .06, 2.2), (x, y + dy, 1.35 + CURB), glass); cyl(f'bus_post{dy}', .05, 2.5, (x - side * .85, y + dy, 1.4), frame, v=8)
    bench('bus_bench', x + side * .45, y, -90 * side)
    cyl('bus_pole', .05, 3.0, (x - side * 1.0, y - 2.6, 1.5 + CURB), frame, v=8)
    sign('bus_sign', 'BUS\nEVERY 10 MIN', .7, .7, (x - side * 1.0, y - 2.6, 2.75), facing=(-side, 0), bg='#1e4a8a', fg='#ffffff', size=(400, 400))
    sign('bus_sched', 'NEXT BUS:\nSOON', .8, .6, (x + side * .8, y + .9, 1.6), facing=(-side, 0), bg='#f0f0e8', fg='#202020', size=(400, 300))
    return Vector((x, y, CURB))


def coffee_cart(y=CART_Y, x=2.2):
    body = plain('cartbody', '#2a6a5a', .5); wood_ = T.wood('cartwood', '#8a5a3a', weather=.2)
    box('cart', (1.0, 1.8, 1.0), (x, y, .65), body, bevel=.04)
    box('cart_top', (1.1, 1.9, .06), (x, y, 1.18), wood_)
    for dy in (-.7, .7): cyl(f'cart_wheel{dy}', .28, .1, (x + .55, y + dy, .28), plain('tire', '#141416', .9), rot=(0, math.pi / 2, 0))
    cyl('umb_pole', .03, 2.4, (x + .2, y, 1.9), plain('lamppole', '#2a2e33', .45, .6), v=8)
    o = bpy.data.meshes.new('umb'); bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=False, segments=16, radius1=1.4, radius2=.05, depth=.55); bm.to_mesh(o); bm.free()
    u = bpy.data.objects.new('umbrella', o); u.location = (x + .2, y, 3.0); o.materials.append(plain('umbr', '#e8d8b8', .7)); T.coll('Town').objects.link(u)
    sign('cart_sign', 'COFFEE\nLATTE $3', 1.4, .7, (x - .52, y, .75), facing=(-1, 0), bg='#f4ecd8', fg='#5a2a1a', size=(600, 300))
    for k in range(4): cyl(f'cup{k}', .045, .12, (x - .25, y - .6 + k * .14, 1.27), plain('cup', '#f4f0e8', .5), v=10)
    cyl('pot', .1, .28, (x + .15, y + .55, 1.35), plain('steel', '#c8c8cc', .2, 1.0), v=12)
    return Vector((x, y, 0))


def barriers(y, n=8, x0=-7.5, dx=2.1):
    red = plain('barrred', '#d02a20', .5); wht = plain('barrwht', '#f2f0ea', .5); leg = plain('barrleg', '#c8c8c8', .6)
    for k in range(n):
        x = x0 + k * dx
        for j in range(4): box(f'barr{k}_{j}', (.46, .05, .2), (x - .69 + j * .46, y, .92), red if (j + k) % 2 else wht)
        for dd in (-.8, .8):
            box(f'barrl{k}{dd}a', (.05, .05, .95), (x + dd, y - .12, .47), leg, rot=(math.radians(14), 0, 0))
            box(f'barrl{k}{dd}b', (.05, .05, .95), (x + dd, y + .12, .47), leg, rot=(math.radians(-14), 0, 0))


def studio(at=Vector((400, 0, 0))):
    """TV news set: desk, big screen with the betting odds, studio lights"""
    box('st_floor', (16, 14, .1), (at.x, at.y, -.05), plain('stfloor', '#1a2030', .3))
    box('st_back', (16, .2, 7), (at.x, at.y + 4.0, 3.5), windows('stwin', '#20283a', glass='#3050a0', lit=.6, cols=1.0, rows=1.0, emit=1.5))
    box('st_desk', (3.6, 1.0, 1.0), (at.x, at.y - .2, .5), plain('desk', '#c8d0e0', .25, .4), bevel=.05)
    box('st_desk2', (3.7, 1.1, .06), (at.x, at.y - .2, 1.02), plain('desktop', '#2a3a6a', .2))
    sign('st_logo', 'CH 7 NEWS', 3.2, .5, (at.x, at.y - .72, .55), facing=(0, -1), bg='#1a3a8a', fg='#ffffff')
    scr = sign('st_screen', 'ZOMBIE WATCH: THE ODDS\nTODAY ........ 500-1\nTHURSDAY ...... 9-1\nNEXT YEAR ...... 2-1', 4.2, 2.6, (at.x + 1.4, at.y + 3.85, 2.9), facing=(0, -1),
               bg='#0e1a3a', fg='#ffe060', size=(1024, 640))
    for k, x in enumerate((-4, 4)):
        l = bpy.data.lights.new(f'stl{k}', 'AREA'); l.energy = 450; l.size = 2.5; o = bpy.data.objects.new(f'stl{k}', l)
        o.location = (at.x + x, at.y - 5, 4.0); o.rotation_euler = (math.radians(60), 0, math.radians(-x * 8)); T.coll('Town').objects.link(o)
    return at


def footprints(path, step=.62, name='fp'):
    m = plain('footprint', '#4a3e30', .95)
    out = []
    for k, (a, b) in enumerate(zip(path[:-1], path[1:])):
        a, b = Vector((a[0], a[1], 0)), Vector((b[0], b[1], 0)); d = (b - a); L = d.length; dirn = d.normalized(); side = Vector((-dirn.y, dirn.x, 0))
        n = int(L / step)
        for j in range(n):
            p = a + dirn * (j * step) + side * (.13 if (j + k) % 2 else -.13)
            o = box(f'{name}{k}_{j}', (.12, .28, .012), (p.x, p.y, .03), m, rot=(0, 0, math.atan2(-dirn.x, dirn.y)))
            out.append(o)
    return out


def build(boarded=False, night=False, mood='day'):
    street(); downtown(boarded=boarded, night=night); city_hall(); outskirts(night=night); skyline()
    for s in (-1, 1):
        for k, y in enumerate(range(-50, 236, 16)):
            if 13 < y < 27 or abs(y - BUS_Y) < 4: continue
            lamp(f'lamp{s}_{k}', s * (ROAD + .6), y, night=night and abs(y) < 80)
        for k, y in enumerate(range(-46, 74, 12)):
            if 12 < y < 28: continue
            tree(f'tree{s}_{k}', s * (ROAD + 1.6), y + 3, seed=k * 3 + (s > 0))
    r = random.Random(5)
    for s in (-1, 1):
        for k, y in enumerate(range(-44, 70, 11)):
            if 12 < y < 28 or r.random() < .25: continue
            car(f'car{s}_{k}', s * 4.6, y + r.uniform(-2, 2), yaw=0 if s > 0 else 180, seed=k * 7 + (s > 0))
        hydrant(f'hyd{s}', s * (ROAD + .7), 8 + s * 3); hydrant(f'hyd2{s}', s * (ROAD + .7), 46 - s * 5)
        for k, y in enumerate((-30, 4, 36, 60)): bin_(f'bin{s}{k}', s * (ROAD + .9), y + s)
    bus_stop(); coffee_cart()
    sign('billboard', 'ZOMBIE?\nSTAY CALM.\nCARRY ON.', 10, 5, (-FRONT - 6, 40, 28), facing=(1, 0), bg='#f0d020', fg='#1a1a1a', size=(1024, 512))
