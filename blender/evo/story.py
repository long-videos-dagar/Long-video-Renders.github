"""FROM DINOSAURS TO HUMANS - shot builders (DAGAR CLIPS, 16:9).
Real worlds (terra/worlds), real animated creatures (Sketchfab CC-BY/CC0 GLBs), ink-toon classroom characters with
audio-driven lip sync.
    python3 story.py -- still <shot> out.png [t]
    python3 story.py -- frames <shot> <f0> <f1> <outdir>"""
import os, sys, json, math, random, importlib.util
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
for d in (HERE, os.path.join(ROOT, 'gta'), os.path.join(ROOT, 'zombie'), os.path.join(ROOT, 'west')): sys.path.insert(0, d)
import film as F
_spec = importlib.util.spec_from_file_location('zstory', os.path.join(ROOT, 'zombie', 'story.py')); Z = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(Z)
F.CFG = json.load(open(os.path.join(HERE, 'shots.json')))
from film import bpy, Vector, Matrix, T, TO, ease, K, head_of, facing
import inkchar as H
import terra as TR, worlds as W, creatures as CR

H.EXPR['sleep'] = dict(H.EXPR['bored'], ring=0.0, arc=.8, lid=0.0, pup=.5, w=.05, op=.03, smile=.005, bh=-.015, bt=0.0)
stand, walk, override, side_of, hold, cam_keys, toon = Z.stand, Z.walk, Z.override, Z.side_of, Z.hold, Z.cam_keys, Z.toon
VOICE = json.load(open(os.path.join(HERE, 'voice.json')))
ENV = json.load(open(os.path.join(HERE, 'voice_env.json'))) if os.path.exists(os.path.join(HERE, 'voice_env.json')) else {}

# ------------------------------------------------------------------ cast (original characters)
P = TO.preset
TEACHER = P('Teacher', '#cfe0ee', '#4a4a52', hat=None, vest='#6a5a48', haircol='#4a4440', stache=True, beardcol='#3a3430', height=1.03, boots='#2a2420', belt='#2a2420')
KEVIN = P('Kevin', '#d8442e', '#2e4a7a', hat=None, haircol='#5a3a1e', height=.86, boots='#f2f2f0', belt='#2e4a7a', collar=False)
ROHAN = P('Rohan', '#3a6ab0', '#2a2a30', hat=None, haircol='#120c08', height=.88, boots='#1a1a1a', belt='#2a2a30')
PRIYA = P('Priya', '#f2f0ea', '#f2f0ea', dress=True, dresscol='#e8a020', hat=None, haircol='#140c08', bun=True, height=.84, boots='#c83a5a', collar=False)
SAM = P('Sam', '#3aa070', '#3a3a42', hat=None, haircol='#2a1a10', height=.87, boots='#2a2a2e', belt='#3a3a42')
WHO = {'teacher': 'TEACHER', 'kevin': 'KEVIN', 'rohan': 'ROHAN', 'priya': 'PRIYA', 'sam': 'SAM'}


def lipsync(sh, ch, who):
    """mouth driven by the real voice amplitude of this speaker's lines (shot-local time)"""
    lines = [v for v in VOICE if v['who'] == who and v['id'] in ENV]
    def env(t):
        g = sh.t0 + t
        for v in lines:
            e = ENV[v['id']]; k = (g - v['t']) * 100
            if 0 <= k < len(e) - 1:
                i = int(k); f = k - i; return e[i] * (1 - f) + e[i + 1] * f
        return 0.0
    f0 = ch.fn
    def fn(t):
        d = f0(t); e = env(t)
        if e > .02 and 'face' in d:
            fc = dict(d['face']); fc['op'] = max(fc.get('op', 0), .015 + .1 * e); fc['w'] = fc.get('w', .07) * (1 - .18 * e); d['face'] = fc
        return d
    ch.fn = fn


def cast(sh, cid, preset):
    ch = toon(sh, cid, preset)
    if cid == 'TEACHER':
        g = Z.glasses_prop('TEACHER_specs'); sh.teacher_specs = g; Z.wear_glasses(sh, ch, g, drop=getattr(sh, 'specs_drop', lambda t: 0.0))
    return ch


