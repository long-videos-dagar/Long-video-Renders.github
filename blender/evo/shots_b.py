# exec'd inside story.py after shots_a: Permian -> Mesozoic -> the asteroid -> mammals

def fz(w):
    return w['focus'].x, w['focus'].y


def falling_tree(sh, ter, xy, t0, yaw=0.0, h=18.0, kind='fir_tree_01'):
    """a tree toppling: pivots on its base, accelerating like a falling rod, bounces once on landing.
    fir, the same model the forests use (the pine model alone pushed a 16 GB runner out of memory)"""
    c = TR.phc(kind)
    if c: o = bpy.data.objects.new('ftree', None); o.instance_type = 'COLLECTION'; o.instance_collection = c; TR.coll().objects.link(o); o.scale = (h / TR.phc_height(c),) * 3
    else: o = T.cyl('ftree', .4, h, (0, 0, h / 2), TR.simple_mat('ftrunk', ('bark',), '#5a4a3a', 1.0))
    x, y = xy; o.location = (x, y, ter.z(x, y) - .2); o.rotation_mode = 'ZXY'
    def u(t):
        k = max(0.0, t - t0); a = min(90.0, 4 * k * k * 22)                       # theta ~ t^2 until it hits the ground
        if a >= 90.0:
            tb = math.sqrt(90 / 88.0); kk = k - tb; a = 90 - 6 * math.exp(-kk * 6) * abs(math.sin(kk * 14))
        o.rotation_euler = (math.radians(a), 0, math.radians(yaw))
    sh.updates.append(u); return o


def eruption(sh, p, scale=1.0, seed=0):
    col = TR.plume(f'erupt{seed}', p, height=260 * scale, r0=6 * scale, r1=90 * scale, drift=(80 * scale, 20 * scale),
                   density=.12, glow=.35, speed=7 * scale, seed=seed)
    sh.updates.append(col); embers(sh, (p[0], p[1], p[2] + 30 * scale), 60, (30 * scale, 30 * scale), 40 * scale, seed=seed + 50, size=.4 * scale)
    l = bpy.data.lights.new(f'eruptl{seed}', 'POINT'); l.energy = 3e6 * scale; l.color = (1, .4, .1); o = bpy.data.objects.new('eruptl', l); TR.coll().objects.link(o)
    o.location = (p[0], p[1], p[2] + 10)


def flock(sh, kind, n, p0, p1, t0, t1, seed=0, spread=4.0, clip='fly', scale=1.0, alt=0.0):
    r = random.Random(seed); out = []
    for k in range(n):
        o = Vector((r.uniform(-spread, spread), r.uniform(-spread, spread), r.uniform(-spread, spread) * .4))
        dt = r.uniform(0, .6)
        b = swim(sh, kind, line3(Vector(p0) + o, Vector(p1) + o * 1.6 + Vector((0, 0, alt)), t0 + dt, t1 + dt, .3, .8), f'{kind}F{seed}_{k}', clip=clip,
                 anim=r.uniform(.9, 1.2), scale=scale * r.uniform(.85, 1.1))
        out.append(b)
    return out


# ------------------------------------------------------------------ p: Permian -> first dinosaurs -> Mesozoic giants
def s_p01(sh):
    """a lush ancient forest (HUD: 252 MILLION YEARS AGO - PERMIAN MASS EXTINCTION in compose)"""
    w, ter = nat(sh, 'permian'); fx, fy = fz(w)
    sh.camera(cam_fn([(0, G(ter, fx - 8, fy - 30, 3), G(ter, fx, fy + 20, 6), 22), (sh.dur, G(ter, fx - 4, fy - 22, 12), G(ter, fx + 2, fy + 30, 8), 22)], shake=.004), fstop=11)


