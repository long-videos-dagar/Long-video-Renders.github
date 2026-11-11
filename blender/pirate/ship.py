"""Procedural wooden sailing ship (hero ship + pirate ship). Local frame: bow = +Y, up = +Z, deck at z = 2.6. Waterline z = 0."""
import os
import bpy, math, numpy as np
from mathutils import Vector, Matrix
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import lib
from lib import lin, mat, coll, box, cyl, sphere, torus, lathe, smooth_tube
from common_p import *
import sea as seamod

L2 = 17.0; DECK = 2.6

def grid_mesh(name, V, n, m, mat_=None, c=None, closed_u=False, smooth=True):
    """V: (n*m,3) vertices of an n x m grid -> quad mesh."""
    me = bpy.data.meshes.new(name); N = n * m
    me.vertices.add(N); me.vertices.foreach_set('co', np.asarray(V, np.float32).ravel())
    idx = np.arange(N).reshape(n, m); a = idx[:-1, :-1].ravel(); b = idx[:-1, 1:].ravel(); cc = idx[1:, 1:].ravel(); d = idx[1:, :-1].ravel()
    nf = len(a); me.loops.add(nf * 4); me.polygons.add(nf)
    me.loops.foreach_set('vertex_index', np.stack([a, b, cc, d], 1).ravel().astype(np.int32))
    me.polygons.foreach_set('loop_start', (np.arange(nf) * 4).astype(np.int32)); me.polygons.foreach_set('loop_total', np.full(nf, 4, np.int32))
    me.update(calc_edges=True); me.polygons.foreach_set('use_smooth', np.full(nf, smooth, bool))
    uv = me.uv_layers.new(name='UVMap'); u = np.repeat(np.linspace(0, 1, n), m).reshape(n, m); v = np.tile(np.linspace(0, 1, m), n).reshape(n, m)
    loops = me.loops; uvs = np.zeros((len(loops), 2), np.float32)
    quad = np.stack([a, b, cc, d], 1).ravel()
    uvs[:, 0] = u.ravel()[quad]; uvs[:, 1] = v.ravel()[quad]; uv.data.foreach_set('uv', uvs.ravel())
    o = bpy.data.objects.new(name, me); (c or bpy.context.scene.collection).objects.link(o)
    if mat_: me.materials.append(mat_)
    return o

def wood(name, c1, c2, scale=(2, 40, 2)):
    if os.environ.get('USE_PH'):
        try: return lib.mat_ph(name, 'wood', 'plank', scale=1.6, tint=c1, avoid=('floor', 'parquet', 'tile'), bump=.6, rough_mul=1.0)
        except Exception as e: lib.log('PH wood failed', e)
    from common import wood_mat
    return wood_mat(name, c1, c2, scale=1.0, stretch=scale)

def sheer(y): return 3.7 + 1.5 * (abs(y) / L2) ** 3 + (.4 if y < -10 else 0)
def half_w(y):
    if y > 4: return 4.6 * math.sqrt(max(0.0, 1 - ((y - 4) / 13.2) ** 2)) + .02
    if y < -12: return 4.6 - (-12 - y) * .25
    return 4.6
def keel(y): return -2.6 + (1.8 * ((y - 4) / 13.0) ** 2 if y > 4 else 0) + (.9 * ((-12 - y) / 5.0) ** 2 if y < -12 else 0)