def stage(sh, world, mood='day', elev=35, az=200):
    F.setup(sh, mood, elev, az, town=False, haze=False); sh.town = False
    cy = bpy.context.scene.cycles
    if os.environ.get('GPU'):                          # Kaggle / any NVIDIA box: same scene, same settings, rendered on the GPU
        pr = bpy.context.preferences.addons['cycles'].preferences
        for kind in ('OPTIX', 'CUDA'):
            try:
                pr.compute_device_type = kind; pr.refresh_devices()
                devs = [d for d in pr.devices if d.type == kind]
                if devs:
                    for d in pr.devices: d.use = d.type == kind
                    cy.device = 'GPU'; print('GPU', kind, [d.name for d in devs], flush=True); break
            except Exception as e: print('gpu fail', kind, e)
    cy.volume_step_rate = float(os.environ.get('VOLSTEP', 1.0)); cy.volume_max_steps = int(os.environ.get('VOLMAX', 1024))   # coarser volume marching for the final
    for o in [o for o in bpy.data.objects if o.name.startswith('sun')]: bpy.data.objects.remove(o)
    w = getattr(W, world)()
    tick = getattr(W, world + '_tick', None)
    if tick: sh.updates.append(lambda t, w=w: tick(w, t + 5.0))      # shot time (+5 s so smoke and waves are already going)
    sh.w = w
    return w


# ------------------------------------------------------------------ classroom staging
SEATS = {'KEVIN': (-1.1, -0.85), 'ROHAN': (1.1, -0.85), 'PRIYA': (-1.1, -2.4), 'SAM': (1.1, 0.7)}
BOARD_Y = 4.0


def seated(sh, cid, preset, face, talk_who=None, asleep=False, hands=None, look=None):
    """a student on a chair behind a desk, facing the board (+Y)"""
    x, y = SEATS[cid]; ch = cast(sh, cid, preset)
    a = stand(sh, ch, (x, y - .55), 180, '77_02', 1.0 + (hash(cid) % 7) * .3, face=face, look=look, z=0)
    seat_h = .46
    def mod(t, d):
        d['crouch'] = max(0.0, ch.L * ch.s - seat_h - .08 * ch.s); d['loc'] = (x, y - .5, 0); d['yaw'] = 180
        for sd, sx in (('L', -1), ('R', 1)): d['foot' + sd] = (sx * .13, -.36, 0)
        if asleep:
            d['lean'] = (.5, 0); d['head'] = [0, 25, 0]
            d['handL'] = (x - .18, y - .12, .78); d['handR'] = (x + .18, y - .12, .78)
        else:
            d['lean'] = (d['lean'][0] * .3 + .03, d['lean'][1] * .3)
            d['handL'] = d.get('handL') if hands else (x - .2, y - .15, .78); d['handR'] = (x + .2, y - .15, .78)
        if hands: d.update(hands(t, d))
        return d
    override(a, mod)
    if talk_who: lipsync(sh, ch, talk_who)
    return ch, a


def teacher(sh, xy=(1.2, 3.0), yaw=0, face=None, clip='77_02', hands=None, look=None):
    ch = cast(sh, 'TEACHER', TEACHER)
    a = stand(sh, ch, xy, yaw, clip, 1.0, face=face or [(0, 'bored')], look=look, z=0)
    if hands: override(a, lambda t, d: (d.update(hands(t, d)) or d))
    lipsync(sh, ch, 'teacher')
    return ch, a


def class_extras(sh, seed=0, faces=('bored', 'idle', 'watch')):
    r = random.Random(seed)
    for k, (x, y) in enumerate([(-3.3, -2.4), (3.3, -2.4), (-3.3, -0.85), (3.3, -0.85), (-3.3, 0.7), (3.3, 0.7), (-1.1, 0.7), (-1.1, 2.25), (1.1, 2.25), (1.1, -2.4)]):
        if (x, y) in SEATS.values(): continue
        pr = Z.CIV(500 + seed * 20 + k); pr['height'] = r.uniform(.82, .9)
        ch = toon(sh, f'ST{k}', pr)
        a = stand(sh, ch, (x, y - .55), 180, '77_02', r.uniform(.5, 3), face=[(0, r.choice(faces))], z=0)
        def mod(t, d, x=x, y=y, ch=ch):
            d['crouch'] = max(0.0, ch.L * ch.s - .54); d['loc'] = (x, y - .5, 0); d['yaw'] = 180
            for sd, sx in (('L', -1), ('R', 1)): d['foot' + sd] = (sx * .13, -.36, 0)
            d['handL'] = (x - .2, y - .15, .78); d['handR'] = (x + .2, y - .15, .78); d['lean'] = (.05, 0)
            return d
        override(a, mod)


def cam_path(sh, keys, roll=0.0, shake=.004, fstop=4.0):
    sh.camera(cam_keys(keys, roll=roll, shake=shake), fstop=fstop)


