"""The middle-class flat and the colony street for the 'Indian Middle Class Edition' parody (DAGAR CLIPS ink style).

Interior (floor z=0, walls 2.8 m, ceiling): LIVING room x[-3, 2] y[0, 4.5] - sofa on the back wall facing -Y, TV on the front
wall, centre table with newspaper and chai; front door in the front wall (x -1.4..-0.4) to the porch.
BEDROOM x[2, 5.2] y[1.5, 4.5] through a doorway in the living room's right wall (y 2.6..3.5): bed along the back wall,
desk with a glowing PC, gamer posters, ceiling fan.
Outside: porch y[-1.6, 0], gate at y -1.6, colony street y[-8, -2.4] along X, row houses on both sides, electric poles
with wires, scooter, a chai stall and a gas agency across the street."""
import math, random, os
import bpy, bmesh
from mathutils import Vector
import town as T
import lib
from town import box, cyl, plain, put
import city as C
import typo as TY
import hero as HR

H = 2.8
LIV = (-3.0, 2.0, 0.0, 4.5); BED = (2.0, 5.2, 1.5, 4.5)
DOOR = (0.5, 1.5); WINF = (-2.7, -1.6)
SOFA = Vector((-.6, 3.95, 0)); TV = Vector((-.75, .3, 0)); TABLE = Vector((-.6, 2.35, 0))
BEDC = Vector((4.05, 3.65, 0)); BED_TOP = .5
_M = {}


def mat_ph(name, kws, col, scale=1.0, tint=None):
    key = name
    if key in _M: return _M[key]
    m = None
    if T.PH:
        try: m = lib.mat_ph(name, *kws, scale=scale, tint=tint, bump=.4, res=os.environ.get('PH_RES', '1k'))
        except Exception as e: lib.log('house PH', name, e)
    if m is None: m = plain(name, col, .85)
    _M[key] = m; return m


def checker(name, c1, c2, scale=10.0, rough=.85, lines=None):
    """object-space checks (bedsheets, lungi): two colours + optional thin light lines"""
    key = ('chk', name)
    if key in _M: return _M[key]
    m = bpy.data.materials.new(name); m.use_nodes = True; N = m.node_tree.nodes; L = m.node_tree.links; b = N['Principled BSDF']
    tc = N.new('ShaderNodeTexCoord'); ck = N.new('ShaderNodeTexChecker'); ck.inputs['Scale'].default_value = scale
    ck.inputs['Color1'].default_value = (*T.hexc(c1)[:3], 1); ck.inputs['Color2'].default_value = (*T.hexc(c2)[:3], 1)
    L.new(tc.outputs['Object'], ck.inputs['Vector']); out = ck.outputs['Color']
    if lines:
        br = N.new('ShaderNodeTexBrick'); br.inputs['Scale'].default_value = scale / 2; br.inputs['Mortar Size'].default_value = .02; br.offset = 0
        br.inputs['Brick Width'].default_value = 1; br.inputs['Row Height'].default_value = 1
        br.inputs['Color1'].default_value = (1, 1, 1, 1); br.inputs['Color2'].default_value = (1, 1, 1, 1); br.inputs['Mortar'].default_value = (*T.hexc(lines)[:3], 1)
        L.new(tc.outputs['Object'], br.inputs['Vector'])
        mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs['Factor'].default_value = 1
        L.new(out, mx.inputs['A']); L.new(br.outputs['Color'], mx.inputs['B']); out = mx.outputs['Result']
    L.new(out, b.inputs['Base Color']); b.inputs['Roughness'].default_value = rough
    _M[key] = m; return m


def wall(name, a, b, h=H, mat=None, holes=(), thick=.12):
    """straight wall from a to b (2D) with rectangular holes [(u0, u1, z0, z1)] along it"""
    a, b = Vector((*a, 0)), Vector((*b, 0)); d = (b - a); L_ = d.length; dn = d.normalized(); ang = math.atan2(dn.y, dn.x)
    cuts = sorted(holes); segs = []; u = 0.0
    for (u0, u1, z0, z1) in cuts:
        if u0 > u: segs.append((u, u0, 0, h))
        if z0 > 0: segs.append((u0, u1, 0, z0))
        if z1 < h: segs.append((u0, u1, z1, h))
        u = u1
    if u < L_: segs.append((u, L_, 0, h))
    for k, (u0, u1, z0, z1) in enumerate(segs):
        c = a + dn * ((u0 + u1) / 2)
        box(f'{name}{k}', (u1 - u0, thick, z1 - z0), (c.x, c.y, (z0 + z1) / 2), mat, rot=(0, 0, ang))


def window(name, c, w, h, facing, grill=True, light=None):
    """a window frame + glass + iron grill; facing = outward normal (2D)"""
    ang = math.atan2(facing[1], facing[0]) - math.pi / 2
    fr = plain('winframe', '#e8e2d4', .6); gl = plain('winglass', '#b8d0e0', .05, emit='#dff0ff', strength=1.2); ir = plain('grill', '#1c1e20', .5, .6)
    root = bpy.data.objects.new(name, None); T.coll('Town').objects.link(root); root.location = c; root.rotation_euler = (0, 0, ang)
    parts = [box(name + '_gl', (w, .02, h), (0, 0, 0), gl)]
    for x in (-w / 2, 0, w / 2): parts.append(box(f'{name}_fv{x}', (.05, .08, h + .05), (x, 0, 0), fr))
    for z in (-h / 2, h / 2): parts.append(box(f'{name}_fh{z}', (w + .05, .08, .05), (0, 0, z), fr))
    if grill:
        for k in range(7): parts.append(cyl(f'{name}_g{k}', .008, h, (-w / 2 + w * (k + .5) / 7, -.06, 0), ir, v=6))
    for p in parts: p.parent = root
    if light:
        l = bpy.data.lights.new(name + '_l', 'AREA'); l.energy = light; l.size = max(w, h); l.color = (1, .93, .82)
        lo = bpy.data.objects.new(name + '_l', l); T.coll('Town').objects.link(lo); lo.parent = root; lo.location = (0, .25, 0); lo.rotation_euler = (math.radians(-90), 0, 0)
    return root


