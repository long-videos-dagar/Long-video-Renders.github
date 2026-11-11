"""Reference-style toon characters (round white head, ink outline, stick limbs) for the Wild West film, dressed as
cowboys / townsfolk and driven by real motion capture (CMU) so they move like people.

    j = Toon('JACK', JACK); a = ToonActor(j, [Act(0, '82_09', 6.6, 3, loc=..., yaw=...)], face=[(0, 'determined')])
    a.apply(t)
"""
import sys, os, math, random
HERE = os.path.dirname(os.path.abspath(__file__)); B = os.path.dirname(HERE)
for p in (os.path.join(B, 'pirate'), os.path.join(B, 'dagar'), B, os.path.join(B, 'real')):
    if p not in sys.path: sys.path.insert(0, p)
import bpy, bmesh
from mathutils import Vector, Matrix
import inkchar as H
from common import solid, smooth
from lib import sphere, lathe, box, cyl, torus, coll
import mocap as M

EXPR = H.EXPR
for a_, b_ in (('fear', 'terror'), ('grin2', 'grin_teeth')):
    if a_ not in EXPR: EXPR[a_] = dict(EXPR[b_])
SCALE = 1.3
for k_, base, kw in (('idle', 'neutral', dict(ring=1.0, lid=.18, pup=.85, ex=1.0, ey=1.0, smile=.008)),
                     ('chat', 'smile', dict(ring=1.0, lid=.1, pup=.85, ex=1.0, ey=1.0)),
                     ('watch', 'neutral', dict(ring=1.0, lid=.3, pup=.75, ex=1.0, ey=1.0, bh=-.01, smile=-.01))):
    if k_ not in EXPR: d = dict(EXPR[base]); d.update(kw); EXPR[k_] = d


class Act:
    """one motion-capture segment: clip from src_t0, starting at shot time t, placed at loc / yaw (degrees, 0 = facing -Y)"""
    def __init__(self, t, clip, src_t0, dur=6, loc=(0, 0, 0), yaw=0.0, speed=1.0, lock_root=False, blend=.35):
        self.t, self.clip, self.s0, self.dur, self.loc, self.yaw, self.speed, self.lock, self.blend = t, clip, src_t0, dur, Vector(loc), yaw, speed, lock_root, blend


