"""Realistic-proportion stylized 3D humans with physics-driven movement:
- standing balance = damped inverted pendulum driven by the deck's real acceleration (knees flex, torso leans, arms brace)
- walking = foot-planted gait IK with weight shift, counter-swing of arms/torso
- face rig: eyes with lids, brows, jaw/mouth, expressions
- cloth: coat skirt / cape / flag use Blender's Cloth solver (stepped sequentially)."""
import bpy, math, numpy as np
from mathutils import Vector, Matrix
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import lib
from lib import lin, mat, coll, sphere, lathe
from common_p import *

HUMANS = []
LEG = (.45, .44); ARM = (.31, .29)
HIP_H = .9; TORSO = .58

def cone(name, r1, r2, mt, seg=20, parent=None):
    bm_prof = [(0, 0), (r1, 0), (r2, 1.0), (0, 1.0)]
    o = lathe(name, bm_prof, seg=seg, m=mt, c=coll('Humans')); return o

def place_seg(o, a, b):
    d = b - a; L = max(1e-4, d.length)
    o.location = a; o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = d.to_track_quat('Z', 'Y'); o.scale = (1, 1, L)

def ik2(p0, tgt, l1, l2, pole):
    d = tgt - p0; dist = max(1e-4, min(d.length, (l1 + l2) * .999)); dv = d.normalized()
    a = (l1 * l1 - l2 * l2 + dist * dist) / (2 * dist); h = math.sqrt(max(0, l1 * l1 - a * a))
    pv = pole - dv * pole.dot(dv); pv = pv.normalized() if pv.length > 1e-5 else Vector((0, -1, 0))
    return p0 + dv * a + pv * h, p0 + dv * dist

EXPR = {   # eyelid open (0-1), brow raise, brow tilt (+ = angry), mouth width, smile, open, gaze-lock
 'neutral': dict(lid=.85, br=0, bt=0, mw=.036, sm=0, op=0),
 'angry':   dict(lid=.6, br=-.012, bt=.9, mw=.038, sm=-.012, op=.01),
 'furious': dict(lid=.55, br=-.015, bt=1.0, mw=.045, sm=-.02, op=.035),
 'confused':dict(lid=.9, br=.012, bt=-.3, mw=.03, sm=-.006, op=.004),
 'terror':  dict(lid=1.15, br=.03, bt=-.7, mw=.04, sm=-.015, op=.05),
 'smirk':   dict(lid=.7, br=.006, bt=.2, mw=.04, sm=.016, op=0),
 'smile':   dict(lid=.8, br=.006, bt=-.1, mw=.045, sm=.022, op=.006),
 'shout':   dict(lid=.7, br=-.005, bt=.8, mw=.04, sm=-.005, op=.05),
 'strain':  dict(lid=.5, br=-.008, bt=.5, mw=.04, sm=-.02, op=.012),
 'surprise':dict(lid=1.1, br=.025, bt=-.4, mw=.026, sm=0, op=.03),
}
EK = ('lid', 'br', 'bt', 'mw', 'sm', 'op')
def expr_track(seq):
    tr = {k: K([(t, EXPR[n][k]) for t, n in seq]) for k in EK}
    return lambda t: {k: tr[k](t) for k in EK}

