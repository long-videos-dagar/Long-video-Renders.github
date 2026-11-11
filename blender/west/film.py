"""THE COWBOY WHO ARRESTED THE SHERIFF - shot builders.

python3 film.py -- still <shot> <out.png> [t]        one frame (t = seconds into the shot)
python3 film.py -- frames <shot> <f0> <f1> <outdir>  frames f0..f1 (1-based, shot-local) as PNG

Env: CAST (cast.blend), RW RH SAMPLES, USE_PH, VEG (grass density), HANDLE (extra seconds rendered after the shot for dissolves)

Every shot: a camera that keeps moving (push-ins, orbits, cranes, whips), real mocap actors with expressions on the
narrated words, a fully dressed set. Shot timing comes from shots.json (aligned to the voiceover)."""
import time
import os as _os, sys as _sys
if _os.environ.get('PYTHONHASHSEED') != '0':        # hash() seeds building/crowd randomness: must be identical in every chunk process
    _os.environ['PYTHONHASHSEED'] = '0'; _os.execv(_sys.executable, [_sys.executable] + _sys.argv)
import sys, os, math, json, random
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'real'))
import bpy
from mathutils import Vector, Matrix, Euler, Quaternion
import town as T, props as PR, mocap as M, toon as TO
CA = TO

FPS = 24
CFG = json.load(open(os.path.join(HERE, 'shots.json')))
CAST = os.environ.get('CAST', '/tmp/cast.blend')
S = T.STREET; W_ = T.WALK; STREET_X = T.STREET
DECK = .34          # boardwalk top


class Shot:
    def __init__(self, sid):
        self.sid = sid; row = next(r for r in CFG['shots'] if r['id'] == sid)
        self.t0, self.dur = row['t0'], row['dur']; self.actors = []; self.updates = []; self.cam = None
        self.chars = {}; self.key = None; self.key_e = 0.0

    # ---- helpers
    def cast(self, *ids):
        need = [i for i in ids if i not in self.chars]
        for i in need:
            p = {'JACK': TO.JACK, 'SHER': TO.SHERIFF}.get(i) or TO.crowd_preset(int(i[1:]) if i[1:].isdigit() else hash(i) % 97)
            self.chars[i] = TO.Toon(i, p)
        return [self.chars[i] for i in ids]

    def crowd(self, n, spots, base_ids=None, seed=0):
        """n townsfolk from the crowd library (cloned when more are needed)"""
        base_ids = base_ids or [f'T{i:02d}' for i in range(14)]
        r = random.Random(seed); out = []
        base_ids = [f'T{(seed * 7 + i) % 40:02d}' for i in range(14)]; loaded = self.cast(*base_ids[:min(n, len(base_ids))])
        for k in range(n):
            b = loaded[k % len(loaded)]
            ch = b if k < len(loaded) else TO.Toon(f'{b.cid}c{k}', TO.crowd_preset(40 + seed * 17 + k))
            out.append(ch)
        return out

    def actor(self, ch, acts, **kw):
        a = TO.ToonActor(ch, acts, **kw); self.actors.append(a); return a

    def populate(self, n=None, seed=None):
        """background townsfolk inside the camera's view: walkers on the street lanes, people chatting and waiting on the
        boardwalks.  Kept clear of the main action, the camera, wagons and the well."""
        if not getattr(self, 'town', True) or getattr(self, 'interior', None) or getattr(self, 'no_extras', False) or self.cam is None: return []
        mood = getattr(self, 'mood', 'day')
        n = n if n is not None else int(os.environ.get('EXTRAS', 2 if mood == 'night' else 9))
        if n <= 0: return []
        r = random.Random(seed if seed is not None else hash(self.sid) % 9973)
        self.at(self.dur / 2); bpy.context.view_layer.update()
        co = self.cam[0]; cp = co.matrix_world.translation.copy(); fw = co.matrix_world.to_3x3() @ Vector((0, 0, -1)); fw.z = 0
        if fw.length < 1e-3: return []
        fw.normalize(); cd = co.data
        half = math.atan(cd.sensor_width / 2 * (9 / 16) / cd.lens) * .95
        busy = [Vector((a.ch.root.location.x, a.ch.root.location.y, 0)) for a in self.actors] + [Vector(p) for p in getattr(self, 'keep_clear', [])]
        obst = [(Vector((-1.8, 44, 0)), 2.6), (Vector((3.3, 38, 0)), 3.2), (Vector((-3.3, 27.5, 0)), 3.2), (Vector((-2.6, -16, 0)), 1.8)]
        def ok(p, rad=1.6):
            d = p - Vector((cp.x, cp.y, 0)); dist = d.length
            if dist < 6.0 or dist > 34: return False
            if abs(math.atan2(d.cross(fw).z, d.dot(fw))) > half: return False
            if any((p - b).length < 3.0 for b in busy): return False
            if any((p - c).length < r_ for c, r_ in obst): return False
            return all((p - q).length > rad for q in placed)
        placed = []; people = []; k = 0; tries = 0
        WALK_CLIPS = [('82_08', 1.0), ('82_09', 1.0), ('82_11', 1.0), ('91_18', 1.0)]
        STAND = ['80_48', '80_44', '77_02', '40_10', '77_05', '79_70']
        while len(people) < n and tries < 400:
            tries += 1
            kind = r.choice(['walk', 'walk', 'pair', 'stand', 'stand'] if mood != 'night' else ['walk', 'stand'])
            side = r.choice((-1, 1)); y = cp.y + fw.y * r.uniform(8, 30) + r.uniform(-6, 6)
            if kind == 'walk':
                x = side * r.uniform(.9, 1.7); dirn = r.choice((-1, 1)); p0 = Vector((x, y, 0)); p1 = p0 + Vector((0, dirn * 1.3 * self.dur, 0))
                if not (ok(p0) and ok(p1)): continue
                ch = TO.Toon(f'X{len(people)}', TO.crowd_preset(200 + r.randint(0, 999)))
                cl, _ = r.choice(WALK_CLIPS)
                self.actor(ch, [TO.Act(0, cl, r.uniform(.5, 1.5), self.dur + 1, loc=p0, yaw=0 if dirn < 0 else 180)], face=[(0, r.choice(['idle', 'watch', 'chat']))])
                placed += [p0, (p0 + p1) / 2, p1]; people.append(ch)
            else:
                x = side * (STREET_X - W_ + r.uniform(.4, .75)); p0 = Vector((x, y, DECK))
                if not any(f['side'] == side and f['porch'] and abs(y - f['y']) < f['w'] / 2 - 1.2 for f in T.FRONTS): continue
                if not ok(Vector((x, y, 0)), 1.8): continue
                cnt = 2 if kind == 'pair' else 1
                for j in range(cnt):
                    pj = p0 + Vector((0, j * .95, 0))
                    ch = TO.Toon(f'X{len(people)}', TO.crowd_preset(200 + r.randint(0, 999)))
                    yaw = (90 * side + r.uniform(-30, 30)) if cnt == 1 else (0 if j == 1 else 180) + side * 25
                    self.actor(ch, [TO.Act(0, r.choice(STAND), r.uniform(.5, 3.0), self.dur + 1, loc=pj, yaw=yaw, lock_root=True)],
                               face=[(0, r.choice(['chat', 'idle', 'watch']) if cnt == 1 else 'chat')], talk=[(0, self.dur, .6)] if cnt == 2 and j == 0 else None)
                    placed.append(Vector((pj.x, pj.y, 0))); people.append(ch)
            k += 1
        print('EXTRAS', self.sid, len(people), flush=True)
        return people

    def clear_camera(self, rad=1.7):
        """hide extras that would sit right in front of the lens (toon heads are big: one near the camera fills the frame)"""
        if self.cam is None: return
        cps = []
        for t in (0, self.dur * .25, self.dur * .5, self.dur * .75, self.dur):
            r_ = self.cam[1](t); cps.append((Vector(r_[0]), Vector(r_[1])))
        hidden = 0
        for a in self.actors:
            ch = a.ch
            if ch.cid in ('JACK', 'SHER') or ch.cid in getattr(self, 'protect', ()): continue
            for t in (0, self.dur * .5, self.dur):
                a.apply(t); p = ch.root.matrix_world.translation.copy() + Vector((0, 0, 1.2))
                bad = False
                for c, tg in cps:
                    d = p - c; dist = d.length; fw = (tg - c).normalized()
                    if dist < rad or (dist < 3.2 and d.normalized().dot(fw) > .8 and dist < (tg - c).length - .6): bad = True
                if bad:
                    for o in [ch.root] + list(ch.root.children_recursive): o.hide_render = True; o.hide_viewport = True
                    a.gone = True; hidden += 1; break          # also parked far below: per-frame face updates unhide eyes/teeth
        print('CLEARCAM', self.sid, hidden, flush=True)

    def keylight(self, energy=25.0, col=(1, .9, .8), size=1.2):
        l = bpy.data.lights.new('key', 'AREA'); l.size = size; l.color = col; l.use_shadow = True
        self.key = bpy.data.objects.new('key', l); bpy.context.scene.collection.objects.link(self.key); self.key_e = energy

    def camera(self, fn, lens=35, fstop=2.8, blur=True):
        cam = bpy.data.cameras.new('cam'); co = bpy.data.objects.new('cam', cam); bpy.context.scene.collection.objects.link(co)
        bpy.context.scene.camera = co; cam.clip_start = .05; cam.clip_end = 6000; cam.sensor_width = 36
        cam.dof.use_dof = True; cam.dof.aperture_fstop = fstop
        self.cam = (co, fn); bpy.context.scene.render.use_motion_blur = blur and not os.environ.get('NOMB'); bpy.context.scene.render.motion_blur_shutter = .5
        return co

    def lod(self):
        """level of detail by distance to the camera (mid-shot): memory and render time stay low for crowds"""
        self.at(self.dur / 2); cam = self.cam[0].matrix_world.translation
        for ch in []:
            d = (head_of(ch) - cam).length
            for o in ch.col.all_objects:
                for md in o.modifiers:
                    if md.type == 'SUBSURF': md.render_levels = 1 if d < 3.0 else 0
                    if md.type == 'PARTICLE_SYSTEM':
                        st = md.particle_system.settings
                        if d > 14: md.show_render = False
                        else:
                            st.rendered_child_count = max(2, min(st.rendered_child_count, 30 if d < 2 else (10 if d < 6 else 4)))
                            st.render_step = 3 if d < 3 else 2
            ch.lod_d = d

    def chars_all(self):
        seen = []
        for a in self.actors:
            if hasattr(a, 'ch') and a.ch not in seen: seen.append(a.ch)
        for c in self.chars.values():
            if c not in seen: seen.append(c)
        return seen

    def at(self, t):
        for a in self.actors:
            a.apply(t)
            if getattr(a, 'gone', False): a.ch.root.location.z = -500.0
        for u in self.updates: u(t)
        bpy.context.view_layer.update()
        co, fn = self.cam; r = fn(t)
        loc, tgt, lens = Vector(r[0]), Vector(r[1]), r[2]
        roll = r[3] if len(r) > 3 else 0.0; focus = Vector(r[4]) if len(r) > 4 and r[4] is not None else tgt
        loc = loc + handheld(t, r[5] if len(r) > 5 else .012)
        co.location = loc; q = (tgt - loc).to_track_quat('-Z', 'Y'); co.rotation_euler = (q @ Quaternion((0, 0, 1), math.radians(roll))).to_euler()
        co.data.lens = lens; co.data.dof.focus_distance = max(.1, (focus - loc).length)
        if self.key is not None:
            d = (tgt - loc); dist = d.length; d.normalize(); side = d.cross(Vector((0, 0, 1))).normalized()
            kp = loc - side * dist * .45 + Vector((0, 0, dist * .35 + .3))
            self.key.location = kp; self.key.rotation_euler = (focus - kp).to_track_quat('-Z', 'Y').to_euler()
            self.key.data.energy = self.key_e * max(.6, dist) ** 2