# ------------------------------------------------------------------ costumes
class Toon(H.Human):
    def __init__(self, cid, p, scale=SCALE):
        o = p['outfit']
        super().__init__(cid, p.get('name', cid), shirt=o.get('dresscol') if o.get('dress') else o['shirt'], vest=o.get('vest'), coat=o.get('coat'),
                         trousers=o.get('trousers', '#2a2a2e'), boots=o.get('boots', '#1a1410'), hair=p.get('haircol', '#2a1a10'),
                         beard=p.get('beardcol') if p.get('beard') else None, hat=None, bandana=o.get('bandana'), scale=scale, height=p.get('height', 1.0))
        self.p = p; self.extra = []
        hz, hx, hy, cz = self.hz, self.hx, self.hy, self.cz
        sa = bpy.data.objects.get(cid + '_sash')
        if sa:                                                   # pirate sash -> leather belt with a buckle
            sa.data.materials[0] = solid(o.get('belt', '#3a2414'), .55); sa.scale = (1, .8, .55)
            bk = box(cid + '_buckle', (.05, .012, .035), (0, -self.rw * .83 - .004, .07), solid('#b8963a', .3)); self._on(bk, self.torso)
            if o.get('dress'): sa.hide_render = True; sa.hide_viewport = True
        ve = bpy.data.objects.get(cid + '_vest')
        if ve:                                                   # open-front vest: V neckline shows the shirt underneath
            import bmesh as _bm
            bm_ = _bm.new(); bm_.from_mesh(ve.data); TL = self.TL
            def cut(f):
                c_ = f.calc_center_median(); a = math.degrees(math.atan2(c_.x, -c_.y))
                return c_.y < 0 and abs(a) < 7 + 26 * max(0.0, (c_.z - .1) / (TL - .1)) ** 1.3
            _bm.ops.delete(bm_, geom=[f for f in bm_.faces if cut(f)], context='FACES')
            for v in bm_.verts: v.co.x *= 1.04; v.co.y *= 1.04
            bm_.to_mesh(ve.data); bm_.free()
            sl_ = ve.modifiers.new('th', 'SOLIDIFY'); sl_.thickness = .006
            vs_ = bpy.data.objects.get(cid + '_vs')
            if vs_: vs_.hide_render = True; vs_.hide_viewport = True
        if False:                                                            # (hair under hats: off - reads as a patch on the round head)
            import bmesh as _bm
            hb = sphere(cid + '_bhair', 1.0, (0, .006, cz), solid(p.get('haircol', '#2a1a10'), .85), seg=40, rings=20)
            bm_ = _bm.new(); bm_.from_mesh(hb.data)
            _bm.ops.delete(bm_, geom=[f for f in bm_.faces if not (-.42 < f.calc_center_median().z < .5 and f.calc_center_median().y > .12 + .35 * max(0.0, f.calc_center_median().z - .1) + .25 * max(0.0, -.15 - f.calc_center_median().z))], context='FACES')
            for v in bm_.verts: v.co.x *= hx * 1.035; v.co.y *= hy * 1.035; v.co.z *= hz * 1.035
            bm_.to_mesh(hb.data); bm_.free(); smooth(hb); self._on(hb, self.head)
        if p.get('bun'):
            b = sphere(cid + '_bun', 1.0, (0, hy * .82, cz + hz * .38), solid(p.get('haircol', '#2a1a10'), .8), seg=24, rings=14, scale=(hx * .42, hy * .36, hz * .36))
            smooth(b); self._on(b, self.head)
        if o.get('hat') in ('cowboy', 'bowler', 'straw', 'slouch', 'tophat'): self._hat(o['hat'], o.get('hatcol', '#6a4a30'))
        if o.get('hat') == 'bonnet': self._bonnet(o.get('hatcol', '#e8e0d0'))
        if p.get('stache'): self._stache(p.get('beardcol', '#2a1a10'))
        if o.get('neckerchief'): self._kerchief(o['neckerchief'])
        if o.get('badge'): self._badge()
        if o.get('gun'): self._gunbelt(o.get('belt', '#3a2414'))
        if o.get('dress'): self._dress(o['dresscol'])
        if o.get('collar', True) and not o.get('dress'): self._collar(o.get('collarcol', o['shirt']))
        if o.get('buttons', True) and not o.get('apron'): self._buttons(o.get('btncol', '#f2ece0'), top_only=bool(o.get('vest')))
        if o.get('vest') and not o.get('dress'): self._vest_details(o['vest'])
        if o.get('suspenders'): self._suspenders(o['suspenders'])
        if o.get('apron'): self._apron(o['apron'], long=bool(o.get('dress')))
        if o.get('duster'): self._duster(o['duster'])
        if o.get('shawl'): self._shawl(o['shawl'])
        if o.get('bolo'): self._bolo()
        if o.get('dress'): self._dress_details(o['dresscol'])
        self._boots(o.get('boots', '#2a1a10'), tall=not o.get('dress'), spurs=bool(o.get('spurs')))
        for ob in self.extra:
            for c in list(ob.users_collection): c.objects.unlink(ob)
            coll('Characters').objects.link(ob)
        self.ink()

    def ink(self, w=.011):
        """ink outline: a child copy of every part (shared mesh), pushed out along the normals, with a material that is
        transparent on its near side and black on its far side - only the rim around the silhouette shows"""
        m = ink_hull_mat()
        objs = [o for o in self.root.children_recursive if o.type == 'MESH']
        for o in objs:
            if any(k in o.name for k in ('_eye', '_scl', '_rg', 'mfill', '_teeth', '_lid', '_sw', '_st', '_star', '_btn', '_vb', '_db', '_bclasp', '_brooch', '_wch', '_bt', '_vp')): continue
            if o.name.endswith(('_nose', '_mouth', '_ink')): continue
            sc_ = max(o.matrix_world.to_scale()[0], 1e-3)
            h = bpy.data.objects.new(o.name + '_ink', o.data)
            for c in o.users_collection: c.objects.link(h)
            h.parent = o; h.matrix_parent_inverse.identity()
            for sl in h.material_slots: sl.link = 'OBJECT'; sl.material = m
            for md in o.modifiers:
                if md.type == 'SOLIDIFY': s = h.modifiers.new('s', 'SOLIDIFY'); s.thickness = md.thickness
            d = h.modifiers.new('ink', 'DISPLACE'); d.direction = 'NORMAL'; d.mid_level = 0.0; d.strength = w / sc_ * self.s
            h.visible_shadow = False; h.visible_diffuse = False; h.visible_glossy = False

    def _on(self, o, parent):
        o.parent = parent; self.extra.append(o); return o

    def _hat(self, kind, col):
        hz, hx, hy, cz = self.hz, self.hx, self.hy, self.cz
        m = solid(col, .85); band = solid('#2a1a10', .6)
        top = cz + hz * .55
        if kind == 'cowboy':
            cr = sphere(self.cid + '_crown', 1.0, (0, 0, top), m, seg=40, rings=20)
            for v in cr.data.vertices:
                z = max(0.0, v.co.z); r = math.hypot(v.co.x, v.co.y)
                rr = 1.0 if z < .55 else math.sqrt(max(0.0, 1 - ((z - .55) / .45) ** 2)) * .35 + .65 * (1 - (z - .55) / .45 * .25)
                if r > 1e-4: v.co.x, v.co.y = v.co.x / r * min(r, 1) * (rr if r > .2 else 1) * (1 - .1 * z), v.co.y / r * min(r, 1) * (rr if r > .2 else 1) * (1 - .1 * z)
                v.co.z = z * .95 if z < .9 else .85 + (z - .9) * .5
                if v.co.z > .6: v.co.z -= .3 * max(0.0, 1 - abs(v.co.x) * 3.0) * (v.co.z - .6) / .4      # centre crease
                if v.co.y < -.3 and v.co.z > .5: v.co.x *= 1 - .25 * (v.co.z - .5) * 2                  # front pinch
            for v in cr.data.vertices: v.co.x *= hx * .72; v.co.y *= hy * .82; v.co.z *= hz * .95
            br = cyl(self.cid + '_brim', 1.0, .02, (0, 0, top + .01), m, seg=48)
            br.scale = (hx * 1.6, hy * 1.7, 1)
            for v in br.data.vertices:
                r = math.hypot(v.co.x, v.co.y)
                if r > .5: v.co.z += (r - .5) ** 2 * abs(v.co.x) * .32 - (r - .5) ** 2 * max(0.0, -v.co.y) * .1
            bd = torus(self.cid + '_hband', 1.0, .016, (0, 0, top + .035), band, seg=40, mseg=8); bd.scale = (hx * .735, hy * .835, 1)
            parts = [cr, br, bd]
        elif kind == 'tophat':
            cr = cyl(self.cid + '_crown', 1.0, 1.0, (0, 0, top + hz * .62), m, seg=40)
            for v in cr.data.vertices:
                if v.co.z > 0: v.co.x *= 1.06; v.co.y *= 1.06
            cr.scale = (hx * .7, hy * .78, hz * 1.25)
            br = cyl(self.cid + '_brim', 1.0, .035, (0, 0, top + .015), m, seg=48); br.scale = (hx * 1.22, hy * 1.26, 1)
            for v in br.data.vertices:
                if abs(v.co.x) > .7: v.co.z += (abs(v.co.x) - .7) * .12
            bd = torus(self.cid + '_hband', 1.0, .02, (0, 0, top + .05), solid('#3a3a42', .5), seg=40, mseg=8); bd.scale = (hx * .72, hy * .8, 1)
            for o_ in (cr, br, bd): smooth(o_); self._on(o_, self.head)
            return
        elif kind in ('straw', 'slouch'):
            straw = kind == 'straw'
            if straw: m = straw_mat(col)
            cr = cyl(self.cid + '_crown', 1.0, 1.0, (0, 0, top + hz * .22), m, seg=40)
            for v in cr.data.vertices:
                if not straw and v.co.z > 0: v.co.x *= .85; v.co.y *= .85
            cr.scale = (hx * .74, hy * .82, hz * .42 if straw else hz * .5)
            br = cyl(self.cid + '_brim', 1.0, .02, (0, 0, top + .01), m, seg=48); br.scale = (hx * (1.7 if straw else 1.55), hy * (1.75 if straw else 1.6), 1)
            for v in br.data.vertices:
                r = math.hypot(v.co.x, v.co.y)
                if r > .55: v.co.z -= (r - .55) * (.04 if straw else .16) * (1 + .6 * math.sin(math.atan2(v.co.y, v.co.x) * 3))
            bd = torus(self.cid + '_hband', 1.0, .014, (0, 0, top + .03), solid('#7a2a22' if straw else '#2a1a10', .7), seg=40, mseg=8); bd.scale = (hx * .745, hy * .825, 1)
            for o_ in (cr, br, bd): smooth(o_); self._on(o_, self.head)
            return
        elif kind in ('cap', 'police'):                         # modern peaked cap: soft crown + stiff visor (police: flat top + badge)
            cr = sphere(self.cid + '_crown', 1.0, (0, 0, top - hz * .05), m, seg=40, rings=20)
            for v in cr.data.vertices:
                if v.co.z < 0: v.co.z = 0
                if kind == 'police' and v.co.z > .55: v.co.z = .55 + (v.co.z - .55) * .25; v.co.x *= 1.08; v.co.y *= 1.08
                v.co.x *= hx * .84; v.co.y *= hy * .88; v.co.z *= hz * (.62 if kind == 'cap' else .78)
            vz = box(self.cid + '_brim', (hx * 1.5, hy * .62, .018), (0, -hy * .98, top - hz * .02), solid('#141618' if kind == 'police' else col, .7), rot=(math.radians(-14), 0, 0))
            parts = [cr, vz]
            if kind == 'police':
                parts.append(box(self.cid + '_hbadge', (.06, .012, .07), (0, -hy * .86, top + hz * .22), solid('#d8b848', .3, metal=1.0)))
                parts.append(torus(self.cid + '_hband', 1.0, .018, (0, 0, top + .025), solid('#101214', .6), seg=40, mseg=8)); parts[-1].scale = (hx * .845, hy * .885, 1)
        else:
            cr = sphere(self.cid + '_crown', 1.0, (0, 0, top), m, seg=40, rings=20)
            for v in cr.data.vertices:
                if v.co.z < 0: v.co.z = 0
                v.co.x *= hx * .8; v.co.y *= hy * .85; v.co.z *= hz * .75
            br = cyl(self.cid + '_brim', 1.0, .02, (0, 0, top + .01), m, seg=48); br.scale = (hx * 1.15, hy * 1.2, 1)
            for v in br.data.vertices:
                r = math.hypot(v.co.x, v.co.y)
                if r > .7: v.co.z += (r - .7) * .12
            bd = torus(self.cid + '_hband', 1.0, .016, (0, 0, top + .03), band, seg=40, mseg=8); bd.scale = (hx * .81, hy * .86, 1)
            parts = [cr, br, bd]
        for o in parts: smooth(o); self._on(o, self.head)

    def _bonnet(self, col):
        hz, hx, hy, cz = self.hz, self.hx, self.hy, self.cz
        import bmesh
        m = solid(col, .9)
        b = sphere(self.cid + '_bonnet', 1.0, (0, .03, cz + hz * .12), m, seg=40, rings=20)
        bm_ = bmesh.new(); bm_.from_mesh(b.data)
        bmesh.ops.delete(bm_, geom=[f for f in bm_.faces if f.calc_center_median().y < -.25 or f.calc_center_median().z < -.5], context='FACES')
        for v in bm_.verts: v.co.x *= hx * 1.1; v.co.y *= hy * 1.12; v.co.z *= hz * 1.04
        bm_.to_mesh(b.data); bm_.free()
        s = b.modifiers.new('th', 'SOLIDIFY'); s.thickness = .012
        smooth(b); self._on(b, self.head)
        br = torus(self.cid + '_bbrim', 1.0, .045, (0, .03 - .25 * hy * 1.12, cz + hz * .12), m, seg=40, mseg=10, arc=math.pi * 4 / 3)
        br.rotation_euler = (math.pi / 2, math.radians(30), 0); br.scale = (hx * 1.07, hz * 1.0, 1); smooth(br); self._on(br, self.head)

    def _stache(self, col):
        hz, hx, hy, cz = self.hz, self.hx, self.hy, self.cz
        m = solid(col, .9)
        for sd in (-1, 1):
            s = sphere(self.cid + f'_st{sd}', .05, (sd * .045, self.surf_y(sd * .045, cz - .088) - .006, cz - .09), m, seg=16, rings=10, scale=(1.3, .55, .45), rot=(0, sd * .35, 0))
            self._on(s, self.head)

    def _kerchief(self, col):
        m = solid(col, .85); TL, rw = self.TL, self.rw
        t = torus(self.cid + '_kc', rw * .62, .025, (0, -.005, TL + .005), m, seg=32, mseg=8); t.scale = (1, .85, 1); self._on(t, self.torso)
        c = cyl(self.cid + '_kt', .07, .012, (0, -rw * .72, TL - .07), m, seg=3, rot=(math.pi / 2, 0, math.pi)); c.scale = (1, 1.3, 1); self._on(c, self.torso)

    def _badge(self):
        TL, rw = self.TL, self.rw; gm = solid('#d8b040', .25)
        me = bpy.data.meshes.new(self.cid + '_star'); pts = [(0, 0, 0)]
        for k in range(10):
            a = k / 10 * math.tau + math.pi / 2; r = .045 if k % 2 == 0 else .019; pts.append((math.cos(a) * r, 0, math.sin(a) * r))
        me.from_pydata(pts, [], [(0, 1 + k, 1 + (k + 1) % 10) for k in range(10)])
        st = bpy.data.objects.new(self.cid + '_star', me); me.materials.append(gm); bpy.context.scene.collection.objects.link(st)
        z_ = TL * .66; st.location = (rw * .44, self.fy(z_, 1.13 if self.p['outfit'].get('duster') else 1.05) - .012, z_); sl = st.modifiers.new('s', 'SOLIDIFY'); sl.thickness = .008
        self._on(st, self.torso)

    def _gunbelt(self, col):
        rw = self.rw; lm = solid(col, .55); steel = solid('#2a2c30', .3)
        b = torus(self.cid + '_gb', rw * 1.02, .022, (0, 0, .03), lm, seg=40, mseg=8); b.scale = (1, .82, 1); self._on(b, self.torso)
        hs = box(self.cid + '_hol', (.045, .09, .2), (-rw * 1.05, .0, -.06), lm); hs.rotation_euler = (math.radians(-8), 0, 0); self._on(hs, self.torso)
        g = box(self.cid + '_grip', (.03, .05, .09), (-rw * 1.07, .02, .07), solid('#5a321a', .4)); g.rotation_euler = (math.radians(-25), 0, 0); self._on(g, self.torso)
        self.gun_grip = g

    # ---- shirt / vest / coat details (torso space: z up from the hips, front is -Y)
    def fy(self, z, out=1.0):
        rw, TL = self.rw, self.TL; u = max(0.0, min(1.0, (z - .04) / (TL - .1)))
        return -(rw * (.92 + .1 * math.sin(math.pi * u * .9))) * .78 * out - .003

    def _collar(self, col):
        m = solid(col, .8); TL = self.TL
        for sd in (-1, 1):
            me = bpy.data.meshes.new(self.cid + f'_col{sd}')
            z0 = TL - .035; y0 = self.fy(z0) * .82
            me.from_pydata([(sd * .012, y0 - .006, z0 - .055), (sd * .07, y0 + .02, z0 + .012), (sd * .02, y0 + .004, z0 + .02)], [], [(0, 1, 2)])
            o = bpy.data.objects.new(self.cid + f'_col{sd}', me); me.materials.append(m); bpy.context.scene.collection.objects.link(o)
            s = o.modifiers.new('s', 'SOLIDIFY'); s.thickness = .006; self._on(o, self.torso)

    def _buttons(self, col, top_only=False):
        m = solid(col, .4)
        for k in range(3):
            z = .1 + k * (self.TL - .2) / 2
            if top_only and z < self.TL * .55: continue
            self._on(sphere(self.cid + f'_btn{k}', .009, (0, self.fy(z) - .002, z), m, seg=10, rings=6, scale=(1, .5, 1)), self.torso)

    def _vest_details(self, col):
        dm = solid(_shade(col, .7), .6); gm = solid('#c8a040', .3)
        for sd in (-1, 1):
            z = .15; self._on(box(self.cid + f'_vp{sd}', (.045, .006, .012), (sd * .08, self.fy(z, 1.07) * .93 - .002, z), dm, rot=(0, 0, -sd * .5)), self.torso)
        for k in range(3):
            z = .07 + k * .045; self._on(sphere(self.cid + f'_vb{k}', .008, (.022 + k * .006, self.fy(z, 1.07) - .002, z), gm, seg=10, rings=6, scale=(1, .5, 1)), self.torso)
        # watch chain
        ch = torus(self.cid + '_wch', .045, .003, (-.03, self.fy(.13, 1.05) - .004, .13), gm, rot=(math.pi / 2, 0, 0), seg=16, mseg=4, arc=math.pi)
        ch.rotation_euler = (math.pi / 2, math.pi, 0); self._on(ch, self.torso)

    def _suspenders(self, col):
        m = solid(col, .6)
        for sd in (-1, 1):
            for fb in (-1, 1):
                z0, z1 = .05, self.TL - .02
                me = bpy.data.meshes.new('sus'); pts = []
                for k in range(7):
                    z = z0 + (z1 - z0) * k / 6; yy = (self.fy(z, 1.03) if fb < 0 else -self.fy(z, 1.03)); pts.append((sd * (.05 + .012 * k / 6), yy, z))
                me.from_pydata(pts, [(i, i + 1) for i in range(6)], [])
                o = bpy.data.objects.new(self.cid + '_sus', me); bpy.context.scene.collection.objects.link(o); o.data.materials.append(m)
                sk = o.modifiers.new('sk', 'SKIN'); o.data.skin_vertices[0].data.foreach_set('radius', [.012, .004] * 7)
                self._on(o, self.torso)

    def _apron(self, col, long=False):
        m = solid(col, .9); L, TL = self.L, self.TL
        top = TL * .55 if not long else TL * .7; bot = -(L * (.45 if not long else .75))
        bm_ = bmesh.new(); vs = {}
        nx, nz = 6, 8
        for i in range(nx + 1):
            for j in range(nz + 1):
                u, v = i / nx, j / nz; z = top + (bot - top) * v
                w = .07 + (.11 if long else .09) * min(1, v * 2.2)
                x = (u - .5) * 2 * w
                y = (self.fy(min(z, TL - .05), 1.12) if z > .04 else self.fy(.05, 1.12) - (.04 - z) * (.25 if not long else .9)) + .01 * (2 * u - 1) ** 2
                vs[i, j] = bm_.verts.new((x, y - .006, z))
        for i in range(nx):
            for j in range(nz): bm_.faces.new((vs[i, j], vs[i + 1, j], vs[i + 1, j + 1], vs[i, j + 1]))
        me = bpy.data.meshes.new(self.cid + '_apron'); bm_.to_mesh(me); bm_.free(); me.materials.append(m)
        o = bpy.data.objects.new(self.cid + '_apron', me); bpy.context.scene.collection.objects.link(o)
        s = o.modifiers.new('s', 'SOLIDIFY'); s.thickness = .006; smooth(o); self._on(o, self.torso)
        tie = torus(self.cid + '_atie', self.rw * 1.0, .008, (0, 0, .07), m, seg=32, mseg=6); tie.scale = (1, .8, 1); self._on(tie, self.torso)

    def _duster(self, col):
        """long open-front coat: lathe from the shoulders to below the knee with the front cut away, lapels"""
        rw, TL, L = self.rw, self.TL, self.L; m = solid(col, .8)
        prof = [(rw * .85, TL - .02), (rw * 1.06, TL - .1), (rw * 1.08, TL * .5), (rw * 1.06, .06), (rw * 1.14, -.05)]
        for k in range(1, 6): u = k / 5; prof.append((rw * 1.14 + u * rw * .38, -.05 - u * L * .62))
        c = lathe(self.cid + '_duster', prof, seg=40, m=m, sy=.82)
        bm_ = bmesh.new(); bm_.from_mesh(c.data)
        def cut(f):
            p = f.calc_center_median(); a = math.degrees(math.atan2(p.x, -p.y))
            half = 9 + (34 if p.z < .06 else 16 * (1 - (p.z - .06) / (TL - .06)) + 8)
            return abs(a) < half
        bmesh.ops.delete(bm_, geom=[f for f in bm_.faces if cut(f)], context='FACES'); bm_.to_mesh(c.data); bm_.free()
        s = c.modifiers.new('s', 'SOLIDIFY'); s.thickness = .008; smooth(c); self._on(c, self.torso)
        for sd in (-1, 1):
            me = bpy.data.meshes.new('lap'); z0 = TL - .03
            me.from_pydata([(sd * .03, self.fy(z0, 1.1) - .004, z0), (sd * .085, self.fy(z0 - .05, 1.12) - .006, z0 - .05), (sd * .04, self.fy(.1, 1.12) - .006, .1)], [], [(0, 1, 2)])
            o = bpy.data.objects.new(self.cid + '_lap', me); bpy.context.scene.collection.objects.link(o); me.materials.append(solid(_shade(col, .8), .8))
            o.modifiers.new('s', 'SOLIDIFY').thickness = .005; self._on(o, self.torso)

    def _shawl(self, col):
        m = solid(col, .9); TL, rw = self.TL, self.rw
        prof = [(rw * .7, TL - .01), (rw * 1.0, TL - .05), (rw * 1.12, TL - .11), (rw * 1.15, TL - .15)]
        sh = lathe(self.cid + '_shawl', prof, seg=40, m=m, sy=.85); s = sh.modifiers.new('s', 'SOLIDIFY'); s.thickness = .01; smooth(sh); self._on(sh, self.torso)
        self._on(sphere(self.cid + '_brooch', .014, (0, self.fy(TL - .06, 1.1) - .01, TL - .06), solid('#c8a040', .3), seg=12, rings=8), self.torso)

    def _bolo(self):
        TL = self.TL; k = solid('#141214', .5)
        for sd in (-1, 1): self._on(cyl(self.cid + '_bt', .003, .1, (sd * .01, self.fy(TL - .08) - .004, TL - .08), k, seg=6), self.torso)
        self._on(sphere(self.cid + '_bclasp', .014, (0, self.fy(TL - .04) - .006, TL - .04), solid('#b8b0a0', .3), seg=12, rings=8, scale=(1, .5, 1.2)), self.torso)

    def _dress_details(self, col):
        TL = self.TL; lace = solid('#f4efe4', .9)
        c = torus(self.cid + '_lace', self.rw * .62, .012, (0, -.004, TL - .01), lace, seg=32, mseg=6); c.scale = (1, .82, 1); self._on(c, self.torso)
        for k in range(4):
            z = .06 + k * (TL - .14) / 3
            self._on(sphere(self.cid + f'_db{k}', .008, (0, self.fy(z) - .002, z), lace, seg=10, rings=6, scale=(1, .5, 1)), self.torso)
        hem = torus(self.cid + '_hem', 1.0, .012, (0, 0, -.02 - (self.L - .1) + .03), solid(_shade(col, .7), .8), seg=40, mseg=6)
        r_ = self.rw * 1.12 + self.rw * .85 - .004; hem.scale = (r_, r_ * .85, 1); self._on(hem, self.torso)

    def _boots(self, col, tall=True, spurs=False):
        m = solid(col, .5); heel = solid('#141010', .5)
        for sd in ('L', 'R'):
            sh = self.shoes[sd]
            sh.data.materials[0] = m if tall else sh.data.materials[0]
            if tall:
                b = cyl(self.cid + '_shaft' + sd, .036, .15, (0, .035, .085), m, seg=16); b.scale = (1, 1.1, 1)
                b.parent = sh; self.extra.append(b)
                t_ = torus(self.cid + '_btop' + sd, .037, .007, (0, .035, .16), solid(_shade(col, .75), .5), seg=20, mseg=6); t_.parent = sh; self.extra.append(t_)
            hl = box(self.cid + '_heel' + sd, (.05, .035, .03), (0, .075, -.03), heel); hl.parent = sh; self.extra.append(hl)
            if spurs:
                sp = torus(self.cid + '_spur' + sd, .018, .003, (0, .105, -.01), solid('#b8b4ac', .3, metal=1.0) if 'metal' in solid.__code__.co_varnames else solid('#b8b4ac', .3), rot=(0, math.pi / 2, 0), seg=10, mseg=4); sp.parent = sh; self.extra.append(sp)

    def _dress(self, col):
        rw, L = self.rw, self.L
        prof = [(0, .12), (rw * 1.04, .12), (rw * 1.1, -.02)]
        for k in range(1, 8):
            u = k / 7; prof.append((rw * 1.12 + u ** 1.5 * rw * .85, -.02 - u * (L - .1)))
        prof.append((0, -.02 - (L - .1)))
        sk = lathe(self.cid + '_dress', prof, seg=40, m=solid(col, .85), sy=.85); smooth(sk); self._on(sk, self.torso)


