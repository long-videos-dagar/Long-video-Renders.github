"""Cast library: build every character once into cast.blend (python3 cast.py -- build <out.blend>),
then shots append them (load) and clone them for crowds. Each character lives in its own collection 'C_<id>'.

Loaded characters are driven per frame by Actor: mocap clip timeline (with blends), expression track, blinks,
lip-sync, props held in the hands, look-at for the head."""
import bpy, os, sys, math, random
from mathutils import Vector, Matrix, Quaternion
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'real'))
import mocap as M

CAST_IDS = ['JACK', 'SHER'] + [f'T{i:02d}' for i in range(14)]
CROWD_PICK = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 13, 16, 19]          # preset seeds giving a good mix


def build(out):
    import realchar as R
    bpy.ops.wm.read_factory_settings(use_empty=True); R.init()
    specs = [('JACK', R.JACK), ('SHER', R.SHERIFF)] + [(f'T{i:02d}', R.crowd_preset(s)) for i, s in enumerate(CROWD_PICK)]
    for cid, p in specs:
        col = bpy.data.collections.new('C_' + cid); bpy.context.scene.collection.children.link(col)
        per = R.Person(cid, p, coll_name='C_' + cid)
        per.rig['cid'] = cid; per.rig['units'] = ','.join(per.units); per.rig['body'] = per.body.name
        per.rig['eye_c'] = list(per.eye_c); per.rig['woman'] = p['gender'] < .5
        if hasattr(per, 'gun'): per.rig['gun'] = per.gun.name
        for o in list(bpy.context.scene.collection.objects):     # strays (e.g. hat parts) belong to this character
            if o.parent is not None or o.name.startswith(cid):
                bpy.context.scene.collection.objects.unlink(o); col.objects.link(o)
        print('built', cid, len(col.objects))
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(out), compress=True)


class Char:
    """a loaded (or cloned) character"""
    def __init__(self, col):
        self.col = col
        self.rig = next(o for o in col.objects if o.type == 'ARMATURE')
        self.body = next(o for o in col.objects if o.type == 'MESH' and o.name.endswith('_body'))
        self.cid = self.rig.get('cid', col.name[2:])
        kb = self.body.data.shape_keys.key_blocks if self.body.data.shape_keys else []
        self.keys = {k.name: k for k in kb}
        self.units = self.rig.get('units', '').split(',')
        self.rt = M.Retarget(self.rig)
        self.gun = bpy.data.objects.get(self.rig.get('gun', '')) if self.rig.get('gun') else None
        self.held = []

    def unit_key(self, u):
        for n, k in self.keys.items():
            if u in n: return k
        return None

    def set_expression(self, mix, blink=0.0, jaw=0.0):
        import realchar as R
        tot = {}
        for e, w in mix.items():
            for u, a in R.EXPRESSIONS[e].items(): tot[u] = tot.get(u, 0.0) + a * w
        tot['eye-left-closure'] = max(tot.get('eye-left-closure', 0), blink); tot['eye-right-closure'] = max(tot.get('eye-right-closure', 0), blink)
        tot['mouth-open'] = min(1.0, tot.get('mouth-open', 0) + jaw)
        for u in self.units:
            k = self.unit_key(u)
            if k: k.value = min(1.0, tot.get(u, 0.0))

    def hide(self, h=True):
        for o in self.col.all_objects: o.hide_render = h; o.hide_viewport = h


def load(path, ids):
    """append characters ids from cast.blend; returns {id: Char}"""
    with bpy.data.libraries.load(os.path.abspath(path), link=False) as (src, dst):
        dst.collections = [c for c in src.collections if c[2:] in ids]
    out = {}
    for c in dst.collections:
        if c is None: continue
        bpy.context.scene.collection.children.link(c); out[c.name[2:]] = Char(c)
    return out


def clone(ch, new_id):
    """cheap copy sharing mesh/armature data (own pose, own transforms) for crowds"""
    col = bpy.data.collections.new('C_' + new_id); bpy.context.scene.collection.children.link(col)
    m = {}
    for o in ch.col.objects:
        c = o.copy(); m[o] = c; col.objects.link(c)
    for o, c in m.items():
        if o.parent in m: c.parent = m[o.parent]
        for md in c.modifiers:
            if md.type == 'ARMATURE' and md.object in m: md.object = m[md.object]
    rig = m[ch.rig]; rig['cid'] = new_id
    nc = Char(col); return nc


# ------------------------------------------------------------------ performance (per frame)
class Act:
    """one action segment: clip from src_t0 for dur seconds, starting at shot time t, placed at loc/yaw"""
    def __init__(self, t, clip, src_t0, dur, loc=(0, 0, 0), yaw=0.0, speed=1.0, lock_root=False, blend=.35, mirror=False):
        self.t, self.clip, self.s0, self.dur, self.loc, self.yaw, self.speed, self.lock, self.blend = t, clip, src_t0, dur, loc, yaw, speed, lock_root, blend


