"""THE SLOWEST ZOMBIE APOCALYPSE - parody short (DAGAR CLIPS).  Same engine as the western shorts (ink-outline round-head
toons with mocap acting, Cycles) in a brand-new modern city (city.py).
    python3 story.py -- still <shot> out.png [t]
    python3 story.py -- frames <shot> <f0> <f1> <outdir>"""
import os, sys, json, math, random
HERE = os.path.dirname(os.path.abspath(__file__)); WEST = os.path.join(os.path.dirname(HERE), 'west')
sys.path.insert(0, HERE); sys.path.insert(0, WEST)
import film as F
F.CFG = json.load(open(os.path.join(HERE, 'shots.json')))
from film import bpy, Vector, Matrix, T, PR, TO, ease, K, lerp, head_of, facing, framed, cu
import inkchar as H
import city as C

# ------------------------------------------------------------------ cast
P = TO.preset
WALT = P('Walt', '#e4dccc', '#6a5a48', hat=None, vest='#8a6e4a', haircol='#e0e0dc', stache=True, beardcol='#e0e0dc', height=.93, boots='#d88aa8', belt='#3a2a1a', buttons=True)
MAYOR = P('Mayor', '#f2eee6', '#262a36', hat=None, vest='#6a1e24', duster='#262a36', bolo=True, haircol='#4a3424', height=1.05, boots='#101012', belt='#101010')
DOC = P('Doctor', '#b8d4e8', '#3a3a42', hat=None, duster='#f6f6f2', haircol='#8a8a88', stache=True, beardcol='#8a8a88', height=.99, boots='#1a1a1a', belt='#1a1a1a')
JOG = P('Jogger', '#f07a20', '#1a1a20', hat='cap', hatcol='#1e4a8a', haircol='#2a1a10', boots='#f2f2f2', height=1.0, belt='#1a1a20')
ANCHOR = P('Anchor', '#f2eee6', '#24242c', hat=None, vest='#2a2a3a', duster='#2e2a5a', bolo=True, haircol='#14100c', height=1.0, boots='#101010', belt='#101010')
BARISTA = P('Barista', '#2a6a5a', '#2a2a2e', hat='cap', hatcol='#2a6a5a', apron='#8a5a3a', haircol='#6a3a1a', height=.97, boots='#1a1a1a')
def COP(i): return P(f'Cop{i}', '#2c3e60', '#1a2232', hat='police', hatcol='#1a2232', badge=True, belt='#101010', boots='#0e0e10', haircol=['#2a1a10', '#5a3a1a', '#1a1410'][i % 3],
                     stache=i % 3 == 1, beardcol='#2a1a10', height=.98 + .04 * (i % 3))
def CIV(i):
    r = random.Random(900 + i * 13); hair = r.choice(['#2a1a10', '#1a1410', '#6a3a1a', '#b08040', '#8a8a88', '#4a2a1a'])
    if r.random() < .4:
        return P(f'Civ{i}', '#ece6da', '#2a2a2e', dress=True, dresscol=r.choice(['#c84a4a', '#3a6ab0', '#e0b030', '#4a9a6a', '#8a4aa0', '#e07a40', '#2a2a30']),
                 hat=None, haircol=hair, bun=r.random() < .5, collar=False, height=r.uniform(.92, 1.0), boots=r.choice(['#1a1410', '#c8302a', '#f0f0f0']))
    return P(f'Civ{i}', r.choice(['#e84a3a', '#3a7ad0', '#f0c030', '#4ab07a', '#f0f0ec', '#9a5ad0', '#2a2a30', '#f08aa0', '#40b0c0']),
             r.choice(['#2e4466', '#3a3a40', '#c8b48a', '#1a1a1e', '#5a6a4a']), hat=r.choice([None, None, 'cap']), hatcol=r.choice(['#c8302a', '#1a1a1e', '#2a6aa0']),
             vest=r.choice([None, None, '#3a3a42']), haircol=hair, stache=r.random() < .25, beard=r.random() < .15, beardcol=hair, height=r.uniform(.95, 1.06),
             boots=r.choice(['#f0f0f0', '#1a1410', '#3a2a1a', '#c8302a']))

ZSKIN = (.42, .55, .36)


def toon(sh, cid, preset, protect=True):
    if protect:
        if not hasattr(sh, 'protect'): sh.protect = set()
        sh.protect.add(cid)
    if cid not in sh.chars: sh.chars[cid] = TO.Toon(cid, preset)
    return sh.chars[cid]


def skin(ch, rgb):
    """tint a toon's skin (zombie grey-green -> wiped back to normal); skin materials are copied per character once"""
    mats = getattr(ch, '_skinmats', None)
    if mats is None:
        cache = {}
        for o in [ch.root] + list(ch.root.children_recursive):
            if o.type != 'MESH' or o.name.endswith('_ink'): continue
            for sl in o.material_slots:
                m = sl.material
                if m and m.name.startswith('s_#f4efe6'):
                    if m.name not in cache: cache[m.name] = m.copy()
                    sl.material = cache[m.name]
        mats = ch._skinmats = list(cache.values())
    for m in mats:
        b = m.node_tree.nodes.get('Principled BSDF')
        if b:
            b.inputs['Base Color'].default_value = (*rgb, 1)
            b.inputs['Emission Color'].default_value = (rgb[0] * .9, rgb[1] * .9, rgb[2] * .95, 1)


WHITE = (.9, .87, .82)


# ------------------------------------------------------------------ staging helpers
def stage(sh, mood='day', elev=40, az=140, boarded=False, night=False):
    F.setup(sh, mood, elev, az, town=False)
    sh.town = False
    C.build(boarded=boarded, night=night or mood == 'night', mood=mood)


