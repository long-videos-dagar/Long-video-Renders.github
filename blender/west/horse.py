"""Realistic horse (bay with black points), built from anatomical cross-sections and driven by an equine gait model.

Body + neck + head are lofted from measured proportions (about 1.55 m at the withers), merged with a voxel remesh into
one watertight surface and deformed by a small armature (neck/head nod). Legs are jointed segments (forearm/gaskin,
cannon, pastern, hoof) solved with IK so hooves stay planted during stance (no sliding).

Gait: walk = 4-beat lateral sequence (LH, LF, RH, RF at phases 0, .25, .5, .75), duty factor .62; trot = diagonal pairs.
Head nods twice per stride at the walk. Tack: saddle, blanket, girth, stirrups, bridle, reins.

    h = Horse('horse'); h.update(t, loc, yaw, gait='walk', speed=1.5)
    h.seat()  -> world matrix of the saddle seat (for the rider)
"""
import bpy, bmesh, math
from mathutils import Vector, Matrix


def _coll(name='Props'):
    c = bpy.data.collections.get(name)
    if not c: c = bpy.data.collections.new(name); bpy.context.scene.collection.children.link(c)
    return c


def _own(o, parent=None):
    for c in list(o.users_collection): c.objects.unlink(o)
    _coll().objects.link(o)
    if parent is not None: o.parent = parent
    return o


def hexc(h):
    h = h.lstrip('#'); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple((x / 12.92 if x <= .04045 else ((x + .055) / 1.055) ** 2.4) for x in c) + (1,)