class Actor:
    def __init__(self, ch, acts, face=None, look=None, talk=None, blink_seed=0, props=None, rest_pose=None, level=True, level_deg=-6.0):
        self.level, self.level_deg = level, level_deg
        self.ch = ch; self.acts = sorted(acts, key=lambda a: a.t); self.face = face or [(0, 'neutral')]
        self.look = look; self.talk = talk or []; self.props = props or []
        r = random.Random(blink_seed); self.blinks = []; tt = r.uniform(.3, 2.0)
        while tt < 200: self.blinks.append(tt); tt += r.uniform(2.0, 5.0)

    def _pose_of(self, a, t):
        src = M.BVH.load(a.clip)
        st = a.s0 + (t - a.t) * a.speed
        st = max(a.s0, min(st, src.dur - .05))
        return self.ch.rt.pose(src, st, place=a.loc, yaw=a.yaw, t0=a.s0, lock_root=a.lock)

    def apply(self, t):
        cur = None; prev = None
        for i, a in enumerate(self.acts):
            if a.t <= t: cur = i
        if cur is None: cur = 0
        a = self.acts[cur]; pose = self._pose_of(a, t)
        if cur > 0 and t - a.t < a.blend:
            pa = self.acts[cur - 1]; pp = self._pose_of(pa, t)
            u = (t - a.t) / a.blend; u = u * u * (3 - 2 * u)
            pose = M.blend(pp, pose, u)
        rots, hips = pose
        if self.look:                              # head/neck turn toward a target, layered on the mocap
            tgt = self.look(t)
            if tgt is not None and 'Hips' in rots:
                inv = self.ch.rt.bones['Hips'].matrix_local.to_3x3().inverted()
                fwd = rots['Head'] @ self.ch.rt.bones['Head'].matrix_local.to_3x3().inverted() @ Vector((0, -1, 0))
                hpos = hips + Vector((0, 0, .62)); d = Vector(tgt) - hpos
                f2, d2 = Vector((fwd.x, fwd.y)), Vector((d.x, d.y))
                if f2.length > 1e-4 and d2.length > 1e-4:
                    ang = max(-1.2, min(1.2, math.atan2(f2.x * d2.y - f2.y * d2.x, f2.dot(d2))))
                    for b_, k in (('Spine2', .2), ('Neck', .55), ('Head', 1.0)):
                        if b_ in rots: rots[b_] = Matrix.Rotation(ang * k, 3, 'Z') @ rots[b_]
        if self.level and 'Head' in rots:            # keep the gaze near the horizon (many mocap takes look at the floor)
            hb = self.ch.rt.bones['Head']; f = rots['Head'] @ hb.matrix_local.to_3x3().inverted() @ Vector((0, -1, 0))
            pitch = math.asin(max(-1, min(1, f.z / max(f.length, 1e-6))))
            want = math.radians(self.level_deg)
            if pitch < want:
                ax = Vector((f.x, f.y, 0)).cross(Vector((0, 0, 1)))
                if ax.length > 1e-6:
                    ax.normalize(); corr = (want - pitch)
                    for b_, k in (('Spine2', .2), ('Neck', .55), ('Head', 1.0)):
                        if b_ in rots: rots[b_] = Matrix.Rotation(corr * k, 3, ax) @ rots[b_]
        self.ch.rt.apply(rots, hips); M.relax_fingers(self.ch.rig)
        # face
        import realchar as R
        e0, e1, u = _track(self.face, t)
        mix = {e0: 1 - u, e1: u} if e0 != e1 else {e0: 1.0}
        bl = 0.0
        for b in self.blinks:
            if b <= t < b + .16: bl = 1 - abs((t - b) - .08) / .08
        jaw = 0.0
        for (t0, t1, amp) in self.talk:
            if t0 <= t <= t1: jaw = max(jaw, .25 + .35 * abs(math.sin((t - t0) * 17.0)) * amp)
        self.ch.set_expression(mix, blink=bl, jaw=jaw)
        for pr in self.props: pr(self, t)


def _track(seq, t):
    """expression at time t: hold, then a quick .18 s change on the beat"""
    seq = sorted(seq, key=lambda k: k[0]); i = 0
    for j, (tj, _) in enumerate(seq):
        if tj <= t: i = j
    if i == 0 and t < seq[0][0]: return seq[0][1], seq[0][1], 0.0
    if i > 0 and t - seq[i][0] < .18:
        u = (t - seq[i][0]) / .18; return seq[i - 1][1], seq[i][1], u * u * (3 - 2 * u)
    return seq[i][1], seq[i][1], 0.0