CU_K = 2.3          # toon heads are ~2.3x a real head: close-up sizes were tuned for real proportions


def cu(sh, ch, angle=15, elev=4, size=(.75, .45), lens=50, up=.0, shake=.006, fstop=2.0, target='Head', key=18.0):
    """close-up camera on a character: push-in from size[0] to size[1] metres of frame height"""
    def fn(t):
        p = head_of(ch, -.02 + up) if target == 'Head' else bone_pos(ch, target) + Vector((0, 0, up))
        s = K([(0, size[0]), (sh.dur, size[1])], t) * CU_K
        return (framed(p, facing(ch), angle, elev, s, lens, ch=ch), p, lens, 0, p, shake)
    sh.camera(fn, lens=lens, fstop=fstop)
    if sh.key is None: sh.keylight(key)


def handheld(t, amp):
    """subtle operator shake (deterministic)"""
    return Vector((amp * (math.sin(t * 1.7) * .6 + math.sin(t * 4.3 + 1) * .4), amp * (math.sin(t * 1.3 + 2) * .6 + math.sin(t * 3.7) * .4), amp * .7 * (math.sin(t * 2.1 + 3) * .7 + math.sin(t * 5.3) * .3)))


def ease(u): u = max(0.0, min(1.0, u)); return u * u * (3 - 2 * u)
def lerp(a, b, u): return Vector(a).lerp(Vector(b), ease(u))
def K(keys, t):
    keys = sorted(keys, key=lambda k: k[0])
    if t <= keys[0][0]: return keys[0][1]
    if t >= keys[-1][0]: return keys[-1][1]
    for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
        if t0 <= t <= t1:
            u = ease((t - t0) / (t1 - t0))
            if isinstance(v0, (tuple, list, Vector)): return tuple(a + (b - a) * u for a, b in zip(v0, v1))
            return v0 + (v1 - v0) * u


def head_of(ch, up=.08):
    """a point between the eyes (up=.08 default kept for callers that meant 'face centre')"""
    bpy.context.view_layer.update()
    return ch.head.matrix_world @ Vector((0, -ch.hy * .2, ch.cz)) + Vector((0, 0, up - .08))


def facing(ch):
    """horizontal forward direction of a character (from the pelvis)"""
    f = ch.root.matrix_world.to_3x3() @ Vector((0, -1, 0)); f.z = 0
    return f.normalized() if f.length > 1e-4 else Vector((0, -1, 0))


def _owner(ob):
    while ob is not None and ob.parent is not None: ob = ob.parent
    return ob


def _clear(subj, d, dist, ch=None):
    """free distance from subj along d (the subject's own geometry ignored; other characters block when ch is given)"""
    sc = bpy.context.scene; dg = bpy.context.evaluated_depsgraph_get(); o = Vector(subj); tr = 0.0
    for _ in range(8):
        hit, loc, nor, idx, ob, mat = sc.ray_cast(dg, o + d * .02, d, distance=max(.01, dist - tr))
        if not hit: return dist
        if ob is not None and any(c.name in ('Characters', 'Face', 'Props') or c.name.startswith('C_') for c in ob.users_collection) and not ob.name.startswith(('vault', 'b_', 's_')):
            if ch is None or _owner(ob) is ch.root or ob.name.endswith('_ink'):
                tr += (loc - o).length + .02; o = loc + d * .02; continue
        return (loc - Vector(subj)).length - .15
    return dist


