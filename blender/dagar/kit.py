"""Kitchen set for the DAGAR CLIPS test scene. 1 unit = 1 m, cartoon scale (props sized for a 1.4 m tall character).
Camera looks mostly along +Y. Back wall y=3.4 with counter, sink and window; fridge on the left, table on the right."""
import bpy, math, random
from mathutils import Vector
from common import *
from lib import box, cyl, sphere, torus, plane, lathe, smooth_tube, coll, point, area, sun

PROPS = lambda: coll('Props')
SET = lambda: coll('Set')
CT = .82          # counter top height
NOOUT = []        # set pieces that get no outline

def B(name, size, loc, m, bevel=.008, rot=(0, 0, 0), c=None, outline_w=.006):
    o = box(name, size, loc, m, rot=rot, bevel=bevel, c=c or PROPS())
    if outline_w: outline(o, outline_w)
    return o

def C(name, r, h, loc, m, seg=24, r2=None, rot=(0, 0, 0), outline_w=.005, c=None):
    o = cyl(name, r, h, loc, m, seg=seg, r2=r2, rot=rot, c=c or PROPS())
    if outline_w: outline(o, outline_w)
    return o

def S(name, r, loc, m, scale=(1, 1, 1), outline_w=.005, c=None):
    o = sphere(name, r, loc, m, seg=32, rings=20, scale=scale, c=c or PROPS())
    if outline_w: outline(o, outline_w)
    return o

def make_mug(loc=(0, 0, 0), col='#d8412f', s=1.6):
    m = solid(col, .25, coat=.6)
    prof = [(0, 0), (.036, 0), (.043, .008), (.047, .05), (.045, .097), (.0415, .1), (.039, .094), (.0385, .014), (0, .014)]
    mug = lathe('mug', prof, seg=40, m=m, c=PROPS()); mug.location = loc; mug.scale = (s,) * 3
    h = torus('mug_handle', .03, .0065, (.05, 0, .055), m, rot=(math.pi / 2, 0, 0), seg=24, mseg=10, c=PROPS()); h.scale = (1, 1, 1.3)
    h.parent = mug
    outline(mug, .0035); outline(h, .0025)
    cf = lathe('mug_coffee', [(0, 0), (.0382, 0), (.0382, .0), (0, 0)], seg=24, m=solid('#3a1f10', .3), c=PROPS())   # placeholder (hidden)
    bpy.data.objects.remove(cf)
    return mug

