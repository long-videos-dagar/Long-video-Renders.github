"""The eras.  Each builder makes a complete, dense world and returns a dict with the terrain + things the shots animate."""
import math, random, os
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
    world_sky('sunset', strength=1.6, tint=(1.0, .7, .5)); bpy.context.scene.view_settings.exposure = .3
    V = [(0, 260, 70, 95), (-170, 330, 85, 120), (190, 300, 70, 100), (-90, 520, 120, 160), (120, 560, 140, 190)]
    def h(x, y):
        z = TR.fbm(x, y, .012, 6, seed) * 9 + TR.ridged(x, y, .02, 4, seed) * 2.5
        z += sum(TR.volcano_h(x, y, cx, cy, r, hh, seed=k) for k, (cx, cy, r, hh) in enumerate(V))
        z -= TR.smooth01((x + 60) / -80) * 14                        # the sea basin to the left
        return z
    rock = TR.blend_mat('basalt', TR.layer(BASALT, '#4a4440', 6.0, tint='#c8b8b0', aid='dark_rock'),
                        [(TR.layer(('rock', 'cliff', 'lava'), '#5a4e48', 10.0, tint='#9a8478'), dict(slope=(.9, .7), noise=.05)),
                         (TR.layer(('ash', 'dirt', 'ground'), '#6a6058', 4.0, tint='#b0a8a0', aid='burned_ground_01'), dict(slope=(.95, 1.0), noise=.08))], bump=.6)
    ter = TR.Terrain('ground', h, 1400.0, 300, rock, center=(0, 300), inner=(260, 260))
    lm = TR.lava_mat()
    rivers = []
    for k, (cx, cy, r, hh) in enumerate(V[:3]):
        for j in range(3):
            a = j * 2.1 + k
            o, pts = TR.lava_river(f'lava{k}{j}', ter, (cx + math.cos(a) * r * .2, cy + math.sin(a) * r * .2), steps=140, step=1.4, width=4 + j, seed=k * 5 + j)
            rivers.append(o)
        crater = T.lib.sphere(f'crater{k}', r * .12, (cx, cy, ter.z(cx, cy) - 2.0), lm, seg=24, rings=8); crater.scale = (1, 1, .12)
    # cracked lava plain patches near the camera
    for k in range(9):
        r_ = random.Random(seed * 10 + k); x = r_.uniform(-80, 80); y = r_.uniform(40, 180)
        p = T.lib.sphere(f'lavapool{k}', r_.uniform(4, 10), (x, y, ter.z(x, y) - .2), lm, seg=20, rings=6); p.scale = (1, r_.uniform(.5, 1.2), .03)
    # ash plumes, glowing from the craters
    plumes = [TR.plume(f'plume{k}', (cx, cy, ter.z(cx, cy) - 4), height=hh * 4.0, r0=r * .07, r1=r * 1.3, drift=(r * 1.2, r * .4),
                       density=.12, glow=.35 if k < 3 else 0.0, speed=8.0 + k, seed=k) for k, (cx, cy, r, hh) in enumerate(V)]
    # boiling sea + steam
    sea = TR.ocean('sea', 900, (-420, 300, -6.5), wave=1.4, choppy=1.6, col='#1a2a26', murk='#3a3020', foam=True)
    steam = []
    # rubble + boulders everywhere
    TR.scatter(ter, ['namaqualand_boulder_02', 'namaqualand_boulder_04', 'namaqualand_boulder_05', 'rock_07', 'rock_09', 'boulder_01', 'moon_rock_03', 'moon_rock_06'],
               420, (-140, 140, 10, 260), seed=seed, scale=(.6, 2.6), slope_min=.6, zrange=(-2, 400), fallback=TR.fallback_rock)
    TR.scatter(ter, ['coast_rocks_02', 'coast_land_rocks_03'], 60, (-200, 200, 100, 500), seed=seed + 1, scale=(1.5, 3.0), slope_min=.6, sink=.4,
               fallback=TR.fallback_rock)
    TR.sun_light(200, 18, 5.0, (1, .66, .42))
    for k, (cx, cy, r, hh) in enumerate(V[:3]):                         # crater glow on the ash and slopes
        l = bpy.data.lights.new(f'craterlight{k}', 'POINT'); l.energy = 2.5e5; l.color = (1, .4, .1); l.shadow_soft_size = r * .2
        o = bpy.data.objects.new(f'craterlight{k}', l); TR.coll().objects.link(o); o.location = (cx, cy, ter.z(cx, cy) + 4)
    TR.fog(.0006, (1.0, .7, .5), .3, center=(0, 300, 0))
    return dict(ter=ter, sea=[sea], volcanoes=V, smoke=plumes + steam)


def young_earth_tick(w, t):
    TR.lava_tick(t); TR.ocean_tick(w['sea'], t)
    for u in w['smoke']: u(t)


# ------------------------------------------------------------------ the classroom
def uv_plane(name, w, h, loc, mat, facing=(0, -1)):
    import bmesh
    me = bpy.data.meshes.new(name); bm = bmesh.new(); uv = bm.loops.layers.uv.new('UVMap')
    vs = [bm.verts.new(p) for p in ((-w / 2, 0, -h / 2), (w / 2, 0, -h / 2), (w / 2, 0, h / 2), (-w / 2, 0, h / 2))]
    f = bm.faces.new(vs)
    for lp, (a, c) in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))): lp[uv].uv = (a, c)
    bm.to_mesh(me); bm.free(); me.materials.append(mat)
    o = bpy.data.objects.new(name, me); o.location = loc; o.rotation_euler = (0, 0, math.atan2(facing[0], -facing[1])); TR.coll().objects.link(o)
    return o


TREX = [(5, 20), (8, 16), (14, 14), (20, 12), (27, 13), (32, 17), (40, 20), (50, 21), (58, 20), (70, 22), (85, 26), (98, 31), (85, 30), (70, 30), (62, 32),
        (60, 38), (56, 46), (58, 52), (58, 57), (51, 59), (47, 58), (51, 52), (49, 43), (47, 35), (40, 33), (32, 31), (26, 28), (22, 24), (12, 24), (6, 23), (5, 20)]
TREX_ARM = [(31, 31), (28, 35), (25, 36), (26, 34)]
TREX_LEG2 = [(44, 33), (41, 41), (43, 49), (43, 57), (37, 58)]


