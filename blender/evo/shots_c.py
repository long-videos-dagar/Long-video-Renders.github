# exec'd inside story.py after shots_b: human evolution, modern times, the classroom finale

CAVEMAN = P('Caveman', '#9a6a3a', '#7a5028', hat=None, haircol='#2a1a10', beard=True, beardcol='#2a1a10', height=.98, boots='#5a3a20', belt='#4a2a14', collar=False)
SOFAGUY = P('Scroller', '#6a6a72', '#2a3a5a', hat=None, haircol='#1a120c', height=.95, boots='#e8e8e8', belt='#2a3a5a', collar=False)


def hominin_walk(sh, ter, start, yaw, kind='neander2', name='walker', scale=1.0, tint=None):
    b = CR.beast(sh, kind, name, clip=CR.SPEC[kind]['clips']['idle'], scale=scale)
    CR.rootmotion(b, 'idle', start, yaw, ter=ter)
    if tint:
        for o in b.m['objs']:
            for ms in getattr(o, 'material_slots', []):
                if ms.material and ms.material.node_tree:
                    m = ms.material.copy(); bs = m.node_tree.nodes.get('Principled BSDF')
                    if bs and not bs.inputs['Base Color'].is_linked: bs.inputs['Base Color'].default_value = tint
                    ms.material = m
    return b


def skin_statue(b, col=(.36, .24, .16, 1), hair=(.08, .06, .05, 1)):
    """untextured anatomical reconstructions (cream scans) -> warm skin with darker body hair tone"""
    m = bpy.data.materials.new(b.name + '_skin'); m.use_nodes = True; N = m.node_tree.nodes; bs = N['Principled BSDF']
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 60; mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'
    m.node_tree.links.new(nz.outputs['Fac'], mx.inputs['Factor']); mx.inputs[6].default_value = col; mx.inputs[7].default_value = hair
    m.node_tree.links.new(mx.outputs[2], bs.inputs['Base Color']); bs.inputs['Roughness'].default_value = .7
    try: bs.inputs['Subsurface Weight'].default_value = .15
    except Exception: pass
    for o in b.m['objs']:
        if o.type == 'MESH': o.data.materials.clear(); o.data.materials.append(m)


# ------------------------------------------------------------------ h: our own branch
def s_h01(sh):
    """from the primate forest across millions of years to the African savanna (drone at sunrise)"""
    w, ter = nat(sh, 'savanna'); fx, fy = fz(w)
    sh.camera(cam_fn([(0, G(ter, fx - 40, fy - 60, 30), G(ter, fx, fy + 80, 4), 22), (sh.dur, G(ter, fx + 10, fy - 40, 18), G(ter, fx + 10, fy + 80, 4), 24)], shake=.003), fstop=16)


def s_h02(sh):
    """a branching family tree of hominins: figures stand on the glowing branches of a tree drawn across the savanna"""
    w, ter = nat(sh, 'savanna'); fx, fy = fz(w)
    gm = bpy.data.materials.new('treeglow'); gm.use_nodes = True; bs = gm.node_tree.nodes['Principled BSDF']
    bs.inputs['Emission Color'].default_value = (1, .85, .5, 1); bs.inputs['Emission Strength'].default_value = 6
    base = Vector((fx, fy - 2)); tips = [(-9, 14), (-4, 18), (2, 20), (7, 16), (11, 10)]
    for k, (dx, dy) in enumerate(tips):
        mid = base + Vector((dx * .4, dy * .45)); pts = [Vector((*base, 0)), Vector((*mid, 0)), Vector((base.x + dx, base.y + dy, 0))]
        pts = [Vector((p.x, p.y, ter.z(p.x, p.y) + .06)) for p in pts]; T.lib.tube(f'branch{k}', pts, .12, m=gm)
    kinds = [('lucy', None), ('erectus', None), ('neander2', 'idle'), ('neander', 'idle'), ('neander2', 'idle')]
    for k, ((dx, dy), (kind, cl)) in enumerate(zip(tips, kinds)):
        b = still(sh, kind, (base.x + dx, base.y + dy), 0, ter, clip=cl, name=f'hom{k}', scale=1.0 if k != 4 else 1.25)
        if kind in ('lucy', 'erectus'): skin_statue(b)
    sh.camera(cam_fn([(0, G(ter, fx, fy - 7, 3.2), G(ter, fx, fy + 12, .9), 24), (sh.dur, G(ter, fx, fy - 5, 4.5), G(ter, fx, fy + 12, .8), 24)], shake=.002), fstop=11)


def s_h03(sh):
    """early human relatives walk upright across the savanna"""
    w, ter = nat(sh, 'savanna'); fx, fy = fz(w)
    for k in range(3): hominin_walk(sh, ter, (fx - 6 + k * .9, fy + 4 + k * .7), 90, name=f'australo{k}', scale=.85 + .08 * k)
    hz = ter.z(fx, fy + 4)
    sh.camera(cam_fn([(0, (fx - 6, fy - 2, hz + .7), (fx - 4, fy + 4.5, hz + .7), 35), (sh.dur, (fx + 3, fy - 2, hz + .7), (fx + 4, fy + 4.5, hz + .7), 35)], shake=.003), fstop=5)