def coat_mat(name, col='#5a3018', dark='#1c120c', points=False):
    m = bpy.data.materials.new(name); m.use_nodes = True; N, L = m.node_tree.nodes, m.node_tree.links; b = N['Principled BSDF']
    tc = N.new('ShaderNodeTexCoord')
    n1 = N.new('ShaderNodeTexNoise'); n1.inputs['Scale'].default_value = 4; n1.inputs['Detail'].default_value = 8; L.new(tc.outputs['Object'], n1.inputs['Vector'])
    n2 = N.new('ShaderNodeTexNoise'); n2.inputs['Scale'].default_value = 300; n2.inputs['Detail'].default_value = 2; L.new(tc.outputs['Object'], n2.inputs['Vector'])
    ramp = N.new('ShaderNodeValToRGB'); c0 = hexc(col)
    ramp.color_ramp.elements[0].color = tuple(x * .7 for x in c0[:3]) + (1,); ramp.color_ramp.elements[1].color = tuple(min(1, x * 1.25) for x in c0[:3]) + (1,)
    L.new(n1.outputs['Fac'], ramp.inputs['Fac']); col_out = ramp.outputs['Color']
    if points:      # black lower legs (bay horse) fading in above the knee
        gz = N.new('ShaderNodeNewGeometry'); sep = N.new('ShaderNodeSeparateXYZ'); L.new(gz.outputs['Position'], sep.inputs[0])
        oi = N.new('ShaderNodeObjectInfo'); so = N.new('ShaderNodeSeparateXYZ'); L.new(oi.outputs['Location'], so.inputs[0])
        rel = N.new('ShaderNodeMath'); rel.operation = 'SUBTRACT'; L.new(sep.outputs['Z'], rel.inputs[0]); L.new(so.outputs['Z'], rel.inputs[1])
        mr = N.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = -.05; mr.inputs['From Max'].default_value = -.3; L.new(rel.outputs[0], mr.inputs['Value'])
        mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; L.new(mr.outputs[0], mx.inputs['Factor']); L.new(col_out, mx.inputs['A']); mx.inputs['B'].default_value = hexc(dark); col_out = mx.outputs['Result']
    L.new(col_out, b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = .62; b.inputs['Sheen Weight'].default_value = .35; b.inputs['Sheen Roughness'].default_value = .5
    b.inputs['Coat Weight'].default_value = .0
    bp = N.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = .08; bp.inputs['Distance'].default_value = .002; L.new(n2.outputs['Fac'], bp.inputs['Height']); L.new(bp.outputs[0], b.inputs['Normal'])
    return m


def plain(name, col, rough=.6, metal=0.0):
    m = bpy.data.materials.get(name)
    if m: return m
    m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = hexc(col); b.inputs['Roughness'].default_value = rough; b.inputs['Metallic'].default_value = metal
    return m


def hair_mat(name, melanin=.95):
    m = bpy.data.materials.new(name); m.use_nodes = True; N, L = m.node_tree.nodes, m.node_tree.links; N.clear()
    o = N.new('ShaderNodeOutputMaterial'); h = N.new('ShaderNodeBsdfHairPrincipled'); L.new(h.outputs[0], o.inputs[0])
    try: h.parametrization = 'MELANIN'
    except Exception: pass
    h.inputs['Melanin'].default_value = melanin; h.inputs['Melanin Redness'].default_value = .2; h.inputs['Roughness'].default_value = .35
    return m


# ---------------------------------------------------------------- lofting
def loft(name, sections, n=28, cap=True, exp=2.0):
    """sections: [(center, right, up, half_width, half_height_up, half_height_down)]"""
    me = bpy.data.meshes.new(name); bm = bmesh.new(); rings = []
    for c, r, u, w, hu, hd in sections:
        ring = []
        for k in range(n):
            a = k / n * math.tau; ca, sa = math.cos(a), math.sin(a)
            x = math.copysign(abs(ca) ** (2 / exp), ca) * w; y = math.copysign(abs(sa) ** (2 / exp), sa) * (hu if sa > 0 else hd)
            ring.append(bm.verts.new(c + r * x + u * y))
        rings.append(ring)
    for a, b in zip(rings, rings[1:]):
        for k in range(n): bm.faces.new((a[k], a[(k + 1) % n], b[(k + 1) % n], b[k]))
    if cap:
        for ring in (rings[0], rings[-1]):
            c = bm.verts.new(sum((v.co for v in ring), Vector()) / n)
            for k in range(n): bm.faces.new((ring[k], ring[(k + 1) % n], c))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free(); o = bpy.data.objects.new(name, me); _coll().objects.link(o)
    for p in me.polygons: p.use_smooth = True
    return o


def curve_sections(pts, prof):
    out = []
    for i, (p, (w, hu, hd)) in enumerate(zip(pts, prof)):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        r = Vector((1, 0, 0)); u = t.cross(r).normalized()
        if u.z < 0: u = -u
        out.append((p, r, u, w, hu, hd))
    return out


def smooth_pts(ctrl, n):
    P = [ctrl[0]] + ctrl + [ctrl[-1]]; out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(n):
            t = k / n
            out.append(.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(ctrl[-1]); return out


def interp(prof, n):
    out = []
    for i in range(len(prof) - 1):
        for k in range(n):
            u = k / n; out.append(tuple(a + (b - a) * u for a, b in zip(prof[i], prof[i + 1])))
    out.append(prof[-1]); return out


def _apply_all(o):
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)


class Horse:
    GAITS = {'walk': dict(T=1.12, duty=.62, ph=(0.0, .25, .5, .75), lift=(.13, .11), bob=.018),
             'trot': dict(T=.72, duty=.45, ph=(0.0, .5, .5, 0.0), lift=(.17, .14), bob=.05)}

    def __init__(self, name='horse', coat='#5a3018'):
        self.name = name
        self.root = bpy.data.objects.new(name, None); _coll().objects.link(self.root)
        self.cm = coat_mat(name + '_coat', coat); self.lm = coat_mat(name + '_legs', coat)
        self._body(); self._legs(); self._hair(); self._tack()

    def _body(self):
        n = self.name
        # trunk along Y (forward is -Y): (y, top z, bottom z, half width)
        T = [(.93, 1.40, 1.22, .05), (.88, 1.47, 1.05, .16), (.74, 1.52, .98, .22), (.55, 1.53, 1.0, .25), (.32, 1.49, .97, .27), (.08, 1.46, .92, .29),
             (-.18, 1.47, .89, .29), (-.40, 1.53, .88, .27), (-.56, 1.58, .9, .24), (-.70, 1.52, .95, .2), (-.82, 1.4, 1.0, .17), (-.92, 1.27, 1.05, .12), (-.97, 1.17, 1.1, .05)]
        T = [(y * .86 - .02, tt, b, w) for (y, tt, b, w) in T]; T = interp(T, 4)
        body = loft(n + '_trunk', [(Vector((0, y, (t + b) / 2)), Vector((1, 0, 0)), Vector((0, 0, 1)), w, (t - b) / 2, (t - b) / 2) for (y, t, b, w) in T], n=32, exp=2.3)
        nc = [Vector((0, -.5, 1.30)), Vector((0, -.7, 1.44)), Vector((0, -.88, 1.64)), Vector((0, -1.0, 1.84)), Vector((0, -1.08, 2.0))]
        nprof = [(.2, .36, .32), (.16, .27, .26), (.12, .2, .21), (.095, .13, .16), (.08, .09, .11)]
        neck = loft(n + '_neck', curve_sections(smooth_pts(nc, 4), interp(nprof, 4)), n=28, exp=2.2)
        hc = [Vector((0, -1.06, 2.02)), Vector((0, -1.18, 1.96)), Vector((0, -1.33, 1.82)), Vector((0, -1.46, 1.67)), Vector((0, -1.54, 1.57)), Vector((0, -1.58, 1.52))]
        hprof = [(.085, .08, .12), (.1, .09, .14), (.085, .07, .1), (.065, .06, .075), (.07, .06, .07), (.055, .04, .045)]
        head = loft(n + '_head', curve_sections(smooth_pts(hc, 4), interp(hprof, 4)), n=28, exp=2.4)
        parts = [body, neck, head]
        for s in (-1, 1):
            bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=(s * .055, -1.21, 1.88)); j = bpy.context.active_object; j.scale = (.054, .09, .09); parts.append(_own(j))
            for loc_, sc in (((s * .1, -.72, 1.12), (.11, .1, .18)), ((s * .19, .5, 1.22), (.11, .24, .26)), ((s * .17, -.52, 1.25), (.1, .15, .28)), ((s * .16, .45, .98), (.09, .14, .14)), ((s * .14, -.5, 1.0), (.085, .11, .12))):
                bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=loc_); m_ = bpy.context.active_object; m_.scale = sc; parts.append(_own(m_))
        for o in parts: _apply_all(o)
        bpy.ops.object.select_all(action='DESELECT')
        for o in parts: o.select_set(True)
        bpy.context.view_layer.objects.active = body; bpy.ops.object.join()
        rm = body.modifiers.new('rm', 'REMESH'); rm.mode = 'VOXEL'; rm.voxel_size = .012; bpy.ops.object.modifier_apply(modifier='rm')
        sm = body.modifiers.new('sm', 'SMOOTH'); sm.iterations = 14; sm.factor = .7; bpy.ops.object.modifier_apply(modifier='sm')
        body.name = n + '_body'; body.data.materials.clear(); body.data.materials.append(self.cm)
        for p in body.data.polygons: p.use_smooth = True
        # armature: body + neck + head with smooth distance-based weights
        arm = bpy.data.armatures.new(n + '_arm'); ao = bpy.data.objects.new(n + '_rig', arm); _coll().objects.link(ao); ao.parent = self.root
        bpy.context.view_layer.objects.active = ao; bpy.ops.object.mode_set(mode='EDIT')
        b0 = arm.edit_bones.new('body'); b0.head = (0, .8, 1.25); b0.tail = (0, -.6, 1.25)
        b1 = arm.edit_bones.new('neck'); b1.head = (0, -.55, 1.32); b1.tail = (0, -1.03, 1.95); b1.parent = b0
        b2 = arm.edit_bones.new('head'); b2.head = (0, -1.03, 1.95); b2.tail = (0, -1.53, 1.55); b2.parent = b1
        bpy.ops.object.mode_set(mode='OBJECT')
        gb, gn, gh = (body.vertex_groups.new(name=k) for k in ('body', 'neck', 'head'))
        for v in body.data.vertices:
            p = v.co
            u = max(0.0, min(1.0, (-.58 - p.y) / .25 + (p.z - 1.45) / .6))
            hz = max(0.0, min(1.0, ((-1.0 - p.y) / .12 + (1.95 - p.z) / .3) * .5)) * (1 if p.z > 1.4 else 0)
            gb.add([v.index], 1 - u, 'REPLACE')
            if u > 0: gn.add([v.index], u * (1 - hz), 'REPLACE')
            if hz > 0: gh.add([v.index], u * hz, 'REPLACE')
        md = body.modifiers.new('arm', 'ARMATURE'); md.object = ao; body.parent = ao
        sd = body.modifiers.new('sd', 'SUBSURF'); sd.levels = 0; sd.render_levels = 1
        self.body, self.rig = body, ao
        # eyes, nostrils, ears ride on the head bone
        eye = plain('horse_eye', '#0a0806', .05); nos = plain('nostril', '#050403', .8)
        for s in (-1, 1):
            bpy.ops.mesh.primitive_uv_sphere_add(radius=.026, location=(s * .088, -1.30, 1.86)); e = _own(bpy.context.active_object); e.data.materials.append(eye)
            bpy.ops.mesh.primitive_uv_sphere_add(radius=.016, location=(s * .03, -1.595, 1.53)); ns = _own(bpy.context.active_object); ns.scale = (.6, .5, 1); ns.data.materials.append(nos)
            bpy.ops.mesh.primitive_cone_add(vertices=12, radius1=.05, radius2=.008, depth=.15, location=(s * .065, -1.08, 2.12), rotation=(math.radians(-15), s * math.radians(14), 0))
            ear = _own(bpy.context.active_object); ear.scale = (.75, 1.0, 1.0); ear.data.materials.append(self.cm)
            for o in (e, ns, ear): self._on_head(o)

    def _on_head(self, o):
        arm = self.rig.data; bpy.context.view_layer.update(); mw = o.matrix_world.copy()
        o.parent = self.rig; o.parent_type = 'BONE'; o.parent_bone = 'head'
        bpy.context.view_layer.update(); o.matrix_world = mw

    def _seg(self, name, r0, r1, length, m, n=16, bulge=0.0, depth=1.0):
        secs = []
        for k in range(9):
            u = k / 8; r = r0 + (r1 - r0) * u + bulge * math.sin(math.pi * u) ** 2
            secs.append((Vector((0, 0, -length * u)), Vector((1, 0, 0)), Vector((0, 1, 0)), r * .85, r * depth, r * depth))
        o = loft(name, secs, n=n, exp=2.2); o.data.materials.append(m)
        sd = o.modifiers.new('sd', 'SUBSURF'); sd.levels = 0; sd.render_levels = 1
        return o

    def _legs(self):
        n = self.name; lm = self.lm; hoof = plain('hoof', '#1a1612', .45); dk = coat_mat(n + '_points', '#1e140e')
        self.legs = []
        for side in (-1, 1):
            for fore in (True, False):
                if fore:
                    top = Vector((side * .15, -.5, 1.0)); L1, L2, L3 = .52, .33, .18
                    a = self._seg(f'{n}_fa{side}', .095, .042, L1, lm, bulge=.01, depth=1.1)
                else:
                    top = Vector((side * .17, .42, .98)); L1, L2, L3 = .46, .44, .18
                    a = self._seg(f'{n}_ga{side}', .11, .042, L1, lm, bulge=.015, depth=1.35)
                b = self._seg(f'{n}_ca{side}{int(fore)}', .042, .036, L2, dk, depth=1.15)
                c = self._seg(f'{n}_pa{side}{int(fore)}', .036, .042, L3 - .07, dk)
                bpy.ops.mesh.primitive_uv_sphere_add(radius=.05); kj = _own(bpy.context.active_object); kj.scale = (.9, 1.1, 1.0); kj.data.materials.append(dk)
                bpy.ops.mesh.primitive_uv_sphere_add(radius=.045); fj = _own(bpy.context.active_object); fj.data.materials.append(dk)
                bpy.ops.mesh.primitive_cone_add(vertices=24, radius1=.068, radius2=.048, depth=.075); hf = _own(bpy.context.active_object); hf.data.materials.append(hoof)
                for o in (a, b, c, kj, fj, hf):
                    o.parent = self.rig
                    for p in o.data.polygons: p.use_smooth = True
                self.legs.append(dict(side=side, fore=fore, top=top, L1=L1, L2=L2, L3=L3, a=a, b=b, c=c, kj=kj, fj=fj, hf=hf))

    def _hair(self):
        hm = hair_mat(self.name + '_hairm'); b = self.body; b.data.materials.append(hm)
        def ps(obj, name, test, count, length, down, tang=0.0, children=20, clump=.4, normal=.3, sidex=0.0, radius=.0006, mat=None):
            if test is not None:
                idx = [v.index for v in obj.data.vertices if test(v.co)]
                if not idx: print('no verts for', name); return
                g = obj.vertex_groups.new(name=name); g.add(idx, 1.0, 'REPLACE')
            md = obj.modifiers.new(name, 'PARTICLE_SYSTEM'); s = md.particle_system; st = s.settings
            st.type = 'HAIR'; st.count = count; st.hair_length = length; st.use_advanced_hair = True; st.emit_from = 'FACE'
            k = length / 4 / math.sqrt(normal ** 2 + down ** 2 + tang ** 2)
            k = length / 4 / math.sqrt(normal ** 2 + down ** 2 + tang ** 2 + sidex ** 2)
            st.normal_factor = normal * k; st.object_align_factor = (sidex * k, 0, -down * k); st.tangent_factor = tang * k
            st.child_type = 'INTERPOLATED'; st.child_percent = 2; st.rendered_child_count = children; st.clump_factor = clump
            st.roughness_1 = .004; st.roughness_endpoint = .02
            st.root_radius = 1; st.tip_radius = .3; st.radius_scale = radius; st.material_slot = (mat or hm).name; st.render_step = 3
            if test is not None: s.vertex_group_density = name
            # keep the hair before the subdivision so it follows the surface
            while obj.modifiers.find(name) > obj.modifiers.find('sd') and obj.modifiers.find('sd') >= 0:
                bpy.context.view_layer.objects.active = obj; bpy.ops.object.modifier_move_up(modifier=name)
        ps(b, 'mane', lambda p: -1.08 < p.y < -.5 and abs(p.x) < .045 and p.z > 1.5 + (-.5 - p.y) * .9, 1400, .26, .7, sidex=.6, normal=.5, clump=.6, children=24)
        fm = coat_mat(self.name + '_furm', '#5a3018'); b.data.materials.append(fm)
        ps(b, 'fur', None, 70000, .014, .15, tang=.6, children=3, clump=0.0, normal=.25, radius=.00025, mat=fm)
        ps(b, 'forelock', lambda p: -1.14 < p.y < -1.04 and p.z > 2.0 and abs(p.x) < .05, 120, .16, .6, tang=.3)
        bpy.ops.mesh.primitive_cone_add(vertices=16, radius1=.06, radius2=.03, depth=.35, location=(0, .82, 1.22), rotation=(math.radians(-25), 0, 0))
        dock = _own(bpy.context.active_object, self.rig); dock.data.materials.append(self.cm); dock.data.materials.append(hm)
        md = dock.modifiers.new('tail', 'PARTICLE_SYSTEM'); st = md.particle_system.settings
        st.type = 'HAIR'; st.count = 500; st.hair_length = .75; st.use_advanced_hair = True; st.normal_factor = .02; st.object_align_factor = (0, .03, -.18)
        st.child_type = 'INTERPOLATED'; st.child_percent = 2; st.rendered_child_count = 30; st.clump_factor = .2; st.roughness_1 = .01; st.roughness_2 = .02; st.roughness_endpoint = .05
        st.root_radius = 1; st.tip_radius = .3; st.radius_scale = .0007; st.material_slot = hm.name; st.render_step = 3
        self.tail = dock

    def _tack(self):
        lea = plain('saddle_leather', '#4a2a16', .45); dark = plain('tack_dark', '#24160e', .5); blanket = plain('blanket', '#8a2a20', .9); steel = plain('tack_steel', '#8a8a88', .3, 1.0)
        sd = loft(self.name + '_saddle', [(Vector((0, y, z)), Vector((1, 0, 0)), Vector((0, 0, 1)), w, .04, .06) for (y, z, w) in
                                          [(-.42, 1.61, .14), (-.3, 1.585, .2), (-.12, 1.56, .22), (.05, 1.57, .22), (.17, 1.6, .2), (.24, 1.66, .15)]], n=24, exp=3.0)
        sd.data.materials.append(lea)
        bl = loft(self.name + '_blanket', [(Vector((0, y, 1.53 + (.03 if y < -.3 else 0))), Vector((1, 0, 0)), Vector((0, 0, 1)), w, .03, .16) for (y, w) in ((-.46, .2), (-.36, .3), (-.1, .31), (.14, .3), (.24, .2))], n=24, exp=3.0)
        bl.data.materials.append(blanket)
        bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=.025, depth=.12, location=(0, -.4, 1.7)); hn = _own(bpy.context.active_object); hn.data.materials.append(lea)
        parts = [sd, bl, hn]
        for s in (-1, 1):
            bpy.ops.mesh.primitive_cube_add(size=1, location=(s * .27, -.08, 1.3)); f = _own(bpy.context.active_object); f.scale = (.01, .12, .42); f.rotation_euler = (0, s * math.radians(6), 0); f.data.materials.append(lea)
            bpy.ops.mesh.primitive_torus_add(major_radius=.07, minor_radius=.012, location=(s * .29, -.08, 1.0), rotation=(0, math.pi / 2, 0)); st = _own(bpy.context.active_object); st.data.materials.append(dark)
            parts += [f, st]
        bpy.ops.mesh.primitive_torus_add(major_radius=1, minor_radius=.03, location=(0, -.32, 1.24), rotation=(math.pi / 2, 0, math.pi / 2)); g = _own(bpy.context.active_object); g.scale = (.31, .35, 1); g.data.materials.append(dark); parts.append(g)
        for o in parts:
            o.parent = self.rig
            for p in o.data.polygons: p.use_smooth = True
        hb = []
        for loc_, rot, sc in (((0, -1.48, 1.64), (math.radians(40), 0, 0), (.085, .075, 1)), ((0, -1.15, 2.02), (math.radians(-35), 0, 0), (.1, .09, 1))):
            bpy.ops.mesh.primitive_torus_add(major_radius=1, minor_radius=.012, location=loc_, rotation=rot); t = _own(bpy.context.active_object); t.scale = sc; t.data.materials.append(dark); hb.append(t)
        rings = []
        for s in (-1, 1):
            bpy.ops.mesh.primitive_torus_add(major_radius=.02, minor_radius=.006, location=(s * .075, -1.5, 1.6), rotation=(0, math.pi / 2, 0)); r = _own(bpy.context.active_object); r.data.materials.append(steel); hb.append(r); rings.append(r)
        for o in hb: self._on_head(o)
        self.bit = rings
        cu = bpy.data.curves.new(self.name + '_reins', 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = .006
        for k in range(2): sp = cu.splines.new('BEZIER'); sp.bezier_points.add(1)
        self.reins = bpy.data.objects.new(self.name + '_reins', cu); self.reins.data.materials.append(dark); _coll().objects.link(self.reins)
        self.rein_target = None

    # ---- motion
    def seat(self):
        return self.rig.matrix_world @ Matrix.Translation((0, -.05, 1.66))

    def update(self, t, loc, yaw, gait='walk', speed=1.5, head_turn=0.0):
        G = self.GAITS[gait]; T = G['T']; duty = G['duty']; S = speed * T * duty; ph0 = t / T
        bob = G['bob'] * math.cos(4 * math.pi * ph0 + .6)
        self.root.location = Vector(loc); self.root.rotation_euler = (0, 0, yaw)
        self.rig.location = (0, 0, bob)
        self.rig.rotation_euler = (math.radians(.8) * math.sin(2 * math.pi * ph0), math.radians(1.2) * math.sin(2 * math.pi * ph0 + 1), math.radians(1.5) * math.sin(2 * math.pi * ph0))
        pb = self.rig.pose.bones
        nod = math.radians(4.5 if gait == 'walk' else 2) * math.sin(4 * math.pi * ph0 + 1.2)
        pb['neck'].rotation_mode = 'XYZ'; pb['neck'].rotation_euler = (nod, 0, head_turn * .6)
        pb['head'].rotation_mode = 'XYZ'; pb['head'].rotation_euler = (-nod * .6, 0, head_turn * .4)
        self.tail.rotation_euler = (math.radians(-25 + 4 * math.sin(2 * math.pi * ph0)), 0, math.radians(6 * math.sin(2 * math.pi * ph0 + .5)))
        order = {(-1, False): 0, (-1, True): 1, (1, False): 2, (1, True): 3}       # LH, LF, RH, RF
        for L in self.legs:
            ph = (ph0 + G['ph'][order[(L['side'], L['fore'])]]) % 1.0
            lift = G['lift'][0 if L['fore'] else 1]; y0 = L['top'].y + (-.02 if L['fore'] else .1)
            if ph < duty:
                u = ph / duty; hy = y0 - S / 2 + S * u; hz = 0.0; tilt = max(0.0, (u - .82) / .18) * math.radians(35); swing = False
            else:
                u = (ph - duty) / (1 - duty); e = .5 - .5 * math.cos(math.pi * u)
                hy = y0 + S / 2 - S * e; hz = lift * math.sin(math.pi * u) ** 1.2
                tilt = math.radians(35) * (1 - u) ** 2 + math.radians(-10) * math.sin(math.pi * u); swing = True
            hoof = Vector((L['side'] * (.13 if L['fore'] else .14), hy, hz - bob))
            self._solve(L, hoof, tilt, u, swing)
        if self.rein_target is not None:
            bpy.context.view_layer.update(); tgt = Vector(self.rein_target)
            for sp, ring in zip(self.reins.data.splines, self.bit):
                a = ring.matrix_world.translation; mid = (a + tgt) / 2 + Vector((0, 0, -.12))
                p0, p1 = sp.bezier_points
                p0.co = a; p1.co = tgt; p0.handle_left = a; p0.handle_right = mid; p1.handle_left = mid; p1.handle_right = tgt

    def _solve(self, L, hoof, tilt, u, swing):
        top = L['top']; L1, L2, L3 = L['L1'], L['L2'], L['L3']
        pdir = Matrix.Rotation(-tilt, 3, 'X') @ Vector((0, .5, .87)).normalized()
        if swing: pdir = Matrix.Rotation(-math.radians(55) * math.sin(math.pi * u), 3, 'X') @ pdir
        fet = hoof + Vector((0, 0, .04)) + pdir * (L3 - .04)
        d = fet - top; dist = min(d.length, L1 + L2 - 1e-4); dn = d.normalized()
        ca = (L1 * L1 + dist * dist - L2 * L2) / (2 * L1 * dist); ang = math.acos(max(-1, min(1, ca)))
        # carpus (fore) folds backward so the joint points forward; hock (hind) points backward
        side = Vector((1, 0, 0))
        k1 = Matrix.Rotation(-ang if L['fore'] else ang, 3, side) @ dn
        knee = top + k1 * L1
        self._place(L['a'], top, knee); self._place(L['b'], knee, fet); self._place(L['c'], fet, hoof + Vector((0, 0, .07)))
        L['kj'].location = knee; L['fj'].location = fet
        L['hf'].location = hoof + Vector((0, -.012, .037)); L['hf'].rotation_euler = (-tilt, 0, 0)

    @staticmethod
    def _place(o, a, b):
        d = b - a; o.location = a; o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = d.to_track_quat('-Z', 'Y')


# ================================================================= realistic scanned-style horse (Sketchfab, CC-BY)
GLB = __import__('os').path.join(__import__('os').path.dirname(__import__('os').path.abspath(__file__)), 'assets', 'horse_walk.glb')
CREDIT = '"Horse Walk" (https://skfb.ly/pEWGT) by Saad Khalid, CC BY 4.0'


def glb_coat(name):
    """bay coat on the imported mesh: object-space (model units: 1 = 10 cm) gradients for black legs, mane and tail"""
    m = bpy.data.materials.new(name); m.use_nodes = True; N, L = m.node_tree.nodes, m.node_tree.links; b = N['Principled BSDF']
    tc = N.new('ShaderNodeTexCoord'); sep = N.new('ShaderNodeSeparateXYZ'); L.new(tc.outputs['Object'], sep.inputs[0])
    n1 = N.new('ShaderNodeTexNoise'); n1.inputs['Scale'].default_value = .35; n1.inputs['Detail'].default_value = 8; L.new(tc.outputs['Object'], n1.inputs['Vector'])
    n2 = N.new('ShaderNodeTexNoise'); n2.inputs['Scale'].default_value = 40; n2.inputs['Detail'].default_value = 3; L.new(tc.outputs['Object'], n2.inputs['Vector'])
    ramp = N.new('ShaderNodeValToRGB'); ramp.color_ramp.elements[0].color = hexc('#3e2010'); ramp.color_ramp.elements[1].color = hexc('#7a4424'); L.new(n1.outputs['Fac'], ramp.inputs['Fac'])
    legs = N.new('ShaderNodeMapRange'); legs.inputs['From Min'].default_value = 6.0; legs.inputs['From Max'].default_value = 4.2; L.new(sep.outputs['Z'], legs.inputs['Value'])
    tail = N.new('ShaderNodeMapRange'); tail.inputs['From Min'].default_value = 7.4; tail.inputs['From Max'].default_value = 8.2; L.new(sep.outputs['Y'], tail.inputs['Value'])
    mx = N.new('ShaderNodeMath'); mx.operation = 'MAXIMUM'; L.new(legs.outputs[0], mx.inputs[0]); L.new(tail.outputs[0], mx.inputs[1])
    mix = N.new('ShaderNodeMix'); mix.data_type = 'RGBA'; L.new(mx.outputs[0], mix.inputs['Factor']); L.new(ramp.outputs['Color'], mix.inputs['A']); mix.inputs['B'].default_value = hexc('#140c08')
    L.new(mix.outputs['Result'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = .55; b.inputs['Sheen Weight'].default_value = .4; b.inputs['Sheen Roughness'].default_value = .4
    b.inputs['Subsurface Weight'].default_value = .03
    bp = N.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = .06; bp.inputs['Distance'].default_value = .02; L.new(n2.outputs['Fac'], bp.inputs['Height']); L.new(bp.outputs[0], b.inputs['Normal'])
    return m


class HorseGLB:
    """the Sketchfab horse, walk cycle from its 30-key morph loop, scaled to metres; forward is -Y"""
    KEY_M = .0355          # hoof travel per morph key during stance, metres (no foot sliding at this rate)
    CYCLE = 30

    def __init__(self, name='horse', with_tack=True):
        self.name = name
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=GLB)
        new = [o for o in bpy.data.objects if o not in before]
        top = next(o for o in new if o.parent is None)
        self.root = bpy.data.objects.new(name, None); _coll().objects.link(self.root)
        top.parent = self.root; top.scale = (.1, .1, .1) if abs(top.scale[0] - 1) < 1e-6 else top.scale * .1
        for o in new:
            for c in list(o.users_collection): c.objects.unlink(o)
            _coll().objects.link(o)
        self.body = next(o for o in new if o.type == 'MESH' and 'body' in o.name)
        self.meshes = [o for o in new if o.type == 'MESH']
        for o in self.meshes:
            if o.data.shape_keys and o.data.shape_keys.animation_data: o.data.shape_keys.animation_data_clear()
            if 'teeth' in o.name or 'tongue' in o.name: o.hide_render = True
            for p in o.data.polygons: p.use_smooth = True
        cm = glb_coat(name + '_coat'); self.body.data.materials.clear(); self.body.data.materials.append(cm)
        eye = plain('horse_eye_glb', '#0a0806', .03)
        for o in self.meshes:
            if 'eye' in o.name: o.data.materials.clear(); o.data.materials.append(eye)
        sd = self.body.modifiers.new('sd', 'SUBSURF'); sd.levels = 0; sd.render_levels = 1
        # back vertices that carry the saddle
        vs = self.body.data.shape_keys.key_blocks[1].data
        cand = [(i, v.co) for i, v in enumerate(vs) if abs(v.co.x) < .35]
        self.v_front = max((c for c in cand if -5.0 < c[1].y < -4.0), key=lambda c: c[1].z)[0]
        self.v_back = max((c for c in cand if -1.0 < c[1].y < 0.0), key=lambda c: c[1].z)[0]
        self._mane()
        self.kps = 30.0
        self.saddle = None
        if with_tack: self._tack()

    def _mane(self):
        b = self.body; vs = self.body.data.shape_keys.key_blocks[1].data
        hm = hair_mat(self.name + '_maneh', .97); b.data.materials.append(hm)
        # crest: the top-most vertices of each slice of the neck
        slices = {}
        for i, v in enumerate(vs):
            c = v.co
            if -13.0 < c.y < -5.2 and abs(c.x) < .6:
                k = round(c.y * 2); 
                if k not in slices or c.z > vs[slices[k]].co.z: slices[k] = i
        crest = set(slices.values())
        crest |= {i for i, v in enumerate(vs) if any((v.co - vs[j].co).length < .45 for j in slices.values())}
        tail = [i for i, v in enumerate(vs) if v.co.y > 8.0 and v.co.z > 9.0]
        def ps(name, idx, count, length, align, normal, children, clump, radius):
            if not idx: print('no verts', name); return
            g = b.vertex_groups.new(name=name); g.add(list(idx), 1.0, 'REPLACE')
            md = b.modifiers.new(name, 'PARTICLE_SYSTEM'); s = md.particle_system; st = s.settings
            st.type = 'HAIR'; st.count = count; st.hair_length = length; st.use_advanced_hair = True; st.emit_from = 'FACE'
            n_ = math.sqrt(sum(a * a for a in align) + normal ** 2); k = length / 4 / n_
            st.normal_factor = normal * k; st.object_align_factor = tuple(a * k for a in align)
            st.child_type = 'INTERPOLATED'; st.child_percent = 2; st.rendered_child_count = children; st.clump_factor = clump
            st.roughness_1 = .02; st.roughness_endpoint = .05; st.roughness_2 = .01
            st.root_radius = 1; st.tip_radius = .25; st.radius_scale = radius; st.material_slot = hm.name; st.render_step = 3
            s.vertex_group_density = name
            while b.modifiers.find(name) > b.modifiers.find('sd'): bpy.context.view_layer.objects.active = b; bpy.ops.object.modifier_move_up(modifier=name)
        # model units are decimetres (object scale .1), so lengths/radii are in model units
        ps('mane', crest, 1600, .26, (.7, 0, -.55), .45, 20, .55, .0006)
        ps('tail', tail, 700, .65, (0, .12, -1.0), .1, 30, .25, .0007)

    def set_pose(self, t, kps=None):
        kps = kps or self.kps; f = (t * kps) % self.CYCLE; k0 = int(f); u = f - k0; k1 = (k0 + 1) % self.CYCLE
        for o in self.meshes:
            if o.hide_render or not o.data.shape_keys: continue
            kb = o.data.shape_keys.key_blocks
            for k in kb[1:]: k.value = 0.0
            kb[1 + k0].value = 1 - u; kb[1 + k1].value = u

    def update(self, t, loc, yaw, gait='walk', speed=1.1, head_turn=0.0):
        self.kps = speed / self.KEY_M
        self.root.location = Vector(loc); self.root.rotation_euler = (0, 0, yaw)
        self.set_pose(t)
        if self.saddle: self._place_tack()

    def _back_points(self):
        """world positions of the two back vertices with the current morph mix"""
        kb = self.body.data.shape_keys.key_blocks; mw = self.body.matrix_world
        def p(i):
            v = Vector()
            for k in kb[1:]:
                if k.value > 0: v += k.data[i].co * k.value
            return mw @ v
        bpy.context.view_layer.update()
        return p(self.v_front), p(self.v_back)

    def seat(self):
        a, b = self._back_points(); c = a.lerp(b, .55); fwd = (a - b); fwd.z *= .25; fwd.normalize()
        R = fwd.to_track_quat('-Y', 'Z').to_matrix().to_4x4(); R.translation = c + Vector((0, 0, .09)); return R

    def _tack(self):
        lea = plain('saddle_leather', '#4a2a16', .45); dark = plain('tack_dark', '#24160e', .5); blanket = plain('blanket_glb', '#5a3a2a', .95)
        self.saddle = bpy.data.objects.new(self.name + '_saddle_rig', None); _coll().objects.link(self.saddle)
        sd = loft(self.name + '_saddle', [(Vector((0, y, z)), Vector((1, 0, 0)), Vector((0, 0, 1)), w, .045, .05) for (y, z, w) in
                                          [(-.3, .06, .13), (-.2, .02, .19), (-.02, 0, .21), (.14, .01, .21), (.25, .05, .18), (.3, .11, .13)]], n=24, exp=3.0)
        sd.data.materials.append(lea)
        bl = loft(self.name + '_blanket', [(Vector((0, y, -.04)), Vector((1, 0, 0)), Vector((0, 0, 1)), w, .02, .2) for (y, w) in ((-.36, .18), (-.26, .28), (0, .3), (.24, .28), (.34, .18))], n=24, exp=3.0)
        bl.data.materials.append(blanket)
        bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=.022, depth=.12, location=(0, -.27, .14)); hn = _own(bpy.context.active_object); hn.data.materials.append(lea)
        parts = [sd, bl, hn]
        for s in (-1, 1):
            bpy.ops.mesh.primitive_cube_add(size=1, location=(s * .29, -.03, -.32)); f = _own(bpy.context.active_object); f.scale = (.01, .13, .46); f.rotation_euler = (0, s * math.radians(-8), 0); f.data.materials.append(lea)
            bpy.ops.mesh.primitive_torus_add(major_radius=.065, minor_radius=.012, location=(s * .36, -.03, -.7), rotation=(0, math.pi / 2, 0)); st = _own(bpy.context.active_object); st.data.materials.append(dark)
            parts += [f, st]
        for o in parts:
            o.parent = self.saddle
            for p in o.data.polygons: p.use_smooth = True
        self.tack = parts

    def _place_tack(self):
        M = self.seat(); self.saddle.matrix_world = M @ Matrix.Translation((0, 0, -.09))
