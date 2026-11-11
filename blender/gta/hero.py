"""Hand-modelled hero props for the 'Indian Middle Class Edition' set: a smooth subdivision-surface scooter, the red LPG
cylinder, the hawai chappal, the newspaper.  Local frame: front = -Y, up = +Z, origin on the ground."""
import math
import bpy, bmesh
from mathutils import Vector, Matrix
import town as T
import lib


def _obj(name, bm, mat, sub=2, parent=None, smooth=True):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = smooth
    if isinstance(mat, (list, tuple)):
        for m in mat: me.materials.append(m)
    else: me.materials.append(mat)
    o = bpy.data.objects.new(name, me); T.coll('Town').objects.link(o)
    if sub:
        s = o.modifiers.new('sub', 'SUBSURF'); s.levels = 1; s.render_levels = sub
    if parent: o.parent = parent
    return o


def loft(name, secs, mat, axis='y', n=20, sub=2, parent=None, caps=True):
    """smooth shell through superellipse sections: secs = [(pos, c1, c2, w, h, p)] - pos along `axis`, (c1, c2) the section
    centre in the other two axes (x,z for axis y; x,y for axis z), w x h its size, p the squareness (2 = ellipse, 4 = boxy)"""
    bm = bmesh.new(); rings = []
    for pos, c1, c2, w, h, p in secs:
        ring = []
        for k in range(n):
            a = math.tau * k / n; ca, sa = math.cos(a), math.sin(a)
            u = c1 + w / 2 * math.copysign(abs(ca) ** (2 / p), ca); v = c2 + h / 2 * math.copysign(abs(sa) ** (2 / p), sa)
            co = (u, pos, v) if axis == 'y' else ((u, v, pos) if axis == 'z' else (pos, u, v))
            ring.append(bm.verts.new(co))
        rings.append(ring)
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(n): bm.faces.new((r0[k], r0[(k + 1) % n], r1[(k + 1) % n], r1[k]))
    if caps:
        for r, flip in ((rings[0], True), (rings[-1], False)):
            c = bm.verts.new(sum((v.co for v in r), Vector()) / n)
            for k in range(n):
                f = (r[k], r[(k + 1) % n], c); bm.faces.new(tuple(reversed(f)) if flip else f)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _obj(name, bm, mat, sub, parent)


def rbox(name, size, loc, mat, bev=.3, parent=None, sub=2, rot=(0, 0, 0)):
    """rounded box (subdivided cube with support loops via bevel)"""
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector(size), verts=bm.verts)
    bmesh.ops.bevel(bm, geom=list(bm.edges), offset=min(size) * bev, segments=2, profile=.6, affect='EDGES')
    o = _obj(name, bm, mat, sub, parent); o.location = loc; o.rotation_euler = rot
    return o


def paint(name, col, rough=.22, metal=.35, coat=1.0):
    m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*lib.lin(col), 1); b.inputs['Roughness'].default_value = rough; b.inputs['Metallic'].default_value = metal
    for k, v in (('Coat Weight', coat), ('Coat Roughness', .05)):
        if k in b.inputs: b.inputs[k].default_value = v
    return m


def emit(name, col, strength=4.0):
    m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*lib.lin(col), 1); b.inputs['Emission Color'].default_value = (*lib.lin(col), 1)
    b.inputs['Emission Strength'].default_value = strength; b.inputs['Roughness'].default_value = .1
    return m


def wheel(name, y, root, r=.215, tw=.105, rubber=None, alloy=None):
    rubber = rubber or T.plain('rubber', '#141416', .85); alloy = alloy or paint('alloy', '#b8bcc2', .3, 1.0, .3)
    t = T.lib.torus(name + '_tyre', r - tw * .45, tw * .5, (0, y, r), rubber, rot=(0, math.pi / 2, 0), seg=40, mseg=14); t.parent = root
    t.scale = (1, 1, 1)
    rim = T.cyl(name + '_rim', r * .62, tw * .82, (0, y, r), alloy, rot=(0, math.pi / 2, 0), v=28); rim.parent = root
    hub = T.cyl(name + '_hub', r * .2, tw * 1.05, (0, y, r), paint('hub', '#2a2a2e', .4, .6, 0), rot=(0, math.pi / 2, 0), v=16); hub.parent = root
    for k in range(5):
        a = k * math.tau / 5
        sp = T.box(f'{name}_sp{k}', (tw * .95, r * .5, .028), (0, y + math.cos(a) * r * .32, r + math.sin(a) * r * .32), paint('spoke', '#9aa0a8', .3, 1.0, .2), rot=(-a + math.pi / 2, 0, 0))
        sp.parent = root
    disc = T.cyl(name + '_disc', r * .52, .006, (-tw * .58, y, r), paint('disc', '#8a8c90', .35, 1.0, 0), rot=(0, math.pi / 2, 0), v=24); disc.parent = root
    return t