def s_p02(sh):
    """volcanic eruptions, collapsing ecosystems, a changing climate"""
    w, ter = nat(sh, 'permian'); fx, fy = fz(w)
    for k, (x, y) in enumerate([(-260, 900), (320, 1100), (40, 1400)]): eruption(sh, (fx + x, fy + y, 0), 3.0, seed=k)
    for k, (x, y, t0, yw) in enumerate([(-6, 22, 2.0, 70), (9, 30, 5.5, -60), (-14, 40, 8.0, 100)]): falling_tree(sh, ter, (fx + x, fy + y), t0, yw, 20)
    sh.updates.append(lambda t: setattr(bpy.context.scene.view_settings, 'exposure', -.45 - .6 * ease(t / sh.dur)))
    sh.camera(cam_fn([(0, G(ter, fx, fy - 12, 2.5), G(ter, fx, fy + 60, 14), 22), (sh.dur, G(ter, fx + 3, fy - 6, 3), G(ter, fx, fy + 60, 18), 24)], shake=.006,
                     quake=lambda t: .02 + .03 * max(0, math.sin(t * 1.3))), fstop=11)


def s_p03(sh):
    stage(sh, 'black'); sh.camera(cam_fn([(0, (0, -5, 1), (0, 0, 1), 35), (sh.dur, (0, -5, 1), (0, 0, 1), 35)]), fstop=16)


def s_p04(sh):
    """a new ecosystem fades in (Triassic): crane up through the ferns"""
    w, ter = nat(sh, 'triassic'); fx, fy = fz(w)
    sh.camera(cam_fn([(0, G(ter, fx, fy - 14, .8), G(ter, fx, fy + 20, 1.5), 24), (sh.dur, G(ter, fx + 2, fy - 18, 7), G(ter, fx, fy + 30, 3), 24)], shake=.003), fstop=11)


def s_p05(sh):
    """small early dinosaurs dart through the forest like nervous chickens"""
    w, ter = nat(sh, 'triassic'); fx, fy = fz(w)
    for k in range(4):
        x0 = fx - 7 + k * 1.6; go(sh, 'compy', [(x0, fy + 6 + k * 1.5), (x0 + 9, fy + 2 + k), (x0 + 14, fy + 8 + k), (x0 + 30, fy + 4)], ter, clip='run', name=f'compy{k}',
                                   scale=1.3, phase=k * .23, t0=k * .4)
    go(sh, 'raptor', [(fx - 10, fy + 12), (fx + 2, fy + 7), (fx + 20, fy + 10)], ter, clip='run', name='earlyraptor', scale=.8, t0=4.5)
    sh.camera(cam_fn([(0, G(ter, fx - 6, fy - 6, 1.0), G(ter, fx - 4, fy + 6, .5), 30), (sh.dur, G(ter, fx + 4, fy - 5, 1.1), G(ter, fx + 10, fy + 7, .5), 30)], shake=.006), fstop=5)


def s_p06(sh):
    """time-lapse: dinosaurs grow bigger - the sun races, ever larger animals cross the clearing"""
    w, ter = nat(sh, 'jurassic'); fx, fy = fz(w)
    sun = next((o for o in bpy.data.objects if o.type == 'LIGHT' and o.data.type == 'SUN'), None)
    if sun: sh.updates.append(lambda t: setattr(sun, 'rotation_euler', (math.radians(30 + 25 * math.sin(t * 2.2)), 0, math.radians(120 + t * 60))))
    seq = [('compy', 1.4, 0.0, 'run'), ('raptor', 1.0, 1.0, 'run'), ('stego', 1.0, 2.2, 'walk'), ('sauropod', 1.0, 3.2, 'walk')]
    for k, (kind, sc, t0, cl) in enumerate(seq):
        go(sh, kind, [(fx - 40, fy + 14 + k * 5), (fx + 60, fy + 14 + k * 5)], ter, clip=cl, name=f'tl{kind}', scale=sc, anim=2.5, t0=t0)
    sh.camera(cam_fn([(0, G(ter, fx, fy - 20, 3), G(ter, fx, fy + 20, 5), 22), (sh.dur, G(ter, fx, fy - 24, 5), G(ter, fx, fy + 20, 7), 22)], shake=.002), fstop=11)