# ------------------------------------------------------------------ 1. the classroom
def s_c01(sh):
    stage(sh, 'classroom')
    teacher(sh, (1.6, 3.3), 170, [(0, 'bored')])
    seated(sh, 'ROHAN', ROHAN, [(0, 'sleep')], asleep=True)
    seated(sh, 'KEVIN', KEVIN, [(0, 'bored')])
    seated(sh, 'PRIYA', PRIYA, [(0, 'deadpan')])
    seated(sh, 'SAM', SAM, [(0, 'bored')])
    class_extras(sh, 1)
    cam_path(sh, [(0, (-3.9, -3.6, 2.6), (0.5, 1.8, .9), 18), (sh.dur, (-3.6, -3.2, 2.5), (0.6, 2.0, 1.0), 19)])
    sh.keylight(6)


def s_c03(sh):
    stage(sh, 'classroom')
    teacher(sh, (0.6, 3.1), 0, [(0, 'bored')])
    class_extras(sh, 2)
    seated(sh, 'KEVIN', KEVIN, [(0, 'idle')])
    def cam(t):
        h = head_of(sh.chars['TEACHER'])
        return (h + Vector((.2, -2.4, -.15)), h, 50, 0, h, .003)
    sh.camera(cam, fstop=2.8); sh.keylight(10)


def s_c04(sh):
    stage(sh, 'classroom')
    def hand(t, d):
        u = ease(t / .5); x, y = SEATS['KEVIN']; return dict(handR=(x + .22, y - .5 + .05 * u, .78 + 1.05 * u))
    ch, a = seated(sh, 'KEVIN', KEVIN, [(0, 'grin'), (.5, 'smug')], talk_who='kevin', hands=hand)
    class_extras(sh, 3)
    def cam(t):
        h = head_of(ch); return (h + Vector((.6, 1.9, .25)), h + Vector((0, 0, .1)), 45, 0, h, .003)
    sh.camera(cam, fstop=2.5); sh.keylight(10)


def board(sh, title=1.0, dino=1.0, blink=None):
    """board state for this shot: title / dino wipes (numbers or functions of t), blink(t) -> True when the chalk eye is shut"""
    def u(t):
        W.board_reveal(sh.w, title(t) if callable(title) else title, dino(t) if callable(dino) else dino)
        if blink: W.board_blink(sh.w, blink(t))
    sh.updates.append(u)


BX = lambda u: -2.6 + 5.2 * u                       # board u (0..1) -> world x
BOARD_FRONT = 3.86


def s_c02(sh):
    """teacher writes EVOLUTION OF LIFE ON EARTH, back to the class"""
    stage(sh, 'classroom'); prog = lambda t: ease(t / (sh.dur * .95)) * .68
    board(sh, title=lambda t: prog(t) * 1.0 / .68 * .66, dino=0.0)
    def hand(t, d):
        x = BX(prog(t)); return dict(handR=(x + .05, BOARD_FRONT - .08, 2.62 - .03 * math.sin(t * 25)))
    ch, a = teacher(sh, (-1.0, 3.25), 180, [(0, 'bored')], hands=hand)
    def walkx(t, d):
        d['loc'] = (min(BX(prog(t)) - .25, 1.5), 3.3, 0); return d
    override(a, walkx)
    seated(sh, 'KEVIN', KEVIN, [(0, 'bored')]); class_extras(sh, 4)
    cam_path(sh, [(0, (-2.2, .4, 1.55), (-.6, 3.8, 2.3), 26), (sh.dur, (-1.6, .6, 1.55), (.2, 3.8, 2.3), 28)])
    sh.keylight(8)


def s_c05(sh):
    """teacher slowly removes his glasses. silence."""
    stage(sh, 'classroom'); board(sh, 1.0, 0.0)
    sh.specs_drop = lambda t: .0
    ch, a = teacher(sh, (0.6, 3.1), 0, [(0, 'deadpan'), (1.6, 'bored')])
    g = sh.teacher_specs
    def hand(t, d):
        u = ease((t - .3) / 1.4); h = head_of(ch, -.02)
        return dict(handR=tuple(h + Vector((.12, -.25 - .1 * u, -.05 - .55 * u))))
    override(a, lambda t, d: (d.update(hand(t, d)) or d))
    def gl(t):
        u = ease((t - .3) / 1.4)
        if u > .05:
            bpy.context.view_layer.update(); g.location = ch.hands['R'].matrix_world.translation + Vector((-.05, -.04, .05))
    sh.updates.append(gl)
    def cam(t):
        h = head_of(ch); return (h + Vector((0, -1.25 + .25 * ease(t / sh.dur), -.05)), h, 55, 0, h, .002)
    sh.camera(cam, fstop=2.2); sh.keylight(10)


