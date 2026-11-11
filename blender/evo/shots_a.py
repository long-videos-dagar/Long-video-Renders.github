# exec'd inside story.py: young Earth, microbes, oxygen, Ediacaran, Cambrian, Devonian seas, the move onto land
# (all names from story.py are available here)

def cam_fn(keys, focus=None, roll=0.0, shake=.003, lens_fn=None, quake=None):
    """keyed glide (t, pos, target, lens); focus(t) -> point to keep sharp; quake(t) -> metres of fast ground shake"""
    base = cam_keys(keys, roll=roll, shake=0.0)
    def fn(t):
        p, tg, ln, rl, fc, sk = base(t); sk = shake(t) if callable(shake) else shake
        if lens_fn: ln = lens_fn(t)
        if quake:
            q = quake(t); p = p + Vector((math.sin(t * 37) + .5 * math.sin(t * 71), math.sin(t * 29 + 1), math.sin(t * 43 + 2) + .5 * math.sin(t * 83))) * q
        return (p, tg, ln, rl, focus(t) if focus else tg, sk)
    return fn


def nat(sh, world, **kw):
    """nature shots: no motion blur (python-driven motion isn't keyed anyway, and blur on wind-deformed forests triples memory)"""
    w = stage(sh, world, **kw); sh.updates.append(lambda t: setattr(bpy.context.scene.render, 'use_motion_blur', False))
    sh.ter = w.get('ter') if isinstance(w, dict) else None
    return w, sh.ter


def G(ter, x, y, dz=0.0):
    return (x, y, ter.z(x, y) + dz)


def at_after(t0, fn):
    """wrap an emitter update so it starts at shot time t0"""
    return lambda t: fn(max(0.0, t - t0))


# ground speeds (m/s at registry size) that keep feet planted - measured once on CI (zoo test) instead of per shot
STRIDE = {('stego', 'walk'): 2.23, ('raptor', 'walk'): 1.49, ('tricera', 'walk'): .76, ('deer', 'walk'): .6, ('ptero2', 'walk'): .49,
          ('raptor', 'run'): 4.6, ('trex', 'run'): 8.5, ('compy', 'run'): 2.2, ('tricera', 'run'): 3.2, ('stego', 'run'): 4.0, ('deer', 'run'): 3.5,
          ('argentino', 'walk'): 2.4, ('sauropod', 'walk'): 2.0, ('trex2', 'walk'): 2.6, ('rat', 'walk'): .18, ('rat', 'run'): .7, ('tiktaalik', 'walk'): .25}


def stride_of(b, clip, anim=1.0):
    L = max(b.size.x, b.size.y); L0 = CR.SPEC[b.kind].get('length', L) or L
    v = STRIDE.get((b.kind, clip))
    if v is None: v = (.3 if clip == 'walk' else 1.1) * L0
    return v * (L / L0) * anim


def go(sh, kind, pts, ter, clip='walk', anim=1.0, speed=None, name=None, phase=0.0, scale=1.0, t0=0.0):
    """a creature travelling a ground path at the speed that keeps its feet planted"""
    b = CR.beast(sh, kind, name, clip=clip, speed=anim, phase=phase, scale=scale)
    v = speed if speed is not None else stride_of(b, clip, anim)
    f = CR.path_poly(pts, v); b.move(lambda t: f(max(0.0, t - t0))).on(ter); b.v = v
    return b


def still(sh, kind, xy, yaw, ter=None, clip='idle', anim=1.0, name=None, phase=0.0, scale=1.0, z=None):
    b = CR.beast(sh, kind, name, clip=clip, speed=anim, phase=phase, scale=scale)
    if z is None: b.move(lambda t: (xy[0], xy[1], yaw)).on(ter)
    else: b.move(lambda t: (xy[0], xy[1], yaw, z))
    return b


def swim(sh, kind, fn, name=None, clip=None, anim=1.0, scale=1.0, wig=None):
    """free 3D motion: fn(t) -> (x, y, yaw, z[, pitch, roll]); static models get a procedural undulation"""
    b = CR.beast(sh, kind, name, clip=clip, speed=anim, scale=scale); b.move(fn)
    if wig or not CR.SPEC[kind]['clips']: CR.wiggle(b, *(wig or (.22, 1.4)))
    return b


def line3(p0, p1, t0, t1, bob=0.0, f=1.0):
    """straight 3D swim from p0 to p1 between t0..t1, heading along the motion, gentle bob"""
    p0, p1 = Vector(p0), Vector(p1); d = p1 - p0; yaw = math.degrees(math.atan2(d.x, -d.y)); pitch = math.degrees(math.atan2(d.z, d.xy.length)) * .6
    def fn(t):
        u = max(0.0, min(1.0, (t - t0) / max(1e-3, t1 - t0))); p = p0.lerp(p1, u)
        return (p.x, p.y, yaw, p.z + bob * math.sin(t * f * math.tau), pitch)
    return fn


