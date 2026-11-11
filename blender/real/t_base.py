import sys, bpy, addon_utils, importlib, math, os
bpy.ops.wm.read_factory_settings(use_empty=True)
addon_utils.enable('bl_ext.user_default.mpfb', default_set=True, persistent=True)
M = lambda p: importlib.import_module('bl_ext.user_default.mpfb.' + p)
HS = M('services.humanservice').HumanService; TS = M('services.targetservice').TargetService; MS = M('services.materialservice').MaterialService
mac = TS.get_default_macro_info_dict(); mac.update(gender=1.0, age=.75, muscle=.7, weight=.55, height=.55); mac['race'] = dict(asian=.1, caucasian=.6, african=.3)
h = HS.create_human(mask_helpers=True, detailed_helpers=True, extra_vertex_groups=True, feet_on_ground=True, scale=0.1, macro_detail_dict=mac)
rig = HS.add_builtin_rig(h, 'mixamo', import_weights=True)
print('RIG', rig and rig.name, rig and [b.name for b in rig.data.bones][:70])
mat = MS.create_v2_skin_material('skin', h)
print('MAT nodes', [n.name for n in mat.node_tree.nodes][:30])
print('DIM', h.dimensions[:], 'mods', [(m.name, m.type) for m in h.modifiers])
bpy.ops.wm.save_as_mainfile(filepath='/tmp/mh/base.blend')