def _shade(h, f):
    h = h.lstrip('#'); c = [int(h[i:i + 2], 16) for i in (0, 2, 4)]
    return '#' + ''.join(f'{max(0, min(255, int(x * f))):02x}' for x in c)


def straw_mat(col):
    m = bpy.data.materials.get('straw_' + col)
    if m: return m
    m = solid(col, .9).copy(); m.name = 'straw_' + col; N, L = m.node_tree.nodes, m.node_tree.links; b = N['Principled BSDF']
    tc = N.new('ShaderNodeTexCoord'); w = N.new('ShaderNodeTexWave'); w.wave_type = 'RINGS'; w.inputs['Scale'].default_value = 60; w.inputs['Distortion'].default_value = 2
    L.new(tc.outputs['Object'], w.inputs['Vector'])
    bp = N.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = .35; L.new(w.outputs['Fac'], bp.inputs['Height']); L.new(bp.outputs[0], b.inputs['Normal'])
    return m


def ink_hull_mat():
    m = bpy.data.materials.get('ink_hull2')
    if m: return m
    m = bpy.data.materials.new('ink_hull2'); m.use_nodes = True; N, L = m.node_tree.nodes, m.node_tree.links; N.clear()
    out = N.new('ShaderNodeOutputMaterial'); g = N.new('ShaderNodeNewGeometry'); tr = N.new('ShaderNodeBsdfTransparent')
    em = N.new('ShaderNodeEmission'); em.inputs['Color'].default_value = (.008, .006, .008, 1); em.inputs['Strength'].default_value = 1.0
    mx = N.new('ShaderNodeMixShader'); L.new(g.outputs['Backfacing'], mx.inputs['Fac']); L.new(tr.outputs[0], mx.inputs[1]); L.new(em.outputs[0], mx.inputs[2])
    L.new(mx.outputs[0], out.inputs['Surface'])
    m.blend_method = 'BLEND' if hasattr(m, 'blend_method') else None
    try: m.use_backface_culling = False
    except Exception: pass
    return m


