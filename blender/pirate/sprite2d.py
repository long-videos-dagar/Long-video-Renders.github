"""Hand-drawn-look 2D characters (reference style) rendered with Skia. Units: metres-ish, origin between feet, y up. Output RGBA numpy (premultiplied -> straight)."""
import math, numpy as np, skia

S = 900.0                      # px per unit
def rgb(h, a=255): h = h.lstrip('#'); return skia.Color(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)
def mix(c1, c2, t):
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]; b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return '#%02x%02x%02x' % tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))

EXPR = {   # eyes: line|ring|dot ; brow: (dy, tilt); mouth: kind ; look: (dx,dy)
 'neutral':  dict(eyes='line', br=(0, 0), mouth='flat', look=(0, 0)),
 'smirk':    dict(eyes='line', br=(.004, .25), mouth='smirk', look=(.01, 0)),
 'smile':    dict(eyes='dot', br=(.01, -.1), mouth='smile', look=(0, 0)),
 'grin':     dict(eyes='arc', br=(.012, -.1), mouth='grin', look=(0, 0)),
 'furious':  dict(eyes='line', br=(-.01, .7), mouth='teeth', look=(0, 0)),
 'angry':    dict(eyes='line', br=(-.008, .55), mouth='frown', look=(0, 0)),
 'confused': dict(eyes='ring', br=(.03, -.35), mouth='wavy', look=(.012, .004)),
 'terror':   dict(eyes='ring', br=(.05, -.5), mouth='open', look=(0, .006)),
 'shout':    dict(eyes='ring', br=(.0, .45), mouth='open', look=(0, 0)),
 'strain':   dict(eyes='squint', br=(-.012, .45), mouth='teeth', look=(0, 0)),
 'surprise': dict(eyes='ring', br=(.05, -.2), mouth='o', look=(0, 0)),
 'sad':      dict(eyes='dot', br=(.02, -.5), mouth='frown', look=(0, .004)),
}

class Spec:
    def __init__(self, **k):
        d = dict(skin='#f7f2f6', body='#3b6fb6', body2=None, pants='#1b1b22', shoes='#16141a', hair=None, hair_col='#1a1714', hat=None, beard=None, bandana=None,
                 costume='shirt', tie=None, sash=None, scale=1.0, stripes=None, hair_style='sweep')
        d.update(k); self.__dict__.update(d)

def P(): return skia.Paint(AntiAlias=True)
def fill(c, grad=None):
    p = P(); p.setStyle(skia.Paint.kFill_Style); p.setColor(rgb(c)); return p
def stroke(w, c='#0b0a0d'):
    p = P(); p.setStyle(skia.Paint.kStroke_Style); p.setStrokeWidth(w); p.setColor(rgb(c)); p.setStrokeCap(skia.Paint.kRound_Cap); p.setStrokeJoin(skia.Paint.kRound_Join); return p