class Ship:
    def __init__(self, tag='hero', hull='#5a3a22', hull2='#3a2414', sail='#d9cfb5', trim='#c0a050', flag=None, detail=1.0, scale=1.0, pirate=False):
        self.tag = tag; self.scale = scale; self.pirate = pirate
        self.root = bpy.data.objects.new('ship_' + tag, None); bpy.context.scene.collection.objects.link(self.root); self.root.scale = (scale,) * 3
        C = coll('Ship_' + tag)
        def P(o, parent=None):
            for cc in list(o.users_collection): cc.objects.unlink(o)
            C.objects.link(o); o.parent = parent or self.root; return o
        self.P = P
        # ---- hull: stations along y, U section
        ys = np.linspace(-L2, L2, 70); us = np.linspace(-1, 1, 25)
        V = []
        for y in ys:
            w = half_w(y); zt = sheer(y); zk = keel(y)
            for u in us:
                z = zt - (zt - zk) * (1 - u * u) ** .72; V.append((w * u * (1 + .04 * (1 - abs(u))), y, z))
        hm = wood('hullw', hull, hull2, scale=(1, 60, 1))
        h = grid_mesh('hull', np.array(V), len(ys), len(us), hm); P(h)
        # hull planks band stripes (strakes) via a second material is skipped; add wales (thick bands)
        for zo, w_ in ((1.6, .22), (3.2, .26)):
            pts = []
            for y in np.linspace(-L2 + .3, L2 - .6, 40):
                pts.append((half_w(y) * 1.02, y, min(zo + (sheer(y) - 3.7) * .9, sheer(y) - .15)))
            for sx in (-1, 1):
                t = smooth_tube('wale', [Vector((sx * p[0], p[1], p[2])) for p in pts[::3]], w_ * .5, mat('wale', hull2, rough=.6), c=C); P(t)
        # transom
        zt0, zk0 = sheer(-L2), keel(-L2); w0 = half_w(-L2)
        tr = box('transom', (2 * w0, .3, zt0 - zk0), (0, -L2 - .1, (zt0 + zk0) / 2), hm, bevel=.05, c=C); P(tr)
        # deck
        VD = []
        ys2 = np.linspace(-L2 + .2, L2 - .5, 50)
        for y in ys2:
            w = half_w(y) * .985
            for u in np.linspace(-1, 1, 9): VD.append((w * u, y, DECK - 0.02 + (0.0)))
        dm = wood('deckw', '#9a7448', '#6a4a2a', scale=(1, 30, 1))
        d = grid_mesh('deck', np.array(VD), len(ys2), 9, dm); P(d)
        # quarterdeck + forecastle blocks
        qm = wood('quarter', '#8a6338', '#5a3a1e', scale=(1, 30, 1))
        q = box('quarterdeck', (8.6, 7.0, 1.3), (0, -13.3, DECK + .65), qm, bevel=.05, c=C); P(q)
        qd = box('qdeck_top', (8.4, 6.9, .08), (0, -13.3, DECK + 1.3), dm, c=C); P(qd)
        fc = box('forecastle', (7.0, 3.6, 1.0), (0, 13.2, DECK + .5), qm, bevel=.05, c=C); P(fc)
        # rails and posts
        rm = mat('rail', hull2, rough=.6)
        for sx in (-1, 1):
            pts = [Vector((sx * half_w(y) * .995, y, sheer(y) + .12)) for y in np.linspace(-L2 + .2, L2 - .8, 40)]
            P(smooth_tube('rail', pts[::2], .1, rm, c=C))
            for y in np.arange(-15, 15.5, 2.0):
                z0 = DECK if abs(y) < 10 else DECK + 1.1
                P(box('post', (.14, .14, sheer(y) + .1 - z0), (sx * half_w(y) * .97, y, (sheer(y) + .1 + z0) / 2), rm, c=C))
        # masts, yards, sails
        mm = mat('mast', '#6b4a2a', rough=.7)
        self.sails = []
        mast_def = [(8.0, 22.0, 3), (-1.0, 25.0, 3), (-9.5, 15.0, 2)] if detail >= .5 else [(5.0, 18.0, 2)]
        sailm = None
        if os.environ.get('USE_PH'):
            try: sailm = lib.mat_ph('sail' + tag, 'fabric', 'canvas', scale=1.2, tint=sail, rough=.95, bump=.5, avoid=('leather',))
            except Exception as e: lib.log('PH sail failed', e)
        if sailm is None: sailm = mat('sail' + tag, sail, rough=.95)
        self.sail_mat = sailm
        for (my, mh, ns) in mast_def:
            mo = cyl('mast', .36, mh, (0, my, DECK + mh / 2), mm, seg=14, c=C); P(mo)
            for k in range(ns):
                zc = DECK + mh * (.34 + .27 * k); wid = (10.5 - 2.6 * k) * (mh / 24.0 + .3) * .9; ht = mh * (.24 if k < ns - 1 else .18)
                yard = cyl('yard', .16, wid, (0, my, zc + ht / 2), mm, seg=10, rot=(0, math.pi / 2, 0), c=C); P(yard)
                self.sails.append(self.make_sail(my, zc, wid * .96, ht, k, sailm, C))
            if detail >= 1.0:
                for sx in (-1, 1):   # shrouds with ratlines
                    top = Vector((sx * .3, my, DECK + mh * .62)); bot = Vector((sx * half_w(my) * .95, my + .5, DECK + .9))
                    P(smooth_tube('shroud', [bot, top], .035, mat('rope', '#7a6a4a', rough=.95), c=C))
                    for kk in range(1, 10):
                        a = bot.lerp(top, kk / 10.0); b = bot.lerp(top, kk / 10.0) + Vector((0, -.0, 0)); 
                        P(smooth_tube('rat', [a + Vector((0, -.5, 0)), a + Vector((0, .5, 0))], .02, mat('rope', '#7a6a4a', rough=.95), c=C))
        # bowsprit and jib
        bs = cyl('bowsprit', .22, 9.0, (0, L2 + 1.2, DECK + 2.4), mm, seg=12, rot=(math.radians(-75), 0, 0), c=C); P(bs)
        # rigging stays
        for (a, b) in (((0, 8.0, DECK + 20), (0, L2 + 4.0, DECK + 5.5)), ((0, -1.0, DECK + 23), (0, 8.0, DECK + 20)), ((0, -9.5, DECK + 13), (0, -1.0, DECK + 23))):
            P(smooth_tube('stay', [Vector(a), Vector(b)], .04, mat('rope', '#6a5a3a', rough=.95), c=C))
        # lantern, helm, cannons, barrels, cabin windows
        self.lanterns = []
        for sx in (-1, 1):
            if detail >= .6:
                lm = mat('lant', '#ffcf80', rough=.3, emit='#ffa840', emit_strength=14)
                lt = sphere('lantern', .22, (sx * 3.6, -16.4, DECK + 3.6), lm, seg=12, rings=8, c=C); P(lt)
                self.lanterns.append(lt)
        for k in range(5 if detail >= .6 else 0):
            for sx in (-1, 1):
                y = -6 + k * 3.2
                P(cyl('cannon', .26, 2.0, (sx * 3.3, y, DECK + .5), mat('iron', '#1e1f22', rough=.35, metal=.7), seg=14, rot=(0, math.pi / 2, 0), c=C))
                P(box('carriage', (1.2, 1.1, .35), (sx * 3.6, y, DECK + .2), rm, bevel=.03, c=C))
        if detail >= .6:
            wheel = torus('helm', .75, .06, (0, -11.3, DECK + 1.9), mat('helm', '#4a2f1a', rough=.5), rot=(math.pi / 2, 0, 0), seg=24, mseg=8, c=C); P(wheel)
            for i in range(8): 
                a = i * math.pi / 4; P(cyl('spoke', .035, 1.6, (0, -11.3, DECK + 1.9), mat('helm', '#4a2f1a', rough=.5), seg=6, rot=(0, a, 0), c=C))
            for sx in (-1, 1):
                for k in range(3):
                    wm = mat('cabwin', '#ffd98a', rough=.2, emit='#ffb050', emit_strength=6)
                    P(box('cabin_window', (.55, .08, .7), (sx * 1.8 + (0 if k != 1 else -sx * 1.8) , -L2 - .28, DECK + 1.0 + 0.0), wm, bevel=.02, c=C)) if k == 1 or True else None
        # flag
        if flag:
            self.flag = self.make_flag(flag, C, my=-9.5, mh=15.0)
        self.barrel_pos = Vector((-3.4, 2.5, DECK))
        self.objs = C

    def make_sail(self, my, zc, wid, ht, k, m, C):
        nx, nz = 16, 14
        gx = np.linspace(-.5, .5, nx); gz = np.linspace(0, 1, nz)
        gxm, gzm = np.meshgrid(gx, gz, indexing='ij')
        base = np.zeros((nx, nz, 3), np.float32)
        taper = 1.0 - .12 * gzm   # narrower at the bottom
        base[..., 0] = gxm * wid * taper; base[..., 1] = my + .35; base[..., 2] = zc + ht * (1 - gzm)
        o = grid_mesh('sail', base.reshape(-1, 3), nx, nz, m, C); self.P(o)
        o.data.materials.append(m)
        mt = o.data.materials[0]
        return dict(o=o, base=base, my=my, k=k, wid=wid, ht=ht)

    def flutter(self, t, wind=1.0, amp=1.0, seed=0):
        """per-frame sail billow + flutter (analytic), local space"""
        for s in self.sails:
            b = s['base']; nx, nz, _ = b.shape
            X = b[..., 0]; Z = b[..., 2]; u = (X / s['wid'] + .5); v = (Z - Z.min()) / max(1e-3, Z.max() - Z.min())
            bil = (1.0 - (2 * u - 1) ** 2) * (.4 + .6 * np.sin(np.pi * v * .9 + .3))
            ph = seed + s['k'] * 1.7 + s['my'] * .3
            fl = np.sin(t * (7.0 + 3 * wind) + u * 9 + v * 6 + ph) * .4 + np.sin(t * (11.0 + 4 * wind) - u * 5 + v * 13 + ph * 1.3) * .22
            dy = amp * (bil * (1.2 + .3 * np.sin(t * 2.2 + ph)) + fl * (.35 + .3 * v)) * wind
            V = b.copy(); V[..., 1] += dy; V[..., 2] -= amp * .25 * bil * wind
            s['o'].data.vertices.foreach_set('co', V.reshape(-1).astype(np.float32)); s['o'].data.update()

    def make_flag(self, col, C, my, mh):
        nx, nz = 10, 6
        base = np.zeros((nx, nz, 3), np.float32)
        for i in range(nx):
            for j in range(nz): base[i, j] = (0, my - i * .45, DECK + mh + .3 + j * .22)
        fm = mat('flag', col, rough=.9); o = grid_mesh('flag', base.reshape(-1, 3), nx, nz, fm, C); self.P(o)
        return dict(o=o, base=base)

    def flag_update(self, t):
        if not hasattr(self, 'flag'): return
        b = self.flag['base']; V = b.copy(); i = np.arange(b.shape[0])[:, None] * np.ones((1, b.shape[1]))
        V[..., 0] += np.sin(t * 9 - i * .9) * .18 * (i / 9.0)
        self.flag['o'].data.vertices.foreach_set('co', V.reshape(-1).astype(np.float32)); self.flag['o'].data.update()

    # ---- pose from the sea (heave / pitch / roll from real wave heights)
    def pose(self, waves, x, y, heading_deg, t, boost=1.15):
        h = math.radians(heading_deg); f = np.array([math.sin(-h), math.cos(-h)]); r = np.array([f[1], -f[0]])
        pts = {'bow': (x + f[0] * 14, y + f[1] * 14), 'stern': (x - f[0] * 14, y - f[1] * 14), 'port': (x - r[0] * 4.5, y - r[1] * 4.5), 'star': (x + r[0] * 4.5, y + r[1] * 4.5)}
        z = {k: float(waves.height(v[0], v[1], t)[0]) for k, v in pts.items()}
        heave = (z['bow'] + z['stern'] + z['port'] + z['star']) / 4
        pitch = math.atan2(z['bow'] - z['stern'], 28.0) * boost; roll = math.atan2(z['star'] - z['port'], 9.0) * boost
        self.root.location = (x, y, heave - .6); self.root.rotation_mode = 'XYZ'
        self.root.rotation_euler = (pitch, -roll, h)
        return heave, pitch, roll
