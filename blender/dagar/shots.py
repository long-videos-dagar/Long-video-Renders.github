"""Test scene 'Quiet Morning' - 5 shots. CHAR_001 'Walt' in the kitchen. Every shot builds its own scene, frames are local (1..n)."""
import bpy, math, os
from mathutils import Vector
from common import *
from lib import coll
import lib, char, kit as env, phys
from char import Char, expr_track, EXPR

FPS = 30
SPOT = (-.55, 2.42)      # where Walt stands
MUGP = Vector((-.35, 2.80, env.CT + .0))

class Rig:
    cam = None; fn = None
RIG = Rig()

def cam_install():
    def on_cam(scene, *a):
        if RIG.fn is None: return
        t = (scene.frame_current - 1) / scene.render.fps
        loc, look, lens, foc, fst, roll = RIG.fn(t)
        c = RIG.cam; c.location = loc
        q = (Vector(look) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler(); q.rotate_axis('Z', math.radians(roll)) if roll else None
        c.rotation_euler = q; c.data.lens = lens
        c.data.dof.focus_distance = max(.1, (Vector(foc) - Vector(loc)).length)
    bpy.app.handlers.frame_change_pre[:] = [h for h in bpy.app.handlers.frame_change_pre if h.__name__ != 'on_cam'] + [on_cam]

def camera(fn, fstop=2.8):
    cd = bpy.data.cameras.new('Cam'); cd.sensor_width = 36; cd.sensor_fit = 'AUTO'; cd.clip_end = 100
    o = bpy.data.objects.new('Cam', cd); bpy.context.scene.collection.objects.link(o); bpy.context.scene.camera = o
    cd.dof.use_dof = True; cd.dof.aperture_fstop = fstop
    RIG.cam, RIG.fn = o, fn; cam_install(); return o

def walt(**kw):
    w = Char('CHAR_001', 'Walt', skin='#f7f4ee', body='#3d73b8', hair='spiky', hair_col='#4a2c16', stache=None, **kw)
    return w

def common_world(exposure=0.4):
    sc = bpy.context.scene
    lib.world_color('#070b18', .6); sc.view_settings.exposure = exposure
    sc.view_settings.look = 'AgX - Punchy' if False else sc.view_settings.look

def idle(base_loc, yaw, t, sway=.5):
    return dict(loc=base_loc, yaw=yaw + math.sin(t * 1.3) * sway, lean=math.sin(t * 1.1) * 1.2)

def build_common(n):
    sc = bpy.context.scene; sc.render.fps = FPS; sc.frame_start = 1; sc.frame_end = n
    common_world()
    k = env.kitchen()
    char.SHOT_T0[0] = 0.0; char.install()
    return k

# ---------------------------------------------------------------- shot 1: wide establishing
def wide(n):
    k = build_common(n); w = walt()
    ex = expr_track([(0, 'deadpan'), (1.6, 'deadpan'), (1.9, 'smile'), (2.9, 'smile')])
    def fn(t):
        s = idle((SPOT[0], SPOT[1], 0), 18, t)
        u = ease(t / 3.0)
        s['head'] = K([(0, (-10, 0, 0)), (1.2, (-10, 2, 0)), (1.6, (18, 4, 0)), (2.6, (18, 4, 0))])(t)
        s['handL'] = Vector((SPOT[0] - .16, SPOT[1] - .04, .62 + math.sin(t * 1.3) * .01))
        s['handR'] = Vector(K([(0, (SPOT[0] + .22, SPOT[1] - .02, .6)), (2.0, (SPOT[0] + .22, SPOT[1] - .02, .6)), (2.5, (SPOT[0] + .3, SPOT[1] + .3, env.CT + .12))])(t))
        s['face'] = ex(t); return s
    w.fn = fn
    camera(lambda t: ((-2.3 + 1.2 * ease(t / 3.0), -0.7 + 1.0 * ease(t / 3.0), 1.95 - .45 * ease(t / 3.0)), (-.1 + .0 * t, 2.9, .95), 27 + 5 * ease(t / 3.0), (SPOT[0], SPOT[1], 1.0), 0, 0), fstop=3.2)
    return dict(char=w)

# ---------------------------------------------------------------- shot 2: face close-up
def face(n):
    k = build_common(n); w = walt()
    ex = expr_track([(0, 'deadpan'), (.7, 'deadpan'), (.95, 'worry'), (1.55, 'worry'), (1.75, 'shock'), (2.5, 'shock')])
    def fn(t):
        s = idle((SPOT[0], SPOT[1], 0), -32, t, sway=.2)
        s['head'] = K([(0, (-8, 3, 0)), (1.0, (0, 0, 0)), (1.8, (10, -4, 3))])(t)
        s['handL'] = Vector((SPOT[0] - .2, SPOT[1] - .05, .7)); s['handR'] = Vector((SPOT[0] + .2, SPOT[1] - .05, .7))
        s['face'] = ex(t); return s
    w.fn = fn
    head = Vector((SPOT[0], SPOT[1], 1.17))
    camera(lambda t: ((head.x - .95 + .35 * ease(t / 2.5), head.y - 1.35 + .45 * ease(t / 2.5), 1.22 + .02 * t), (head.x, head.y, head.z), 33 + 5 * ease(t / 2.5), (head.x, head.y - .25, head.z), 0, -2 + 3 * ease(t / 2.5)), fstop=2.0)
    return dict(char=w)

# ---------------------------------------------------------------- shot 3: tap water (Mantaflow)
def water(n):
    k = build_common(n); w = walt()
    ex = expr_track([(0, 'smile'), (1.2, 'smile'), (1.5, 'deadpan')])
    def fn(t):
        s = idle((SPOT[0] + .0, SPOT[1], 0), 40, t, sway=.4)
        s['head'] = K([(0, (0, -4, 0)), (3, (0, -10, 0))])(t)
        s['handL'] = Vector((SPOT[0] - .2, SPOT[1] + .0, .62)); s['handR'] = Vector((SPOT[0] + .3, SPOT[1] + .12, .66))
        s['face'] = ex(t); return s
    w.fn = fn
    camera(lambda t: ((1.25 - .2 * ease(t / 3.0), 1.9, 1.5 - .05 * t / 3.0), (k['fx'] - .02, k['fy'] - .05, .72), 40, (k['fx'], k['fy'] - .3, .8), 0, 0), fstop=3.5)
    res = int(os.environ.get('FLUID_RES', 96))
    sink = [bpy.data.objects[nm] for nm in ('sink_floor', 'sink_f', 'sink_b', 'sink_l', 'sink_r')]
    nz = (k['fx'], k['fy'] - .3, env.CT + .205)
    if os.environ.get('NOFLUID') == '1': return dict(char=w)
    dom = phys.fluid_pour(nz, (.08, 2.88, .50), (.82, 3.27, 1.12), sink, res=res, n_frames=n, start_vel=(0, 0, -.9), radius=.018, rate_frames=(6, 0))
    if os.environ.get('NOBAKE') != '1': phys.bake_fluid(dom)
    # water look
    dom.display_type = 'WIRE'
    wm = water_mat(); dom.data.materials.append(wm)
    return dict(char=w, dom=dom)

# ---------------------------------------------------------------- shot 4: mug drop (Bullet)
HAND_PATH = lambda t: Vector(K([(0, (SPOT[0] + .1, 2.99, env.CT + .12)), (.35, (SPOT[0] + .1, 2.99, env.CT + .12)), (.55, (MUGP.x + .0, 3.0, env.CT + .1)), (.95, (MUGP.x, 2.88, env.CT + .1)), (1.15, (MUGP.x, 2.62, env.CT + .12))])(t))
def drop(n):
    k = build_common(n); w = walt()
    ex = expr_track([(0, 'deadpan'), (.5, 'worry'), (1.0, 'shock'), (1.6, 'shock')])
    def fn(t):
        s = idle((SPOT[0], SPOT[1], 0), 5, t, sway=.1)
        h = HAND_PATH(t); s['handR'] = h; s['handL'] = Vector((SPOT[0] - .2, SPOT[1], .62))
        s['lean'] = 10 + 10 * ease((t - .3) / .8)
        s['head'] = K([(0, (0, 0, 0)), (.5, (-5, 8, 0)), (1.2, (20, 8, 0))])(t)
        s['face'] = ex(t); return s
    w.fn = fn
    mug = k['mug']; mug.location = MUGP
    pusher = lib.sphere('pusher', .04, (0, 0, 0), None, seg=12, rings=8, c=coll('Set')); pusher.hide_render = True
    floor = [bpy.data.objects['floor']]; stat = [bpy.data.objects['top_l']]
    path = phys.bake_mug(mug, floor, stat, pusher, n, FPS, HAND_PATH)
    def pos(t):
        i = max(0, min(len(path) - 1, int(t * FPS))); return path[i]
    def cfn(t):
        p = pos(t); base = Vector((MUGP.x, 2.75, .55))
        look = base.lerp(p, .75 if t > .9 else .0 + .75 * ease((t - .5) / .5))
        return ((.75 - .2 * ease(t / 3.0), 1.0 - .05 * t, .42 + .12 * math.sin(t * .8)), look, 32, p if t > .9 else base, 0, 0)
    camera(cfn, fstop=2.2)
    return dict(char=w, path=path)

# ---------------------------------------------------------------- shot 5: reaction
def react(n):
    k = build_common(n); w = walt()
    mug = k['mug']; mug.location = (SPOT[0] + .02, SPOT[1] - .25, .09); mug.rotation_euler = (math.pi / 2, 0, .8)
    ex = expr_track([(0, 'shock'), (.5, 'scream'), (1.7, 'scream')])
    def fn(t):
        s = idle((SPOT[0], SPOT[1], 0), 0, t, sway=0)
        s['lean'] = 28 + 4 * ease(t / .4); s['crouch'] = .4
        hz = 1.0 + .0
        s['handL'] = Vector((SPOT[0] - .26, SPOT[1] - .12, 1.12 + math.sin(t * 18) * .01)); s['handR'] = Vector((SPOT[0] + .26, SPOT[1] - .12, 1.12 + math.sin(t * 18 + 1) * .01))
        s['head'] = (0, 4, 3 * math.sin(t * 22) * ease(t / .6)); s['face'] = ex(t); return s
    w.fn = fn
    camera(lambda t: ((SPOT[0] - .1 + .1 * math.sin(t * 1.4), SPOT[1] - 1.75 + .55 * ease(t / 2.0), .8 + .3 * ease(t / 2.0)), (SPOT[0], SPOT[1], 1.0), 30 + 14 * ease(t / 2.0), (SPOT[0], SPOT[1] - .1, 1.0), 0, -4 + 5 * ease(t / 2.0)), fstop=2.4)
    return dict(char=w)

SHOTS = dict(wide=wide, face=face, water=water, drop=drop, react=react)
