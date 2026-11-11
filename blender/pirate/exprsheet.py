"""python3 exprsheet.py -- <out.png> name1,name2,name3,name4 : bust row of 4 characters, one expression each."""
import sys, os, math
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'dagar')); sys.path.insert(0, HERE)
import bpy
from mathutils import Vector
import lib
from lib import *
from common import ink_setup
import world as W, inkchar as H
out = sys.argv[sys.argv.index('--') + 1]; names = sys.argv[sys.argv.index('--') + 2].split(','); T = float(os.environ.get('TT', 0.35))
RW, RH = int(os.environ.get('RW', 1200)), int(os.environ.get('RH', 520))
lib.reset(); sc = lib.setup(RW, RH, int(os.environ.get('SAMPLES', 16))); lib.DRAFT = False; sc.cycles.max_bounces = 4
W.sky('storm', 1.2, sun_dir=(.5, .8, .5), sun_energy=3.0)
plane('ground', 60, 60, (0, 0, 0), mat('ground', '#5a4630', rough=.8)); plane('wall', 60, 20, (0, 3, 5), mat('wall', '#3a4a60', rough=.9), rot=(math.pi / 2, 0, 0))
cast = [dict(shirt='#d9d2c2', vest='#4b3a2a', bandana='#a82a24', beard='#2a1a10'), dict(coat='#1b2a4a', hat='tricorn', beard='#9a9a9a', hair='#9a9a9a', height=1.04),
        dict(shirt='#c9c0a8', vest='#3a4a5a', hair='#3a2a1a'), dict(shirt='#2a2a30', vest='#1c1c20', bandana='#1a1a1e', beard='#1a1410')]
for i, nm in enumerate(names):
    h = H.Human(f'C{i}', nm, **cast[i % 4]); x = (i - (len(names) - 1) / 2) * .66
    h.fn = lambda t, x=x, nm=nm, i=i: dict(loc=(x, 0, 0), yaw=(8, -6, 10, -10)[i % 4], face=H.EXPR[nm], head=((6, -4, 5, -6)[i % 4], 0, 0))
for h in H.HUMANS: h.apply(T)
zc = sum(h.head.matrix_world.translation.z for h in H.HUMANS) / len(H.HUMANS) if False else 1.02
bpy.context.view_layer.update(); zc = H.HUMANS[0].head.matrix_world.translation.z + .2
lib.camera(Vector((0, -4.6, zc)), Vector((0, 0, zc - .06)), lens=62, focus=Vector((0, 0, zc)), fstop=8)
area((-2, -3, 3.5), (0, 0, 1.2), size=3, energy=500, color='#ffe2c0'); area((3, -2, 2), (0, 0, 1.4), size=2, energy=220, color='#a8c4ff')
ink_setup(RW, 1.0, 4.2, 2.2)
lib.render(os.path.abspath(out))
