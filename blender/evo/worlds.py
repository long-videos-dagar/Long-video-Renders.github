"""The eras.  Each builder makes a complete, dense world and returns a dict with the terrain + things the shots animate."""
import math, random
import bpy
from mathutils import Vector
import terra as TR
import town as T
import lib

ROCK = ('rock', 'cliff')
BASALT = ('volcanic', 'rock')


def world_sky(kind='day', strength=1.0, rot=0.0, tint=None):
    """HDRI sky (Poly Haven) or a Nishita fallback"""
    ids = {'day': 'kloofendal_48d_partly_cloudy_puresky', 'haze': 'kloofendal_misty_morning_puresky', 'sunset': 'kloppenheim_06_puresky',
           'storm': 'kloofendal_overcast_puresky', 'dusk': 'qwantani_dusk_2_puresky', 'golden': 'golden_gate_hills', 'night': 'qwantani_night_puresky'}
    ok = False
    if TR.PH:
        try:
            lib.world_hdri(aid=ids.get(kind, kind), strength=strength, rot=math.radians(rot) if False else rot, res='2k'); ok = True
        except Exception as e:
            lib.log('sky fail', kind, e)
            try: lib.world_hdri('sky', 'clouds', strength=strength); ok = True
            except Exception: pass
    if not ok:
        w = bpy.data.worlds.new('sky'); bpy.context.scene.world = w; w.use_nodes = True; N = w.node_tree.nodes
        sk = N.new('ShaderNodeTexSky'); sk.sky_type = 'MULTIPLE_SCATTERING'
        try: sk.sun_elevation = math.radians(20); sk.air_density = 1.0; sk.dust_density = 3.0 if kind in ('storm', 'sunset') else 1.0
        except Exception: pass
        w.node_tree.links.new(sk.outputs[0], N['Background'].inputs[0]); N['Background'].inputs[1].default_value = .35 * strength
    if tint and bpy.context.scene.world.node_tree:
        N, L = bpy.context.scene.world.node_tree.nodes, bpy.context.scene.world.node_tree.links; bg = N['Background']
        src = bg.inputs['Color'].links[0].from_socket if bg.inputs['Color'].links else None
        if src:
            mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs['Factor'].default_value = 1
            L.new(src, mx.inputs['A']); mx.inputs['B'].default_value = (*tint, 1); L.new(mx.outputs['Result'], bg.inputs['Color'])
    sc = bpy.context.scene; sc.view_settings.view_transform = 'AgX'
    try: sc.view_settings.look = 'AgX - Medium High Contrast'
    except Exception: pass