def preset(name, shirt, trousers, hat=None, hatcol='#6a4a30', vest=None, coat=None, bandana=None, neckerchief=None, badge=False, gun=False,
           beard=False, stache=False, haircol='#2a1a10', beardcol='#2a1a10', dress=False, dresscol=None, height=1.0, boots='#2a1a10', bun=False, **more):
    return dict(name=name, haircol=haircol, bun=bun, beard=beard, beardcol=beardcol, stache=stache, height=height,
                outfit=dict(shirt=shirt, trousers=trousers, hat=hat, hatcol=hatcol, vest=vest, coat=coat, bandana=bandana, neckerchief=neckerchief,
                            badge=badge, gun=gun, dress=dress, dresscol=dresscol or shirt, boots=boots, **more))


JACK = preset('Jack', '#8fa8bc', '#3c4656', hat='cowboy', hatcol='#a07848', vest='#6a4022', neckerchief='#a82a20', gun=True, haircol='#6a3a1a',
              height=1.04, boots='#5a3420', spurs=True, belt='#4a2c16')
SHERIFF = preset('Sheriff', '#e8e0cf', '#3a342e', hat='cowboy', hatcol='#1e1c20', vest='#2a2426', badge=True, gun=True, stache=True, beardcol='#3a2416',
                 haircol='#3a2416', height=1.0, duster='#2c2824', bolo=True, boots='#1a1614', spurs=True, belt='#1e1612')