def embers(sh, center, n=120, area=(60, 60), height=60, seed=0, size=.15):
    """glowing lava bombs and embers arcing down (ballistic, analytic)"""
    r = random.Random(seed); m = bpy.data.materials.new('ember'); m.use_nodes = True; b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Emission Color'].default_value = (1, .45, .1, 1); b.inputs['Emission Strength'].default_value = 40; b.inputs['Base Color'].default_value = (.2, .05, 0, 1)
    obs = []
    for k in range(n):
        o = T.lib.sphere(f'ember{seed}_{k}', size * r.uniform(.5, 1.6), (0, 0, -999), m, seg=6, rings=4)
        p0 = Vector((center[0] + r.uniform(-area[0], area[0]) * .3, center[1] + r.uniform(-area[1], area[1]) * .3, center[2] + height * r.uniform(.6, 1.0)))
        v0 = Vector((r.uniform(-1, 1) * area[0] * .3, r.uniform(-1, 1) * area[1] * .3, r.uniform(-4, 6))); per = r.uniform(2.0, 4.0); ph = r.uniform(0, per)
        obs.append((o, p0, v0, per, ph))
    def u(t):
        for o, p0, v0, per, ph in obs:
            k = (t + ph) % per; o.location = p0 + v0 * k + Vector((0, 0, -4.9 * k * k))
    sh.updates.append(u)


def lava_fade(sh, fn):
    """scale every lava emission by fn(t) (time-lapse cooling)"""
    mats = []
    for m in bpy.data.materials:
        if m.node_tree and ('lava' in m.name.lower() or m.name.startswith('ember')):
            for n in m.node_tree.nodes:
                for i in n.inputs:
                    if i.name in ('Emission Strength', 'Strength') and not i.is_linked and isinstance(i.default_value, float):
                        mats.append((i, i.default_value))
    def u(t):
        k = fn(t)
        for i, v in mats: i.default_value = v * k
    sh.updates.append(u)


def splash(sh, p, t0, size=30.0, seed=0):
    """a meteor hitting the sea: white spray column + expanding foam ring + steam"""
    spray_u = TR.plume(f'spray{seed}', p, height=size * 3.0, r0=size * .35, r1=size * 1.1, drift=(size * .3, 0), col=(.92, .93, .95), density=.25, speed=size * .6, seed=seed)
    spo = bpy.data.objects[f'spray{seed}']
    def spray(k):                                   # the column grows out of the sea after the hit
        spray_u(k); spo.scale = (1, 1, max(.02, min(1.0, k / 1.2))); spo.location.z = p[2] + size * 1.5 * spo.scale.z
    steam = lambda k: None
    fm = TR.simple_mat('foam', ('',), '#f0f4f4', .5)
    ring = bpy.data.objects.new('foamring', bpy.data.meshes.new('foamring')); TR.coll().objects.link(ring)
    import bmesh
    bm = bmesh.new(); bmesh.ops.create_circle(bm, segments=64, radius=1.0); bm.to_mesh(ring.data); bm.free(); ring.data.materials.append(fm)
    sk = ring.modifiers.new('sk', 'SKIN') if False else None
    ring.modifiers.new('sol', 'SOLIDIFY').thickness = .2
    tor = T.lib.sphere('splashdome', 1, (p[0], p[1], p[2]), fm, seg=32, rings=12)
    def u(t):
        k = t - t0
        if k < 0: spray_off(); spo.hide_render = True; return
        spo.hide_render = False; spray(k); steam(k)
        tor.scale = (.001, .001, .001)
    def spray_off():
        tor.scale = (.001, .001, .001)
    sh.updates.append(u)


def flash_light(sh, fn, energy=40, col=(1, .9, .8)):
    l = bpy.data.lights.new('flashsun', 'SUN'); l.color = col; o = bpy.data.objects.new('flashsun', l); bpy.context.scene.collection.objects.link(o)
    o.rotation_euler = (math.radians(30), 0, 0); sh.updates.append(lambda t: setattr(l, 'energy', energy * fn(t)))


# ------------------------------------------------------------------ c13 / e: the young Earth
def s_c13(sh):
    """out of the chalk eye (iris wipe in compose) into a sweeping fly-over of the molten planet"""
    w, ter = nat(sh, 'young_earth'); embers(sh, (0, 260, 100), 60, seed=1)
    sh.camera(cam_fn([(0, (-10, 40, 22), (0, 260, 60), 18), (sh.dur, (-4, 70, 30), (0, 260, 70), 22)], shake=.02), fstop=16)


def s_e01(sh):
    """drone sweep: volcanoes, lava rivers, boiling sea, orange clouds"""
    w, ter = nat(sh, 'young_earth'); embers(sh, (0, 260, 95), 80, seed=2)
    sh.camera(cam_fn([(0, (-170, 20, 70), (-20, 300, 40), 20), (sh.dur * .55, (-60, 60, 55), (20, 300, 50), 22), (sh.dur, (40, 90, 48), (60, 330, 60), 24)], shake=.006), fstop=16)


