"""CMU motion capture (BVH) -> MakeHuman/Mixamo rig retargeting, evaluated per frame (deterministic, no NLA).

Retarget method: for every mapped bone the source world rotation delta (pose * rest^-1) is applied to the target rest
orientation after aligning the rest bone directions (so a T-pose source drives an A-pose target correctly).
Root motion is scaled by the leg-length ratio; the clip is placed in the world with a position + heading.
Clips blend with slerp, which gives natural transitions between actions.
"""
import math, os, re
from mathutils import Matrix, Vector, Quaternion, Euler

CMU = os.environ.get('CMU_DIR', '/tmp/mocap/cmu-mocap/data')

MAP = {  # target (mixamorig:) <- source (CMU), source child joint used for the bone direction
    'Hips': ('Hips', None), 'Spine': ('LowerBack', 'Spine'), 'Spine1': ('Spine', 'Spine1'), 'Spine2': ('Spine1', 'Neck1'),
    'Neck': ('Neck1', 'Head'), 'Head': ('Head', None),
    'LeftShoulder': ('LeftShoulder', 'LeftArm'), 'LeftArm': ('LeftArm', 'LeftForeArm'), 'LeftForeArm': ('LeftForeArm', 'LeftHand'), 'LeftHand': ('LeftHand', 'LeftFingerBase'),
    'RightShoulder': ('RightShoulder', 'RightArm'), 'RightArm': ('RightArm', 'RightForeArm'), 'RightForeArm': ('RightForeArm', 'RightHand'), 'RightHand': ('RightHand', 'RightFingerBase'),
    'LeftUpLeg': ('LeftUpLeg', 'LeftLeg'), 'LeftLeg': ('LeftLeg', 'LeftFoot'), 'LeftFoot': ('LeftFoot', 'LeftToeBase'), 'LeftToeBase': ('LeftToeBase', None),
    'RightUpLeg': ('RightUpLeg', 'RightLeg'), 'RightLeg': ('RightLeg', 'RightFoot'), 'RightFoot': ('RightFoot', 'RightToeBase'), 'RightToeBase': ('RightToeBase', None),
}
TCHILD = {'Spine': 'Spine1', 'Spine1': 'Spine2', 'Spine2': 'Neck', 'Neck': 'Head', 'LeftShoulder': 'LeftArm', 'LeftArm': 'LeftForeArm', 'LeftForeArm': 'LeftHand',
          'LeftHand': 'LeftHandMiddle1', 'RightShoulder': 'RightArm', 'RightArm': 'RightForeArm', 'RightForeArm': 'RightHand', 'RightHand': 'RightHandMiddle1',
          'LeftUpLeg': 'LeftLeg', 'LeftLeg': 'LeftFoot', 'LeftFoot': 'LeftToeBase', 'RightUpLeg': 'RightLeg', 'RightLeg': 'RightFoot', 'RightFoot': 'RightToeBase'}
SEC = {}
Y2Z = Matrix(((1, 0, 0), (0, 0, -1), (0, 1, 0)))   # BVH Y-up (+Z forward)  ->  Blender Z-up (-Y forward)