def chalkboard_png(path, eye_closed=False, W=2400, H=1200, title='EVOLUTION OF LIFE ON EARTH', dino=True):
    """green board with chalk writing and a (too good) chalk T-rex; eye_closed draws the blink frame"""
    from PIL import Image, ImageDraw, ImageFilter
    import random as R
    import typo
    rr = R.Random(3)
    im = Image.new('RGB', (W, H), (34, 72, 52)); d = ImageDraw.Draw(im)
    for k in range(9000):                                    # board grain + old eraser smears
        x, y = rr.randrange(W), rr.randrange(H); c = 34 + rr.randrange(-6, 7)
        d.point((x, y), fill=(c, 72 + rr.randrange(-6, 7), 52 + rr.randrange(-5, 6)))
    for k in range(14):
        x, y = rr.randrange(W), rr.randrange(H); d.ellipse([x, y, x + rr.randrange(200, 600), y + rr.randrange(40, 120)], fill=(48, 86, 66))
    im = im.filter(ImageFilter.GaussianBlur(14)); d = ImageDraw.Draw(im)
    f = typo.font('patrickhand', 120) if 'patrickhand' in typo.FONTS else None
    def chalk_line(pts, w=9, col=(236, 236, 228)):
        for k in range(4):
            jit = [(x + rr.uniform(-2.5, 2.5), y + rr.uniform(-2.5, 2.5)) for x, y in pts]
            d.line(jit, fill=col, width=max(2, w - k * 2), joint='curve')
    d.text((W * .05, H * .06), title, font=f, fill=(238, 238, 230))
    chalk_line([(W * .05, H * .2), (W * .62, H * .2)], 6)
    if dino:
        ox, oy, s = W * .30, H * .26, 15.5
        P = lambda pts: [(ox + x * s, oy + y * s) for x, y in pts]
        chalk_line(P(TREX), 11); chalk_line(P(TREX_ARM), 9); chalk_line(P(TREX_LEG2), 9, (210, 214, 206))
        chalk_line(P([(7, 21), (11, 22), (13, 21), (15, 22), (17, 21), (19, 22), (21, 21)]), 6)        # teeth
        ex, ey = ox + 19 * s, oy + 15.3 * s
        if eye_closed: chalk_line([(ex - 26, ey), (ex - 8, ey + 6), (ex + 8, ey + 6), (ex + 26, ey)], 8)
        else:
            d.ellipse([ex - 24, ey - 20, ex + 24, ey + 20], outline=(240, 240, 232), width=8); d.ellipse([ex - 8, ey - 8, ex + 10, ey + 10], fill=(240, 240, 232))
        for k in range(26):                                  # scale texture strokes
            x, y = rr.uniform(35, 62), rr.uniform(22, 31); chalk_line(P([(x, y), (x + 1.2, y + .6)]), 4, (200, 204, 196))
    if not dino: im.save(path); return
    d.text((W * .70, H * .32), '4.54 bn yrs', font=typo.font('patrickhand', 80), fill=(236, 230, 160))
    d.text((W * .70, H * .45), '-> life?', font=typo.font('patrickhand', 80), fill=(236, 236, 228))
    im.save(path)


def classroom(seed=3):
    """sunny school classroom: front wall with a big green board (teacher's chalk T-rex), rows of desks, windows with sun
    shafts on the left, posters, clock, shelves of books, plants.  Students face +Y; board on y = 4.0"""
    import house as HS, hero as HR
    from house import put as hput
    world_sky('day', strength=1.0)
    Wd, D, Hh = 10.0, 9.0, 3.4; x0, x1, y0, y1 = -Wd / 2, Wd / 2, -D / 2 + .5, D / 2
    floor = TR.simple_mat('cls_floor', ('wood', 'floor', 'parquet'), '#8a6a48', 1.5)
    wallm = TR.simple_mat('cls_wall', ('plaster', 'painted'), '#e8dcc0', 1.0, tint='#f0e4c8')
    T.box('cls_floor', (Wd + .4, D + .4, .06), (0, (y0 + y1) / 2, -.03), floor)
    T.box('cls_ceiling', (Wd + .4, D + .4, .06), (0, (y0 + y1) / 2, Hh + .03), T.plain('clsceil', '#f2efe8', .9, emit='#f2efe8', strength=.25))
    HS.wall('cw_front', (x0, y1), (x1, y1), Hh, wallm); HS.wall('cw_back', (x0, y0), (x1, y0), Hh, wallm, holes=[(7.6, 8.6, 0, 2.2)])
    HS.wall('cw_left', (x0, y0), (x0, y1), Hh, wallm, holes=[(1.0, 2.6, .95, 2.6), (3.6, 5.2, .95, 2.6), (6.2, 7.8, .95, 2.6)])
    HS.wall('cw_right', (x1, y0), (x1, y1), Hh, wallm)
    for k, yy in enumerate((y0 + 1.8, y0 + 4.4, y0 + 7.0)):
        HS.window(f'cls_win{k}', (x0, yy, 1.78), 1.6, 1.6, (-1, 0), grill=False, light=None)
    # board
    import os
    os.makedirs('/tmp/evotex', exist_ok=True)
    chalkboard_png('/tmp/evotex/board_blank.png', False, title='', dino=False)
    chalkboard_png('/tmp/evotex/board_title.png', False, dino=False)
    chalkboard_png('/tmp/evotex/board_open.png', False); chalkboard_png('/tmp/evotex/board_closed.png', True)
    bm = bpy.data.materials.new('board'); bm.use_nodes = True; N, L = bm.node_tree.nodes, bm.node_tree.links; b = N['Principled BSDF']
    uvn = N.new('ShaderNodeTexCoord'); sx = N.new('ShaderNodeSeparateXYZ'); L.new(uvn.outputs['UV'], sx.inputs[0])
    def img(p_, nm):
        t_ = N.new('ShaderNodeTexImage'); t_.name = nm; t_.image = bpy.data.images.load(p_); L.new(uvn.outputs['UV'], t_.inputs['Vector']); return t_
    blank = img('/tmp/evotex/board_blank.png', 'blank'); title = img('/tmp/evotex/board_title.png', 'title'); full = img('/tmp/evotex/board_open.png', 'boardtex')
    def wipe(name, src_axis):                          # 0..1 value node -> chalk appears left to right
        v = N.new('ShaderNodeValue'); v.name = name; v.outputs[0].default_value = 1.0
        cmp = N.new('ShaderNodeMath'); cmp.operation = 'LESS_THAN'; L.new(src_axis, cmp.inputs[0]); L.new(v.outputs[0], cmp.inputs[1]); return cmp.outputs[0]
    m1 = N.new('ShaderNodeMix'); m1.data_type = 'RGBA'; L.new(wipe('reveal_title', sx.outputs['X']), m1.inputs['Factor']); L.new(blank.outputs[0], m1.inputs['A']); L.new(title.outputs[0], m1.inputs['B'])
    m2 = N.new('ShaderNodeMix'); m2.data_type = 'RGBA'; L.new(wipe('reveal_dino', sx.outputs['X']), m2.inputs['Factor']); L.new(m1.outputs['Result'], m2.inputs['A']); L.new(full.outputs[0], m2.inputs['B'])
    L.new(m2.outputs['Result'], b.inputs['Base Color']); b.inputs['Roughness'].default_value = .9
    tx = full
    board = uv_plane('board', 5.2, 2.2, (0, y1 - .09, 1.75), bm)
    T.box('board_frame', (5.4, .06, 2.4), (0, y1 - .05, 1.75), T.plain('boardframe', '#6a4a2a', .5))
    T.box('chalk_tray', (5.2, .14, .04), (0, y1 - .14, .64), T.plain('boardframe', '#6a4a2a', .5))
    # desks + chairs
    desks = []
    for r_ in range(4):
        for c_ in range(4):
            x = -3.3 + c_ * 2.2; y = -2.4 + r_ * 1.55
            if hput('SchoolDesk_01', (x, y, 0), 0, 1.0) is None: T.box(f'desk{r_}{c_}', (1.0, .55, .05), (x, y, .72), T.plain('deskw', '#b08050', .5))
            if hput('SchoolChair_01', (x, y - .55, 0), 180, 1.0) is None: T.box(f'chair{r_}{c_}', (.42, .42, .04), (x, y - .55, .44), T.plain('chairw', '#3a5a8a', .5))
            desks.append((x, y))
    hput('WoodenTable_02', (2.6, y1 - 1.6, 0), 90, 1.0); hput('wall_clock', (-2.9, y1 - .02, 2.85), 0, 1.0)
    hput('potted_plant_02', (x1 - .5, y1 - .5, 0), 30, 1.0); hput('potted_plant_02', (x0 + .5, y0 + .5, 0), 0, .9)
    hput('wooden_bookshelf_worn', (x1 - .35, 0.0, 0), -90, 1.0); hput('steel_frame_shelves_01', (x1 - .3, -2.6, 0), -90, 1.0)
    hput('book_encyclopedia_set_01', (2.5, y1 - 1.6, .76), 0, .25)
    for k, (txt, xx) in enumerate((('THE\nPERIODIC\nTABLE', -4.2), ('TREE\nOF\nLIFE', 4.2))):
        HS.poster(f'cls_poster{k}', txt, (xx, y1 - .07, 1.9), .9, 1.2, (0, -1), ['#f4f0e0', '#e8f0e0'][k], '#2a3a4a')
    # sunlight through the windows + soft fill
    TR.sun_light(-70, 28, 4.5, (1, .92, .8), .5)
    for k, (x, y) in enumerate(((-2.0, -1.0), (1.5, 1.5), (0, -3.0))):
        l = bpy.data.lights.new(f'clsfill{k}', 'AREA'); l.energy = 260; l.size = 2.5; l.color = (1, .95, .88)
        o = bpy.data.objects.new(f'clsfill{k}', l); TR.coll().objects.link(o); o.location = (x, y, Hh - .1)
    vol = T.box('cls_air', (Wd, D, Hh), (0, (y0 + y1) / 2, Hh / 2), None)       # dust in the air: sun shafts
    vm = bpy.data.materials.new('cls_air'); vm.use_nodes = True; N2 = vm.node_tree.nodes; N2.remove(N2['Principled BSDF'])
    sv = N2.new('ShaderNodeVolumeScatter'); sv.inputs['Density'].default_value = .012; vm.node_tree.links.new(sv.outputs[0], N2['Material Output'].inputs['Volume'])
    vol.data.materials.clear(); vol.data.materials.append(vm)
    return dict(board=board, boardtex=tx, desks=desks, y1=y1)


