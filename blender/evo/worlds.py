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
    world_sky('sunset', strength=1.6, tint=(1.0, .7, .5)); bpy.context.scene.view_settings.exposure = .3
    V = [(0, 260, 70, 95), (-170, 330, 85, 120), (190, 300, 70, 100), (-90, 520, 120, 160), (120, 560, 140, 190)]
    def h(x, y):
        z = TR.fbm(x, y, .012, 6, seed) * 9 + TR.ridged(x, y, .02, 4, seed) * 2.5
        z += sum(TR.volcano_h(x, y, cx, cy, r, hh, seed=k) for k, (cx, cy, r, hh) in enumerate(V))
        z -= TR.smooth01((x + 60) / -80) * 14                        # the sea basin to the left
        return z
    rock = TR.blend_mat('basalt', TR.layer(BASALT, '#4a4440', 6.0, tint='#a89890'),
                        [(TR.layer(('rock', 'cliff', 'lava'), '#5a4e48', 10.0, tint='#9a8478'), dict(slope=(.9, .7), noise=.05)),
                         (TR.layer(('ash', 'dirt', 'ground'), '#6a6058', 4.0, tint='#9a9088'), dict(slope=(.95, 1.0), noise=.08))], bump=.6)
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
    plumes = [TR.smoke_column(f'plume{k}', (cx, cy, ter.z(cx, cy) - 2), rate=7.0, life=18, rise=9.0 + k, r0=r * .06, r1=r * .32, wind=(3.0, 1.0),
                              turb=r * .2, density=.05, glow=.6 if k < 3 else 0.0, voxel=max(1.2, r * .025), seed=k) for k, (cx, cy, r, hh) in enumerate(V)]
    # boiling sea + steam
    sea = TR.ocean('sea', 900, (-420, 300, -6.5), wave=1.4, choppy=1.6, col='#1a2a26', murk='#3a3020', foam=True)
    steam = [TR.smoke_column(f'steam{k}', (-150 - k * 60, 120 + k * 70, -7), rate=2.0, life=10, rise=4.0, r0=6, r1=22, wind=(2.0, .5), turb=6,
                             col=(.75, .72, .7), density=.01, voxel=1.5, seed=k + 9) for k in range(4)]
    # rubble + boulders everywhere
    TR.scatter(ter, ['namaqualand_boulder_02', 'namaqualand_boulder_04', 'namaqualand_boulder_05', 'rock_07', 'rock_09', 'boulder_01', 'moon_rock_03', 'moon_rock_06'],
               420, (-140, 140, 10, 260), seed=seed, scale=(.6, 2.6), slope_min=.6, zrange=(-2, 400), fallback=TR.fallback_rock)
    TR.scatter(ter, ['coast_rocks_02', 'rock_face_01', 'namaqualand_cliff_02'], 40, (-200, 200, 100, 500), seed=seed + 1, scale=(1.5, 4.0), slope_min=.3,
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
            if hput('SchoolChair_01', (x, y - .55, 0), 180 if False else 0, 1.0) is None: T.box(f'chair{r_}{c_}', (.42, .42, .04), (x, y - .55, .44), T.plain('chairw', '#3a5a8a', .5))
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
