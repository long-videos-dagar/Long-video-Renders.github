"""Gerstner ocean: analytic, deterministic per frame (any frame renderable on any machine). Used for the mesh, the ship motion and
the oil-film wave damping (small waves are damped first, like a real surface film)."""
import bpy, math, numpy as np
sys_path_done = False
G = 9.81

class Waves:
    def __init__(self, storm=1.0, wind=0.0, seed=3):
        rnd = np.random.RandomState(seed)
        # wavelength, amplitude/λ ratio  (storm: big groups + chop)
        lam = np.array([95, 62, 41, 27, 18, 12, 8, 5.2, 3.4, 2.2, 1.4, .9])
        rat = np.array([.040, .036, .034, .032, .030, .028, .026, .024, .022, .02, .018, .016]) * storm
        self.lam = lam; self.k = 2 * math.pi / lam; self.a = lam * rat
        self.th = np.radians(wind + rnd.uniform(-38, 38, len(lam)))          # direction (0 = +Y)
        self.d = np.stack([np.sin(self.th), np.cos(self.th)], 1)
        self.w = np.sqrt(G * self.k); self.ph = rnd.uniform(0, 6.28, len(lam))
        self.Q = np.clip(0.85 / (self.k * self.a * len(lam) * .5 + 1e-6), 0, 1.0) * .55   # choppiness (loops avoided)
        # damping weight by wavelength: short waves are killed first by a surface film
        self.small = np.clip(1.15 - lam / 24.0, 0.05, 1.0)
        self.oil = None            # (cx, cy, R) callable of t or None
        self.rogue = None          # callable(t) -> (cy, A) : one huge wave front travelling +Y (the gigantic wave of scene 3)

    def mask(self, x, y, t):
        if self.oil is None: return 0.0
        st = self.oil(t)
        if st is None: return 0.0
        cx, cy, R = st
        r = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
        return np.clip(1.0 - (r - R * .6) / (R * .5 + 1e-6), 0.0, 1.0)

    def eval(self, x, y, t, want_foam=False, kmin=0.0, kmax=1e9, fade=None):
        """x,y arrays (rest positions). returns X,Y,Z (displaced), foam."""
        X = x.copy(); Y = y.copy(); Z = np.zeros_like(x)
        m = self.mask(x, y, t); jxx = np.ones_like(x); jyy = np.ones_like(x); jxy = np.zeros_like(x)
        for i in range(len(self.k)):
            if self.k[i] < kmin or self.k[i] > kmax: continue
            amp = self.a[i] * (1.0 - m * self.small[i] * .93)
            if fade is not None and self.k[i] > fade[3]:
                cheb = np.maximum(np.abs(x - fade[0]), np.abs(y - fade[1])); amp = amp * np.clip((1 - cheb / fade[2]) / .22, 0, 1)
            ph = self.k[i] * (self.d[i, 0] * x + self.d[i, 1] * y) - self.w[i] * t + self.ph[i]
            c = np.cos(ph); s = np.sin(ph)
            qa = self.Q[i] * amp
            X += qa * self.d[i, 0] * c; Y += qa * self.d[i, 1] * c; Z += amp * s
            if want_foam:
                f = self.Q[i] * self.k[i] * amp * s
                jxx -= f * self.d[i, 0] ** 2; jyy -= f * self.d[i, 1] ** 2; jxy -= f * self.d[i, 0] * self.d[i, 1]
        if self.rogue is not None:
            cy, A = self.rogue(t)
            if A > 0.01:
                d = y - cy; sig = np.where(d > -10, 22.0, 46.0)
                rz = A * np.exp(-(((d + 10) / sig) ** 2)) - .28 * A * np.exp(-(((d - 48) / 26) ** 2))
                Z = Z + rz; Y = Y - .45 * np.clip(rz, 0, None)
        foam = None
        if want_foam:
            J = jxx * jyy - jxy ** 2
            foam = np.clip((0.55 - J) * 2.0, 0, 1) * (1.0 - m * .96)
            foam = np.maximum(foam, np.clip((Z - self.a.sum() * .5) * .8, 0, .45) * (1 - m))
            if self.rogue is not None:
                cy, A = self.rogue(t)
                if A > .01: foam = np.maximum(foam, .6 * np.clip((Z - A * .7) / (A * .25), 0, 1) * np.clip(1 - (np.abs(y - cy - 6) / 20), 0, 1))
        return X, Y, Z, foam

    def height(self, x, y, t):
        x = np.atleast_1d(np.asarray(x, float)); y = np.atleast_1d(np.asarray(y, float))
        z = np.zeros_like(x); m = self.mask(x, y, t)
        for i in range(len(self.k)):
            amp = self.a[i] * (1.0 - m * self.small[i] * .93)
            z += amp * np.sin(self.k[i] * (self.d[i, 0] * x + self.d[i, 1] * y) - self.w[i] * t + self.ph[i])
        if self.rogue is not None:
            cy, A = self.rogue(t)
            if A > .01:
                d = y - cy; sig = np.where(d > -10, 22.0, 46.0); z = z + A * np.exp(-(((d + 10) / sig) ** 2)) - .28 * A * np.exp(-(((d - 48) / 26) ** 2))
        return z