def board_blink(w, closed):
    w['boardtex'].image = bpy.data.images.load('/tmp/evotex/board_closed.png' if closed else '/tmp/evotex/board_open.png', check_existing=True)


def board_reveal(w, title=1.0, dino=1.0):
    N = w['board'].data.materials[0].node_tree.nodes
    N['reveal_title'].outputs[0].default_value = title; N['reveal_dino'].outputs[0].default_value = dino


# ------------------------------------------------------------------ prehistoric land: forests, plains, coasts
FOREST = {
    # kind: sky, sun(az, el, energy, color), ground layers, trees [(ids, n, heights)], plants [(kind, n)], understory ids, river, sea
    'permian': dict(sky='haze', sun=(140, 30, 3.5, (1, .9, .75)), ground=('forest ground', 'leaves'), gaid='forest_floor', gcol='#5a4a32', drygrass=False,
                    trees=[(['fir_tree_01'], 420, (14, 26)), (['dead_tree_trunk', 'dead_tree_trunk_02'], 20, (6, 12))],
                    plants=[('treefern', 60), ('horsetail', 140), ('cycad', 30)], under=['fern_02', 'moss_01', 'rock_moss_set_01'], river=True),
    'triassic': dict(sky='day', sun=(150, 40, 4.0, (1, .93, .82)), ground=('dry ground', 'dirt', 'sand'), gaid='red_dirt_mud_01', gcol='#9a6a48', drygrass=False,
                     trees=[(['fir_tree_01'], 220, (10, 22))], plants=[('cycad', 200), ('treefern', 90), ('horsetail', 160)],
                     under=['fern_02', 'shrub_03', 'namaqualand_boulder_02', 'rock_07'], river=True),
    'jurassic': dict(sky='day', sun=(160, 38, 4.2, (1, .94, .84)), ground=('forest ground', 'grass', 'moss'), gaid='forest_leaves_02', gcol='#4a5a2a', drygrass=False,
                     trees=[(['fir_tree_01'], 520, (18, 34))], plants=[('treefern', 220), ('cycad', 160), ('horsetail', 200)],
                     under=['fern_02', 'moss_01', 'rock_moss_set_02', 'root_cluster_01'], river=True),
    'cretaceous': dict(sky='day', sun=(170, 35, 4.2, (1, .94, .84)), ground=('forest ground', 'grass', 'leaves'), gaid='leafy_grass', gcol='#4a5a2a', drygrass=False,
                       trees=[(['island_tree_01', 'tree_small_02'], 380, (10, 24)), (['fir_tree_01'], 200, (18, 30))],
                       plants=[('cycad', 50), ('treefern', 50)], under=['fern_02', 'shrub_01', 'shrub_02', 'shrub_03', 'grass_medium_01', 'periwinkle_plant'], river=True),
    'paleogene': dict(sky='day', sun=(180, 42, 4.0, (1, .95, .86)), ground=('forest ground', 'leaves', 'grass'), gaid='grass_ground', gcol='#4a5a2a', drygrass=False,
                      trees=[(['island_tree_02', 'tree_small_02'], 480, (10, 26)), (['fir_tree_01'], 80, (16, 26))],
                      plants=[('treefern', 20)], under=['fern_02', 'shrub_01', 'shrub_02', 'shrub_03', 'nettle_plant', 'periwinkle_plant', 'grass_medium_01'], river=True),
    'savanna': dict(sky='golden', sun=(200, 28, 4.5, (1, .86, .66)), ground=('dry grass', 'dry ground', 'savanna'), gaid='dry_ground_01', gcol='#a89058', drygrass=True,
                    trees=[(['quiver_tree_01', 'island_tree_02', 'tree_small_02'], 30, (6, 11))], plants=[],
                    under=['grass_medium_02', 'grass_medium_01', 'wild_rooibos_bush', 'searsia_burchellii', 'namaqualand_boulder_04', 'dry_branches_medium_01'], river=False),
}