def kitchen(night=True):
    """Builds the room; returns dict of key objects/positions."""
    W = 2.8; D0, D1 = -2.6, 3.4; H = 2.8
    wall = plaster_mat('wall', '#d6c29a', scale=18, bumpv=.05)
    wall2 = plaster_mat('wallb', '#8fb0ae', scale=18, bumpv=.05)
    floor = tile_mat('floor', '#e8dfc6', '#a8b7a2', '#6b6858', scale=2.2, rough=.28)
    back = tile_mat('backsplash', '#f2ede0', '#e4dcc8', '#9a9382', scale=9, rough=.2)
    ceil = plaster_mat('ceil', '#e8dfcf', scale=10, bumpv=.03)
    c = SET()
    pl = lambda n, sz, loc, m, rot=(0, 0, 0): plane(n, sz[0], sz[1], loc, m, rot=rot, c=c)
    bx = lambda n, sz, loc, m: box(n, sz, loc, m, c=c)
    bx('floor', (2 * W + .6, D1 - D0 + .6, .1), (0, (D0 + D1) / 2, -.05), floor)
    bx('ceil', (2 * W + .6, D1 - D0 + .6, .1), (0, (D0 + D1) / 2, H + .05), ceil)
    # back wall with a window opening: build from 4 boxes
    wx0, wx1, wz0, wz1 = -.35, 1.15, 1.25, 2.25
    bx('bw_l', (wx0 + W + .3, .2, H), ((-W - .3 + wx0) / 2, D1 + .1, H / 2), wall)
    bx('bw_r', (W + .3 - wx1, .2, H), ((wx1 + W + .3) / 2, D1 + .1, H / 2), wall)
    bx('bw_b', (wx1 - wx0, .2, wz0), ((wx0 + wx1) / 2, D1 + .1, wz0 / 2), wall)
    bx('bw_t', (wx1 - wx0, .2, H - wz1), ((wx0 + wx1) / 2, D1 + .1, (wz1 + H) / 2), wall)
    bx('wall_l', (.2, D1 - D0 + .6, H), (-W - .1, (D0 + D1) / 2, H / 2), wall2)
    bx('wall_r', (.2, D1 - D0 + .6, H), (W + .1, (D0 + D1) / 2, H / 2), wall2)
    bx('wall_f', (2 * W + .6, .2, H), (0, D0 - .1, H / 2), wall)
    # backsplash tiles
    bx('splash', (2 * W, .02, .55), (0, D1 - .005, CT + .3), back)
    # wainscot on side walls
    wood = wood_mat('wainscot', '#a87a4c', '#6e4a2a', scale=2.5, stretch=(1, 1, 1.2))
    for sd in (-1, 1): bx('wains%d' % sd, (.04, D1 - D0, .95), (sd * (W - .02), (D0 + D1) / 2, .5), wood)
    # window: night outside
    sky = mat('sky', '#0e1830', rough=1, emit='#1d2f5c', emit_strength=1.2)
    pl('nightsky', (4.2, 3.2), ((wx0 + wx1) / 2, D1 + 3.2, 1.75), sky, rot=(math.pi / 2, 0, 0))
    gm = solid('#d9dcd5', .5)
    for nm, sz, lc in (('wf_l', (.07, .1, wz1 - wz0 + .1), (wx0 + .035, D1 - .06, (wz0 + wz1) / 2)), ('wf_r', (.07, .1, wz1 - wz0 + .1), (wx1 - .035, D1 - .06, (wz0 + wz1) / 2)),
                       ('wf_b', (wx1 - wx0 + .1, .2, .07), ((wx0 + wx1) / 2, D1 - .1, wz0), ), ('wf_t', (wx1 - wx0 + .1, .1, .07), ((wx0 + wx1) / 2, D1 - .06, wz1)),
                       ('wf_m', (.045, .08, wz1 - wz0), ((wx0 + wx1) / 2, D1 - .06, (wz0 + wz1) / 2)), ('wf_h', (wx1 - wx0, .08, .045), ((wx0 + wx1) / 2, D1 - .06, (wz0 + wz1) / 2 + .08))):
        B(nm, sz, lc, gm, bevel=.005, outline_w=.005)
    # distant buildings outside with lit windows
    rnd = random.Random(4)
    for i in range(14):
        h = rnd.uniform(1.5, 5.0); x = -5 + i * .9 + rnd.uniform(-.2, .2)
        b = bx('bld%d' % i, (.8, .5, h), (x, D1 + 2.4, h / 2 - .2), solid('#14203a', .9))
        for k in range(rnd.randint(2, 6)):
            wm = mat('bw%d_%d' % (i, k), '#ffe7a0', rough=1, emit='#ffcf6a', emit_strength=4)
            plane('bwin', .1, .13, (x + rnd.uniform(-.3, .3), D1 + 2.14, rnd.uniform(.4, h - .3)), wm, rot=(math.pi / 2, 0, 0), c=c)
    # ---- counters
    cab = wood_mat('cab', '#c98b56', '#8d5a33', scale=2.2, stretch=(1, 1, 1))
    top = solid('#5b6a73', .22, coat=.1, metal=.0)
    # lower cabinets (two runs, sink opening between)
    sx0, sx1 = .05, .85
    B('cab_l', (2 * W * .5 - (-0) + 0 - 0 + (sx0 - 0) , .62, .78), (((-W + sx0) / 2), 3.08, .39), cab, bevel=.01)
    B('cab_r', (W - sx1, .62, .78), ((W + sx1) / 2, 3.08, .39), cab, bevel=.01)
    B('cab_s', (sx1 - sx0, .62, .45), ((sx0 + sx1) / 2, 3.08, .225), cab, bevel=.01)
    # counter top slabs with a hole for the sink
    B('top_l', (W + sx0, .66, .045), ((-W + sx0) / 2, 3.07, CT - .022), top, bevel=.006)
    B('top_r', (W - sx1, .66, .045), ((W + sx1) / 2, 3.07, CT - .022), top, bevel=.006)
    B('top_f', (sx1 - sx0, .1, .045), ((sx0 + sx1) / 2, 2.77, CT - .022), top, bevel=.006)
    B('top_b', (sx1 - sx0, .12, .045), ((sx0 + sx1) / 2, 3.34, CT - .022), top, bevel=.006)
    steel = solid('#b9c0c4', .25, metal=.9)
    bw = .018
    B('sink_floor', (sx1 - sx0, .5, bw), ((sx0 + sx1) / 2, 3.07, .52), steel, bevel=.004)
    B('sink_f', (sx1 - sx0, bw, .3), ((sx0 + sx1) / 2, 2.84, .67), steel, bevel=.004, outline_w=0)
    B('sink_b', (sx1 - sx0, bw, .3), ((sx0 + sx1) / 2, 3.30, .67), steel, bevel=.004, outline_w=0)
    B('sink_l', (bw, .5, .3), (sx0 + .01, 3.07, .67), steel, bevel=.004, outline_w=0)
    B('sink_r', (bw, .5, .3), (sx1 - .01, 3.07, .67), steel, bevel=.004, outline_w=0)
    for i, x in enumerate((-2.2, -1.5, -.8, -.1)):     # cabinet doors/handles lower-left
        B('door%d' % i, (.66, .02, .7), (x - .0, 2.76, .4), solid('#d9a066', .45), bevel=.01)
        B('hnd%d' % i, (.14, .03, .02), (x + .25, 2.74, .6), steel, bevel=.005)
    for i, x in enumerate((1.25, 1.95)):
        B('doorr%d' % i, (.66, .02, .7), (x + .2, 2.76, .4), solid('#d9a066', .45), bevel=.01)
        B('hndr%d' % i, (.14, .03, .02), (x + .45, 2.74, .6), steel, bevel=.005)
    # upper cabinets
    for i, x in enumerate((-2.2, -1.5, -.9)):
        B('up%d' % i, (.7 if i < 2 else .5, .36, .8), (x, 3.2, 1.9), cab, bevel=.01)
        B('upd%d' % i, (.66 if i < 2 else .46, .02, .74), (x, 3.02, 1.9), solid('#d9a066', .45), bevel=.01)
        B('uph%d' % i, (.03, .03, .16), (x + .27 - (0 if i < 2 else .1), 3.0, 1.7), steel, bevel=.005)
    for i, x in enumerate((1.5, 2.15)):
        B('upr%d' % i, (.64, .36, .8), (x, 3.2, 1.9), cab, bevel=.01)
        B('uprd%d' % i, (.6, .02, .74), (x, 3.02, 1.9), solid('#d9a066', .45), bevel=.01)
        B('uprh%d' % i, (.03, .03, .16), (x - .24, 3.0, 1.7), steel, bevel=.005)
    # faucet
    fx, fy = .45, 3.28
    C('fau_base', .035, .05, (fx, fy, CT + .045), steel, seg=20)
    neck = smooth_tube('fau_neck', [Vector((fx, fy, CT + .05)), Vector((fx, fy, CT + .3)), Vector((fx, fy - .1, CT + .42)), Vector((fx, fy - .27, CT + .38)), Vector((fx, fy - .3, CT + .3))], .02, steel, c=PROPS())
    outline_note = neck
    C('fau_tip', .028, .05, (fx, fy - .3, CT + .27), steel, seg=20)
    C('fau_hdl', .012, .1, (fx + .07, fy, CT + .16), steel, seg=12, rot=(0, math.pi / 2, 0))
    # kettle, toaster, bowl, jars on the right counter
    S('kettle', .12, (1.7, 3.1, CT + .12), solid('#c43a2e', .25, coat=.5), scale=(1, 1, 1.05))
    C('kettle_lid', .045, .02, (1.7, 3.1, CT + .26), steel, seg=20)
    smooth_tube('kettle_hdl', [Vector((1.8, 3.1, CT + .2)), Vector((1.92, 3.1, CT + .26)), Vector((1.8, 3.1, CT + .06))], .012, solid('#222', .5), c=PROPS())
    B('toaster', (.28, .16, .18), (2.3, 3.1, CT + .09), solid('#cfc7b2', .3, metal=.5), bevel=.04)
    for i, (x, col) in enumerate(((1.15, '#d9c27a'), (1.3, '#c97b4a'))):
        C('jar%d' % i, .06, .17, (x + 0.02 * i, 3.25, CT + .085), glass_mat('jarg%d' % i, '#dff0ff', .05, 1.45, .95), seg=20)
        C('jarc%d' % i, .052, .12, (x + 0.02 * i, 3.25, CT + .07), solid(col, .8), seg=20, outline_w=0)
        C('jarl%d' % i, .062, .03, (x + 0.02 * i, 3.25, CT + .185), solid('#303030', .4), seg=20)
    bowl = lathe('fbowl', [(0, 0), (.06, 0), (.1, .03), (.15, .09), (.16, .1), (.15, .1), (.1, .04), (.06, .01), (0, .01)], seg=40, m=solid('#e0b84a', .35, coat=.4), c=PROPS())
    bowl.location = (-1.0, 3.05, CT); outline(bowl, .005)
    for i, (dx, dy, col) in enumerate(((0, 0, '#d63a2c'), (.07, .03, '#7bbf3a'), (-.06, .04, '#f0a82a'), (.0, -.06, '#d63a2c'))):
        S('fruit%d' % i, .05, (-1.0 + dx, 3.05 + dy, CT + .09 + (.03 if i == 1 else 0)), solid(col, .35, coat=.4))
    B('board', (.5, .32, .03), (-1.75, 3.05, CT + .015), wood_mat('board', '#d8b078', '#a9794a', scale=3), bevel=.008)
    for i in range(4): S('cuke%d' % i, .035, (-1.75 + i * .06 - .1, 3.05, CT + .05), solid('#7cb64a', .5), scale=(1, .5, 1))
    # knife block
    B('kblock', (.14, .1, .26), (-2.4, 3.1, CT + .13), wood_mat('kb', '#7a5230', '#4f3119'), bevel=.01)
    # wall clock, calendar, shelf with plates, hanging pots
    clk = cyl('clock', .17, .03, (-.1 + 0, 3.28, 2.55), solid('#f4f0e6', .4), seg=48, rot=(math.pi / 2, 0, 0), c=PROPS()); outline(clk, .008)
    ch = mat('clockhand', '#111111'); 
    box('chour', (.012, .006, .09), (-.1, 3.255, 2.58), ch, rot=(0, 0, 0), c=PROPS()); box('cmin', (.01, .006, .13), (-.04, 3.255, 2.6), ch, rot=(0, -.9, 0), c=PROPS())
    B('shelf', (1.0, .22, .035), (-1.55, 3.3, 1.3), wood_mat('shelfw', '#9b6a3d', '#6a4526'), bevel=.008)
    for i in range(5): C('plate%d' % i, .1, .015, (-1.9 + i * .06, 3.3, 1.34 + i * .016), solid('#f0ece0' if i % 2 == 0 else '#9ab9c8', .2, coat=.6), seg=32, rot=(1.25, 0, 0))
    rail = C('rail', .01, 1.2, (1.9, 3.28, 2.3), steel, seg=10, rot=(0, math.pi / 2, 0), outline_w=0)
    for i, x in enumerate((1.45, 1.8, 2.15)):
        C('hook%d' % i, .005, .1, (x, 3.28, 2.25), steel, seg=8, outline_w=0)
        pot = lathe('pot%d' % i, [(0, 0), (.08, 0), (.09, .02), (.09, .13), (.095, .14), (.0, .14)], seg=32, m=solid('#2c2f33', .3, metal=.7), c=PROPS())
        pot.location = (x, 3.2, 1.98 - i * .02); outline(pot, .004)
        B('potbar%d' % i, (.14, .025, .025), (x + .13, 3.2, 2.06 - i * .02), solid('#2c2f33', .3, metal=.7), bevel=.006)
    # fridge on the left wall
    fr = solid('#e8e4da', .25, coat=.4)
    B('fridge', (.8, .75, 2.1), (-W + .45, 1.85, 1.05), fr, bevel=.03)
    B('fridge_gap', (.01, .74, .02), (-W + .45 + .4, 1.85, 1.45), solid('#555', .5), bevel=.0, outline_w=0)
    B('fr_h1', (.04, .04, .5), (-W + .88, 1.5, 1.65), steel, bevel=.01); B('fr_h2', (.04, .04, .4), (-W + .88, 1.5, 1.0), steel, bevel=.01)
    for i, col in enumerate(('#d63a2c', '#2f7fc4', '#f0a82a', '#6cb24a')): 
        B('mag%d' % i, (.01, .07, .07), (-W + .86, 1.9 + i * .08 - .1, 1.5 + (i % 2) * .09), solid(col, .5), bevel=.004)
    B('note', (.01, .17, .22), (-W + .86, 2.06, 1.2), solid('#fff6b8', .8), bevel=.002, rot=(.1, 0, 0))
    # dining table + chairs on the right
    tw = wood_mat('tablew', '#a06f3e', '#6d4423', scale=2.5)
    B('table_top', (1.1, 1.6, .06), (W - .9, .4, .72), tw, bevel=.012)
    for sx in (-.47, .47):
        for sy in (-.72, .72): B('tleg', (.07, .07, .7), (W - .9 + sx, .4 + sy, .35), tw, bevel=.01)
    for i, (cx, cy, rt) in enumerate(((W - 1.75, .0, math.pi / 2), (W - 1.75, .8, math.pi / 2), (W - 0.05 - .0, .4, -math.pi / 2))):
        sc = solid('#c94c3a' if i != 1 else '#3f78b5', .5)
        B('seat%d' % i, (.42, .42, .05), (cx, cy, .46), sc, bevel=.015)
        for lx in (-.17, .17):
            for ly in (-.17, .17): B('cleg', (.04, .04, .44), (cx + lx, cy + ly, .22), tw, bevel=.008, outline_w=.004)
        B('cback%d' % i, (.05, .42, .5), (cx - (.2 if cx < W - 1 else -.2), cy, .73), sc, bevel=.015)
    # table items: bowl and newspaper and a flower vase
    vase = lathe('vase', [(0, 0), (.05, 0), (.07, .08), (.045, .16), (.05, .2), (.04, .2), (.035, .16), (.0, .1)], seg=32, m=glass_mat('vaseg', '#9fd0d8', .05, 1.45, .9), c=PROPS())
    vase.location = (W - .9, .75, .75); outline(vase, .004)
    for i, (dx, dz, col) in enumerate(((0, .3, '#e84a7a'), (.05, .26, '#f5c63a'), (-.05, .27, '#fff'))):
        smooth_tube('stem%d' % i, [Vector((W - .9, .75, .8)), Vector((W - .9 + dx * .6, .75, .8 + dz * .6)), Vector((W - .9 + dx, .75, .78 + dz))], .006, solid('#3d8a3a', .8), c=PROPS())
        S('flower%d' % i, .035, (W - .9 + dx, .75, .79 + dz), solid(col, .7), scale=(1, 1, .6))
    B('paper', (.34, .24, .008), (W - .9, .1, .755), solid('#e8e2cf', .9), bevel=.002, rot=(0, 0, .3))
    # rug, pendant lamp, plants, wall art
    rug = cyl('rug', 1.1, .02, (0, 0.5, .01), stripe_mat('rugm', '#b9573a', '#e7d3a5', 7, axis='Y'), seg=64, c=PROPS()); rug.scale = (1.3, 1.0, 1)
    lamp_x, lamp_y = 0.3, 1.2
    C('lamp_cord', .005, 1.0, (lamp_x, lamp_y, H - .5), solid('#222', .5), seg=8, outline_w=0)
    lshade = lathe('lshade', [(.05, 0), (.28, -.2), (.29, -.205), (.06, .02)], seg=40, m=solid('#e9b44b', .45, coat=.3), c=PROPS())
    lshade.location = (lamp_x, lamp_y, H - 1.0 + .3); outline(lshade, .007)
    bulb = mat('bulb', '#fff2cc', rough=.3, emit='#ffd48a', emit_strength=40)
    sphere('bulb', .055, (lamp_x, lamp_y, H - 1.0 + .05), bulb, seg=20, rings=10, c=PROPS())
    point((lamp_x, lamp_y, H - .95), 350, '#ffc77a', .08)
    # plants
    pot = lathe('plantpot', [(0, 0), (.1, 0), (.14, .2), (.15, .22), (.0, .22)], seg=32, m=solid('#b5532d', .6), c=PROPS()); pot.location = (-W + .45, .25, 0); outline(pot, .006)
    for i in range(9):
        a = i / 9 * math.tau
        lf = S('leaf%d' % i, .12, (-W + .45 + math.cos(a) * .13, .25 + math.sin(a) * .13, .5 + (i % 3) * .1), solid('#3f9d46', .5), scale=(.35, .12, 1.0))
        lf.rotation_euler = (math.sin(a) * .5, -math.cos(a) * .5, a)
    B('frame1', (.55, .03, .4), (W - .02, 2.3, 1.7), solid('#6b4a2a', .5), bevel=.01, rot=(0, 0, math.pi / 2))
    B('art1', (.46, .01, .31), (W - .045, 2.3, 1.7), solid('#e7a53a', .6), bevel=.0, rot=(0, 0, math.pi / 2), outline_w=0)
    B('frame2', (.03, .5, .6), (-W + .02, 0.3, 1.6), solid('#6b4a2a', .5), bevel=.01)
    B('art2', (.01, .42, .52), (-W + .05, 0.3, 1.6), solid('#5aa0b8', .6), bevel=.0, outline_w=0)
    # fridge-side doorway (dark opening on the front-left wall)
    B('door_frame', (.1, 1.0, 2.2), (-W + .05, -.9, 1.1), solid('#e8dfc6', .6), bevel=.01)
    B('door_dark', (.02, .8, 2.1), (-W + .08, -.9, 1.05), mat('doordark', '#05060a', rough=1), bevel=.0, outline_w=0)
    # lights: moon through the window, under-cabinet strip, fill
    ar = area((.4, D1 + 1.2, 1.8), (.45, 2.0, .7), size=1.6, energy=900, color='#7fa4ff')
    ar2 = area((.4, 3.0, CT + .65), (.4, 2.8, CT), size=1.4, energy=40, color='#ffcf8a')
    ar3 = area((0, -2.0, 2.4), (0, 1.5, .8), size=3.5, energy=120, color='#ffe6c8')
    # god rays: volume wedge from the window towards the floor
    beam = bpy.data.objects.new('beam', bpy.data.meshes.new('beam')); SET().objects.link(beam)
    import bmesh
    bmx = bmesh.new()
    p0 = [Vector((wx0, D1 - .1, wz0)), Vector((wx1, D1 - .1, wz0)), Vector((wx1, D1 - .1, wz1)), Vector((wx0, D1 - .1, wz1))]
    p1 = [Vector((v.x - .7, v.y - 1.3, max(.0, v.z - 1.1))) for v in p0]
    vs = [bmx.verts.new(v) for v in p0 + p1]
    for a, b, c2, d in ((0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
        try: bmx.faces.new((vs[a], vs[b], vs[c2], vs[d]))
        except Exception: pass
    bmx.normal_update(); bmx.to_mesh(beam.data); bmx.free()
    bm_ = bpy.data.materials.new('beam'); bm_.use_nodes = True; Nn = bm_.node_tree.nodes; Ln = bm_.node_tree.links
    for n in list(Nn): Nn.remove(n)
    out = Nn.new('ShaderNodeOutputMaterial'); mx = Nn.new('ShaderNodeMixShader'); tr = Nn.new('ShaderNodeBsdfTransparent'); em = Nn.new('ShaderNodeEmission')
    em.inputs['Color'].default_value = (.55, .7, 1.0, 1); em.inputs['Strength'].default_value = 1.0
    tc = Nn.new('ShaderNodeTexCoord'); sp = Nn.new('ShaderNodeSeparateXYZ'); rp = Nn.new('ShaderNodeValToRGB')
    rp.color_ramp.elements[0].position = 0.0; rp.color_ramp.elements[0].color = (.07, .07, .07, 1); rp.color_ramp.elements[1].position = 1.0; rp.color_ramp.elements[1].color = (0, 0, 0, 1)
    Ln.new(tc.outputs['Generated'], sp.inputs['Vector']); Ln.new(sp.outputs['Y'], rp.inputs['Fac']); Ln.new(rp.outputs['Color'], mx.inputs['Fac'])
    Ln.new(tr.outputs[0], mx.inputs[1]); Ln.new(em.outputs[0], mx.inputs[2]); Ln.new(mx.outputs[0], out.inputs['Surface'])
    Ln.new  # fake light shaft: cheap, no volume tracing
    beam.data.materials.append(bm_)
    beam.visible_diffuse = False; beam.visible_glossy = False; beam.visible_transmission = False
    beam.visible_shadow = False
    mug = make_mug((0.18, 2.97, CT + .0), '#d8412f')
    return dict(mug=mug, fx=fx, fy=fy, fz=CT + .27, sink=(sx0, sx1), W=W, D1=D1, lamp=(lamp_x, lamp_y), ar=ar, ar2=ar2, ar3=ar3)