def knap_action(b, at=0.0, rate=.5):
    """hammerstone strikes: the right forearm swings down every `rate` seconds (keyed NLA layer)"""
    if b.arm is None: return
    from mathutils import Euler
    fa = next((p for p in b.arm.pose.bones if p.name.lower().startswith('lowerarm_r') and 'scalecomp' not in p.name.lower()), None)
    up = next((p for p in b.arm.pose.bones if p.name.lower().startswith('upperarm_r') and 'scalecomp' not in p.name.lower()), None)
    if fa is None: return
    act = bpy.data.actions.new('knap'); ad = b.arm.animation_data or b.arm.animation_data_create(); keep = ad.action; ad.action = act
    n = int(30 / rate)
    for k in range(n):
        f0 = 1 + (at + k * rate) * 24
        for pb, a, c in ((fa, (0, -95, 0), (0, -40, 0)), (up, (0, 0, -35), (0, 0, -25))):      # raise the hammerstone, strike down
            if pb is None: continue
            pb.rotation_mode = 'QUATERNION'
            pb.rotation_quaternion = Euler([math.radians(v) for v in a]).to_quaternion(); pb.keyframe_insert('rotation_quaternion', frame=f0)
            pb.rotation_quaternion = Euler([math.radians(v) for v in c]).to_quaternion(); pb.keyframe_insert('rotation_quaternion', frame=f0 + rate * 24 * .25)
    ad.action = keep; tr = ad.nla_tracks.new(); st = tr.strips.new('knap', 1, act); st.blend_type = 'REPLACE'


