"""DAGAR CLIPS characters (reference style): big round white head, thick ink outline, dot eyes, thin brows,
small coloured bean torso, long thin black stick limbs, small round hands and oval shoes.
Everything is posed procedurally each frame from tracks (see Char.apply)."""
import bpy, math, random
from mathutils import Vector, Matrix
from common import *
from lib import sphere, lathe, box, cyl, torus, coll

CHARS = []

EXPR = {   # mouth w, smile, open ; brow height, brow tilt (+ = angry inner-down), brow arch ; eye scale x, y, ; pupil 
    'deadpan':  dict(w=.07, smile=0.0,  op=0.0,  bh=0.0,  bt=0.0,  ba=0.0,  ex=1.0, ey=1.0),
    'smile':    dict(w=.10, smile=.035, op=0.0,  bh=.01,  bt=-.1,  ba=.2,   ex=1.0, ey=.9),
    'grin':     dict(w=.12, smile=.05,  op=.05,  bh=.015, bt=-.15, ba=.3,   ex=1.0, ey=.85),
    'shock':    dict(w=.045, smile=0.0, op=.085, bh=.075, bt=-.2,  ba=.5,   ex=1.25, ey=1.5),
    'scream':   dict(w=.075, smile=-.02, op=.13, bh=.07,  bt=-.35, ba=.4,   ex=1.2, ey=1.4),
    'worry':    dict(w=.07, smile=-.03, op=.01,  bh=.04,  bt=-.45, ba=.0,   ex=1.1, ey=1.2),
    'angry':    dict(w=.09, smile=-.04, op=.03,  bh=-.03, bt=.55,  ba=.0,   ex=1.0, ey=.8),
    'sad':      dict(w=.07, smile=-.04, op=0.0,  bh=.03,  bt=-.5,  ba=-.1,  ex=1.0, ey=.9),
    'smug':     dict(w=.09, smile=.02,  op=0.0,  bh=.0,   bt=.15,  ba=.2,   ex=1.0, ey=.55),
    'ohno':     dict(w=.08, smile=-.02, op=.05,  bh=.05,  bt=-.35, ba=.1,   ex=1.2, ey=1.3),
}
PKEYS = ('w', 'smile', 'op', 'bh', 'bt', 'ba', 'ex', 'ey')

def expr_track(seq):
    """seq: [(t, 'name')] -> function t -> dict of params (smooth blends, quick 0.12s transitions)."""
    tr = {k: K([(max(0, t - .12), None) if False else (t, EXPR[n][k]) for t, n in seq]) for k in PKEYS}
    return lambda t: {k: tr[k](t) for k in PKEYS}

def two_bone(p0, tgt, l1, l2, pole):
    d = tgt - p0; dist = max(1e-4, min(d.length, (l1 + l2) * .995)); dv = d.normalized()
    a = (l1 * l1 - l2 * l2 + dist * dist) / (2 * dist); h = math.sqrt(max(0, l1 * l1 - a * a))
    pv = pole - dv * pole.dot(dv)
    pv = pv.normalized() if pv.length > 1e-5 else Vector((0, -1, 0))
    return p0 + dv * a + pv * h, p0 + dv * dist

def _curve(name, n, r, m, parent, cyc=False, fill=False):
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = r; cu.bevel_resolution = 3; cu.use_fill_caps = True; cu.resolution_u = 8
    sp = cu.splines.new('POLY' if cyc else 'NURBS'); sp.points.add(n - 1)
    if not cyc: sp.order_u = 3; sp.use_endpoint_u = True
    else: sp.use_cyclic_u = True
    o = bpy.data.objects.new(name, cu); coll('Characters').objects.link(o); cu.materials.append(m); o.parent = parent
    return o

def _link(o, parent):
    for c in list(o.users_collection): c.objects.unlink(o)
    coll('Characters').objects.link(o); o.parent = parent; return o

