import sys, os, math
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'dagar')); sys.path.insert(0, HERE)
import bpy
from mathutils import Vector
import lib
from lib import *
from common import ink_setup
import world as W, inkchar as H
mode = sys.argv[sys.argv.index('--') + 1]; out = sys.argv[sys.argv.index('--') + 2]
lib.reset(); sc = lib.setup(int(os.environ.get('RW', 720)), int(os.environ.get('RH', 960)), int(os.environ.get('SAMPLES', 24))); lib.DRAFT = False; sc.cycles.max_bounces = 5
W.sky('storm', 1.2, sun_dir=(.5, .8, .5), sun_energy=3.5)
plane('ground', 60, 60, (0, 0, 0), mat('ground', '#7a5a3a', rough=.8))
sl = H.Human('C1', 'Sailor', shirt='#d9d2c2', vest='#4b3a2a', trousers='#1a1a1e', bandana='#a82a24', beard='#2a1a10')
cp = H.Human('C2', 'Captain', coat='#1b2a4a', hat='tricorn', beard='#9a9a9a', hair='#9a9a9a', height=1.04)
cw = H.Human('C3', 'Crew', shirt='#c9c0a8', vest='#3a4a5a', hair='#3a2a1a')
E = H.EXPR
def pose(h, x, yaw, face, **kw):
    d = dict(loc=(x, 0, 0), yaw=yaw, face=E[face]); d.update(kw); h.fn = lambda T, d=d: d
pose(sl, -1.0, 12, 'confused', handR=Vector((-.45, -.5, 1.2)))
pose(cp, 0, 0, 'furious', handR=Vector((.6, -.7, 1.45)))
pose(cw, 1.0, -12, 'smile')
for h in H.HUMANS: h.apply(0.0)
cam = (Vector((0, -5.0, 1.15)), Vector((0, 0, .85)), 38)
if mode == 'face': pose(cp, 50, 0, 'neutral'); pose(cw, 60, 0, 'neutral'); pose(sl, -1.0, 0, 'confused'); [h.apply(0.0) for h in H.HUMANS]; cam = (Vector((-1.0, -2.2, 1.62)), Vector((-1.0, 0, 1.6)), 85)
lib.camera(cam[0], cam[1], lens=cam[2], focus=cam[1], fstop=3.5)
area((-2, -3, 3.5), (0, 0, 1.2), size=3, energy=500, color='#ffe2c0'); area((3, -2, 2), (0, 0, 1.4), size=2, energy=200, color='#a8c4ff')
ink_setup(int(os.environ.get('RW', 720)), 1.0, 9.0, 3.2)
lib.render(os.path.abspath(out))