def s_c06(sh):
    stage(sh, 'classroom'); board(sh, 1.0, 0.0)
    ch, a = teacher(sh, (0.6, 3.1), 0, [(0, 'bored'), (1.0, 'suspicious')])
    def cam(t):
        h = head_of(ch); return (h + Vector((-.5, -2.0, -.2)), h, 48, 0, h, .003)
    sh.camera(cam, fstop=2.6); sh.keylight(10)


def s_c07(sh):
    """the class laughs; Kevin laughs a second late, not sure why"""
    stage(sh, 'classroom'); board(sh, 1.0, 0.0)
    seated(sh, 'PRIYA', PRIYA, [(0, 'laugh')]); seated(sh, 'SAM', SAM, [(0, 'laugh')]); seated(sh, 'ROHAN', ROHAN, [(0, 'sleep')], asleep=True)
    ch, a = seated(sh, 'KEVIN', KEVIN, [(0, 'confused'), (1.0, 'laugh')])
    class_extras(sh, 5, faces=('laugh', 'grin', 'laugh'))
    cam_path(sh, [(0, (2.6, 3.4, 1.7), (-.4, -1.0, .9), 24), (sh.dur, (2.4, 3.3, 1.65), (-.6, -1.0, .95), 26)])
    sh.keylight(8)


def s_c08(sh):
    """the teacher draws a giant chalk dinosaur - annoyingly good"""
    stage(sh, 'classroom'); prog = lambda t: .3 + .55 * ease(t / (sh.dur * .95))
    board(sh, 1.0, dino=prog)
    def hand(t, d):
        x = BX(prog(t)); return dict(handR=(x, BOARD_FRONT - .08, 1.6 + .35 * math.sin(t * 7)))
    ch, a = teacher(sh, (-0.4, 3.3), 180, [(0, 'determined')], hands=hand)
    override(a, lambda t, d: (d.update(loc=(min(BX(prog(t)) - .3, 1.6), 3.3, 0)) or d))
    cam_path(sh, [(0, (.2, .3, 1.6), (0, 3.9, 1.7), 30), (sh.dur, (.3, .6, 1.6), (.2, 3.9, 1.7), 30)])
    sh.keylight(8)


def s_c09(sh):
    stage(sh, 'classroom'); board(sh, 1.0, 1.0)
    def hand(t, d):
        return dict(handL=(-1.0, 3.6, 1.7)) if t > 1.0 else {}
    ch, a = teacher(sh, (-1.8, 3.0), -30, [(0, 'smirk'), (2.5, 'determined')], hands=hand)
    seated(sh, 'KEVIN', KEVIN, [(0, 'watch')]); class_extras(sh, 6)
    cam_path(sh, [(0, (-.5, -2.6, 1.4), (-.6, 3.6, 1.55), 30), (sh.dur, (-.5, -1.6, 1.42), (-.6, 3.6, 1.6), 32)])
    sh.keylight(8)


def s_c10(sh):
    """slow push toward the chalk dinosaur; it BLINKS"""
    stage(sh, 'classroom'); board(sh, 1.0, 1.0, blink=lambda t: 2.3 < t < 2.5)
    seated(sh, 'KEVIN', KEVIN, [(0, 'watch'), (2.45, 'shock')]); class_extras(sh, 7)
    eye = Vector((BX(.30 + 19 * 15.5 / 2400) , BOARD_Y - .1, 1.75 + (.5 - (.26 + 15.3 * 15.5 / 1200)) * 2.2))
    cam_path(sh, [(0, (-1.1, -1.9, 1.35), (0, 3.9, 1.7), 26), (sh.dur, (-.4, 1.4, 1.62), tuple(eye), 34)], shake=.002)
    sh.keylight(6)


def s_c11(sh):
    """Kevin looks at the teacher (not looking), then back at the board: it blinks again"""
    stage(sh, 'classroom'); board(sh, 1.0, 1.0, blink=lambda t: 2.2 < t < 2.4)
    teacher(sh, (2.2, 3.0), 120, [(0, 'bored')])
    ch, a = seated(sh, 'KEVIN', KEVIN, [(0, 'shock'), (.6, 'suspicious'), (1.6, 'watch'), (2.3, 'wow')],
                   look=lambda t: (2.2, 3.0, 1.6) if .6 < t < 1.5 else (-1.0, 3.9, 1.8))
    def cam(t):
        h = head_of(ch); return (h + Vector((-.7, 1.4, .1)), h, 42, 0, h, .003)
    sh.camera(cam, fstop=2.4); sh.keylight(10)


