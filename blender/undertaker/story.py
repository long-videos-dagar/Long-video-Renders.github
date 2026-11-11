"""THE UNDERTAKER'S BEST CUSTOMER - dark comedy short (DAGAR CLIPS).  Same engine as the Wild West short: ink-outline
round-head toons with mocap acting in the real Dry Gulch town, plus Boot Hill, coffins and the undertaker's shop.
    python3 story.py -- still <shot> out.png [t]
    python3 story.py -- frames <shot> <f0> <f1> <outdir>"""
import os, sys, json, math, random
HERE = os.path.dirname(os.path.abspath(__file__)); WEST = os.path.join(os.path.dirname(HERE), 'west')
sys.path.insert(0, HERE); sys.path.insert(0, WEST)
import film as F
F.CFG = json.load(open(os.path.join(HERE, 'shots.json')))
from film import bpy, Vector, Matrix, T, PR, TO, ease, K, lerp, head_of, facing, bone_pos, framed, cu, night_lights, S, W_, DECK
import town
import dress
import sets as U
import inkchar as H

# Dry Gulch: the barber becomes the undertaker, the street banner names the town
town.TOWN_BUILDINGS[:] = [('undertaker', -1, 22.5, 6.0, 9, 4.6, 'UNDERTAKER', '#3e3836', '#d8d0c0', 1) if b[0] == 'barber' else b for b in town.TOWN_BUILDINGS]
_banner = dress.banner
dress.banner = lambda y, text='WELCOME TO DRY GULCH', **k: _banner(y, text, **k)

HZ = U.HILL_H
EZ = TO.preset('Ezra', '#ece4d4', '#5a4a3a', hat='bowler', hatcol='#5a4632', vest='#8a6a3a', neckerchief='#b02020', stache=True, beardcol='#6a4a2a',
               haircol='#6a4a2a', height=1.0, boots='#3a2418', belt='#3a2418')
MORT = TO.preset('Mortimer', '#d8d4cc', '#18181c', hat='tophat', hatcol='#121214', vest='#1e1e24', duster='#111114', bolo=True, height=1.12,
                 boots='#0c0c0e', haircol='#2a2a2a', belt='#111111')
JOE = TO.preset('FatherJoe', '#1a1a1e', '#1a1a1e', hat=None, duster='#141418', neckerchief='#f4f0e8', haircol='#a8a8a4', height=.98, boots='#141414')
def widow(i): return TO.preset(f'Widow{i}', '#2a2830', '#1a1a1e', hat='bonnet', hatcol='#1c1a1e', dress=True, dresscol=['#1c1a1e', '#26222a', '#1e1c22'][i % 3],
                               shawl='#2e2a32', haircol=['#2a1a10', '#6a3a1a', '#8a8a88'][i % 3], height=.95, bun=True, collar=False, boots='#111111')
def bandsman(i): return TO.preset(f'Band{i}', '#ece4d4', '#2a2a3a', hat='bowler', hatcol='#2a2a3a', vest='#8a2a24', stache=i % 2 == 0, beardcol='#3a2a1a',
                                  haircol='#3a2a1a', height=1.0 + .04 * (i % 2), boots='#1a1a1a')

COFFIN_HEAD = Vector((0.0, 94.85, HZ + .08))          # coffin over the open grave (on planks), head end towards town


# ------------------------------------------------------------------ helpers
def stage(sh, mood='day', elev=38, az=140, veg=.7, grave=True, shop=False):
    out = F.setup(sh, mood, elev, az, town=True, veg=veg)
    if grave: U.boot_hill()
    if shop: out = U.shop_interior(SHOP)
    return out


SHOP = Vector((-95.0, -60.0, 0.0))


def toon(sh, cid, preset):
    if cid in ('EZRA', 'MORT', 'JOE') or cid[0] in 'WBP':           # the story's own characters are never auto-hidden
        if not hasattr(sh, 'protect'): sh.protect = set()
        sh.protect.add(cid)
    if cid not in sh.chars: sh.chars[cid] = TO.Toon(cid, preset)
    return sh.chars[cid]


def stand(sh, ch, xy, yaw, clip='77_02', s0=1.0, face=None, look=None, z=None, talk=None):
    z = U.ground_z(*xy) if z is None else z
    return sh.actor(ch, [TO.Act(0, clip, s0, sh.dur + 2, loc=(xy[0], xy[1], z), yaw=yaw, lock_root=True)], face=face or [(0, 'idle')], look=look, talk=talk)


def walk(sh, ch, p0, yaw, clip='82_08', s0=1.0, face=None, speed=1.0, look=None):
    return sh.actor(ch, [TO.Act(0, clip, s0, sh.dur + 2, loc=p0, yaw=yaw, speed=speed)], face=face or [(0, 'idle')], look=look)


def override(actor, fn):
    """post-process the pose dict of a ToonActor: fn(t, pose) -> pose"""
    f0 = actor._fn
    actor.ch.fn = lambda t: fn(t, f0(t))
    return actor


class Puppet:
    """direct pose control (lying in a coffin, sitting up...): pose(t) -> dict; post(t) runs after apply"""
    def __init__(self, ch, pose, post=None):
        self.ch, self.pose, self.post = ch, pose, post
        ch.fn = lambda t: self.pose(t)
    def apply(self, t):
        self.ch.apply(t)
        if self.post: self.post(t)


def local_to_world(loc, yaw, sc, p):
    M = Matrix.Translation(Vector(loc)) @ Matrix.Rotation(math.radians(yaw), 4, 'Z') @ Matrix.Scale(sc, 4)
    return tuple(M @ Vector(p))


def lie_in(sh, ch, coffin, face, sit=None, hands='folded', wave=None, hand_targets=None, head_y=.36, z=.34):
    """lay a toon in a coffin, face up, head on the pillow (head_y from the head end).  The toon head is ~.56 m deep, so
    the body rides z above the coffin floor (z=.2 keeps the face under a closed lid).  sit(t) -> 0..1 sits the torso up."""
    yaw_c = math.degrees(coffin.root.rotation_euler.z); yaw = yaw_c + 180
    ftrack = H.expr_track(face); reach = 1.1 * ch.s
    def pose(t):
        feet = coffin.world((0, head_y + reach, z))
        u = sit(t) if sit else 0.0
        d = dict(loc=tuple(feet), yaw=yaw, face=ftrack(t), lean=(.714 * u, 0), head=[0, -18 * (1 - u), 0], crouch=0.0)
        sc = ch.s
        if hands == 'folded' and u < .5:
            d['handL'] = local_to_world(feet, yaw, sc, (-.07, -.2, ch.L + ch.TL * .3))
            d['handR'] = local_to_world(feet, yaw, sc, (.07, -.22, ch.L + ch.TL * .26))
        if hand_targets:
            for k, v in hand_targets(t, feet, yaw, sc).items(): d[k] = v
        return d
    def post(t):
        ch.root.rotation_euler = (-math.pi / 2, 0, math.radians(yaw))
    p = Puppet(ch, pose, post); sh.actors.append(p); return p


def grave_coffin(kind='pine', length=2.15, at=None, yaw=0.0, planks=True, name='coffin'):
    at = at or COFFIN_HEAD
    if planks:
        pw = T.wood('gplank', '#6a5640', weather=.8)
        for y in (at.y + .45, at.y + length - .45): T.box('gplank', (2.0, .26, .07), (at.x, y, HZ + .035), pw)
    c = U.Coffin(name, tuple(at), yaw=yaw, kind=kind, length=length)
    return c


