import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'dagar'))
import bpy
from mathutils import Vector
import lib
from lib import *
import world as W, rpm, own
from common_p import *
out = sys.argv[sys.argv.index('--') + 1]
lib.reset(); sc = lib.setup(540, 720, 24); lib.DRAFT = False; sc.cycles.max_bounces = 5
W.sky('storm', 1.2, sun_dir=(.5, .8, .5), sun_energy=3.5)
plane('ground', 60, 60, (0, 0, 0), mat('ground', '#6a5038', rough=.8))
B = rpm.import_base(); arm = B['arm'].copy(); arm.data = B['arm'].data.copy(); coll('Humans').objects.link(arm)
sk = mat('skin_t', '#b98a68', rough=.55, sss=.15)
ob = own.body_mesh(arm, 'ownbody', sk); own.rig(ob, arm)
arm.animation_data_create(); tr = arm.animation_data.nla_tracks.new(); act = B['acts']['M_Standing_Idle_001']; s = tr.strips.new('i', 1, act); s.action_frame_start = 30
arm.rotation_euler = (0, 0, math.pi); sc.frame_set(1)
lib.camera(Vector((0, -5.0, 1.0)), Vector((0, 0, .9)), 40, focus=Vector((0, 0, .9)), fstop=2.8)
area((-2, -3, 3.5), (0, 0, 1.2), size=3, energy=400, color='#ffe2c0'); area((3, -2, 2), (0, 0, 1.4), size=2, energy=150, color='#a8c4ff')
lib.render(os.path.abspath(out))