def forest(kind='jurassic', seed=2, focus=(0, 60), clear=()):
    """a full prehistoric landscape: rolling hills with a river, dense forest around a clearing (focus), mountains on the
    horizon fading into haze, birds/insects added by shots.  clear = [(x, y, r)] kept open for the action"""
    K = FOREST[kind]
    world_sky(K['sky'], strength=1.0)
    fx, fy = focus
    def h(x, y):
        z = TR.fbm(x, y, .006, 5, seed) * 18 + TR.fbm(x, y, .03, 4, seed + 1) * 2.0
        rv = abs((x - fx) - 40 * math.sin((y - fy) * .012)) if K['river'] else 1e9           # a river meandering through the valley
        z -= 4.5 * math.exp(-(rv / 14) ** 2)
        d = math.hypot(x - fx, y - fy); z = z * min(1.0, .35 + d / 260)                     # flatter near the action
        far = max(0.0, math.hypot(x - fx, y - fy) - 700); z += (TR.ridged(x, y, .0025, 5, seed + 3) * 240 + 60) * TR.smooth01(far / 900)   # mountains far away
        return z
    gk = K['ground']
    ground = TR.blend_mat('ground_' + kind, TR.layer(gk, K['gcol'], 3.0, tint=None, aid=K.get('gaid')),
                          [(TR.layer(('grass',), '#4a6a2a', 3.0, aid='sparse_grass' if kind == 'savanna' else 'leafy_grass'), dict(noise=.02)),
                           (TR.layer(('rock', 'cliff'), '#6a6458', 8.0, aid='rock_pitted_mossy' if kind not in ('savanna', 'triassic') else 'dry_riverbed_rock'), dict(slope=(.85, .7), noise=.03)),
                           (TR.layer(('mud', 'wet ground', 'dirt'), '#4a3a2a', 3.0, aid='brown_mud_leaves_01'), dict(height=(-1.5, -3.0), noise=.1)),
                           (TR.layer(('snow',), '#e8ecf0', 6.0), dict(height=(250, 300), noise=.004))], bump=.4)
    ter = TR.Terrain('ground', h, 5200.0, 360, ground, center=(fx, fy), inner=(420, 300))
    if K['river']:
        river = TR.ocean('river', 1600, (fx, fy, -2.6), wave=.08, choppy=.2, res=10, col='#2a3a30', murk='#2a3020', foam=False)
    avoid = [(fx, fy, 28)] + list(clear)
    edge = lambda x, y: TR.smooth01((math.hypot(x - fx, y - fy) - 30) / 60)                # forest thickens away from the clearing
    for ids, n, hh in ([] if os.environ.get('NOTREES') else K['trees']):
        TR.scatter_h(ter, ids, n, (fx - 420, fx + 420, fy - 160, fy + 620), hh, seed=seed, avoid=avoid, slope_min=.78, zrange=(-1.0, 250),
                     density_fn=lambda x, y: .25 + .75 * edge(x, y), fallback=TR.fallback_tree)
    for pk, n in K['plants']:
        TR.scatter_plants(ter, pk, n, (fx - 160, fx + 160, fy - 60, fy + 260), seed=seed + 5, avoid=[(fx, fy, 16)] + list(clear), zrange=(-1.0, 200))
    if not os.environ.get('NOUNDER'): TR.scatter(ter, K['under'], 2600, (fx - 160, fx + 160, fy - 70, fy + 260), seed=seed + 7, scale=(.8, 1.8), avoid=[(fx, fy, 16)] + list(clear),
               slope_min=.75, zrange=(-1.2, 200), fallback=TR.fallback_fern)
    TR.scatter(ter, ['namaqualand_boulder_02', 'namaqualand_boulder_05', 'rock_07', 'boulder_01'], 60, (fx - 200, fx + 200, fy - 80, fy + 300), seed=seed + 9,
               scale=(.6, 2.2), slope_min=.6, fallback=TR.fallback_rock, avoid=[(fx, fy, 14)] + list(clear))
    az, el, en, sc_ = K['sun']; sun = TR.sun_light(az, el, en * .5, sc_)        # the sky HDRI already carries a sun: keep the key from blowing out
    bpy.context.scene.view_settings.exposure = -.45
    TR.fog(.00006 if kind != 'savanna' else .00005, (.85, .9, 1.0) if kind != 'savanna' else (1, .9, .75), .4, size=(8000, 8000, 900), center=(fx, fy, -50))
    if not os.environ.get('NOWIND'): TR.wind_setup(.05)
    return dict(ter=ter, focus=Vector((fx, fy, h(fx, fy))), kind=kind, sea=[river] if K['river'] else [])


def forest_tick(w, t):
    TR.wind_tick(t)
    if w.get('sea'): TR.ocean_tick(w['sea'], t)


def _forest_world(kind):
    def f(): return forest(kind)
    return f


permian = _forest_world('permian'); triassic = _forest_world('triassic'); jurassic = _forest_world('jurassic')
cretaceous = _forest_world('cretaceous'); paleogene = _forest_world('paleogene'); savanna = _forest_world('savanna')
permian_tick = triassic_tick = jurassic_tick = cretaceous_tick = paleogene_tick = savanna_tick = forest_tick