class Draw:
    def __init__(self, W=900, H=1500):
        self.W, self.H = W, H; self.sf = skia.Surface(W, H); self.c = self.sf.getCanvas(); self.c.clear(skia.ColorTRANSPARENT)
        self.ox, self.oy = W / 2, H - 70
    def X(self, x): return self.ox + x * S
    def Y(self, y): return self.oy - y * S
    def pt(self, p): return (self.X(p[0]), self.Y(p[1]))
    def path_pts(self, pts, closed=False, smooth=True):
        pa = skia.Path(); q = [self.pt(p) for p in pts]; pa.moveTo(*q[0])
        if smooth and len(q) > 2:
            for i in range(1, len(q) - 1):
                mx, my = (q[i][0] + q[i + 1][0]) / 2, (q[i][1] + q[i + 1][1]) / 2
                pa.quadTo(q[i][0], q[i][1], mx, my) if i < len(q) - 2 else pa.quadTo(q[i][0], q[i][1], q[i + 1][0], q[i + 1][1])
        else:
            for x, y in q[1:]: pa.lineTo(x, y)
        if closed: pa.close()
        return pa
    def closed_smooth(self, pts):
        q = [self.pt(p) for p in pts]; n = len(q); pa = skia.Path()
        m0 = ((q[-1][0] + q[0][0]) / 2, (q[-1][1] + q[0][1]) / 2); pa.moveTo(*m0)
        for i in range(n):
            a = q[i]; b = q[(i + 1) % n]; pa.quadTo(a[0], a[1], (a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        pa.close(); return pa
    def shape(self, pts, col, ow=.016, grad=None):
        pa = self.closed_smooth(pts); p = fill(col)
        if grad:
            (x0, y0), (x1, y1), c0, c1 = grad
            p.setShader(skia.GradientShader.MakeLinear([self.pt((x0, y0)), self.pt((x1, y1))], [rgb(c0), rgb(c1)]))
        self.c.drawPath(pa, p)
        if ow: self.c.drawPath(pa, stroke(ow * S))
        return pa
    def line(self, pts, w, col='#0b0a0d', smooth=True):
        self.c.drawPath(self.path_pts(pts, smooth=smooth), stroke(w * S, col))
    def circle(self, c, r, col, ow=.012):
        self.c.drawCircle(self.X(c[0]), self.Y(c[1]), r * S, fill(col))
        if ow: self.c.drawCircle(self.X(c[0]), self.Y(c[1]), r * S, stroke(ow * S))
    def ellipse(self, c, rx, ry, col, ow=.012, rot=0):
        self.c.save(); self.c.translate(self.X(c[0]), self.Y(c[1])); self.c.rotate(-rot)
        r = skia.Rect(-rx * S, -ry * S, rx * S, ry * S); self.c.drawOval(r, fill(col))
        if ow: self.c.drawOval(r, stroke(ow * S))
        self.c.restore()
    def clip_path(self, pa): self.c.save(); self.c.clipPath(pa, doAntiAlias=True)
    def unclip(self): self.c.restore()
    def result(self):
        img = self.sf.makeImageSnapshot(); a = img.toarray(colorType=skia.kRGBA_8888_ColorType, alphaType=skia.kUnpremul_AlphaType); return np.array(a)

def head_pts(cx, cy, w, h):
    """squashed-egg head (wider at cheeks, flat-ish chin), 12 control points"""
    pts = []
    for i in range(16):
        a = i / 16 * 2 * math.pi; ca, sa = math.cos(a), math.sin(a)
        r = 1.0 + (.06 if sa < 0 else -.03) * -sa * 0
        x = ca * w / 2 * (1 + .07 * (-sa)); y = sa * h / 2
        if sa < -.55: y = -h / 2 * (.88 + .12 * (-sa - .55) / .45 * 0 + .0) if False else y
        pts.append((cx + x, cy + y))
    return pts

def hair_stripes(D, pa, col, lines, spacing=.028, ang=75, w=.004, lc='#dad6d0'):
    D.clip_path(pa)
    for k in range(-30, 31):
        a = math.radians(ang); x0 = lines[0] + k * spacing
        D.c.drawLine(D.X(x0), D.Y(lines[1]), D.X(x0 + math.cos(a) * .5), D.Y(lines[1] + math.sin(a) * .5), stroke(w * S, lc))
    D.unclip()

def draw_character(sp, pose, W=900, H=1500):
    D = Draw(W, H); sc = 1.0
    crouch = pose.get('crouch', 0.0); lean = pose.get('lean', 0.0)       # lean: x shift of the shoulders
    face = EXPR[pose.get('face', 'neutral')] if isinstance(pose.get('face', 'neutral'), str) else pose['face']
    turn = pose.get('turn', 0.0)                                        # -1..1 : head turned (features shift)
    HIP = .46 - crouch; TOP = HIP + .40
    shL = (-.17 + lean, TOP - .04); shR = (.17 + lean, TOP - .04)
    # legs
    for sd, foot in ((-1, pose.get('footL', (-.1, 0))), (1, pose.get('footR', (.1, 0)))):
        hp = (sd * .08, HIP + .03); kn = pose.get('kneeL' if sd < 0 else 'kneeR') or ((hp[0] + foot[0]) / 2 + sd * .015, (hp[1] + foot[1]) / 2 + .02)
        D.line([hp, kn, (foot[0], foot[1] + .055)], .017)
        D.ellipse((foot[0] + sd * .01 + .03 * (1 if turn >= 0 else -1) * 0, foot[1] + .035), .062, .042, sp.shoes, ow=.013)
    # arms (behind body when raised? simple: draw both after body except far arm)
    def arm(sd, hand):
        sh = shL if sd < 0 else shR
        d = (hand[0] - sh[0], hand[1] - sh[1]); dl = math.hypot(*d) + 1e-6; L = min(dl, .56)
        hand = (sh[0] + d[0] / dl * L, sh[1] + d[1] / dl * L) if dl > .56 else hand
        mid = ((sh[0] + hand[0]) / 2, (sh[1] + hand[1]) / 2); nx, ny = -d[1] / dl, d[0] / dl
        if nx * sd - ny * .5 < 0: nx, ny = -nx, -ny
        bend = math.sqrt(max(0, .29 ** 2 - (L / 2) ** 2)) * .85
        el = (mid[0] + nx * bend, mid[1] + ny * bend)
        D.line([sh, el, hand], .016)
        D.circle(hand, .036, sp.skin, ow=.012)
    # body
    bt = TOP + .02
    body_pts = [(-.19 + lean * .9, TOP - .02), (-.205 + lean * .5, TOP - .16), (-.19, HIP + .14), (-.16, HIP + .02), (0, HIP - .02), (.16, HIP + .02), (.19, HIP + .14), (.205 + lean * .5, TOP - .16), (.19 + lean * .9, TOP - .02), (lean + 0, bt)]
    body_pts = [(x, y) for x, y in body_pts]
    g = ((0, TOP), (0, HIP), mix(sp.body, '#ffffff', .12), mix(sp.body, '#000000', .22))
    for sd in (-1,):   # far arm behind the body
        arm(-1, pose.get('handL', (-.25, HIP + .02)))
    pa = D.shape(body_pts, sp.body, ow=.02, grad=g)
    # costume details clipped to body
    D.clip_path(pa)
    if sp.stripes:
        for k in range(-12, 13): D.c.drawLine(D.X(k * .035), D.Y(HIP - .1), D.X(k * .035 + lean * .3), D.Y(TOP + .1), stroke(.006 * S, sp.stripes))
    if sp.costume == 'coat':
        D.c.drawLine(D.X(lean * .3), D.Y(TOP), D.X(0), D.Y(HIP - .02), stroke(.012 * S, '#0b0a0d'))
        v = D.closed_smooth([(-.015, TOP + .01), (-.09, TOP - .11), (-.06, TOP - .2), (0, TOP - .05)]); D.c.drawPath(v, fill('#f2eee3')); D.c.drawPath(v, stroke(.01 * S))
        v = D.closed_smooth([(.015, TOP + .01), (.09, TOP - .11), (.06, TOP - .2), (0, TOP - .05)]); D.c.drawPath(v, fill('#f2eee3')); D.c.drawPath(v, stroke(.01 * S))
        for i in range(4):
            D.circle((.028, TOP - .17 - i * .055), .013, '#d9ad3b', ow=.006); D.circle((-.028, TOP - .17 - i * .055), .013, '#d9ad3b', ow=.006)
        D.c.drawLine(D.X(-.22), D.Y(HIP + .1), D.X(.22), D.Y(HIP + .1), stroke(.02 * S, '#d9ad3b'))
    elif sp.costume == 'vest':
        v = D.closed_smooth([(-.2, TOP - .02), (-.025, TOP + .01), (-.012, HIP + .02), (-.2, HIP + .02)]); D.c.drawPath(v, fill(sp.body2 or '#5a3d28')); D.c.drawPath(v, stroke(.012 * S))
        v = D.closed_smooth([(.2, TOP - .02), (.025, TOP + .01), (.012, HIP + .02), (.2, HIP + .02)]); D.c.drawPath(v, fill(sp.body2 or '#5a3d28')); D.c.drawPath(v, stroke(.012 * S))
        for i in range(4): D.c.drawLine(D.X(-.02 - .002), D.Y(TOP - .04 - i * .06), D.X(-.045), D.Y(TOP - .04 - i * .06), stroke(.005 * S, '#2a1a10'))
        D.c.drawLine(D.X(-.03), D.Y(TOP + .0), D.X(.03), D.Y(TOP - .08), stroke(.006 * S, '#e8e0cc'))
    elif sp.costume == 'suit':
        D.c.drawLine(D.X(0), D.Y(TOP), D.X(0), D.Y(HIP), stroke(.01 * S))
    if sp.sash:
        sa = D.closed_smooth([(-.21, HIP + .11), (.21, HIP + .11), (.21, HIP + .03), (-.21, HIP + .03)]); D.c.drawPath(sa, fill(sp.sash)); D.c.drawPath(sa, stroke(.01 * S))
    if sp.tie:
        t = D.closed_smooth([(0, TOP), (.022, TOP - .03), (.016, TOP - .2), (0, TOP - .24), (-.016, TOP - .2), (-.022, TOP - .03)]); D.c.drawPath(t, fill(sp.tie)); D.c.drawPath(t, stroke(.008 * S))
    D.unclip()
    arm(1, pose.get('handR', (.25, HIP + .02)))
    # coat tails (below hip) drawn over legs
    if sp.costume == 'coat':
        tl = D.shape([(-.2, HIP + .08), (-.27, HIP - .16), (-.1, HIP - .22), (0, HIP - .12), (.1, HIP - .22), (.27, HIP - .16), (.2, HIP + .08)], sp.body, ow=.02, grad=((0, HIP), (0, HIP - .2), sp.body, mix(sp.body, '#000000', .3)))
    # head
    hr = pose.get('headroll', 0.0); hc = (lean * 1.1 + pose.get('headx', 0.0), TOP + .20 + pose.get('heady', 0.0)); hw, hh = .50, .45
    D.c.save(); D.c.translate(D.X(hc[0]), D.Y(hc[1])); D.c.rotate(-hr); D.c.translate(-D.X(0), -D.Y(0)); D.ox_save = (D.ox, D.oy)
    D.ox, D.oy = D.ox, D.oy
    H0 = (0.0, 0.0)
    hp = D.closed_smooth(head_pts(0, 0, hw, hh)) if False else None
    pts = head_pts(0, 0, hw, hh)
    # head is drawn about origin (0,0) after translate trick: shift so that unit (0,0) maps to head centre
    D.c.translate(D.X(0) - D.X(0), 0)
    pa = D.closed_smooth(pts)
    p = fill(sp.skin); p.setShader(skia.GradientShader.MakeRadial((D.X(-.08), D.Y(.12)), .5 * S, [rgb('#ffffff'), rgb(mix(sp.skin, '#c9b6d8', .35))]))
    D.c.drawPath(pa, p); D.c.drawPath(pa, stroke(.024 * S))
    face_draw(D, sp, face, turn, hw, hh, pa)
    D.c.restore()
    img = D.result(); return img, D

def face_draw(D, sp, f, turn, hw, hh, headpath):
    tx = turn * .16; ey = -.02; k = '#0b0a0d'
    ex = [(-.105 + tx, ey), (.105 + tx, ey)]
    scale_far = [1 - .25 * max(0, turn), 1 - .25 * max(0, -turn)]
    lk = f['look']
    for i, (x, y) in enumerate(ex):
        s = scale_far[i]
        if f['eyes'] == 'ring':
            D.circle((x, y), .048 * s, '#ffffff', ow=.014); D.circle((x + lk[0] * 1.6, y + lk[1] * 1.6), .0125, k, ow=0)
        elif f['eyes'] == 'dot':
            D.ellipse((x, y), .016 * s, .02, k, ow=0)
        elif f['eyes'] == 'arc':
            D.line([(x - .04 * s, y - .006), (x, y + .02), (x + .04 * s, y - .006)], .014)
        elif f['eyes'] == 'squint':
            D.line([(x - .045 * s, y + .012 * (1 if i == 0 else -1)), (x + .045 * s, y - .012 * (1 if i == 0 else -1))], .016)
        else:   # half-closed line eyes with a small iris sliver
            D.line([(x - .05 * s, y + .004), (x + .05 * s, y + .004)], .015)
            D.line([(x - .05 * s, y + .004), (x - .058 * s, y + .012)], .008)
            D.c.drawOval(skia.Rect(D.X(x - .016 * s + lk[0]), D.Y(y - .002), D.X(x + .016 * s + lk[0]), D.Y(y - .02)), fill(k))
    dy, tilt = f['br']
    for i, (x, y) in enumerate(ex):
        s = scale_far[i]; sd = -1 if i == 0 else 1
        by = y + .075 + dy + (.012 if f['eyes'] == 'ring' else 0)
        a = tilt * .035 * (-sd * 0 + 1)
        inner = (x - sd * -.05 * s, by + a * -1 * 1) if False else None
        xin, xout = x - sd * .05 * s * -1 * -1, x + sd * .05 * s
        D.line([(x - sd * .045 * s, by - tilt * .03 * 1), (x + sd * .045 * s, by + tilt * .03 * 1 * -1 * -1 * 0 + .0 + (.0))], .016, smooth=False) if False else D.line([(x - sd * .05 * s, by - tilt * .028), (x + sd * .05 * s, by + tilt * .028)], .017, smooth=False)
    # nose hook
    nx = .012 + tx
    D.line([(nx - .012, ey - .005), (nx + .012, ey - .045), (nx, ey - .062), (nx - .016, ey - .054)], .009) if f['mouth'] != 'open' else None
    my = -.135; mx = tx * .9; m = f['mouth']
    if m == 'flat': D.line([(mx - .03, my), (mx + .03, my)], .011)
    elif m == 'smirk': D.line([(mx - .04, my - .004), (mx + .02, my - .008), (mx + .055, my + .02)], .011)
    elif m == 'smile': D.line([(mx - .06, my + .012), (mx, my - .02), (mx + .06, my + .012)], .011)
    elif m == 'grin':
        D.shape([(mx - .09, my + .02), (mx, my - .05), (mx + .09, my + .02)], '#ffffff', ow=.012)
    elif m == 'frown': D.line([(mx - .055, my - .01), (mx, my + .018), (mx + .055, my - .01)], .011)
    elif m == 'wavy': D.line([(mx - .05, my), (mx - .02, my + .014), (mx + .01, my - .008), (mx + .05, my + .008)], .011)
    elif m == 'teeth':
        pa = D.closed_smooth([(mx - .075, my + .03), (mx + .075, my + .03), (mx + .075, my - .035), (mx - .075, my - .035)])
        D.c.drawPath(pa, fill('#fdfbf7')); D.c.drawPath(pa, stroke(.013 * S))
        D.c.save(); D.c.clipPath(pa, doAntiAlias=True)
        for i in range(-2, 3): D.c.drawLine(D.X(mx + i * .03), D.Y(my + .04), D.X(mx + i * .03), D.Y(my - .04), stroke(.006 * S))
        D.c.drawLine(D.X(mx - .08), D.Y(my - .002), D.X(mx + .08), D.Y(my - .002), stroke(.006 * S)); D.c.restore()
    elif m == 'open':
        pa = D.closed_smooth([(mx - .06, my + .03), (mx, my + .04), (mx + .06, my + .03), (mx + .055, my - .06), (mx, my - .09), (mx - .055, my - .06)])
        D.c.drawPath(pa, fill('#1a0d0f')); D.c.drawPath(pa, stroke(.013 * S))
        D.ellipse((mx, my - .06), .03, .014, '#b8484c', ow=0)
    elif m == 'o': D.ellipse((mx, my - .01), .028, .036, '#1a0d0f', ow=.012)
    # beard
    if sp.beard:
        bc = sp.beard
        bp = D.closed_smooth([(-.285, -.02), (-.25, -.14), (-.14, -.235), (0, -.255), (.14, -.235), (.25, -.14), (.285, -.02), (.2, -.11), (.1, -.095), (0, -.18), (-.1, -.095), (-.2, -.11)])
        D.c.drawPath(bp, fill(bc)); D.c.drawPath(bp, stroke(.016 * S))
        D.c.save(); D.c.clipPath(bp, doAntiAlias=True)
        for i in range(-12, 13): D.c.drawLine(D.X(i * .024), D.Y(-.1), D.X(i * .024 + .02), D.Y(-.27), stroke(.004 * S, mix(bc, '#ffffff', .35)))
        D.c.restore()
        mo = D.closed_smooth([(-.07 + tx * .5, -.095), (0 + tx * .5, -.085), (.07 + tx * .5, -.095), (.05 + tx * .5, -.12), (-.05 + tx * .5, -.12)])
        D.c.drawPath(mo, fill(bc)); D.c.drawPath(mo, stroke(.012 * S))
    # hair / hats (clipped by drawing over the top of the head)
    hair_draw(D, sp, hw, hh, tx)

def hair_draw(D, sp, hw, hh, tx):
    col = sp.hair_col; hs = sp.hair_style
    if sp.bandana:
        pa = D.closed_smooth([(-.29, .02), (-.3, .14), (-.2, .24), (0, .285), (.2, .24), (.3, .14), (.29, .02), (.15, .075), (0, .1), (-.15, .075)])
        D.c.drawPath(pa, fill(sp.bandana)); D.c.drawPath(pa, stroke(.02 * S))
        D.c.save(); D.c.clipPath(pa, doAntiAlias=True)
        for i in range(-8, 9):
            for j in range(0, 5): D.circle((i * .06 + (j % 2) * .03, .05 + j * .05), .008, '#f1e6d2', ow=0)
        D.c.restore()
        kn = D.closed_smooth([(.27, .03), (.36, .08), (.4, -.02), (.34, -.08), (.28, -.02)]); D.c.drawPath(kn, fill(sp.bandana)); D.c.drawPath(kn, stroke(.016 * S))
    elif hs == 'sweep' and not sp.hat:
        pa = D.closed_smooth([(-.285, -.01), (-.3, .13), (-.2, .24), (0, .27), (.22, .22), (.3, .1), (.27, .0), (.25, .08), (.1, .11), (-.08, .17), (-.2, .1)])
        D.c.drawPath(pa, fill(col)); D.c.drawPath(pa, stroke(.02 * S))
        D.c.save(); D.c.clipPath(pa, doAntiAlias=True)
        for i in range(-12, 13): D.c.drawLine(D.X(i * .026), D.Y(.27), D.X(i * .026 + .12), D.Y(.1), stroke(.004 * S, mix(col, '#ffffff', .45)))
        D.c.restore()
    elif hs == 'grey' and not sp.hat:
        pa = D.closed_smooth([(-.285, -.02), (-.3, .13), (-.2, .24), (0, .27), (.2, .24), (.3, .13), (.285, -.02), (.2, .06), (.0, .1), (-.2, .06)])
        D.c.drawPath(pa, fill(col)); D.c.drawPath(pa, stroke(.02 * S))
    if sp.hat == 'tricorn':
        hp = D.closed_smooth([(-.38, .14), (-.3, .2), (-.12, .33), (0, .42), (.12, .33), (.3, .2), (.38, .14), (.3, .1), (.0, .17), (-.3, .1)])
        D.c.drawPath(hp, fill('#17161c')); D.c.drawPath(hp, stroke(.022 * S))
        D.c.drawPath(D.path_pts([(-.37, .14), (-.3, .1), (0, .17), (.3, .1), (.37, .14)]), stroke(.012 * S, '#d9ad3b'))
        fe = D.closed_smooth([(.2, .26), (.34, .34), (.38, .3), (.26, .22)]); D.c.drawPath(fe, fill('#b03028')); D.c.drawPath(fe, stroke(.01 * S))
    if sp.hat == 'cap':
        cp = D.closed_smooth([(-.3, .06), (-.28, .22), (-.1, .32), (.1, .32), (.28, .22), (.3, .06), (.08, .1), (-.08, .1)])
        D.c.drawPath(cp, fill('#3d5f9a')); D.c.save(); D.c.clipPath(cp, doAntiAlias=True)
        for i in range(-14, 15): D.c.drawLine(D.X(i * .03), D.Y(.34), D.X(i * .03 * 1.2), D.Y(.06), stroke(.01 * S, '#f1efe9'))
        D.c.restore(); D.c.drawPath(cp, stroke(.02 * S))
