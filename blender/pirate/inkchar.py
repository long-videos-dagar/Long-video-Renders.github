"""Reference-style 2D ink characters for the pirate film (drop-in for human.py: Human, EXPR, expr_track, HUMANS, Balance).
Big round white head, thick ink outline (Freestyle), line/dot eyes, flat-colour bean torso, thin black stick limbs, tiny round hands.
Pirate costumes: tricorn, bandana, beard, coat tails, sash. Front = -Y at yaw 0 ; hand targets in parent (ship) space, foot targets root-local."""
import sys, os, math
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'dagar'))
import bpy
from mathutils import Vector, Matrix
import char as C
from char import Char, two_bone
from common import solid, ink_mat, smooth
from lib import sphere, lathe, box, cyl, torus, coll
from human import Balance

HUMANS = []
C.EXPR.update({
    'neutral':  dict(C.EXPR['deadpan']),
    'smirk':    dict(w=.09, smile=.025, op=0.0, bh=.0, bt=.2, ba=.2, ex=1.0, ey=.55),
    'furious':  dict(w=.10, smile=-.05, op=.06, bh=-.045, bt=.75, ba=.0, ex=1.0, ey=.7),
    'confused': dict(w=.06, smile=-.015, op=0.0, bh=.035, bt=-.25, ba=.25, ex=1.1, ey=1.2),
    'terror':   dict(w=.08, smile=-.03, op=.11, bh=.085, bt=-.45, ba=.3, ex=1.3, ey=1.5),
    'shout':    dict(w=.085, smile=-.02, op=.12, bh=.0, bt=.5, ba=.0, ex=1.0, ey=.8),
    'strain':   dict(w=.09, smile=-.045, op=.03, bh=-.02, bt=.35, ba=.0, ex=1.0, ey=.45),
    'surprise': dict(C.EXPR['shock']),
})
for k, v in C.EXPR.items(): v.setdefault('ring', 1.0 if k in ('shock', 'scream', 'worry', 'ohno', 'terror', 'confused', 'surprise') else 0.0)
for k in ('neutral', 'deadpan', 'smug', 'smirk', 'angry', 'furious', 'strain', 'sad', 'smile', 'grin', 'shout'): C.EXPR[k]['ring'] = 0.0
C.EXPR['shout']['ring'] = 1.0
# reference-style acting: arc = closed happy (+1) / squeezed (-1) eyes, lid = half-closed lids, teeth = gritted teeth grid,
# sweat = sweat drops, steam = rage puffs, tint = purple rage face, pup = pupil size
def _e(base, **kw): d = dict(C.EXPR[base]); d.update(kw); return d
C.EXPR.update({
    'happy':      _e('smile', w=.10, smile=.045, op=.045, arc=1.0, bh=.03, ba=.5, bt=-.1),
    'laugh':      _e('grin', w=.105, smile=.04, op=.12, arc=1.0, bh=.035, ba=.5),
    'grin_teeth': _e('grin', w=.115, smile=.03, op=.085, arc=1.0, teeth=1.0, bh=.03, ba=.4),
    'relief':     _e('smile', w=.07, smile=.03, op=.0, arc=1.0, bh=.02, ba=.4, sweat=.6),
    'smug':       _e('smirk', ring=1.0, lid=.5, ex=1.0, ey=1.0, bh=-.005, bt=.25, w=.085, smile=.035, pup=.9),
    'bored':      _e('neutral', ring=1.0, lid=.55, ex=1.0, ey=1.0, bh=-.01, bt=0.0, w=.06, smile=-.01),
    'suspicious': _e('neutral', ring=1.0, lid=.62, ex=1.05, ey=1.0, bh=-.02, bt=.4, w=.05, smile=-.02, pup=.8),
    'grit':       _e('angry', w=.105, smile=-.01, op=.075, teeth=1.0, bt=.7, bh=-.04, ey=.75),
    'furious':    _e('furious', ring=1.0, ex=1.0, ey=.95, pup=.55, w=.11, smile=-.015, op=.085, teeth=1.0, bh=-.03, bt=.9, tint=.35),
    'rage':       _e('furious', ring=1.0, ex=1.05, ey=1.0, pup=.5, w=.115, smile=-.02, op=.10, teeth=1.0, bh=-.03, bt=1.0, tint=1.0, steam=1.0),
    'nervous':    _e('worry', ring=1.0, ex=1.1, ey=1.15, pup=.7, w=.075, smile=-.02, op=.035, teeth=1.0, sweat=1.0, bh=.05, bt=-.5),
    'terror':     _e('terror', ring=1.0, ex=1.3, ey=1.45, pup=.5, sweat=1.0, op=.13, w=.07),
    'wow':        _e('shock', ring=1.0, ex=1.35, ey=1.5, pup=.75, w=.04, op=.07, bh=.09),
    'strain':     _e('strain', arc=-1.0, teeth=1.0, w=.10, op=.07, smile=-.015, sweat=1.0, bh=-.03, bt=.6),
    'determined': _e('angry', w=.07, smile=.012, op=0.0, bh=-.035, bt=.55, ey=.7),
    'shout':      _e('shout', ring=1.0, ex=1.1, ey=1.1, pup=.7, op=.15, w=.085, bt=.7, bh=-.02),
    'confused':   _e('confused', ring=1.0, pup=.8, sweat=.5),
})
NEWK = ('ring', 'arc', 'lid', 'teeth', 'sweat', 'steam', 'tint', 'pup')
for k, v in C.EXPR.items():
    for nk in NEWK: v.setdefault(nk, 1.0 if nk == 'pup' else 0.0)