def hold(obj, bone='RightHand', offset=Matrix.Identity(4)):
    """prop follows a hand bone"""
    def f(actor, t):
        rig = actor.ch.rig; pb = rig.pose.bones['mixamorig:' + bone]
        bpy.context.view_layer.update()
        obj.matrix_world = rig.matrix_world @ pb.matrix @ offset
    return f


if __name__ == '__main__':
    a = sys.argv[sys.argv.index('--') + 1:]
    if a[0] == 'build': build(a[1])


# ------------------------------------------------------------------ riding
def _aim(rest3, rest_dir, new_dir):
    return rest_dir.normalized().rotation_difference(new_dir.normalized()).to_matrix() @ rest3


def _ik(a, tgt, l1, l2, pole):
    d = tgt - a; dist = max(1e-4, min(d.length, l1 + l2 - 1e-4)); dn = d.normalized()
    ca = (l1 * l1 + dist * dist - l2 * l2) / (2 * l1 * dist); ang = math.acos(max(-1, min(1, ca)))
    ax = dn.cross(pole); ax = ax.normalized() if ax.length > 1e-6 else Vector((1, 0, 0))
    return a + (Matrix.Rotation(ang, 3, ax) @ dn) * l1


def ride(ch, seatM, t, clip='77_02', bounce=Vector(), rein=True, face=None, sway=0.0):
    """seat the character on a saddle: upper body from a calm standing clip, thighs around the barrel, feet in the
    stirrups, hands forward on the reins. seatM: world matrix of the saddle seat (forward -Y)."""
    rt = ch.rt; src = M.BVH.load(clip)
    rots, hips = rt.pose(src, 1.0 + (t * .5) % (src.dur - 2.0), place=(0, 0, 0), yaw=0, t0=1.0, lock_root=True)
    B = rt.bones; hipz = B['Hips'].head_local.z
    ch.rig.matrix_world = seatM @ Matrix.Translation(Vector((0, .02, .08 - hipz)) + bounce) @ Matrix.Rotation(sway, 4, 'Y')
    hips = Vector((0, 0, hipz))
    rots['Hips'] = Matrix.Rotation(math.radians(3), 3, 'X') @ B['Hips'].matrix_local.to_3x3()
    for b_, a_ in (('Spine', 2), ('Spine1', 2), ('Spine2', 1)):
        if b_ in rots: rots[b_] = Matrix.Rotation(math.radians(a_), 3, 'X') @ rots[b_]
    for b_, a_ in (('Neck', -10), ('Head', -14)):
        if b_ in rots: rots[b_] = Matrix.Rotation(math.radians(a_), 3, 'X') @ rots[b_]        # pelvis tucked under
    pose = rt.apply(rots, hips)
    S = (ch.rig.matrix_world).inverted() @ seatM                                                     # seat frame in rig space
    for sd, s in (('Left', 1), ('Right', -1)):
        up, lo, ft = sd + 'UpLeg', sd + 'Leg', sd + 'Foot'
        a = pose[up].translation; l1 = (B[lo].head_local - B[up].head_local).length; l2 = (B[ft].head_local - B[lo].head_local).length
        foot = S @ Vector((s * .36, -.12, -.8))
        knee = _ik(a, foot, l1, l2, Vector((s * .7, -1.0, 0)))
        rots[up] = _aim(B[up].matrix_local.to_3x3(), B[lo].head_local - B[up].head_local, knee - a)
        rots[lo] = _aim(B[lo].matrix_local.to_3x3(), B[ft].head_local - B[lo].head_local, foot - knee)
        if (sd + 'ToeBase') in B: rots[ft] = _aim(B[ft].matrix_local.to_3x3(), B[sd + 'ToeBase'].head_local - B[ft].head_local, Vector((s * .15, -1, -.35)))
        if rein:
            sh, el, hd = sd + 'Arm', sd + 'ForeArm', sd + 'Hand'
            pose = rt.apply(rots, hips)
            a = pose[sh].translation; l1 = (B[el].head_local - B[sh].head_local).length; l2 = (B[hd].head_local - B[el].head_local).length
            hand = S @ Vector((s * .11, -.3, .1))
            elb = _ik(a, hand, l1, l2, Vector((s * .5, .8, -1)))
            rots[sh] = _aim(B[sh].matrix_local.to_3x3(), B[el].head_local - B[sh].head_local, elb - a)
            rots[el] = _aim(B[el].matrix_local.to_3x3(), B[hd].head_local - B[el].head_local, hand - elb)
            rots[hd] = rots[el] @ (B[el].matrix_local.to_3x3().inverted() @ B[hd].matrix_local.to_3x3())
    rt.apply(rots, hips); M.relax_fingers(ch.rig, 1.8 if rein else 1.0)
    if face: ch.set_expression(face)
    return ch.rig.matrix_world @ (rt.rig.pose.bones['mixamorig:RightHand'].head if False else Vector())