def s_e02(sh):
    """meteors hammer the surface, volcanoes erupt"""
    w, ter = nat(sh, 'young_earth'); embers(sh, (0, 260, 95), 120, seed=3); embers(sh, (-170, 330, 120), 80, seed=4)
    r = random.Random(5)
    for k in range(9):
        e = Vector((r.uniform(-150, 150), r.uniform(120, 420), 0)); e.z = ter.z(e.x, e.y); s = e + Vector((r.uniform(-600, 600), r.uniform(200, 900), 900))
        t0 = .5 + k * sh.dur / 10; m = TR.meteor(f'met{k}', s, e, t0, 1.6, size=r.uniform(2, 5)); sh.updates.append(m)
        dust = TR.smoke_column(f'metdust{k}', tuple(e), rate=30, life=5, rise=14, r0=4, r1=26, wind=(2, 0), turb=8, col=(.3, .25, .22), density=.05, glow=1.5, voxel=1.5, seed=k)
        sh.updates.append(lambda t, d=dust, t1=t0 + 1.6: d(t - t1) if t > t1 else None)
        l = bpy.data.lights.new(f'methit{k}', 'POINT'); l.color = (1, .5, .2); lo = bpy.data.objects.new(f'methit{k}', l); TR.coll().objects.link(lo); lo.location = e + Vector((0, 0, 8))
        sh.updates.append(lambda t, l=l, t1=t0 + 1.6: setattr(l, 'energy', 4e6 * math.exp(-(t - t1) * 2.5) if t > t1 else 0))
    sh.camera(cam_fn([(0, (30, -10, 26), (0, 260, 50), 24), (sh.dur, (-20, 30, 34), (-20, 280, 60), 26)], shake=.012), fstop=16)


def s_e03(sh):
    """a meteor crashes into the sea - huge splash"""
    w, ter = nat(sh, 'young_earth'); p = (-330, 330, -6.5)
    sh.updates.append(TR.meteor('bigmet', (-100, 1400, 1500), p, 0.0, .8, size=8))
    splash(sh, p, .8, 40, seed=7); flash_light(sh, lambda t: max(0, 1 - abs(t - .85) * 3) if t > .8 else 0, 30, (1, .8, .6))
    sh.camera(cam_fn([(0, (-140, 120, 20), p, 26), (sh.dur, (-150, 110, 22), p, 24)], shake=lambda t: .004 + (.05 * math.exp(-(t - .8) * 2) if t > .8 else 0)), fstop=16)


def lambda_shake(t0, a):
    return a


def beach_chair(name, loc, yaw=0):
    """folding beach chair: aluminium frame + striped canvas"""
    al = TR.simple_mat(name + '_al', ('metal',), '#c8ccd0', .3, rough=.3); root = bpy.data.objects.new(name, None); TR.coll().objects.link(root)
    cv = bpy.data.materials.new(name + '_canvas'); cv.use_nodes = True; N = cv.node_tree.nodes; wv = N.new('ShaderNodeTexWave'); wv.inputs['Scale'].default_value = 3
    wv.bands_direction = 'X'; cr = N.new('ShaderNodeValToRGB'); cr.color_ramp.interpolation = 'CONSTANT'; cr.color_ramp.elements[0].color = (.9, .2, .15, 1)
    cr.color_ramp.elements[1].position = .5; cr.color_ramp.elements[1].color = (.95, .95, .9, 1); cv.node_tree.links.new(wv.outputs[1], cr.inputs[0])
    cv.node_tree.links.new(cr.outputs[0], N['Principled BSDF'].inputs['Base Color'])
    seat = T.box(name + '_seat', (.5, .45, .02), (0, 0, .3), cv); seat.parent = root; seat.rotation_euler = (math.radians(-8), 0, 0)
    back = T.box(name + '_back', (.5, .02, .6), (0, .28, .58), cv); back.parent = root; back.rotation_euler = (math.radians(-22), 0, 0)
    for sx in (-1, 1):
        for a, b in (((0, -.25, 0), (0, .3, .32)), ((0, .25, 0), (0, -.2, .34)), ((0, .2, .3), (0, .4, .88))):
            o = T.lib.tube(f'{name}_leg{sx}{a[1]}', [Vector((sx * .26, a[1], a[2])), Vector((sx * .26, b[1], b[2]))], .012, m=al); o.parent = root
    root.location = loc; root.rotation_euler = (0, 0, math.radians(yaw)); return root