def ceiling_fan(name, c):
    m = plain('fanwhite', '#ece8e0', .5); rod = cyl(name + '_rod', .015, .45, (c.x, c.y, H - .225), m, v=8)
    hub = cyl(name + '_hub', .1, .1, (c.x, c.y, H - .5), m, v=16)
    blades = bpy.data.objects.new(name + '_bl', None); T.coll('Town').objects.link(blades); blades.location = (c.x, c.y, H - .52)
    for k in range(3):
        a = k * math.tau / 3
        b_ = box(f'{name}_b{k}', (.55, .1, .012), (math.cos(a) * .35, math.sin(a) * .35, 0), m, rot=(0, 0, a)); b_.parent = blades
    return blades


def poster(name, txt, c, w, h, facing, bg, fg, size=(600, 840)):
    return C.sign(name, txt, w, h, c, facing=facing, bg=bg, fg=fg, size=size, font_scale=.5, border=fg, **TY.kw('bungee'))


# ------------------------------------------------------------------ Poly Haven models (CC0), instanced; primitives as fallback
PHC = {}


def phm(aid):
    if not T.PH or os.environ.get('NOPHPROPS'): return None
    if aid in PHC: return PHC[aid]
    PHC[aid] = None
    try:
        m = lib.model([aid], res=os.environ.get('PH_MODEL_RES', '1k'))
    except Exception as e:
        lib.log('phm fail', aid, e); m = None
    if not m: return None
    root, objs = m; cn = 'PHM_' + aid
    c = bpy.data.collections.new(cn); bpy.context.scene.collection.children.link(c)
    for o in [root] + list(objs):
        for cc in list(o.users_collection): cc.objects.unlink(o)
        c.objects.link(o)
    c.instance_offset = root.location.copy()
    bpy.context.view_layer.layer_collection.children[cn].exclude = True
    PHC[aid] = c; return c


def put(aid, loc, rot=0.0, scale=1.0, fallback=None):
    """place a Poly Haven model (rot in degrees about Z; models face -Y); fallback() builds a stand-in when PH is off"""
    c = phm(aid)
    if c is None:
        return fallback() if fallback else None
    e = bpy.data.objects.new(aid + '_i', None); e.instance_type = 'COLLECTION'; e.instance_collection = c
    e.location = loc; e.rotation_euler = (0, 0, math.radians(rot)); e.scale = scale if isinstance(scale, tuple) else (scale,) * 3
    T.coll('Town').objects.link(e); return e


def conduit(name, pts, m=None):
    """surface-run electric wiring conduit (white PVC) - every Indian wall has it"""
    m = m or plain('conduit', '#ece8e0', .5)
    T.lib.tube(name, [Vector(p) for p in pts], .012, m=m)


def switchboard(name, c, facing):
    ang = math.atan2(facing[1], facing[0]) - math.pi / 2
    root = bpy.data.objects.new(name, None); T.coll('Town').objects.link(root); root.location = c; root.rotation_euler = (0, 0, ang)
    HR.rbox(name + '_b', (.32, .03, .14), (0, -.015, 0), plain('swb', '#f2f0ea', .4), .15, root, sub=1)
    for k in range(4): HR.rbox(f'{name}_s{k}', (.035, .015, .05), (-.11 + k * .06, -.035, .01), plain('sw', '#e8e4dc', .4), .3, root, sub=1)
    T.lib.sphere(name + '_led', .006, (.13, -.034, .04), plain('swled', '#ff3020', .3, emit='#ff3020', strength=3)).parent = root
    return root


def curtain(name, c, w, h, facing, col, pattern='#e8b84a'):
    """pleated cotton curtain on a rod: a wavy strip (folds) with a printed motif"""
    ang = math.atan2(facing[1], facing[0]) - math.pi / 2
    bm = bmesh.new(); nx, nz = 28, 6; vs = []
    for i in range(nx + 1):
        row = []
        for j in range(nz + 1):
            x = -w / 2 + w * i / nx; z = -h + h * j / nz; y = .035 * math.sin(i * math.pi / 2) * (1 - .3 * j / nz)
            row.append(bm.verts.new((x, y, z)))
        vs.append(row)
    for i in range(nx):
        for j in range(nz): bm.faces.new((vs[i][j], vs[i + 1][j], vs[i + 1][j + 1], vs[i][j + 1]))
    m = checker(name + '_m', col, pattern, 22, rough=.9)
    o = HR._obj(name, bm, m, 1); o.location = c; o.rotation_euler = (0, 0, ang)
    so = o.modifiers.new('sol', 'SOLIDIFY'); so.thickness = .006
    rod = cyl(name + '_rod', .012, w + .3, (0, 0, .04), plain('rod', '#8a6a3a', .3, .8), rot=(0, math.pi / 2, 0), v=8); rod.parent = o
    return o


def door_leaf(name, w, h, mat):
    """panelled wooden door with a brass handle, hinge at local x=0, opening along +x"""
    root = bpy.data.objects.new(name, None); T.coll('Town').objects.link(root)
    HR.rbox(name + '_slab', (w, .05, h), (w / 2, 0, h / 2), mat, .08, root, sub=1)
    for k, (z0, z1) in enumerate(((.15, .95), (1.1, 1.9))):
        for sd in (-1, 1):
            HR.rbox(f'{name}_p{k}{sd}', (w * .36, .016, z1 - z0), (w / 2 + sd * w * .22, sd * 0 - .03, (z0 + z1) / 2), mat, .1, root, sub=1)
            HR.rbox(f'{name}_q{k}{sd}', (w * .36, .016, z1 - z0), (w / 2 + sd * w * .22, .03, (z0 + z1) / 2), mat, .1, root, sub=1)
    br = plain('brass', '#c8a040', .3, 1.0)
    for y in (-.05, .05): T.lib.sphere(f'{name}_k{y}', .03, (w - .1, y, 1.0), br, seg=12, rings=8).parent = root
    return root


