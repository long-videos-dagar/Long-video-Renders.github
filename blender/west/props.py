"""Story props: horse (for silhouettes), revolver, gold bars, money sacks, wanted posters, lantern, pocket watch,
calendar, tumbleweed, dust puffs."""
import bpy, bmesh, math, os, random
from mathutils import Vector, Matrix
import town as T
from town import box, cyl, plain, coll


def _skin_obj(name, pts, edges, radii, m, sub=2):
    me = bpy.data.meshes.new(name); me.from_pydata(pts, edges, []); o = bpy.data.objects.new(name, me); coll('Props').objects.link(o)
    sk = o.modifiers.new('skin', 'SKIN'); sk.use_smooth_shade = True
    for v, r in zip(me.skin_vertices[0].data, radii): v.radius = (r, r * .85)
    me.skin_vertices[0].data[0].use_root = True
    sd = o.modifiers.new('sd', 'SUBSURF'); sd.levels = 1; sd.render_levels = sub
    o.data.materials.append(m); return o


def horse(name='horse', coat='#5a3420'):
    """stylised-real horse built from skin-modifier volumes; legs are separate pivots for a walk cycle"""
    m = plain('horsecoat_' + coat, coat, .6)
    root = bpy.data.objects.new(name, None); coll('Props').objects.link(root)
    pts = [(0, -.75, 1.25), (0, -.2, 1.32), (0, .45, 1.3), (0, .8, 1.22), (0, -1.05, 1.55), (0, -1.3, 1.85), (0, -1.55, 1.75), (0, -1.75, 1.5), (0, 1.05, 1.15), (0, 1.25, .85)]
    edges = [(0, 1), (1, 2), (2, 3), (0, 4), (4, 5), (5, 6), (6, 7), (3, 8), (8, 9)]
    radii = [.36, .38, .38, .33, .2, .14, .13, .1, .07, .05]
    body = _skin_obj(name + '_body', pts, edges, radii, m); body.parent = root
    mane = _skin_obj(name + '_mane', [(0, -.95, 1.72), (0, -1.2, 1.98), (0, -1.45, 2.0)], [(0, 1), (1, 2)], [.06, .07, .05], plain('mane', '#1a120c', .8)); mane.parent = root
    legs = []
    for sx, sy in ((-.17, -.7), (.17, -.7), (-.17, .65), (.17, .65)):
        piv = bpy.data.objects.new(name + '_hip', None); coll('Props').objects.link(piv); piv.parent = root; piv.location = (sx, sy, 1.12)
        up = _skin_obj(name + '_leg', [(0, 0, 0), (0, .05 if sy > 0 else -.02, -.5)], [(0, 1)], [.13, .07], m); up.parent = piv
        kn = bpy.data.objects.new(name + '_knee', None); coll('Props').objects.link(kn); kn.parent = piv; kn.location = (0, .05 if sy > 0 else -.02, -.5)
        lo = _skin_obj(name + '_shin', [(0, 0, 0), (0, 0, -.52), (0, -.05, -.6)], [(0, 1), (1, 2)], [.06, .05, .07], plain('hoof', '#1a1410', .6) if False else m); lo.parent = kn
        legs.append((piv, kn, sy > 0))
    root['legs'] = len(legs)

    def update(t, speed=1.0, loc=(0, 0, 0), yaw=0.0):
        ph = t * 1.7 * speed * math.tau
        root.location = loc; root.rotation_euler = (0, 0, yaw)
        for i, (piv, kn, back) in enumerate(legs):
            o = (0, .5, .75, .25)[i] * math.tau
            piv.rotation_euler = (.35 * math.sin(ph + o), 0, 0)
            kn.rotation_euler = (max(0.0, -.7 * math.sin(ph + o + 1.2)) * (-1 if back else 1), 0, 0)
        body_bob = .03 * math.sin(2 * ph)
        for o in root.children:
            if o.name.startswith(name + '_body') or o.name.startswith(name + '_mane'): o.location.z = body_bob
    return root, update


