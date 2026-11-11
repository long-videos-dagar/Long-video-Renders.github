import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'dagar'))
import bpy
from mathutils import Vector
import lib
from lib import *
import world as W, rpm
from common_p import *
mode = sys.argv[sys.argv.index('--') + 1]; out = sys.argv[sys.argv.index('--') + 2]
lib.reset(); sc = lib.setup(int(os.environ.get('RW', 720)), int(os.environ.get('RH', 960)), int(os.environ.get('SAMPLES', 32))); lib.DRAFT = False
sc.cycles.max_bounces = 5
W.sky('storm', 1.2, sun_dir=(.5, .8, .5), sun_energy=3.5)
plane('ground', 60, 60, (0, 0, 0), mat('ground', '#6a5038', rough=.8))
sl = rpm.Avatar('C1', 'Sailor', shirt=(222, 214, 192), trousers=(52, 58, 66), shoes=(42, 28, 20), hair=(34, 22, 14), skin_mul=(1.0, .93, .86), beard='full', beard_col=(30, 20, 14), bandana='#a82a24')
cp = rpm.Avatar('C2', 'Captain', shirt=(240, 236, 224), trousers=(28, 28, 36), shoes=(24, 16, 12), hair=(150, 150, 150), skin_mul=(1.05, .98, .92), beard='grey', beard_col=(150, 150, 150), hat='tricorn', scale=1.03)
cw = rpm.Avatar('C3', 'Crew', shirt=(176, 164, 138), trousers=(70, 62, 52), shoes=(36, 24, 16), hair=(58, 40, 24), skin_mul=(.85, .78, .70), bandana='#3a5a8a')
sl.costume('sailor'); cp.costume('captain'); cw.costume('crew')
fps = 24; sc.render.fps = fps
for a, x, yaw, clip in ((sl, -1.0, 15, 'M_Standing_Idle_001'), (cp, 0, 0, 'M_Talking_Variations_003'), (cw, 1.0, -15, 'M_Standing_Idle_001')):
    a.arm.location = (x, 0, 0); a.arm.rotation_euler = (0, 0, math.radians(180 + yaw)); a.play(clip, 0, 0, fps, offset=1.0)
sc.frame_set(1)
cam = {'lineup': (Vector((0, -5.0, 1.3)), Vector((0, 0, .95)), 40), 'face': (Vector((0, -1.1, 1.7)), Vector((0, 0, 1.68)), 85)}[mode.split(':')[0]]
if mode.startswith('face'):
    idx = int(mode.split(':')[1]); a = (sl, cp, cw)[idx]; a.set_face(dict(op=.1, sm=.2)); cam = (Vector((a.arm.location.x, -1.1, 1.7)), Vector((a.arm.location.x, 0, 1.68)), 85)
lib.camera(cam[0], cam[1], lens=cam[2], focus=cam[1], fstop=2.8)
area((-2, -3, 3.5), (0, 0, 1.2), size=3, energy=400, color='#ffe2c0'); area((3, -2, 2), (0, 0, 1.4), size=2, energy=150, color='#a8c4ff')
lib.render(os.path.abspath(out))