def stand(sh, ch, xy, yaw, clip='77_02', s0=1.0, face=None, look=None, z=None, talk=None):
    z = C.CURB if (z is None and abs(xy[0]) > C.ROAD) else (z or 0.0)
    return sh.actor(ch, [TO.Act(0, clip, s0, sh.dur + 2, loc=(xy[0], xy[1], z), yaw=yaw, lock_root=True)], face=face or [(0, 'idle')], look=look, talk=talk)


def walk(sh, ch, p0, yaw, clip='82_08', s0=1.0, face=None, speed=1.0, look=None):
    return sh.actor(ch, [TO.Act(0, clip, s0, sh.dur + 2, loc=p0, yaw=yaw, speed=speed)], face=face or [(0, 'idle')], look=look)


def override(actor, fn):
    f0 = actor._fn
    actor.ch.fn = lambda t: fn(t, f0(t))
    return actor


def side_of(ch):
    f = facing(ch); return f, f.cross(Vector((0, 0, 1))).normalized()


def hold(sh, obj, ch, side='R', off=(0, 0, 0), rot=None, track=None):
    """keep a prop in a hand (pose key handR drives hands['R']); track(t) -> direction to point the prop's -Y along"""
    def u(t):
        bpy.context.view_layer.update(); p = ch.hands[side].matrix_world.translation.copy(); obj.location = p + Vector(off)
        if track is not None:
            d = track(t); obj.rotation_mode = 'QUATERNION'; obj.rotation_quaternion = Vector(d).to_track_quat('-Y', 'Z')
        elif rot is not None: obj.rotation_euler = rot(t) if callable(rot) else rot
    sh.updates.append(u)


def cam_keys(keys, roll=0.0, shake=.008):
    def fn(t):
        ks = sorted(keys, key=lambda k: k[0])
        if t <= ks[0][0]: a = b = ks[0]; u = 0
        elif t >= ks[-1][0]: a = b = ks[-1]; u = 0
        else:
            for a, b in zip(ks, ks[1:]):
                if a[0] <= t <= b[0]: break
            u = ease((t - a[0]) / (b[0] - a[0]))
        p = Vector(a[1]).lerp(Vector(b[1]), u); tg = Vector(a[2]).lerp(Vector(b[2]), u); ln = a[3] + (b[3] - a[3]) * u
        return (p, tg, ln, roll(t) if callable(roll) else roll, tg, shake)
    return fn


def zombie(sh, p0, yaw=0, speed=.32, s0=1.0, face=None, arms=True, walking=True, clip='82_08'):
    """Grandpa Walt, grey-green and dusty, shuffling with his arms out"""
    z = toon(sh, 'WALT', WALT); skin(z, ZSKIN)
    if walking: a = walk(sh, z, p0, yaw, clip, s0, face=face or [(0, 'bored')], speed=speed)
    else: a = stand(sh, z, p0[:2], yaw, '77_02', s0, face=face or [(0, 'bored')], z=p0[2] if len(p0) > 2 else None)
    def mod(t, s):
        if arms:
            f, sd = side_of(z); c = head_of(z, -.5) + f * .5
            sw = .03 * math.sin(t * 2.2)
            s['handL'] = tuple(c - sd * .17 + Vector((0, 0, sw))); s['handR'] = tuple(c + sd * .17 - Vector((0, 0, sw)))
        s['head'] = [s['head'][0], 8 + 4 * math.sin(t * 1.3), 10 * math.sin(t * .9)]
        s['lean'] = (s['lean'][0] + .05, s['lean'][1])
        return s
    override(a, mod)
    return z, a


def extras(sh, spots, seed=0, face=None, clips=('77_02', '80_48', '40_10', '80_44', '77_05'), look=None, walkers=()):
    """townsfolk at given (x, y, yaw) spots + walkers (x, y, yaw, speed)"""
    r = random.Random(seed); out = []
    for k, (x, y, yaw) in enumerate(spots):
        ch = toon(sh, f'X{seed}_{k}', CIV(seed * 50 + k), protect=False)
        stand(sh, ch, (x, y), yaw, clips[k % len(clips)], r.uniform(.5, 2.5), face=[(0, face[k % len(face)] if isinstance(face, (list, tuple)) else (face or r.choice(['idle', 'chat', 'watch'])))], look=look)
        out.append(ch)
    for k, (x, y, yaw, sp) in enumerate(walkers):
        ch = toon(sh, f'Y{seed}_{k}', CIV(seed * 50 + 30 + k), protect=False)
        walk(sh, ch, (x, y, C.CURB if abs(x) > C.ROAD else 0), yaw, r.choice(['82_08', '82_09', '82_11']), r.uniform(.5, 1.5), face=[(0, r.choice(['idle', 'chat', 'watch']))], speed=sp)
        out.append(ch)
    return out


def phone_prop(name, txt='NO WI-FI'):
    root = bpy.data.objects.new(name, None); T.coll('Town').objects.link(root)
    b = T.box(name + '_b', (.08, .012, .15), (0, 0, 0), T.plain('phonebody', '#16161a', .3)); b.parent = root
    s = C.sign(name + '_s', txt, .07, .13, (0, -.0065, 0), facing=(0, -1), bg='#2a5ad0', fg='#ffffff', size=(300, 560), font_scale=.3); s.parent = root
    return root


def glasses_prop(name):
    root = bpy.data.objects.new(name, None); T.coll('Town').objects.link(root)
    rim = T.plain('rim', '#1a1a1e', .4, .5)
    for x in (-.12, .12):
        o = T.lib.torus(f'{name}{x}', .075, .011, (x, 0, 0), rim, rot=(math.pi / 2, 0, 0), seg=24, mseg=6); o.parent = root
        g = T.cyl(f'{name}g{x}', .072, .004, (x, 0, 0), T.plain('lens', '#d8e8f0', .05, transmit=.8), rot=(math.pi / 2, 0, 0), v=20); g.parent = root
    br = T.box(name + 'br', (.1, .012, .012), (0, 0, .02), rim); br.parent = root
    return root