def bed(bc):
    """wooden double bed: headboard with panels, rounded mattress, checked bedsheet, soft pillows"""
    wd = mat_ph('bedwood', ('wood', 'veneer', 'oak'), '#6a4028', scale=.6, tint='#8a5838')
    HR.rbox('bed_frame', (2.05, 1.15, .3), (bc.x, bc.y, .17), wd, .1)
    HR.rbox('bed_head', (.07, 1.2, .95), (bc.x + 1.03, bc.y, .5), wd, .12)
    HR.rbox('bed_headtop', (.1, 1.26, .07), (bc.x + 1.03, bc.y, .98), wd, .3)
    HR.rbox('bed_foot', (.06, 1.2, .5), (bc.x - 1.03, bc.y, .3), wd, .12)
    HR.rbox('mattress', (1.98, 1.08, .17), (bc.x, bc.y, .4), checker('bedsheet', '#2a5aa8', '#3a78c0', 14, lines='#e8e8e0'), .35)
    pm = plain('pillowc', '#f2ece0', .85)
    for sd in (-1, 1): HR.rbox(f'pillow{sd}', (.36, .48, .13), (bc.x + .76, bc.y + sd * .26, .53), pm, .45)
    return wd


def interior(night=False):
    floor = mat_ph('floortile', ('marble', 'floor', 'tiles'), '#e0d8cc', scale=.9)
    paint_l = mat_ph('wall_living', ('plaster', 'painted', 'wall'), '#ecdcb4', scale=.6, tint='#f2e2b8')
    paint_b = mat_ph('wall_bed', ('plaster', 'painted', 'wall'), '#a8c8d8', scale=.6, tint='#b4d4e4')
    skirt = plain('skirting', '#8a7a68', .4)
    box('floor', (8.4, 4.8, .06), (1.1, 2.25, -.03), floor)
    box('ceiling', (8.4, 4.8, .06), (1.1, 2.25, H + .03), plain('ceilingw', '#f4f0e8', .9, emit='#f4f0e8', strength=.35))
    x0, x1, y0, y1 = LIV
    wall('lw_front', (x0, y0), (x1, y0), mat=paint_l, holes=[(DOOR[0] - x0, DOOR[1] - x0, 0, 2.1), (WINF[0] - x0, WINF[1] - x0, .95, 2.05)])
    wall('lw_back', (x0, y1), (x1, y1), mat=paint_l, holes=[(.5, 1.6, 1.0, 2.05)])
    wall('lw_left', (x0, y0), (x0, y1), mat=paint_l)
    wall('lw_right', (x1, y0), (x1, y1), mat=paint_l, holes=[(2.6, 3.5, 0, 2.1)])
    bx0, bx1, by0, by1 = BED
    wall('bw_front', (bx0, by0), (bx1, by0), mat=paint_b)
    wall('bw_back', (bx0, by1), (bx1, by1), mat=paint_b)
    wall('bw_right', (bx1, by0), (bx1, by1), mat=paint_b, holes=[(1.0, 2.1, 1.0, 2.0)])
    for nm, a, b in (('sk_lf', (x0, .07), (DOOR[0], .07)), ('sk_lf2', (DOOR[1], .07), (x1, .07)), ('sk_lb', (x0, y1 - .07), (x1, y1 - .07)),
                     ('sk_ll', (x0 + .07, 0), (x0 + .07, y1)), ('sk_bb', (bx0, by1 - .07), (bx1, by1 - .07)), ('sk_br', (bx1 - .07, by0), (bx1 - .07, by1))):
        a, b = Vector(a), Vector(b); c = (a + b) / 2; d = b - a
        box(nm, (d.length, .015, .09), (c.x, c.y, .045), skirt, rot=(0, 0, math.atan2(d.y, d.x)))
    # door frame + the open front door
    dw = mat_ph('doorwood', ('wood', 'planks', 'door'), '#6a3e22', scale=.5, tint='#7a4a2a')
    for x in DOOR: box(f'dframe{x}', (.08, .16, 2.14), (x, 0, 1.07), dw)
    box('dframe_top', (DOOR[1] - DOOR[0] + .16, .16, .08), ((DOOR[0] + DOOR[1]) / 2, 0, 2.14), dw)
    dl = door_leaf('frontdoor', DOOR[1] - DOOR[0] - .04, 2.06, dw); dl.location = (DOOR[1] - .02, .04, 0); dl.rotation_euler = (0, 0, math.radians(180 - 80))
    # windows: frame + glass + grill + curtains (morning sun comes through the back window)
    window('win_lfront', ((WINF[0] + WINF[1]) / 2, y0, 1.5), WINF[1] - WINF[0], 1.1, (0, -1))
    window('win_lback', (x0 + 1.05, y1, 1.52), 1.1, 1.05, (0, 1), light=140)
    window('win_bed', (bx1, by0 + 1.55, 1.5), 1.1, 1.0, (1, 0), light=240)
    curtain('cur_lf', ((WINF[0] + WINF[1]) / 2 - .35, y0 + .1, 2.2), .5, 1.35, (0, 1), '#c86a3a')
    curtain('cur_lb', (x0 + .45, y1 - .1, 2.2), .45, 1.35, (0, -1), '#c86a3a')
    curtain('cur_lb2', (x0 + 1.65, y1 - .1, 2.2), .45, 1.35, (0, -1), '#c86a3a')
    curtain('cur_bed', (bx1 - .1, by0 + .85, 2.15), .5, 1.3, (-1, 0), '#2a6a8a', '#e8e0c8')
    # ---- living room
    s = SOFA
    put('sofa_03', (s.x, s.y + .12, 0), 0, .8, fallback=lambda: _sofa_prim(s))
    put('throw_pillows_01', (s.x + .55, s.y + .05, .36), 0, .6)
    put('modern_coffee_table_01', (TABLE.x, TABLE.y, 0), 0, 1.0, fallback=lambda: _table_prim(TABLE))
    cyl('chai_cup', .035, .07, (TABLE.x + .3, TABLE.y - .1, .43), plain('cup', '#f4f0e8', .4), v=14)
    cyl('chai_tea', .032, .005, (TABLE.x + .3, TABLE.y - .1, .465), plain('chai', '#a8703a', .3), v=14)
    cyl('saucer', .06, .008, (TABLE.x + .3, TABLE.y - .1, .396), plain('cup', '#f4f0e8', .4), v=18)
    pass
    v = TV
    put('modern_wooden_cabinet', (v.x, v.y + .02, 0), 180, (.62, .8, .9), fallback=lambda: box('tv_cab', (1.3, .45, .55), (v.x, v.y, .28), plain('teak', '#5a3420', .45), bevel=.02))
    if put('Television_01', (v.x, v.y + .02, .61), 180, 1.3) is None:
        box('tv', (.75, .45, .55), (v.x, v.y + .02, .87), plain('tvbody', '#1a1a1c', .3), bevel=.03)
    if not T.PH: box('tv_scr', (.56, .01, .4), (v.x, v.y + .26, .87), plain('tvscr', '#203048', .15, emit='#5080c0', strength=.5))
    put('potted_plant_02', (x0 + .45, y1 - .45, 0), 30, 1.0)
    put('potted_plant_02', (v.x - 1.05, v.y + .3, 0), -40, .7)
    if put('wall_clock', (s.x, y1 - .01, 2.25), 0, 1.0) is None:
        cyl('clock', .17, .03, (s.x, y1 - .08, 2.2), plain('clockface', '#f4f0e8', .5), rot=(math.pi / 2, 0, 0), v=24)
    put('hanging_picture_frame_01', (s.x - .95, y1 - .07, 1.7), 0, .7)
    put('hanging_picture_frame_02', (s.x + .95, y1 - .07, 1.75), 0, .7)
    C.sign('calendar', 'NOVEMBER\n2026', .4, .55, (x0 + .07, 2.0, 1.7), facing=(1, 0), bg='#f4f0e4', fg='#b02020', size=(400, 550), **TY.kw('oswald_b'))
    put('hanging_picture_frame_02', (x0 + .08, 3.3, 1.75), 90, .6)
    box('tubelight_b', (1.25, .05, .06), (x0 + .07, 1.0, 2.4), plain('tubeholder', '#ece8e0', .4), rot=(0, 0, math.pi / 2))
    box('tubelight', (1.18, .035, .035), (x0 + .1, 1.0, 2.38), plain('tube', '#ffffff', .2, emit='#fff8e8', strength=10 if night else 4), rot=(0, 0, math.pi / 2))
    switchboard('swb_door', (DOOR[0] - .35, .07, 1.25), (0, 1)); switchboard('swb_sofa', (s.x + 1.3, y1 - .07, 1.25), (0, -1))
    conduit('cd1', [(DOOR[0] - .35, .07, 1.32), (DOOR[0] - .35, .07, 2.7), (x0 + .07, .07, 2.7), (x0 + .07, 1.0, 2.7), (x0 + .07, 1.0, 2.45)])
    conduit('cd2', [(s.x + 1.3, y1 - .07, 1.32), (s.x + 1.3, y1 - .07, 2.72), (TABLE.x, y1 - .07, 2.72)])
    put('wicker_basket_01', (x0 + .4, .5, 0), 20, 1.0)
    rack = mat_ph('rackwood', ('wood', 'planks'), '#5a3a22', scale=.4)
    HR.rbox('shoerack', (.75, .3, .45), (DOOR[0] - .6, .3, .23), rack, .05)
    for k in range(3):
        c_ = HR.chappal(f'rack_chappal{k}'); c_.location = (DOOR[0] - .85 + k * .22, .3, .455); c_.rotation_euler = (0, 0, math.radians(90 + k * 12))
    # ---- bedroom (the gamer's den)
    bc = BEDC; bed(bc)
    put('painted_wooden_nightstand', (bc.x + .85, bc.y - .85, 0), 0, .9)
    tw = mat_ph('deskwood', ('wood', 'veneer'), '#5a3420', scale=.5)
    HR.rbox('desk', (1.15, .55, .045), (bx0 + .78, by0 + .4, .74), tw, .1)
    for sx in (-1, 1): HR.rbox(f'desk_leg{sx}', (.045, .5, .72), (bx0 + .78 + sx * .53, by0 + .4, .36), tw, .2)
    blk = plain('tvbody', '#141416', .3)
    HR.rbox('monitor', (.6, .04, .36), (bx0 + .78, by0 + .3, 1.07), blk, .08)
    box('monitor_scr', (.56, .005, .32), (bx0 + .78, by0 + .33, 1.07), plain('pcscr', '#102040', .2, emit='#40a0ff', strength=2.5))
    HR.rbox('monitor_st', (.05, .05, .16), (bx0 + .78, by0 + .28, .84), blk, .2); HR.rbox('monitor_ft', (.22, .14, .015), (bx0 + .78, by0 + .28, .77), blk, .3)
    HR.rbox('keyboard', (.42, .13, .02), (bx0 + .78, by0 + .5, .775), plain('kb', '#1e1e22', .5), .2)
    HR.rbox('pc', (.2, .42, .44), (bx0 + 1.22, by0 + .42, .985), blk, .05)
    box('pc_led', (.004, .3, .02), (bx0 + 1.115, by0 + .42, 1.12), plain('rgb', '#ff30c0', .2, emit='#ff30c0', strength=6))
    put('gaming_console', (bx0 + .4, by0 + .45, .765), 10, 1.0)
    put('gamepad', (bx0 + .55, by0 + .6, .765), -20, .5)
    if put('plastic_monobloc_chair_01', (bx0 + .78, by0 + 1.0, 0), 15, 1.0) is None:
        box('chair', (.45, .45, .05), (bx0 + .78, by0 + 1.05, .45), plain('monobloc', '#f2f0ea', .5))
    T.lib.sphere('clothes', .22, (bx0 + .78, by0 + 1.18, .62), checker('tshirtpile', '#4a6a3a', '#3a5a2a', 30)).scale = (1.1, .8, .45)
    poster('poster1', 'LEVEL\nUP', (bx0 + 1.6, by1 - .07, 1.7), .6, .85, (0, -1), '#1a1a3a', '#40e0ff')
    poster('poster2', 'NO\nSLEEP\nJUST\nGAMES', (bx1 - .07, by0 + 2.5, 1.6), .55, .8, (-1, 0), '#3a0a1a', '#ff5070')
    poster('poster3', 'PRESS\nSTART', (bx0 + .78, by0 + .07, 1.75), .5, .55, (0, 1), '#20103a', '#ffd040', size=(600, 660))
    put('steel_frame_shelves_01', (bx1 - .3, by0 + .35, 0), -90, .8)
    switchboard('swb_bed', (bx0 + .07, by0 + .6, 1.25), (1, 0))
    fans = []
    for k, c_ in enumerate((Vector((bc.x - .4, bc.y - .6, 0)), Vector((TABLE.x, TABLE.y, 0)))):
        f = put('ceiling_fan', (c_.x, c_.y, H), 0, .85)
        if f is None: f = ceiling_fan(f'fan{k}', c_)
        fans.append(f)
    # ceiling lights (soft, warm) so the rooms read
    for k, (x, y, e) in enumerate(((-1.4, 1.6, 160), (.4, 3.4, 120), (3.6, 2.6, 140))):
        l = bpy.data.lights.new(f'room{k}', 'AREA'); l.energy = e * (1.6 if night else 1.0); l.size = 1.6; l.color = (1, .92, .8)
        o = bpy.data.objects.new(f'room{k}', l); T.coll('Town').objects.link(o); o.location = (x, y, H - .15)
    return dict(fans=fans)