def revolver(name='revolver'):
    steel = plain('gunsteel', '#2a2c30', .3, 1.0); wood = plain('gungrip', '#4a2a16', .45)
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    def cube(c, s, mi):
        r = bmesh.ops.create_cube(bm, size=1, matrix=Matrix.Translation(c) @ Matrix.Diagonal((*s, 1)))
        for f in {f for v in r['verts'] for f in v.link_faces}: f.material_index = mi
    def cylr(c, r_, d, n, mi):
        res = bmesh.ops.create_cone(bm, cap_ends=True, segments=n, radius1=r_, radius2=r_, depth=d, matrix=Matrix.Translation(c) @ Matrix.Rotation(math.pi / 2, 4, 'X'))
        for f in {f for v in res['verts'] for f in v.link_faces}: f.material_index = mi
    cylr((0, .1, .0), .009, .19, 20, 0); cylr((0, -.0, -.004), .021, .045, 6, 0); cube((0, -.035, -.01), (.016, .05, .04), 0)
    r = bmesh.ops.create_cube(bm, size=1, matrix=Matrix.Translation((0, -.075, -.06)) @ Matrix.Rotation(math.radians(20), 4, 'X') @ Matrix.Diagonal((.022, .032, .085, 1)))
    for f in {f for v in r['verts'] for f in v.link_faces}: f.material_index = 1
    bm.to_mesh(me); bm.free(); o = bpy.data.objects.new(name, me); me.materials.append(steel); me.materials.append(wood)
    bv = o.modifiers.new('b', 'BEVEL'); bv.width = .002; coll('Props').objects.link(o); return o


def gold_bar(name, loc, rot=0.0):
    g = plain('gold', '#e8b040', .2, 1.0)
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=4, radius1=.17, radius2=.12, depth=.07, matrix=Matrix.Rotation(math.pi / 4, 4, 'Z') @ Matrix.Diagonal((1, .45, 1, 1)))
    bm.to_mesh(me); bm.free(); o = bpy.data.objects.new(name, me); o.location = loc; o.rotation_euler = (0, 0, rot); me.materials.append(g)
    bv = o.modifiers.new('b', 'BEVEL'); bv.width = .006; bv.segments = 2; coll('Props').objects.link(o); return o


def sack(name, loc, fill=1.0, label=True):
    m = plain('burlapp', '#8a7450', .95)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=.22, location=loc); o = bpy.context.active_object; o.name = name
    for v in o.data.vertices:
        if v.co.z > .1: v.co.x *= .45 + .3 * (1 - fill); v.co.y *= .45 + .3 * (1 - fill)
        v.co.z *= .6 + .6 * fill
    d = o.modifiers.new('d', 'DISPLACE'); tx = bpy.data.textures.new(name, 'CLOUDS'); tx.noise_scale = .05; d.texture = tx; d.strength = .02
    o.data.materials.append(m)
    for p in o.data.polygons: p.use_smooth = True
    for cc in list(o.users_collection): cc.objects.unlink(o)
    coll('Props').objects.link(o)
    if label:
        ink = plain('sackink', '#1a1410', .8)
        tx_ = T.text(name + '_lbl', '$', (loc[0], loc[1] - .21, loc[2] - .02), .16, ink, rot=(math.pi / 2, 0, 0), c='Props'); tx_.parent = o; tx_.matrix_parent_inverse = o.matrix_world.inverted()
    return o