def mourners(sh, n, seed=0, face='sad', clip=None, x=-3.0, y0=93.8, dy=1.05, black=True, look=None):
    out = []
    for k in range(n):
        p = widow(k + seed) if (black and k % 2 == 0) else TO.crowd_preset(300 + seed * 11 + k)
        ch = toon(sh, f'M{seed}_{k}', p)
        xx = x - (k % 2) * .9; yy = y0 + (k // 2) * dy * 1.6 + (k % 2) * .5
        stand(sh, ch, (xx, yy), 90 + random.Random(k + seed).uniform(-15, 15), clip or ['77_02', '40_10', '77_05'][k % 3], 1.0 + k * .7,
              face=[(0, face if isinstance(face, str) else face[k % len(face)])], look=look or (lambda t: (0, 96, HZ + 1.2)))
        out.append(ch)
    return out


def hold(sh, obj, ch, side='R', off=(0, 0, 0), rot=None):
    def u(t):
        bpy.context.view_layer.update(); p = ch.hands[side].matrix_world.translation.copy(); obj.location = p + Vector(off)   # pose key handR drives hands['R']
        if rot is not None: obj.rotation_euler = rot(t) if callable(rot) else rot
    sh.updates.append(u)


def cam_keys(keys, roll=0.0, shake=.008, lens=None):
    """keys: [(t, pos, target, lens)] smooth glide between them -> camera fn"""
    def fn(t):
        ks = sorted(keys, key=lambda k: k[0])
        if t <= ks[0][0]: a = b = ks[0]; u = 0
        elif t >= ks[-1][0]: a = b = ks[-1]; u = 0
        else:
            for a, b in zip(ks, ks[1:]):
                if a[0] <= t <= b[0]: break
            u = ease((t - a[0]) / (b[0] - a[0]))
        p = Vector(a[1]).lerp(Vector(b[1]), u); tg = Vector(a[2]).lerp(Vector(b[2]), u); ln = a[3] + (b[3] - a[3]) * u
        r = roll(t) if callable(roll) else roll
        return (p, tg, ln, r, tg, shake)
    return fn


def clear_area(xy, r):
    """hide town props (horses, wagons, barrels...) around a spot so a set piece can sit there"""
    for o in list(bpy.data.objects):
        if o.parent is not None or o.type not in ('MESH', 'EMPTY', 'CURVE') or o.hide_render: continue
        p = o.matrix_world.translation
        if math.hypot(p.x - xy[0], p.y - xy[1]) > r or (o.type == 'MESH' and max(o.dimensions) > 6.0): continue
        for q in [o] + list(o.children_recursive): q.hide_render = True


def side_of(ch):
    f = facing(ch); return f, f.cross(Vector((0, 0, 1))).normalized()


# ------------------------------------------------------------------ 1-2  Boot Hill, the four graves, the climb out
def s_hook(sh):
    """'Ezra Pike had been buried four times.'  Close on a board marked EZRA PIKE / NOT DEAD, pull back and up along the
    row of four identical graves, the undertaker waiting at the far end, dusk."""
    stage(sh, 'sunset', 7, 300)
    mort = toon(sh, 'MORT', MORT)
    stand(sh, mort, (7.3, 92.6), -70, '40_10', 2.0, face=[(0, 'bored')])
    sh.camera(cam_keys([(0, (-6.2, 90.65, HZ + .74), (-6.0, 91.8, HZ + .42), 32), (.45, (-6.25, 90.55, HZ + .78), (-5.98, 91.8, HZ + .44), 32),
                        (sh.dur, (-9.4, 88.7, HZ + 2.2), (1.2, 92.6, HZ + .5), 26)], roll=lambda t: K([(0, 2), (sh.dur, 0)], t), shake=.006), fstop=4)


def s_climb(sh):
    """'And every time, he climbed out to complain about the service.'  Low at the foot of the open grave: the lid bangs
    open, Ezra sits up furious, waving his complaint form; the undertaker peers down from the far rim, the town beyond."""
    stage(sh, 'sunset', 7, 300)
    c = grave_coffin(at=Vector((0, 94.95, HZ - U.PIT[3] + .05)), planks=False)
    c.open(0)
    ez = toon(sh, 'EZRA', EZ); mort = toon(sh, 'MORT', MORT)
    form = U.paper('form', 'complaint', (0, 0, 0), w=.34, h=.45)
    def lid(t): c.open(max(0.0, min(1.0, (t - .35) / .22)) * (1 + .08 * math.sin(max(0, t - .57) * 14) * math.exp(-max(0, t - .57) * 4)))
    sh.updates.append(lid)
    sit = lambda t: ease((t - .55) / .6)
    def hands(t, feet, yaw, sc):
        if t < 1.1: return {}
        w = math.sin((t - 1.1) * 9) * .06
        return {'handR': local_to_world(feet, yaw, sc, (.2, .25 + w, ch_h(ez) + .55)), 'handL': local_to_world(feet, yaw, sc, (-.25, .3, ch_h(ez) * .55))}
    lie_in(sh, ez, c, [(0, 'deadpan'), (.6, 'furious'), (2.2, 'shout')], sit=sit, hands=None, hand_targets=hands)
    hold(sh, form, ez, 'R', (0, 0, .2), rot=(0, 0, math.radians(180)))
    stand(sh, mort, (.35, 94.15), 180, '77_02', 3.0, face=[(0, 'bored'), (2.4, 'deadpan')], look=lambda t: (0, 96.0, 1.0))
    sh.camera(cam_keys([(0, (.55, 98.05, HZ + .95), (0, 95.6, .6), 26), (1.2, (.5, 97.9, HZ + .72), (0, 95.6, .85), 28), (sh.dur, (.42, 97.75, HZ + .55), (0, 95.5, 1.1), 30)],
                       roll=lambda t: K([(0, -3), (sh.dur, -1)], t), shake=.01), fstop=3.2)
    sh.keylight(14.0, (1, .85, .7))


def ch_h(ch): return ch.L + ch.TL


# ------------------------------------------------------------------ 3-8  Dry Gulch, the healthiest man in town
def s_gulch(sh):
    """'Dry Gulch, eighteen eighty.'  Drone glide in over the rooftops at morning, down to the main street banner."""
    stage(sh, 'day', 34, 120, veg=.6, grave=False)
    sh.camera(cam_keys([(0, (-24, -52, 36), (0, 10, 2), 22), (sh.dur, (-1.5, -6.5, 5.2), (0, 17.2, 4.6), 30)], roll=lambda t: K([(0, -6), (sh.dur, 0)], t), shake=.004), fstop=8)


def s_healthy(sh):
    """'Ezra was the healthiest man in town, and the most dramatic.'  Leading dolly: Ezra struts up the busy street towards
    us, chest out, then throws the back of his hand to his forehead in a theatrical swoon."""
    stage(sh, 'day', 34, 120, veg=.6, grave=False)
    for o in list(bpy.data.objects):
        p_ = o.matrix_world.translation
        if o.parent is None and o.type == 'MESH' and max(o.dimensions) < 2.5 and -.6 < p_.x < 3.2 and -1.0 < p_.y < 10 and p_.z < 1.0: o.hide_render = True
    for k, (x, y, yw, sp) in enumerate(((-1.7, -3.5, 180, .8), (2.9, -2.0, 0, 1.0), (-.6, -9.0, 180, .9))):
        walk(sh, toon(sh, f'Q{k}', TO.crowd_preset(130 + k * 9)), (x, y, 0), yw, '82_08' if k % 2 else '82_09', 1.0 + k, face=[(0, 'chat')], speed=sp)
    ez = toon(sh, 'EZRA', EZ)
    a = walk(sh, ez, (1.4, 1.0, 0), 180, '82_08', 1.0, face=[(0, 'smug'), (2.05, 'ohno')], speed=1.0)
    def mod(t, s):
        if t > 2.0:
            u = ease((t - 2.0) / .25); f, sd = side_of(ez)
            hd = head_of(ez, .12) + f * .3 + sd * .05
            s['handR'] = tuple(Vector(s['handR']).lerp(hd, u)); s['lean'] = (s['lean'][0] - .12 * u, s['lean'][1]); s['head'] = [s['head'][0], -14 * u, 0]
        return s
    override(a, mod)
    def cam(t):
        y = 1.0 + 1.25 * min(t, 2.0) + .2 * max(0, t - 2.0)
        return (Vector((.85, y + 3.7 - .3 * t, 1.5)), Vector((1.35, y, 1.12)), K([(0, 30), (sh.dur, 34)], t), 0, Vector((1.4, y + .2, 1.3)), .012)
    sh.camera(cam, fstop=3.2)


def s_cough(sh):
    """'A cough?'  Tight on Ezra: one tiny cough, eyes widen in horror."""
    stage(sh, 'day', 34, 120, veg=.5, grave=False)
    ez = toon(sh, 'EZRA', EZ)
    a = stand(sh, ez, (1.4, 4.0), 160, '77_02', 2.0, face=[(0, 'strain'), (.3, 'shock')], z=0)
    def mod(t, s):
        u = ease(t / .2) * (1 - ease((t - .3) / .2))
        s['handR'] = tuple(Vector(s['handR']).lerp(head_of(ez, -.12) + facing(ez) * .25, u * .9)); s['lean'] = (s['lean'][0] + .06 * u, 0)
        return s
    override(a, mod)
    cu(sh, ez, angle=18, elev=2, size=(.75, .6), lens=50, fstop=2.0)


def s_fun1(sh):
    """'Funeral.'  Smash to straight overhead: Ezra already lying in a pine coffin in the middle of the street, hands
    folded, utterly content; townsfolk peer in from the edges of frame."""
    stage(sh, 'day', 34, 120, veg=.5, grave=False)
    P = Vector((.4, 20.6, 0))
    clear_area(P, 2.6)
    c = U.Coffin('coffin', tuple(P), yaw=0, kind='pine'); c.open(1.0)
    ez = toon(sh, 'EZRA', EZ)
    lie_in(sh, ez, c, [(0, 'smug')])
    U.flowers('lily', c.world((.04, .95, .78)), n=3, spread=.05)
    for k, (dx, dy, yw) in enumerate(((1.2, .5, -90), (-1.25, 1.1, 90), (1.15, 1.85, -95))):
        ch = toon(sh, f'P{k}', TO.crowd_preset(90 + k * 7))
        stand(sh, ch, (P.x + dx, P.y + dy), yw, '77_02', 1.0 + k, face=[(0, ['bored', 'deadpan', 'confused'][k])], look=lambda t: tuple(c.world((0, .6, .5))), z=0)
    tg = c.world((0, 1.05, .4))
    sh.camera(cam_keys([(0, tg + Vector((0, .14, 3.4)), tg, 30), (sh.dur, tg + Vector((0, .13, 3.1)), tg, 31)], roll=0, shake=.004), fstop=4)


def s_splinter(sh):
    """'A splinter?'  Ezra holds up a fingertip with a tiny splinter, his face behind it frozen in terror."""
    stage(sh, 'day', 34, 120, veg=.5, grave=False)
    ez = toon(sh, 'EZRA', EZ)
    a = stand(sh, ez, (1.4, 4.0), 160, '77_02', 3.0, face=[(0, 'terror')], z=0)
    tip = []
    def mod(t, s):
        f, sd = side_of(ez); hp = head_of(ez, -.05) + f * .34 + sd * .2 - Vector((0, 0, .22)); s['handR'] = tuple(hp); tip[:] = [hp]; return s
    override(a, mod)
    spl = T.box('splinter', (.008, .008, .07), (0, 0, 0), T.plain('splinter', '#8a6a3a', .8))
    def u(t):
        if tip: spl.location = tip[0] + Vector((0, 0, .07)); spl.rotation_euler = (math.radians(15), math.radians(20), 0)
    sh.updates.append(u)
    def cam(t):
        hp = tip[0] if tip else Vector((1.3, 3.5, 1.1)); f, sd = side_of(ez); h = head_of(ez)
        mid = hp.lerp(h, .45)
        return (hp + f * (1.55 - .1 * t) - sd * .12 + Vector((0, 0, .15)), mid, 40, 0, hp, .004)
    sh.camera(cam, fstop=2.2); sh.keylight(16)


def s_fun2(sh):
    """'Funeral.'  Four pallbearers march the open coffin down the street towards camera, Ezra sitting up inside waving to
    the town like a parade float, the welcome banner overhead."""
    stage(sh, 'day', 34, 120, veg=.6, grave=False)
    c = U.Coffin('coffin', (0, 0, 0), yaw=180, kind='pine'); c.open(1.0)
    ez = toon(sh, 'EZRA', EZ)
    v = 1.15; y0 = 14.0; H0 = 1.42
    bearers = []
    for k, (dx, dy) in enumerate(((-.7, .35), (.7, .35), (-.7, 1.75), (.7, 1.75))):
        ch = toon(sh, f'P{k}', TO.crowd_preset(60 + k))
        a = walk(sh, ch, (dx, y0 + dy, 0), 0, '82_08', 1.0 + k * .3, face=[(0, 'bored')], speed=.9)
        def mod(t, s, dx=dx, dy=dy, a=a):
            cy = y0 - v * t; s['loc'] = (dx * 1.05, cy + dy, s['loc'][2]); s['yaw'] = 0
            s['handL' if dx > 0 else 'handR'] = (dx * .55, cy + dy, H0)
            return s
        override(a, mod); bearers.append(ch)
    def carry(t):
        c.root.location = (0, y0 + 2.12 - v * t, H0 + .03 * math.sin(t * 7)); c.root.rotation_euler = (0, 0, math.pi)
    sh.updates.append(carry)
    def hands(t, feet, yaw, sc):
        w = math.sin(t * 8) * .12
        return {'handR': local_to_world(feet, yaw, sc, (.3 + w, .35, ch_h(ez) + .6))}
    lie_in(sh, ez, c, [(0, 'happy'), (1.0, 'grin')], sit=lambda t: .55, hands='folded', hand_targets=hands)
    sh.keep_clear = [(0, y0 - v * k * .5, 0) for k in range(6)]
    sh.camera(cam_keys([(0, (1.3, 8.3, 1.75), (0, 13.6, 2.2), 21), (sh.dur, (1.35, 7.8, 1.75), (0, 12.0, 2.1), 23)], roll=-2, shake=.012), fstop=3.5)


# ------------------------------------------------------------------ 9-12  funerals one and two
def funeral_base(sh, kind='pine', length=2.15, lid=0.0, joe=True, n_mourn=4, mourn_face='sad'):
    c = grave_coffin(kind=kind, length=length); c.open(lid)
    people = mourners(sh, n_mourn, face=mourn_face) if n_mourn else []
    jo = None
    if joe:
        jo = toon(sh, 'JOE', JOE)
        stand(sh, jo, (-1.35, 94.0), 60, '77_02', 1.5, face=[(0, 'deadpan')], talk=[(0, sh.dur, .8)], look=lambda t: (0, 95.6, HZ + .8))
        bible = T.box('bible', (.16, .22, .05), (0, 0, 0), T.plain('bible', '#2a1a14', .6)); hold(sh, bible, jo, 'R', (0, -.05, .05), rot=(math.radians(60), 0, math.radians(60)))
    return c, people, jo


def s_small(sh):
    """'The first time, the coffin was too small.'  Slow push along a short closed coffin to the end: Ezra's boots stick
    out through it; the priest reads on regardless behind."""
    stage(sh, 'day', 36, 200)
    c, people, jo = funeral_base(sh, length=1.5, lid=0.0)
    ez = toon(sh, 'EZRA', EZ)
    lie_in(sh, ez, c, [(0, 'grit')], head_y=.52, z=.24)
    def cam(t):
        u = ease(t / sh.dur)
        p = c.world((1.75, .15, .95)).lerp(c.world((.95, 2.7, .95)), u)
        tg = c.world((0, .55, .42)).lerp(c.world((0, 1.85, .5)), u)
        return (p, tg, 30 + 4 * u, 0, tg, .008)
    sh.camera(cam, fstop=3.2)


def s_kick(sh):
    """'He kicked the lid off in the middle of the eulogy.'  Wide: the priest reads, the lid blasts off end over end,
    mourners leap back, Ezra sits up furious."""
    stage(sh, 'day', 36, 200)
    c, people, jo = funeral_base(sh, length=1.5, lid=0.0, mourn_face='sad')
    ez = toon(sh, 'EZRA', EZ)
    TK = 1.15
    lid = c.lid
    def fly(t):
        if t < TK: c.open(0); return
        u = t - TK; lid.parent = None
        p0 = c.world((0, .75, .55)); lid.location = p0 + Vector((1.6 * u, 1.2 * u, 4.2 * u - 4.9 * u * u)); lid.rotation_euler = (u * 9, u * 5, u * 2)
    sh.updates.append(fly)
    lie_in(sh, ez, c, [(0, 'grit'), (TK, 'furious')], sit=lambda t: ease((t - TK - .1) / .45), hands=None, head_y=.52, z=.24)
    for a in sh.actors:
        if hasattr(a, 'face') and a.ch is not ez and a.ch.cid.startswith('M'): a.face = H.expr_track([(0, 'sad'), (TK + .08, 'terror')])
    jo_a = [a for a in sh.actors if getattr(a, 'ch', None) is jo][0]; jo_a.face = H.expr_track([(0, 'deadpan'), (TK + .05, 'scream')])
    sh.camera(cam_keys([(0, (3.4, 101.2, HZ + 1.6), (-.6, 95.3, HZ + 1.15), 28), (sh.dur, (3.0, 100.6, HZ + 1.55), (-.5, 95.6, HZ + 1.25), 30)],
                       roll=lambda t: 2.5 * math.sin(max(0, t - TK) * 30) * math.exp(-max(0, t - TK) * 5)), fstop=4)


def s_nocry(sh):
    """'The second time, nobody cried.'  Slow diagonal dolly down the line of three bored mourners: a yawn, a pocket
    watch, a blank stare."""
    stage(sh, 'day', 36, 200)
    c, people, jo = funeral_base(sh, lid=0.0, joe=False, n_mourn=3, mourn_face=['bored', 'deadpan', 'bored'])
    watch = T.cyl('pwatch', .04, .015, (0, 0, 0), T.plain('watchgold', '#d4b048', .3, 1.0), rot=(math.pi / 2, 0, 0), v=16); hold(sh, watch, people[1], 'R', (0, -.04, .06))
    sh.camera(cam_keys([(0, (-.6, 91.25, HZ + 1.2), (-3.2, 94.1, HZ + 1.15), 28), (sh.dur, (-.75, 92.55, HZ + 1.15), (-3.4, 95.4, HZ + 1.15), 30)], shake=.006), fstop=3.2)


def s_names(sh):
    """'Ezra sat up and asked for names.'  From the foot of the grave: Ezra rises from the open coffin with a notebook,
    jabbing his pencil at the startled mourners."""
    stage(sh, 'day', 36, 200)
    c, people, jo = funeral_base(sh, lid=1.0, joe=False, n_mourn=3, mourn_face=['bored', 'deadpan', 'bored'])
    for o in [c.lid] + list(c.lid.children_recursive): o.hide_render = True
    ez = toon(sh, 'EZRA', EZ)
    for a in sh.actors:
        if getattr(a, 'ch', None) in people: a.face = H.expr_track([(0, 'bored'), (.55, 'fear')])
    def hands(t, feet, yaw, sc):
        if t < .7: return {}
        jab = math.sin((t - .7) * 7) * .1
        return {'handL': local_to_world(feet, yaw, sc, (-.15, .2, ch_h(ez) * .9)), 'handR': local_to_world(feet, yaw, sc, (.55 + jab, .25, ch_h(ez) + .25))}
    lie_in(sh, ez, c, [(0, 'suspicious'), (1.2, 'angry')], sit=lambda t: ease((t - .05) / .55), hands=None, hand_targets=hands)
    book = T.box('notebook', (.16, .22, .02), (0, 0, 0), T.plain('nb', '#d8ccb0', .8)); hold(sh, book, ez, 'L', (0, 0, .05), rot=(math.radians(50), 0, math.radians(20)))
    sh.camera(cam_keys([(0, (1.25, 99.1, HZ + 1.65), (-1.35, 95.3, HZ + 1.05), 24), (sh.dur, (1.05, 98.5, HZ + 1.55), (-1.15, 95.45, HZ + 1.1), 27)], shake=.009), fstop=3.2)


# ------------------------------------------------------------------ 13-15  the bill, the complaint
def s_double(sh):
    """'The third time, the undertaker charged him double.'  Shop interior, over Ezra's shoulder: the undertaker brings the
    DOUBLE stamp down on the invoice twice; push in and rack to the paper."""
    out = stage(sh, 'day', 30, 110, veg=.3, grave=False, shop=True)
    o = SHOP; ctr = out['counter']
    mort = toon(sh, 'MORT', MORT); ez = toon(sh, 'EZRA', EZ)
    bp = ctr + Vector((-.25, .04, .012))
    bill = U.paper('bill', 'bill', bp, rot=(-math.pi / 2, 0, 0), w=.3, h=.4)
    a = stand(sh, mort, (ctr.x - .1, ctr.y + .32), 0, '77_02', 1.0, face=[(0, 'deadpan'), (1.3, 'smirk')], z=0, look=lambda t: tuple(bp + Vector((0, 0, .3))) if t < 1.9 else tuple(head_of(ez)))
    stamp = T.cyl('stamp', .075, .16, (0, 0, 0), T.plain('stamp', '#8a1e1a', .5), v=16)
    def mod(t, s):
        k = 0.0
        for tt in (1.15, 1.75): k = max(k, math.exp(-((t - tt) / .09) ** 2))
        s['handR'] = tuple(bp + Vector((.04, .02, .3 - .24 * k))); return s
    override(a, mod); hold(sh, stamp, mort, 'R', (0, 0, -.11))
    stand(sh, ez, (ctr.x - .8, ctr.y - .95), 175, '79_74', 2.0, face=[(0, 'confused'), (1.2, 'shock'), (1.8, 'furious')], z=0, look=lambda t: tuple(bp))
    sh.camera(cam_keys([(0, (ctr.x - .3, ctr.y - 2.7, ctr.z + .85), (ctr.x - .15, ctr.y + .45, ctr.z + .45), 30), (1.9, (ctr.x - .1, ctr.y - 1.85, ctr.z + .7), (ctr.x - .2, ctr.y + .1, ctr.z + .2), 34),
                        (sh.dur, (ctr.x + .02, ctr.y - .95, ctr.z + .55), (ctr.x - .24, ctr.y + .02, ctr.z + .02), 38)], shake=.006), fstop=2.6)
    T.lantern('ctrlamp', tuple(ctr + Vector((.55, .15, .2))), energy=35)


def s_complaint(sh):
    """'Ezra filed a complaint.'  Lantern light in the grave: Ezra sits in his coffin scribbling on the complaint form in
    his lap; push in until the form reads."""
    stage(sh, 'sunset', 3, 300)
    c = grave_coffin(at=Vector((0, 94.95, HZ - U.PIT[3] + .05)), planks=False); c.open(1.0)
    ez = toon(sh, 'EZRA', EZ)
    form_p = c.world((0, 1.45, .66))
    form = U.paper('form', 'complaint', form_p, rot=(math.radians(-80), 0, math.pi), w=.34, h=.45)
    pencil = T.cyl('pencil', .008, .16, (0, 0, 0), T.plain('pencil', '#d8a830', .6), v=6)
    def hands(t, feet, yaw, sc):
        wx = math.sin(t * 22) * .03 + (t % .6) * .12 - .04
        return {'handR': tuple(form_p + Vector((wx, .02, .06))), 'handL': tuple(form_p + Vector((-.2, .1, .02)))}
    lie_in(sh, ez, c, [(0, 'determined'), (1.0, 'smirk')], sit=lambda t: 1.0, hands=None, hand_targets=hands)
    hold(sh, pencil, ez, 'R', (0, 0, .04), rot=(0, math.radians(30), math.radians(20)))
    T.lantern('glamp', tuple(c.world((.38, .55, .55))), energy=60)
    tg0 = c.world((0, 1.28, .85)); tg1 = c.world((0, 1.4, .75))
    sh.camera(cam_keys([(0, (.48, 97.55, HZ + 1.0), tg0, 26), (sh.dur, (.32, 97.32, HZ + .72), tg1, 28)], shake=.003), fstop=3.5)


def s_inside(sh):
    """'From inside the grave.'  Start low in the pit on Ezra handing his form up over his head; crane up and out of the
    grave to find the undertaker at the rim reaching down for it, lantern glow below."""
    stage(sh, 'sunset', 3, 300)
    c = grave_coffin(at=Vector((0, 94.95, HZ - U.PIT[3] + .05)), planks=False); c.open(1.0)
    ez = toon(sh, 'EZRA', EZ); mort = toon(sh, 'MORT', MORT)
    form = U.paper('form', 'complaint', (0, 0, 0), w=.34, h=.45)
    def hands(t, feet, yaw, sc):
        u = ease((t - .6) / 1.0)
        return {'handR': local_to_world(feet, yaw, sc, (.12, .5 + .15 * u, .7 + .65 * u))}
    lie_in(sh, ez, c, [(0, 'determined'), (1.4, 'smug')], sit=lambda t: 1.0, hands=None, hand_targets=hands)
    hold(sh, form, ez, 'R', (0, 0, .2), rot=(0, 0, math.radians(180)))
    a = stand(sh, mort, (.1, 94.2), 180, '77_02', 4.0, face=[(0, 'deadpan')], look=lambda t: (0, 95.6, 1.2))
    override(a, lambda t, s: (s.__setitem__('handR', (.05, 94.75, HZ - .2)) or s))
    T.lantern('glamp', tuple(c.world((.38, .55, .55))), energy=70)
    sh.camera(cam_keys([(0, (.1, 97.1, 1.2), (0, 96.0, 1.2), 22), (.5, (.1, 97.1, 1.3), (0, 96.0, 1.25), 22), (sh.dur, (.4, 98.3, 5.9), (0, 95.6, 1.2), 24)], shake=.004), fstop=4)


# ------------------------------------------------------------------ 16-17  the fourth funeral
def s_empty(sh):
    """'By the fourth funeral, the town stopped coming.'  Rows of empty benches, a tumbleweed bounces through, the
    undertaker alone in front of them; slow creep in."""
    stage(sh, 'day', 30, 220)
    c = grave_coffin(); c.open(0)
    for k in range(3): U.bench(f'bench{k}', (-3.8 - k * 1.4, 95.9, HZ), yaw=90, length=3.2)
    mort = toon(sh, 'MORT', MORT)
    a = stand(sh, mort, (-2.15, 94.2), 18, '40_10', 3.0, face=[(0, 'bored'), (1.6, 'sad')])
    tw = PR.tumbleweed('tw', (-9, 96.9, HZ + .35))
    if tw:
        def roll(t):
            x = -9 + 4.2 * t; tw.location = (x, 96.9 - .3 * t, HZ + .35 + abs(math.sin(t * 5)) * .35); tw.rotation_euler = (0, t * 6, 0)
        sh.updates.append(roll)
    sh.camera(cam_keys([(0, (-1.0, 91.0, HZ + 1.55), (-3.4, 95.7, HZ + .65), 26), (sh.dur, (-1.25, 91.75, HZ + 1.5), (-3.4, 95.7, HZ + .72), 28)], shake=.006), fstop=5)


def s_card(sh):
    """'Even the priest just mailed a card.'  Low on the closed coffin: a sympathy card propped on the lid - SORRY FOR YOUR
    LOSS (AGAIN) - the undertaker standing over it, flat-faced."""
    stage(sh, 'day', 30, 220)
    c = grave_coffin(); c.open(0)
    for k in range(3): U.bench(f'bench{k}', (-3.8 - k * 1.4, 95.9, HZ), yaw=90, length=3.2)
    mort = toon(sh, 'MORT', MORT)
    stand(sh, mort, (.35, 97.75), 0, '77_02', 2.0, face=[(0, 'deadpan'), (2.2, 'bored')], look=lambda t: tuple(c.world((0, .6, .6))))
    cp = c.world((0, .6, .685))
    card = U.paper('card', 'card', cp, rot=(math.radians(-14), 0, 0), w=.3, h=.225)
    T.box('envelope', (.3, .2, .008), c.world((.2, .82, .58)), T.plain('envelope', '#e8dcc0', .8), rot=(0, 0, .4))
    def cam(t):
        u = ease(t / sh.dur)
        p = (cp + Vector((.04, -1.0, .26))).lerp(cp + Vector((.02, -.78, .2)), u)
        tg = cp + Vector((0, .6, .14))
        fc = head_of(mort).lerp(cp, ease((t - .2) / .5))
        return (p, tg, 38, 0, fc, .004)
    sh.camera(cam, fstop=2.8); sh.keylight(14)


# ------------------------------------------------------------------ 18-22  the decision, the perfect funeral
def s_decision(sh):
    """'So the undertaker made a decision.'  Night, lantern-lit shop: slow push-in on the undertaker behind his counter;
    he slams his palm on the ledger."""
    out = stage(sh, 'night', 30, 110, veg=.3, grave=False, shop=True)
    ctr = out['counter']
    for n in ('s_window_l',):
        if n in bpy.data.objects: bpy.data.objects[n].data.energy = 120; bpy.data.objects[n].data.color = (.5, .6, 1.0)
    mort = toon(sh, 'MORT', MORT)
    a = stand(sh, mort, (ctr.x + .1, ctr.y + .3), 0, '77_02', 2.0, face=[(0, 'suspicious'), (.9, 'determined')], z=0)
    def mod(t, s):
        k = ease((t - .75) / .12)
        s['handR'] = tuple((ctr + Vector((-.25, .08, .45))).lerp(ctr + Vector((-.22, .08, .06)), k)) if t > .4 else s['handR']; return s
    override(a, mod)
    T.lantern('ctrlamp', tuple(ctr + Vector((.55, -.05, .2))), energy=45)
    def cam(t):
        h = head_of(mort); d = Vector((-.18, -1.0, .02)).normalized()
        dist = K([(0, 2.9), (sh.dur, 1.8)], t)
        return (h + d * dist, h + Vector((0, 0, -.18)), 36, K([(0, 0), (sh.dur, -5)], t), h, .006 + .02 * math.exp(-max(0, t - .87) * 12) * (t > .87))
    sh.camera(cam, fstop=2.4); sh.keylight(8, (1, .7, .45))


def perfect_set(sh, with_people=True, crowd=0, wreaths=(0, 1, 2, 3)):
    """the velvet funeral on Boot Hill: draped stand, wreaths, flowers, candles, band, paid mourners"""
    c = grave_coffin(kind='velvet', name='vcoffin'); c.open(1.0)
    for o in bpy.data.objects:
        if o.name.startswith(('mound', 'shovel')): o.hide_render = True
    drape = T.plain('drape', '#3a1430', .9); drape.node_tree.nodes['Principled BSDF'].inputs['Sheen Weight'].default_value = 1.0
    T.box('drape', (1.5, 2.6, .05), (0, 95.95, HZ + .07), drape)
    for k, (x, y) in enumerate(((-1.25, 94.2), (1.25, 94.2), (-1.25, 97.8), (1.25, 97.8))):
        if k not in wreaths: continue
        T.cyl(f'wstand{k}', .02, 1.2, (x, y, HZ + .6), T.plain('wstand', '#2a2a2a', .5, .8), v=6); U.wreath(f'wreath{k}', (x, y - .02, HZ + 1.25))
    for k in range(6): U.flowers(f'fl{k}', (-1.0 + k * .4, 93.6, HZ), n=6, spread=.18)
    for k, (x, y) in enumerate(((-.9, 93.9), (.9, 93.9), (-.9, 98.1), (.9, 98.1))):
        T.cyl(f'candle{k}', .035, .5, (x, y, HZ + .25), T.plain('wax', '#f0e8d8', .5), v=10)
        T.lib.sphere(f'flame{k}', .028, (x, y, HZ + .535), T.plain('cflame', '#ffd070', .5, emit='#ffaa30', strength=18))
        l = bpy.data.lights.new(f'cflame{k}', 'POINT'); l.energy = 6; l.color = (1, .7, .35); lo = bpy.data.objects.new(f'cflame{k}', l); lo.location = (x, y, HZ + .56); bpy.context.scene.collection.objects.link(lo)
    ez = toon(sh, 'EZRA', EZ)
    band = []
    if with_people:
        for k, kind in enumerate(('tuba', 'trumpet', 'drum')):
            ch = toon(sh, f'B{k}', bandsman(k)); x, y = 3.3 + (k % 2) * .5, 96.2 + k * 1.15
            a = stand(sh, ch, (x, y), -90, '77_02', 1.0 + k, face=[(0, 'happy')])
            ins = U.instrument(f'ins{k}', kind); band.append((ch, a, ins, kind))
    return c, ez, band


def tuba_at(ch): return head_of(ch, -.66) + Vector((-.22, 0, 0))


def play_band(sh, band, t_on=0.0, t_off=99.0):
    for ch, a, ins, kind in band:
        def mod(t, s, ch=ch, kind=kind):
            on = t_on <= t <= t_off; bob = math.sin(t * 2 * math.pi * 1.4) * (.04 if on else 0)
            hc = head_of(ch, -.18)
            fw = Vector((-1, 0, 0))
            if kind == 'trumpet': tg = hc + fw * .32 + Vector((0, 0, .02 + bob * .3)); s['handR'] = tuple(tg); s['handL'] = tuple(tg + Vector((0, .12, -.06)))
            elif kind == 'tuba': tl = tuba_at(ch); s['handR'] = tuple(tl + Vector((.02, -.08, -.14))); s['handL'] = tuple(tl + Vector((.02, .08, .18)))
            else: tg = hc + fw * .35 + Vector((0, 0, -.55 + (abs(math.sin(t * 9)) * .12 if on else 0))); s['handR'] = tuple(tg); s['handL'] = tuple(tg + Vector((0, .12, -.06)))
            s['crouch'] = s['crouch'] + max(0, bob) * .5
            return s
        override(a, mod)
        def u(t, ch=ch, ins=ins, kind=kind):
            p = ch.hands['R'].matrix_world.translation.copy()
            if kind == 'trumpet': ins.location = p + Vector((-.05, 0, 0)); ins.rotation_euler = (0, 0, math.radians(-90))
            elif kind == 'tuba': ins.location = tuba_at(ch); ins.rotation_euler = (0, math.radians(-12), math.radians(90)); ins.scale = (.85, .85, .85)
            else: ins.location = head_of(ch, -.85) + Vector((-.32, 0, 0)); ins.rotation_euler = (0, 0, 0)
        sh.updates.append(u)


def s_perfect(sh):
    """'One perfect funeral.'  Crane down over wreaths and candles onto the velvet funeral at golden hour."""
    stage(sh, 'sunset', 12, 245)
    c, ez, band = perfect_set(sh)
    lie_in(sh, ez, c, [(0, 'relief')])
    mourners(sh, 8, seed=3, face='sad')
    play_band(sh, band)
    sh.camera(cam_keys([(0, (4.2, 103.2, HZ + 6.8), (0, 96, HZ + .5), 22), (sh.dur, (2.9, 101.3, HZ + 3.5), (0, 95.9, HZ + .6), 26)], roll=lambda t: K([(0, 4), (sh.dur, 0)], t), shake=.005), fstop=5)


def s_velvet(sh):
    """'A velvet coffin.'  High three-quarter dolly along the open velvet coffin - gold handles, glowing purple lining -
    ending on Ezra's peaceful face on the pillow."""
    stage(sh, 'sunset', 12, 245)
    c, ez, band = perfect_set(sh, with_people=False)
    lie_in(sh, ez, c, [(0, 'relief')])
    def cam(t):
        u = ease(t / sh.dur)
        p = c.world((1.7, 2.3, 1.75)).lerp(c.world((1.25, .9, 1.55)), u)
        tg = c.world((0, 1.3, .35)).lerp(c.world((0, .55, .45)), u)
        return (p, tg, 30, 0, tg, .004)
    sh.camera(cam, fstop=3.2)


def s_band(sh):
    """'A brass band.'  Low three-quarter angle on the three-piece band in full swing, Boot Hill behind."""
    stage(sh, 'sunset', 12, 245)
    c, ez, band = perfect_set(sh)
    lie_in(sh, ez, c, [(0, 'relief')])
    play_band(sh, band)
    sh.camera(cam_keys([(0, (.6, 100.4, HZ + 1.3), (3.5, 97.3, HZ + 1.2), 26), (sh.dur, (.75, 100.15, HZ + 1.3), (3.55, 97.3, HZ + 1.25), 28)], roll=-3, shake=.008), fstop=3.5)


def s_tears(sh):
    """'Real tears. He paid for those.'  The undertaker presses a coin into each widow's glove - they instantly burst into
    tears."""
    stage(sh, 'sunset', 12, 245)
    c, ez, band = perfect_set(sh, wreaths=(1, 2, 3))
    lie_in(sh, ez, c, [(0, 'relief')])
    mort = toon(sh, 'MORT', MORT)
    ws = [toon(sh, f'W{k}', widow(k)) for k in range(2)]
    pos = [(-2.0, 93.7), (-2.0, 95.0)]
    TT = [.75, 1.45]
    for k, (w, p) in enumerate(zip(ws, pos)):
        a = stand(sh, w, p, 90, '77_02', 1.0 + k, face=[(0, 'deadpan'), (TT[k] + .1, 'sad')])
        def mod(t, s, k=k, w=w):
            if t > TT[k] + .1:
                hc = head_of(w, -.1); s['handR'] = tuple(hc + Vector((.22, 0, 0))); s['lean'] = (s['lean'][0] + .05 * math.sin(t * 14), 0)
            return s
        override(a, mod)
    m = stand(sh, mort, (-.8, 94.3), -115, '77_02', 2.5, face=[(0, 'deadpan')], look=lambda t: (pos[0][0], pos[0][1], HZ + 1.2) if t < 1.1 else (pos[1][0], pos[1][1], HZ + 1.2))
    def mmod(t, s):
        tg = pos[0] if t < 1.1 else pos[1]; u = math.sin(min(1, ((t - .3) % .7) / .7) * math.pi)
        s['handR'] = tuple(Vector((tg[0] + .6, tg[1], HZ + 1.1)).lerp(Vector((tg[0] + .3, tg[1], HZ + 1.05)), u)); return s
    override(m, mmod)
    coin = T.cyl('coin', .08, .012, (0, 0, 0), T.plain('coinb', '#ffd040', .2, 1.0, emit='#ffb020', strength=1.5), rot=(math.pi / 2, 0, 0), v=24); hold(sh, coin, mort, 'R', (-.1, -.04, .05), rot=(math.pi / 2, 0, math.radians(-30)))
    tear_streams(sh, [(w, TT[k] + .12) for k, w in enumerate(ws)], n=10, r=.03)
    sh.camera(cam_keys([(0, (-.42, 91.25, HZ + 1.55), (-1.3, 94.4, HZ + 1.3), 28), (sh.dur, (-.5, 91.7, HZ + 1.5), (-1.32, 94.5, HZ + 1.3), 31)], shake=.008), fstop=3.2)


def tear_streams(sh, who, n=6, r=.024):
    """comic tear streams squirting sideways from both eyes: who = [(toon, t_start)]"""
    tearm = T.plain('tearb', '#2f9cff', .05, emit='#2f8cff', strength=.6)
    drops = []
    for k, (w, t0) in enumerate(who):
        for j in range(n): drops.append((w, t0, j, T.lib.sphere(f'tear{k}_{j}', r, (0, 0, -50), tearm)))
    def upd(t):
        for w, t0, j, d in drops:
            if t < t0: d.location = (0, 0, -50); continue
            f, sd = side_of(w); ph = ((t - t0) * 2.2 + j / n) % 1.0; side = -1 if j % 2 else 1
            d.location = head_of(w, .02) + f * .2 + sd * side * (.14 + ph * .1) - Vector((0, 0, ph * .45))
    sh.updates.append(upd)


# ------------------------------------------------------------------ 23-26  happy, stopped, the band played, the undertaker wept
def s_happy(sh):
    """'Ezra lay there, listening, and for the first time in his life, he was happy.'  Slow push down onto Ezra in the
    velvet: eyes closed, the smile growing with the music, golden light and drifting petals."""
    stage(sh, 'sunset', 9, 245)
    c, ez, band = perfect_set(sh)
    lie_in(sh, ez, c, [(0, 'relief'), (2.6, 'smile'), (4.6, 'happy')])
    play_band(sh, band)
    petals(sh, c)
    def cam(t):
        hp = head_of(ez); u = ease(t / sh.dur)
        return (hp + Vector((.05, 1.15 - .3 * u, 1.95 - .55 * u)), hp + Vector((0, .3 - .12 * u, 0)), 32, 0, hp, .004)
    sh.camera(cam, fstop=2.4); sh.keylight(10, (1, .85, .65))


def petals(sh, c, n=14, t_land=None):
    pm = T.plain('petal', '#c8406a', .6)
    ps = []
    for k in range(n):
        o = T.box(f'petal{k}', (.04, .03, .004), (0, 0, -60), pm); ps.append(o)
    rng = random.Random(4)
    seeds = [(rng.uniform(-.5, .5), rng.uniform(.0, 2.1), rng.uniform(0, 4)) for _ in ps]
    def fall(t):
        for o, (x, y, ph) in zip(ps, seeds):
            z = 2.6 - ((t * .35 + ph) % 2.6)
            o.location = c.world((x + .1 * math.sin(t * 2 + ph), y, .45 + z)); o.rotation_euler = (t * 3 + ph, t * 2, ph)
    sh.updates.append(fall)


def s_stopped(sh):
    """'So happy, his heart simply stopped.'  Close on the smile, face-on.  The music cuts; a single petal settles on his
    nose; he does not blink again."""
    stage(sh, 'sunset', 9, 245)
    c, ez, band = perfect_set(sh)
    TS = 1.7
    lie_in(sh, ez, c, [(0, 'happy')])
    petal = T.box('lastpetal', (.05, .035, .004), (0, 0, -60), T.plain('petal', '#c8406a', .6))
    def land(t):
        hp = head_of(ez, .05); u = ease((t - 1.9) / 1.4)
        petal.location = (hp + Vector((-.2, .1, .75))).lerp(hp + Vector((0, .0, .3)), u); petal.rotation_euler = (0, u * .3, math.sin(t * 3) * (1 - u))
    sh.updates.append(land)
    def cam(t):
        hp = head_of(ez); d = K([(0, 2.35), (TS, 2.1), (sh.dur, 2.0)], t)
        return (hp + Vector((.02, .45, .88)) * d, hp + Vector((0, .04, 0)), 40, 0, hp + Vector((0, 0, .2)), .002 if t < TS else .0005)
    sh.camera(cam, fstop=2.4); sh.keylight(10, (1, .85, .65))


def s_played(sh):
    """'The band played.'  High over the band's shoulders: horns up, the open coffin and the mourners beyond."""
    stage(sh, 'sunset', 9, 245)
    c, ez, band = perfect_set(sh)
    lie_in(sh, ez, c, [(0, 'happy')])
    mourners(sh, 6, seed=5, face='sad')
    play_band(sh, band)
    sh.camera(cam_keys([(0, (6.3, 98.7, HZ + 2.6), (-.5, 95.9, HZ + .8), 28), (sh.dur, (5.8, 98.4, HZ + 2.5), (-.6, 95.8, HZ + .8), 30)], shake=.008), fstop=4)


def s_wept(sh):
    """'The undertaker wept.'  Close: the undertaker dabbing his streaming eyes with a white handkerchief."""
    stage(sh, 'sunset', 9, 245)
    c, ez, band = perfect_set(sh, with_people=False)
    lie_in(sh, ez, c, [(0, 'happy')])
    mort = toon(sh, 'MORT', MORT)
    a = stand(sh, mort, (-.95, 93.7), 40, '77_02', 3.0, face=[(0, 'sad')], look=lambda t: (0, 96, HZ + .5))
    def mod(t, s):
        f, sd = side_of(mort); hc = head_of(mort, -.3)
        s['handR'] = tuple(hc + f * .3 + sd * .1 + Vector((0, 0, .03 * math.sin(t * 10)))); return s
    override(a, mod)
    hk = T.box('hanky', (.15, .02, .15), (0, 0, 0), T.plain('hanky', '#f4f0e8', .8)); hold(sh, hk, mort, 'R', (0, 0, 0), rot=(.3, 0, .4))
    tear_streams(sh, [(mort, .0)], n=8)
    cu(sh, mort, angle=25, elev=3, size=(.8, .62), lens=55, fstop=2.0)


# ------------------------------------------------------------------ 27-30  the whole town, laughter, he didn't, three days
def town_crowd(sh, n=22, face='laugh', clips=('79_70', '80_44', '79_70', '77_02', '80_48'), arriving=False):
    out = []; rng = random.Random(9)
    for k in range(n):
        ring = 4.2 + (k % 3) * 1.25; a = math.radians(55 + k * (290 / n) + rng.uniform(-5, 5))
        x, y = math.cos(a) * ring * 1.15, 96 + math.sin(a) * ring
        if -1.8 < x < 1.8 and y > 96: x += 3.5 * (1 if x >= 0 else -1)
        ch = toon(sh, f'C{k}', TO.crowd_preset(400 + k) if k % 4 else widow(k))
        yaw = math.degrees(math.atan2(x, -(y - 96))) + 180
        if arriving and k % 2 == 0:
            walk(sh, ch, (x, y - 7, U.ground_z(x, y - 7) + 0), 180, '82_09' if k % 3 else '82_11', 1.0 + k * .2, face=[(0, face if isinstance(face, str) else face[k % len(face)])])
        else:
            stand(sh, ch, (x, y), yaw, clips[k % len(clips)], .8 + (k * .37) % 2.2, face=[(0, face if isinstance(face, str) else face[k % len(face)])], look=lambda t: (0, 96, HZ + .6))
        out.append(ch)
    return out


def s_town(sh):
    """'And the whole town finally showed up.'  Crane up and back from the coffin: the hill fills with townsfolk streaming
    through the gate, Dry Gulch behind them."""
    stage(sh, 'sunset', 9, 245)
    c, ez, band = perfect_set(sh)
    c.open(0.0)
    play_band(sh, band)
    town_crowd(sh, 22, face=['watch', 'chat', 'idle'], arriving=True)
    sh.camera(cam_keys([(0, (1.4, 99.0, HZ + 1.8), (0, 95.5, HZ + 1.0), 26), (sh.dur, (5.5, 105.5, HZ + 7.2), (0, 92.0, HZ + .6), 22)], roll=lambda t: K([(0, 0), (sh.dur, 3)], t), shake=.006), fstop=6)


def s_laugh(sh):
    """'To laugh. Because everyone knew Ezra would climb out any second.'  From inside the ring: sweep across the laughing,
    pointing faces, then settle on the closed coffin with the grinning crowd behind it, waiting."""
    stage(sh, 'sunset', 9, 245)
    c, ez, band = perfect_set(sh, wreaths=(3,))
    c.open(0.0)
    crowd = town_crowd(sh, 32, face='laugh')
    for a in sh.actors:
        if getattr(a, 'ch', None) in crowd: a.face = H.expr_track([(0, 'laugh'), (3.6, 'grin')])
    def cam(t):
        u = ease(t / sh.dur); ang = math.radians(175 + 115 * u); r = 3.0
        p = Vector((math.cos(ang) * r, 96 + math.sin(ang) * r, HZ + 1.75))
        out = Vector((math.cos(ang + .25) * 6.0, 96 + math.sin(ang + .25) * 6.0, HZ + 1.3))
        tg = out.lerp(Vector((0, 96, HZ + .7)), ease((t - 2.8) / 1.8))
        return (p, tg, 26, 0, tg, .008)
    sh.camera(cam, fstop=4)


def s_didnt(sh):
    """'He didn't.'  Silence.  Slow push on the closed velvet coffin framed by candles and wreaths; the crowd behind,
    soft, waiting."""
    stage(sh, 'sunset', 7, 245)
    c, ez, band = perfect_set(sh)
    c.open(0.0)
    town_crowd(sh, 22, face=['watch', 'confused', 'watch', 'bored'], clips=('77_02', '40_10'))
    tg = c.world((0, 1.0, .5))
    sh.camera(cam_keys([(0, (.05, 99.9, HZ + 1.85), tg + Vector((0, -.6, .35)), 30), (sh.dur, (.03, 99.2, HZ + 1.6), tg + Vector((0, -.5, .3)), 33)], shake=.003), fstop=3.2)


def s_days(sh):
    """'And nobody noticed for three days.'  Locked-off on the abandoned funeral: three days and nights race past, the
    crowd gone, the flowers wilting, the velvet coffin still sitting there."""
    stage(sh, 'day', 30, 160)
    c, ez, band = perfect_set(sh, with_people=False)
    c.open(0.0)
    sun = next((o for o in bpy.data.objects if o.type == 'LIGHT' and o.data.type == 'SUN'), None)
    e0 = sun.data.energy if sun else 3
    bgs = [n for n in bpy.context.scene.world.node_tree.nodes if n.type == 'BACKGROUND'] if bpy.context.scene.world and bpy.context.scene.world.use_nodes else []
    b0 = [n.inputs['Strength'].default_value for n in bgs]
    fls = [(o, o.location.copy()) for o in bpy.data.objects if o.name.startswith('fl') and ('_fl' in o.name or '_st' in o.name)]
    D = 2.9 / 3
    def cyc(t):
        ph = (t / D) % 1.0; day = max(0.0, math.sin(ph * math.tau)); amt = .08 + .92 * day
        if t > 2.9: amt = .35 + .3 * (1 - (t - 2.9) / .5)
        if sun: sun.data.energy = e0 * amt; sun.rotation_euler = (math.radians(30), 0, math.radians(90 + 360 * ph))
        for n, b in zip(bgs, b0): n.inputs['Strength'].default_value = b * (.12 + .88 * amt)
        w = ease(t / 3.0)
        for o, l0 in fls:
            if '_fl' in o.name: o.location = l0 + Vector((.12 * w, 0, -.3 * w))
            else: o.scale = (1, 1, 1 - .5 * w); o.location = l0 - Vector((0, 0, .11 * w)); o.rotation_euler = (0, .6 * w, 0)
    sh.updates.append(cyc)
    sh.camera(cam_keys([(0, (.5, 101.2, HZ + 2.3), (0, 95.6, HZ + .55), 30), (sh.dur, (.48, 101.0, HZ + 2.25), (0, 95.6, HZ + .55), 30)], shake=.0), fstop=6)
    sh.no_extras = True


SHOTS = {k[2:]: v for k, v in list(globals().items()) if k.startswith('s_') and callable(v)}

if __name__ == '__main__':
    F.main(SHOTS)