def s_c12(sh):
    """narrator: but the story of life didn't begin with dinosaurs... the camera pushes INTO the chalk eye"""
    stage(sh, 'classroom'); board(sh, 1.0, 1.0)
    class_extras(sh, 8)
    eye = Vector((BX(.30 + 19 * 15.5 / 2400), BOARD_Y - .1, 1.75 + (.5 - (.26 + 15.3 * 15.5 / 1200)) * 2.2))
    cam_path(sh, [(0, (-.5, 1.2, 1.65), tuple(eye), 34), (sh.dur * .7, tuple(eye + Vector((0, -1.1, 0))), tuple(eye), 40), (sh.dur, tuple(eye + Vector((0, -.25, 0))), tuple(eye), 50)], shake=.001)
    sh.keylight(6)


for _p in ('shots_a.py', 'shots_b.py', 'shots_c.py'):
    exec(compile(open(os.path.join(HERE, _p)).read(), os.path.join(HERE, _p), 'exec'))

_CB = {}
def _coll_radius(c):
    if c.name in _CB: return _CB[c.name]
    pts = [o.matrix_world @ Vector(v) for o in c.all_objects if o.type == 'MESH' for v in o.bound_box]
    if not pts: _CB[c.name] = (Vector(), 0.0); return _CB[c.name]
    lo = Vector([min(p[i] for p in pts) for i in range(3)]); hi = Vector([max(p[i] for p in pts) for i in range(3)])
    cen = (lo + hi) / 2 - c.instance_offset; _CB[c.name] = (cen, (hi - lo).length / 2); return _CB[c.name]


_clear0 = F.Shot.clear_camera
def _clear_props(self, rad=1.7):
    """also hide scattered props (rocks, trees, plants) the camera would pass through or sit inside"""
    _clear0(self, rad)
    if self.cam is None: return
    cps = []
    for k in range(13):                                 # lens path + the sight line to the subject (props must not sit inside either)
        r_ = self.cam[1](self.dur * k / 12); c0, tg = Vector(r_[0]), Vector(r_[1])
        cps += [q for q in (c0.lerp(tg, u) for u in (0, .25, .5, .75, .92)) if (q - c0).length < 15.0]   # near the lens only: no holes in far forests
    n = 0
    for e in bpy.data.objects:
        if e.instance_type != 'COLLECTION' or e.instance_collection is None or e.hide_render: continue
        cen, r = _coll_radius(e.instance_collection); r *= max(e.scale); c = e.matrix_world @ cen
        if any((c - p).length < r * .75 + .3 for p in cps): e.hide_render = True; n += 1
    print('CLEARPROPS', n, flush=True)
    if os.environ.get('CAMDBG'):                      # what is the lens inside of?
        p = Vector(self.cam[1](self.dur * .6)[0]); bpy.context.view_layer.update(); hits = []
        for o in bpy.data.objects:
            if o.hide_render: continue
            if o.type == 'MESH':
                bb = [o.matrix_world @ Vector(v) for v in o.bound_box]
            elif o.instance_type == 'COLLECTION' and o.instance_collection:
                cen, r = _coll_radius(o.instance_collection); c = o.matrix_world @ cen; r *= max(o.scale)
                bb = [c - Vector((r, r, r)), c + Vector((r, r, r))]
            else: continue
            lo = Vector([min(v[i] for v in bb) for i in range(3)]); hi = Vector([max(v[i] for v in bb) for i in range(3)])
            if all(lo[i] <= p[i] <= hi[i] for i in range(3)): hits.append(o.name)
        ter = getattr(self, 'ter', None)
        self.at(self.dur * .6)
        print('BEASTS', [(o.name, tuple(round(v, 1) for v in o.location), tuple(round(v, 2) for v in o.scale)) for o in bpy.data.objects if o.name.endswith('_root')][:12], flush=True)
        print('CAMDBG', tuple(round(v, 2) for v in p), 'ground', round(ter.z(p.x, p.y), 2) if ter else None, hits[:40], flush=True)
F.Shot.clear_camera = _clear_props

_cam0 = F.Shot.camera
def _camera_safe(self, fn, *a, **k):
    """never let the lens sink under the terrain (rough ground between keyed positions)"""
    ter = getattr(self, 'ter', None)
    if ter is not None:
        f0 = fn
        def fn(t):
            r = list(f0(t)); p = Vector(r[0]); g = ter.z(p.x, p.y) + .3
            if p.z < g: r[0] = Vector((p.x, p.y, g))
            return tuple(r)
    return _cam0(self, fn, *a, **k)
F.Shot.camera = _camera_safe

SHOTS = {k[2:]: v for k, v in list(globals().items()) if k.startswith('s_') and callable(v)}

if __name__ == '__main__':
    F.main(SHOTS)