def s_p07(sh):
    """a giant sauropod walks through the forest; the ground shakes; birds scatter"""
    w, ter = nat(sh, 'jurassic'); fx, fy = fz(w)
    b = go(sh, 'argentino', [(fx - 30, fy + 26), (fx + 40, fy + 18)], ter, name='giant')
    flock(sh, 'archaeo', 7, (fx + 8, fy + 30, ter.z(fx, fy) + 14), (fx - 30, fy - 20, ter.z(fx, fy) + 30), 1.2, 5.0, seed=2, clip='shake', spread=3, scale=1.2)
    step = lambda t: .035 * max(0.0, math.sin(t * 2 * math.pi * .55)) ** 8
    sh.camera(cam_fn([(0, G(ter, fx + 6, fy - 14, 1.6), G(ter, fx - 10, fy + 24, 9), 22), (sh.dur, G(ter, fx + 8, fy - 13, 1.6), G(ter, fx + 6, fy + 22, 10), 22)],
                     shake=.003, quake=step), fstop=11)


def s_p08(sh):
    """Stegosaurus in a Jurassic forest, swinging its tail"""
    w, ter = nat(sh, 'jurassic'); fx, fy = fz(w)
    b = go(sh, 'stego', [(fx - 12, fy + 10), (fx + 6, fy + 5)], ter, name='stego')
    b.set_clip(CR.clip_of(b, 'tail'), 1.0, at=8.0)
    stop = (Vector((fx + 6, fy + 5)) - Vector((fx - 12, fy + 10))).length / b.v
    f = b.path; b.move(lambda t: f(min(t, min(stop, 7.9))))
    sh.camera(cam_fn([(0, G(ter, fx - 2, fy - 8, 1.8), G(ter, fx - 8, fy + 9, 2), 28), (sh.dur, G(ter, fx + 4, fy - 6, 1.7), G(ter, fx + 4, fy + 6, 2), 28)], shake=.004), fstop=6)


def s_p09a(sh):
    """split screen (left): the Stegosaurus waves goodbye"""
    w, ter = nat(sh, 'jurassic'); fx, fy = fz(w)
    b = still(sh, 'stego', (fx, fy + 6), -30, ter, clip='roar', name='stegoL')
    sh.camera(cam_fn([(0, G(ter, fx - 3, fy - 4, 2.4), G(ter, fx, fy + 6, 2.4), 32), (sh.dur, G(ter, fx - 3, fy - 3.6, 2.4), G(ter, fx, fy + 6, 2.4), 32)], shake=.003), fstop=5)


def s_p09b(sh):
    """split screen (right): the T-rex has no idea who he is"""
    w, ter = nat(sh, 'cretaceous'); fx, fy = fz(w)
    b = still(sh, 'trex2', (fx, fy + 8), 30, ter, clip='idle', name='trexR')
    sh.camera(cam_fn([(0, G(ter, fx + 4, fy - 5, 3.4), G(ter, fx, fy + 8, 3.4), 32), (sh.dur, G(ter, fx + 4, fy - 4.6, 3.4), G(ter, fx, fy + 8, 3.4), 32)], shake=.003), fstop=5)


def s_p10(sh):
    """Mesozoic panorama"""
    w, ter = nat(sh, 'cretaceous'); fx, fy = fz(w)
    for k in range(3): go(sh, 'tricera', [(fx - 30 + k * 5, fy + 30 + k * 4), (fx + 30, fy + 26 + k * 4)], ter, name=f'pan_tri{k}', phase=k * .4)
    go(sh, 'sauropod', [(fx + 60, fy + 90), (fx - 40, fy + 100)], ter, name='pan_saur')
    flock(sh, 'ptero', 3, (fx - 60, fy + 40, ter.z(fx, fy) + 35), (fx + 80, fy + 80, ter.z(fx, fy) + 45), 0, sh.dur, seed=3, spread=10)
    sh.camera(cam_fn([(0, G(ter, fx - 20, fy - 30, 14), G(ter, fx - 10, fy + 60, 6), 20), (sh.dur, G(ter, fx + 20, fy - 30, 16), G(ter, fx + 15, fy + 60, 6), 20)], shake=.003), fstop=16)


def s_p11(sh):
    """T-rex roars directly into the camera"""
    w, ter = nat(sh, 'cretaceous'); fx, fy = fz(w)
    b = still(sh, 'trex', (fx, fy + 10), 0, ter, clip='roar', name='trexroar')
    hz = ter.z(fx, fy + 10)
    sh.camera(cam_fn([(0, (fx + .5, fy - 1.5, hz + 4.0), (fx, fy + 6, hz + 4.2), 24), (sh.dur, (fx + .3, fy - .2, hz + 4.0), (fx, fy + 6, hz + 4.3), 24)], shake=.004,
                     quake=lambda t: .02 if t > .8 else 0), fstop=4)