# ------------------------------------------------------------------ underwater
def seafloor(kind='cambrian', seed=4):
    """ancient sea floor: sand + rock terrain, water volume with sun shafts and caustics, the wavy surface overhead,
    sponges / algae / stromatolites by era, drifting marine snow"""
    world_sky('day', strength=.6, tint=(.5, .8, .9))
    def h(x, y): return TR.fbm(x, y, .03, 5, seed) * 2.5 + TR.ridged(x, y, .06, 3, seed) * .8 - 18
    base = TR.layer(('sand', 'beach'), '#c8b896', 2.0, tint='#b8d0c8', aid='coast_sand_01')
    rules = [(TR.layer(('rock', 'mossy'), '#5a6458', 3.0, tint='#7a9a88'), dict(slope=(.9, .75), noise=.15))]
    m = TR.blend_mat('seafloor_' + kind, base, rules, bump=.5)
    nd = m.node_tree.nodes; b = nd['Principled BSDF']                                   # animated caustics added as emission ripples
    tc = nd.new('ShaderNodeTexCoord'); mp = nd.new('ShaderNodeMapping'); mp.name = 'caustic_flow'; m.node_tree.links.new(tc.outputs['Object'], mp.inputs['Vector'])
    vo = nd.new('ShaderNodeTexVoronoi'); vo.feature = 'SMOOTH_F1' if hasattr(vo, 'feature') else vo.feature; vo.voronoi_dimensions = '4D'; vo.name = 'caustic'
    vo.inputs['Scale'].default_value = .9; m.node_tree.links.new(mp.outputs['Vector'], vo.inputs['Vector'])
    cp = nd.new('ShaderNodeMath'); cp.operation = 'POWER'; m.node_tree.links.new(vo.outputs['Distance'], cp.inputs[0]); cp.inputs[1].default_value = 4.0
    cm = nd.new('ShaderNodeMath'); cm.operation = 'MULTIPLY'; m.node_tree.links.new(cp.outputs[0], cm.inputs[0]); cm.inputs[1].default_value = 1.6
    m.node_tree.links.new(cm.outputs[0], b.inputs['Emission Strength']); b.inputs['Emission Color'].default_value = (.55, .85, .9, 1)
    ter = TR.Terrain('seabed', h, 900.0, 240, m, center=(0, 60), inner=(160, 220))
    water = T.box('water', (900, 900, 18.5), (0, 60, -9.25), None)
    wm = bpy.data.materials.new('water_vol'); wm.use_nodes = True; N = wm.node_tree.nodes; N.remove(N['Principled BSDF'])
    pv = N.new('ShaderNodeVolumePrincipled'); pv.inputs['Color'].default_value = (.45, .85, .9, 1); pv.inputs['Density'].default_value = .018
    pv.inputs['Absorption Color'].default_value = (.55, .85, .9, 1); pv.inputs['Anisotropy'].default_value = .6
    wm.node_tree.links.new(pv.outputs[0], N['Material Output'].inputs['Volume']); water.data.materials.clear(); water.data.materials.append(wm)
    surf = TR.ocean('surface', 900, (0, 60, -.1), wave=.5, choppy=.6, res=10, col='#8ac8d0', murk='#8ac8d0', foam=False)
    for m_ in surf.data.materials:
        vn = [n for n in m_.node_tree.nodes if n.type == 'VOLUME_ABSORPTION']
        for n in vn: m_.node_tree.nodes.remove(n)
    TR.sun_light(160, 65, 12.0, (.95, 1, 1), 1.5); bpy.context.scene.view_settings.exposure = .8
    r = random.Random(seed)
    life = []
    if kind in ('cambrian', 'devonian_sea', 'ediacaran'):
        import creatures as CR
        smats = [CR.pmat(f'sponge{c}', c, .85, sss=.3) for c in ('#d8903a', '#e0b84a', '#c86a4a', '#b8a070')]
        for m_ in smats:                                   # porous surface: voronoi pits in the bump
            N_, L_ = m_.node_tree.nodes, m_.node_tree.links; vo = N_.new('ShaderNodeTexVoronoi'); vo.inputs['Scale'].default_value = 40
            bp = N_.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = .6; L_.new(vo.outputs['Distance'], bp.inputs['Height'])
            L_.new(bp.outputs['Normal'], N_['Principled BSDF'].inputs['Normal'])
        for k in range(160 if kind != 'ediacaran' else 40):
            x, y = r.uniform(-60, 60), r.uniform(0, 160); z = ter.z(x, y)
            for j in range(r.randint(1, 4)):                # vase / tube sponges: open, flaring tops, slightly wobbly
                hh = r.uniform(.3, 1.6); rr = r.uniform(.06, .22); fl = r.uniform(1.0, 1.8)
                prof = [(rr * .6, 0), (rr, hh * .25), (rr * (1 + (fl - 1) * .5), hh * .6), (rr * fl, hh), (rr * fl * .82, hh * .98), (rr * .7, hh * .55), (rr * .5, hh * .2)]
                o = lib.lathe(f'sponge{k}_{j}', prof, seg=14, m=r.choice(smats)); o.location = (x + r.uniform(-.4, .4), y + r.uniform(-.4, .4), z - .03)
                o.rotation_euler = (r.uniform(-.25, .25), r.uniform(-.25, .25), r.uniform(0, 6.3))
        alg = TR.simple_mat('algae', ('leaves', 'grass'), '#3a6a3a', .2, tint='#4a8a4a')
        for k in range(220):
            x, y = r.uniform(-60, 60), r.uniform(-10, 170); z = ter.z(x, y); hh = r.uniform(.8, 3.5)
            pts = [Vector((x, y, z)) + Vector((math.sin(j * .9 + k) * .15 * j / 6, 0, hh * j / 6)) for j in range(7)]
            o = T.lib.tube(f'algae{k}', pts, .03, m=alg)
            wv = o.modifiers.new('sway', 'WAVE') if o.type == 'MESH' else None
        if kind == 'ediacaran':
            import creatures as CR
            for k, (hx, hy, hs) in enumerate([(0, 15, 1.6), (1.6, 16.6, 1.1), (-1.7, 14.2, .8)]):     # hero Dickinsonia for the close-up
                d = CR.dickinsonia(f'dickhero{k}', hs); d.location = (hx, hy, ter.z(hx, hy) + .08); d.rotation_euler = (0, 0, k * 1.7)
            for k in range(40):
                x, y = r.uniform(-25, 25), r.uniform(10, 80); z = ter.z(x, y)
                if abs(x) < 7 and y < 24: x += 14 if x >= 0 else -14            # keep the camera's glide path open
                d = CR.dickinsonia(f'dick{k}', r.uniform(.3, 1.2)); d.location = (x, y, z + .03); d.rotation_euler = (0, 0, r.uniform(0, 6.3))
                f = CR.charnia(f'charnia{k}', r.uniform(.6, 1.6)); f.location = (x + 2, y + 1, z); life.append(f)
    if kind == 'shallows':
        import creatures as CR
        CR.stromatolite_field(ter, 180, (-60, 60, 0, 160), seed)
    TR.scatter(ter, ['coast_rocks_01', 'coast_rocks_02', 'rock_07', 'rock_09', 'namaqualand_boulder_04'], 120, (-80, 80, -10, 200), seed=seed,
               scale=(.6, 2.5), slope_min=.5, fallback=TR.fallback_rock)
    snow = [TR.smoke_column(f'snow{k}', (r.uniform(-30, 30), r.uniform(10, 120), -18), rate=1.0, life=20, rise=.6, r0=.05, r1=.12, wind=(.2, .1),
                            turb=3.0, col=(.9, .95, .95), density=.0, voxel=.2, seed=k) for k in range(0)]
    return dict(ter=ter, sea=[surf], life=life, z0=-18)


def seafloor_tick(w, t):
    TR.ocean_tick(w['sea'], t)
    for m in bpy.data.materials:
        if m.name.startswith('seafloor_') and m.node_tree:
            n = m.node_tree.nodes.get('caustic')
            if n: n.inputs['W'].default_value = t * .35
    for k, f in enumerate(w.get('life', [])): f.rotation_euler = (math.sin(t * .8 + k) * .08, math.cos(t * .6 + k) * .06, f.rotation_euler.z)


def cambrian(): return seafloor('cambrian')
def devonian_sea(): return seafloor('devonian_sea', 6)
def ediacaran(): return seafloor('ediacaran', 7)
def shallows():
    w = seafloor('shallows', 8)
    return w
cambrian_tick = devonian_sea_tick = ediacaran_tick = shallows_tick = seafloor_tick