def poster_image(path, face_png, title='WANTED', reward='$ 5,000 REWARD', name='', crime='FOR BANK ROBBERY'):
    """old paper wanted poster with an engraved-looking portrait"""
    from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter
    W, H = 900, 1260
    rng = random.Random(len(name))
    im = Image.new('RGB', (W, H), (226, 206, 160)); d = ImageDraw.Draw(im)
    for _ in range(9000):   # paper fibre and stains
        x, y = rng.randrange(W), rng.randrange(H); c = rng.randint(185, 225); d.point((x, y), fill=(c, int(c * .9), int(c * .68)))
    for _ in range(14):
        x, y, r = rng.randrange(W), rng.randrange(H), rng.randint(30, 140); d.ellipse((x - r, y - r, x + r, y + r), outline=None, fill=None)
    fb = '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'
    f1 = ImageFont.truetype(fb, 170); f2 = ImageFont.truetype(fb, 60); f3 = ImageFont.truetype(fb, 44)
    ink = (40, 26, 16)
    d.text((W / 2, 130), title, font=f1, fill=ink, anchor='mm'); d.text((W / 2, 245), 'DEAD OR ALIVE', font=f3, fill=ink, anchor='mm')
    d.rectangle((40, 40, W - 40, H - 40), outline=ink, width=8); d.rectangle((58, 58, W - 58, H - 58), outline=ink, width=3)
    if face_png and os.path.exists(face_png):
        p = Image.open(face_png).convert('L'); p = ImageOps.fit(p, (560, 620)); p = ImageOps.autocontrast(p, cutoff=2)
        p = p.filter(ImageFilter.UnsharpMask(2, 160)); sep = ImageOps.colorize(p, (40, 26, 16), (226, 206, 160))
        im.paste(sep, ((W - 560) // 2, 300)); d.rectangle(((W - 560) // 2 - 6, 294, (W + 560) // 2 + 6, 926), outline=ink, width=6)
    d.text((W / 2, 990), name, font=f2, fill=ink, anchor='mm'); d.text((W / 2, 1075), crime, font=f3, fill=ink, anchor='mm')
    d.text((W / 2, 1160), reward, font=f2, fill=(120, 30, 20), anchor='mm')
    im = im.filter(ImageFilter.GaussianBlur(.6)); im.save(path)
    return path


def poster(name, img_path, loc, rot, size=(.6, .84), curl=.0):
    m = bpy.data.materials.new(name); m.use_nodes = True; N, L = m.node_tree.nodes, m.node_tree.links; b = N['Principled BSDF']
    t = N.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(img_path, check_existing=True); L.new(t.outputs['Color'], b.inputs['Base Color']); b.inputs['Roughness'].default_value = .85
    b.inputs['Subsurface Weight'].default_value = .1
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=8, y_subdivisions=10, size=1, location=loc, rotation=rot); o = bpy.context.active_object; o.name = name
    o.scale = (size[0], size[1], 1)
    _r = random.Random(len(o.data.vertices))
    for v in o.data.vertices: v.co.z += curl * (v.co.y + .5) ** 2 * .1 + _r.uniform(0, .002)
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.uv.unwrap(); bpy.ops.object.mode_set(mode='OBJECT')
    me = o.data; uv = me.uv_layers.active
    for poly in me.polygons:
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co; uv.data[li].uv = (co.x + .5, co.y + .5)
    o.data.materials.append(m)
    for cc in list(o.users_collection): cc.objects.unlink(o)
    coll('Props').objects.link(o); return o


def lantern_prop(name, loc, energy=30):
    return T.lantern(name, loc, c='Props', energy=energy)


def tumbleweed(name, loc, r=.4):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=r * .5, location=loc); o = bpy.context.active_object; o.name = name
    mod = o.modifiers.new('tw', 'PARTICLE_SYSTEM'); st = mod.particle_system.settings
    st.type = 'HAIR'; st.count = 160; st.use_advanced_hair = True; st.hair_length = r; st.normal_factor = r / 4
    st.child_type = 'INTERPOLATED'; st.child_percent = 6; st.rendered_child_count = 6; st.kink = 'CURL'; st.kink_amplitude = .12; st.kink_frequency = 2; st.roughness_2 = .3
    st.root_radius = 1; st.tip_radius = .5; st.radius_scale = .004
    tm = plain('tumble', '#8a6a40', .9); o.data.materials.append(tm); o.show_instancer_for_render = False
    for cc in list(o.users_collection): cc.objects.unlink(o)
    coll('Props').objects.link(o); return o