# ------------------------------------------------------------------ d: life of the dinosaurs
def s_d01(sh):
    """drone: a herd of enormous sauropods crosses a valley"""
    w, ter = nat(sh, 'jurassic'); fx, fy = fz(w)
    for k in range(5):
        kind = 'argentino' if k % 2 == 0 else 'sauropod'
        go(sh, kind, [(fx - 70 + k * 6, fy + 40 + k * 12), (fx + 60 + k * 6, fy + 30 + k * 12)], ter, name=f'herd{k}', phase=k * .37, scale=.8 + .1 * k)
    sh.camera(cam_fn([(0, G(ter, fx - 60, fy - 40, 70), G(ter, fx, fy + 60, 0), 22), (sh.dur, G(ter, fx + 10, fy - 30, 55), G(ter, fx + 10, fy + 60, 0), 22)], shake=.004), fstop=16)


def s_d02(sh):
    """pterosaurs glide over the coastline (HUD: NOT A DINOSAUR)"""
    w, ter = nat(sh, 'coast_cretaceous')
    flock(sh, 'ptero', 5, (-45, -40, 16), (45, -26, 22), 0, sh.dur * 1.05, seed=4, spread=6, scale=1.5)
    sh.camera(cam_fn([(0, (-14, -64, 10), (-14, -38, 17), 28), (sh.dur, (8, -62, 11), (14, -30, 20), 28)], shake=.005), fstop=11)


def s_d03(sh):
    """a pack of small theropods sprints through the forest; a T-rex hunts behind them"""
    w, ter = nat(sh, 'cretaceous'); fx, fy = fz(w)
    for k in range(4): go(sh, 'raptor', [(fx - 20 + k * 1.4, fy + 4 + k * 1.2), (fx + 30, fy + 2 + k)], ter, clip='run', name=f'pack{k}', phase=k * .2)
    go(sh, 'trex', [(fx - 34, fy + 8), (fx + 20, fy + 4)], ter, clip='run', name='hunter', anim=1.0)
    sh.camera(cam_fn([(0, G(ter, fx + 4, fy - 6, 1.4), G(ter, fx - 10, fy + 5, 1.5), 26), (sh.dur, G(ter, fx + 6, fy - 5, 1.5), G(ter, fx + 6, fy + 4, 2), 26)], shake=.01,
                     quake=lambda t: .012), fstop=6)


def droplets(sh, center, t0, t1, n=120, seed=0, speed=2.5):
    r = random.Random(seed); m = bpy.data.materials.new('drop'); m.use_nodes = True; b = m.node_tree.nodes['Principled BSDF']; b.inputs['Roughness'].default_value = 0
    try: b.inputs['Transmission Weight'].default_value = 1.0
    except Exception: pass
    obs = []
    for k in range(n):
        o = T.lib.sphere(f'drop{seed}_{k}', r.uniform(.004, .01), (0, 0, -99), m, seg=6, rings=4)
        a = r.uniform(0, 6.3); v = Vector((math.cos(a), math.sin(a), r.uniform(.2, 1.0))) * speed * r.uniform(.5, 1.2); obs.append((o, v, r.uniform(t0, t1)))
    def u(t):
        for o, v, ts in obs:
            k = t - ts; o.location = (Vector(center) + v * k + Vector((0, 0, -4.9 * k * k))) if 0 < k < 1.2 else (0, 0, -99)
    sh.updates.append(u)


def s_d04(sh):
    """a feathered dinosaur shakes out its feathers like a wet dog"""
    w, ter = nat(sh, 'cretaceous'); fx, fy = fz(w)
    b = still(sh, 'archaeo', (fx, fy), 20, ter, clip='look', name='fluffy', scale=1.6)
    b.set_clip(CR.clip_of(b, 'shake'), 1.6, at=4.0); b.set_clip(CR.clip_of(b, 'look'), 1.0, at=7.5)
    hz = ter.z(fx, fy); droplets(sh, (fx, fy, hz + .5), 4.0, 7.0, 160, 1)
    sh.camera(cam_fn([(0, (fx + .8, fy - 2.6, hz + .6), (fx, fy, hz + .45), 40), (sh.dur, (fx + .6, fy - 2.2, hz + .55), (fx, fy, hz + .45), 42)], shake=.002), fstop=3.2)