def framed(subj, face_dir, angle, elev, size, lens, ignore=(), ch=None):
    """camera position framing `subj` at `size` metres of frame height, from `angle` degrees around the subject's facing
    (0 = straight on the face) and `elev` degrees up. If a wall/prop blocks that view, nearby angles are tried first,
    then the camera is pulled in front of the obstacle."""
    dist = size * lens / 36.0; best = None
    for da in (0, 12, -12, 25, -25, 40, -40, 60, -60):
        d = Matrix.Rotation(math.radians(angle + da), 3, 'Z') @ Vector(face_dir); d.z = 0; d.normalize()
        d = (d * math.cos(math.radians(elev)) + Vector((0, 0, math.sin(math.radians(elev))))).normalized()
        free = _clear(subj, d, dist, ch)
        if free >= dist * .9: return Vector(subj) + d * dist
        if best is None or free > best[0]: best = (free, d)
    return Vector(subj) + best[1] * max(.35, best[0])


def bone_pos(ch, b):
    bpy.context.view_layer.update()
    if b in ('RightHand', 'LeftHand'): return ch.hands['L' if b == 'RightHand' else 'R'].matrix_world.translation.copy()
    if b == 'Head': return head_of(ch)
    return ch.torso.matrix_world.translation.copy()


# ------------------------------------------------------------------ scene setup
def setup(shot, mood='day', elev=30, az=150, town=True, interior=None, veg=None, haze=True):
    haze = haze and not os.environ.get('NOHAZE')
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene; W, H = int(os.environ.get('RW', 1440)), int(os.environ.get('RH', 2560))
    sc.render.engine = 'CYCLES'; sc.render.resolution_x, sc.render.resolution_y = W, H; sc.render.fps = FPS
    sc.cycles.samples = int(os.environ.get('SAMPLES', 64)); sc.cycles.use_denoising = True
    try: sc.cycles.denoiser = 'OPENIMAGEDENOISE'
    except Exception: pass
    sc.cycles.use_adaptive_sampling = True; sc.cycles.adaptive_threshold = float(os.environ.get('ADAPT', .02))
    if os.environ.get('FAST'):        # final video: fewer bounces (toon look barely changes), persistent data across frames
        sc.cycles.max_bounces = 4; sc.cycles.diffuse_bounces = 2; sc.cycles.glossy_bounces = 1; sc.cycles.transmission_bounces = 2; sc.cycles.volume_bounces = 0
        sc.cycles.transparent_max_bounces = 12; sc.render.use_persistent_data = True
    else:
        sc.cycles.max_bounces = 6; sc.cycles.diffuse_bounces = 3; sc.cycles.glossy_bounces = 3; sc.cycles.transmission_bounces = 4; sc.cycles.volume_bounces = 1
    sc.render.film_transparent = False
    shot.mood, shot.interior, shot.town = mood, interior, town
    if town:
        os.environ['VEG'] = str(veg if veg is not None else os.environ.get('VEG', 1.0)); T.build_town()
    sun = T.sky(mood, sun_elev=elev, sun_az=az)
    if haze and mood != 'night': T.haze(.0008 if mood == 'day' else .0014, (1, .82, .6) if mood != 'day' else (1, .95, .88))
    if haze and mood == 'night': T.haze(.0012, (.5, .6, 1.0))
    out = {}
    if interior == 'bank': out = T.bank_interior()
    if interior == 'sheriff': out = T.sheriff_interior()
    sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'
    return out


def night_lights():
    """oil lamps on porches and lit windows for night shots"""
    for k, (x, y) in enumerate([(-S + W_ - .2, -4.5), (-S + W_ - .2, 9.0), (S - W_ + .2, -1.5), (S - W_ + .2, 12.0), (-S + W_ - .2, 15.0), (S - W_ + .2, 24.0)]):
        T.lantern(f'nl{k}', (x, y, 2.6), energy=45)
    moon = bpy.data.lights.new('moon', 'SUN'); moon.energy = .5; moon.color = (.55, .65, 1.0); moon.angle = math.radians(.5)
    mo = bpy.data.objects.new('moon', moon); bpy.context.scene.collection.objects.link(mo); mo.rotation_euler = (math.radians(55), 0, math.radians(-30))


def walk_line(t, start, end, dur): return lerp(start, end, t / dur)


# ------------------------------------------------------------------ the shots
def s_hook(sh):
    """0-4.3 'In the Wild West, there was a cowboy who once arrested the town sheriff.'  Drone dive from the sky over the
    town at golden hour down the main street to Jack holding the Sheriff at gunpoint, crowd around."""
    setup(sh, 'sunset', 9, 235)
    jack, sher = sh.cast('JACK', 'SHER')
    people = sh.crowd(10, None, seed=1)
    sh.actor(jack, [CA.Act(0, '80_03', 2.6, 6, loc=(.3, 4.0, 0), yaw=180 - 0)], face=[(0, 'determined'), (3.2, 'smirk')])
    sh.actor(sher, [CA.Act(0, '79_73', 3.6, 6, loc=(.3, 6.6, 0), yaw=0, lock_root=True)], face=[(0, 'shock'), (2.6, 'fear')])
    _g = PR.revolver('jgun'); _g.scale = (1.4, 1.4, 1.4); sh.updates.append(lambda t, _g=_g: hold_gun(jack, _g, sher))
    spots = [(-3.2, 6.5), (-2.5, 8.6), (3.4, 7.2), (2.6, 9.4), (-4.0, 3.6), (4.2, 4.4), (-1.5, 10.6), (1.4, 11.2), (-4.6, 9.8), (4.8, 10.0)]
    clips = ['79_74', '80_48', '77_02', '79_73', '80_44', '79_70', '77_05', '79_74', '80_48', '77_02']
    for k, (ch, (x, y)) in enumerate(zip(people, spots)):
        yaw = math.degrees(math.atan2(-(.3 - x), (5.3 - y))) if False else math.degrees(math.atan2(x - .3, -(y - 5.3))) + 180
        sh.actor(ch, [CA.Act(0, clips[k], 1.0 + (k * .37) % 2, 8, loc=(x, y, 0), yaw=yaw, lock_root=True)], face=[(0, ['shock', 'angry', 'worry', 'fear', 'laugh'][k % 5])], look=lambda t: (.3, 5.3, 1.6))
    def cam(t):
        u = t / sh.dur
        p = (Vector((14, -70, 46)).lerp(Vector((4.5, -9, 6)), ease(min(1, u * 1.25)))).lerp(Vector((1.8, 1.4, 1.75)), ease((u - .62) / .38))
        tgt = Vector((0, 20, 4)).lerp(Vector((.3, 5.3, 1.5)), ease(u * 1.1))
        return (p, tgt, K([(0, 18), (sh.dur * .6, 24), (sh.dur, 32)], t), K([(0, -8), (sh.dur, 0)], t), (.3, 5.3, 1.5), .02)
    sh.camera(cam, fstop=4.0)