def scooter(name='scooter', loc=(0, 0, 0), yaw=0.0, col='#8a1620', plate='DL 3S AB 4512'):
    """an everyday Indian 110cc scooter: smooth leg shield + apron, floorboard, rounded rear cowl, seat, handlebar with
    headlamp and mirrors, alloy wheels, centre stand, number plates"""
    root = bpy.data.objects.new(name, None); T.coll('Town').objects.link(root)
    body = paint(name + '_paint', col); dark = paint(name + '_dark', '#1a1a1e', .5, .1, .3); chrome = paint('chrome', '#d8dce0', .08, 1.0, .5)
    seatm = paint('seat', '#141414', .55, 0, .2); mat_ = T.plain('floor_mat', '#202022', .9)
    # rear body (the big rounded cowl over the engine), slightly kicked up at the tail
    loft(name + '_cowl', [(.05, 0, .40, .26, .26, 3), (.18, 0, .46, .36, .40, 3), (.40, 0, .50, .42, .46, 3.2), (.62, 0, .54, .41, .42, 3),
                          (.80, 0, .60, .33, .32, 2.8), (.92, 0, .66, .18, .18, 2.4)], body, parent=root)
    # side panel trim line + under-tray
    loft(name + '_under', [(.10, 0, .26, .22, .12, 3), (.55, 0, .30, .30, .14, 3), (.82, 0, .40, .22, .12, 3)], dark, parent=root)
    # seat: long and soft, a step for the pillion
    loft(name + '_seat', [(-.02, 0, .76, .24, .07, 3), (.08, 0, .79, .31, .11, 3.4), (.38, 0, .79, .32, .11, 3.4), (.58, 0, .82, .31, .12, 3.4),
                          (.76, 0, .82, .26, .10, 3), (.84, 0, .80, .16, .06, 2.6)], seatm, parent=root)
    grab = T.lib.torus(name + '_grab', .13, .014, (0, .80, .80), chrome, rot=(0, 0, 0), seg=24, mseg=8, arc=math.pi)
    grab.rotation_euler = (0, 0, math.pi); grab.scale = (1.15, .7, 1); grab.parent = root
    # floorboard with rubber mat
    rbox(name + '_floor', (.34, .52, .08), (0, -.17, .26), body, .25, root)
    rbox(name + '_mat', (.30, .46, .012), (0, -.17, .305), mat_, .2, root, sub=1)
    # leg shield (curved panel) + front apron, leaning back like the real thing
    loft(name + '_shield', [(.22, 0, -.36, .34, .16, 3.4), (.30, 0, -.42, .46, .16, 3.4), (.55, 0, -.48, .46, .17, 3.4), (.80, 0, -.53, .40, .16, 3.2),
                            (.95, 0, -.56, .30, .15, 3), (1.02, 0, -.57, .20, .12, 2.6)], body, axis='z', parent=root)
    badge = T.lib.sphere(name + '_badge', .03, (0, -.645, .78), chrome, seg=16, rings=8); badge.scale = (1.4, .3, 1); badge.parent = root
    for sd in (-1, 1):                                                 # front indicators on the apron
        rbox(f'{name}_find{sd}', (.06, .02, .03), (sd * .13, -.61, .9), emit('indicator', '#ff9a20', .6), .4, root)
    loft(name + '_tunnel', [(.30, 0, -.34, .14, .10, 3), (.50, 0, -.37, .12, .08, 3)], body, axis='z', parent=root)
    # handlebar cover with headlamp, speedo pod, grips, levers, mirrors
    hb = rbox(name + '_hbar', (.54, .20, .14), (0, -.58, 1.07), body, .48, root)
    loft(name + '_neck', [(1.0, 0, -.57, .16, .12, 2.6), (1.06, 0, -.58, .2, .15, 2.6)], body, axis='z', parent=root)
    rbox(name + '_hbtop', (.24, .14, .03), (0, -.56, 1.135), dark, .3, root)
    lamp = rbox(name + '_lamp', (.20, .03, .09), (0, -.685, 1.06), emit('headlamp', '#fff6e0', 6.0), .35, root)
    for sd in (-1, 1):
        g = T.cyl(f'{name}_grip{sd}', .02, .13, (sd * .36, -.6, 1.06), dark, rot=(0, math.pi / 2, 0), v=12); g.parent = root
        lv = T.box(f'{name}_lever{sd}', (.14, .012, .012), (sd * .32, -.66, 1.08), chrome, rot=(0, 0, sd * .2)); lv.parent = root
        st = T.cyl(f'{name}_mst{sd}', .007, .16, (sd * .21, -.56, 1.2), chrome, rot=(0, sd * .3, 0), v=8); st.parent = root
        mi = T.lib.sphere(f'{name}_mir{sd}', .055, (sd * .24, -.56, 1.29), dark, seg=20, rings=10); mi.scale = (1.25, .35, .8); mi.parent = root
        ind = rbox(f'{name}_ind{sd}', (.05, .03, .025), (sd * .23, -.66, 1.03), emit('indicator', '#ff9a20', .6), .4, root)
    # front fork + fender + wheel
    for sd in (-1, 1):
        f = T.cyl(f'{name}_fork{sd}', .022, .62, (sd * .07, -.66, .55), chrome, rot=(-.32, 0, 0), v=12); f.parent = root
    bm = bmesh.new(); prev = None
    for k in range(15):                                                # mudguard: a curved strip hugging the top of the tyre
        a = math.radians(15 + 140 * k / 14); y_ = -.74 - math.cos(a) * .265; z_ = .215 + math.sin(a) * .265; wv = .065 + .01 * math.sin(a)
        cur = [bm.verts.new((-wv, y_, z_)), bm.verts.new((wv, y_, z_))]
        if prev: bm.faces.new((prev[0], prev[1], cur[1], cur[0]))
        prev = cur
    fen = _obj(name + '_fender', bm, body, 2, root); so = fen.modifiers.new('sol', 'SOLIDIFY'); so.thickness = .012; fen.modifiers.move(1, 0)
    wheel(name + '_fw', -.74, root)
    wheel(name + '_rw', .58, root)
    # engine/swing arm (left) and exhaust (right)
    rbox(name + '_engine', (.14, .42, .18), (-.12, .48, .28), paint('engine', '#4a4c50', .5, .7, 0), .3, root)
    ex = T.cyl(name + '_exhaust', .055, .40, (.15, .55, .25), paint('muffler', '#2a2a2c', .4, .8, .2), rot=(math.pi / 2 - .12, 0, 0), v=16); ex.parent = root
    exs = rbox(name + '_exshield', (.02, .30, .07), (.21, .55, .27), chrome, .4, root)
    # centre stand
    for sd in (-1, 1):
        s_ = T.cyl(f'{name}_stand{sd}', .012, .2, (sd * .12, .22, .09), dark, rot=(.25, 0, 0), v=8); s_.parent = root
    # tail lamp + number plates
    rbox(name + '_tail', (.16, .04, .06), (0, .93, .70), emit('taillamp', '#d8101a', 2.0), .4, root)
    import city as C
    import typo as TY
    p1 = C.sign(name + '_plateR', plate.replace(' ', ' ', 1), .20, .06, (0, .925, .55), facing=(0, 1), bg='#f4f4f0', fg='#111', size=(600, 180), font_scale=.6, border='#111', **TY.kw('oswald_b')); p1.parent = root
    p2 = C.sign(name + '_plateF', plate, .16, .05, (0, -.70, .90), facing=(0, -1), bg='#f4f4f0', fg='#111', size=(600, 180), font_scale=.6, border='#111', **TY.kw('oswald_b')); p2.parent = root
    root.location = loc; root.rotation_euler = (0, 0, math.radians(yaw))
    return root