ROLES = ['rancher', 'shopkeeper', 'banker', 'miner', 'farmer', 'lady', 'worker', 'rancher', 'lady', 'miner']


def crowd_preset(i):
    """townsfolk archetypes so the crowd reads as a real town: ranchers, shopkeepers, bankers, miners, farmers, ladies"""
    r = random.Random(500 + i * 11); role = ROLES[(i * 7 + r.randint(0, 2)) % len(ROLES)]
    hair = r.choice(['#2a1a10', '#1a1410', '#5a3a1a', '#8a6a40', '#7a7a78'])
    beard = dict(beard=r.random() < .2, stache=r.random() < .35, beardcol=hair)
    h = r.uniform(.95, 1.07)
    if role == 'rancher':
        return preset(f'Rancher{i}', r.choice(['#c8b8a0', '#8a5a48', '#6a7a8a', '#b8a888', '#7a8a6a']), r.choice(['#3a3d42', '#4a4036', '#5a4a3a']), hat='cowboy',
                      hatcol=r.choice(['#6a4a30', '#9a7a50', '#4a3a2a', '#7a6a58']), vest=r.choice([None, '#4a3626', '#2a2420']), neckerchief=r.choice([None, '#2a4a6a', '#8a2a20', '#c8a040']),
                      gun=r.random() < .4, boots=r.choice(['#4a2c18', '#2a1a10']), spurs=r.random() < .5, haircol=hair, height=h, **beard)
    if role == 'shopkeeper':
        return preset(f'Shop{i}', '#ece6d8', '#3a3a3e', hat=r.choice([None, 'bowler']), hatcol='#2a2622', vest=r.choice(['#3a4a3a', '#4a3a4a', None]),
                      apron='#f0ece2', boots='#1a1614', haircol=hair, height=h, **beard)
    if role == 'banker':
        return preset(f'Banker{i}', '#f0ece4', '#2a2a30', hat='bowler', hatcol='#1a1a1e', vest=r.choice(['#5a1e22', '#3a3a44', '#6a5a3a']), duster=r.choice(['#2a2a32', '#3a3028']),
                      bolo=True, boots='#121014', haircol=hair, height=h, stache=True, beardcol=hair)
    if role == 'miner':
        return preset(f'Miner{i}', r.choice(['#a85a3a', '#7a5a4a', '#5a6a7a', '#c0a080']), r.choice(['#5a4a3a', '#3a3d42']), hat='slouch', hatcol=r.choice(['#5a4a3a', '#3a3028']),
                      suspenders=r.choice(['#3a2a1a', '#2a2a2a', '#6a3020']), boots='#3a2a1a', haircol=hair, height=h, beard=r.random() < .5, beardcol=hair, buttons=True)
    if role == 'farmer':
        return preset(f'Farmer{i}', r.choice(['#d8ccb0', '#a8b8c8', '#c89a7a']), '#4a5a78', hat='straw', hatcol='#d0b878', suspenders='#4a5a78',
                      boots='#4a3020', haircol=hair, height=h, **beard)
    dcol = r.choice(['#7a3a4a', '#3a4a6a', '#5a6a4a', '#8a6a4a', '#6a4a6a', '#a07050', '#4a6a7a'])
    if role == 'lady':
        return preset(f'Lady{i}', '#e8e0d0', '#2a2a2e', hat=r.choice(['bonnet', 'bonnet', None]), hatcol=r.choice(['#e8d8b8', '#a8b8c8', '#c8a8a8', '#d8c890']), dress=True, dresscol=dcol,
                      shawl=r.choice([None, '#8a3a3a', '#4a5a7a', '#6a5a4a', '#d8ccb4']), haircol=r.choice(['#2a1a10', '#6a3a1a', '#b08040', '#1a1410']), height=r.uniform(.92, 1.0), bun=True, collar=False, boots='#1a1410')
    return preset(f'Worker{i}', '#e8e0d0', '#2a2a2e', hat=None, dress=True, dresscol=dcol, apron='#efe9dc', haircol=r.choice(['#2a1a10', '#6a3a1a', '#b08040']),
                  height=r.uniform(.92, 1.0), bun=True, collar=False, boots='#1a1410')