def s_d05(sh):
    """a small bird lands on a giant dinosaur's head; the dinosaur does not react"""
    w, ter = nat(sh, 'cretaceous'); fx, fy = fz(w); hz = ter.z(fx, fy + 6)
    big = still(sh, 'tricera', (fx, fy + 6), 25, ter, clip='idle', name='calmtri')
    yw = math.radians(25); top = Vector((fx, fy + 6, hz)) + Vector((math.sin(yw), -math.cos(yw), 0)) * 3.0 + Vector((0, 0, 2.3))
    land = 5.0
    def fly(t):
        u = ease(min(1, t / land)); p = (top + Vector((-14, 10, 9))).lerp(top, u) + Vector((0, 0, 3 * math.sin(u * math.pi) * (1 - u)))
        return (p.x, p.y, 120, p.z)
    bird = swim(sh, 'pigeon', fly, 'lander', clip='fly', scale=.9)
    bird.set_clip(CR.clip_of(bird, 'fly'), .02, at=land)
    sh.camera(cam_fn([(0, (fx + 7, fy - 4, hz + 3.2), tuple(top), 34), (sh.dur, (fx + 6, fy - 3, hz + 3.0), tuple(top), 40)], shake=.003), fstop=5)


# ------------------------------------------------------------------ a: the asteroid
def s_a01(sh):
    """peaceful Cretaceous: dinosaurs graze, a dragonfly lands on a Triceratops"""
    w, ter = nat(sh, 'cretaceous'); fx, fy = fz(w)
    tri = still(sh, 'tricera', (fx, fy + 6), -20, ter, clip='graze', name='grazer')
    still(sh, 'tricera', (fx - 9, fy + 16), 40, ter, clip='graze', name='grazer2', phase=1.3)
    go(sh, 'sauropod', [(fx + 40, fy + 60), (fx - 20, fy + 70)], ter, name='bgsaur')
    yw = math.radians(-20); hd = Vector((fx, fy + 6, ter.z(fx, fy + 6))) + Vector((math.sin(yw), -math.cos(yw), 0)) * 3.4 + Vector((0, 0, 1.9))
    df = swim(sh, 'dragonfly', lambda t: (*(lambda p: (p.x, p.y))((hd + Vector((3, -2, 1.5))).lerp(hd, ease(min(1, t / 3.5)))), 200,
                                          ((hd + Vector((3, -2, 1.5))).lerp(hd, ease(min(1, t / 3.5)))).z + .05 * math.sin(t * 9)), 'dfly', clip='fly', scale=1.5)
    sh.camera(cam_fn([(0, G(ter, fx + 3, fy - 2, 2.0), tuple(hd), 30), (sh.dur, G(ter, fx + 2.4, fy - 1, 2.0), tuple(hd), 36)], shake=.003), fstop=5)


def impact_phase(sh, w, fn):
    w['phase_fn'] = lambda T: fn(T - 5.0)            # world ticks run at shot time + 5 s


def s_a02(sh):
    """a bright dot appears in the sky - slow cinematic zoom"""
    w, ter = nat(sh, 'impact'); fx, fy = fz(w); impact_phase(sh, w, lambda t: dict(entry=.02 + .05 * t / sh.dur))
    still(sh, 'tricera', (fx + 2, fy + 8), 160, ter, clip='graze', name='unaware')
    a0 = Vector((fx - 4000, fy + 9000, 9000)) ; tgt = a0.lerp(Vector((fx + 200, fy + 3200, 0)), .05)
    sh.camera(cam_fn([(0, G(ter, fx, fy - 6, 1.8), tuple(tgt), 18), (sh.dur, G(ter, fx, fy - 6, 1.8), tuple(tgt), 60)], shake=.002), fstop=16)