def s_e04(sh):
    """a cartoon guy relaxes in a tiny beach chair with sunglasses and a drink while lava rains; the drink catches fire; he keeps sipping"""
    w, ter = nat(sh, 'young_earth'); x, y = 18.0, 95.0; z = ter.z(x, y)
    chair = beach_chair('chair', (x, y, z), 0)
    GUY = P('Guy', '#f2c84a', '#2a6ab0', hat=None, haircol='#3a2414', height=.95, boots='#e8e0d0', belt='#2a6ab0', collar=False)
    ch = toon(sh, 'GUY', GUY)
    g = Z.glasses_prop('GUY_shades'); [setattr(m, 'diffuse_color', (0, 0, 0, 1)) for m in []]
    for o in [g] + list(g.children_recursive):
        if o.type == 'MESH':
            for ms in o.material_slots:
                if ms.material and ('lens' in ms.material.name.lower() or 'glass' in ms.material.name.lower()):
                    m = ms.material.copy(); m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (.01, .01, .012, 1)
                    try: m.node_tree.nodes['Principled BSDF'].inputs['Transmission Weight'].default_value = 0
                    except Exception: pass
                    ms.material = m
    Z.wear_glasses(sh, ch, g)
    cup_m = TR.simple_mat('cupm', ('plastic',), '#3ab0d0', .3, rough=.2); cup = T.cyl('cup', .045, .14, (0, 0, -99), cup_m, v=16)
    straw = T.cyl('straw', .006, .2, (0, 0, -99), TR.simple_mat('strawm', ('',), '#f04a8a', .2), v=8)
    fire = TR.smoke_column('cupfire', (0, 0, -99), rate=18, life=.6, rise=.5, r0=.03, r1=.07, wind=(0, 0), turb=.04, col=(.05, .03, .02), density=.6, glow=40, voxel=.012, seed=4)
    a = stand(sh, ch, (x, y), 0, '77_02', 1.0, face=[(0, 'smug'), (4.5, 'idle'), (5.6, 'smug')], z=z)
    yaw = math.radians(0); fw = Vector((math.sin(yaw), -math.cos(yaw), 0)); sd = Vector((math.cos(yaw), math.sin(yaw), 0))
    def sip(t):                       # sip at 1.5 s and 6.5 s
        return max(0.0, 1 - abs(t - 2.0) / .8) + max(0.0, 1 - abs(t - 7.0) / .9)
    def mod(t, d):
        d['crouch'] = max(0.0, ch.L * ch.s - .36 - .08 * ch.s); d['loc'] = (x, y, z); d['yaw'] = 0
        for s_, sx in (('L', -1), ('R', 1)): d['foot' + s_] = (sx * .2, -.55, 0)
        d['lean'] = (-.25, 0)
        hp = head_of(ch, -.1); u = sip(t)
        d['handR'] = tuple((Vector((x, y, z)) + sd * .26 + fw * .18 + Vector((0, 0, .52))).lerp(hp + fw * .12 + sd * .03 - Vector((0, 0, .06)), u))
        d['handL'] = tuple(Vector((x, y, z)) - sd * .3 + Vector((0, 0, .42)))
        return d
    override(a, mod)
    def cu(t):
        bpy.context.view_layer.update(); hm = ch.hands['R'].matrix_world.translation
        cup.location = hm + Vector((0, 0, .03)); straw.location = hm + Vector((0, 0, .14)); straw.rotation_euler = (.25, 0, 0)
        fire(max(0.0, t - 4.2)); bpy.data.objects['cupfire'].location = hm + Vector((0, 0, .1)) if t > 4.2 else Vector((0, 0, -99))
    sh.updates.append(cu)
    embers(sh, (x + 10, y + 30, z + 40), 70, (40, 40), 30, seed=6, size=.12)
    h0 = Vector((x, y, z + .9))
    sh.camera(cam_fn([(0, tuple(h0 + fw * 4.2 + sd * 1.2 + Vector((0, 0, .6))), tuple(h0 + Vector((0, 0, .5))), 34), (sh.dur, tuple(h0 + fw * 3.4 + sd * .9 + Vector((0, 0, .6))), tuple(h0 + Vector((0, 0, .5))), 36)],
                     shake=.004), fstop=4)
    sh.keylight(30, (1, .75, .55))


def s_e05(sh):
    """time-lapse: the planet cools, the oceans settle"""
    w, ter = nat(sh, 'young_earth'); k = lambda t: max(.08, 1 - ease(t / sh.dur) * .92)
    lava_fade(sh, k)
    for o in bpy.data.objects:
        if o.name.startswith('craterlight'): sh.updates.append(lambda t, l=o.data: setattr(l, 'energy', 2.5e5 * k(t) ** 2))
    def sky(t):
        bpy.context.scene.view_settings.exposure = .3 + .5 * ease(t / sh.dur)
    sh.updates.append(sky)
    sh.camera(cam_fn([(0, (-120, 60, 60), (-200, 300, 0), 20), (sh.dur, (-110, 80, 70), (-220, 320, 0), 20)], shake=.003), fstop=16)


def s_e06(sh):
    """the camera dives beneath the ocean surface"""
    w, ter = nat(sh, 'shallows')
    sh.camera(cam_fn([(0, (0, 0, 6), (0, 40, -2), 24), (sh.dur * .6, (0, 8, .2), (0, 30, -8), 24), (sh.dur, (0, 12, -5), (0, 30, -14), 24)], shake=.004), fstop=16)