def _sofa_prim(s):
    sofa_m = mat_ph('sofa', ('fabric', 'leather'), '#7a3a2a', scale=.5, tint='#8a4430')
    HR.rbox('sofa_base', (2.0, .8, .3), (s.x, s.y, .2), sofa_m, .1)
    HR.rbox('sofa_back', (2.0, .22, .55), (s.x, s.y + .32, .55), sofa_m, .2)
    for sx in (-1, 1): HR.rbox(f'sofa_arm{sx}', (.2, .8, .45), (s.x + sx * 1.0, s.y, .32), sofa_m, .25)
    for k in range(2): HR.rbox(f'sofa_cush{k}', (.8, .62, .12), (s.x - .41 + k * .82, s.y - .04, .41), sofa_m, .35)


def _table_prim(t):
    tw = plain('teak', '#5a3420', .45); HR.rbox('ctable_top', (1.1, .6, .05), (t.x, t.y, .4), tw, .1)
    for sx in (-1, 1):
        for sy in (-1, 1): box(f'ctable_leg{sx}{sy}', (.05, .05, .38), (t.x + sx * .48, t.y + sy * .24, .19), tw)



def chajja(name, c, w, facing, depth=.45):
    """the concrete sunshade slab over every Indian window"""
    ang = math.atan2(facing[1], facing[0]) - math.pi / 2
    o = HR.rbox(name, (w + .3, depth, .07), (0, 0, 0), mat_ph('concrete', ('concrete', 'plaster'), '#c8c0b0', scale=.5), .15, sub=1)
    o.rotation_euler = (math.radians(-6), 0, ang); o.location = Vector(c) + Vector((facing[0], facing[1], 0)) * (depth / 2)
    return o