C.PKEYS = tuple(k for k in C.PKEYS if k not in NEWK) + NEWK
EXPR = C.EXPR

def expr_track(seq, snap=.10):
    """seq [(t, name)] -> t -> params. Expressions HOLD and then snap to the next one in `snap` seconds (on the narrated word), with a small head pop."""
    seq = sorted(seq, key=lambda k: k[0])
    def f(t):
        i = 0
        for j, (tj, _) in enumerate(seq):
            if tj <= t: i = j
        cur = EXPR[seq[i][1]]
        if i == 0 or seq[i - 1][1] == seq[i][1]: d = dict(cur); d['pop'] = 0.0; return d
        prev = EXPR[seq[i - 1][1]]; u = min(1.0, max(0.0, (t - seq[i][0]) / snap)); u = u * u * (3 - 2 * u)
        d = {k: prev[k] + (cur[k] - prev[k]) * u for k in C.PKEYS}
        for k in ('ring', 'arc', 'teeth'): d[k] = cur[k] if u > .5 else prev[k]
        v = min(1.0, max(0.0, (t - seq[i][0]) / .26)); d['pop'] = math.sin(math.pi * v) if v < 1 else 0.0
        return d
    return f

class Human(Char):
    L0, TL0, RW0 = .46, .40, .175
    def __init__(self, cid, name, skin='#f4efe6', shirt='#d8d0bc', vest=None, coat=None, trousers='#1a1a1e', boots='#15131a', hair='#2a1a10', beard=None, hat=None, bandana=None,
                 scale=1.0, height=1.0, build=1.0, eye=None):
        body = coat or shirt
        kind = 'cap' if (hair and not hat and not bandana) else None
        super().__init__(cid, name, skin=skin if skin not in ('#b98a64', '#d3a784', '#a97a58') else '#f4efe6', body=body, hair=None, hat=None, scale=scale * height * .9, pants=trousers, hair_col=hair or '#2a1a10', head_r=.25)
        self.pir = []
        hz, hx, hy, cz = self.hz, self.hx, self.hy, self.cz
        self._style(cid, skin); self.mo_off = .017 if beard else 0.0
        def link(o): o.parent = self.head; self.pir.append(o); return o
        hcol = hair or '#2a1a10'
        def shell(name, mt, lo, sc_=1.045, up=True):
            o = sphere(cid + name, 1.0, (0, .004, cz), mt, seg=56, rings=32, scale=(hx * sc_, hy * sc_, hz * sc_)); link(o)
            for v in o.data.vertices:
                if up and v.co.z < lo * hz * sc_: v.co.z = lo * hz * sc_
                if (not up) and v.co.z > lo * hz * sc_: v.co.z = lo * hz * sc_
            smooth(o); return o
        if not hat and not bandana:                                  # hair cap with fringe
            shell('_hr', solid(hcol, .8), .5)
        if bandana:
            bm = solid(bandana, .85)
            shell('_bn', bm, .56)
            er = math.sqrt(1 - .56 ** 2) * 1.045
            bb = torus(cid + '_bnb', hx * er, .014, (0, .004, cz + hz * .56 * 1.045), bm, seg=48, mseg=8); bb.scale = (1, hy / hx, 1); link(bb)
            kn = sphere(cid + '_kn', .035, (hx * .8, hy * .45, cz + hz * .5), bm, seg=12, rings=8); link(kn)
            for i, a in enumerate((-.5, .5)):
                t = cyl(cid + f'_bt{i}', .026, .16, (hx * .78 + a * .05, hy * .72, cz + hz * .38), bm, seg=8, r2=.004, rot=(math.radians(150), a * .6, a * .5)); link(t)
        if hat == 'tricorn':
            hm = solid('#17161c', .7); gold = solid('#c9a23a', .35, metal=1.0)
            top = cz + hz * .86
            cr = cyl(cid + '_cr', hx * .72, .09, (0, 0, top + .0), hm, seg=32); link(cr)
            for i, a in enumerate((0, 120, 240)):
                br = box(cid + f'_br{i}', (hx * 1.35, hx * .95, .02), (math.sin(math.radians(a)) * hx * .48, -math.cos(math.radians(a)) * hx * .48, top - .015), hm, rot=(0, 0, math.radians(a)))
                br.rotation_euler = (0, 0, math.radians(a)); link(br)
            ed = torus(cid + '_ed', hx * .74, .008, (0, 0, top + .035), gold, seg=32, mseg=6); link(ed)
            fe = sphere(cid + '_fe', .03, (hx * .7, 0, top + .1), solid('#a82a24', .8), seg=12, rings=8, scale=(.4, .8, 3.4)); link(fe)
        if beard:
            bc = solid(beard, .9)
            shell('_bd', bc, -.56, 1.05, up=False)
            for sd in (-1, 1):
                m_ = sphere(cid + f'_mo{sd}', .03, (sd * .036, -hy * .985 + .002, cz - .079), bc, seg=14, rings=8, scale=(1.5, .45, .36), rot=(0, sd * .25, 0)); link(m_)
        if coat:                                                      # tail-coat skirt
            sk = lathe(cid + '_sk', [(0, 0), (self.rw * 1.0, 0), (self.rw * 1.34, -.2), (self.rw * 1.34, -.215), (0, -.215)], seg=40, m=solid(coat, .75), sy=.82); sk.parent = self.torso; sk.location = (0, 0, .06); self.pir.append(sk)
            gm = solid('#d4aa3c', .3, metal=1.0)
            for i in range(4):
                bt = sphere(cid + f'_bt{i}', .02, (0, -self.rw * .74 * .82 - .004, .06 + i * .075 + .03), gm, seg=12, rings=8); bt.parent = self.torso; self.pir.append(bt)
            cv = sphere(cid + '_cv', .06, (0, -.045, self.TL * 1.0), solid('#f1ece0', .9), seg=14, rings=8, scale=(1.1, .8, .9)); cv.parent = self.torso; self.pir.append(cv)
            tr = torus(cid + '_tr', self.rw * 1.0, .012, (0, 0, .24), gm, seg=40, mseg=6); tr.scale = (1, .82, 1); tr.parent = self.torso; self.pir.append(tr)
        elif vest:
            vm = solid(vest, .6)
            v = lathe(cid + '_vest', [(0, .06), (self.rw * 1.0, .06), (self.rw * 1.02, .26), (self.rw * .9, self.TL - .03), (0, self.TL - .02)], seg=40, m=vm, sy=.8); v.parent = self.torso; self.pir.append(v)
            st = box(cid + '_vs', (.05, .02, self.TL - .12), (0, -self.rw * .8 * 1.02 - .004, .06 + (self.TL - .12) / 2), solid('#e8e0cc', .9)); st.parent = self.torso; self.pir.append(st)
            sa = torus(cid + '_sash', self.rw * 1.03, .028, (0, 0, .07), solid('#9a2a24', .85), seg=40, mseg=8); sa.scale = (1, .8, 1); sa.parent = self.torso; self.pir.append(sa)
        for o in self.pir:
            for cc in list(o.users_collection): cc.objects.unlink(o)
            coll('Characters').objects.link(o)
        HUMANS.append(self)

    def _style(self, cid, skin):
        hz, hx, hy, cz = self.hz, self.hx, self.hy, self.cz
        # squashed egg head: wider at the cheeks, flat chin
        for v in self.skull.data.vertices:
            zf = v.co.z / 1.0
            v.co.x *= 1 + .07 * (-zf); v.co.y *= 1 + .02 * (-zf)
            if v.co.z < -.88: v.co.z = -.88 + (v.co.z + .88) * .35
        self.skull.data.update()
        hm = self.skull.data.materials[0]; b = hm.node_tree.nodes['Principled BSDF']
        b.inputs['Roughness'].default_value = 1.0; b.inputs['Emission Color'].default_value = (.85, .8, .95, 1); b.inputs['Emission Strength'].default_value = .18
        ink = ink_mat(); white = solid('#fbf9f6', .9)
        self.rings, self.scl, self.pup = [], [], []
        for sd in (-1, 1):
            sc_ = sphere(cid + f'_scl{sd}', .05, (0, 0, 0), white, seg=24, rings=12, scale=(1, .5, 1)); sc_.parent = self.head
            rg = torus(cid + f'_rg{sd}', .049, .0075, (0, 0, 0), ink, rot=(math.pi / 2, 0, 0), seg=32, mseg=8); rg.parent = self.head
            self.rings.append(rg); self.scl.append(sc_)
            for o in (sc_, rg):
                for cc in list(o.users_collection): cc.objects.unlink(o)
                coll('Face').objects.link(o)
        hm = hm.copy(); self.skull.data.materials[0] = hm; self.skin_bsdf = hm.node_tree.nodes['Principled BSDF']; self.skin0 = tuple(self.skin_bsdf.inputs['Base Color'].default_value)
        def face_obj(o, col='Face'):
            o.parent = self.head
            for cc in list(o.users_collection): cc.objects.unlink(o)
            coll(col).objects.link(o); return o
        self.arcs = [face_obj(C._curve(cid + f'_arc{i}', 5, .0095, ink, self.head)) for i in (0, 1)]
        self.lids, self.lidl = [], []
        for i in (0, 1):
            me = bpy.data.meshes.new(cid + f'_lid{i}'); me.from_pydata([(0, 0, 0)] * 14, [], [(0, j, j + 1) for j in range(1, 13)]); me.materials.append(hm)
            self.lids.append(face_obj(bpy.data.objects.new(cid + f'_lid{i}', me))); self.lidl.append(face_obj(C._curve(cid + f'_lidl{i}', 2, .0085, ink, self.head)))
        me = bpy.data.meshes.new(cid + '_teeth'); me.from_pydata([(0, 0, 0)] * 48, [], [(q * 4, q * 4 + 1, q * 4 + 2, q * 4 + 3) for q in range(12)]); me.materials.append(solid('#fffdf8', .9))
        self.teeth = face_obj(bpy.data.objects.new(cid + '_teeth', me))
        swm = solid('#8fd0ff', .25); sb = swm.node_tree.nodes['Principled BSDF']; sb.inputs['Emission Color'].default_value = (.45, .75, 1, 1); sb.inputs['Emission Strength'].default_value = .5
        self.sweat = []
        for i in range(2):
            d = sphere(cid + f'_sw{i}', .024, (0, 0, 0), swm, seg=16, rings=10)
            for v in d.data.vertices:
                if v.co.z > 0: k_ = max(0.0, 1 - v.co.z / .024) ** .7; v.co.x *= k_; v.co.y *= k_; v.co.z *= 1.9
            smooth(d); self.sweat.append(face_obj(d, 'Characters'))
        stm = solid('#f4f4f8', 1.0); self.steam = []
        for i in range(3):
            pf = sphere(cid + f'_st{i}', .05, (0, 0, 0), stm, seg=16, rings=10)
            for j, (ox, oz, r) in enumerate(((.045, .01, .036), (-.04, .015, .034), (.0, .045, .03))):
                s2 = sphere(cid + f'_st{i}{j}', r, (ox, 0, oz), stm, seg=14, rings=8); s2.parent = pf
                for cc in list(s2.users_collection): cc.objects.unlink(s2)
                coll('Characters').objects.link(s2)
            self.steam.append(face_obj(pf, 'Characters'))
        self.nose = C._curve(cid + '_nose', 4, .0075, ink, self.head)
        for o in list(self.brows):
            o.data.bevel_depth = .0115
        self.mouth.data.bevel_depth = .0065
        try:
            for cc in list(self.nose.users_collection): cc.objects.unlink(self.nose)
        except Exception: pass
        coll('Face').objects.link(self.nose)

    def face(self, p, t):
        cz = self.cz; g = p.get; ring = g('ring', 0.0); arc = g('arc', 0.0); lid = g('lid', 0.0); teeth = g('teeth', 0.0); pup = g('pup', 1.0)
        look = g('look', (0.0, 0.0)); Z3 = (0, 0, 0)
        for i, (e, sd) in enumerate(zip(self.eyes, (-1, 1))):
            x = sd * .088; z = cz - .018
            bl = 1.0
            for b0 in self.blinks:
                if b0 <= t < b0 + .14: bl = max(.08, abs((t - b0) - .07) / .07)
            sy = self.surf_y(x, z); ar = self.arcs[i].data.splines[0]; lidm = self.lids[i].data.vertices; ll = self.lidl[i].data.splines[0]
            show_arc = abs(arc) > .5; show_lid = ring > .5 and lid > .05 and not show_arc
            self.arcs[i].hide_render = not show_arc; self.lids[i].hide_render = not show_lid; self.lidl[i].hide_render = not show_lid
            if show_arc:                                                   # closed eye: ^ (happy) or v (squeezed)
                self.scl[i].scale = Z3; self.rings[i].scale = Z3; e.scale = Z3; s_ = 1 if arc > 0 else -1
                for j in range(5):
                    u = -1 + j / 2; xx = x + u * .046; zz = z + s_ * (.03 * (1 - u * u) - .012)
                    if s_ < 0: zz = z + .016 * (-u * sd) - .0 + .0 * u; zz = z + .02 * abs(u) * 0 + (-u * sd) * .018   # '> <' slanted squeeze
                    if .5 < arc < .95: zz = z - .025 * (1 - u * u) - .004                  # sleeping: soft 'u' lids
                    ar.points[j].co = (xx, self.surf_y(xx, zz) - .004, zz, 1)
            elif ring > .5:
                rx = .05 * p['ex']; rz = .05 * max(.12, p['ey'] * .95 * bl)
                self.scl[i].location = (x, sy - .004, z); self.scl[i].scale = (p['ex'], 1, rz / .05)
                self.rings[i].location = (x, sy - .014, z); self.rings[i].scale = (p['ex'], 1, rz / .05)
                pz = z + look[1] * .02 - .004 - (rz * lid * .75 if show_lid else 0)
                e.location = (x + sd * -.004 + look[0] * .02, sy - .034, pz); e.scale = (.55 * pup, .4, .55 * pup * min(1.0, bl * 1.5))
                if show_lid:
                    ed = rz * (1 - 2 * lid * .9); th0 = math.asin(max(-1.0, min(1.0, ed / (rz + .009)))); yy = sy - .05
                    lidm[0].co = (x, yy, max(ed, z * 0 + ed) + z)
                    for j in range(13):
                        th = th0 + (math.pi - 2 * th0) * j / 12; lidm[j + 1].co = (x + math.cos(th) * (rx + .009), yy, z + math.sin(th) * (rz + .009))
                    hw = math.cos(th0) * (rx + .009)
                    ll.points[0].co = (x - hw, yy - .002, z + ed, 1); ll.points[1].co = (x + hw, yy - .002, z + ed, 1)
            else:
                self.scl[i].scale = Z3; self.rings[i].scale = Z3
                e.location = (x, sy + .004, z + .004); e.scale = (1.75, .5, max(.1, .26 * p['ey'] * bl + .06))
        for br, sd in zip(self.brows, (-1, 1)):
            sp = br.data.splines[0]; base_z = cz + .082 + p['bh'] * 1.0 + (.012 if ring > .5 else 0)
            for i, u in enumerate((-1, 0, 1)):
                x = sd * (.088 + .036 * u)
                z = base_z + u * p['bt'] * .03 + (1 - u * u) * p['ba'] * .018
                sp.points[i].co = (x, self.surf_y(x, z) - .002, z, 1)
        nz = self.nose.data.splines[0]
        for i, (x, z) in enumerate(((0.012, cz - .01), (.02, cz - .045), (.012, cz - .062), (-.006, cz - .056))):
            nz.points[i].co = (x, self.surf_y(x, z) - .002, z, 1)
        self.nose.hide_render = p.get('op', 0) > .09
        mo_off = getattr(self, 'mo_off', 0.0); my = lambda x_, z_: self.surf_y(x_, z_) - mo_off
        mo = self.mouth.data.splines[0]; w, sm, op = p['w'] * .62, p['smile'] * .8, p['op']; n = 9; z0 = cz - .115; ex_ = .5 - .32 * (1 if teeth > .5 else 0)
        def zu_(x): q = ((x - .006) / w) ** 2; return z0 + sm * q + op * .3 * max(0.0, 1 - q) ** ex_
        def zl_(x): q = ((x - .006) / w) ** 2; return z0 + sm * q - op * .7 * max(0.0, 1 - q) ** ex_
        for i in range(n):
            x = -w + 2 * w * i / (n - 1) + .006; zu = zu_(x); mo.points[i].co = (x, my(x, zu) - .002, zu, 1)
            zl = zl_(x); j = 2 * n - 2 - i
            if 0 < i < n - 1: mo.points[j].co = (x, my(x, zl) - .002, zl, 1)
        vs = self.mfill.data.vertices
        for i in range(n):
            x = -w + 2 * w * i / (n - 1) + .006; zu = zu_(x); zl = zl_(x)
            for r in range(5):
                z = zu + (zl - zu) * r / 4; vs[r * 9 + i].co = (x, my(x, z) - .0015, z)
        tv = self.teeth.data.vertices; self.teeth.hide_render = not (teeth > .5 and op > .02)
        if teeth > .5 and op > .02:
            gp = .0035; ww = w * .93
            for c in range(6):
                x0 = -ww + 2 * ww * c / 6 + .006 + gp / 2; x1 = -ww + 2 * ww * (c + 1) / 6 + .006 - gp / 2
                for r in range(2):
                    q = (r * 6 + c) * 4; pts = []
                    for xx in (x0, x1):
                        zu = zu_(xx) - .003; zl = zl_(xx) + .003; zm = (zu + zl) / 2
                        pts.append((xx, (zu, zm + gp / 2) if r == 0 else (zm - gp / 2, zl)))
                    (xa, (za1, za0)), (xb, (zb1, zb0)) = pts
                    for k_, (xx, zz) in enumerate(((xa, za0), (xb, zb0), (xb, zb1), (xa, za1))): tv[q + k_].co = (xx, my(xx, zz) - .0045, zz)
        sw = g('sweat', 0.0)
        for i, d in enumerate(self.sweat):
            ph = (t * .55 + i * .5) % 1.0; sd = 1 if i == 0 else -1
            xx = sd * self.hx * (.62 + .1 * i); zz = cz + .13 - ph * .12 - i * .04
            d.location = (xx, self.surf_y(xx, zz) - .012, zz); s_ = sw * (1.0 - .25 * i) * min(1.0, (1 - ph) * 4) * min(1.0, ph * 8 + .3); d.scale = (s_,) * 3; d.hide_render = sw < .05
        stv = g('steam', 0.0)
        for i, pf in enumerate(self.steam):
            ph = (t * .9 + i / 3) % 1.0; sd = (-1, 1, -1)[i]
            pf.location = (sd * (self.hx * .75 + .05 * ph), .02, cz + self.hz * .9 + ph * .2); s_ = stv * math.sin(math.pi * ph) ** .6 * (1.1 - .15 * i); pf.scale = (s_,) * 3
            pf.hide_render = stv < .05
            for ch in pf.children: ch.hide_render = stv < .05
        tn = g('tint', 0.0); c0 = self.skin0; c1 = (.36, .13, .5, 1)
        self.skin_bsdf.inputs['Base Color'].default_value = tuple(a_ + (b_ - a_) * tn for a_, b_ in zip(c0, c1))
        self.skin_bsdf.inputs['Emission Color'].default_value = tuple(a_ + (b_ - a_) * tn for a_, b_ in zip((.85, .8, .95, 1), (.4, .12, .55, 1)))
        pp = 1 + .07 * g('pop', 0.0); self.head.scale = (pp, pp, pp)

    def apply(self, t):
        s = self.fn(t); sc = self.s
        loc = Vector(s.get('loc', (0, 0, 0))); yaw = s.get('yaw', 0.0)
        M = Matrix.Translation(loc) @ Matrix.Rotation(math.radians(yaw), 4, 'Z'); Mi = (M @ Matrix.Scale(sc, 4)).inverted()
        self.root.location = loc; self.root.rotation_euler = (0, 0, math.radians(yaw))
        l0, l1 = s.get('lean', (0, 0)); k = 2.2; crouch = s.get('crouch', 0.0); bob = s.get('bob', 0.0) + .0
        self.torso.rotation_euler = (l0 * k, l1 * k, s.get('twist', 0.0))
        hy_, hp, hr_ = s.get('head', (0, 0, 0)); self.head.rotation_euler = (math.radians(hp), math.radians(hr_), math.radians(hy_))
        drop = (crouch + bob) / sc * 1.0
        hip0 = Vector((s.get('sway', 0.0) * 1.0, 0, self.L - drop)); self.torso.location = hip0
        R = Matrix.Rotation(l0 * k, 3, 'X') @ Matrix.Rotation(l1 * k, 3, 'Y')
        for sd in ('L', 'R'):
            side = -1 if sd == 'L' else 1
            sh = hip0 + R @ Vector((side * self.rw * .98, 0, self.TL * .84)); tg = s.get('hand' + sd)
            tgl = Vector((side * .22, -.02, self.L + self.TL * .12 - drop)) if tg is None else Mi @ Vector(tg)
            el, hd = two_bone(sh, tgl, .31, .31, Vector((side * .5, .8, -.4)))
            for pnt, v in zip(self.arms[sd].data.splines[0].points, (sh, el, hd)): pnt.co = (v.x, v.y, v.z, 1)
            self.hands[sd].location = hd
        for sd in ('L', 'R'):
            side = -1 if sd == 'L' else 1
            hip = hip0 + Vector((side * self.rw * .5, 0, -.01)); ft = Vector(s.get('foot' + sd, (side * .11, 0, 0))) / sc * 1.0
            tgl = Vector((ft.x, ft.y, ft.z + .04))
            kn, fo = two_bone(hip, tgl + Vector((0, 0, .03)), .29, .29, Vector((0, -1, .1)))
            for pnt, v in zip(self.legs[sd].data.splines[0].points, (hip, kn, fo)): pnt.co = (v.x, v.y, v.z, 1)
            self.shoes[sd].location = tgl + Vector((0, -.045, 0)); self.shoes[sd].rotation_euler = (0, 0, math.radians(s.get('footyaw' + sd, 0)))
        self.face(s.get('face', EXPR['neutral']), t)