class BVH:
    _cache = {}

    @classmethod
    def load(cls, name):
        if name not in cls._cache: cls._cache[name] = cls(name)
        return cls._cache[name]

    def __init__(self, name):
        sub = name.split('_')[0].zfill(3)
        path = name if os.path.exists(name) else os.path.join(CMU, sub, name + '.bvh')
        txt = open(path).read(); hier, mot = txt.split('MOTION')
        self.joints = []; stack = []; cur = None
        for line in hier.splitlines():
            t = line.split()
            if not t: continue
            if t[0] in ('ROOT', 'JOINT'):
                cur = dict(name=t[1], parent=stack[-1] if stack else None, off=None, ch=[], end=None); self.joints.append(cur)
            elif t[0] == 'End':
                cur = dict(name=None, endof=stack[-1])
            elif t[0] == '{': stack.append(len(self.joints) - 1 if cur.get('name') else ('end', stack[-1]))
            elif t[0] == '}': stack.pop()
            elif t[0] == 'OFFSET':
                v = Vector([float(x) for x in t[1:4]])
                if cur.get('name'): cur['off'] = v
                else: self.joints[cur['endof']]['end'] = v
            elif t[0] == 'CHANNELS': cur['ch'] = t[2:]
        # fix parents that point at 'end' tuples (never happens for joints, but be safe)
        for j in self.joints:
            if isinstance(j['parent'], tuple): j['parent'] = j['parent'][1]
        ml = mot.strip().splitlines()
        self.n = int(ml[0].split()[1]); self.dt = float(ml[1].split()[2])
        self.data = [[float(x) for x in l.split()] for l in ml[2:2 + self.n]]
        self.idx = {j['name']: i for i, j in enumerate(self.joints)}
        self.dur = self.n * self.dt
        # rest world positions (Blender space)
        self.rest = []
        for j in self.joints:
            p = Vector((0, 0, 0)) if j['parent'] is None else self.rest[j['parent']]
            self.rest.append(p + Y2Z @ j['off'] if j['parent'] is not None else Y2Z @ j['off'])
        self._fk = {}

    def fk(self, f):
        """world rotation (3x3, Blender space) and position of every joint at integer frame f"""
        f = max(0, min(self.n - 1, f))
        if f in self._fk: return self._fk[f]
        row = self.data[f]; k = 0; R = []; P = []
        for j in self.joints:
            loc = Vector((0, 0, 0)); rot = Matrix.Identity(3)
            for c in j['ch']:
                v = row[k]; k += 1
                if c.endswith('position'): loc['XYZ'.index(c[0])] = v
                else: rot = rot @ Matrix.Rotation(math.radians(v), 3, c[0])
            rot = Y2Z @ rot @ Y2Z.transposed()
            if j['parent'] is None:
                R.append(rot); P.append(Y2Z @ (j['off'] + loc))
            else:
                pr = R[j['parent']]; R.append(pr @ rot); P.append(P[j['parent']] + pr @ (Y2Z @ j['off']))
        if len(self._fk) > 4000: self._fk.clear()
        self._fk[f] = (R, P); return R, P

    def sample(self, t):
        """(R, P) at time t (seconds), nearest-frame blend"""
        x = t / self.dt; f0 = int(math.floor(x)); u = x - f0
        R0, P0 = self.fk(f0); R1, P1 = self.fk(f0 + 1)
        R = [a.to_quaternion().slerp(b.to_quaternion(), u).to_matrix() for a, b in zip(R0, R1)]
        P = [a.lerp(b, u) for a, b in zip(P0, P1)]
        return R, P