def ext_window(name, c, w, h, facing, frame='#e8e2d4', grill='#1c1e20', lit=False):
    """outside view of a window: dark glass with sky reflection, frame, a patterned MS grill box, chajja on top"""
    ang = math.atan2(facing[1], facing[0]) - math.pi / 2
    root = bpy.data.objects.new(name, None); T.coll('Town').objects.link(root); root.location = c; root.rotation_euler = (0, 0, ang)
    gl = plain('extglass_lit' if lit else 'extglass', '#2a3440', .04, emit='#ffcc80' if lit else None, strength=1.5 if lit else 0)
    fr = plain('frame' + frame, frame, .5); ir = plain('grill' + grill, grill, .45, .6)
    box(name + '_gl', (w, .02, h), (0, .02, 0), gl).parent = root
    for x in (-w / 2, 0, w / 2): box(f'{name}_fv{x:.2f}', (.05, .06, h + .05), (x, 0, 0), fr).parent = root
    for z in (-h / 2, h / 2): box(f'{name}_fh{z:.2f}', (w + .05, .06, .05), (0, 0, z), fr).parent = root
    gd = -.14
    for k in range(9): cyl(f'{name}_g{k}', .007, h, (-w / 2 + w * (k + .5) / 9, gd, 0), ir, v=6).parent = root
    for z in (-h / 2, -h / 6, h / 6, h / 2): box(f'{name}_gh{z:.2f}', (w + .04, .012, .012), (0, gd, z), ir).parent = root
    for x in (-w / 2 - .02, w / 2 + .02): box(f'{name}_gs{x:.2f}', (.012, .14, h), (x, gd / 2, 0), ir).parent = root
    chajja(name + '_ch', Vector(c) + Vector((0, 0, h / 2 + .12)), w, facing)
    return root


def water_tank(name, c, r=.5, h=.9):
    """black ribbed plastic rooftop water tank"""
    m = plain('tankblk', '#1a1a1c', .55)
    secs = []
    for k in range(9):
        z = h * k / 8; rr = r * (1.0 if k % 2 == 0 else .965)
        if k == 8: rr = r * .8
        secs.append((z, 0, 0, rr * 2, rr * 2, 2))
    o = HR.loft(name, secs + [(h + .06, 0, 0, r * .35, r * .35, 2)], m, axis='z', n=28, sub=1); o.location = c
    cyl(name + '_lid', r * .3, .05, (c[0], c[1], c[2] + h + .07), m, v=16)
    return o