def lpg_cylinder(name='lpg', scale=1.0):
    """14.2 kg domestic LPG cylinder: red body, collar guard with handle cut-outs, foot ring, valve + pressure regulator cap"""
    root = bpy.data.objects.new(name, None); T.coll('Town').objects.link(root)
    red = paint(name + '_red', '#c4161a', .35, .15, .6); grey = paint(name + '_g', '#9a9ca0', .45, .8, 0)
    loft(name + '_body', [(.03, 0, 0, .25, .25, 2), (.06, 0, 0, .31, .31, 2), (.12, 0, 0, .32, .32, 2), (.52, 0, 0, .32, .32, 2), (.60, 0, 0, .30, .30, 2),
                          (.65, 0, 0, .20, .20, 2), (.67, 0, 0, .09, .09, 2)], red, axis='z', n=28, parent=root)
    ft = T.lib.torus(name + '_foot', .135, .018, (0, 0, .03), red, seg=32, mseg=8); ft.scale = (1, 1, 1.6); ft.parent = root
    # collar (open ring with two handle holes)
    bm = bmesh.new(); n = 48; lo = []; hi = []
    for k in range(n):
        a = math.tau * k / n; d = min(abs(math.sin(a) - 1), abs(math.sin(a) + 1))
        zt = .83 - .06 * max(0.0, 1 - d / .25) ** .5                  # two dips = the carry handles
        lo.append(bm.verts.new((math.cos(a) * .115, math.sin(a) * .115, .64))); hi.append(bm.verts.new((math.cos(a) * .115, math.sin(a) * .115, zt)))
    for k in range(n): bm.faces.new((lo[k], lo[(k + 1) % n], hi[(k + 1) % n], hi[k]))
    o = _obj(name + '_collar', bm, red, 1, root, smooth=True); s = o.modifiers.new('sol', 'SOLIDIFY'); s.thickness = .009; o.modifiers.move(1, 0)
    T.cyl(name + '_valve', .025, .05, (0, 0, .70), T.plain('brass', '#c8a040', .3, 1.0), v=14).parent = root
    cap = T.lib.sphere(name + '_cap', .04, (0, 0, .745), T.plain('capblack', '#18181a', .4), seg=16, rings=8); cap.scale = (1, 1, .55); cap.parent = root
    import city as C
    import typo as TY
    lab = C.sign(name + '_label', 'LPG', .09, .05, (0, -.163, .4), facing=(0, -1), bg='#c4161a', fg='#f4f0e8', size=(240, 130), font_scale=.7, **TY.kw('oswald_b')); lab.parent = root
    root.scale = (scale,) * 3; root['s'] = scale
    return root