def s_a03(sh):
    """the asteroid enters the atmosphere; the sky glows orange; white flash"""
    w, ter = nat(sh, 'impact'); fx, fy = fz(w); impact_phase(sh, w, lambda t: dict(entry=.2 + .8 * t / sh.dur))
    flash_light(sh, lambda t: max(0.0, (t - sh.dur + .5) / .5), 80, (1, .9, .8))
    sh.updates.append(lambda t: setattr(bpy.context.scene.view_settings, 'exposure', -.45 + 3.5 * max(0.0, (t - sh.dur + .4) / .4)))
    sh.camera(cam_fn([(0, G(ter, fx, fy - 10, 3), (fx - 600, fy + 3000, 2000), 22), (sh.dur, G(ter, fx, fy - 10, 3), (fx, fy + 3200, 200), 22)], shake=.006), fstop=16)


def s_a04(sh):
    """impact: fireball, shockwave, earthquakes, a wall of dust"""
    w, ter = nat(sh, 'impact'); fx, fy = fz(w); impact_phase(sh, w, lambda t: dict(boom=t / 10.0, burn=1 if t > 6 else 0))
    sh.updates.append(lambda t: setattr(bpy.context.scene.view_settings, 'exposure', -.45 - 1.6 * min(1.0, t / 2.5)))
    for k, (x, y) in enumerate([(-8, 30), (10, 36), (-20, 50), (16, 60)]): falling_tree(sh, ter, (fx + x, fy + y), 3.0 + k * .4, 180 + k * 10, 18)
    sh.camera(cam_fn([(0, G(ter, fx, fy - 20, 6), (fx + 200, fy + 3200, 400), 22), (sh.dur, G(ter, fx, fy - 26, 8), (fx + 200, fy + 3200, 900), 20)], shake=.006,
                     quake=lambda t: .08 * math.exp(-max(0, t - 2.5) * .25) if t > 2.5 else .01), fstop=16)


def ash_fall(sh, center, n=400, seed=0, area=20):
    r = random.Random(seed); m = TR.simple_mat('ashm', ('',), '#8a8580', .2); obs = []
    for k in range(n):
        o = T.lib.sphere(f'ash{seed}_{k}', r.uniform(.01, .03), (0, 0, -99), m, seg=4, rings=3); obs.append((o, r.uniform(-area, area), r.uniform(-area, area), r.uniform(.3, .8), r.uniform(0, 20)))
    def u(t):
        for o, x, y, v, ph in obs:
            h = 12 - ((t + ph) * v) % 12; o.location = (center[0] + x + math.sin(t + ph) * .4, center[1] + y, center[2] + h)
    sh.updates.append(u)


def s_a05(sh):
    """forests burn, the sky goes dark, dinosaurs struggle in the cold"""
    w, ter = nat(sh, 'impact'); fx, fy = fz(w); impact_phase(sh, w, lambda t: dict(burn=1))
    bpy.context.scene.view_settings.exposure = -1.6; ash_fall(sh, G(ter, fx, fy + 8), 500, 1)
    b = go(sh, 'tricera', [(fx - 10, fy + 12), (fx + 4, fy + 8)], ter, name='cold', anim=.6)
    b.set_clip(CR.clip_of(b, 'Fall'), .8, at=5.5); f = b.path; b.move(lambda t: f(min(t, 5.5)))
    sh.camera(cam_fn([(0, G(ter, fx + 2, fy - 4, 1.8), G(ter, fx - 4, fy + 10, 1.8), 28), (sh.dur, G(ter, fx + 3, fy - 3, 1.7), G(ter, fx + 2, fy + 8, 1.6), 30)], shake=.004), fstop=6)


def s_a06(sh):
    """a bird flies calmly out of the smoke"""
    w, ter = nat(sh, 'impact'); fx, fy = fz(w); impact_phase(sh, w, lambda t: dict(burn=1))
    bpy.context.scene.view_settings.exposure = -.6
    sm = TR.plume('wall', G(ter, fx, fy + 30, -1), height=26, r0=6, r1=11, drift=(3, 0), col=(.3, .28, .26), density=.35, speed=1.2, seed=9)
    sh.updates.append(sm)
    hz = ter.z(fx, fy)
    swim(sh, 'pigeon', line3((fx, fy + 30, hz + 6), (fx + .4, fy - 1, hz + 3.2), 0, sh.dur * 1.05, .15, .9), 'survivor', clip='fly', scale=1.0)
    sh.camera(cam_fn([(0, (fx + .6, fy - 3, hz + 3.0), (fx, fy + 10, hz + 3.6), 35), (sh.dur, (fx + .8, fy - 3.4, hz + 3.0), (fx, fy, hz + 3.4), 35)], shake=.003,
                     focus=lambda t: Vector((fx, fy + 30 - 31 * t / sh.dur, hz + 4.5))), fstop=5)