def plaster(col, key=None):
    return mat_ph('plaster_' + (key or col), ('plaster', 'painted', 'wall'), col, scale=.7, tint=col)


def rowhouse(name, x0, w, front_y, side, floors, col, seed, shop=None, night=False):
    """an Indian colony house: plastered block, floor bands, windows with grills + chajjas, a balcony with railing and
    drying clothes, parapet, water tank, AC unit, rain pipe; ground floor = gate+door or a shop shutter with a board.
    side=+1: front faces -Y (north side of the street); side=-1: front faces +Y"""
    r = random.Random(seed); fdir = (0, -side); D = 8.0; FH = 3.1; Hh = floors * FH + .3
    cy = front_y + side * D / 2; xc = x0 + w / 2
    pm = plaster(col)
    box(name + '_body', (w, D, Hh), (xc, cy, Hh / 2), pm)
    band = plaster('#e8e0d0', 'band')
    for f in range(1, floors + 1):
        box(f'{name}_band{f}', (w + .08, .14, .14), (xc, front_y - side * .05, f * FH), band)
    box(name + '_parapet', (w + .1, .2, .7), (xc, front_y + side * .1, Hh + .35), band)
    for f in range(floors):
        z = f * FH + 1.55
        if f == 0 and shop: continue
        nwin = 2 if w > 5 else 1
        for k in range(nwin):
            xx = x0 + w * (k + 1) / (nwin + 1)
            if f == 0 and k == 0 and not shop: continue
            ext_window(f'{name}_w{f}{k}', (xx, front_y - side * .01, z), r.choice([1.1, 1.3]), 1.15, fdir, lit=night and r.random() < .6,
                       frame=r.choice(['#e8e2d4', '#6a4a30', '#8a9a8a']), grill=r.choice(['#1c1e20', '#2a5a4a', '#3a2a5a']))
    if floors >= 2:                                              # balcony on the 1st floor
        bw_ = min(w - 1.0, 3.2); bx = x0 + w * .3 + r.uniform(-.3, .3); by = front_y - side * .55
        HR.rbox(f'{name}_bal', (bw_, 1.1, .14), (bx, by, FH + .07), mat_ph('concrete', ('concrete', 'plaster'), '#c8c0b0', scale=.5), .1, sub=1)
        rail = plain('rail' + str(seed % 3), ['#2a2a2a', '#2a5a4a', '#6a2a2a'][seed % 3], .45, .6)
        for k in range(int(bw_ / .12)): cyl(f'{name}_rl{k}', .009, .85, (bx - bw_ / 2 + .06 + k * .12, by - side * .52, FH + .55), rail, v=6)
        box(f'{name}_rtop', (bw_, .05, .04), (bx, by - side * .52, FH + .98), rail)
        if r.random() < .8:
            box(f'{name}_clrope', (bw_ - .2, .006, .006), (bx, by - side * .3, FH + 1.9), plain('rope', '#d8d0c0', .9))
            for k in range(r.randint(2, 4)):
                cl = HR.rbox(f'{name}_cl{k}', (r.uniform(.35, .55), .015, r.uniform(.45, .8)), (bx - bw_ / 2 + .4 + k * .55, by - side * .3, FH + 1.6),
                             plain('cloth' + str(k), ['#c83030', '#3060c0', '#e8c030', '#f0f0f0', '#e07ab0'][(k + seed) % 5], .95), .1, sub=1)
        if r.random() < .6: put('potted_plant_04', (bx + bw_ / 2 - .25, by - side * .3, FH + .14), r.uniform(0, 360), 1.6)
    if r.random() < .7:                                          # AC outdoor unit
        acx = x0 + r.uniform(.6, w - .6); acz = (floors - 1) * FH + r.uniform(.6, 1.0)
        HR.rbox(f'{name}_ac', (.8, .3, .55), (acx, front_y - side * .17, acz), plain('acunit', '#ecebe6', .45), .08, sub=1)
        cyl(f'{name}_acfan', .19, .02, (acx - .1, front_y - side * .33, acz), plain('acgrill', '#3a3a3a', .6), rot=(math.pi / 2, 0, 0), v=20)
    pipe = plain('pipe', '#3a3a3a', .5)
    cyl(f'{name}_pipe', .04, Hh, (x0 + .2, front_y - side * .06, Hh / 2), pipe, v=8)
    water_tank(f'{name}_tank', (x0 + r.uniform(1.0, w - 1.0), cy + side * r.uniform(-1, 1), Hh), r.uniform(.45, .6))
    if r.random() < .5:                                          # dish antenna on the parapet
        d = T.lib.sphere(f'{name}_dish', .3, (x0 + w - .7, front_y + side * .1, Hh + .95), plain('dish', '#e8e8e4', .4), seg=20, rings=10)
        d.scale = (1, .25, 1); d.rotation_euler = (math.radians(20), 0, math.radians(r.uniform(-30, 30)))
    if shop:
        sw = w - 1.0
        sh_ = mat_ph('shutter', ('corrugated', 'metal'), '#8a8c8e', scale=.4)
        box(f'{name}_shut', (sw, .06, .55), (xc, front_y - side * .02, 2.55), sh_)
        box(f'{name}_shopin', (sw, .1, 2.25), (xc, front_y + side * .2, 1.12), plain('shopdark', '#2a241e', .9))
        bwid = sw + .3; px = (int(220 * bwid / .75), 220); fsc = min(.55, .88 * px[0] / (len(shop) * .64 * px[1]))
        C.sign(f'{name}_board', shop, bwid, .75, (xc, front_y - side * .12, 3.25), facing=fdir, bg=r.choice(['#c01818', '#f0d020', '#1a5aa8', '#1a8a4a']),
               fg='#ffffff' if 'Gas' in shop else '#1a1a1a', size=px, font_scale=fsc, **TY.kw('baloo'))
        box(f'{name}_step', (sw, .5, .18), (xc, front_y - side * .25, .09), mat_ph('concrete', ('concrete', 'plaster'), '#c8c0b0', scale=.5))
    else:                                                        # gate + compound wall + door
        gx = x0 + w * .72
        door_leaf(f'{name}_door', .95, 2.05, mat_ph('doorwood', ('wood', 'planks', 'door'), '#6a3e22', scale=.5)).location = (gx - .47, front_y - side * .01, 0)
        cw = plaster('#e0d0b0', 'compound')
        for xa, xb in ((x0, gx - .7), (gx + .7, x0 + w)):
            if xb - xa > .1: box(f'{name}_cw{xa:.1f}', (xb - xa, .15, 1.0), ((xa + xb) / 2, front_y - side * 1.6, .5), cw)
    return dict(x0=x0, w=w, front_y=front_y)


