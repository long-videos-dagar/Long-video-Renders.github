"""Realistic avatars (Ready Player Me base body) driven by motion-capture clips from the RPM animation library.
 * costume/skin/hair re-painted per character (no branding), hats/bandana added as geometry on the head bone
 * mocap plays through NLA strips (deterministic for any frame)
 * facial control: jaw / brows / smile shape keys driven by expression tracks."""
import bpy, math, os, io, numpy as np, subprocess, sys, tempfile
from mathutils import Vector, Matrix, Euler
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import lib
from lib import lin, mat, coll
from common_p import *

AVATARS = []
_BASE = {}

def _atlas_regions():
    # (x0,y0,x1,y1) in a 1024 px atlas, origin top-left (as viewed)
    return dict(shirt=(0, 512, 512, 1024), trousers=(512, 0, 768, 256), shoes=(512, 256, 1024, 768), face=(0, 0, 512, 512))

def paint_texture(src_png, out_png, shirt=(215, 208, 190), trousers=(70, 60, 52), shoes=(48, 32, 22), hair=(40, 28, 20), skin_mul=(1.0, 1.0, 1.0), beard=None, beard_col=(40, 30, 24), stubble=False, shirt_stripes=None):
    from PIL import Image, ImageFilter, ImageDraw
    im = Image.open(src_png).convert('RGB'); W = np.asarray(im).astype(np.float32); R = _atlas_regions()
    def lum(a): return (a[..., 0] * .3 + a[..., 1] * .59 + a[..., 2] * .11)
    def recolor(box, col, lift=1.0, remove_bright=None, floor=0.0):
        x0, y0, x1, y1 = box; sub = W[y0:y1, x0:x1].copy(); L = lum(sub)
        if remove_bright is not None:     # remove printed branding: inpaint bright print pixels from surrounding fabric (normalised blur)
            m = L > remove_bright
            md = np.asarray(Image.fromarray(m.astype(np.uint8) * 255).filter(ImageFilter.MaxFilter(15)))[..., None] > 0
            keep = (~md).astype(np.float32)
            def gb(a, r):
                from scipy.ndimage import gaussian_filter
                return gaussian_filter(a, (r, r, 0) if a.ndim == 3 else (r, r))
            fill = sub.copy()
            for r in (6, 14, 30):
                num = gb((sub * keep).astype(np.float32), r); den = gb(keep[..., 0].astype(np.float32), r)[..., None]
                est = num / np.maximum(den, 1e-3); fill = np.where((den > .08) & md, est, fill)
                keep = np.where(md & (den > .08), 1.0, keep)
            sub = np.where(md, fill, sub); L = lum(sub)
        base = np.percentile(L[L > 8], 60) if (L > 8).any() else 40
        k = np.clip(L / max(1.0, base), 0, 2.2)[..., None]
        out = np.array(col, np.float32)[None, None, :] * (k * .78 + .22 * lift)
        W[y0:y1, x0:x1] = np.clip(np.where((L > 3)[..., None], out, sub), 0, 255)
    recolor(R['shirt'], shirt, remove_bright=95)
    if shirt_stripes:
        x0, y0, x1, y1 = R['shirt']
        for yy in range(y0, y1, shirt_stripes[1] * 2):
            W[yy:yy + shirt_stripes[1], x0:x1] = W[yy:yy + shirt_stripes[1], x0:x1] * .35 + np.array(shirt_stripes[0], np.float32) * .65
    recolor(R['trousers'], trousers)
    recolor(R['shoes'], shoes)
    # hair + skin in the head block
    x0, y0, x1, y1 = R['face']; sub = W[y0:y1, x0:x1]; L = lum(sub)
    r, g, b = sub[..., 0], sub[..., 1], sub[..., 2]
    is_hair = (L < 85) & (r < 120) & (np.arange(sub.shape[0])[:, None] < 330)
    base = np.percentile(L[is_hair], 60) if is_hair.any() else 40
    k = np.clip(L / max(1.0, base), .3, 2.0)[..., None]
    hair_out = np.array(hair, np.float32)[None, None, :] * k
    sub[:] = np.where(is_hair[..., None], hair_out, sub * np.array(skin_mul, np.float32)[None, None, :])
    W[y0:y1, x0:x1] = np.clip(sub, 0, 255)
    img = Image.fromarray(W.astype(np.uint8))
    if beard:
        ov = Image.new('RGBA', img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(ov); S = 1024 / 768.0
        def E(x0, y0, x1, y1, a=235): d.ellipse([x0 * S, y0 * S, x1 * S, y1 * S], fill=(*beard_col, a))
        if beard in ('full', 'grey'):
            E(128, 192, 280, 258); E(112, 140, 146, 232, 215); E(246, 140, 280, 232, 215)   # jaw + sideburns
            E(158, 172, 226, 184, 235)                                                    # moustache
            d.ellipse([160 * S, 184 * S, 222 * S, 204 * S], fill=(0, 0, 0, 0))           # keep the lips
        ov = ov.filter(ImageFilter.GaussianBlur(5 if not stubble else 3))
        n = (np.random.RandomState(4).rand(img.size[1], img.size[0]) * 60 + 195).astype(np.uint8)
        a = np.asarray(ov).copy(); a[..., 3] = (a[..., 3].astype(np.float32) * (n / 255.0)).astype(np.uint8)
        img = Image.alpha_composite(img.convert('RGBA'), Image.fromarray(a, 'RGBA')).convert('RGB')
    img.save(out_png)

def base_glb():
    """merged avatar+mocap GLB path (built once)"""
    return os.environ.get('RPM_GLB', '/tmp/avatar_anims.glb')

def import_base():
    if _BASE: return _BASE
    n0 = set(bpy.data.objects.keys()); a0 = set(bpy.data.actions.keys())
    bpy.ops.import_scene.gltf(filepath=base_glb())
    new = [bpy.data.objects[k] for k in bpy.data.objects.keys() if k not in n0]
    arm = next(o for o in new if o.type == 'ARMATURE'); mesh = next(o for o in new if o.type == 'MESH' and o.name.startswith('Wolf3D'))
    for o in new:
        if o not in (arm, mesh): bpy.data.objects.remove(o)
    acts = {a.name: a for a in bpy.data.actions if a.name not in a0}
    for o in (arm, mesh):
        for c in list(o.users_collection): c.objects.unlink(o)
    _BASE.update(arm=arm, mesh=mesh, acts=acts)
    return _BASE

class Avatar:
    def __init__(self, cid, name, shirt=(215, 208, 190), trousers=(70, 60, 52), shoes=(48, 32, 22), hair=(40, 28, 20), skin_mul=(1, 1, 1), beard=None, beard_col=(40, 30, 24),
                 hat=None, bandana=None, scale=1.0, shirt_stripes=None, parent=None):
        B = import_base(); self.cid = cid; self.name = name
        self.arm = B['arm'].copy(); self.arm.data = B['arm'].data.copy(); self.arm.name = f'{cid}_arm'; coll('Humans').objects.link(self.arm)
        self.mesh = B['mesh'].copy(); self.mesh.data = B['mesh'].data.copy(); self.mesh.name = f'{cid}_body'; coll('Humans').objects.link(self.mesh)
        self.mesh.parent = self.arm
        for md in self.mesh.modifiers:
            if md.type == 'ARMATURE': md.object = self.arm
        self.acts = B['acts']
        # texture
        src = os.path.join(tempfile.gettempdir(), 'rpm_src_tex.png')
        if not os.path.exists(src):
            im = [i for i in bpy.data.images if i.name.startswith('glTF_Embedded')][0]
            im.filepath_raw = src; im.file_format = 'PNG'; im.save()
        out = os.path.join(tempfile.gettempdir(), f'rpm_{cid}.png')
        paint_texture(src, out, shirt, trousers, shoes, hair, skin_mul, beard, beard_col, shirt_stripes=shirt_stripes)
        m = bpy.data.materials.new('av_' + cid); m.use_nodes = True; N, L = m.node_tree.nodes, m.node_tree.links; b = N['Principled BSDF']
        t = N.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(out); t.image.colorspace_settings.name = 'sRGB'; t.interpolation = 'Cubic'
        L.new(t.outputs['Color'], b.inputs['Base Color']); b.inputs['Roughness'].default_value = .62; b.inputs['Specular IOR Level'].default_value = .3
        b.inputs['Subsurface Weight'].default_value = .06; b.inputs['Subsurface Radius'].default_value = (.5, .22, .12)
        self.mesh.data.materials.clear(); self.mesh.data.materials.append(m)
        self.arm.scale = (scale,) * 3
        self.hat = hat; self.bandana = bandana
        self.props = []
        self.arm.animation_data_create()
        self.track = self.arm.animation_data.nla_tracks.new()
        self.fn = lambda T: {}
        AVATARS.append(self)
        self._face_setup()
        self.add_headwear(hat, bandana, hair)

    def play(self, clip, t_start_global, T0, fps, speed=1.0, loop=True, offset=0.0, length=None):
        """schedule mocap clip: starts at global time t_start_global (seconds), clip time offset `offset`s"""
        act = self.acts[clip]; f0, f1 = act.frame_range
        scene_frame = lambda T: (T - T0) * fps + 1
        s = self.track.strips.new(f'{clip}_{len(self.track.strips)}', int(round(scene_frame(t_start_global))), act)
        s.action_frame_start = f0 + offset * 30.0; s.action_frame_end = f1
        s.scale = fps / (30.0 * speed)
        s.use_sync_length = False
        if loop: s.repeat = 40
        s.blend_type = 'REPLACE'; s.extrapolation = 'HOLD' if not loop else 'HOLD_FORWARD'
        return s

    # ---------------------------------------------------------------- headwear
    def head_top(self):
        me = self.mesh.data; co = np.array([v.co[:] for v in me.vertices]); zmax = co[:, 2].max(); return zmax
    def add_headwear(self, hat, bandana, hair):
        ht = self.head_top()
        def child(o, loc):
            o.parent = self.arm; o.parent_type = 'BONE'; o.parent_bone = 'Head'
            # bone-local: place via world offset computed from rest pose
            hb = self.arm.data.bones['Head']; world_rest = hb.head_local
            o.matrix_parent_inverse = Matrix.Translation(-(Vector(world_rest))) @ Matrix.Identity(4)
            o.location = Vector(loc) ; return o
        # position expressed in armature rest space; parent inverse makes it track the head bone
        def add(o, loc_arm):
            hb = self.arm.data.bones['Head']
            o.parent = self.arm; o.parent_type = 'BONE'; o.parent_bone = 'Head'
            o.matrix_parent_inverse = (hb.matrix_local @ Matrix.Translation((0, hb.length, 0))).inverted()
            o.location = Vector(loc_arm)
            for c in list(o.users_collection): c.objects.unlink(o)
            coll('Humans').objects.link(o); self.props.append(o); return o
        # head centre in armature space
        hc = Vector((0, 0.0, ht - .13))
        if hat == 'tricorn':
            hm = mat('hat' + self.cid, '#17171d', rough=.65); gold = mat('goldtrim', '#c9a23a', rough=.3, metal=1.0)
            z = ht - .035
            crown = lib.lathe('crown', [(0, 0), (.086, 0), (.083, .075), (0, .08)], seg=24, m=hm, c=coll('Humans')); add(crown, (0, .005, z + .01))
            for i, a in enumerate((0, 2.094, 4.189)):
                br = lib.sphere('brim', 1, (0, 0, 0), hm, seg=20, rings=8, scale=(.125, .125, .014), c=coll('Humans')); add(br, (math.sin(a) * .085, .005 - math.cos(a) * .085, z + .012))
            bd = lib.sphere('band', .09, (0, 0, 0), gold, seg=24, rings=4, scale=(1, 1, .05), c=coll('Humans')); add(bd, (0, .005, z + .022))
            fe = lib.sphere('feather', .02, (0, 0, 0), mat('plume', '#a82a24', rough=.8), seg=10, rings=6, scale=(.4, 1.4, 3.0), c=coll('Humans')); add(fe, (.09, .0, z + .09)); fe.rotation_euler = (0, .6, 0)
        if bandana:
            bn = mat('bandana' + self.cid, bandana, rough=.85)
            z = ht - .075
            band = lib.torus('band', .088, .011, (0, 0, 0), bn, seg=28, mseg=8, c=coll('Humans')); band.scale = (1, 1.08, 1); add(band, (0, .006, z))
            top = lib.sphere('bantop', 1, (0, 0, 0), bn, seg=28, rings=12, scale=(.088, .094, .046), c=coll('Humans')); add(top, (0, .004, z + .028))
            kn = lib.sphere('knot', .03, (0, 0, 0), bn, seg=12, rings=8, c=coll('Humans')); add(kn, (.06, .095, z - .005))
            for sx in (.02, .045):
                tl = lib.sphere('tail', .02, (0, 0, 0), bn, seg=10, rings=6, scale=(.5, .35, 2.2), c=coll('Humans')); add(tl, (.06 + sx * .3, .105, z - .045 - sx * .5))


    # ---------------------------------------------------------------- garments (skinned shells over the body: deform with the mocap)
    def _attach(self, o, bone, loc):
        hb = self.arm.data.bones[bone]
        o.parent = self.arm; o.parent_type = 'BONE'; o.parent_bone = bone
        o.matrix_parent_inverse = (hb.matrix_local @ Matrix.Translation((0, hb.length, 0))).inverted(); o.location = Vector(loc)
        for c in list(o.users_collection): c.objects.unlink(o)
        coll('Humans').objects.link(o); self.props.append(o); return o

    def garment(self, name, color, groups, offset=.01, open_front=0.0, zmin=0.0, zmax=9.0, rough=.85, weave=1.0, bump=.4, sleeves=True, edge=None, skirt=0.0):
        import bmesh
        src = self.mesh; me = src.data.copy()
        ob = src.copy(); ob.data = me; ob.name = f'{self.cid}_{name}'; coll('Humans').objects.link(ob); ob.parent = self.arm
        vg = {i: g.name for i, g in enumerate(src.vertex_groups)}
        bm = bmesh.new(); bm.from_mesh(me); dl = bm.verts.layers.deform.active
        def dom(v):
            w = v[dl]; return vg[max(w.keys(), key=lambda k: w[k])] if len(w) else ''
        kill = []
        for f in bm.faces:
            c = f.calc_center_median(); d = [dom(v) for v in f.verts]; ok = sum(x in groups for x in d) * 2 > len(d)
            if ok and not (zmin <= c.z <= zmax): ok = False
            if ok and not sleeves and abs(c.x) > .2: ok = False
            if ok and open_front and c.y > -.02 and abs(c.x) < open_front and c.z > 1.05: ok = False
            if not ok: kill.append(f)
        bmesh.ops.delete(bm, geom=kill, context='FACES')
        bm.verts.ensure_lookup_table(); bm.normal_update()
        for v in bm.verts: v.co += v.normal * offset
        if skirt:
            names = {g.name: g.index for g in src.vertex_groups}
            lx = self.arm.data.bones['LeftUpLeg'].head_local.x
            ring = [e for e in bm.edges if e.is_boundary and all(v.co.z < 1.15 and abs(v.co.x) < .3 and v.co.z > .8 for v in e.verts)]
            cur = ring; steps = 4
            for k in range(1, steps + 1):
                r = bmesh.ops.extrude_edge_only(bm, edges=cur); nv = [g for g in r['geom'] if isinstance(g, bmesh.types.BMVert)]
                ne = [g for g in r['geom'] if isinstance(g, bmesh.types.BMEdge) and g.is_boundary]
                t = k / steps
                for v in nv:
                    v.co.z -= skirt / steps; cx, cy = v.co.x, v.co.y
                    v.co.x += cx * .10 * (1 / steps); v.co.y += cy * .10 * (1 / steps)
                    w = v[dl]
                    for key in list(w.keys()): del w[key]
                    up = names['LeftUpLeg'] if cx * lx > 0 else names['RightUpLeg']
                    w[names['Hips']] = 1 - .55 * t; w[up] = .55 * t
                cur = ne
        for v in bm.verts: pass
        bm.to_mesh(me); bm.free()
        for md in ob.modifiers:
            if md.type == 'ARMATURE': md.object = self.arm
        if me.shape_keys:
            ob.shape_key_clear()
        sm = ob.modifiers.new('sub', 'SUBSURF'); sm.levels = 1; sm.render_levels = 1
        for p in me.polygons: p.use_smooth = True
        m = bpy.data.materials.new(f'g_{self.cid}_{name}'); m.use_nodes = True; N, L = m.node_tree.nodes, m.node_tree.links; b = N['Principled BSDF']
        b.inputs['Base Color'].default_value = (*lin(color), 1) if isinstance(color, str) else (*[ (c / 255.0) ** 2.2 for c in color], 1)
        b.inputs['Roughness'].default_value = rough; b.inputs['Sheen Weight'].default_value = .4
        tc = N.new('ShaderNodeTexCoord'); mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (260 * weave, 260 * weave, 260 * weave)
        w1 = N.new('ShaderNodeTexWave'); w1.wave_type = 'BANDS'; w1.inputs['Scale'].default_value = 1; w1.inputs['Distortion'].default_value = 1.5; w1.inputs['Detail'].default_value = 3
        nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 900 * weave; nz.inputs['Detail'].default_value = 3
        bp = N.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = bump; bp.inputs['Distance'].default_value = .002
        L.new(tc.outputs['Object'], mp.inputs['Vector']); L.new(mp.outputs['Vector'], nz.inputs['Vector']); L.new(nz.outputs['Fac'], bp.inputs['Height']); L.new(bp.outputs['Normal'], b.inputs['Normal'])
        me.materials.clear(); me.materials.append(m); self.props.append(ob); return ob

    def costume(self, kind):
        M = ('Spine', 'Spine1', 'Spine2', 'LeftShoulder', 'RightShoulder'); AR = ('LeftArm', 'RightArm', 'LeftForeArm', 'RightForeArm'); HP = ('Hips',)
        co = np.array([v.co[:] for v in self.mesh.data.vertices])
        def chest_y(z, tol=.04):
            sel = (np.abs(co[:, 0]) < .06) & (np.abs(co[:, 2] - z) < tol) & (co[:, 1] > -.05); return co[sel, 1].max() if sel.any() else .1
        gold = mat('gold_btn', '#d4aa3c', rough=.28, metal=1.0); leather = mat('belt_lea', '#2a1a10', rough=.5)
        if kind == 'sailor':
            self.garment('shirt', (222, 214, 192), M + AR + HP, offset=.007, zmin=1.0, rough=.92, weave=1.2)           # long linen shirt
            self.garment('vest', (88, 58, 36), M, offset=.016, open_front=.032, zmin=1.0, zmax=1.5, sleeves=False, rough=.55, weave=.6, bump=.6)  # leather vest
            for zz in (1.18, 1.27, 1.36):
                pass
            self.belt(leather, gold, 1.02)
        elif kind == 'captain':
            self.garment('shirt', (240, 236, 224), M + AR + HP, offset=.006, zmin=1.0, rough=.9, weave=1.4)
            self.garment('coat', (24, 38, 74), M + AR + HP, offset=.02, open_front=.07, zmin=.95, rough=.8, weave=.8, bump=.7, skirt=.30)
            for side in (-1, 1):
                for zz in (1.18, 1.27, 1.36, 1.45):
                    b = lib.sphere('btn', .011, (0, 0, 0), gold, seg=12, rings=8, c=coll('Humans')); self._attach(b, 'Spine2', (side * .075, chest_y(zz) + .026, zz - 1.52)) if False else None
            self.belt(leather, gold, 1.0)
            cr = lib.sphere('cravat', .05, (0, 0, 0), mat('cravat', '#f1ece0', rough=.9), seg=14, rings=8, scale=(1, .8, .9), c=coll('Humans')); self._attach(cr, 'Neck', (0, chest_y(1.5, .05) + .005, 1.52))
        elif kind == 'crew':
            self.garment('shirt', (176, 164, 138), M + AR + HP, offset=.007, zmin=1.0, rough=.92, weave=1.2)
            self.garment('vest', (64, 70, 82), M, offset=.016, open_front=.03, zmin=1.0, zmax=1.5, sleeves=False, rough=.8, weave=.7)
            self.belt(leather, gold, 1.02)
    def belt(self, leather, gold, z):
        co = np.array([v.co[:] for v in self.mesh.data.vertices]); sel = (np.abs(co[:, 2] - z) < .03) & (np.abs(co[:, 0]) < .25) & (np.abs(co[:, 1]) < .3)
        if not sel.any(): return
        w = np.abs(co[sel, 0]).max(); d = (co[sel, 1].max() - co[sel, 1].min()) / 2; cy = (co[sel, 1].max() + co[sel, 1].min()) / 2
        t = lib.torus('belt', 1, .016, (0, 0, 0), leather, seg=32, mseg=8, c=coll('Humans')); t.scale = (w + .02, d + .02, 1.6)
        self._attach(t, 'Hips', (0, cy, z - self.arm.data.bones['Hips'].tail_local.z + self.arm.data.bones['Hips'].tail_local.z - self.arm.data.bones['Hips'].head_local.z * 0))
        bk = lib.box('buckle', (.05, .012, .045), (0, 0, 0), gold, c=coll('Humans')); self._attach(bk, 'Hips', (0, cy + d + .03, z))

    # ---------------------------------------------------------------- face
    def _face_setup(self):
        me = self.mesh.data; self.fk = {}
        if not me.shape_keys: self.mesh.shape_key_add(name='Basis')
        co = np.array([v.co[:] for v in me.vertices]); uv = me.uv_layers.active.data; vuv = np.zeros((len(co), 2))
        for p in me.polygons:
            for li in p.loop_indices: vuv[me.loops[li].vertex_index] = uv[li].uv
        self.co0 = co; self.vuv = vuv
        # image-space (top origin, 768 preview units) -> uv: u = x/768 ; v = 1 - y/768
        P = lambda x, y: (x / 768.0, 1 - y / 768.0)
        def mask(cx, cy, rx, ry):
            u, v = P(cx, cy); d = ((vuv[:, 0] - u) / (rx / 768.0)) ** 2 + ((vuv[:, 1] - v) / (ry / 768.0)) ** 2
            return np.clip(1 - d, 0, 1) ** .8
        # head vertices only (z high)
        head = co[:, 2] > np.percentile(co[:, 2], 100) - .33
        self.head_mask = head
        mouth_c = mask(190, 186, 60, 22) * head; lower = mask(190, 205, 70, 40) * head * (co[:, 2] < np.median(co[mouth_c > .1, 2]) + .004 if (mouth_c > .1).any() else 1)
        upper = mask(190, 178, 55, 14) * head
        brow_l = mask(160, 112, 45, 16) * head; brow_r = mask(237, 112, 45, 16) * head
        corner_l = mask(150, 186, 20, 16) * head; corner_r = mask(232, 186, 20, 16) * head
        self.masks = dict(mouth=mouth_c, lower=lower, upper=upper, brow_l=brow_l, brow_r=brow_r, cl=corner_l, cr=corner_r, uvx=vuv[:, 0] * 768)
        self.fk_names = ('jaw', 'browdown', 'browup', 'smile', 'frown', 'wide', 'angry_l', 'angry_r')
        z = np.zeros_like(co)
        def key(name, delta):
            sk = self.mesh.shape_key_add(name=name, from_mix=False); sk.data.foreach_set('co', (co + delta).astype(np.float32).ravel()); sk.slider_min = 0; sk.slider_max = 1.5; self.fk[name] = sk
        d = z.copy(); d[:, 2] -= .026 * lower; d[:, 1] += .004 * lower; d[:, 2] += .003 * upper; key('jaw', d)
        d = z.copy(); d[:, 2] -= .012 * (brow_l + brow_r); key('browdown', d)
        d = z.copy(); d[:, 2] += .014 * (brow_l + brow_r); key('browup', d)
        d = z.copy(); d[:, 2] += .010 * (corner_l + corner_r); d[:, 0] += np.where(co[:, 0] > 0, .006, -.006) * (corner_l + corner_r); key('smile', d)
        d = z.copy(); d[:, 2] -= .008 * (corner_l + corner_r); key('frown', d)
        d = z.copy(); d[:, 2] += .008 * (brow_l + brow_r); d[:, 2] -= .004 * mouth_c; key('wide', d)
        # angry: inner brow ends down, outer up (inner = nearer the face centre x)
        inner_l = np.clip(1 - np.abs(vuv[:, 0] * 768 - 190 + 0) / 60.0, 0, 1)   # not used, kept simple below
        def tilt(bm, sign):
            d = z.copy(); w = np.clip((vuv[:, 0] * 768 - 190) * sign / 45.0, -1, 1)    # + at outer end
            d[:, 2] += .012 * bm * w * -1 * -1; return d
        key('angry_l', tilt(brow_l, -1)); key('angry_r', tilt(brow_r, 1))
        self.fkv = {k: 0.0 for k in self.fk}

    def set_face(self, e):
        v = dict(jaw=e.get('op', 0) * 25, browdown=max(0, -e.get('br', 0)) * 60, browup=max(0, e.get('br', 0)) * 60, smile=max(0, e.get('sm', 0)) * 35, frown=max(0, -e.get('sm', 0)) * 35,
                 wide=max(0, e.get('lid', .85) - .95) * 4, angry_l=max(0, e.get('bt', 0)), angry_r=max(0, e.get('bt', 0)))
        for k, sk in self.fk.items(): sk.value = float(min(1.5, v.get(k, 0)))

def on_frame(scene, *a):
    pass