def leaf_pile(ter, x, y, n=60, seed=0):
    r = random.Random(seed); m = TR.simple_mat('deadleaf', ('leaves',), '#6a4a22', .3)
    for k in range(n):
        o = T.box(f'leaf{seed}_{k}', (r.uniform(.04, .09), r.uniform(.06, .12), .003), (x + r.gauss(0, .18), y + r.gauss(0, .18), ter.z(x, y) + r.uniform(0, .08)), m)
        o.rotation_euler = (r.uniform(-.5, .5), r.uniform(-.5, .5), r.uniform(0, 6.3))


def s_a07(sh):
    """the camera pans down through the smoke to a tiny mammal under fallen leaves, blinking"""
    w, ter = nat(sh, 'impact'); fx, fy = fz(w); impact_phase(sh, w, lambda t: dict(burn=1))
    bpy.context.scene.view_settings.exposure = -.8; leaf_pile(ter, fx, fy, 90, 1)
    sm = TR.smoke_column('lowsmoke', G(ter, fx + 1, fy + 3, 2), rate=8, life=10, rise=.8, r0=1.5, r1=5, wind=(.3, -.2), turb=1.5, col=(.3, .28, .26), density=.08, voxel=.15, seed=2)
    sh.updates.append(sm)
    still(sh, 'rat', (fx, fy + .05), 200, ter, clip='look', name='survivor_mammal', scale=1.0)
    hz = ter.z(fx, fy)
    sh.camera(cam_fn([(0, (fx + .4, fy - 1.0, hz + 6), (fx, fy + 4, hz + 6), 30), (sh.dur * .7, (fx + .45, fy - 1.0, hz + .35), (fx, fy + .05, hz + .02), 45), (sh.dur, (fx + .4, fy - .85, hz + .2), (fx, fy + .05, hz + .02), 55)],
                     shake=.002), fstop=2.8)


# ------------------------------------------------------------------ n: the age of mammals
def s_n01(sh):
    """small early mammals scurry through the forest"""
    w, ter = nat(sh, 'paleogene'); fx, fy = fz(w)
    for k in range(6):
        go(sh, 'rat', [(fx - 3 + k * .3, fy + k * .4), (fx + 1 + k * .2, fy + 1.5 + k * .3), (fx + 4, fy + .5 + k * .5)], ter, clip='run' if k % 2 else 'walk',
           name=f'scurry{k}', t0=k * .8, phase=k * .1)
    leaf_pile(ter, fx + 1, fy + 1, 120, 3)
    hz = ter.z(fx, fy)
    sh.camera(cam_fn([(0, (fx - 1.5, fy - 1.8, hz + .35), (fx, fy + 1, hz + .05), 30), (sh.dur, (fx + 1.0, fy - 1.6, hz + .3), (fx + 2, fy + 1.5, hz + .05), 30)], shake=.002), fstop=3.5)


def s_n02(sh):
    """mammals spread: grasslands, forests and the sky (bats)"""
    w, ter = nat(sh, 'paleogene'); fx, fy = fz(w)
    for k in range(5): go(sh, 'deer', [(fx - 10 + k * 2, fy + 14 + k * 3), (fx + 30, fy + 12 + k * 3)], ter, name=f'mam{k}', phase=k * .3, scale=.8)
    flock(sh, 'bat', 9, (fx + 30, fy + 30, ter.z(fx, fy) + 12), (fx - 30, fy - 5, ter.z(fx, fy) + 8), 0, sh.dur, seed=5, spread=4, scale=1.2)
    sh.camera(cam_fn([(0, G(ter, fx, fy - 12, 2.5), G(ter, fx, fy + 20, 4), 24), (sh.dur, G(ter, fx + 4, fy - 10, 3), G(ter, fx + 4, fy + 20, 5), 24)], shake=.003), fstop=8)