def s_funniest(sh):
    """4.3-5.7 'And the funniest part?'  Fast push into Jack's face, he smirks to camera."""
    setup(sh, 'sunset', 9, 235, veg=.4)
    jack, sher = sh.cast('JACK', 'SHER')
    sh.actor(jack, [CA.Act(0, '80_03', 3.0, 6, loc=(.3, 4.0, 0), yaw=180)], face=[(0, 'determined'), (.5, 'smirk')])
    sh.actor(sher, [CA.Act(0, '79_73', 4.0, 6, loc=(.3, 6.6, 0), yaw=0, lock_root=True)], face=[(0, 'fear')])
    _g = PR.revolver('jgun'); _g.scale = (1.4, 1.4, 1.4); sh.updates.append(lambda t, _g=_g: hold_gun(jack, _g, sher))
    cu(sh, jack, angle=20, elev=2, size=(1.4, .5), lens=45, fstop=2.2)


def s_nobody(sh):
    """5.7-7.55 'Nobody believed him.'  Townsfolk laugh and wave him off; slow dolly across their faces."""
    setup(sh, 'sunset', 9, 235, veg=.4)
    people = sh.crowd(7, None, seed=2)
    clips = ['79_70', '80_44', '79_70', '79_74', '80_44', '79_70', '80_48']
    pos = [(-1.6, 7.0), (-.7, 7.6), (.3, 7.2), (1.2, 7.8), (2.1, 7.1), (-2.4, 8.2), (2.9, 8.3)]
    for k, (ch, (x, y)) in enumerate(zip(people, pos)):
        sh.actor(ch, [CA.Act(0, clips[k], .8 + k * .4, 6, loc=(x, y, 0), yaw=0, lock_root=True)], face=[(0, 'laugh' if k % 3 != 2 else 'smirk')], look=lambda t: (0, 3.5, 1.6))
    def cam(t):
        x = K([(0, -2.6), (sh.dur, 2.4)], t)
        return ((x, 5.0, 1.62), (x * .7, 8.0, 1.5), 32, 0, (x * .7, 7.3, 1.6), .01)
    sh.camera(cam, fstop=2.8)


def s_ride(sh):
    """7.55-10.0 'One morning, Jack rode into a dusty little town' - dawn, low tracking shot in front of the horse as Jack rides
    down the main street, sun behind him, dust in the air."""
    setup(sh, 'dawn', 6, 0, veg=.8)
    import horse as HO
    jack, = sh.cast('JACK')
    h = HO.HorseGLB('jack_horse'); v = 1.35; y0 = -34.0
    TO.ride_fn(jack, lambda t: h.seat(), face=[(0, 'determined')])
    sh.keep_clear = [(.6, y0 + v * k * .5, 0) for k in range(8)]
    def ride(t):
        h.update(t, (.6, y0 + v * t, 0), math.pi, speed=v); bpy.context.view_layer.update(); jack.apply(t)
    sh.updates.append(ride)
    def cam(t):
        p = Vector((.6, y0 + v * t, 0)); u = ease(t / sh.dur)
        return (p + Vector((1.1 - .4 * u, 6.2 - 2.2 * u, .55 + .25 * u)), p + Vector((0, -.2, 1.75)), K([(0, 30), (sh.dur, 35)], t), 2.0, p + Vector((0, 0, 1.8)), .015)
    sh.camera(cam, fstop=2.8)


def s_walkin(sh):
    """10.0-12.45 '...and noticed something strange.'  Jack walks down the main street, slows and looks around."""
    setup(sh, 'dawn', 10, 20, veg=.6)
    jack, = sh.cast('JACK')
    people = sh.crowd(5, None, seed=3)
    sh.actor(jack, [CA.Act(0, '82_09', 6.6, 3, loc=(.5, -6, 0), yaw=180 + 180, speed=.9), CA.Act(1.5, '91_18', 5.0, 4, loc=(.5, -3.4, 0), yaw=0, lock_root=True, blend=.6)],
             face=[(0, 'idle'), (1.4, 'suspicious')], look=lambda t: None if t < 1.4 else (-6.5, 12, 3.0))
    for k, ch in enumerate(people):
        x = (-S + W_ * .5) if k % 2 else (S - W_ * .5); y = 2 + k * 4
        sh.actor(ch, [CA.Act(0, '77_02' if k % 2 else '40_10', 2 + k, 6, loc=(x, y, DECK), yaw=90 if k % 2 else -90, lock_root=True)], face=[(0, 'suspicious')], look=lambda t: bone_pos(jack, 'Head'))
    def cam(t):
        hp = bone_pos(jack, 'Hips')
        return (hp + Vector(K([(0, (-.8, 3.4, .55)), (sh.dur, (-1.2, 2.3, .65))], t)), hp + Vector((0, 0, .55)), 30, 0, hp + Vector((0, 0, .6)), .02)
    sh.camera(cam, fstop=2.8)


FACES = os.environ.get('FACES', '/tmp')
BANK_DOOR = Vector((-S, 12.0, 0)); SHER_DOOR = Vector((-S, -2.0, 0))


def poster_img(who):
    face = os.path.join(FACES, f'{who}_face.png'); out = os.path.join(FACES, f'poster_{who}.png')
    if not os.path.exists(out):
        PR.poster_image(out, face, name='JACK "THE DRIFTER"' if who == 'jack' else 'THE SHERIFF', crime='FOR BANK ROBBERY')
    return out


def s_robbed(sh):
    """12.45-14.95 'Every bank in town had been robbed,'  Bank front: smashed window, CLOSED sign, townsfolk staring; whip-pan out."""
    setup(sh, 'day', 28, 110, veg=.5)
    people = sh.crowd(4, None, seed=4)
    T.box('board_x1', (.04, 1.7, .12), (-S + .02, 12 - 2.4, 1.55), T.wood('plank_x', '#7a5a3a', weather=.8), rot=(math.radians(35), 0, 0))
    T.box('board_x2', (.04, 1.7, .12), (-S + .02, 12 - 2.4, 1.55), T.wood('plank_x', '#7a5a3a', weather=.8), rot=(math.radians(-35), 0, 0))
    T.text('closed', 'CLOSED', (-S + .2, 12.0, 2.0), .22, T.plain('red_paint', '#8a1a14', .7), rot=(math.pi / 2, 0, math.pi / 2), extrude=.005)
    for k, ch in enumerate(people):
        x = -S + W_ + .8 + (k % 2) * .9; y = 9.0 + k * 1.6
        sh.actor(ch, [CA.Act(0, ['79_74', '77_02', '80_48', '77_05'][k], 1.5 + k, 6, loc=(x, y, 0), yaw=-90 + (k - 1.5) * 12, lock_root=True)], face=[(0, ['worry', 'angry', 'shout', 'sad'][k])], look=lambda t: (-S, 12, 2.0))
    def cam(t):
        u = t / sh.dur
        p = Vector((-1.5, 6.5, 1.7)).lerp(Vector((-2.6, 9.6, 2.0)), ease(u / .8))
        tgt = Vector((-S, 12.0, 2.2)).lerp(Vector((-S, 13.0, 2.6)), ease(u))
        if u > .85: tgt = tgt.lerp(Vector((S, 4.0, 2.0)), ease((u - .85) / .15))       # whip pan to the next shot
        return (p, tgt, 28, 0, (-S, 12.0, 2.0), .015)
    sh.camera(cam, fstop=4.0)