class Char:
    def __init__(self, cid, name, skin='#f6f3ee', body='#3b6fb6', hair=None, hat=None, glasses=False, stache=None, scale=1.0, pants='#1a1a1e', eyes=1.0, hair_col='#3a2412', head_r=.27):
        self.cid, self.name, self.s = cid, name, scale
        self.hr = hr = head_r; self.hx, self.hy, self.hz = hr * 1.04, hr * .96, hr * .98
        self.L = getattr(self, 'L0', .56); self.TL = getattr(self, 'TL0', .34); self.rw = getattr(self, 'RW0', .15)
        self.root = bpy.data.objects.new(f'{cid}_{name}', None); coll('Characters').objects.link(self.root)
        self.torso = bpy.data.objects.new(cid + '_torso', None); coll('Characters').objects.link(self.torso); self.torso.parent = self.root
        self.torso.location = (0, 0, self.L)
        bm = solid(body, .75, sss=.03)
        prof = [(0, 0)]
        for i in range(1, 6): a = i / 6 * math.pi / 2; prof.append((self.rw * .92 * math.sin(a), .04 * (1 - math.cos(a))))
        for i in range(1, 6): t = i / 6; prof.append((self.rw * (.92 + .1 * math.sin(math.pi * t * .9)), .04 + (self.TL - .1) * t))
        for i in range(0, 6): a = i / 6 * math.pi / 2; prof.append((self.rw * .82 * math.cos(a) + .01, self.TL - .06 + .06 * math.sin(a)))
        prof.append((0, self.TL))
        self.body = lathe(cid + '_body', prof, seg=40, m=bm, sy=.78); _link(self.body, self.torso); outline(self.body, .0085 * 1.0)
        # pants cuff / belt band
        self.belt = torus(cid + '_belt', self.rw * .93, .018, (0, 0, .045), solid(pants, .7), seg=40, mseg=8); self.belt.scale = (1, .78, 1); _link(self.belt, self.torso)
        # head
        self.head = bpy.data.objects.new(cid + '_head', None); coll('Characters').objects.link(self.head); self.head.parent = self.torso
        self.head.location = (0, 0, self.TL + .035)
        hm = solid(skin, .5, sss=.05)
        self.skull = sphere(cid + '_skull', 1.0, (0, 0, self.hz * .86), hm, seg=64, rings=40, scale=(self.hx, self.hy, self.hz)); _link(self.skull, self.head)
        outline(self.skull, .0125)
        self.cz = self.hz * .86     # skull centre height in head space
        k = solid('#0c0b0e', .35)
        self.eyes = []
        for sd in (-1, 1):
            e = sphere(cid + f'_eye{sd}', .027 * eyes, (0, 0, 0), k, seg=20, rings=12, scale=(1, .35, 1.12)); _link(e, self.head); self.eyes.append(e)
        # eye whites for 'shock' (ring) are skipped: reference uses solid dots
        self.brows = [_curve(cid + f'_brow{i}', 3, .0085, ink_mat(), self.head) for i in (0, 1)]
        for b in self.brows: coll('Characters').objects.unlink(b) if False else None
        self.mouth = _curve(cid + '_mouth', 16, .0072, ink_mat(), self.head, cyc=True)
        me = bpy.data.meshes.new(cid + '_mfill'); me.from_pydata([(0, 0, 0)] * 45, [], [(r * 9 + i, r * 9 + i + 1, (r + 1) * 9 + i + 1, (r + 1) * 9 + i) for r in range(4) for i in range(8)])
        self.mfill = bpy.data.objects.new(cid + '_mfill', me); coll('Characters').objects.link(self.mfill); self.mfill.parent = self.head; me.materials.append(ink_mat())
        self.extras(hair, hat, glasses, stache, hair_col, pants)
        # limbs
        self.legs, self.shoes, self.arms, self.hands = {}, {}, {}, {}
        sk = solid(skin, .5, sss=.05); shoe = solid('#15131a', .4, coat=.3)
        for sd in ('L', 'R'):
            self.legs[sd] = _curve(cid + '_leg' + sd, 3, .0125, ink_mat(), self.root)
            self.arms[sd] = _curve(cid + '_arm' + sd, 3, .0115, ink_mat(), self.root)
            sh = sphere(cid + '_shoe' + sd, .065, (0, 0, 0), shoe, seg=24, rings=14, scale=(.85, 1.6, .62)); _link(sh, self.root); self.shoes[sd] = sh; outline(sh, .006)
            hd = sphere(cid + '_hand' + sd, .042, (0, 0, 0), sk, seg=24, rings=14); _link(hd, self.root); self.hands[sd] = hd; outline(hd, .006)
        self.root.scale = (scale,) * 3
        self.fn = lambda t: {}
        self.props = []
        for o in self.eyes + self.brows + [self.mouth, self.mfill]:
            for cc in list(o.users_collection): cc.objects.unlink(o)
            coll('Face').objects.link(o)
        CHARS.append(self)
        self.blinks = sorted(random.Random(hash(cid) % 9999).uniform(.5, 12) for _ in range(5))

    # ---- accessories -----------------------------------------------------------------------
    def extras(self, hair, hat, glasses, stache, hair_col, pants):
        hz, cz, cid = self.hz, self.cz, self.cid
        top = cz + hz
        hm = solid(hair_col, .8)
        if hair == 'spiky':
            for i, a in enumerate(range(-60, 61, 30)):
                c = cyl(f'{cid}_sp{i}', .045, .13, (math.sin(math.radians(a)) * self.hx * .55, 0, top - .005 + (0.02 if a == 0 else 0)), hm, seg=10, r2=0, rot=(0, math.radians(a) * .6, 0)); _link(c, self.head)
        elif hair == 'tuft':
            for i, a in enumerate((-18, 0, 20)):
                c = cyl(f'{cid}_tf{i}', .018, .14, (a * .0035, 0, top + .03), hm, seg=8, r2=.0, rot=(0, math.radians(a) * 1.6, 0)); _link(c, self.head)
        elif hair == 'cap':
            h = sphere(cid + '_hair', 1.0, (0, .008, cz + hz * .22), hm, seg=48, rings=24, scale=(self.hx * 1.025, self.hy * 1.02, hz * .84)); _link(h, self.head)
            # keep only the upper part
            for v in h.data.vertices:
                if v.co.z < -.05: v.co.z = -.05
            outline(h, .01)
        if hat == 'beanie':
            b = sphere(cid + '_beanie', 1.0, (0, .006, cz + hz * .25), solid('#c8372d', .9), seg=48, rings=24, scale=(self.hx * 1.04, self.hy * 1.04, hz * .8)); _link(b, self.head)
            for v in b.data.vertices:
                if v.co.z < -.05: v.co.z = -.05
            outline(b, .011); smooth(b)
            c = torus(cid + '_cuff', self.hx * 1.0, .03, (0, .005, cz + hz * .2), solid('#a22a22', .95), seg=48, mseg=10); c.scale = (1, self.hy / self.hx, 1); _link(c, self.head)
            pm = sphere(cid + '_pom', .05, (0, 0, top + .06), solid('#e8e0d0', .95), seg=16, rings=10); _link(pm, self.head)
        if glasses:
            gm = ink_mat()
            for sd in (-1, 1):
                t = torus(cid + f'_gl{sd}', .062, .006, (sd * .1, -self.hy * .93, cz + .035), gm, rot=(math.pi / 2, 0, 0), seg=32, mseg=8); _link(t, self.head)
            bridge = box(cid + '_br', (.05, .008, .008), (0, -self.hy * .96, cz + .045), gm); _link(bridge, self.head)
        if stache:
            sm = solid(stache, .85)
            for sd in (-1, 1):
                s = sphere(cid + f'_st{sd}', .05, (sd * .045, -self.hy * .95, cz - .07), sm, seg=16, rings=10, scale=(1.5, .5, .65), rot=(0, sd * .35, 0)); _link(s, self.head)

    # ---- per-frame pose -----------------------------------------------------------------------
    def surf_y(self, x, z):
        u = 1 - (x / self.hx) ** 2 - ((z - self.cz) / self.hz) ** 2
        return -self.hy * math.sqrt(max(0.02, u))

    def face(self, p, t):
        cz = self.cz
        for e, sd in zip(self.eyes, (-1, 1)):
            x = sd * .098; z = cz + .035
            bl = 1.0
            for b0 in self.blinks:
                if b0 <= t < b0 + .14: bl = max(.08, abs((t - b0) - .07) / .07)
            e.location = (x, self.surf_y(x, z) + .004, z); e.scale = (p['ex'], 1, p['ey'] * bl * (1 if p.get('look') is None else 1))
        for br, sd in zip(self.brows, (-1, 1)):
            sp = br.data.splines[0]; base_z = cz + .125 + p['bh']
            for i, u in enumerate((-1, 0, 1)):     # u=-1 inner, 1 outer (for each side)
                x = sd * (.098 + .052 * u)
                z = base_z + u * p['bt'] * .03 + (1 - u * u) * p['ba'] * .018
                sp.points[i].co = (x, self.surf_y(x, z) - .002, z, 1)
        mo = self.mouth.data.splines[0]; w, sm, op = p['w'], p['smile'], p['op']; n = 9; z0 = cz - .095
        for i in range(n):
            x = -w + 2 * w * i / (n - 1); q = (x / w) ** 2
            ub = op * .3 * (1 - q) ** .5; zu = z0 + sm * q + ub; mo.points[i].co = (x, self.surf_y(x, zu) - .002, zu, 1)
            zl = z0 + sm * q - op * .7 * (1 - q) ** .5
            j = 2 * n - 2 - i
            if 0 < i < n - 1: mo.points[j].co = (x, self.surf_y(x, zl) - .002, zl, 1)
        vs = self.mfill.data.vertices
        for i in range(n):
            x = -w + 2 * w * i / (n - 1); q = (x / w) ** 2; zu = z0 + sm * q + op * .3 * (1 - q) ** .5; zl = z0 + sm * q - op * .7 * (1 - q) ** .5
            for r in range(5):
                z = zu + (zl - zu) * r / 4; vs[r * 9 + i].co = (x, self.surf_y(x, z) - .0015, z)

    def apply(self, t):
        s = self.fn(t); sc = self.s
        loc = Vector(s.get('loc', (0, 0, 0))); yaw = s.get('yaw', 0.0)
        M = Matrix.Translation(loc) @ Matrix.Rotation(math.radians(yaw), 4, 'Z')
        self.root.location = loc; self.root.rotation_euler = (0, 0, math.radians(yaw))
        Mi = (M @ Matrix.Scale(sc, 4)).inverted()
        lean = math.radians(s.get('lean', 0)); roll = math.radians(s.get('roll', 0))
        self.torso.rotation_euler = (lean, roll, 0)
        hy, hp, hr_ = s.get('head', (0, 0, 0)); self.head.rotation_euler = (math.radians(hp), math.radians(hr_), math.radians(hy))
        self.torso.location = (0, 0, self.L + s.get('crouch', 0) * -.1)
        R = Matrix.Rotation(lean, 3, 'X') @ Matrix.Rotation(roll, 3, 'Y')
        hip0 = Vector((0, 0, self.L + s.get('crouch', 0) * -.1))
        # arms
        for sd in ('L', 'R'):
            side = -1 if sd == 'L' else 1
            sh = hip0 + R @ Vector((side * self.rw * .98, 0, self.TL * .84))
            tg = s.get('hand' + sd)
            if tg is None: tg = M @ Vector((side * .24, -.03, self.L + self.TL * .2 + .02))
            tgl = Mi @ Vector(tg) if not isinstance(tg, Vector) else Mi @ tg
            el, hd = two_bone(sh, tgl, .31, .31, Vector((side * .5, .8, -.4)))
            pts = self.arms[sd].data.splines[0].points
            for pnt, v in zip(pts, (sh, el, hd)): pnt.co = (v.x, v.y, v.z, 1)
            self.hands[sd].location = hd
        for sd in ('L', 'R'):
            side = -1 if sd == 'L' else 1
            hip = Vector((side * self.rw * .5, 0, self.L - .01 + s.get('crouch', 0) * -.1))
            tg = s.get('foot' + sd)
            if tg is None: tg = M @ Vector((side * .1, 0, .04))
            tgl = Mi @ Vector(tg)
            kn, ft = two_bone(hip, tgl + Vector((0, 0, .03)), .29, .29, Vector((0, -1, .1)))
            pts = self.legs[sd].data.splines[0].points
            for pnt, v in zip(pts, (hip, kn, ft)): pnt.co = (v.x, v.y, v.z, 1)
            self.shoes[sd].location = tgl + Vector((0, -.045, 0)); self.shoes[sd].rotation_euler = (0, 0, math.radians(s.get('shoeyaw', 0)))
        self.face(s.get('face', EXPR['deadpan']), t)

def on_frame(scene, *a):
    t = (scene.frame_current - 1) / scene.render.fps
    for c in CHARS: c.apply(t + SHOT_T0[0])
SHOT_T0 = [0.0]

def install():
    bpy.app.handlers.frame_change_pre[:] = [h for h in bpy.app.handlers.frame_change_pre if h.__name__ != 'on_frame'] + [on_frame]
