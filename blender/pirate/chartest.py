import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'dagar'))
import bpy
from mathutils import Vector
import lib
from lib import *
import human as H, world as W
from common_p import *
mode = sys.argv[sys.argv.index('--') + 1]; out = sys.argv[sys.argv.index('--') + 2]
lib.reset(); sc = lib.setup(int(os.environ.get('RW', 720)), int(os.environ.get('RH', 960)), int(os.environ.get('SAMPLES', 48))); lib.DRAFT = False
sc.cycles.max_bounces = 6
W.sky('storm', 1.2, sun_dir=(.5, .8, .5), sun_energy=3.5)
plane('ground', 60, 60, (0, 0, -.12), mat('ground', '#6a5038', rough=.8))
# a patch of deck planks behind
from common import wood_mat
box('deck', (6, 6, .1), (0, 0, -.05), wood_mat('deckw', '#9a7448', '#6a4a2a', stretch=(1, 30, 1)))
sl = H.Human('CHAR_001', 'Sailor', skin='#b98a64', shirt='#d9d2c2', vest='#4b3a2a', trousers='#2f3a44', boots='#2a1c14', hair='#2a1a10', bandana='#a82a24', beard='#2a1a10', build=1.05, eye='#5a4a3a')
cp = H.Human('CHAR_002', 'Captain', skin='#d3a784', shirt='#efe9dc', coat='#1b2a4a', trousers='#1b1b22', boots='#15100c', hair='#8a8a8a', beard='#9a9a9a', hat='tricorn', height=1.04, build=1.1, eye='#3a5a7a')
cw = H.Human('CHAR_003', 'Crew', skin='#a97a58', shirt='#c9c0a8', vest='#5a4630', trousers='#33302c', boots='#241810', hair='#3a2a1a', bandana='#3a5a8a', eye='#4a3a2a')
E = H.EXPR
def pose(h, x, yaw, face, **kw):
    d = dict(loc=(x, 0, 0), yaw=yaw, face=E[face], lean=(.03, 0), head=(0, 0, 0)); d.update(kw); h.fn = lambda T, d=d: d
if mode == 'lineup':
    pose(sl, -.9, 12, 'smirk', handL=Vector((-1.12, -.02, .82)), handR=Vector((-.66, -.1, .85)), crouch=.03)
    pose(cp, 0, 0, 'furious', handR=Vector((.45, -.65, 1.4)), handL=Vector((-.3, -.08, .82)), crouch=.02)
    pose(cw, .95, -14, 'smile', handL=Vector((.66, -.1, .82)), handR=Vector((1.28, -.1, .85)), crouch=.04)
    cam = (Vector((0, -5.2, 1.35)), Vector((0, 0, .95)), 40)
elif mode == 'captain':
    pose(sl, 50, 0, 'neutral'); pose(cw, 60, 0, 'neutral'); pose(cp, 0, 15, 'furious', head=(-8, 3, 0)); cam = (Vector((.5, -1.25, 1.78)), Vector((0, 0, 1.72)), 85)
elif mode == 'sailor':
    pose(cp, 50, 0, 'neutral'); pose(cw, 60, 0, 'neutral'); pose(sl, 0, -12, 'smirk', head=(10, 2, 0)); cam = (Vector((-.45, -1.25, 1.7)), Vector((0, 0, 1.66)), 85)
elif mode == 'terror':
    pose(sl, 50, 0, 'neutral'); pose(cw, 60, 0, 'neutral'); pose(cp, 0, 10, 'terror', head=(0, 0, 0)); cam = (Vector((.4, -1.2, 1.68)), Vector((0, 0, 1.68)), 85)
for h in H.HUMANS:
    if mode != 'lineup' and h.fn(0).get('loc') is None: pass
for h in H.HUMANS: h.apply(0.0)
lib.camera(cam[0], cam[1], lens=cam[2], focus=cam[1], fstop=2.8)
area((-2, -3, 3.5), (0, 0, 1.2), size=3, energy=400, color='#ffe2c0'); area((3, -2, 2), (0, 0, 1.4), size=2, energy=150, color='#a8c4ff')
lib.render(os.path.abspath(out))