def s_knew(sh):
    """14.95-18.85 '...but the sheriff somehow knew exactly when each robbery would happen.'  Sheriff's office: he checks his
    pocket watch, smiles; calendar with circled dates; push in to the watch."""
    setup(sh, 'day', 28, 110, veg=.2, interior='sheriff')
    sher, = sh.cast('SHER')
    desk = Vector((-S - 4.5, -2 + .6, 1.04))
    sh.actor(sher, [CA.Act(0, '77_05', .8, 6, loc=(desk.x - .75, desk.y - .1, .2), yaw=-90, lock_root=True)], face=[(0, 'idle'), (1.4, 'smirk'), (3.0, 'grin')], look=lambda t: (desk.x + 1, desk.y - .4, 1.3))
    if PR.T.PH:
        try:
            import lib
            w = lib.model(['vintage_pocket_watch', 'pocket_watch'])
            if w: wo = lib.place(w, (0, 0, 0), 0, 1.6); sh.updates.append(lambda t, wo=wo: setattr(wo, 'location', bone_pos(sher, 'RightHand') + Vector((.05, -.04, .02))))
        except Exception as e: print('watch', e)
    else:
        wo = T.cyl('watch', .025, .01, (0, 0, 0), T.plain('gold', '#e8b040', .2, 1.0), rot=(math.pi / 2, 0, 0), v=24, c='Props')
        sh.updates.append(lambda t: setattr(wo, 'location', bone_pos(sher, 'RightHand') + Vector((.05, -.04, .02))))
    # calendar on the wall with circled dates
    cal = os.path.join(FACES, 'calendar.png')
    if not os.path.exists(cal):
        from PIL import Image, ImageDraw, ImageFont
        im = Image.new('RGB', (600, 760), (232, 222, 196)); d = ImageDraw.Draw(im); fb = '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'
        d.text((300, 60), 'OCTOBER 1879', font=ImageFont.truetype(fb, 46), fill=(40, 26, 16), anchor='mm')
        for i in range(31):
            x, y = 60 + (i % 7) * 80, 160 + (i // 7) * 110; d.text((x, y), str(i + 1), font=ImageFont.truetype(fb, 40), fill=(40, 26, 16), anchor='mm')
            if i + 1 in (3, 9, 17, 24): d.ellipse((x - 34, y - 34, x + 34, y + 34), outline=(150, 20, 16), width=6); d.text((x + 10, y + 34), 'BANK', font=ImageFont.truetype(fb, 16), fill=(150, 20, 16), anchor='mm')
        im.save(cal)
    PR.poster('calendar', cal, (-S - 9.4 + .12, -2 + 1.2, 1.9), (math.pi / 2, 0, -math.pi / 2), size=(.55, .7))
    def cam(t):
        w = bone_pos(sher, 'RightHand'); h = head_of(sher)
        tgt = h.lerp(w, ease((t - 1.6) / 1.8)); s = K([(0, 1.4), (sh.dur, .5)], t)
        return (framed(tgt, facing(sher), 25, 10, s * 1.8, 40, ch=sher), tgt, 40, 0, tgt, .008)
    sh.camera(cam, fstop=2.0)


def s_suspicious(sh):
    """18.85-20.85 'Jack became suspicious.'  Close-up, his eyes narrow; slow push."""
    setup(sh, 'day', 28, 110, veg=.4)
    jack, = sh.cast('JACK')
    sh.actor(jack, [CA.Act(0, '77_02', 2.0, 6, loc=(S - W_ * .5, -1.0, DECK), yaw=-90, lock_root=True)], face=[(0, 'idle'), (.7, 'suspicious')], look=lambda t: (-S, -2.0, 2.0))
    cu(sh, jack, angle=35, elev=2, size=(.7, .45), lens=60)


def s_nights(sh):
    """20.85-24.25 'So he spent three nights watching the sheriff's office.'  Night, Jack in the shadow of a porch across the street,
    the lamp in the sheriff's window; moon and stars move (time passing)."""
    setup(sh, 'night', 20, 300, veg=.4); night_lights()
    jack, = sh.cast('JACK')
    sh.actor(jack, [CA.Act(0, '86_09', 9.0, 4, loc=(S - W_ * .6, -2.4, DECK), yaw=-90, lock_root=True)], face=[(0, 'suspicious')], look=lambda t: (-S, -2, 1.8))
    T.lantern('sher_window', (-S - .4, -2 + 2.3, 1.5), energy=40)
    def cam(t):
        return (Vector((S - W_ - .3, -6.5, 1.4)).lerp(Vector((S - W_ - .6, -4.4, 1.5)), ease(t / sh.dur)), Vector((-S, -1.0, 1.9)), 30, 0, head_of(jack), .006)
    sh.camera(cam, fstop=2.8)


def s_fourth(sh):
    """24.25-25.55 'And on the fourth night,'  crane down from the moonlit sky onto the dark street."""
    setup(sh, 'night', 20, 300, veg=.6); night_lights()
    def cam(t):
        u = t / sh.dur
        return (Vector((3, -18, 14)).lerp(Vector((1.5, -10, 2.2)), ease(u)), Vector((0, 20, 12)).lerp(Vector((-S, 12, 2.5)), ease(u)), 22, 0, None, .01)
    sh.camera(cam, fstop=8)


def s_unbelievable(sh):
    """25.55-28.05 'he saw something unbelievable.'  Jack's eyes go wide; fast push-in."""
    setup(sh, 'night', 20, 300, veg=.3); night_lights()
    jack, = sh.cast('JACK')
    sh.actor(jack, [CA.Act(0, '86_09', 9.5, 4, loc=(S - W_ * .6, -2.4, DECK), yaw=90, lock_root=True), CA.Act(.6, '79_73', 3.4, 4, loc=(S - W_ * .6, -2.4, DECK), yaw=60, lock_root=True)],
             face=[(0, 'suspicious'), (.6, 'shock')], look=lambda t: (-S, 12, 1.6))
    cu(sh, jack, angle=25, elev=0, size=(1.4, .6), lens=50, fstop=1.8)


def s_sneak(sh):
    """28.05-30.55 'The sheriff quietly walked into the bank,'  low angle: the sheriff creeps across the street to the bank door with a lantern."""
    setup(sh, 'night', 20, 300, veg=.5); night_lights()
    sher, = sh.cast('SHER')
    sh.actor(sher, [CA.Act(0, '17_03', 6.0, 4, loc=(2.0, 6.0, 0), yaw=-50 - 0, speed=1.0)], face=[(0, 'suspicious'), (1.4, 'smirk')])
    lan = T.lantern('sher_lantern', (0, 0, 0), c='Props', energy=25)
    lan_parts = [o for o in bpy.data.objects if o.name.startswith('sher_lantern')]
    def carry(t):
        p = bone_pos(sher, 'LeftHand') + Vector((0, 0, -.15))
        for o in lan_parts: o.location = p + (Vector((0, 0, .12)) if o.name.endswith('_t') else Vector())
    sh.updates.append(carry)
    def cam(t):
        hp = bone_pos(sher, 'Hips')
        return (Vector((-1.5, 4.5, .35)), hp + Vector((0, 0, .4)), 24, 0, hp, .01)
    sh.camera(cam, fstop=2.8)


def s_vault(sh):
    """30.55-31.55 'opened the vault,'  insert: the vault wheel spins and the heavy door swings open, gold light spills out."""
    o = setup(sh, 'night', 20, 300, town=False, interior='bank', haze=False)
    vd = bpy.data.objects['vault_door']; c = o['vault_center']
    vd.rotation_mode = 'XYZ'; base = vd.rotation_euler.copy()
    pivot = Vector((c.x + .2, c.y - 1.25, c.z))
    def swing(t):
        a = ease((t - .2) / .75) * math.radians(115)
        vd.rotation_euler = (base.x + t * 2.4, base.y, base.z)                    # wheel+door turn (spoke children follow)
        vd.location = pivot + Matrix.Rotation(-a, 3, 'Z') @ (Vector((c.x + .6 - .4, c.y, c.z)) - pivot)
    sh.updates.append(swing)
    T.lantern('vault_lamp', (c.x + 1.6, c.y - 1.2, 1.3), c='Interior', energy=35)
    def cam(t):
        return (Vector((c.x + 3.4, c.y + 2.2, 1.9)).lerp(Vector((c.x + 2.9, c.y + 1.7, 1.8)), ease(t / sh.dur)), c + Vector((-.2, -.5, -.15)), 24, 0, c, .008)
    sh.camera(cam, fstop=4.0); sh.keylight(30.0, (1, .85, .65))


def s_gold(sh):
    """31.55-34.15 'and started filling his bags with gold.'  The sheriff stuffs gold bars into sacks, greedy grin; camera arcs."""
    o = setup(sh, 'night', 20, 300, town=False, interior='bank', haze=False)
    c = o['vault_center']; open_vault(o); sher, = sh.cast('SHER'); sh.keylight(20.0, (1, .85, .65))
    sh.actor(sher, [CA.Act(0, '80_08', 1.8, 6, loc=(c.x + 1.6, c.y - .1, .2), yaw=-90, lock_root=True)], face=[(0, 'grin')], look=lambda t: (c.x - .6, c.y, .9))
    bar = PR.gold_bar('held_bar', (0, 0, 0))
    sh.updates.append(lambda t: setattr(bar, 'location', bone_pos(sher, 'RightHand') + Vector((0, -.05, -.04))))
    for k in range(3): PR.sack(f'sack{k}', (c.x + 1.25 + k * .3, c.y - .75 - (k % 2) * .25, .42), fill=.6 + .2 * k)
    T.lantern('vault_lamp', (c.x + 1.4, c.y - 1.0, 1.2), c='Interior', energy=35)
    def cam(t):
        h = head_of(sher, -.1); f = facing(sher)
        return (framed(h, f, K([(0, -70), (sh.dur, -40)], t), 4, 2.7, 28, ch=sher), h + Vector((0, 0, -.15)), 28, 0, h, .008)
    sh.camera(cam, fstop=2.4)


def s_draw(sh):
    """34.15-36.65 'Jack immediately pulled out his revolver.'  At the bank doorway: holster close-up, whip up as the gun comes out."""
    o = setup(sh, 'night', 20, 300, town=True, interior='bank', veg=.2); night_lights()
    jack, = sh.cast('JACK')
    jp = Vector((-S - 2.0, 11.3, .2))
    sh.actor(jack, [CA.Act(0, '79_96', 1.2, 6, loc=jp, yaw=-90, lock_root=True)], face=[(0, 'determined'), (1.4, 'angry')])
    gun = PR.revolver('jgun'); gun.scale = (1.4, 1.4, 1.4)
    def draw(t):
        if t > .9: hold_gun(jack, gun, sher=None)
        else: gun.location = bone_pos(jack, 'Hips') + facing(jack).cross(Vector((0, 0, 1))) * -.28 + Vector((0, 0, -.05))
    sh.updates.append(draw)
    def cam(t):
        hip = bone_pos(jack, 'RightHand'); h = head_of(jack)
        tgt = hip.lerp(h, ease((t - .8) / .7)); s = K([(0, .7), (.8, .7), (1.5, 1.1), (sh.dur, 1.0)], t)
        return (framed(tgt, facing(jack), 35, K([(0, -10), (1.5, 0)], t), s * 1.6, 35, ch=jack), tgt, 35, 0, tgt, .01)
    sh.camera(cam, fstop=2.2); sh.keylight(22.0, (1, .85, .65))


def hold_gun(ch, gun, sher=None):
    h = bone_pos(ch, 'RightHand'); f = facing(ch) if sher is None else (head_of(sher) - h).normalized()
    gun.location = h; gun.rotation_mode = 'QUATERNION'; gun.rotation_quaternion = f.to_track_quat('-Y', 'Z')


def open_vault(o, a=math.radians(165)):
    vd = bpy.data.objects['vault_door']; c = o['vault_center']; pivot = Vector((c.x + .2, c.y - 1.25, c.z))
    vd.location = pivot + Matrix.Rotation(-a, 3, 'Z') @ (Vector((c.x + .2, c.y, c.z)) - pivot); vd.rotation_euler.z += -a


def _bank_pair(sh, jack_face, sher_face, sher_turn=None, jack_talk=None, sher_talk=None, sher_clip=('80_08', 4.2), facing=False):
    """Jack in the bank doorway side (+X) aiming at the sheriff, who works at the vault (-X)."""
    o = setup(sh, 'night', 20, 300, town=False, interior='bank', haze=False)
    c = o['vault_center']; open_vault(o); jack, sher = sh.cast('JACK', 'SHER')
    sh.keylight(30.0, (1, .85, .65))
    jp = Vector((c.x + 3.7, c.y - .4, .2)); spos = Vector((c.x + 1.6, c.y - .1, .2))
    sh.actor(jack, [CA.Act(0, '79_96', 2.4, 6, loc=jp, yaw=-90, lock_root=True, speed=.3)], face=jack_face, talk=jack_talk, look=lambda t: head_of(sher))
    if facing: acts = [CA.Act(0, '77_02', 2.0, 6, loc=spos, yaw=90, lock_root=True)]
    else: acts = [CA.Act(0, sher_clip[0], sher_clip[1], 6, loc=spos, yaw=-90, lock_root=True, speed=.15)]
    if sher_turn is not None: acts.append(CA.Act(sher_turn, '69_18', 2.2, 6, loc=spos, yaw=-90, lock_root=True, speed=1.0, blend=.5))
    sh.actor(sher, acts, face=sher_face, talk=sher_talk, look=(lambda t: head_of(jack)) if (facing or sher_turn is not None) else None)
    gun = PR.revolver('jgun'); gun.scale = (1.4, 1.4, 1.4)
    sh.updates.append(lambda t: hold_gun(jack, gun, sher))
    bar = PR.gold_bar('held_bar', (0, 0, 0)); sh.updates.append(lambda t: setattr(bar, 'location', bone_pos(sher, 'RightHand') + Vector((0, -.05, -.04))))
    for k in range(3): PR.sack(f'sack{k}', (c.x + 1.25 + k * .3, c.y - .75 - (k % 2) * .25, .42), fill=.6 + .2 * k)
    T.lantern('vault_lamp', (c.x + 1.4, c.y - 1.0, 1.2), c='Interior', energy=35)
    return c, jack, sher


def s_handsup(sh):
    """36.65-38.10 '"Hands up, Sheriff!"'  over the gun barrel onto the sheriff's back; Jack shouts."""
    c, jack, sher = _bank_pair(sh, [(0, 'shout')], [(0, 'grin')], jack_talk=[(0.05, 1.1, 1.0)])
    def cam(t):
        s_ = head_of(sher); j = bone_pos(jack, 'RightHand'); d = (j - s_); d.z = 0; d.normalize()
        p = j + d * 1.75 + Vector((0, 0, .5)) + Vector((-d.y, d.x, 0)) * .8
        return (p, s_ + Vector((0, 0, -.35)), K([(0, 26), (sh.dur, 32)], t), -3, s_, .012)
    sh.camera(cam, fstop=2.2)


def s_froze(sh):
    """38.10-39.65 'The sheriff froze.'  His face from the front: grin drops into shock, sweat; slow push."""
    c, jack, sher = _bank_pair(sh, [(0, 'determined')], [(0, 'grin'), (.25, 'shock'), (1.0, 'fear')], sher_clip=('77_02', 2.0))
    cu(sh, sher, angle=12, elev=3, size=(.8, .42), lens=55)


def s_turn(sh):
    """39.65-42.55 'Then he slowly turned around and said...'  the sheriff turns to face Jack; fear becomes a smirk."""
    c, jack, sher = _bank_pair(sh, [(0, 'determined'), (2.0, 'suspicious')], [(0, 'fear'), (1.6, 'idle'), (2.3, 'smirk')], sher_turn=.3, sher_clip=('77_02', 2.0))
    def cam(t):
        h = head_of(sher); j = head_of(jack); d = j - h; d.z = 0; d.normalize()
        side = Vector((-d.y, d.x, 0))
        p = h + d * .9 + side * 1.9 + Vector((0, 0, .1))
        return (p, h.lerp(j, .3), 28, 0, h, .006)
    sh.camera(cam, fstop=2.4)


def s_arrest(sh):
    """42.55-44.85 '"You're under arrest, cowboy."'  the sheriff, smug, faces the gun; push in."""
    c, jack, sher = _bank_pair(sh, [(0, 'suspicious'), (1.0, 'shock')], [(0, 'smirk'), (.9, 'grin')], sher_talk=[(.15, 1.6, .8)], facing=True)
    cu(sh, sher, angle=-20, elev=0, size=(.9, .5), lens=50)


def s_poster_jack(sh):
    """44.85-47.30 'Turns out, the sheriff had already reported Jack...'  day: Jack's WANTED poster nailed by the sheriff's door; push in."""
    setup(sh, 'day', 28, 110, veg=.4)
    img = poster_img('jack')
    PR.poster('poster_j', img, (-S + .06, -2 + 1.2, 1.85), (math.pi / 2, 0, math.pi / 2), size=(.6, .84), curl=.3)
    for k in range(3): PR.poster(f'old{k}', img if k == 9 else poster_img('jack'), (-S + .05, -2 + 1.9 + k * .02, 1.4 + k * .9), (math.pi / 2, 0, math.pi / 2 + .05 * k), size=(.4, .55)) if k == 9 else None
    def cam(t):
        p = Vector((-S + 3.2, -2 + 1.2, 1.9)).lerp(Vector((-S + .9, -2 + 1.2, 1.88)), ease(t / sh.dur))
        return (p, (-S, -2 + 1.2, 1.85), 35, 0, (-S, -2 + 1.2, 1.85), .006)
    sh.camera(cam, fstop=4.0)


def s_reading(sh):
    """47.30-49.75 '...as the town's most wanted criminal.'  townsfolk crowd around the poster, point and talk."""
    setup(sh, 'day', 28, 110, veg=.4)
    PR.poster('poster_j', poster_img('jack'), (-S + .06, -2 + 1.2, 1.85), (math.pi / 2, 0, math.pi / 2), size=(.6, .84), curl=.3)
    people = sh.crowd(6, None, seed=5)
    for k, ch in enumerate(people):
        x = -S + .9 + (k % 3) * .7; y = -2 + .2 + (k // 3) * 1.2 + (k % 3) * .35
        sh.actor(ch, [CA.Act(0, ['80_48', '77_02', '79_74', '77_05', '80_44', '80_48'][k], 1.2 + k * .6, 6, loc=(x, y, DECK), yaw=-90 + (k - 2.5) * 10, lock_root=True)], face=[(0, ['angry', 'shock', 'shout', 'suspicious', 'worry', 'angry'][k])], look=lambda t: (-S, -.8, 1.85))
    def cam(t):
        return (Vector((-S + 5.6, -6.6, 2.1)).lerp(Vector((-S + 4.8, -5.2, 2.0)), ease(t / sh.dur)), (-S + .9, -1.0, 1.5), 26, 0, None, .01)
    sh.camera(cam, fstop=4.0); sh.keylight(30.0)


def s_neverseen(sh):
    """49.75-53.85 'And since nobody had ever seen the real sheriff outside his office...'  dusk: the office window lit, a silhouette behind
    the blind; townsfolk pass by and never look; slow truck along the boardwalk."""
    setup(sh, 'day', 28, 110, veg=.4)
    T.lantern('office_glow', (-S - .5, -2 + 2.3, 1.6), energy=140)
    sher, = sh.cast('SHER')
    sh.actor(sher, [CA.Act(0, '77_02', 2, 6, loc=(-S - .9, -2 + 2.3, .2), yaw=90, lock_root=True)], face=[(0, 'smirk')])
    people = sh.crowd(5, None, seed=6)
    for k, ch in enumerate(people):
        sh.actor(ch, [CA.Act(0, '82_11' if k % 2 else '82_09', 2.2 if k % 2 else 6.8, 6, loc=(-2.6 - (k % 2) * .9, -7 + k * 2.4 if k % 2 == 0 else 5 - k * 2.0, 0), yaw=180 if k % 2 == 0 else 0, speed=.85)], face=[(0, ['idle', 'chat', 'watch'][k % 3])])
    def cam(t):
        return (Vector((1.2, -11.0, 1.9)).lerp(Vector((.6, -9.0, 1.85)), ease(t / sh.dur)), (-S + .3, -1.0, 1.7), 30, 0, (-S, -1.0, 1.7), .008)
    sh.camera(cam, fstop=2.8); sh.keylight(16.0, (1, .8, .6))


def _surround(sh, mood='sunset', jack_face=None, sher_present=False, crowd_face='angry', n=12, jack_clip=('77_02', 2.0), seed=7):
    setup(sh, mood, 6, 250, veg=.5)
    jack, = sh.cast('JACK'); jp = Vector((0, 8, 0))
    sh.actor(jack, [CA.Act(0, jack_clip[0], jack_clip[1], 6, loc=jp, yaw=0, lock_root=True)], face=jack_face or [(0, 'worry')])
    people = sh.crowd(n, None, seed=seed); acts = []
    for k, ch in enumerate(people):
        a = k / n * math.tau + .3; r = 2.4 + (k % 3) * .6
        x, y = jp.x + math.cos(a) * r, jp.y + math.sin(a) * r
        yaw = math.degrees(math.atan2(-(jp.x - x), (jp.y - y))) + 180
        acts.append(sh.actor(ch, [CA.Act(0, ['80_48', '79_74', '80_48', '77_02'][k % 4], 1.0 + (k * .53) % 3, 6, loc=(x, y, 0), yaw=yaw, lock_root=True)],
                             face=[(0, crowd_face if isinstance(crowd_face, str) else crowd_face[k % len(crowd_face)])], look=lambda t: head_of(jack)))
    return jack, jp, people, acts


def s_believed(sh):
    """53.85-56.85 'The entire town believed Jack was the robber.'  Jack in the middle of an angry crowd; crane up and around."""
    jack, jp, people, acts = _surround(sh, 'sunset', [(0, 'worry'), (1.5, 'fear')], crowd_face=['angry', 'shout', 'angry'])
    def cam(t):
        a = math.radians(K([(0, 200), (sh.dur, 250)], t)); r = K([(0, 3.4), (sh.dur, 5.0)], t)
        return (jp + Vector((math.cos(a) * r, math.sin(a) * r, K([(0, 1.7), (sh.dur, 4.5)], t))), head_of(jack) + Vector((0, 0, -.2)), 24, 0, head_of(jack), .01)
    sh.camera(cam, fstop=4.0)


def s_trick(sh):
    """56.85-59.45 'But Jack had one final trick.'  close: his worry turns into a sly smile; he looks at camera."""
    jack, jp, people, acts = _surround(sh, 'sunset', [(0, 'worry'), (.8, 'smirk')], crowd_face='angry', n=8)
    cu(sh, jack, angle=10, elev=-4, size=(.85, .45), lens=55)


def s_pullposter(sh):
    """59.45-62.20 'He pulled out the sheriff's own wanted poster...'  Jack pulls a folded paper from his vest and holds it up to the crowd."""
    jack, jp, people, acts = _surround(sh, 'sunset', [(0, 'smirk'), (1.6, 'determined')], crowd_face=['suspicious', 'angry', 'confused' if False else 'suspicious'], n=10, jack_clip=('80_08', 4.6))
    img = poster_img('sher')
    pst = PR.poster('poster_s', img, (0, 0, 0), (math.pi / 2, 0, 0), size=(.45, .63))
    def hold(t):
        hr = bone_pos(jack, 'RightHand'); hl = bone_pos(jack, 'LeftHand'); m = (hr + hl) / 2
        k = ease((t - .9) / .9); pst.location = m + Vector((0, -.06, .15)); s = .25 + .75 * k; pst.scale = (s * .45, s * .63, 1)
        pst.rotation_euler = (math.pi / 2, 0, 0)
    sh.updates.append(hold)
    def cam(t):
        h = head_of(jack)
        return (jp + Vector(K([(0, (1.0, -3.6, 1.5)), (sh.dur, (.6, -2.4, 1.6))], t)), h + Vector((0, 0, -.3)), 32, 0, h, .01)
    sh.camera(cam, fstop=3.2)


def s_face(sh):
    """62.20-64.20 'Which showed the sheriff's face.'  insert: the poster fills the frame - the sheriff's portrait, $5,000; slow push."""
    setup(sh, 'sunset', 6, 250, veg=.3)
    img = poster_img('sher')
    PR.poster('poster_s', img, (0, 8, 1.7), (math.pi / 2, 0, 0), size=(.45, .63), curl=.2)
    def cam(t):
        return (Vector((0, 8 - K([(0, 1.0), (sh.dur, .62)], t), 1.72)), (0, 8, 1.72), 50, 0, (0, 8, 1.7), .004)
    sh.camera(cam, fstop=5.6)


def s_realised(sh):
    """64.20-67.05 'And suddenly, the whole town realised...'  the crowd gasps and turns; whip-pan to the sheriff."""
    jack, jp, people, acts = _surround(sh, 'sunset', [(0, 'determined')], crowd_face='shock', n=12)
    sher, = sh.cast('SHER'); sp = Vector((-3.2, 13.5, 0))
    sh.actor(sher, [CA.Act(0, '77_02', 1, 6, loc=sp, yaw=200, lock_root=True)], face=[(0, 'smirk'), (1.6, 'shock')])
    for a in acts: a.look = (lambda t, a=a: head_of(jack) if t < 1.1 else head_of(sher))
    def cam(t):
        h = head_of(sher); j = jp + Vector((0, 0, 1.6))
        tgt = j.lerp(h, ease((t - 1.6) / .5))
        return (jp + Vector((2.6, -2.8, 1.8)), tgt, K([(0, 26), (1.6, 26), (2.2, 45)], t), 0, tgt, .015)
    sh.camera(cam, fstop=4.0)


def s_allalong(sh):
    """67.05-69.72 'Their sheriff was the criminal all along.'  the sheriff is surrounded, sweating; camera pulls up and back into a wide
    golden shot of the whole town."""
    setup(sh, 'sunset', 5, 250, veg=1.0)
    sher, jack = sh.cast('SHER', 'JACK'); sp = Vector((-3.2, 13.5, 0))
    sh.actor(sher, [CA.Act(0, '79_73', 3.4, 6, loc=sp, yaw=200, lock_root=True)], face=[(0, 'fear')])
    sh.actor(jack, [CA.Act(0, '79_96', 2.4, 6, loc=sp + Vector((1.2, -2.6, 0)), yaw=-25, lock_root=True, speed=.2)], face=[(0, 'smirk')], look=lambda t: head_of(sher))
    people = sh.crowd(12, None, seed=8)
    for k, ch in enumerate(people):
        a = k / 12 * math.tau; r = 2.2 + (k % 3) * .5; x, y = sp.x + math.cos(a) * r, sp.y + math.sin(a) * r
        if (Vector((x, y, 0)) - (sp + Vector((1.2, -2.6, 0)))).length < .9: continue
        yaw = math.degrees(math.atan2(-(sp.x - x), (sp.y - y))) + 180
        sh.actor(ch, [CA.Act(0, ['80_48', '79_74'][k % 2], 1.5 + k * .3, 6, loc=(x, y, 0), yaw=yaw, lock_root=True)], face=[(0, 'angry')], look=lambda t: head_of(sher))
    def cam(t):
        u = ease(t / sh.dur)
        return (sp + Vector((1.5, -3.0, 1.7)).lerp(Vector((10, -38, 22)), u), (sp + Vector((0, 0, 1.4))).lerp(Vector((0, 15, 3)), u), K([(0, 32), (sh.dur, 22)], t), 0, None, .01)
    sh.camera(cam, fstop=5.6)


SHOTS = {k[2:]: v for k, v in list(globals().items()) if k.startswith('s_') and callable(v)}


def rss(tag):
    import resource; print('RSS', tag, resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1024, 'MB', flush=True)


def main(shots=None):
    a = sys.argv[sys.argv.index('--') + 1:]; mode, sid = a[0], a[1]
    sh = Shot(sid); (shots or SHOTS)[sid](sh); rss('built'); sh.populate(); rss('extras'); sh.clear_camera(); sh.lod(); rss('lod')
    if sh.key is None and sh.cam is not None:            # soft camera-side fill for faces in the shade of porches
        sh.at(sh.dur / 2); r = sh.cam[1](sh.dur / 2)
        if (Vector(r[1]) - Vector(r[0])).length < 10: sh.keylight(10.0 if getattr(sh, 'mood', 'day') != 'night' else 6.0)
    if os.environ.get('NOCHARHAIR'):
        for o in bpy.data.objects:
            for md in o.modifiers:
                if md.type == 'PARTICLE_SYSTEM' and any(o.name.startswith(p) for p in ('JACK', 'SHER', 'T0', 'T1')): md.show_render = False
    if os.environ.get('NOGRASS'):
        for o in bpy.data.objects:
            if o.name.startswith('grass_ground'):
                for md in o.modifiers: md.show_render = False
    sc = bpy.context.scene
    if mode == 'still':
        t = float(a[3]) if len(a) > 3 else sh.dur / 2
        sh.at(t); rss('posed'); dg = bpy.context.evaluated_depsgraph_get(); dg.update(); rss('depsgraph')
        print('OBJECTS', len(bpy.data.objects), 'MESHES', len(bpy.data.meshes), 'IMAGES', len(bpy.data.images), sum(i.size[0] * i.size[1] for i in bpy.data.images) // 1000000, 'Mpx', flush=True)
        sc.render.filepath = os.path.abspath(a[2]); _t0 = time.time(); bpy.ops.render.render(write_still=True); print('RTIME', round(time.time() - _t0, 1), flush=True); rss('rendered'); print('RENDERED', sid, t)
    else:
        f0, f1, out = int(a[2]), int(a[3]), a[4]; os.makedirs(out, exist_ok=True); g0 = round(sh.t0 * FPS)
        for f in range(f0, f1 + 1):
            sh.at((f - 1) / FPS); sc.render.filepath = os.path.join(os.path.abspath(out), f'f_{g0 + f:05d}.png'); bpy.ops.render.render(write_still=True)
            print('frame', g0 + f, flush=True)


if __name__ == '__main__':
    main()