class Patch:
    """A grid of the ocean around (cx, cy). Updated per frame with numpy."""
    def __init__(self, waves, cx, cy, size, n, name='sea', mat=None, kmin=0.0, col=None, hole=None, zoff=0.0, kmax=1e9, fade_k=None):
        self.w = waves; self.kmin = kmin; self.kmax = kmax; self.fade = (cx, cy, size / 2, fade_k) if fade_k else None; self.n = n; self.zoff = zoff
        ax = np.linspace(-size / 2, size / 2, n); gx, gy = np.meshgrid(ax + cx, ax + cy)
        self.x = gx.ravel(); self.y = gy.ravel()
        me = bpy.data.meshes.new(name); self.me = me
        me.vertices.add(n * n); me.vertices.foreach_set('co', np.zeros(n * n * 3, np.float32))
        idx = np.arange(n * n).reshape(n, n); a = idx[:-1, :-1].ravel(); b = idx[:-1, 1:].ravel(); c = idx[1:, 1:].ravel(); d = idx[1:, :-1].ravel()
        if hole is not None:
            hx, hy, hs = hole; cxs = (self.x[a] + self.x[c]) / 2; cys = (self.y[a] + self.y[c]) / 2
            keep = ~((np.abs(cxs - hx) < hs) & (np.abs(cys - hy) < hs)); a, b, c, d = a[keep], b[keep], c[keep], d[keep]
        loops = np.stack([a, b, c, d], 1).ravel(); nf = len(a)
        me.loops.add(nf * 4); me.polygons.add(nf)
        me.loops.foreach_set('vertex_index', loops.astype(np.int32)); me.polygons.foreach_set('loop_start', (np.arange(nf) * 4).astype(np.int32))
        me.polygons.foreach_set('loop_total', np.full(nf, 4, np.int32)); me.update(calc_edges=True)
        me.polygons.foreach_set('use_smooth', np.ones(nf, bool))
        self.foam = me.attributes.new('foam', 'FLOAT', 'POINT')
        self.o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(self.o)
        if mat: me.materials.append(mat)
        self.update(0.0)

    def update(self, t):
        X, Y, Z, F = self.w.eval(self.x, self.y, t, want_foam=True, kmin=self.kmin, kmax=self.kmax, fade=self.fade)
        if self.kmax < .2: F = F * 0.0
        co = np.stack([X, Y, Z + self.zoff], 1).astype(np.float32).ravel()
        self.me.vertices.foreach_set('co', co); self.foam.data.foreach_set('value', F.astype(np.float32)); self.me.update()