def s_e07(sh):
    """microscopic world: bacteria drifting in ancient water"""
    w, _ = nat(sh, 'microbes')
    sh.camera(cam_fn([(0, (-1.5, -3, .3), (0, 8, 0), 35), (sh.dur, (1.2, 1.0, -.2), (.5, 10, 0), 35)], shake=.002), fstop=2.8)


def s_e08(sh):
    """one microbe bumps into another. neither apologizes"""
    w, _ = nat(sh, 'microbes')
    a = CR.microbe('bumpA', 'rod', .5, '#9ad0b8', 1); b = CR.microbe('bumpB', 'rod', .45, '#c8b07a', 2)
    tc = 3.2
    def u(t):
        ka = min(t, tc) - max(0, t - tc) * .4; kb = min(t, tc) - max(0, t - tc) * .5
        a.location = (-1.2 + .3 * ka, 2.4, .05 * math.sin(t)); b.location = (1.25 - .3 * kb, 2.5, -.05)
        a.rotation_euler = (0, math.radians(90), t * .1 + (max(0, t - tc) * .6)); b.rotation_euler = (0, math.radians(90), -t * .1 - (max(0, t - tc) * .4))
    sh.updates.append(u)
    sh.camera(cam_fn([(0, (0, -1.0, .3), (0, 2.45, 0), 45), (sh.dur, (0, -.6, .25), (0, 2.45, 0), 50)], shake=.001), fstop=3.2)


# ------------------------------------------------------------------ m: oxygen
def bubbles(sh, area, n=160, seed=0, z0=-18, z1=0):
    r = random.Random(seed); m = bpy.data.materials.new('bubble'); m.use_nodes = True; b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Roughness'].default_value = 0; b.inputs['IOR'].default_value = 1.0 / 1.33
    try: b.inputs['Transmission Weight'].default_value = 1.0
    except Exception: pass
    obs = []
    for k in range(n):
        o = T.lib.sphere(f'bub{seed}_{k}', r.uniform(.01, .05), (0, 0, -99), m, seg=8, rings=6)
        obs.append((o, r.uniform(area[0], area[1]), r.uniform(area[2], area[3]), r.uniform(.5, 1.4), r.uniform(0, 30)))
    def u(t):
        for o, x, y, v, ph in obs:
            h = ((t + ph) * v) % (z1 - z0); o.location = (x + .1 * math.sin(h * 2 + ph), y, z0 + .3 + h)
    sh.updates.append(u)


def s_m01(sh):
    """cyanobacteria mats soaking up sunlight in shallow water"""
    w, ter = nat(sh, 'shallows'); bubbles(sh, (-8, 8, 6, 30), 100, 1)
    sh.camera(cam_fn([(0, G(ter, -6, 2, 1.6), G(ter, 2, 22, -.2), 24), (sh.dur, G(ter, 2, 6, 1.2), G(ter, 6, 24, -.2), 24)], shake=.003), fstop=8)


def s_m02(sh):
    """oxygen bubbles rising from the mats, the light above brightening"""
    w, ter = nat(sh, 'shallows'); bubbles(sh, (-5, 5, 8, 20), 260, 2)
    sh.updates.append(lambda t: setattr(bpy.context.scene.view_settings, 'exposure', .8 + .6 * ease(t / sh.dur)))
    sh.camera(cam_fn([(0, G(ter, 0, 4, 1.0), G(ter, 0, 14, .5), 24), (sh.dur, G(ter, 0, 6, 2.0), (0, 14, 0), 20)], shake=.003), fstop=8)


def o2(name, m):
    a = T.lib.sphere(name + 'a', .12, (0, 0, 0), m, seg=16, rings=10); b = T.lib.sphere(name + 'b', .12, (.16, 0, 0), m, seg=16, rings=10); b.parent = a; return a


def s_m03(sh):
    """the screen fills with oxygen molecules; oxygen-hating microbes shrivel"""
    w, _ = nat(sh, 'microbes'); r = random.Random(3); om = CR.pmat('oxy', '#e0402a', .25, coat=.5)
    mol = []
    for k in range(260):
        o = o2(f'O2_{k}', om); p = Vector((r.uniform(-5, 5), r.uniform(0, 12), r.uniform(-3, 3))); tin = r.uniform(0, sh.dur * .8)
        mol.append((o, p, tin, r.uniform(0, 6.3)))
    def u(t):
        for o, p, tin, ph in mol:
            s = ease((t - tin) / .6) if t > tin else 0.0; o.scale = (max(.001, s),) * 3
            o.location = p + Vector((math.sin(t + ph) * .2, 0, math.cos(t * .8 + ph) * .2)); o.rotation_euler = (ph + t, ph, 0)
        for k, (m, p0, v, ph) in enumerate(w['cells']):
            if k % 3 == 0:
                s = 1 - .7 * ease((t - 3 - k * .05) / 3); m.scale = (max(.2, s), max(.2, s), max(.2, s * .7))
    sh.updates.append(u)
    sh.camera(cam_fn([(0, (0, -3, 0), (0, 8, 0), 30), (sh.dur, (0, -.5, .2), (0, 8, 0), 32)], shake=.002), fstop=4)