def microbes(seed=5):
    """the microscopic world: deep blue-green water, drifting bacteria and cocci, out-of-focus particles everywhere"""
    import creatures as CR
    lib.world_color('#04141a', 1.0)
    r = random.Random(seed); out = []
    for k in range(70):
        kind = r.choice(['rod', 'rod', 'coccus', 'chain'])
        m = CR.microbe(f'mic{k}', kind, r.uniform(.15, .45), r.choice(['#7ac8a0', '#9ad0b8', '#c8b07a', '#a8c86a']), k)
        m.location = (r.uniform(-6, 6), r.uniform(0, 14), r.uniform(-3, 3)); m.rotation_euler = (r.uniform(0, 6.3), r.uniform(0, 6.3), r.uniform(0, 6.3))
        out.append((m, Vector(m.location), Vector((r.uniform(-.2, .2), r.uniform(-.15, .15), r.uniform(-.1, .1))), r.uniform(0, 6.3)))
    dust = TR.simple_mat('motes', ('',), '#cfeee8', .2)
    for k in range(500):
        o = T.lib.sphere(f'mote{k}', r.uniform(.005, .03), (r.uniform(-8, 8), r.uniform(-2, 20), r.uniform(-5, 5)), dust, seg=6, rings=4)
    l1 = bpy.data.lights.new('micro_key', 'AREA'); l1.energy = 900; l1.size = 8; l1.color = (.7, 1, .95)
    o1 = bpy.data.objects.new('micro_key', l1); TR.coll().objects.link(o1); o1.location = (0, 6, 9); o1.rotation_euler = (0, 0, 0)
    l2 = bpy.data.lights.new('micro_rim', 'AREA'); l2.energy = 600; l2.size = 6; l2.color = (.4, .7, 1)
    o2 = bpy.data.objects.new('micro_rim', l2); TR.coll().objects.link(o2); o2.location = (0, 20, 0); o2.rotation_euler = (math.radians(90), 0, math.pi)
    vol = T.box('micro_water', (40, 40, 20), (0, 8, 0), None)
    wm = bpy.data.materials.new('micro_vol'); wm.use_nodes = True; N = wm.node_tree.nodes; N.remove(N['Principled BSDF'])
    sv = N.new('ShaderNodeVolumeScatter'); sv.inputs['Density'].default_value = .02; sv.inputs['Color'].default_value = (.5, .9, .85, 1)
    wm.node_tree.links.new(sv.outputs[0], N['Material Output'].inputs['Volume']); vol.data.materials.clear(); vol.data.materials.append(wm)
    return dict(cells=out)


def microbes_tick(w, t):
    for m, p0, v, ph in w['cells']:
        m.location = p0 + v * t + Vector((math.sin(t * .7 + ph) * .15, math.cos(t * .5 + ph) * .1, math.sin(t * .9 + ph) * .12))
        m.rotation_euler = (m.rotation_euler.x, m.rotation_euler.y, ph + t * .2)


def black():
    lib.world_color('#000000', 0.0)
    return {}


# ------------------------------------------------------------------ coasts
def coast(seed=11):
    """Devonian shoreline: rocky beach, tide pools, the first plants (mosses, horsetails, low ferns) creeping inland, no trees"""
    world_sky('day', 1.0)
    def h(x, y): return TR.fbm(x, y, .01, 5, seed) * 6 + (y - 40) * .08 + TR.ridged(x, y, .03, 3, seed) * 1.2
    m = TR.blend_mat('coast', TR.layer(('sand', 'beach'), '#b8a888', 2.5),
                     [(TR.layer(('rock', 'cliff'), '#5a5650', 4.0), dict(slope=(.9, .75), noise=.08)),
                      (TR.layer(('moss', 'grass'), '#4a6a2a', 2.0), dict(height=(1.5, 3.0), noise=.12))], bump=.5)
    ter = TR.Terrain('coast', h, 2400.0, 300, m, center=(0, 60), inner=(240, 240))
    sea = TR.ocean('sea', 2400, (0, -200, -.2), wave=.9, choppy=1.0, res=11, col='#4a8a90', murk='#3a7a78', foam=True)
    TR.scatter(ter, ['coast_rocks_01', 'coast_rocks_02', 'coast_rocks_03', 'coast_land_rocks_02', 'coast_land_rocks_03', 'namaqualand_boulder_02'], 220,
               (-120, 120, -30, 120), seed=seed, scale=(.6, 2.8), slope_min=.4, fallback=TR.fallback_rock)
    TR.scatter_plants(ter, 'horsetail', 260, (-100, 100, 15, 160), seed=seed, zrange=(1.2, 80))
    TR.scatter(ter, ['moss_01', 'fern_02', 'rock_moss_set_01'], 400, (-110, 110, 10, 170), seed=seed + 2, scale=(.6, 1.2), zrange=(1.0, 80), fallback=TR.fallback_fern)
    TR.scatter(ter, ['coastal_cliff_01', 'coastal_cliff_02', 'coastal_cliff_04'], 10, (-400, 400, 200, 600), seed=seed + 3, scale=(3, 6), slope_min=0, fallback=TR.fallback_rock)
    TR.sun_light(150, 35, 4.0); TR.fog(.0003, (.85, .92, 1.0), .4, size=(6000, 6000, 600))
    TR.wind_setup(.05)
    return dict(ter=ter, sea=[sea])


def coast_cretaceous(seed=12):
    w = coast(seed)
    T.box('cliffs_far', (1, 1, 1), (0, 0, -100), None)
    return w


coast_tick = coast_cretaceous_tick = forest_tick


