"""Real physics: Bullet rigid bodies (mug drop, baked to keyframes) and Mantaflow liquid (tap water)."""
import bpy, math, os, time
from mathutils import Vector
from common import *
import lib

def _active(o):
    vl = bpy.context.view_layer
    for x in bpy.context.selected_objects: x.select_set(False)
    o.select_set(True); vl.objects.active = o

def rb(o, kind, shape, mass=1.0, friction=.5, bounce=.0, kinematic=False, margin=.002):
    _active(o)
    bpy.ops.rigidbody.object_add(type=kind)
    r = o.rigid_body; r.collision_shape = shape; r.friction = friction; r.restitution = bounce
    r.collision_margin = margin; r.use_margin = True
    if kind == 'ACTIVE': r.mass = mass; r.linear_damping = .03; r.angular_damping = .05
    if kinematic: r.kinematic = True
    return r

def bake_mug(mug, floor_objs, static_objs, pusher, n, fps, hand_path):
    """Simulate frames 1..n with Bullet, then store the result as plain keyframes (deterministic, any frame renderable)."""
    sc = bpy.context.scene
    if not sc.rigidbody_world: bpy.ops.rigidbody.world_add()
    w = sc.rigidbody_world; w.time_scale = 1.0; w.substeps_per_frame = 20; w.solver_iterations = 40
    sc.rigidbody_world.point_cache.frame_start = 1; sc.rigidbody_world.point_cache.frame_end = n + 5
    sc.render.fps = fps
    for o in floor_objs + static_objs: rb(o, 'PASSIVE', 'BOX', friction=.6, bounce=.2)
    for o in floor_objs:
        o.rigid_body.collision_shape = 'BOX'
    rb(mug, 'ACTIVE', 'CONVEX_HULL', mass=.35, friction=.55, bounce=.32)
    rb(pusher, 'PASSIVE', 'SPHERE', friction=.4, kinematic=True)
    # animate the pusher (hand path) with explicit keys so the solver sees real motion
    pusher.rotation_mode = 'XYZ'
    for f in range(1, n + 6):
        pusher.location = hand_path((f - 1) / fps); pusher.keyframe_insert('location', frame=f)
    sc.frame_set(1)
    rec = []
    for f in range(1, n + 1):
        sc.frame_set(f); bpy.context.view_layer.update()
        rec.append(mug.matrix_world.copy())
    # strip physics and keep keyframes
    bpy.ops.rigidbody.world_remove()
    mug.animation_data_clear(); mug.rotation_mode = 'QUATERNION'
    for f, M in enumerate(rec, 1):
        loc, rot, _ = M.decompose(); mug.location = loc; mug.rotation_quaternion = rot
        mug.keyframe_insert('location', frame=f); mug.keyframe_insert('rotation_quaternion', frame=f)
    if mug.animation_data and mug.animation_data.action:
        for fc in mug.animation_data.action.fcurves if hasattr(mug.animation_data.action, 'fcurves') else []:
            for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'
    sc.frame_set(1)
    return [M.translation.copy() for M in rec]

def fluid_pour(nozzle, box_lo, box_hi, effectors, res=96, n_frames=90, cache='/tmp/dagar_fluid', start_vel=(0, 0, -1.4), radius=.011, rate_frames=None):
    """Tap water: a liquid inflow at the nozzle falling into the sink basin, solved by Mantaflow (FLIP). Returns the fluid mesh object."""
    sc = bpy.context.scene
    dom = lib.box('fluid_domain', (box_hi[0] - box_lo[0], box_hi[1] - box_lo[1], box_hi[2] - box_lo[2]),
                  ((box_hi[0] + box_lo[0]) / 2, (box_hi[1] + box_lo[1]) / 2, (box_hi[2] + box_lo[2]) / 2), None)
    dom.display_type = 'WIRE'
    _active(dom); bpy.ops.object.modifier_add(type='FLUID')
    m = dom.modifiers['Fluid']; m.fluid_type = 'DOMAIN'; d = m.domain_settings
    d.domain_type = 'LIQUID'; d.resolution_max = res; d.use_mesh = True; d.mesh_scale = 2 if res < 100 else 1
    d.cache_directory = cache; d.cache_type = 'ALL'
    d.use_adaptive_timesteps = True; d.timesteps_max = 4
    d.particle_radius = 2.0 if res >= 80 else 2.5; d.use_fractions = False
    d.surface_tension = 0.0
    d.use_collision_border_front = d.use_collision_border_back = d.use_collision_border_left = d.use_collision_border_right = False
    d.use_collision_border_bottom = False; d.use_collision_border_top = False
    d.cache_frame_start = 1; d.cache_frame_end = n_frames
    d.use_viscosity = False
    for o in effectors:
        _active(o); bpy.ops.object.modifier_add(type='FLUID'); mm = o.modifiers['Fluid']; mm.fluid_type = 'EFFECTOR'
        mm.effector_settings.effector_type = 'COLLISION'; mm.effector_settings.surface_distance = .004; mm.effector_settings.use_effector = True
    # inflow emitter: a short cylinder at the tap tip
    em = lib.cyl('fluid_inflow', radius, .03, nozzle, None, seg=16); em.display_type = 'WIRE'
    _active(em); bpy.ops.object.modifier_add(type='FLUID'); fm = em.modifiers['Fluid']; fm.fluid_type = 'FLOW'
    fs = fm.flow_settings; fs.flow_type = 'LIQUID'; fs.flow_behavior = 'INFLOW'; fs.flow_source = 'MESH'
    fs.use_initial_velocity = True; fs.velocity_coord = start_vel; fs.volume_density = 1.0; fs.surface_distance = .0
    fs.use_plane_init = False
    if rate_frames:   # tap opens at frame a, closes at frame b
        fs.use_inflow = False; fs.keyframe_insert('use_inflow', frame=1)
        fs.use_inflow = True; fs.keyframe_insert('use_inflow', frame=rate_frames[0])
        if rate_frames[1]: fs.use_inflow = False; fs.keyframe_insert('use_inflow', frame=rate_frames[1])
    return dom

def bake_fluid(dom):
    t = time.time(); _active(dom)
    bpy.context.scene.frame_set(1)
    bpy.ops.fluid.bake_data(); lib.log('fluid data baked', f'{time.time() - t:.0f}s')
    t = time.time(); bpy.ops.fluid.bake_mesh(); lib.log('fluid mesh baked', f'{time.time() - t:.0f}s')