def dino_skeleton(name, loc, yaw=0.0, L=10.0):
    """a weathered theropod skeleton half sunk in the ground: vertebrae, ribs, legs, skull"""
    bone = TR.simple_mat('bone', ('',), '#d8ccb0', .2, rough=.7); root = bpy.data.objects.new(name, None); TR.coll().objects.link(root)
    sp = lambda u: Vector((0, -L * .5 + L * u, L * .18 * math.sin(math.pi * min(1, u * 1.4)) + .2))
    for k in range(36):
        u = k / 35; p = sp(u); s = .1 * L * .1 * (1.6 - abs(u - .35))
        v = T.lib.sphere(f'{name}_v{k}', s, tuple(p), bone, seg=8, rings=6); v.parent = root
        if .2 < u < .5:
            for sx in (-1, 1):
                pts = [p + Vector((sx * L * .1 * math.sin(a), 0, -L * .12 * (1 - math.cos(a)))) for a in (0, .5, 1.0, 1.5, 1.9)]
                r_ = T.lib.tube(f'{name}_rib{k}{sx}', pts, .015 * L * .1, m=bone); r_.parent = root
    for sx in (-1, 1):
        hp = sp(.42); pts = [hp, hp + Vector((sx * .2, -L * .05, -L * .09)), hp + Vector((sx * .2, L * .02, -L * .17)), hp + Vector((sx * .25, -L * .04, -L * .21))]
        lg = T.lib.tube(f'{name}_leg{sx}', pts, .04 * L * .1, m=bone); lg.parent = root
    sk = T.lib.sphere(f'{name}_skull', L * .07, tuple(sp(0) + Vector((0, -L * .03, .1))), bone, seg=16, rings=8); sk.scale = (.7, 1.6, .8); sk.parent = root
    root.location = loc; root.rotation_euler = (math.radians(-6), math.radians(4), math.radians(yaw)); return root


def s_n03(sh):
    """a tiny mammal looks up at a giant dinosaur skeleton, checks both ways, walks off with confidence"""
    w, ter = nat(sh, 'paleogene'); fx, fy = fz(w); hz = ter.z(fx, fy)
    dino_skeleton('skel', (fx, fy + 4, hz - .6), 90, 12)
    b = CR.beast(sh, 'rat', 'brave', clip=CR.SPEC['rat']['clips']['look'])
    b.set_clip(CR.clip_of(b, 'walk'), 1.0, at=2.0); v = stride_of(b, 'walk')
    b.move(lambda t: (fx + .2 + (v * (t - 2.0) if t > 2.0 else 0), fy + .3, 0 if t < 1.0 else (-40 if t < 1.5 else (40 if t < 2.0 else 90)))).on(ter)
    sh.camera(cam_fn([(0, (fx - .6, fy - 1.4, hz + .25), (fx + .2, fy + 2, hz + 1.2), 26), (sh.dur, (fx - .4, fy - 1.3, hz + .25), (fx + .6, fy + 1, hz + .6), 28)], shake=.002), fstop=4)


def s_n04(sh):
    """an ancient primate climbs a tree: grasping hands, forward-facing eyes"""
    w, ter = nat(sh, 'paleogene'); fx, fy = fz(w); hz = ter.z(fx, fy + 3)
    tm = TR.simple_mat('trunkm', ('bark',), '#5a4a3a', 1.0)
    trunk = T.cyl('climbtree', .32, 14, (fx, fy + 3, hz + 7), tm, v=24)
    b = CR.beast(sh, 'monkey', 'primate', clip=CR.SPEC['monkey']['clips']['dance'], speed=.25)
    CR.addpose(b, {'Arm': (0, 0, -60), 'ForeArm': (0, 0, -40), 'UpLeg': (-50, 0, 0), 'Leg': (80, 0, 0)}, at=0.0, ramp=.01)
    def climb(t):
        k = t * .9; hops = math.floor(k) + ease(k % 1.0)                          # bursts of climbing, pauses for grip
        z = hz + .4 + hops * .55
        return (fx, fy + 3 - .42, 180, z)
    b.move(climb)
    def cam(t):                                    # rides up with the climber, slightly below and to the side
        z = climb(t)[3]; m = Vector((fx, fy + 2.5, z + .35))
        return (m + Vector((1.3, -2.0, -.25)), m, 35, 0, m, .002)
    sh.camera(cam, fstop=4)