def chappal(name='chappal'):
    """hawai chappal: white sole with blue rim, blue V straps"""
    root = bpy.data.objects.new(name, None); T.coll('Town').objects.link(root)
    pts = [(0, -.13), (.045, -.12), (.05, -.06), (.042, .0), (.045, .07), (.04, .11), (0, .125), (-.04, .11), (-.045, .07), (-.042, 0), (-.05, -.06), (-.045, -.12)]
    def sole(nm, z0, z1, m):
        bm = bmesh.new(); lo = [bm.verts.new((x, y, z0)) for x, y in pts]; hi = [bm.verts.new((x, y, z1)) for x, y in pts]
        bm.faces.new(lo[::-1]); bm.faces.new(hi)
        for k in range(len(pts)): bm.faces.new((lo[k], lo[(k + 1) % len(pts)], hi[(k + 1) % len(pts)], hi[k]))
        return _obj(nm, bm, m, 2, root)
    sole(name + '_bot', 0, .012, paint('chblue', '#2a4ab0', .6, 0, 0)); sole(name + '_top', .012, .022, paint('chwhite', '#f2f2ee', .7, 0, 0))
    for sd in (-1, 1):
        pts3 = [Vector((0, -.07, .022)), Vector((sd * .02, -.05, .05)), Vector((sd * .04, -.0, .045)), Vector((sd * .045, .03, .022))]
        T.lib.tube(f'{name}_strap{sd}', pts3, .008, m=paint('chstrap', '#2a4ab0', .5, 0, 0)).parent = root
    return root