def s_h04(sh):
    """early Homo knapping stone tools: flakes fly from the core"""
    w, ter = nat(sh, 'savanna'); fx, fy = fz(w); hz = ter.z(fx, fy)
    b = still(sh, 'neander', (fx, fy), 0, ter, clip='idle', name='knapper'); knap_action(b, 0.0, .55)
    core = T.lib.sphere('core', .08, (fx + .05, fy - .42, hz + .95), TR.simple_mat('flint', ('rock',), '#6a6460', .4), seg=12, rings=8); core.scale = (1, .7, .6)
    r = random.Random(3); cm = TR.simple_mat('flake', ('rock',), '#8a8480', .3); fl = []
    for k in range(40):
        o = T.box(f'flake{k}', (.02, .015, .004), (0, 0, -99), cm); fl.append((o, Vector((r.uniform(-1, 1), r.uniform(-1.2, .2), r.uniform(.6, 1.6))), .55 * (k // 2) + .14))
    def u(t):
        for o, v, ts in fl:
            k = t - ts; o.location = (Vector((fx + .05, fy - .42, hz + 1.0)) + v * k + Vector((0, 0, -4.9 * k * k))) if 0 < k < .5 else (0, 0, -99); o.rotation_euler = (k * 20, k * 13, 0)
    sh.updates.append(u)
    sh.camera(cam_fn([(0, (fx + 1.3, fy - 2.4, hz + 1.45), (fx, fy - .2, hz + 1.2), 35), (sh.dur, (fx + 1.0, fy - 2.0, hz + 1.4), (fx, fy - .3, hz + 1.1), 40)], shake=.002), fstop=3.5)


def thumbs_up(b, at=1.0):
    # bone axes measured on this rig (UE-style names): upperarm z- lifts the arm out, lowerarm y- folds the forearm up, finger y- curls
    CR.addpose(b, {'upperarm_r': (0, 0, -60), 'lowerarm_r': (0, -80, 0), 'index_0': (0, -80, 0), 'middle_0': (0, -80, 0), 'ring_0': (0, -80, 0),
                   'pinky_0': (0, -80, 0)}, at=at, ramp=.4)


def s_h05(sh):
    """a Neanderthal gives a thumbs-up from a cave"""
    w, _ = nat(sh, 'cave')
    b = still(sh, 'neander', (.3, 10.6), 0, None, clip='idle', name='neanderthal', z=0.0); thumbs_up(b, 3.5)
    bpy.context.scene.view_settings.exposure = .5
    sh.camera(cam_fn([(0, (-.6, 6.6, 1.5), (.3, 10.6, 1.4), 32), (sh.dur, (-.4, 7.6, 1.5), (.3, 10.6, 1.45), 36)], shake=.003), fstop=3.5)


def s_h06(sh):
    """early Homo sapiens appear: a small band walking at golden hour"""
    w, ter = nat(sh, 'savanna'); fx, fy = fz(w)
    for k in range(4): hominin_walk(sh, ter, (fx - 6 + k * 1.2, fy + 5 + (k % 2) * 1.2), 95, name=f'sapiens{k}', scale=1.25 + .05 * (k % 2))
    sh.camera(cam_fn([(0, G(ter, fx - 2, fy - 6, .6), G(ter, fx - 6, fy + 11, 1.4), 30), (sh.dur, G(ter, fx + 2, fy - 6, .7), G(ter, fx - 1, fy + 11, 1.4), 30)], shake=.003), fstop=4)


def s_h07(sh):
    """tools, hunting, talking, and painting animals on the cave wall by firelight"""
    w, _ = nat(sh, 'cave')
    p = still(sh, 'neander', (-1.0, 18.6), 180, None, clip='idle', name='painter', z=0.0)
    CR.addpose(p, {'upperarm_r': (0, 0, -80), 'lowerarm_r': (0, -25, 0)}, at=0.0, ramp=.01)
    still(sh, 'neander2', (2.6, 10.5), 220, None, clip='idle', name='watcher', z=0.0, scale=1.25)
    tl = bpy.data.lights.new('torch', 'POINT'); tl.energy = 900; tl.color = (1, .55, .22); tl.shadow_soft_size = .15
    to = bpy.data.objects.new('torch', tl); TR.coll().objects.link(to); to.location = (-1.6, 18.2, 1.9)
    sh.updates.append(lambda t: setattr(tl, 'energy', 900 * (1 + .15 * math.sin(t * 19) + .1 * math.sin(t * 31))))
    bpy.context.scene.view_settings.exposure = .6
    sh.camera(cam_fn([(0, (-3.5, 12, 1.6), (-.5, 19.5, 2.2), 28), (sh.dur, (-2.2, 14.5, 1.7), (-.5, 19.5, 2.3), 32)], shake=.003), fstop=4)


def s_h08(sh):
    """ancient settlements transform into modern cities (drone over the city, low sun)"""
    w, _ = nat(sh, 'city')
    sh.camera(cam_fn([(0, (0, -22, 18), (0, 70, 4), 24), (sh.dur, (0, -14, 26), (0, 80, 4), 24)], shake=.003), fstop=16)


# ------------------------------------------------------------------ t: now
def s_t01(sh):
    """time-lapse: sun races over the city, crane up to the skyline"""
    w, _ = nat(sh, 'city')
    sun = next((o for o in bpy.data.objects if o.type == 'LIGHT' and o.data.type == 'SUN'), None)
    if sun: sh.updates.append(lambda t: setattr(sun, 'rotation_euler', (math.radians(20 + 50 * t / sh.dur), 0, math.radians(90 + 140 * t / sh.dur))))
    sh.camera(cam_fn([(0, (0, -8, 1.8), (0, 40, 4), 22), (sh.dur, (0, -6, 26), (0, 60, 10), 22)], shake=.003), fstop=16)


def phone_prop(name, on_from=0.0):
    pm = TR.simple_mat(name + '_body', ('',), '#1a1a1e', .2, rough=.25)
    ph = T.box(name, (.075, .01, .15), (0, 0, -99), pm)
    sm = bpy.data.materials.new(name + '_screen'); sm.use_nodes = True; b = sm.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (0, 0, 0, 1); b.inputs['Emission Color'].default_value = (.55, .75, 1, 1)
    scr = T.box(name + '_scr', (.066, .002, .136), (0, -.006, 0), sm); scr.parent = ph; scr.location = (0, -.006, 0)
    return ph, b


def s_t02(sh):
    """a caveman pokes a smartphone; it lights up; he screams, throws it, then slowly picks it back up"""
    w, _ = nat(sh, 'cave'); x, y = 0.4, 4.0
    ch = toon(sh, 'CAVE', CAVEMAN)
    phone, scr = phone_prop('phone'); t_on, t_throw, t_pick = 1.0, 1.6, 2.9
    a = stand(sh, ch, (x, y), 180 + 180, '77_02', 1.0, face=[(0, 'confused'), (t_on, 'scream'), (t_throw + .5, 'worry'), (t_pick, 'suspicious')], z=0)
    land = Vector((x + 1.4, y - 1.6, .005))
    def mod(t, d):
        d['loc'] = (x, y, 0); d['yaw'] = 0
        hp = head_of(ch, -.3)
        if t < t_throw:
            d['handL'] = (x - .1, y - .45, 1.0); d['handR'] = (x + .02, y - .5, 1.02 + .02 * math.sin(t * 20))
        elif t < t_pick:
            u = ease((t - t_throw) / .25); d['handR'] = (x + .3, y - .2 * u, 1.3 + .5 * u); d['handL'] = (x - .3, y - .3, 1.1)
        else:
            u = ease((t - t_pick) / 1.0); d['crouch'] = .45 * math.sin(u * math.pi) if u < .5 else .45 * (1 - (u - .5) * 2) * 0 + .45 * math.sin(u * math.pi)
            d['handR'] = tuple(Vector((x + .3, y - .4, 1.0)).lerp(land + Vector((0, 0, .1)), math.sin(u * math.pi)))
        return d
    override(a, mod)
    def ph(t):
        bpy.context.view_layer.update(); hl = ch.hands['L'].matrix_world.translation
        scr.inputs['Emission Strength'].default_value = 4.0 if t > t_on else 0.0
        if t < t_throw: phone.location = hl + Vector((0, -.05, .05)); phone.rotation_euler = (math.radians(-70), 0, 0)
        elif t < t_throw + .5:
            k = (t - t_throw) / .5; p0 = Vector((x + .3, y - .3, 1.6)); phone.location = p0.lerp(land, k) + Vector((0, 0, 1.2 * math.sin(k * math.pi)))
            phone.rotation_euler = (k * 12, k * 7, 0)
        elif t < t_pick + .5: phone.location = land; phone.rotation_euler = (math.radians(90), 0, .4)
        else: phone.location = ch.hands['R'].matrix_world.translation; phone.rotation_euler = (math.radians(-60), 0, 0)
    sh.updates.append(ph)
    sh.camera(cam_fn([(0, (x + 1.8, y - 3.6, 1.5), (x + .3, y - .4, 1.1), 30), (sh.dur, (x + 1.6, y - 3.3, 1.45), (x + .4, y - .6, 1.0), 30)], shake=.003), fstop=4)
    sh.keylight(20, (1, .7, .45))


def rocket(name):
    w = TR.simple_mat(name + '_w', ('metal',), '#e8e8ea', .5, rough=.35); k = TR.simple_mat(name + '_k', ('metal',), '#2a2a2e', .5, rough=.4)
    root = bpy.data.objects.new(name, None); TR.coll().objects.link(root)
    for o in (T.cyl(name + '_b1', 1.8, 40, (0, 0, 20), w, v=32), T.cyl(name + '_band', 1.82, 2, (0, 0, 12), k, v=32), T.cyl(name + '_b2', 1.5, 14, (0, 0, 47), w, v=32)):
        o.parent = root
    nose = T.lib.sphere(name + '_nose', 1.5, (0, 0, 54), w, seg=24, rings=12); nose.scale = (1, 1, 2.4); nose.parent = root
    for j in range(4):
        f = T.box(f'{name}_fin{j}', (.2, 3, 5), (0, 0, 2.5), k); f.parent = root; a = j * math.pi / 2; f.location = (math.cos(a) * 2.2, math.sin(a) * 2.2, 2.5); f.rotation_euler = (0, 0, a)
    fm = bpy.data.materials.new(name + '_flame'); fm.use_nodes = True; b = fm.node_tree.nodes['Principled BSDF']
    b.inputs['Emission Color'].default_value = (1, .7, .3, 1); b.inputs['Emission Strength'].default_value = 80; b.inputs['Alpha'].default_value = .8
    fl = T.lib.sphere(name + '_flame', 1.5, (0, 0, -8), fm, seg=16, rings=10); fl.scale = (1, 1, 6); fl.parent = root
    return root, fl


def s_t03(sh):
    """a rocket climbs out of the atmosphere into space"""
    w, _ = nat(sh, 'space')
    root, fl = rocket('rocket'); s = .004; root.scale = (s, s, s)
    p0 = Vector((-1.2, -6.2, 6.0)); p1 = Vector((-.6, -9.5, 8.6))
    def u(t):
        k = ease(t / sh.dur); root.location = p0.lerp(p1, k); d = (p1 - p0).normalized(); root.rotation_mode = 'QUATERNION'; root.rotation_quaternion = d.to_track_quat('Z', 'Y')
        fl.scale = (1 + .2 * math.sin(t * 40), 1 + .2 * math.sin(t * 37), 6 + math.sin(t * 23))
    sh.updates.append(u)
    sh.camera(cam_fn([(0, (-2.0, -11.5, 7.6), (-1.0, -6.6, 6.6), 30), (sh.dur, (-1.6, -12.5, 9.2), (-.6, -9.3, 8.5), 30)], shake=.002,
                     focus=lambda t: Vector(root.location)), fstop=8)


def cat_png(path):
    from PIL import Image, ImageDraw
    im = Image.new('RGBA', (256, 512), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.ellipse([70, 180, 190, 300], fill=(240, 150, 60, 255)); d.ellipse([90, 120, 170, 200], fill=(240, 150, 60, 255))
    d.polygon([(95, 140), (105, 100), (125, 135)], fill=(240, 150, 60, 255)); d.polygon([(165, 140), (155, 100), (135, 135)], fill=(240, 150, 60, 255))
    for x in (110, 150): d.ellipse([x - 6, 150, x + 6, 162], fill=(20, 20, 20, 255))
    d.line([(180, 260), (230, 210)], fill=(240, 150, 60, 255), width=14)
    for x in (85, 120, 145, 175): d.line([(x, 290), (x - 10 + (x % 3) * 8, 340)], fill=(240, 150, 60, 255), width=12)
    im.save(path)


def s_t04(sh):
    """a human on a sofa scrolling, dead-eyed; on the phone a cat falls off a table"""
    stage(sh, 'livingroom'); import house as HS
    seat = Vector((HS.SOFA.x + .3, HS.SOFA.y - .02, 0)); dg = bpy.context.evaluated_depsgraph_get()
    hit = bpy.context.scene.ray_cast(dg, Vector((seat.x, seat.y, 1.6)), Vector((0, 0, -1))); sz = hit[1].z if hit[0] and .25 < hit[1].z < .7 else .45
    ch = toon(sh, 'SCROLL', SOFAGUY)
    a = stand(sh, ch, (seat.x, seat.y), 0, '77_02', 1.0, face=[(0, 'deadpan'), (4.6, 'laugh')], z=0)
    def mod(t, d):
        d['crouch'] = max(0.0, ch.L * ch.s - (sz + .09 * ch.s)); d['loc'] = (seat.x, seat.y, 0); d['yaw'] = 0
        for s_, sx in (('L', -1), ('R', 1)): d['foot' + s_] = (sx * .15, -.42, 0)
        d['lean'] = (-.08, 0); hp = head_of(ch, -.3)
        d['handL'] = tuple(hp + Vector((-.04, -.35, -.25))); d['handR'] = tuple(hp + Vector((.06, -.34, -.22 + .015 * math.sin(t * 6))))
        return d
    override(a, mod)
    os.makedirs('/tmp/evotex', exist_ok=True); cat_png('/tmp/evotex/cat.png')
    phone, scr = phone_prop('phone'); scr.inputs['Emission Strength'].default_value = 3.0
    m = bpy.data.objects['phone_scr'].data.materials[0]; N, L = m.node_tree.nodes, m.node_tree.links
    tc = N.new('ShaderNodeTexCoord'); mp = N.new('ShaderNodeMapping'); tx = N.new('ShaderNodeTexImage'); tx.image = bpy.data.images.load('/tmp/evotex/cat.png'); tx.extension = 'CLIP'
    L.new(tc.outputs['Generated'], mp.inputs['Vector']); L.new(mp.outputs['Vector'], tx.inputs['Vector'])
    mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.inputs[6].default_value = (.9, .85, .75, 1)
    L.new(tx.outputs['Alpha'], mx.inputs['Factor']); L.new(tx.outputs['Color'], mx.inputs[7]); L.new(mx.outputs[2], scr.inputs['Emission Color'])
    def u(t):
        bpy.context.view_layer.update(); phone.location = (ch.hands['L'].matrix_world.translation + ch.hands['R'].matrix_world.translation) / 2 + Vector((0, -.03, .06))
        phone.rotation_euler = (math.radians(-60), 0, 0)
        k = max(0.0, t - 2.5); mp.inputs['Location'].default_value = (0, -0.0 - 1.2 * k * k, 0); mp.inputs['Rotation'].default_value = (0, 0, k * 3)
    sh.updates.append(u)
    sh.camera(cam_fn([(0, (seat.x + .6, seat.y - 2.2, 1.15), (seat.x, seat.y, 1.0), 32), (sh.dur, (seat.x + .5, seat.y - 1.8, 1.1), (seat.x, seat.y, 1.0), 36)], shake=.002), fstop=3)
    sh.keylight(10)


def satellite(name):
    m = TR.simple_mat(name + '_m', ('metal',), '#d8c070', .3, rough=.3); p = TR.simple_mat(name + '_p', ('',), '#1a2a5a', .3, rough=.2)
    root = bpy.data.objects.new(name, None); TR.coll().objects.link(root)
    b = T.box(name + '_bus', (1, 1, 1.4), (0, 0, 0), m); b.parent = root
    for sx in (-1, 1):
        s = T.box(f'{name}_pan{sx}', (3, .05, 1.2), (sx * 2.2, 0, 0), p); s.parent = root
    return root


def s_t05(sh):
    """medicine, satellites, space: a satellite glides over the Earth"""
    w, _ = nat(sh, 'space'); s = satellite('sat'); s.scale = (.02,) * 3
    sh.updates.append(lambda t: (setattr(s, 'location', (-.3 + .12 * t, -7.4, 1.2)), setattr(s, 'rotation_euler', (.3, t * .2, .5))))
    sh.camera(cam_fn([(0, (-.6, -8.6, 1.4), (0, -7.4, 1.2), 30), (sh.dur, (-.2, -8.6, 1.45), (.2, -7.4, 1.2), 30)], shake=.001, focus=lambda t: Vector(s.location)), fstop=8)


def s_t06(sh):
    """evolution did not stop: animals on the savanna today"""
    w, ter = nat(sh, 'savanna'); fx, fy = fz(w)
    for k in range(5): go(sh, 'deer', [(fx - 9 + k * 2, fy + 10 + k * 2.5), (fx + 25, fy + 12 + k * 2)], ter, name=f'herdn{k}', phase=k * .3)
    sh.camera(cam_fn([(0, G(ter, fx - 4, fy - 8, 1.5), G(ter, fx, fy + 14, 2), 30), (sh.dur, G(ter, fx + 2, fy - 7, 1.6), G(ter, fx + 6, fy + 14, 2), 30)], shake=.003), fstop=6)


def s_t07(sh):
    """life keeps changing: city pigeons, populations adapting"""
    w, _ = nat(sh, 'city')
    flock(sh, 'pigeon', 9, (-14, 30, 4), (16, 10, 14), 0, sh.dur, seed=7, spread=3)
    for k in range(4): still(sh, 'pigeon', (-1 + k * .5, 6 + k * .3), 20 * k, None, clip='fly', anim=.01, name=f'groundpig{k}', z=0.0)
    sh.camera(cam_fn([(0, (0, -2, 1.2), (0, 20, 5), 26), (sh.dur, (1, 0, 1.6), (2, 20, 8), 26)], shake=.003), fstop=8)


# ------------------------------------------------------------------ the classroom finale
def s_m04(sh):
    """teacher: sometimes the smallest things make the biggest difference"""
    stage(sh, 'classroom'); board(sh, 1.0, 1.0)
    ch, a = teacher(sh, (0.8, 3.0), 10, [(0, 'smug')])
    def cam(t):
        h = head_of(ch); return (h + Vector((-.4, -2.2, -.1)), h, 46, 0, h, .003)
    sh.camera(cam, fstop=2.6); sh.keylight(10)


def s_m05(sh):
    """Rohan wakes up: 'Like homework, sir?' teacher stares; Rohan slowly lowers his head back onto the desk"""
    stage(sh, 'classroom'); board(sh, 1.0, 1.0)
    ch, a = seated(sh, 'ROHAN', ROHAN, [(0, 'sleep'), (.3, 'grin'), (2.4, 'deadpan'), (3.2, 'sleep')], talk_who='rohan')
    x, y = SEATS['ROHAN']; sleep = lambda t: 1 - ease(t / .35) + ease((t - 2.6) / 1.2)
    def mod(t, d):
        s = min(1.0, sleep(t)); d['lean'] = (.03 + .47 * s, 0); d['head'] = [0, 25 * s, 0]
        d['handL'] = (x - .18, y - .12 - .1 * (1 - s), .78); d['handR'] = (x + .18, y - .12 - .1 * (1 - s), .78); return d
    override(a, mod); class_extras(sh, 9)
    def cam(t):
        h = head_of(ch); return (h + Vector((-.7, 1.9, .2)), h, 42, 0, h, .003)
    sh.camera(cam, fstop=2.6); sh.keylight(10)


def two_shot(sh, who_a, who_b, cam_off=(2.4, 3.2, 1.65), tgt=(-.4, -.6, 1.0)):
    cam_path(sh, [(0, cam_off, tgt, 26), (sh.dur, tuple(Vector(cam_off) + Vector((-.2, -.1, 0))), tgt, 28)])


def s_l05(sh):
    """Priya: so my legs are ancient fish technology? teacher: one way of putting it. Priya: I want a refund."""
    stage(sh, 'classroom'); board(sh, 1.0, 1.0)
    ch, a = seated(sh, 'PRIYA', PRIYA, [(0, 'confused'), (3.4, 'deadpan'), (5.4, 'angry')], talk_who='priya')
    teacher(sh, (1.0, 3.0), 20, [(0, 'bored'), (3.6, 'smirk')]); seated(sh, 'KEVIN', KEVIN, [(0, 'watch')]); class_extras(sh, 10)
    def cam(t):
        h = head_of(ch)
        if 3.4 < t < 5.4:
            th = head_of(sh.chars['TEACHER']); return (th + Vector((-.5 * .6, -1.3, -.05)), th, 38, 0, th, .003)
        return (h + Vector((.7, 1.9, .15)), h, 44, 0, h, .003)
    sh.camera(cam, fstop=2.6); sh.keylight(10)


def s_p12(sh):
    """Kevin: can we keep one as a class pet? teacher: you can't even keep your attendance above fifty percent"""
    stage(sh, 'classroom'); board(sh, 1.0, 1.0)
    ch, a = seated(sh, 'KEVIN', KEVIN, [(0, 'grin'), (2.6, 'shock'), (4.6, 'sad')], talk_who='kevin',
                   hands=lambda t, d: dict(handR=(SEATS['KEVIN'][0] + .22, SEATS['KEVIN'][1] - .45, 1.8)) if t < 2.3 else {})
    teacher(sh, (0.6, 3.0), 10, [(0, 'deadpan'), (2.4, 'smirk')]); class_extras(sh, 11)
    def cam(t):
        if t > 2.4:
            th = head_of(sh.chars['TEACHER']); return (th + Vector((.3 * .6, -1.3, -.05)), th, 38, 0, th, .003)
        h = head_of(ch); return (h + Vector((.6, 1.8, .2)), h, 42, 0, h, .003)
    sh.camera(cam, fstop=2.6); sh.keylight(10)


def s_d06(sh):
    """Sam: so a pigeon attack is technically a dinosaur attack? teacher: yes. and the pigeon usually wins."""
    stage(sh, 'classroom'); board(sh, 1.0, 1.0)
    ch, a = seated(sh, 'SAM', SAM, [(0, 'wow'), (4.4, 'shock'), (6.4, 'worry')], talk_who='sam')
    teacher(sh, (-0.6, 3.0), -10, [(0, 'bored'), (4.2, 'deadpan')]); seated(sh, 'KEVIN', KEVIN, [(0, 'watch'), (5.6, 'laugh')]); class_extras(sh, 12)
    def cam(t):
        if 4.2 < t < 6.2:
            th = head_of(sh.chars['TEACHER']); return (th + Vector((-.3 * .6, -1.3, -.05)), th, 38, 0, th, .003)
        h = head_of(ch); return (h + Vector((-.6, 1.8, .15)), h, 42, 0, h, .003)
    sh.camera(cam, fstop=2.6); sh.keylight(10)


def s_n05(sh):
    """Kevin: so we evolved from monkeys? teacher: common ancestors... Kevin: cousins? teacher: very distant. stop asking about the T-rex"""
    stage(sh, 'classroom'); board(sh, 1.0, 1.0)
    ch, a = seated(sh, 'KEVIN', KEVIN, [(0, 'confused'), (8.1, 'wow'), (12.4, 'sad')], talk_who='kevin')
    teacher(sh, (0.4, 3.0), 10, [(0, 'bored'), (9.4, 'deadpan'), (12.0, 'angry')]); seated(sh, 'PRIYA', PRIYA, [(0, 'bored')]); class_extras(sh, 13)
    T_ = [(0, 'k'), (2.1, 't'), (8.2, 'k'), (9.4, 't')]
    def cam(t):
        who = [w_ for t_, w_ in T_ if t >= t_][-1]
        if who == 't':
            th = head_of(sh.chars['TEACHER']); return (th + Vector((.4 * .6, -1.3, -.05)), th, 38, 0, th, .003)
        h = head_of(ch); return (h + Vector((.6, 1.9, .2)), h, 42, 0, h, .003)
    sh.camera(cam, fstop=2.6); sh.keylight(10)


def s_b01(sh):
    """back out of the chalk eye (iris in compose): Kevin staring at the board, mouth open"""
    stage(sh, 'classroom'); board(sh, 1.0, 1.0)
    ch, a = seated(sh, 'KEVIN', KEVIN, [(0, 'shock')]); class_extras(sh, 14)
    eye = Vector((BX(.30 + 19 * 15.5 / 2400), BOARD_Y - .1, 1.75 + (.5 - (.26 + 15.3 * 15.5 / 1200)) * 2.2))
    def cam(t):
        h = head_of(ch); u = ease(t / (sh.dur * .8)); p = (eye + Vector((0, -.3, 0))).lerp(h + Vector((.15, 1.1, .05)), u) + Vector((0, 0, .9 * math.sin(math.pi * u)))
        tg = eye.lerp(h, u)
        return (p, tg, 40, 0, tg, .002)
    sh.camera(cam, fstop=2.8); sh.keylight(8)


def s_b02(sh):
    stage(sh, 'classroom'); board(sh, 1.0, 1.0)
    ch, a = teacher(sh, (0.2, 3.0), 180 + 180, [(0, 'smug')]); class_extras(sh, 15); seated(sh, 'KEVIN', KEVIN, [(0, 'watch')])
    cam_path(sh, [(0, (-.8, -3.0, 1.6), (0.2, 3.0, 1.5), 30), (sh.dur, (-.6, -2.2, 1.6), (0.2, 3.0, 1.55), 34)])
    sh.keylight(8)


def s_b03(sh):
    """Kevin: after billions of years... we still have to do homework?"""
    stage(sh, 'classroom'); board(sh, 1.0, 1.0)
    ch, a = seated(sh, 'KEVIN', KEVIN, [(0, 'determined'), (6.6, 'worry')], talk_who='kevin')
    teacher(sh, (0.4, 3.0), 10, [(0, 'bored'), (5.8, 'smirk')]); class_extras(sh, 16)
    def cam(t):
        if 5.8 < t < 6.8:
            th = head_of(sh.chars['TEACHER']); return (th + Vector((.3 * .6, -1.3, -.05)), th, 38, 0, th, .003)
        h = head_of(ch); return (h + Vector((.6, 1.9 - .4 * ease(t / 5.8), .2)), h, 40, 0, h, .003)
    sh.camera(cam, fstop=2.6); sh.keylight(10)


def s_b04(sh):
    """the teacher drops an enormous stack of notebooks; the room shakes; a pencil rolls off the desk (rigid-body style)"""
    stage(sh, 'classroom'); board(sh, 1.0, 1.0)
    TX, TY = 2.6, sh.w['y1'] - 1.6; dg = bpy.context.evaluated_depsgraph_get()
    hit = bpy.context.scene.ray_cast(dg, Vector((TX, TY, 2.0)), Vector((0, 0, -1))); desk_top = hit[1].z if hit[0] and .5 < hit[1].z < 1.1 else .76
    ch, a = teacher(sh, (TX - .1, TY + .7), 0, [(0, 'smug')])
    def hands(t, d):
        u = ease(t / .5) if t < .6 else 1.0; z = desk_top + .75 - .62 * u
        return dict(handL=(TX - .25, TY, z), handR=(TX + .25, TY, z)) if t < .7 else {}
    override(a, lambda t, d: (d.update(hands(t, d)) or d))
    r = random.Random(4); books = []
    cols = ['#c83a2a', '#2a6ab0', '#3aa070', '#e8b020', '#8a4ab0', '#e86a2a']
    for k in range(26):
        m = TR.simple_mat(f'nb{k}', ('',), r.choice(cols), .2); b = T.box(f'notebook{k}', (.3, .22, .022), (0, 0, -99), m); books.append((b, r.uniform(-.02, .02), r.uniform(-.06, .06)))
    pen = T.cyl('pencil', .005, .17, (0, 0, -99), TR.simple_mat('pencilm', ('',), '#f0c020', .2), rot=(0, math.pi / 2, 0), v=6)
    tl = .5
    def u(t):
        for k, (b, dx, rz) in enumerate(books):
            z_rest = desk_top + .011 + k * .0225
            if t < tl: z = z_rest + .62 * (1 - ease(t / tl))
            else:
                k2 = t - tl; z = z_rest + .02 * math.exp(-k2 * 10) * abs(math.sin(k2 * 40))
            b.location = (TX + dx * min(1, t / tl), TY, z); b.rotation_euler = (0, 0, rz)
        k2 = max(0.0, t - tl - .15); px = .35 + .25 * k2 * k2 * 4          # the pencil rolls (accelerating) to the edge, then falls
        if px < .62: pen.location = (TX + px, TY - .13, desk_top + .006); pen.rotation_euler = (k2 * 30, math.pi / 2, 0)
        else:
            tf = k2 - math.sqrt(.27); zf = desk_top + .006 - 4.9 * max(0, tf) ** 2
            pen.location = (TX + .62 + .1 * max(0, tf), TY - .13, max(.005, zf)); pen.rotation_euler = (k2 * 30, math.pi / 2, 0)
    sh.updates.append(u)
    seated(sh, 'KEVIN', KEVIN, [(0, 'watch'), (.5, 'shock')]); class_extras(sh, 17, faces=('shock', 'worry', 'shock'))
    sh.camera(cam_fn([(0, (TX - 1.6, TY - 2.0, 1.4), (TX, TY, desk_top + .2), 30), (sh.dur, (TX - 1.4, TY - 1.8, 1.35), (TX + .2, TY, desk_top + .15), 32)], shake=.002,
                     quake=lambda t: .025 * math.exp(-(t - tl) * 6) if t > tl else 0), fstop=4)
    sh.keylight(8)


def s_b05(sh):
    stage(sh, 'classroom'); board(sh, 1.0, 1.0)
    ch, a = teacher(sh, (0.2, 2.6), 0, [(0, 'smug')])
    def cam(t):
        h = head_of(ch); return (h + Vector((-.3, -1.9 + .2 * ease(t / sh.dur), -.15)), h, 46, 0, h, .003)
    sh.camera(cam, fstop=2.6); sh.keylight(10)


def s_b06(sh):
    """the class groans; Rohan wakes, sees the stack, goes back to sleep out of principle"""
    stage(sh, 'classroom'); board(sh, 1.0, 1.0)
    ch, a = seated(sh, 'ROHAN', ROHAN, [(0, 'sleep'), (.6, 'shock'), (1.4, 'deadpan'), (2.0, 'sleep')])
    x, y = SEATS['ROHAN']; s_ = lambda t: 1 - ease((t - .4) / .3) + ease((t - 1.7) / .8)
    def mod(t, d):
        s = max(0.0, min(1.0, s_(t))); d['lean'] = (.03 + .47 * s, 0); d['head'] = [0, 25 * s, 0]; return d
    override(a, mod)
    seated(sh, 'KEVIN', KEVIN, [(0, 'sad')]); seated(sh, 'PRIYA', PRIYA, [(0, 'sad')]); seated(sh, 'SAM', SAM, [(0, 'worry')]); class_extras(sh, 18, faces=('sad', 'worry', 'sad'))
    cam_path(sh, [(0, (3.2, 2.6, 1.8), (.6, -1.0, .9), 28), (sh.dur, (3.0, 2.4, 1.75), (.9, -.9, .9), 32)])
    sh.keylight(8)


def s_b07(sh):
    """narrator over the class: slow pull back from the room"""
    stage(sh, 'classroom'); board(sh, 1.0, 1.0)
    teacher(sh, (1.6, 3.2), 180 + 180, [(0, 'smug')])
    seated(sh, 'KEVIN', KEVIN, [(0, 'bored')]); seated(sh, 'PRIYA', PRIYA, [(0, 'idle')]); seated(sh, 'SAM', SAM, [(0, 'idle')])
    seated(sh, 'ROHAN', ROHAN, [(0, 'sleep')], asleep=True); class_extras(sh, 19)
    cam_path(sh, [(0, (-1.0, -2.6, 1.7), (0, 2.0, 1.1), 28), (sh.dur, (-3.4, -3.8, 2.6), (0, 2.0, 1.0), 20)])
    sh.keylight(6)


def s_b08(sh):
    """pull out from the planet: Earth from space, calm and blue"""
    w, _ = nat(sh, 'space')
    sh.camera(cam_fn([(0, (-.8, -7.2, 1.5), (-.4, -6.3, 1.2), 30), (sh.dur, (0, -24, 3), (0, 0, 0), 35)], shake=.001), fstop=16)


def s_b09(sh):
    """END CARD over the Earth (text in compose)"""
    w, _ = nat(sh, 'space')
    sh.camera(cam_fn([(0, (0, -24, 3), (0, 0, 0), 35), (sh.dur, (0, -25, 3.1), (0, 0, 0), 35)], shake=.001), fstop=16)