def pole(name, x, y, h=8.0):
    pm = mat_ph('polecon', ('concrete',), '#8a8a84', scale=.4)
    HR.loft(name, [(0, 0, 0, .26, .2, 3), (h, 0, 0, .14, .12, 3)], pm, axis='z', n=12, sub=0).location = (x, y, 0)
    box(name + '_arm', (1.3, .08, .08), (x, y, h - .5), plain('polesteel', '#5a5a58', .5, .6))
    for k in (-.55, -.2, .2, .55): cyl(f'{name}_ins{k}', .03, .09, (x + k, y, h - .41), plain('insul', '#e8e4dc', .3), v=10)
    lamp = HR.rbox(name + '_lamp', (.45, .16, .08), (x, y - .7, h - 1.4), plain('lamphead', '#3a3a3a', .4), .2, sub=1)
    box(name + '_lamparm', (.04, .7, .04), (x, y - .35, h - 1.35), plain('polesteel', '#5a5a58', .5, .6))
    return Vector((x, y, h - .4))


def street(night=False):
    road = mat_ph('road', ('asphalt', 'road'), '#5a5650', scale=.6)
    dirt = mat_ph('dust', ('dirt', 'ground', 'gravel'), '#a89070', scale=.6)
    pave = mat_ph('pavers', ('paving', 'cobblestone', 'brick floor'), '#9a9088', scale=.5)
    box('road', (80, 5.2, .06), (0, -5.2, -.03), road)
    box('shoulder_n', (80, .9, .08), (0, -2.15, -.01), dirt); box('shoulder_s', (80, .9, .08), (0, -8.25, -.01), dirt)
    box('drain_n', (80, .3, .1), (0, -1.65, -.04), plain('drain', '#4a4840', .7)); box('drain_s', (80, .3, .1), (0, -8.85, -.04), plain('drain', '#4a4840', .7))
    box('ground_far', (300, 300, .1), (0, 0, -.12), dirt)
    put('water_manhole_cover', (-4.0, -5.0, .005), 0, 1.0)
    # our house: porch, gate, compound wall, upper floor with balcony
    dx = (DOOR[0] + DOOR[1]) / 2
    box('porch', (3.6, 1.5, .12), (dx - .4, -.75, .06), pave)
    box('porch_step', (1.2, .3, .06), (dx, -1.62, .03), pave)
    pw = plaster('#e0d0b0', 'compound'); post = plaster('#d8c8a8', 'post')
    for x in (dx - .62, dx + .62): HR.rbox(f'gatepost{x}', (.22, .22, 1.35), (x, -1.65, .67), post, .08, sub=1)
    gate = plain('gate', '#2a4a3a', .5, .4)
    for k in range(9): cyl(f'gatebar{k}', .012, 1.0, (dx - .7 - .12 - k * .12, -1.62 - k * .03, .55), gate, v=6)       # the gate leaf, swung open
    box('compound', (6.0, .15, 1.1), (dx - .7 - 3.0, -1.65, .55), pw); box('compound2', (2.8, .15, 1.1), (dx + .7 + 1.4, -1.65, .55), pw)
    for k, x in enumerate((dx - 3.4, dx - 1.6, dx + 2.4)):
        if put('planter_pot_clay', (x, -1.45, 1.1), k * 40, 1.0) is None: cyl(f'pot{k}', .14, .22, (x, -1.45, 1.21), plain('pot', '#a85a30', .8), v=12)
        T.lib.sphere(f'plant{k}', .2, (x, -1.45, 1.4), plain('leafy', '#3a7a2a', .8)).scale = (1, 1, .8)
    ours = plaster('#efd08a', 'ours')
    x0, x1 = LIV[0] - .2, BED[1] + .2
    box('our_upper', (x1 - x0, 4.8, 3.1), ((x0 + x1) / 2, 2.25, H + 1.55), ours)          # 1st floor block over the flat
    box('our_front_low', (x1 - x0 - (LIV[1] - LIV[0] + .2), .14, H), ((LIV[1] + x1) / 2 + .05, BED[2] - .07, H / 2), ours)   # bedroom front (outside)
    box('our_band', (x1 - x0 + .1, .16, .14), ((x0 + x1) / 2, -.14, H), plaster('#e8e0d0', 'band'))
    box('our_parapet', (x1 - x0 + .1, .2, .7), ((x0 + x1) / 2, -.05, H + 3.45), plaster('#e8e0d0', 'band'))
    ext_window('our_w_up1', (-1.8, -.08, H + 1.6), 1.3, 1.15, (0, -1)); ext_window('our_w_up2', (1.0, -.08, H + 1.6), 1.1, 1.15, (0, -1))
    chajja('our_ch_door', (dx, -.02, 2.3), 1.2, (0, -1), .6); chajja('our_ch_win', ((WINF[0] + WINF[1]) / 2, -.02, 2.2), WINF[1] - WINF[0], (0, -1))
    for k in range(9): cyl(f'grillf{k}', .007, 1.1, (WINF[0] + (WINF[1] - WINF[0]) * (k + .5) / 9, -.14, 1.5), plain('grill#1c1e20', '#1c1e20', .45, .6), v=6)
    HR.rbox('our_bal', (2.6, 1.0, .14), (3.4, -.5, H + .07), mat_ph('concrete', ('concrete', 'plaster'), '#c8c0b0', scale=.5), .1, sub=1)
    for k in range(21): cyl(f'balrail{k}', .009, .85, (2.15 + k * .12, -.98, H + .55), plain('rail2', '#2a2a2a', .45, .6), v=6)
    box('balrail_top', (2.6, .05, .04), (3.4, -.98, H + .98), plain('rail2', '#2a2a2a', .45, .6))
    water_tank('our_tank', (-1.4, 2.0, H + 3.1), .55)
    C.sign('nameplate', 'Sharma\nNiwas', .6, .32, (dx - .62, -1.78, 1.05), facing=(0, -1), bg='#2a2a2a', fg='#e8d8a0', size=(500, 270), border='#c8a040', **TY.kw('playfair'))
    HR.rbox('our_ac', (.8, .3, .55), (-.4, -.17, H + .9), plain('acunit', '#ecebe6', .45), .08, sub=1)
    # the colony: houses on our side (front y -1.65 line) and across the street (front y -9.0), a few shops opposite
    cols = ['#e8c890', '#b8d8c8', '#f0b8a8', '#c8c0e8', '#f0e0a0', '#a8c8e0', '#e8a888', '#d0e0a8', '#f4d4c0', '#c4e0d0']
    r = random.Random(4); x = -30.0; k = 0
    while x < 30:
        w = r.uniform(6, 8)
        if not (x + w > LIV[0] - .6 and x < BED[1] + .6):
            rowhouse(f'nbN{k}', x, w, -.1, 1, r.choice([2, 2, 3]), r.choice(cols), 100 + k, night=night)
        x += w + .15; k += 1
    shops = {1: 'Sharma Gas Agency', 3: 'Gupta General Store', 5: 'Chai ₹10', 6: 'Mobile Repair'}
    x = -26.0; k = 0
    while x < 30:
        w = r.uniform(6, 8)
        rowhouse(f'nbS{k}', x, w, -9.0, -1, r.choice([2, 3, 3]), r.choice(cols), 200 + k, shop=shops.get(k), night=night)
        if shops.get(k, '').startswith('Sharma Gas'):
            for j in range(5):
                c_ = HR.lpg_cylinder(f'shopcyl{j}'); c_.location = (x + 1.0 + j * .42, -8.6 + (j % 2) * .1, 0)
            gas_x = x + w / 2
        if shops.get(k, '').startswith('Chai'):
            HR.rbox('chai_counter', (1.6, .6, .9), (x + w / 2, -8.2, .45), mat_ph('stallwood', ('wood', 'planks'), '#7a5a3a', scale=.4), .05, sub=1)
            put('brass_pot_01', (x + w / 2 - .4, -8.2, .9), 0, 1.0); cyl('stove', .15, .12, (x + w / 2 + .3, -8.2, .96), plain('stove', '#2a2a2a', .5, .5), v=14)
            for j in range(3): put('plastic_monobloc_chair_01', (x + .8 + j * .9, -7.5, 0), 180 + j * 25, 1.0)
            put('plastic_crate_01', (x + w - .6, -8.4, 0), 10, 1.2)
        x += w + .15; k += 1
    # poles + a tangle of wires, trees, parked stuff
    tops = [pole(f'pole{k}', x, y) for k, (x, y) in enumerate([(-9.5, -1.95), (6.8, -1.95), (18.0, -1.95), (-3.0, -8.55), (11.0, -8.55), (-20.0, -1.95)])]
    wire = plain('wire', '#1a1a1a', .6); rr = random.Random(9)
    for a, b in ((5, 0), (0, 1), (1, 2), (0, 3), (3, 4), (1, 4), (2, 4), (1, 3)):
        pa, pb = tops[a], tops[b]
        for j in range(3):
            off = Vector((rr.uniform(-.5, .5), 0, -.12 * j)); sag = rr.uniform(.5, 1.1); pts = []
            for q in range(14):
                u = q / 13; p = pa.lerp(pb, u) + off; p.z -= sag * math.sin(u * math.pi); pts.append(p)
            T.lib.tube(f'wire{a}{b}{j}', pts, .009, m=wire)
    for k, (x, y) in enumerate(((dx + .05, -1.6), (4.0, -1.0))):                   # service wires into our house
        T.lib.tube(f'svc{k}', [tops[1], Vector((x, y + .2, H + 2.6))], .006, m=wire)
    for k, (x, y, s_) in enumerate(((-6.2, -1.3, 1.0), (13.5, -1.3, .9), (-14.0, -9.4, 1.1), (22.0, -9.4, 1.0))):
        if put('tree_small_02', (x, y, 0), k * 70, s_) is None:
            cyl(f'trunk{k}', .12, 2.5, (x, y, 1.25), plain('bark', '#5a4030', .9), v=10); T.lib.sphere(f'crown{k}', 1.4, (x, y, 3.2), plain('leafy', '#3a7a2a', .8))
    put('covered_car', (-11.5, -7.3, 0), 90, 1.0)
    HR.scooter('scooter_ours', (dx + 1.85, -.45, .12), 80, '#8a1620')
    HR.scooter('scooter_nb', (-7.6, -2.4, 0), 160, '#e8e8e4', plate='DL 8C XY 0921')
    HR.scooter('scooter_shop', (16.0, -7.9, 0), 20, '#1a3a8a', plate='HR 26 DK 3307')
    for k, (x, y) in enumerate(((-9.2, -1.6), (18.3, -1.6))): put('trashbag', (x, y, 0), k * 50, 1.0)
    put('old_tyre', (7.4, -1.5, .3), 80, 1.0)


def build(night=False):
    out = interior(night); street(night)
    sun = bpy.data.objects.get('sun')
    return out