class Human:
    def __init__(self, cid, name, skin='#c99876', shirt='#d8d0bc', vest=None, coat=None, trousers='#3a2f28', boots='#2a1c14', hair='#2a1a10',
                 beard=None, hat=None, bandana=None, scale=1.0, height=1.0, build=1.0, eye='#4a6a8a'):
        self.cid, self.name = cid, name; s = scale * height; self.s = s; self.b = build
        self.root = bpy.data.objects.new(f'{cid}_{name}', None); coll('Humans').objects.link(self.root)
        sk = mat('skin' + cid, skin, rough=.55, sss=.25); self.skin_c = skin
        sh = mat('shirt' + cid, shirt, rough=.9); tr = mat('trou' + cid, trousers, rough=.85); bt = mat('boot' + cid, boots, rough=.5, coat=.2)
        top = mat('top' + cid, coat or vest or shirt, rough=.85)
        self.segs = {}
        def S(n, r1, r2, m): o = cone(f'{cid}_{n}', r1 * build, r2 * build, m); self.segs[n] = o; o.parent = self.root; return o
        def J(n, r, m, sc=(1, 1, 1)): o = sphere(f'{cid}_{n}', r * build, (0, 0, 0), m, seg=20, rings=12, scale=sc, c=coll('Humans')); self.segs[n] = o; o.parent = self.root; return o
        sleeve = top if coat else sh
        for sd in 'LR':
            S('thigh' + sd, .092, .07, tr); S('shin' + sd, .07, .05, tr); J('knee' + sd, .07, tr)
            S('uarm' + sd, .056, .046, sleeve); S('farm' + sd, .046, .036, sk if not coat else sleeve); J('elbow' + sd, .048, sleeve if coat else sh)
            J('hand' + sd, .045, sk, (.8, 1.1, .6)); J('shoulder' + sd, .062, sleeve)
            f = J('boot' + sd, .08, bt, (.8, 2.0, 1.0)); f.parent = self.root
            S('cuff' + sd, .05, .05, sh if coat else sk)
        # torso (pelvis + chest) as one lathe, built in root space and posed by matrix
        w = .205 * build
        prof = [(0, 0), (w * .9, .0), (w * 1.0, .1), (w * .88, .24), (w * 1.08, .4), (w * 1.16, .49), (w * .9, .56), (.06, .62), (0, .62)]
        self.torso = lathe(cid + '_torso', prof, seg=28, m=top, c=coll('Humans'), sy=.7); self.torso.parent = self.root
        self.belt = lathe(cid + '_belt', [(w * .9, .02), (w * .92, .02), (w * .92, .08), (w * .9, .08)], seg=28, m=mat('belt' + cid, '#1d140e', rough=.5), c=coll('Humans'), sy=.62); self.belt.parent = self.torso
        self.neck = cone(cid + '_neck', .045, .04, sk); self.neck.parent = self.root
        # head
        self.rx, self.ry, self.rz = .092 * build, .105 * build, .118 * build
        self.head = bpy.data.objects.new(cid + '_head', None); coll('Humans').objects.link(self.head); self.head.parent = self.root
        sk2 = mat('skinh' + cid, skin, rough=.5, sss=.3)
        self.skull = sphere(cid + '_skull', 1, (0, 0, self.rz), sk2, seg=48, rings=32, scale=(self.rx, self.ry, self.rz), c=coll('Humans')); self.skull.parent = self.head
        self.jaw = sphere(cid + '_jaw', 1, (0, -.012, self.rz * .3), sk2, seg=32, rings=20, scale=(self.rx * .86, self.ry * .86, self.rz * .52), c=coll('Humans')); self.jaw.parent = self.head
        nose = sphere(cid + '_nose', .022, (0, -self.ry * .95, self.rz * .92), sk2, seg=16, rings=10, scale=(.8, 1.3, 1.5), c=coll('Humans')); nose.parent = self.head
        for sd in (-1, 1):
            e = sphere(cid + f'_ear{sd}', .024, (sd * self.rx * .98, .005, self.rz * 1.0), sk2, seg=12, rings=8, scale=(.4, .8, 1.2), c=coll('Humans')); e.parent = self.head
        self.eyes = []; self.lids = []; self.brows = []
        wm = mat('eyew' + cid, '#f1ece4', rough=.25); im = mat('iris' + cid, eye, rough=.2); pm = mat('pupil', '#060606', rough=.1)
        self.ez = self.rz * 1.06; self.ex = self.rx * .47
        for sd in (-1, 1):
            c = (sd * self.ex, -self.ry * .78, self.ez)
            g = sphere(cid + f'_eye{sd}', .02, c, wm, seg=20, rings=12, c=coll('Humans')); g.parent = self.head
            ir = sphere(cid + f'_iris{sd}', .0115, (c[0], c[1] - .0178, c[2]), im, seg=16, rings=8, scale=(1, .35, 1), c=coll('Humans')); ir.parent = self.head
            pu = sphere(cid + f'_pup{sd}', .0056, (c[0], c[1] - .0212, c[2]), pm, seg=12, rings=6, scale=(1, .3, 1), c=coll('Humans')); pu.parent = self.head
            self.eyes.append((g, ir, pu, c))
            br = sphere(cid + f'_brow{sd}', .02, (c[0], c[1] - .008, c[2] + .028), mat('brow' + cid, hair, rough=.9), seg=12, rings=8, scale=(1.5, .5, .38), c=coll('Humans')); br.parent = self.head
            self.brows.append((br, sd))
        self.mouth = bpy.data.curves.new(cid + '_mouth', 'CURVE'); self.mouth.dimensions = '3D'; self.mouth.bevel_depth = .0035; self.mouth.resolution_u = 4
        sp = self.mouth.splines.new('POLY'); sp.points.add(15); sp.use_cyclic_u = True
        self.mo = bpy.data.objects.new(cid + '_mouth', self.mouth); coll('Humans').objects.link(self.mo); self.mo.parent = self.head
        self.mouth.materials.append(mat('lip' + cid, '#7a3f3a', rough=.5))
        me = bpy.data.meshes.new(cid + '_mfill'); me.from_pydata([(0, 0, 0)] * 45, [], [(r * 9 + i, r * 9 + i + 1, (r + 1) * 9 + i + 1, (r + 1) * 9 + i) for r in range(4) for i in range(8)])
        self.mfill = bpy.data.objects.new(cid + '_mfill', me); coll('Humans').objects.link(self.mfill); self.mfill.parent = self.head; me.materials.append(mat('mouthin', '#1a0808', rough=.8))
        # hair / beard / hat
        hm = mat('hair' + cid, hair, rough=.9)
        if hat != 'tricorn':
            hr = sphere(cid + '_hair', 1, (0, .012, self.rz * 1.12), hm, seg=32, rings=16, scale=(self.rx * 1.06, self.ry * 1.04, self.rz * .95), c=coll('Humans')); hr.parent = self.head
            for v in hr.data.vertices:
                if v.co.z < -.02: v.co.z = -.02 + (v.co.z + .02) * .0
        if beard:
            bm = mat('beard' + cid, beard, rough=.95)
            for i, a in enumerate(np.linspace(-1.35, 1.35, 11)):
                z = self.rz * (.22 + .16 * abs(a) / 1.35) ; r = .02 + .008 * (1 - abs(a) / 1.35)
                b = sphere(cid + f'_beard{i}', r, (math.sin(a) * self.rx * .86, -math.cos(a) * self.ry * .84, z), bm, seg=14, rings=8, scale=(1, .9, 1.4), c=coll('Humans')); b.parent = self.head
            for sd in (-1, 1):
                sb = sphere(cid + f'_burn{sd}', .02, (sd * self.rx * .9, -self.ry * .35, self.rz * .6), bm, seg=12, rings=8, scale=(.5, 1.0, 2.0), c=coll('Humans')); sb.parent = self.head
            b = sphere(cid + '_chinbeard', .03, (0, -self.ry * .72, self.rz * .1), bm, seg=14, rings=8, scale=(1, .9, 1.8), c=coll('Humans')); b.parent = self.head
            mu = sphere(cid + '_stache', .026, (0, -self.ry * .97, self.rz * .68), bm, seg=14, rings=8, scale=(1.6, .5, .45), c=coll('Humans')); mu.parent = self.head
        if hat == 'tricorn':
            hc = mat('hat' + cid, '#16161c', rough=.7); gold = mat('gold', '#c9a23a', rough=.3, metal=1.0)
            cr = lathe(cid + '_crown', [(0, 0), (.1, 0), (.095, .09), (0, .095)], seg=24, m=hc, c=coll('Humans')); cr.location = (0, 0, self.rz * 1.35); cr.parent = self.head
            for i, a in enumerate((0, 2.09, 4.19)):
                br = sphere(cid + f'_brim{i}', 1, (math.sin(a) * .09, -math.cos(a) * .09, self.rz * 1.45), hc, seg=16, rings=8, scale=(.12, .12, .018), c=coll('Humans')); br.parent = self.head
            tp = sphere(cid + '_hatrim', 1, (0, 0, self.rz * 1.4), hc, seg=32, rings=8, scale=(.17, .17, .014), c=coll('Humans')); tp.parent = self.head
            tp2 = sphere(cid + '_hatband', .1, (0, 0, self.rz * 1.43), gold, seg=32, rings=4, scale=(1, 1, .04), c=coll('Humans')); tp2.parent = self.head
        if bandana:
            bn = mat('bandana' + cid, bandana, rough=.85)
            bb = sphere(cid + '_bandana', 1, (0, .005, self.rz * 1.32), bn, seg=32, rings=12, scale=(self.rx * 1.08, self.ry * 1.08, self.rz * .5), c=coll('Humans')); bb.parent = self.head
            for v in bb.data.vertices:
                if v.co.z < -.1: v.co.z = -.1
        for ob in list(coll('Humans').objects):
            if ob.parent is None or True: pass
        self.root.scale = (s,) * 3
        self.fn = lambda t: {}
        self.st = {}
        HUMANS.append(self)

    # --- surface helper for face features (head local) ---
    def sy(self, x, z):
        u = 1 - (x / self.rx) ** 2 - ((z - self.rz) / self.rz) ** 2
        return -self.ry * math.sqrt(max(.02, u))

    def face(self, e, t, gaze=None):
        ez = self.ez
        bl = 1.0
        for b0 in (1.3, 4.1, 7.7, 11.2, 15.9, 19.4, 23.7, 28.1, 33.3, 38.9, 44.4, 50.1, 56.2, 61.8, 67.5, 72.6):
            if b0 <= t < b0 + .16: bl = abs((t - b0) - .08) / .08
        lid = e['lid'] * (.1 + .9 * bl)
        for (g, ir, pu, c) in self.eyes:
            f = max(.08, min(1.15, lid)); zc = c[2]
            for o in (g, ir, pu): o.scale = (o.scale[0], o.scale[1], f if o is g else f); o.location.z = zc + (1 - f) * .006 * 0
            g.scale = (1, 1, f); ir.scale = (1, .35, f); pu.scale = (1, .3, f)
        for (br, sd) in self.brows:
            c = (sd * self.ex, 0, ez); x = c[0]; z = ez + .029 + e['br']
            br.location = (x, self.sy(x, z) - .004, z); br.rotation_euler = (0, math.radians(-sd * e['bt'] * 26), 0)
        mo = self.mouth.splines[0]; w, sm, op = e['mw'], e['sm'], e['op']; n = 9; z0 = self.rz * .5
        for i in range(n):
            x = -w + 2 * w * i / (n - 1); q = (x / w) ** 2
            zu = z0 + sm * q + op * .25 * (1 - q) ** .5; mo.points[i].co = (x, self.sy(x, zu) - .0015, zu, 1)
            if 0 < i < n - 1:
                zl = z0 + sm * q - op * .75 * (1 - q) ** .5; mo.points[2 * n - 2 - i].co = (x, self.sy(x, zl) - .0015, zl, 1)
        vs = self.mfill.data.vertices
        for i in range(n):
            x = -w + 2 * w * i / (n - 1); q = (x / w) ** 2; zu = z0 + sm * q + op * .25 * (1 - q) ** .5; zl = z0 + sm * q - op * .75 * (1 - q) ** .5
            for r in range(5):
                z = zu + (zl - zu) * r / 4; vs[r * 9 + i].co = (x, self.sy(x, z) - .001, z)
        self.jaw.location = (0, -.012, self.rz * .3 - op * .45)

    def apply(self, t):
        s = self.fn(t); sc = self.s; b = self.b
        loc = Vector(s.get('loc', (0, 0, 0))); yaw = math.radians(s.get('yaw', 0)); par = s.get('parent')
        R = Matrix.Rotation(yaw, 3, 'Z')
        self.root.location = loc; self.root.rotation_euler = (0, 0, yaw)
        # all joints in root-local unscaled coords
        lean = s.get('lean', (0, 0)); crouch = s.get('crouch', 0.0)       # lean: (forward rad, side rad)
        pelvis = Vector((s.get('sway', 0.0), 0, HIP_H - crouch)) + Vector((0, 0, s.get('bob', 0.0)))
        Rt = Matrix.Rotation(lean[0], 3, 'X') @ Matrix.Rotation(lean[1], 3, 'Y') @ Matrix.Rotation(s.get('twist', 0.0), 3, 'Z')
        chest = pelvis + Rt @ Vector((0, 0, TORSO * .98))
        self.torso.location = pelvis; self.torso.rotation_mode = 'XYZ'; self.torso.rotation_euler = Rt.to_euler(); self.torso.parent = self.root
        neck0 = pelvis + Rt @ Vector((0, 0, TORSO * .93)); head0 = neck0 + Rt @ Vector((0, .0, .1))
        hy, hp, hr = s.get('head', (0, 0, 0))
        Rh = Rt @ Matrix.Rotation(math.radians(hy), 3, 'Z') @ Matrix.Rotation(math.radians(hp), 3, 'X') @ Matrix.Rotation(math.radians(hr), 3, 'Y')
        self.head.location = head0 - Rh @ Vector((0, 0, .0)); self.head.rotation_mode = 'XYZ'; self.head.rotation_euler = Rh.to_euler()
        place_seg(self.neck, neck0, head0 + Rh @ Vector((0, 0, .02)))
        wr = lambda p: Vector(p)
        # legs
        for sd, sx in (('L', -1), ('R', 1)):
            hip = pelvis + Rt @ Vector((sx * .085 * b, 0, -.02))
            ft = Vector(s.get('foot' + sd, (sx * .11 * b, 0, .0)))
            ft_ank = ft + Vector((0, 0, .075))
            kn, an = ik2(hip, ft_ank, LEG[0], LEG[1], Vector((0, -1, .15)))
            place_seg(self.segs['thigh' + sd], hip, kn); place_seg(self.segs['shin' + sd], kn, an)
            self.segs['knee' + sd].location = kn; self.segs['boot' + sd].location = ft + Vector((0, -.045, .062)); self.segs['boot' + sd].rotation_euler = (0, 0, math.radians(s.get('footyaw' + sd, 0)))
        # arms
        for sd, sx in (('L', -1), ('R', 1)):
            sho = chest + Rt @ Vector((sx * .205 * b, 0, -.04))
            hd = s.get('hand' + sd)
            if hd is None: hd = sho + Rt @ Vector((sx * .06, -.06, -.52))
            hd = Vector(hd)
            el, hh = ik2(sho, hd, ARM[0], ARM[1], Rt @ Vector((sx * .5, .8, -.3)) if s.get('elbowpole' + sd) is None else Vector(s['elbowpole' + sd]))
            place_seg(self.segs['uarm' + sd], sho, el); place_seg(self.segs['farm' + sd], el, hh)
            self.segs['elbow' + sd].location = el; self.segs['hand' + sd].location = hh + (hh - el).normalized() * .03; self.segs['shoulder' + sd].location = sho
            self.segs['cuff' + sd].location = hh - (hh - el).normalized() * .07; place_seg(self.segs['cuff' + sd], hh - (hh - el).normalized() * .075, hh - (hh - el).normalized() * .05)
        self.face(s.get('face', EXPR['neutral']), t)
        self.last = dict(pelvis=pelvis, chest=chest, head=head0)