# ------------------------------------------------------------------ mocap -> toon pose
class ToonActor:
    def __init__(self, ch, acts, face=None, look=None, talk=None, blink_seed=0, props=None, level=True):
        self.ch = ch; self.acts = sorted(acts, key=lambda a: a.t); self.face = H.expr_track(face or [(0, 'idle')])
        self.look = look; self.talk = talk or []; self.props = props or []
        ch.fn = self._fn; self.t = 0.0

    def _sample(self, a, t):
        src = M.BVH.load(a.clip)
        st = max(a.s0, min(a.s0 + (t - a.t) * a.speed, src.dur - .05))
        R, P = src.sample(st); R0, P0 = src.sample(a.s0); I = src.idx
        h0 = M.Retarget.heading(R0[I['Hips']]); hn = M.Retarget.heading(R[I['Hips']])
        yaw = math.radians(a.yaw)
        r = Matrix.Rotation(yaw - h0, 3, 'Z')
        sl = (src.rest[I['LeftUpLeg']] - src.rest[I['LeftLeg']]).length + (src.rest[I['LeftLeg']] - src.rest[I['LeftFoot']]).length
        tl = .58 * self.ch.s; k = tl / sl
        d = (P[I['Hips']] - P0[I['Hips']]) * k; d.z = 0
        if a.lock: d = Vector()
        loc = a.loc + r @ d
        cy = yaw + hn - h0                                   # character yaw (radians)
        inv = Matrix.Rotation(-(hn), 3, 'Z')                 # mocap world -> mocap body frame (facing -Y)
        def body(p): return inv @ (p - P[I['Hips']])
        gz = self._ground(src)
        hip_h = P[I['Hips']].z - gz
        crouch = max(0.0, (sl * .97 - hip_h) * k)
        sp = body(P[I['Neck1']]); l0 = math.atan2(-sp.y, sp.z) / 2.2; l1 = math.atan2(sp.x, sp.z) / 2.2
        hd = body(P[I['Head']]) - sp; hp = math.degrees(math.atan2(-hd.y, hd.z)) - math.degrees(l0 * 2.2)
        l0 = max(-.07, min(.16, l0)); l1 = max(-.08, min(.08, l1))
        if self.ch.p['outfit'].get('dress'): l0, l1 = l0 * .35, l1 * .35
        out = dict(loc=(loc.x, loc.y, a.loc.z), yaw=math.degrees(cy), crouch=crouch, lean=(l0, l1), head=[0.0, max(-6, min(10, hp * .35)), 0.0])
        ch = self.ch; sc = ch.s
        # hands: mocap hand relative to its shoulder, scaled to the toon arm, re-attached at the toon shoulder
        al = (src.rest[I['LeftArm']] - src.rest[I['LeftForeArm']]).length + (src.rest[I['LeftForeArm']] - src.rest[I['LeftHand']]).length
        ka = .62 * sc / al
        Rc = Matrix.Rotation(cy, 3, 'Z'); RL = Matrix.Rotation(l0 * 2.2, 3, 'X') @ Matrix.Rotation(l1 * 2.2, 3, 'Y')
        for sd, ms in (('L', 'Right'), ('R', 'Left')):
            side = -1 if sd == 'L' else 1
            shl = Vector((side * ch.rw * .98 * .0, 0, 0))
            sh_local = Vector((0, 0, ch.L - crouch / sc)) + RL @ Vector((side * ch.rw * .98, 0, ch.TL * .84))
            rel = body(P[I[ms + 'Hand']]) - body(P[I[ms + 'Arm']])
            out['hand' + sd] = loc + Vector((0, 0, a.loc.z)) + Rc @ (sh_local * sc + rel * ka)
            fr = body(P[I[ms + 'Foot']]); fz = max(0.0, (P[I[ms + 'Foot']].z - gz)) * k
            out['foot' + sd] = (fr.x * k, fr.y * k, fz)
        return out

    def _ground(self, src):
        if not hasattr(src, '_gz'):
            I = src.idx; lows = []
            for f in range(0, src.n, max(1, src.n // 80)):
                R, P = src.fk(f); lows.append(min(P[I[n]].z for n in ('LeftFoot', 'RightFoot')))
            lows.sort(); src._gz = lows[len(lows) // 10]
        return src._gz

    def _fn(self, t):
        cur = 0
        for i, a in enumerate(self.acts):
            if a.t <= t: cur = i
        s = self._sample(self.acts[cur], t)
        if cur > 0 and t - self.acts[cur].t < self.acts[cur].blend:
            p = self._sample(self.acts[cur - 1], t); u = (t - self.acts[cur].t) / self.acts[cur].blend; u = u * u * (3 - 2 * u)
            for k_ in ('loc', 'handL', 'handR', 'footL', 'footR'):
                s[k_] = tuple(x + (y - x) * u for x, y in zip(p[k_], s[k_]))
            dy = (s['yaw'] - p['yaw'] + 180) % 360 - 180; s['yaw'] = p['yaw'] + dy * u
            s['crouch'] = p['crouch'] + (s['crouch'] - p['crouch']) * u
            s['lean'] = tuple(x + (y - x) * u for x, y in zip(p['lean'], s['lean']))
        if self.look:
            tg = self.look(t)
            if tg is not None:
                d = Vector(tg) - Vector(s['loc']); want = math.degrees(math.atan2(d.x, -d.y)) if d.length > 1e-3 else s['yaw']
                dy = (want - s['yaw'] + 180) % 360 - 180; s['head'][0] = max(-70, min(70, dy))
        f = dict(self.face(t))
        for (t0, t1, amp) in self.talk:
            if t0 <= t <= t1: f['op'] = max(f['op'], .03 + .07 * abs(math.sin((t - t0) * 15)) * amp)
        s['face'] = f
        return s

    def apply(self, t):
        self.t = t; self.ch.apply(t)
        for pr in self.props: pr(self, t)


def ride_fn(ch, seat_fn, face=None, rein=True):
    """sit a toon on a saddle: seat_fn(t) -> world matrix of the seat"""
    ft = H.expr_track(face or [(0, 'determined')])
    def fn(t):
        S = seat_fn(t); loc = S.translation - S.to_3x3() @ Vector((0, 0, (ch.L - .02) * ch.s))
        fwd = S.to_3x3() @ Vector((0, -1, 0)); yaw = math.degrees(math.atan2(fwd.x, -fwd.y))
        Rc = Matrix.Rotation(math.radians(yaw), 3, 'Z')
        out = dict(loc=tuple(loc), yaw=yaw, lean=(.02, 0), crouch=0.0, head=[0.0, 4.0, 0.0], face=ft(t))
        for sd, side in (('L', -1), ('R', 1)):
            out['foot' + sd] = (side * .4, -.08, -.12)
            if rein: out['hand' + sd] = tuple(S.translation + Rc @ Vector((side * .12, -.32, .18)))
        return out
    ch.fn = fn