# ------------------------------------------------------------------ the asteroid
def impact(seed=13):
    """end of the Cretaceous: the same forest; a burning asteroid, the impact fireball on the horizon, the shockwave, a wall of
    dust, fires, darkness.  Shots drive it with impact_tick(w, t) + w['phase'] (0 = peaceful, 1 = entry, 2 = impact, 3 = aftermath)"""
    w = forest('cretaceous', seed)
    fx, fy = w['focus'].x, w['focus'].y
    ast_m = TR.simple_mat('asteroid', ('rock',), '#3a3632', 2.0).copy(); ast_m.name = 'asteroid_hot'
    ab = ast_m.node_tree.nodes['Principled BSDF']; ab.inputs['Emission Color'].default_value = (1, .5, .15, 1); ab.inputs['Emission Strength'].default_value = 25
    ast = T.lib.sphere('asteroid', 60, (0, 0, -9000), ast_m, seg=32, rings=16)
    d = ast.modifiers.new('d', 'DISPLACE'); tx = bpy.data.textures.new('asttx', 'CLOUDS'); tx.noise_scale = .4; d.texture = tx; d.strength = 25
    trail = TR.smoke_column('ast_trail', (0, 0, -9000), rate=12, life=4, rise=0, r0=40, r1=160, wind=(0, 0), turb=30, col=(.4, .3, .25), density=.02, glow=8, voxel=12, seed=3)
    fire_m = bpy.data.materials.new('fireball'); fire_m.use_nodes = True; N = fire_m.node_tree.nodes; N.remove(N['Principled BSDF'])
    pv = N.new('ShaderNodeVolumePrincipled'); pv.inputs['Density'].default_value = .006; pv.inputs['Emission Strength'].default_value = 1.2; pv.inputs['Emission Color'].default_value = (1, .38, .08, 1)
    fire_m.node_tree.links.new(pv.outputs[0], N['Material Output'].inputs['Volume'])
    fb = T.lib.sphere('fireball', 1, (fx + 200, fy + 3200, 0), fire_m, seg=24, rings=12)
    dust = TR.smoke_column('dustwall', (fx + 200, fy + 2600, 0), rate=10, life=20, rise=30, r0=200, r1=900, wind=(0, -60), turb=200, col=(.25, .2, .17), density=.0015, voxel=40, seed=5)
    flash = bpy.data.lights.new('flash', 'SUN'); flash.energy = 0; flash.color = (1, .85, .7); fo = bpy.data.objects.new('flash', flash); bpy.context.scene.collection.objects.link(fo)
    fo.rotation_euler = (math.radians(80), 0, math.radians(180))
    fires = [TR.smoke_column(f'fire{k}', (fx + x, fy + y, w['ter'].z(fx + x, fy + y)), rate=4, life=6, rise=6, r0=3, r1=14, wind=(4, -2), turb=4, col=(.06, .05, .05),
                             density=.06, glow=12, voxel=1.2, seed=20 + k) for k, (x, y) in enumerate([(-60, 140), (40, 200), (90, 120), (-120, 260)])]
    r0 = max(v.co.length for v in fb.data.vertices)
    w.update(dict(ast=ast, trail=trail, fireball=fb, fb_r0=r0, dust=dust, flash=fo, fires=fires, ifocus=(fx, fy)))
    return w


def impact_tick(w, t, phase=None):
    """phase(t) from the shot: dict(entry=0..1, boom=0..1 (seconds since impact / 10), burn=0..1)"""
    forest_tick(w, t)
    ph = w.get('phase_fn', lambda t: dict(entry=0, boom=0, burn=0))(t)
    fx, fy = w['ifocus']
    e = ph.get('entry', 0); s = Vector((fx - 4000, fy + 9000, 9000)); g = Vector((fx + 200, fy + 3200, 0))
    w['ast'].location = s.lerp(g, min(1, e)) if 0 < e < 1 else (0, 0, -9000)
    w['trail'](t) if 0 < e < 1 else None
    b = ph.get('boom', 0)
    k_ = 1.0 / w.get('fb_r0', 1.0); w['fireball'].scale = ((1 + 900 * b) * k_,) * 2 + ((1 + 600 * b) * k_,) if b > 0 else (.0001,) * 3   # metres
    w['flash'].data.energy = 60 * max(0.0, 1 - b * 6) if b > 0 else 0
    if b > 0: w['dust'](t)
    for f in w['fires']: f(t) if ph.get('burn', 0) > 0 else None


# ------------------------------------------------------------------ cave
def _cave_painting(path):
    from PIL import Image, ImageDraw, ImageFilter
    import random as R
    r = R.Random(4); W_, H_ = 2048, 1024
    im = Image.new('RGBA', (W_, H_), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    def beast(ox, oy, s, col):                     # bison/aurochs silhouette in ochre
        body = [(0, 20), (10, 8), (30, 4), (52, 6), (66, 12), (70, 24), (66, 36), (60, 38), (58, 52), (54, 52), (52, 40), (24, 40), (22, 54), (18, 54), (16, 40),
                (8, 36), (2, 30)]
        d.polygon([(ox + x * s, oy + y * s) for x, y in body], fill=col)
        d.line([(ox + 6 * s, oy + 10 * s), (ox + 2 * s, oy + 2 * s), (ox + 8 * s, oy + 4 * s)], fill=col, width=int(2 * s))
    for k in range(9):
        beast(r.uniform(60, 1800), r.uniform(80, 700), r.uniform(2.4, 4.2), (r.choice([150, 120, 90]), r.choice([60, 40, 30]), 20, r.choice([200, 170, 140])))
    for k in range(14):
        x, y = r.uniform(80, 1950), r.uniform(60, 960)
        d.ellipse([x, y, x + 50, y + 70], fill=(140, 40, 20, 120)); d.polygon([(x + 20, y + 70), (x + 30, y + 130), (x + 10, y + 130)], fill=(140, 40, 20, 90))
    im = im.filter(ImageFilter.GaussianBlur(1.6)); im.save(path)


def cave(seed=14):
    """a limestone cave: rock walls closing in, a fire on the floor lighting painted animals, the bright mouth of the cave
    opening on the savanna"""
    world_sky('golden', 1.2)
    rock = TR.blend_mat('cave_rock', TR.layer(('rock', 'cave', 'limestone'), '#8a7a68', 3.0, tint='#b8a088'),
                        [(TR.layer(('rock', 'wet'), '#5a5048', 2.0), dict(slope=(.3, .9), noise=.2))], bump=1.0)
    import bmesh
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=96, v_segments=48, radius=1.0)
    for v in bm.verts:
        p = v.co.copy(); n = TR.fbm(p.x * 4, p.y * 4 + p.z * 2, 1.0, 5, seed) * .22
        v.co = Vector((p.x * 9, p.y * 14, max(-.15, p.z) * 5)) * (1 + n)
    me = bpy.data.meshes.new('cave'); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    me.flip_normals() if hasattr(me, 'flip_normals') else None
    me.materials.append(rock); o = bpy.data.objects.new('cave', me); TR.coll().objects.link(o); o.location = (0, 8, 0)
    hole = T.lib.sphere('cave_mouth_cut', 4.5, (0, -6.5, 2.0), None, seg=24, rings=12)
    bo = o.modifiers.new('mouth', 'BOOLEAN'); bo.object = hole; bo.operation = 'DIFFERENCE'; hole.hide_render = True; hole.hide_viewport = True
    floor = TR.simple_mat('cave_floor', ('dirt', 'ground'), '#6a5a48', 1.5); T.box('cave_floor', (24, 34, .1), (0, 8, -.05), floor)
    import os; os.makedirs('/tmp/evotex', exist_ok=True); _cave_painting('/tmp/evotex/cavepaint.png')
    pm = bpy.data.materials.new('cavepaint'); pm.use_nodes = True; pm.blend_method = 'BLEND' if hasattr(pm, 'blend_method') else None
    N, L = pm.node_tree.nodes, pm.node_tree.links; tx = N.new('ShaderNodeTexImage'); tx.image = bpy.data.images.load('/tmp/evotex/cavepaint.png')
    b = N['Principled BSDF']; L.new(tx.outputs['Color'], b.inputs['Base Color']); L.new(tx.outputs['Alpha'], b.inputs['Alpha']); b.inputs['Roughness'].default_value = .9
    pl = uv_plane('cave_paint', 9, 4.5, (0, 19.6, 2.6), pm, facing=(0, -1))
    fire_root = Vector((1.5, 9.0, 0))
    for k in range(10):
        a = k * math.tau / 10; T.lib.sphere(f'firestone{k}', .22, (fire_root.x + math.cos(a) * .6, fire_root.y + math.sin(a) * .6, .1), TR.simple_mat('stones', ('rock',), '#5a5650', .5), seg=10, rings=6)
    for k in range(6):
        T.cyl(f'firelog{k}', .07, 1.1, (fire_root.x, fire_root.y, .15), TR.simple_mat('charwood', ('bark',), '#2a1a10', .5), rot=(math.pi / 2, 0, k * .52), v=8)
    flame = TR.plume('flame', tuple(fire_root + Vector((0, 0, .05))), height=1.3, r0=.28, r1=.12, drift=(.05, 0), col=(.05, .03, .02), density=6.0, glow=18.0,
                     speed=1.8, seed=3, glow_h=1.0)
    smoke = TR.smoke_column('firesmoke', tuple(fire_root + Vector((0, 0, 1.2))), rate=3, life=8, rise=.8, r0=.3, r1=2.0, wind=(0, -.6), turb=.6, col=(.2, .19, .18),
                            density=.015, voxel=.2, seed=4)
    fl = bpy.data.lights.new('firelight', 'POINT'); fl.energy = 2600; fl.color = (1, .55, .2); fl.shadow_soft_size = .4
    flo = bpy.data.objects.new('firelight', fl); TR.coll().objects.link(flo); flo.location = fire_root + Vector((0, 0, .8))
    TR.sun_light(180, 22, 4.0, (1, .86, .66))
    return dict(fire=fire_root, flame=flame, smoke=smoke, light=flo)