def on_frame(scene, *a):
    t = (scene.frame_current - 1) / scene.render.fps + T0[0]
    for h in HUMANS: h.apply(t)
def install():
    bpy.app.handlers.frame_change_pre[:] = [f for f in bpy.app.handlers.frame_change_pre if f.__name__ != 'on_frame'] + [on_frame]

# ----------------------------------------------------------- physics-driven acting helpers
class Balance:
    """Damped inverted-pendulum balance of a standing person on a moving deck.
    acc(t): deck acceleration in the person's frame (forward, side, up) m/s^2 ; tilt(t): deck (pitch, roll) rad.
    Integrates the lean angles with semi-implicit Euler at 240 Hz from t0 (deterministic)."""
    def __init__(self, accfn, tiltfn, t0=0.0, t1=80.0, dt=1 / 240., wn=5.5, zeta=.55, h=1.0):
        self.ts = []; th = np.zeros(2); w = np.zeros(2); out = []; up = []
        ay = 0.0; vy = 0.0; z = 0.0
        t = t0
        while t < t1:
            a = accfn(t); pt = tiltfn(t)
            # lean angle response: th'' = -wn^2 (th - target) - 2 zeta wn th' - a/h   (target: align with perceived "up", i.e. partly follow deck tilt)
            tgt = np.array([-pt[0] * .35, -pt[1] * .35])
            acc = -wn * wn * (th - tgt) - 2 * zeta * wn * w - np.array([a[0], a[1]]) / (9.81 * h) * 9.0
            w += acc * dt; th += w * dt
            # vertical: knee flex (spring) driven by vertical accel
            az = a[2]; zacc = -45.0 * z - 9.0 * vy - az * .35
            vy += zacc * dt; z += vy * dt
            out.append((th[0], th[1], z)); t += dt
        self.out = np.array(out); self.t0 = t0; self.dt = dt
    def at(self, t):
        i = int(max(0, min(len(self.out) - 1, (t - self.t0) / self.dt))); return self.out[i]