def s_m06(sh):
    """Ediacaran sea floor: Dickinsonia - a pancake and a pillow had a baby"""
    w, ter = nat(sh, 'ediacaran')
    sh.camera(cam_fn([(0, G(ter, -4, 7, 4.0), G(ter, 0, 16, 0), 26), (sh.dur * .6, G(ter, -1.5, 11, 2.6), G(ter, 0, 15, 0), 32), (sh.dur, G(ter, -.6, 12.6, 1.8), G(ter, 0, 15, 0), 40)],
                     shake=.002), fstop=6)


# ------------------------------------------------------------------ k: the Cambrian explosion
def cambrian_life(sh, ter, n_tri=40, n_ano=4, hallu=3, seed=0, area=(-14, 14, 4, 40)):
    """procedural crowds (cheap) + a few hero GLBs"""
    r = random.Random(seed); out = dict(tri=[], ano=[])
    for k in range(n_tri):
        o, wk = CR.trilobite(f'tri{seed}_{k}', r.uniform(.12, .35)); x, y = r.uniform(area[0], area[1]), r.uniform(area[2], area[3]); o.location = (x, y, ter.z(x, y) + .02)
        o.rotation_euler = (0, 0, r.uniform(0, 6.3)); v = r.uniform(.03, .12); yaw = o.rotation_euler.z
        out['tri'].append((o, Vector((x, y)), v, yaw, wk))
    for k in range(n_ano):
        root, sw = CR.anomalocaris(f'ano{seed}_{k}', r.uniform(.5, .9)); x, y = r.uniform(area[0], area[1]), r.uniform(area[2] + 6, area[3]); z = ter.z(x, y) + r.uniform(1.5, 4)
        out['ano'].append((root, sw, Vector((x, y, z)), r.uniform(.5, 1.2), r.uniform(0, 6.3)))
    for k in range(hallu):
        x, y = r.uniform(-4, 4), r.uniform(6, 14)
        still(sh, 'hallu', (x, y), r.uniform(0, 360), ter, clip='walk', scale=2.5, name=f'hallu{seed}{k}')
    def u(t):
        for o, p, v, yaw, wk in out['tri']:
            d = Vector((math.sin(yaw), -math.cos(yaw))); q = p + d * v * t; o.location = (q.x, q.y, ter.z(q.x, q.y) + .02); wk(t)
        for root, sw, p, v, ph in out['ano']:
            a = ph + t * v * .3; root.location = p + Vector((math.cos(a) * 6, math.sin(a) * 6, math.sin(t * .7 + ph) * .4)); root.rotation_euler = (0, 0, a + math.pi)
            sw(t, 1.0)
    sh.updates.append(u)
    return out


def s_k01(sh):
    """the camera races through a crowded ancient ocean"""
    w, ter = nat(sh, 'cambrian'); cambrian_life(sh, ter, 70, 8, 2, 1, (-16, 16, 0, 90))
    swim(sh, 'anomalo', line3(G(ter, 6, 40, 3), G(ter, -10, 70, 4), 0, sh.dur, .2, .3), 'heroAno', scale=1.0)
    sh.camera(cam_fn([(0, G(ter, 0, -2, 2.5), G(ter, 0, 20, 1.5), 22), (sh.dur, G(ter, 2, 55, 1.8), G(ter, 2, 80, 1.2), 22)], shake=.006), fstop=8)


def s_k02(sh):
    """trilobites, Hallucigenia, sponges: a dangerous playground"""
    w, ter = nat(sh, 'cambrian'); cambrian_life(sh, ter, 50, 3, 4, 2, (-8, 8, 4, 22))
    for k, (x, y) in enumerate([(-.6, 9.5), (.5, 10.4), (1.2, 9.2)]):
        b = still(sh, 'trilobite', (x, y), 30 + 70 * k, ter, clip=None, name=f'trihero{k}', scale=1.3)
    sh.camera(cam_fn([(0, G(ter, -2.5, 6, .8), G(ter, 0, 10, .1), 32), (sh.dur, G(ter, 1.5, 6.5, .6), G(ter, .3, 10, .1), 34)], shake=.002), fstop=4)


def s_k03(sh):
    """Anomalocaris swims straight toward the camera"""
    w, ter = nat(sh, 'cambrian'); cambrian_life(sh, ter, 40, 3, 1, 3, (-10, 10, 6, 40))
    swim(sh, 'anomalo', line3(G(ter, 0, 24, 2.2), G(ter, 0, 6.2, 1.6), 0, sh.dur, .15, .35), 'heroAno', scale=1.1, wig=(.25, 1.1))
    sh.camera(cam_fn([(0, G(ter, 0, 3.5, 1.5), G(ter, 0, 14, 1.8), 30), (sh.dur, G(ter, 0, 3.0, 1.5), G(ter, 0, 8, 1.6), 30)], shake=.003,
                     focus=lambda t: Vector(G(ter, 0, 24 - 17.8 * min(1, t / sh.dur), 1.8))), fstop=4)