def cave_tick(w, t):
    w['flame'](t); w['smoke'](t)
    w['light'].data.energy = 2600 * (1 + .18 * math.sin(t * 17) + .12 * math.sin(t * 29 + 1))


# ------------------------------------------------------------------ Earth from space, the living room, the modern city
def space(seed=15):
    """Earth from orbit: NASA Blue Marble surface + clouds + thin atmosphere glow, stars, the Sun"""
    import os
    lib.world_color('#000000', 0)
    w = bpy.context.scene.world; N, L = w.node_tree.nodes, w.node_tree.links
    vo = N.new('ShaderNodeTexVoronoi'); vo.inputs['Scale'].default_value = 900; cp = N.new('ShaderNodeMath'); cp.operation = 'LESS_THAN'
    L.new(vo.outputs['Distance'], cp.inputs[0]); cp.inputs[1].default_value = .025; mul = N.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; L.new(cp.outputs[0], mul.inputs[0]); mul.inputs[1].default_value = 2.0
    L.new(mul.outputs[0], N['Background'].inputs['Strength'])
    tex = '/tmp/evotex/earth.jpg'; clouds = '/tmp/evotex/clouds.jpg'; os.makedirs('/tmp/evotex', exist_ok=True)
    TJ = 'https://raw.githubusercontent.com/mrdoob/three.js/r160/examples/textures/planets/'
    for path, urls in ((tex, ['https://eoimages.gsfc.nasa.gov/images/imagerecords/73000/73909/world.topo.bathy.200412.3x5400x2700.jpg',
                              'https://upload.wikimedia.org/wikipedia/commons/c/cd/Land_ocean_ice_2048.jpg', TJ + 'earth_atmos_2048.jpg']),
                       (clouds, ['https://eoimages.gsfc.nasa.gov/images/imagerecords/57000/57747/cloud_combined_2048.jpg', TJ + 'earth_clouds_1024.png'])):
        for url in urls:                            # NASA Blue Marble imagery (public domain), mirrors tried in order
            if (os.path.exists(path) and os.path.getsize(path) > 1000) or not TR.PH: break
            try: lib._dl(url, path); lib.log('earth tex', url)
            except Exception as e: lib.log('earth tex fail', url, e)
            if os.path.exists(path) and os.path.getsize(path) < 1000: os.remove(path)
    em = bpy.data.materials.new('earth'); em.use_nodes = True; N2, L2 = em.node_tree.nodes, em.node_tree.links; b = N2['Principled BSDF']
    if os.path.exists(tex):
        t1 = N2.new('ShaderNodeTexImage'); t1.image = bpy.data.images.load(tex); L2.new(t1.outputs[0], b.inputs['Base Color'])
    else: b.inputs['Base Color'].default_value = (.08, .2, .45, 1)
    b.inputs['Roughness'].default_value = .6
    earth = T.lib.sphere('earth', 6.371, (0, 0, 0), em, seg=128, rings=64)
    cm = bpy.data.materials.new('clouds'); cm.use_nodes = True; N3, L3 = cm.node_tree.nodes, cm.node_tree.links; b3 = N3['Principled BSDF']
    if os.path.exists(clouds):
        t2 = N3.new('ShaderNodeTexImage'); t2.image = bpy.data.images.load(clouds); L3.new(t2.outputs['Alpha' if t2.image.depth in (32, 128) and t2.image.channels == 4 else 'Color'], b3.inputs['Alpha']); b3.inputs['Base Color'].default_value = (1, 1, 1, 1)
    else:
        nz = N3.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 6; nz.inputs['Detail'].default_value = 12
        mr = N3.new('ShaderNodeMapRange'); L3.new(nz.outputs['Fac'], mr.inputs[0]); mr.inputs[1].default_value = .5; mr.inputs[2].default_value = .7; L3.new(mr.outputs[0], b3.inputs['Alpha'])
    cl = T.lib.sphere('clouds', 6.41, (0, 0, 0), cm, seg=128, rings=64)
    am = bpy.data.materials.new('atmo'); am.use_nodes = True; N4 = am.node_tree.nodes; N4.remove(N4['Principled BSDF'])
    sv = N4.new('ShaderNodeVolumeScatter'); sv.inputs['Density'].default_value = 1.2; sv.inputs['Color'].default_value = (.3, .55, 1, 1)
    am.node_tree.links.new(sv.outputs[0], N4['Material Output'].inputs['Volume']); atmo = T.lib.sphere('atmo', 6.52, (0, 0, 0), am, seg=96, rings=48)
    TR.sun_light(60, 10, 5.0, (1, .98, .95), .5)
    return dict(earth=earth, clouds=cl)


def space_tick(w, t):
    w['earth'].rotation_euler = (math.radians(23.4), 0, t * .02); w['clouds'].rotation_euler = (math.radians(23.4), 0, t * .024)


def livingroom():
    import house as HS
    world_sky('day', 1.0)
    out = HS.interior(False)
    for f in out['fans']: pass
    return dict(fans=out['fans'])


def livingroom_tick(w, t):
    for k, f in enumerate(w['fans']): f.rotation_euler = (0, 0, t * 9 + k)


def city():
    import city as C
    world_sky('day', 1.0)
    C.build(boarded=False, night=False, mood='day')
    return {}