class Retarget:
    """per-character retarget data"""

    def __init__(self, rig):
        self.rig = rig; self.bones = {}
        for b in rig.data.bones:
            if b.name.startswith('mixamorig:'): self.bones[b.name[10:]] = b
        self.order = [n for n in (b.name[10:] for b in rig.data.bones if b.name.startswith('mixamorig:')) if n in MAP]
        b = self.bones
        self.hip_h = b['Hips'].head_local.z
        self.leg = (b['LeftUpLeg'].head_local - b['LeftLeg'].head_local).length + (b['LeftLeg'].head_local - b['LeftFoot'].head_local).length
        self._align = {}

    def align(self, src, name):
        key = (id(src), name)
        if key in self._align: return self._align[key]
        sj, sc = MAP[name]; bone = self.bones[name]
        Rt = bone.matrix_local.to_3x3()
        if sc is None or sj not in src.idx or sc not in src.idx:
            A = Matrix.Identity(3)
        else:
            ds = (src.rest[src.idx[sc]] - src.rest[src.idx[sj]]).normalized()
            tc = TCHILD.get(name)
            dt = ((self.bones[tc].head_local - bone.head_local) if tc in self.bones else Rt.col[1]).normalized()
            A = dt.rotation_difference(ds).to_matrix()
            if name in SEC and SEC[name][0] in src.idx and SEC[name][1] in self.bones:
                ss = src.rest[src.idx[SEC[name][0]]] - src.rest[src.idx[sj]]; st_ = A @ (self.bones[SEC[name][1]].head_local - bone.head_local)
                ss = ss - ds * ss.dot(ds); st_ = st_ - ds * st_.dot(ds)
                if ss.length > 1e-6 and st_.length > 1e-6:
                    ang = st_.normalized().angle(ss.normalized()); sgn = 1 if st_.cross(ss).dot(ds) > 0 else -1
                    A = Matrix.Rotation(sgn * ang, 3, ds) @ A
        self._align[key] = A; return A

    def src_leg(self, src):
        r = src.rest; i = src.idx
        return (r[i['LeftUpLeg']] - r[i['LeftLeg']]).length + (r[i['LeftLeg']] - r[i['LeftFoot']]).length

    def pose(self, src, t, place=(0, 0, 0), yaw=0.0, t0=0.0, lock_root=False):
        """armature-space target rotations {bone: Matrix3} and hips position for clip src at clip time t.
        place/yaw put the clip's start (time t0) at this position and heading."""
        R, P = src.sample(t)
        k = self.leg / self.src_leg(src)
        R0, P0 = src.sample(t0)
        hdg0 = self.heading(R0[src.idx['Hips']])
        rot = Matrix.Rotation(math.radians(yaw) - hdg0, 3, 'Z')
        rot_q = rot
        hp = P[src.idx['Hips']]; hp0 = P0[src.idx['Hips']]
        d = (hp - hp0) * k; d.z = 0
        if lock_root: d = Vector((0, 0, 0))
        out = {}
        for name in self.order:
            sj = MAP[name][0]
            if sj not in src.idx: continue
            Rs = R[src.idx[sj]]
            A = self.align(src, name); Rt = self.bones[name].matrix_local.to_3x3()
            out[name] = rot_q @ Rs @ A @ Rt
        # hands follow the forearm (CMU hand data is noisy) with a light natural flex
        for sd in ('Left', 'Right'):
            fa, hd = sd + 'ForeArm', sd + 'Hand'
            if fa in out and hd in self.bones:
                rel = self.bones[fa].matrix_local.to_3x3().inverted() @ self.bones[hd].matrix_local.to_3x3()
                out[hd] = out[fa] @ rel @ Matrix.Rotation(math.radians(12), 3, 'X')
        # thicker bodies than the mocap actor: open the upper arms a little so they clear the torso
        hr = out.get('Hips')
        if hr is not None:
            fwd = hr @ Vector((0, 0, 1)); fwd.z = 0
            fwd = fwd.normalized() if fwd.length > 1e-6 else Vector((0, -1, 0))
            for sd, s in (('Left', 1), ('Right', -1)):
                for b in (sd + 'Arm', sd + 'ForeArm', sd + 'Hand'):
                    if b in out: out[b] = Matrix.Rotation(math.radians(-7 * s), 3, fwd) @ out[b]
        hips = Vector(place) + rot @ d
        hips.z = hp.z * k + self.ground_off(src, k)
        return out, hips

    def ground_off(self, src, k):
        key = ('g', id(src))
        if key not in self._align:
            # lowest toe height over the clip, mapped, sits on the floor
            lows = []
            for f in range(0, src.n, max(1, src.n // 60)):
                R, P = src.fk(f)
                lows.append(min(P[src.idx[n]].z for n in ('LeftToeBase', 'RightToeBase', 'LeftFoot', 'RightFoot') if n in src.idx))
            lows.sort(); low = lows[len(lows) // 10]
            foot_h = min(self.bones[n].head_local.z for n in ('LeftToeBase', 'RightToeBase'))
            self._align[key] = -low * k + foot_h * .6
        return self._align[key]

    @staticmethod
    def heading(Rh):
        f = Rh @ Vector((0, -1, 0)); f.z = 0     # BVH +Z (forward) became Blender -Y
        if f.length < 1e-6: return 0.0
        return math.atan2(f.x, -f.y)   # angle of forward from -Y

    def apply(self, rots, hips):
        """write armature-space rotations into pose bones (basis), in hierarchy order"""
        pose = {}
        for name in self.order:
            if name not in rots: continue
            b = self.bones[name]; pb = self.rig.pose.bones['mixamorig:' + name]
            rest = b.matrix_local
            if b.parent is not None and b.parent.name[10:] in pose:
                pr_rest = b.parent.matrix_local; pr_pose = pose[b.parent.name[10:]]
                rel = pr_rest.inverted() @ rest
                head = (pr_pose @ rel).translation
            elif name == 'Hips':
                head = hips
            else:
                head = rest.translation
            M = rots[name].to_4x4(); M.translation = head
            pose[name] = M
            if b.parent is not None and b.parent.name[10:] in pose:
                basis = (b.parent.matrix_local.inverted() @ rest).inverted() @ pose[b.parent.name[10:]].inverted() @ M
            else:
                basis = rest.inverted() @ M
            loc, q, _ = basis.decompose()
            pb.rotation_mode = 'QUATERNION'; pb.rotation_quaternion = q
            pb.location = loc if name == 'Hips' else (0, 0, 0)
        return pose


def blend(a, b, u):
    """blend two (rots, hips) poses"""
    ra, ha = a; rb, hb = b; out = {}
    for k in ra:
        if k in rb: out[k] = ra[k].to_quaternion().slerp(rb[k].to_quaternion(), u).to_matrix()
        else: out[k] = ra[k]
    return out, ha.lerp(hb, u)


def relax_fingers(rig, curl=1.0):
    """natural relaxed hand: fingers slightly curled, thumb in"""
    for sd in ('Left', 'Right'):
        for f, base in (('Index', 12), ('Middle', 16), ('Ring', 20), ('Pinky', 24)):
            for k in (1, 2, 3):
                pb = rig.pose.bones.get(f'mixamorig:{sd}Hand{f}{k}')
                if pb: pb.rotation_mode = 'XYZ'; pb.rotation_euler = (math.radians((base + 6 * k) * curl), 0, 0)
        for k in (1, 2, 3):
            pb = rig.pose.bones.get(f'mixamorig:{sd}HandThumb{k}')
            if pb: pb.rotation_mode = 'XYZ'; pb.rotation_euler = (math.radians(8 * curl), 0, math.radians((-10 if sd == 'Left' else 10) * curl))