def cartoon_fish(name, col='#f0a020'):
    root, sw = CR.fish(name, .25, col, jaws=True) if 'jaws' in CR.fish.__code__.co_varnames else CR.fish(name, .25, col)
    return root, sw


def s_k04(sh):
    """Anomalocaris looms; a tiny cartoon fish gasps and reverses at top speed"""
    w, ter = nat(sh, 'cambrian')
    ano = swim(sh, 'anomalo', lambda t: (0, 9.0 - .6 * ease(t / 1.2), 180 * 0, ter.z(0, 9) + 1.6 + .05 * math.sin(t * 3), -6), 'heroAno', scale=1.3, wig=(.15, 1.6))
    fr, fsw = cartoon_fish('tinyfish')
    def u(t):
        back = max(0.0, t - 1.1); x = .05; y = 7.6 - .2 * min(1, t) + 3.5 * back * back; fr.location = (x, y, ter.z(0, 9) + 1.65 + .02 * math.sin(t * 9))
        fr.rotation_euler = (0, 0, math.pi); fsw(t, 3.0 if back > 0 else 1.0, bite=1.0 if .7 < t < 1.6 else 0.0)
    sh.updates.append(u)
    sh.camera(cam_fn([(0, G(ter, -1.2, 6.2, 1.9), G(ter, 0, 8.4, 1.75), 45), (sh.dur, G(ter, -1.0, 6.4, 1.85), G(ter, 0, 8.6, 1.75), 45)], shake=.003), fstop=3.2)


def s_k05(sh):
    """arms race: predators chase, prey hides"""
    w, ter = nat(sh, 'cambrian'); life = cambrian_life(sh, ter, 30, 2, 1, 5, (-10, 10, 8, 30))
    ano = swim(sh, 'anomalo', line3(G(ter, -12, 30, 1.0), G(ter, 8, 14, .7), 0, sh.dur, .1, .4), 'chaser', scale=1.0, wig=(.22, 1.8))
    prey = []
    for k in range(5):
        o, wk = CR.trilobite(f'runner{k}', .25); prey.append((o, wk))
    def u(t):
        for k, (o, wk) in enumerate(prey):
            wk(t * 3)
            p0 = Vector((-6 + k * .7, 24 - k * .8)); p1 = Vector((3 + k * .5, 12 + k * .3)); q = p0.lerp(p1, min(1, ease(t / (sh.dur * .7))))
            o.location = (q.x, q.y, ter.z(q.x, q.y) + .02); o.rotation_euler = (0, 0, math.atan2((p1 - p0).x, -(p1 - p0).y))
    sh.updates.append(u)
    sh.camera(cam_fn([(0, G(ter, 8, 10, 1.4), G(ter, -6, 24, .6), 26), (sh.dur, G(ter, 9, 12, 1.2), G(ter, 4, 14, .5), 28)], shake=.004), fstop=6)


def s_k06(sh):
    """Devonian: a fish with brand-new jaws looks proud and bites the nearest rock"""
    w, ter = nat(sh, 'devonian_sea'); rx, ry = 1.5, 14.0; rz = ter.z(rx, ry)
    rock = T.lib.sphere('bitrock', .9, (rx, ry, rz + .4), TR.simple_mat('brock', ('rock',), '#6a6458', 1.5), seg=24, rings=12); rock.scale = (1, .8, .7)
    tb = 5.0
    def path(t):
        u = ease(min(1, t / 3.5)); lunge = max(0.0, 1 - abs(t - tb) / .35)
        return (rx - 1.8 + .9 * u + .9 * lunge, ry + 7 - 6 * u, 140 - 30 * u, rz + 1.2 + .15 * math.sin(t * 1.3), -5 * lunge)
    swim(sh, 'dunkle', path, 'dunk', scale=1.0, wig=(.08, .8))
    r = random.Random(1); chips = []
    cm = TR.simple_mat('chipm', ('rock',), '#6a6458', 1)
    for k in range(18):
        o = T.lib.sphere(f'chip{k}', r.uniform(.03, .08), (0, 0, -99), cm, seg=6, rings=4); chips.append((o, Vector((r.uniform(-1, 1), r.uniform(-1, .2), r.uniform(.5, 2.0)))))
    def u(t):
        k = t - tb
        for o, v in chips:
            o.location = (Vector((rx - .5, ry - .5, rz + .9)) + v * k + Vector((0, 0, -1.2 * k * k))) if k > 0 else (0, 0, -99)
    sh.updates.append(u)
    sh.camera(cam_fn([(0, G(ter, rx - 7, ry - 3, 1.6), G(ter, rx - .5, ry + 2, 1.2), 30), (sh.dur, G(ter, rx - 6, ry - 2, 1.5), G(ter, rx - .5, ry, 1.2), 32)], shake=.003), fstop=6)