# ------------------------------------------------------------------ 4.5 billion years ago
def young_earth(seed=1):
    """molten young Earth: black basalt plains cracked with glowing lava, a ring of erupting volcanoes, lava rivers, ash
    columns lit from below, a boiling sea on one side, an orange storm sky.  Camera space: x[-150, 150], y[-60, 400]"""
    world_sky('storm', strength=.7, tint=(1.0, .62, .4))
    V = [(0, 260, 70, 95), (-170, 330, 85, 120), (190, 300, 70, 100), (-90, 520, 120, 160), (120, 560, 140, 190)]
    def h(x, y):
        z = TR.fbm(x, y, .012, 6, seed) * 9 + TR.ridged(x, y, .02, 4, seed) * 2.5
        z += sum(TR.volcano_h(x, y, cx, cy, r, hh, seed=k) for k, (cx, cy, r, hh) in enumerate(V))
        z -= TR.smooth01((x + 60) / -80) * 14                        # the sea basin to the left
        return z
    rock = TR.blend_mat('basalt', TR.layer(BASALT, '#2a2624', 6.0, tint='#6a5a52'),
                        [(TR.layer(('rock', 'cliff', 'lava'), '#3a2e2a', 10.0, tint='#5a4840'), dict(slope=(.9, .7), noise=.05)),
                         (TR.layer(('ash', 'dirt', 'ground'), '#3a3430', 4.0, tint='#4a4440'), dict(slope=(.95, 1.0), noise=.08))], bump=.6)
    ter = TR.Terrain('ground', h, 1400.0, 300, rock, center=(0, 300), inner=(260, 260))
    lm = TR.lava_mat()
    rivers = []
    for k, (cx, cy, r, hh) in enumerate(V[:3]):
        for j in range(3):
            a = j * 2.1 + k
            o, pts = TR.lava_river(f'lava{k}{j}', ter, (cx + math.cos(a) * r * .2, cy + math.sin(a) * r * .2), steps=140, step=1.4, width=4 + j, seed=k * 5 + j)
            rivers.append(o)
        crater = T.lib.sphere(f'crater{k}', r * .17, (cx, cy, ter.z(cx, cy) + 1.0), lm, seg=24, rings=8); crater.scale = (1, 1, .08)
    # cracked lava plain patches near the camera
    for k in range(9):
        r_ = random.Random(seed * 10 + k); x = r_.uniform(-80, 80); y = r_.uniform(40, 180)
        p = T.lib.sphere(f'lavapool{k}', r_.uniform(4, 10), (x, y, ter.z(x, y) - .2), lm, seg=20, rings=6); p.scale = (1, r_.uniform(.5, 1.2), .03)
    # ash plumes, glowing from the craters
    plumes = [TR.smoke_column(f'plume{k}', (cx, cy, ter.z(cx, cy) - 2), rate=3.0, life=16, rise=9.0 + k, r0=r * .1, r1=r * .45, wind=(3.0, 1.0),
                              turb=r * .12, density=.03, glow=.6 if k < 3 else 0.0, voxel=max(1.2, r * .025), seed=k) for k, (cx, cy, r, hh) in enumerate(V)]
    # boiling sea + steam
    sea = TR.ocean('sea', 900, (-420, 300, -6.5), wave=1.4, choppy=1.6, col='#1a2a26', murk='#3a3020', foam=True)
    steam = [TR.smoke_column(f'steam{k}', (-150 - k * 60, 120 + k * 70, -7), rate=2.0, life=10, rise=4.0, r0=6, r1=22, wind=(2.0, .5), turb=6,
                             col=(.75, .72, .7), density=.01, voxel=1.5, seed=k + 9) for k in range(4)]
    # rubble + boulders everywhere
    TR.scatter(ter, ['namaqualand_boulder_02', 'namaqualand_boulder_04', 'namaqualand_boulder_05', 'rock_07', 'rock_09', 'boulder_01', 'moon_rock_03', 'moon_rock_06'],
               420, (-140, 140, 10, 260), seed=seed, scale=(.6, 2.6), slope_min=.6, zrange=(-2, 400), fallback=TR.fallback_rock)
    TR.scatter(ter, ['coast_rocks_02', 'rock_face_01', 'namaqualand_cliff_02'], 40, (-200, 200, 100, 500), seed=seed + 1, scale=(1.5, 4.0), slope_min=.3,
               fallback=TR.fallback_rock)
    TR.sun_light(200, 16, 3.5, (1, .62, .38))
    for k, (cx, cy, r, hh) in enumerate(V[:3]):                         # crater glow on the ash and slopes
        l = bpy.data.lights.new(f'craterlight{k}', 'POINT'); l.energy = 2.5e5; l.color = (1, .4, .1); l.shadow_soft_size = r * .2
        o = bpy.data.objects.new(f'craterlight{k}', l); TR.coll().objects.link(o); o.location = (cx, cy, ter.z(cx, cy) + 4)
    TR.fog(.0005, (1.0, .7, .5), .3)
    return dict(ter=ter, sea=[sea], volcanoes=V, smoke=plumes + steam)


def young_earth_tick(w, t):
    TR.lava_tick(t); TR.ocean_tick(w['sea'], t)
    for u in w['smoke']: u(t)