def wear_glasses(sh, ch, g, drop=lambda t: 0.0):
    def u(t):
        f, sd = side_of(ch); h = head_of(ch, .02)
        g.location = h + f * (ch.hy * ch.s * .98) - Vector((0, 0, drop(t)))
        g.rotation_mode = 'QUATERNION'; g.rotation_quaternion = (-f).to_track_quat('Y', 'Z')
    sh.updates.append(u)


def megaphone(name):
    me = bpy.data.meshes.new(name); import bmesh as bm_; b = bm_.new(); bm_.ops.create_cone(b, cap_ends=False, segments=16, radius1=.14, radius2=.05, depth=.4); b.to_mesh(me); b.free()
    o = bpy.data.objects.new(name, me); me.materials.append(T.plain('megaphone', '#e8e4dc', .5)); T.coll('Town').objects.link(o)
    return o


def pistol(name):
    g = PR.revolver(name); g.scale = (2.0, 2.0, 2.0); return g


def tp_stack(name, n=4):
    root = bpy.data.objects.new(name, None); T.coll('Town').objects.link(root); m = T.plain('tp', '#f8f8f4', .7)
    for k in range(n):
        o = T.cyl(f'{name}{k}', .06, .11, ((k % 2) * .12 - .06, 0, (k // 2) * .115), m, v=14); o.parent = root
    return root


def latte(name):
    root = bpy.data.objects.new(name, None); T.coll('Town').objects.link(root)
    c = T.cyl(name + 'c', .045, .13, (0, 0, .065), T.plain('cup', '#f4f0e8', .5), v=14); c.parent = root
    l = T.cyl(name + 'l', .048, .02, (0, 0, .135), T.plain('lid', '#3a2418', .5), v=14); l.parent = root
    s = T.cyl(name + 's', .047, .04, (0, 0, .06), T.plain('sleeve', '#8a5a3a', .8), v=14); s.parent = root
    return root


def police_line(sh, y, xs, face='determined', aim=None, seed=0):
    cops = []
    for k, x in enumerate(xs):
        c = toon(sh, f'COP{k}', COP(k + seed)); cops.append(c)
        a = stand(sh, c, (x, y), 180, '77_02', .8 + k * .37, face=[(0, face if isinstance(face, str) else face[k % len(face)])], look=(lambda t: aim(t)) if aim else None, z=.0)
        if aim:
            g = pistol(f'gun{k}')
            def mod(t, s, c=c):
                f, sd = side_of(c); tg = Vector(aim(t)); h = head_of(c, -.35)
                d = (tg - h); d.z = 0; d.normalize(); h = head_of(c, -.22)
                s['handR'] = tuple(h + d * .5 + sd * .06); s['handL'] = tuple(h + d * .44 - sd * .02 - Vector((0, 0, .04))); return s
            override(a, mod)
            hold(sh, g, c, 'R', (0, 0, .03), track=lambda t, c=c: (Vector(aim(t)) - head_of(c, -.22)).normalized())
    return cops


# ------------------------------------------------------------------ 1-5  Tuesday, sunrise, the alarm
def s_tuesday(sh):
    """'The zombie apocalypse reached the city on a Tuesday.'  Aerial glide down over the downtown towers at morning to the
    avenue: traffic, people, the big yellow billboard."""
    stage(sh, 'day', 32, 120)
    extras(sh, [(-8.2, 30, 90), (-8.6, 31, 0), (8.0, 44, -90), (8.4, 52, 180)], seed=1,
           walkers=[(7.6, 20, 0, 1.0), (-7.4, 36, 180, 1.0), (8.2, 60, 0, .9), (-8.0, 48, 0, 1.0), (7.2, 38, 180, 1.0)])
    sh.camera(cam_keys([(0, (26, 118, 46), (0, 40, 8), 24), (sh.dur, (9, 92, 13), (-1, 40, 6), 28)], roll=lambda t: K([(0, -5), (sh.dur, 0)], t), shake=.004), fstop=8)


def s_slowly(sh):
    """'Very, very slowly.'  Ground level on the empty outskirts road at dawn: a pair of fuzzy pink slippers shuffles one
    inch at a time; tilt up to the lurching grey silhouette."""
    stage(sh, 'sunset', 6, 20)
    z, a = zombie(sh, (0.6, 214.0, 0), yaw=0, speed=.22, face=[(0, 'bored')])
    def cam(t):
        u = ease((t - .9) / 1.9)
        base = Vector((0.75, 212.2 - .3 * t, .0))
        p = base + Vector((.35, -.4 * u, .18 + 1.0 * u))
        ft = Vector((0.6, 213.6 - .25 * t, .12)); hd = head_of(z, -.2)
        tg = ft.lerp(hd, u)
        return (p, tg, K([(0, 45), (sh.dur, 30)], t), 0, tg, .004)
    sh.camera(cam, fstop=2.6); sh.keylight(10, (1, .75, .55))


def s_jogger(sh):
    """'At sunrise, a jogger spotted one zombie,'  A jogger in a headband jogs towards us along the outskirts sidewalk,
    stops dead and points back up the road, mouth open."""
    stage(sh, 'sunset', 6, 20)
    j = toon(sh, 'JOG', JOG)
    a = sh.actor(j, [TO.Act(0, '09_01', .3, 1.6, loc=(7.6, 196.0, C.CURB), yaw=0, speed=.75),
                     TO.Act(1.35, '77_02', 1.0, 5, loc=(7.6, 193.4, C.CURB), yaw=160, lock_root=True, blend=.35)],
                 face=[(0, 'determined'), (1.4, 'shock'), (2.1, 'scream')], look=lambda t: (1.0, 214, 1.6) if t > 1.4 else None)
    def mod(t, s):
        if t > 1.7:
            f, sd = side_of(j); u = ease((t - 1.7) / .3); h = head_of(j, -.1)
            s['handR'] = tuple(Vector(s['handR']).lerp(h + Vector((-.2, .65, .15)), u))
        return s
    override(a, mod)
    sh.camera(cam_keys([(0, (4.7, 188.6, 1.45), (7.5, 194.6, 1.25), 30), (sh.dur, (4.9, 189.8, 1.45), (7.4, 194.0, 1.3), 34)], shake=.012), fstop=2.8)
    sh.keylight(12, (1, .78, .58))


def s_mile(sh):
    """'a mile outside downtown.'  Over the jogger's shoulder: the long empty road, the retirement home far away in the
    dawn haze, and one tiny swaying silhouette on it."""
    stage(sh, 'sunset', 6, 20)
    j = toon(sh, 'JOG', JOG)
    stand(sh, j, (6.95, 193.4), 160, '77_02', 1.4, face=[(0, 'scream')], look=lambda t: (1.0, 222, 1.4))
    zombie(sh, (0.8, 222.0, 0), yaw=0, speed=.25)
    sh.camera(cam_keys([(0, (6.5, 190.6, 1.85), (0.9, 221.5, 1.2), 50), (sh.dur, (6.5, 190.9, 1.85), (0.9, 221.5, 1.15), 62)], shake=.006), fstop=6)


def s_alarm(sh):
    """'The mayor sounded the alarm.'  Low angle on the City Hall steps: the mayor bellows into a megaphone, the siren on
    its pole spinning red, staff running."""
    stage(sh, 'day', 30, 120)
    m = toon(sh, 'MAYOR', MAYOR)
    a = stand(sh, m, (0.6, C.CITYHALL_Y + 4.6), 175, '79_73', 1.5, face=[(0, 'shout')], z=.95, talk=[(0, 3, 1.0)])
    meg = megaphone('meg')
    def mod(t, s):
        f, sd = side_of(m); h = head_of(m, -.12); s['handR'] = tuple(h + f * .32 + sd * .12); s['handL'] = tuple(h + f * .5 - sd * .02 - Vector((0, 0, .05))); return s
    override(a, mod)
    def mpos(t):
        f, sd = side_of(m); h = head_of(m, -.1); meg.location = h + f * .5 - sd * .03
        meg.rotation_mode = 'QUATERNION'; meg.rotation_quaternion = (-f).to_track_quat('Z', 'Y')
    sh.updates.append(mpos)
    T.cyl('siren_pole', .06, 4.2, (3.4, C.CITYHALL_Y + 6.2, 2.1), T.plain('lamppole', '#2a2e33', .45, .6), v=8)
    sr = T.cyl('siren', .22, .3, (3.4, C.CITYHALL_Y + 6.2, 4.35), T.plain('sirenred', '#ff2010', .2, emit='#ff2010', strength=6), v=16)
    l = bpy.data.lights.new('sirenl', 'SPOT'); l.energy = 600; l.color = (1, .1, .05); l.spot_size = math.radians(40)
    lo = bpy.data.objects.new('sirenl', l); lo.location = (3.4, C.CITYHALL_Y + 6.2, 4.35); T.coll('Town').objects.link(lo)
    sh.updates.append(lambda t: setattr(lo, 'rotation_euler', (math.radians(80), 0, t * 9.0)))
    extras(sh, [], seed=2, walkers=[(-4.0, C.CITYHALL_Y + 10, 180, 1.6), (5.0, C.CITYHALL_Y + 12, 0, 1.6), (-7.5, C.CITYHALL_Y + 16, 0, 1.4)])
    sh.camera(cam_keys([(0, (2.2, C.CITYHALL_Y + 8.6, .7), (0.5, C.CITYHALL_Y + 4.0, 2.4), 26), (sh.dur, (1.8, C.CITYHALL_Y + 7.8, .8), (0.55, C.CITYHALL_Y + 4.2, 2.3), 30)],
                       roll=3, shake=.01), fstop=3.5)


# ------------------------------------------------------------------ 6-8  boarded, shelves, waiting
def s_boarded(sh):
    """'The city boarded up every window,'  A shopkeeper hammers plywood over his shop window; up the street every shop
    front is already boarded."""
    stage(sh, 'day', 30, 120, boarded=True)
    w = toon(sh, 'P_ham', CIV(7))
    xw = C.FRONT - .7; y0 = 33.0
    a = stand(sh, w, (xw, y0), -90, '77_02', 1.2, face=[(0, 'determined')])
    ham = T.box('hammer_h', (.03, .03, .3), (0, 0, 0), T.plain('hhandle', '#8a5a3a', .6))
    hh = T.box('hammer_k', (.12, .04, .04), (0, 0, .15), T.plain('steel', '#6a6a70', .3, 1.0)); hh.parent = ham
    def mod(t, s):
        k = abs(math.sin(t * 5.5)); s['handR'] = (C.FRONT - .12, y0 - .1, 1.75 + .3 * k); s['handL'] = (C.FRONT - .1, y0 + .45, 1.6); return s
    override(a, mod); hold(sh, ham, w, 'R', (0, 0, .05), rot=lambda t: (0, math.radians(-50 + 40 * abs(math.sin(t * 5.5))), 0))
    extras(sh, [(-8.6, 44, 90), (8.4, 52, -90)], seed=3, face='worry', walkers=[(-7.4, 60, 0, 1.6), (7.0, 70, 0, 1.5)])
    sh.keylight(16)
    sh.camera(cam_keys([(0, (6.9, 37.6, 1.75), (9.2, 33.0, 1.65), 28), (sh.dur, (7.1, 37.0, 1.7), (9.2, 33.2, 1.65), 30)], shake=.009), fstop=3.2)


def s_shelf(sh):
    """'emptied every shelf,'  Shoppers burst out of the MART hugging towers of toilet paper."""
    stage(sh, 'day', 30, 120, boarded=True)
    mart_y = None
    for o in bpy.data.objects:
        if o.name.endswith('_sign') and o.name.startswith('bld') and 'MART' in o.data.materials[0].name: pass
    ys = [(-8.4, 4.0), (-7.4, 6.2), (-8.8, 8.6), (-7.2, 10.4)]
    for k, (x, y) in enumerate(ys):
        ch = toon(sh, f'P_shop{k}', CIV(20 + k))
        a = walk(sh, ch, (x, y, C.CURB), 0, '09_01' if k % 2 == 0 else '82_09', .3, face=[(0, ['fear', 'determined', 'grin', 'worry'][k])], speed=.8 if k % 2 == 0 else 1.3)
        tp = tp_stack(f'tp{k}', 6 if k % 2 == 0 else 4)
        def mod(t, s, ch=ch):
            f, sd = side_of(ch); c = head_of(ch, -.55) + f * .3; s['handL'] = tuple(c - sd * .16); s['handR'] = tuple(c + sd * .16); return s
        override(a, mod)
        hold(sh, tp, ch, 'R', (0, 0, .0))
    sh.keylight(16)
    sh.camera(cam_keys([(0, (-7.3, -1.6, 1.45), (-8.0, 6.0, 1.3), 28), (sh.dur, (-7.3, -1.2, 1.45), (-8.0, 4.6, 1.3), 30)], shake=.012), fstop=3.2)


def s_waited(sh):
    """'and waited.'  Behind the police barriers in front of City Hall, cops and citizens stare up the empty avenue."""
    stage(sh, 'day', 30, 120, boarded=True)
    C.barriers(C.CITYHALL_Y + 14, n=8)
    police_line(sh, C.CITYHALL_Y + 12.6, [-5.6, -2.8, 0.2, 3.0, 5.8], face=['watch', 'determined', 'watch', 'suspicious', 'watch'])
    extras(sh, [(-7.6, C.CITYHALL_Y + 11.0, 180), (7.4, C.CITYHALL_Y + 10.6, 180), (-1.4, C.CITYHALL_Y + 10.4, 180), (1.6, C.CITYHALL_Y + 10.2, 180)], seed=4, face='watch',
           look=lambda t: (0, 40, 1.6))
    sh.camera(cam_keys([(0, (2.0, C.CITYHALL_Y + 19.5, 1.2), (0, C.CITYHALL_Y + 11.5, 1.5), 24), (sh.dur, (1.2, C.CITYHALL_Y + 18.0, 1.25), (0, C.CITYHALL_Y + 11.5, 1.5), 26)], shake=.006), fstop=4)


# ------------------------------------------------------------------ 9-10  the bus stop
def s_noon(sh):
    """'By noon, the zombie had reached the bus stop.'  High noon, wide: the zombie shuffles up to the bus stop."""
    stage(sh, 'day', 72, 160)
    zombie(sh, (C.ROAD + 1.0, C.BUS_Y + 4.0, C.CURB), yaw=0, speed=.25)
    sh.camera(cam_keys([(0, (1.0, C.BUS_Y - 5.5, 1.9), (C.ROAD + 1.3, C.BUS_Y + 1.8, 1.2), 30), (sh.dur, (1.4, C.BUS_Y - 4.6, 1.8), (C.ROAD + 1.3, C.BUS_Y + 2.0, 1.2), 33)], shake=.005), fstop=5)


def s_bus(sh):
    """'By sunset, it was still waiting for the bus.'  Sunset, slow push in: the zombie sits on the bus-stop bench, arms
    still out, under the sign NEXT BUS: SOON."""
    stage(sh, 'sunset', 7, 250)
    bx = C.ROAD + 2.6 + .45
    z, a = zombie(sh, (bx - .15, C.BUS_Y, C.CURB), yaw=90, walking=False, face=[(0, 'bored')])
    def sit(t, s):
        s['crouch'] = .62; s['loc'] = (bx - .2, C.BUS_Y, C.CURB + .02); return s
    override(a, sit)
    sh.camera(cam_keys([(0, (4.2, C.BUS_Y - 3.4, 1.45), (bx - .2, C.BUS_Y + .2, 1.15), 32), (sh.dur, (4.8, C.BUS_Y - 2.4, 1.35), (bx - .2, C.BUS_Y + .2, 1.1), 38)], shake=.004), fstop=3.2)
    sh.keylight(9, (1, .7, .5))


# ------------------------------------------------------------------ 11-14  bored, the news, the coffee cart
def s_bored(sh):
    """'On day two, the city got bored.'  The barrier line: one cop asleep standing up, one yawning, one on his phone."""
    stage(sh, 'day', 30, 120, boarded=True)
    C.barriers(C.CITYHALL_Y + 14, n=8)
    cops = police_line(sh, C.CITYHALL_Y + 12.6, [-2.2, -.6, 1.0, 2.6], face=['bored', 'bored', 'deadpan', 'bored'])
    ph = phone_prop('ph1')
    for a in sh.actors:
        if getattr(a, 'ch', None) is cops[2]:
            def mod(t, s, c=cops[2]):
                f, sd = side_of(c); h = head_of(c, -.25); s['handR'] = tuple(h + f * .3 + sd * .05); s['head'] = [0, -20, 0]; return s
            override(a, mod); hold(sh, ph, cops[2], 'R', (0, 0, .06), rot=lambda t: (math.radians(70), 0, 0))
        if getattr(a, 'ch', None) is cops[0]:
            a.face = H.expr_track([(0, 'bored')]); override(a, lambda t, s: (s.__setitem__('head', [0, 25, 18]) or s))
    extras(sh, [(-6.8, C.CITYHALL_Y + 11.0, 150), (6.9, C.CITYHALL_Y + 11.2, 200)], seed=5, face=['bored', 'bored'])
    for k, (x, y) in enumerate(((-6.8, C.CITYHALL_Y + 11.0),)):
        pass
    sh.camera(cam_keys([(0, (-3.6, C.CITYHALL_Y + 15.6, 1.7), (0.2, C.CITYHALL_Y + 12.5, 1.35), 26), (sh.dur, (-2.8, C.CITYHALL_Y + 15.5, 1.65), (.9, C.CITYHALL_Y + 12.5, 1.35), 28)], shake=.006), fstop=3.2)


def s_news(sh):
    """'The evening news started taking bets.'  TV studio: the anchor beams at camera beside a big screen of odds."""
    F.setup(sh, 'night', 20, 120, town=False, haze=False); sh.town = False
    at = C.studio()
    an = toon(sh, 'ANCHOR', ANCHOR)
    T.box('st_riser', (2.4, 1.4, .4), (at.x - .4, at.y + .55, .2), T.plain('riser', '#1a2030', .4))
    stand(sh, an, (at.x - .4, at.y + .5), 0, '80_48', 1.0, face=[(0, 'grin')], z=.4, talk=[(0, 2.6, 1.0)])
    sh.camera(cam_keys([(0, (at.x + .6, at.y - 4.6, 1.7), (at.x + .55, at.y + 2.0, 1.9), 26), (sh.dur, (at.x + .4, at.y - 3.6, 1.65), (at.x + .6, at.y + 2.0, 1.95), 28)], shake=.003), fstop=4)


def s_cart(sh):
    """'Someone opened a coffee cart, right on the zombie's route.'  A barista sets out cups at a coffee cart in the middle
    of the road; the zombie shuffles towards it in the background."""
    stage(sh, 'day', 34, 120)
    cart = Vector((2.2, C.CART_Y, 0))
    b = toon(sh, 'BARISTA', BARISTA)
    stand(sh, b, (cart.x - 1.0, cart.y - .5), 200, '80_48', 1.0, face=[(0, 'grin')], z=0)
    zombie(sh, (0.2, C.CART_Y + 6.5, 0), yaw=0, speed=.25)
    extras(sh, [(-7.6, C.CART_Y - 4, 90), (-7.8, C.CART_Y - 3, 0)], seed=6, face='watch', look=lambda t: (0.4, C.CART_Y + 9, 1.4))
    sh.camera(cam_keys([(0, (-1.6, C.CART_Y - 5.4, 1.6), (1.4, C.CART_Y + 2.0, 1.3), 26), (sh.dur, (-1.2, C.CART_Y - 4.2, 1.5), (1.4, C.CART_Y + 2.5, 1.3), 28)], shake=.006), fstop=4)


def s_bought(sh):
    """'The zombie bought a latte.'  At the cart: the zombie pays with a coin, takes the cup and sips; the barista smiles."""
    stage(sh, 'day', 34, 120)
    cart = Vector((2.2, C.CART_Y, 0))
    b = toon(sh, 'BARISTA', BARISTA)
    ab = stand(sh, b, (cart.x + 1.0, cart.y - .2), -90, '80_48', 1.0, face=[(0, 'grin'), (1.4, 'happy')], z=0)
    z, az = zombie(sh, (cart.x - 1.1, cart.y - .1, 0), yaw=90, walking=False, arms=False, face=[(0, 'bored'), (2.0, 'happy')])
    cup = latte('latte')
    def zmod(t, s):
        f, sd = side_of(z); h = head_of(z, -.2)
        if t < 1.2: s['handR'] = tuple(Vector((cart.x - .55, cart.y - .1, 1.2)))
        else:
            u = ease((t - 1.2) / .6); s['handR'] = tuple(Vector((cart.x - .55, cart.y - .1, 1.2)).lerp(h + f * .22 + sd * .05 - Vector((0, 0, .12)), u))
        s['handL'] = tuple(head_of(z, -.5) + f * .35 - sd * .2)
        return s
    override(az, zmod)
    def bmod(t, s):
        if t < 1.3: s['handR'] = (cart.x - .2, cart.y - .1, 1.25)
        return s
    override(ab, bmod)
    hold(sh, cup, z, 'R', (0, 0, -.04))
    sh.camera(cam_keys([(0, (cart.x - .2, cart.y - 3.9, 1.6), (cart.x - .1, cart.y, 1.25), 26), (sh.dur, (cart.x - .3, cart.y - 3.3, 1.55), (cart.x - .2, cart.y, 1.3), 29)], shake=.005), fstop=3.2)


# ------------------------------------------------------------------ 15-19  City Hall, aim, the bite
def ch_scene(sh, aim_t=None, cops=True, mayor_xy=(0.3, None), face=None, barrier=False, xs=(-2.4, -1.2, 1.8, 3.0)):
    stage(sh, 'day', 38, 320, boarded=True)
    yC = C.CITYHALL_Y
    if barrier: C.barriers(yC + 14, n=8)
    if cops:
        target = lambda t: (0.3, yC + 18.0, 1.3)
        police_line(sh, yC + 12.6, list(xs), face=face or 'determined', aim=target)
    extras(sh, [(-7.6, yC + 11.0, 180), (7.4, yC + 10.6, 180), (-8.6, yC + 12.4, 160), (8.6, yC + 12.2, 200)], seed=8, face=['fear', 'watch', 'worry', 'shock'], look=lambda t: (0.3, yC + 18, 1.5))


def s_cityhall(sh):
    """'On day three, it finally reached City Hall.'  High wide from the City Hall portico: the zombie shuffles across the
    plaza towards the police line."""
    ch_scene(sh, barrier=True)
    yC = C.CITYHALL_Y
    zombie(sh, (0.3, yC + 23.0, 0), yaw=0, speed=.3)
    sh.camera(cam_keys([(0, (-1.8, yC + 8.2, 3.6), (0.3, yC + 21.5, 1.0), 26), (sh.dur, (-1.5, yC + 9.0, 3.0), (0.3, yC + 21.8, 1.1), 28)], shake=.004), fstop=6)


def s_aim(sh):
    """'The whole police force took aim.'  Zombie's-eye dolly along the line of pistols pointed straight at us."""
    ch_scene(sh, xs=(-2.0, -.7, .6, 1.9), face=['determined', 'angry', 'determined', 'suspicious'])
    yC = C.CITYHALL_Y
    sh.camera(cam_keys([(0, (-1.6, yC + 16.6, 1.45), (-1.0, yC + 12.6, 1.45), 24), (sh.dur, (2.4, yC + 16.5, 1.45), (1.6, yC + 12.6, 1.45), 24)], shake=.008), fstop=3.5)


def s_bite(sh):
    """'The zombie groaned, raised a rotting hand, and bit the mayor.'  The mayor steps out to greet it; the zombie
    groans, lifts a hand and chomps the mayor's arm."""
    ch_scene(sh)
    yC = C.CITYHALL_Y
    m = toon(sh, 'MAYOR', MAYOR)
    mp = Vector((0.3, yC + 16.6, 0)); zp = Vector((0.3, yC + 17.7, 0))
    am = stand(sh, m, mp.xy, 180, '79_73', 1.0, face=[(0, 'smile'), (1.0, 'nervous'), (2.6, 'shock')], z=0)
    z, az = zombie(sh, (zp.x, zp.y, 0), yaw=0, walking=False, arms=False, face=[(0, 'bored'), (.4, 'scream'), (2.4, 'chat')])
    TB = 2.45
    def mmod(t, s):
        f, sd = side_of(m); s['handR'] = tuple(head_of(m, -.55) + f * .55 + sd * .08); return s
    override(am, mmod)
    def zmod(t, s):
        f, sd = side_of(z); h = head_of(z, -.2)
        u = ease((t - .9) / .8)
        s['handR'] = tuple((h + f * .2 + sd * .25 - Vector((0, 0, .5))).lerp(h + f * .3 + sd * .22 + Vector((0, 0, .25)), u))
        s['handL'] = tuple(h + f * .25 - sd * .2 - Vector((0, 0, .45)))
        b = ease((t - TB) / .25); s['lean'] = (s['lean'][0] + .14 * b, 0); s['head'] = [0, 22 * b, 0]
        return s
    override(az, zmod)
    sh.camera(cam_keys([(0, (-3.4, yC + 16.2, 1.5), (0.3, yC + 17.2, 1.35), 30), (sh.dur, (-2.7, yC + 16.5, 1.45), (0.3, yC + 17.2, 1.3), 34)],
                       roll=lambda t: 2.5 * math.sin(max(0, t - TB) * 26) * math.exp(-max(0, t - TB) * 5), shake=.008), fstop=3.2)


def s_gently(sh):
    """'Gently. It had no teeth.'  Close two-shot: the zombie gums the mayor's sleeve; the mayor looks down, baffled."""
    ch_scene(sh, face='confused')
    yC = C.CITYHALL_Y
    m = toon(sh, 'MAYOR', MAYOR)
    am = stand(sh, m, (0.3, yC + 16.6), 180, '77_02', 1.0, face=[(0, 'confused'), (1.6, 'deadpan')], z=0, look=lambda t: tuple(head_of(sh.chars['WALT'], -.1)))
    z, az = zombie(sh, (0.3, yC + 17.55, 0), yaw=0, walking=False, arms=False, face=[(0, 'chat')])
    def mmod(t, s):
        f, sd = side_of(m); s['handR'] = tuple(head_of(m, -.55) + f * .5 + sd * .08); return s
    override(am, mmod)
    def zmod(t, s):
        f, sd = side_of(z); s['lean'] = (s['lean'][0] + .12, 0); s['head'] = [0, 20 + 6 * math.sin(t * 9), 0]
        hp = head_of(m, -.55) + facing(m) * .5; s['handR'] = tuple(hp + sd * .1); s['handL'] = tuple(hp - sd * .1); return s
    override(az, zmod)
    cu_two = lambda t: head_of(m, -.2).lerp(head_of(z, -.2), .5)
    def cam(t):
        c = cu_two(t); return (c + Vector((-1.6 + .2 * t / sh.dur, .75, .2)), c, 34, 0, c, .004)
    sh.camera(cam, fstop=2.4)


def s_doctor(sh):
    """'The doctor took one look, and lowered his glasses.'  Close on the doctor in his white coat peering, then slowly
    lowering his spectacles."""
    ch_scene(sh, cops=False)
    yC = C.CITYHALL_Y
    d = toon(sh, 'DOC', DOC)
    ad = stand(sh, d, (-.6, yC + 17.0), -110, '77_02', 1.0, face=[(0, 'suspicious'), (1.6, 'deadpan')], z=0, look=lambda t: (0.6, yC + 17.4, 1.3))
    zombie(sh, (0.6, yC + 17.5, 0), yaw=70, walking=False, arms=False, face=[(0, 'bored')])
    g = glasses_prop('specs')
    wear_glasses(sh, d, g, drop=lambda t: .07 * ease((t - 1.4) / .8))
    def dmod(t, s):
        if t > 1.2:
            u = ease((t - 1.2) / .5); f, sd = side_of(d); s['handR'] = tuple(Vector(s['handR']).lerp(head_of(d, -.06) + f * .3 + sd * .1, u))
        return s
    override(ad, dmod)
    cu(sh, d, angle=-20, elev=3, size=(.85, .62), lens=50, fstop=2.0)


def s_notzombie(sh):
    """'It wasn't a zombie.'  The doctor wipes the grey dust off the 'zombie's' face with a handkerchief - pink skin
    underneath."""
    ch_scene(sh, cops=False)
    yC = C.CITYHALL_Y
    d = toon(sh, 'DOC', DOC)
    ad = stand(sh, d, (-.55, yC + 17.0), -110, '77_02', 1.0, face=[(0, 'deadpan')], z=0, look=lambda t: (0.6, yC + 17.5, 1.3))
    z, az = zombie(sh, (0.6, yC + 17.5, 0), yaw=70, walking=False, arms=False, face=[(0, 'bored'), (.8, 'surprise')])
    g = glasses_prop('specs'); wear_glasses(sh, d, g, drop=lambda t: .07)
    hk = T.box('hanky', (.16, .02, .14), (0, 0, 0), T.plain('hanky', '#f4f0e8', .8))
    def dmod(t, s):
        zf = head_of(z, -.05) + facing(z) * .25
        s['handR'] = tuple(zf + Vector((0, 0, .06 * math.sin(t * 12)))); return s
    override(ad, dmod); hold(sh, hk, d, 'R', (0, 0, 0))
    sh.updates.append(lambda t: skin(z, tuple(a + (b - a) * ease((t - .2) / 1.0) for a, b in zip(ZSKIN, WHITE))))
    cu(sh, z, angle=35, elev=3, size=(.9, .7), lens=50, fstop=2.2)


def s_walt(sh):
    """'It was Grandpa Walt.'  Reveal: Grandpa Walt in his cardigan and pink slippers, sipping his latte, beaming; the
    mayor, the doctor and the cops behind him gape."""
    ch_scene(sh, cops=True, face='shock')
    yC = C.CITYHALL_Y
    z, az = zombie(sh, (0.3, yC + 17.4, 0), yaw=180, walking=False, arms=False, face=[(0, 'happy'), (1.0, 'grin')])
    skin(z, WHITE)
    cup = latte('latte')
    def zmod(t, s):
        f, sd = side_of(z); s['handR'] = tuple(head_of(z, -.32) + f * .25 + sd * .12); s['head'] = [0, -6, 0]; s['lean'] = (0, 0); return s
    override(az, zmod); hold(sh, cup, z, 'R', (0, 0, -.04))
    m = toon(sh, 'MAYOR', MAYOR); stand(sh, m, (-1.2, yC + 16.2), 150, '77_02', 1.2, face=[(0, 'shock')], z=0, look=lambda t: tuple(head_of(z)))
    d = toon(sh, 'DOC', DOC); stand(sh, d, (1.7, yC + 16.4), 210, '77_02', 1.6, face=[(0, 'deadpan')], z=0, look=lambda t: tuple(head_of(z)))
    g = glasses_prop('specs'); wear_glasses(sh, d, g, drop=lambda t: .07)
    sh.camera(cam_keys([(0, (0.5, yC + 20.6, 1.5), (0.3, yC + 17.0, 1.25), 34), (sh.dur, (0.45, yC + 19.9, 1.45), (0.3, yC + 17.0, 1.3), 38)], shake=.004), fstop=2.8)


# ------------------------------------------------------------------ 20-21  the long walk, the Wi-Fi
def s_home(sh):
    """'He'd walked all the way from the retirement home,'  Aerial: a single trail of slipper prints runs from the steps of
    SUNSET ACRES RETIREMENT HOME all the way down the avenue towards downtown."""
    stage(sh, 'day', 30, 120)
    C.footprints([(0.4, C.HOME_Y + 3.5), (0.5, 200), (0.4, 150), (1.2, C.BUS_Y + 3), (C.ROAD + 1, C.BUS_Y), (0.5, 120), (0.4, 80)])
    sh.camera(cam_keys([(0, (6, 150, 22), (0, C.HOME_Y, 3), 30), (sh.dur, (3.5, 205, 12), (0, C.HOME_Y + 4, 4.5), 34)], roll=lambda t: K([(0, 3), (sh.dur, 0)], t), shake=.004), fstop=8)


def s_wifi(sh):
    """'to complain about the Wi-Fi.'  Grandpa Walt shoves his phone (NO WI-FI) in the mayor's face; the mayor sighs."""
    ch_scene(sh, cops=True, face='bored')
    yC = C.CITYHALL_Y
    z, az = zombie(sh, (0.3, yC + 17.5, 0), yaw=0, walking=False, arms=False, face=[(0, 'angry'), (1.2, 'shout')])
    skin(z, WHITE)
    m = toon(sh, 'MAYOR', MAYOR); stand(sh, m, (0.3, yC + 16.6), 180, '77_02', 1.0, face=[(0, 'deadpan'), (1.6, 'bored')], z=0, look=lambda t: tuple(head_of(z)))
    ph = phone_prop('wph')
    def zmod(t, s):
        f, sd = side_of(z); jab = .05 * math.sin(t * 9) if t > 1.2 else 0
        s['handR'] = tuple(head_of(z, -.08) + f * (.42 + jab) + sd * .1); s['head'] = [0, -4, 0]; return s
    override(az, zmod)
    def ph_u(t):
        bpy.context.view_layer.update(); f, sd = side_of(z)
        ph.location = z.hands['R'].matrix_world.translation + Vector((0, 0, .08)); ph.rotation_mode = 'QUATERNION'; ph.rotation_quaternion = (-f).to_track_quat('Y', 'Z')
    sh.updates.append(ph_u)
    sh.camera(cam_keys([(0, (-1.9, yC + 15.6, 1.55), (0.3, yC + 17.05, 1.35), 32), (sh.dur, (-1.6, yC + 15.9, 1.5), (0.3, yC + 17.05, 1.35), 36)], shake=.005), fstop=2.6)


SHOTS = {k[2:]: v for k, v in list(globals().items()) if k.startswith('s_') and callable(v)}

if __name__ == '__main__':
    F.main(SHOTS)