# ------------------------------------------------------------------ l: onto land
def find_y(ter, x, y, ok, step=1.0, n=400):
    """walk along +Y from y until ok(z) (e.g. dry land, shallow water)"""
    for k in range(n):
        if ok(ter.z(x, y + k * step)): return y + k * step
    return y


def millipede(name, n=14, size=.04):
    m = TR.simple_mat(name + '_m', ('',), '#4a2a1a', .2, rough=.4); root = bpy.data.objects.new(name, None); TR.coll().objects.link(root); segs = []
    for k in range(n):
        s = T.lib.sphere(f'{name}_s{k}', size, (0, 0, 0), m, seg=10, rings=6); s.scale = (1.3, 1, .8); s.parent = root; segs.append(s)
    return root, segs


def s_l01(sh):
    """the camera rises out of the water to a coastline carpeted with early plants"""
    w, ter = nat(sh, 'coast')
    sh.camera(cam_fn([(0, (0, -40, -.4), (0, 0, .5), 24), (sh.dur * .35, (0, -34, 1.2), (0, 20, 1), 24), (sh.dur, (4, -18, 12), (0, 50, 2), 22)], shake=.004), fstop=16)


def s_l02(sh):
    """early land arthropods crawl across the rocks"""
    w, ter = nat(sh, 'coast'); r = random.Random(2); crawlers = []; Y = find_y(ter, 0, -60, lambda z: z > .05) + 7.0
    for k in range(5):
        root, segs = millipede(f'mill{k}', 14, .035); p0 = Vector((r.uniform(-1, 1), Y + 1 + r.uniform(-1, 1))); a = r.uniform(0, 6.3); crawlers.append((segs, p0, a, r.uniform(.05, .1)))
    def u(t):
        for segs, p0, a, v in crawlers:
            for k, s in enumerate(segs):
                d = t * v - k * .05; q = p0 + Vector((math.cos(a + math.sin(d * 6) * .3), math.sin(a + math.sin(d * 6) * .3))) * d
                s.location = (q.x, q.y, ter.z(q.x, q.y) + .03 + .006 * math.sin(t * 20 + k))
    sh.updates.append(u)
    sh.camera(cam_fn([(0, G(ter, -1.2, Y + 3.6, 1.1), G(ter, 0, Y + 1.2, .05), 40), (sh.dur, G(ter, -.9, Y + 3.3, 1.0), G(ter, .2, Y + 1.4, .05), 45)], shake=.001), fstop=4)


def s_l03(sh):
    """a lobe-finned fish paddles in the shallows on thick fleshy fins"""
    w, ter = nat(sh, 'coast'); Y = find_y(ter, 0, -80, lambda z: z > -1.6)          # where the sea bed rises to ~1.5 m deep
    swim(sh, 'coelacanth', line3((-6, Y - 1, -.5), (5, Y + 1, -.45), 0, sh.dur, .03, .5), 'lobe', clip='swim', scale=1.0)
    sh.camera(cam_fn([(0, (-4, Y - 3.5, 1.8), (-2.5, Y - .6, -.5), 32), (sh.dur, (3, Y - 2.5, 1.7), (3.5, Y + .6, -.45), 32)], shake=.003), fstop=5)


def s_l04(sh):
    """Tiktaalik hauls itself through the mud, gets stuck, stares at the camera"""
    w, ter = nat(sh, 'coast'); Y0 = find_y(ter, 0, -60, lambda z: z > .05) - 3.0
    b = CR.beast(sh, 'tiktaalik', 'tik', clip='walk_on_land', speed=1.0)
    v = stride_of(b, 'walk'); stop = 2.6
    def path(t):
        k = min(t, stop); x, y = -1.2 + v * k * .3, Y0 + 4.0 + v * k * .95
        yaw = 162 + (12 * ease((t - stop - .6) / .8) if t > stop + .6 else 0)           # crawls inland toward the lens, stuck, looks up at it
        return (x, y, yaw, max(ter.z(x, y), -.25) - .05)
    b.move(path)
    def freeze(t):                             # stuck: the clip stops
        if t > stop and b.arm and b.arm.animation_data:
            for tr in b.arm.animation_data.nla_tracks:
                for st in tr.strips: pass
    b.set_clip('walk_on_land', .001, at=stop)
    cz = lambda x, y, d: (x, y, max(ter.z(x, y), -.2) + d)
    sh.camera(cam_fn([(0, cz(.6, Y0 + 10.5, .7), cz(-1.0, Y0 + 5.0, .25), 35), (sh.dur, cz(.3, Y0 + 9.2, .55), cz(-.5, Y0 + 6.2, .3), 45)], shake=.002), fstop=3.5)
