"""TALEVENTURE 9:16 promo - "From idea to screen".
One continuous shot, 60 fps, 21.2 s, drawn entirely in code (numpy / Pillow / OpenCV 2.5D).
One orange-red line of light carries the whole story; every scene draws it through light().

usage:  python3 render.py frames A B outdir      (frames A..B-1 -> outdir/f_%05d.png)
        python3 render.py stills "t1,t2,..." outdir
env:    SCALE (1.0 = 1080x1920), SUB (motion-blur sub-frames, default 6)
"""
import os, sys, math, json
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
S = float(os.environ.get('SCALE', '1'))
SUB = int(os.environ.get('SUB', '6'))
FPS = 60
W, H = int(round(1080 * S)) // 2 * 2, int(round(1920 * S)) // 2 * 2
DUR = 21.2
ACC = np.array([1.0, 0.30, 0.11], np.float32)          # TALEVENTURE red-orange #FF4D1C
ACC8 = (255, 77, 28)
WHITE = np.ones(3, np.float32)
cv2.setNumThreads(2)

# ---------------------------------------------------------------- easing
def cl(x, a=0.0, b=1.0): return a if x < a else b if x > b else x
def sg(t, a, b): return cl((t - a) / (b - a))
def ss(x): x = cl(x); return x * x * x * (x * (6 * x - 15) + 10)
def eo(x, p=3): x = cl(x); return 1 - (1 - x) ** p
def ei(x, p=3): x = cl(x); return x ** p
def eio(x): x = cl(x); return 4 * x ** 3 if x < .5 else 1 - (-2 * x + 2) ** 3 / 2
def back(x, s=1.4): x = cl(x) - 1; return x * x * ((s + 1) * x + s) + 1
def lerp(a, b, u): return a + (b - a) * u
def lerp2(a, b, u): return (lerp(a[0], b[0], u), lerp(a[1], b[1], u))

# ---------------------------------------------------------------- fonts, text, images
_fc = {}
def F(name, size):
    k = (name, int(round(size * S)))
    if k not in _fc: _fc[k] = ImageFont.truetype(os.path.join(HERE, 'fonts', name + '.otf'), max(4, k[1]))
    return _fc[k]

def rgba_from_L(alpha, color):
    a = np.asarray(alpha, np.float32) / 255.0
    c = np.asarray(color, np.float32)
    return np.dstack([a * c[0], a * c[1], a * c[2], a]).astype(np.float32)

_tc = {}
def text_sprite(txt, size, font='InterDisplay-Bold', color=(1, 1, 1), track=0.0):
    """premultiplied RGBA sprite of a text line, with its pixel offset of the text origin; returns (spr, ox, oy, w_design, h_design)"""
    k = (txt, size, font, tuple(np.round(color, 3)), track)
    if k in _tc: return _tc[k]
    f = F(font, size); pad = int(8 * S) + 2
    if track:
        widths = [f.getlength(c) + track * size * S for c in txt]; tw = int(sum(widths))
    else:
        tw = int(f.getlength(txt))
    asc, desc = f.getmetrics()
    im = Image.new('L', (tw + 2 * pad, asc + desc + 2 * pad), 0); d = ImageDraw.Draw(im)
    if track:
        x = pad
        for c, w_ in zip(txt, widths): d.text((x, pad), c, font=f, fill=255); x += w_
    else:
        d.text((pad, pad), txt, font=f, fill=255)
    spr = rgba_from_L(im, color)
    r = (spr, pad, pad, im.size[0] / S, im.size[1] / S)
    _tc[k] = r
    return r

_ic = {}
def img(name):
    if name not in _ic:
        a = cv2.imread(os.path.join(HERE, 'img', name + '.jpg'))[:, :, ::-1].astype(np.float32) / 255.0
        _ic[name] = a
    return _ic[name]

def rounded_mask(w, h, r, ss_=2):
    m = Image.new('L', (w * ss_, h * ss_), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, w * ss_ - 1, h * ss_ - 1], radius=r * ss_, fill=255)
    return np.asarray(m.resize((w, h), Image.LANCZOS), np.float32) / 255.0

_cc = {}
def card_sprite(name, w, h, r, title=None, border=0.10):
    """photo card (premultiplied RGBA), cover-fit, rounded, thin light border, optional title over a dark gradient"""
    k = (name, w, h, r, title)
    if k in _cc: return _cc[k]
    pw, ph = max(2, int(w * S)), max(2, int(h * S))
    src = img(name); sh, sw = src.shape[:2]
    sc = max(pw / sw, ph / sh); rs = cv2.resize(src, (int(sw * sc) + 1, int(sh * sc) + 1), interpolation=cv2.INTER_AREA)
    y0 = (rs.shape[0] - ph) // 2; x0 = (rs.shape[1] - pw) // 2; rgb = rs[y0:y0 + ph, x0:x0 + pw].copy()
    if title:
        g = np.clip((np.linspace(0, 1, ph) - 0.45) / 0.55, 0, 1)[:, None, None] ** 1.5
        rgb *= (1 - 0.78 * g)
        im = Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8)); d = ImageDraw.Draw(im)
        f = F('InterDisplay-Bold', h * 0.105)
        d.text((int(w * 0.06 * S), int(ph - h * 0.20 * S)), title, font=f, fill=(255, 255, 255))
        rgb = np.asarray(im, np.float32) / 255
    m = rounded_mask(pw, ph, int(r * S))
    inner = cv2.erode(m, np.ones((3, 3), np.uint8), iterations=max(1, int(1.5 * S)))
    edge = np.clip(m - inner, 0, 1)[..., None]
    rgb = rgb * (1 - edge) + border * 8 * edge * np.ones(3)
    spr = np.dstack([rgb * m[..., None], m]).astype(np.float32)
    _cc[k] = spr
    return spr

# ---------------------------------------------------------------- compositing
def place(fr, spr, quad, blur=0.0, op=1.0):
    """warp a premultiplied RGBA sprite onto the quad (TL,TR,BR,BL, screen px) and composite 'over'"""
    if op <= 0.003: return None
    q = np.float32(quad)
    pad = int(blur * 3) + 2
    x0, y0 = np.floor(q.min(0)).astype(int) - pad; x1, y1 = np.ceil(q.max(0)).astype(int) + pad
    X0, Y0, X1, Y1 = max(x0, 0), max(y0, 0), min(x1, W), min(y1, H)
    h, w = spr.shape[:2]
    src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    M = cv2.getPerspectiveTransform(src, q)
    if X1 <= X0 or Y1 <= Y0: return M
    Ml = cv2.getPerspectiveTransform(src, q - np.float32([X0, Y0]))
    out = cv2.warpPerspective(spr, Ml, (X1 - X0, Y1 - Y0), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    if blur > 0.35: out = cv2.GaussianBlur(out, (0, 0), blur)
    if op < 1: out *= op
    roi = fr[Y0:Y1, X0:X1]
    roi *= (1 - out[..., 3:4]); roi += out[..., :3]
    return M

def mapM(M, pts):
    p = np.float32(pts).reshape(-1, 1, 2)
    return cv2.perspectiveTransform(p, M).reshape(-1, 2)

def rect_quad(cx, cy, w, h, rot=0.0):
    c, s_ = math.cos(rot), math.sin(rot)
    pts = []
    for dx, dy in ((-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)):
        pts.append((cx + dx * c - dy * s_, cy + dx * s_ + dy * c))
    return pts

def add_glow(fr, x, y, sigma, color, amp, sx=1.0, sy=1.0):
    """additive gaussian blob (screen px), optionally stretched (sx, sy) - for the line's hot head and flares"""
    rx, ry = int(sigma * sx * 3.2) + 1, int(sigma * sy * 3.2) + 1
    x0, y0, x1, y1 = int(x) - rx, int(y) - ry, int(x) + rx + 1, int(y) + ry + 1
    X0, Y0, X1, Y1 = max(x0, 0), max(y0, 0), min(x1, W), min(y1, H)
    if X1 <= X0 or Y1 <= Y0: return
    yy, xx = np.mgrid[Y0:Y1, X0:X1].astype(np.float32)
    g = np.exp(-(((xx - x) / (sigma * sx)) ** 2 + ((yy - y) / (sigma * sy)) ** 2) / 2) * amp
    fr[Y0:Y1, X0:X1] += g[..., None] * np.asarray(color, np.float32)

# ---------------------------------------------------------------- THE line (every scene draws it through this)
def light(fr, pts, a=0.0, b=1.0, wd=7.0, heat=1.0, op=1.0, head=1.0, cool=0.0, glow=1.0):
    """The TALEVENTURE light line. pts: polyline in screen px. Draws the part between arc fractions a..b.
    heat: white-hot core; head: brightness of the leading dot; cool: 0 = light, 1 = solid printed ink."""
    if op <= 0.003 or b - a <= 1e-4: return None
    pts = np.float32(pts)
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1); L = np.r_[0, np.cumsum(seg)]; tot = L[-1]
    if tot < 0.5: return None
    sa, sb = a * tot, b * tot
    n = max(2, int((sb - sa) / max(1.5, 2 * S)) + 2)
    s_ = np.linspace(sa, sb, n)
    q = np.stack([np.interp(s_, L, pts[:, 0]), np.interp(s_, L, pts[:, 1])], 1)
    wpx = max(1.0, wd * S); g1, g2 = 9 * S * glow + 1, 30 * S * glow + 1
    pad = int(g2 * 3 + wpx + 4)
    x0, y0 = np.floor(q.min(0)).astype(int) - pad; x1, y1 = np.ceil(q.max(0)).astype(int) + pad
    X0, Y0, X1, Y1 = max(x0, 0), max(y0, 0), min(x1, W), min(y1, H)
    hp = q[-1]
    if X1 > X0 and Y1 > Y0:
        core = np.zeros((Y1 - Y0, X1 - X0), np.uint8)
        k = max(1, n // 32)
        for i in range(0, n - 1, k):
            j = min(n - 1, i + k); u = (s_[i] - sa) / max(sb - sa, 1e-6)
            inten = (0.42 + 0.58 * u ** 1.6) if head > 0 else 0.9
            seg_pts = np.int32(np.round((q[i:j + 1] - [X0, Y0]) * 16))
            cv2.polylines(core, [seg_pts], False, int(255 * inten), max(1, int(round(wpx))), cv2.LINE_AA, shift=4)
        c = core.astype(np.float32) / 255
        gl = cv2.GaussianBlur(c, (0, 0), g1) * 1.1 + cv2.GaussianBlur(c, (0, 0), g2) * 0.75
        gl *= (1 - cool)
        hot = ACC + (WHITE - ACC) * (0.72 * heat * (1 - cool))
        lay = c[..., None] * hot + gl[..., None] * ACC * 1.35
        fr[Y0:Y1, X0:X1] += lay * op
    if head > 0 and cool < 1:
        hh = head * op * (1 - cool)
        add_glow(fr, hp[0], hp[1], 7 * S + 1, WHITE, 1.3 * hh)
        add_glow(fr, hp[0], hp[1], 22 * S + 1, ACC, 0.75 * hh)
        add_glow(fr, hp[0], hp[1], 5 * S + 1, ACC * 0.8 + 0.2, 0.55 * hh, sx=14, sy=0.7)      # anamorphic flare
    return hp

def path_len(pts):
    pts = np.float32(pts); return float(np.linalg.norm(np.diff(pts, axis=0), axis=1).sum())

def bez(p0, p1, p2, p3, n=40):
    t = np.linspace(0, 1, n)[:, None]
    p0, p1, p2, p3 = (np.float32(p) for p in (p0, p1, p2, p3))
    return (1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1 + 3 * (1 - t) * t ** 2 * p2 + t ** 3 * p3

# ---------------------------------------------------------------- camera (design units -> screen px)
class Cam:
    def __init__(self, zoom=1.0, cx=540, cy=960, dx=0, dy=0, roll=0.0):
        self.z, self.cx, self.cy, self.dx, self.dy, self.r = zoom, cx, cy, dx, dy, roll
    def P(self, pts):
        p = np.float32(pts).reshape(-1, 2)
        c, s_ = math.cos(self.r), math.sin(self.r)
        x = (p[:, 0] - self.cx) * self.z; y = (p[:, 1] - self.cy) * self.z
        X = x * c - y * s_ + 540 + self.dx; Y = x * s_ + y * c + 960 + self.dy
        return np.stack([X, Y], 1) * S

def drift(t):
    return 7 * math.sin(0.53 * t) + 3 * math.sin(1.31 * t), 9 * math.sin(0.41 * t + 1), 0.004 * math.sin(0.33 * t)

def shake(t, t0, amp=16, decay=13, freq=70):
    if t < t0: return 0.0, 0.0
    e = math.exp(-(t - t0) * decay) * amp
    return e * math.sin((t - t0) * freq * 1.3 + 1), e * math.sin((t - t0) * freq)

# ---------------------------------------------------------------- stage: background, grain, vignette
_yy, _xx = np.mgrid[0:H // 8 + 1, 0:W // 8 + 1].astype(np.float32) * 8 / S
def background(t, bright=1.0):
    gx, gy = 540 + 170 * math.sin(0.23 * t), 860 + 260 * math.sin(0.17 * t + 1.1)
    br = (0.85 + 0.15 * math.sin(1.7 * t)) * bright
    g = np.exp(-(((_xx - gx) ** 2 + (_yy - gy) ** 2) / (2 * 560 ** 2)))[..., None] * np.float32([0.105, 0.045, 0.020]) * br
    g += np.exp(-((_xx + 60) ** 2 + (_yy + 120) ** 2) / (2 * 720 ** 2))[..., None] * np.float32([0.030, 0.040, 0.055])
    g += np.float32([0.027, 0.027, 0.027])
    return cv2.resize(g, (W, H), interpolation=cv2.INTER_CUBIC)

_vy, _vx = np.mgrid[0:H, 0:W].astype(np.float32)
VIG = (1 - 0.38 * (((_vx / W - 0.5) * 1.15) ** 2 + ((_vy / H - 0.47) * 0.95) ** 2) ** 1.1 * 2.2).clip(0.35, 1)[..., None]
del _vy, _vx

def finish(fr, fi):
    fr *= VIG
    rng = np.random.default_rng(fi * 7919 + 13)
    gr = rng.standard_normal((H // 2 + 1, W // 2 + 1)).astype(np.float32)
    gr = cv2.resize(gr, (W, H), interpolation=cv2.INTER_LINEAR)[:H, :W]
    fr += gr[..., None] * 0.016
    hi = fr > 0.85
    fr[hi] = 0.85 + 0.15 * np.tanh((fr[hi] - 0.85) / 0.15)
    return np.clip(fr, 0, 1)

# ---------------------------------------------------------------- shared props
WM_TXT, WM_SIZE, WM_Y, LINE_Y = 'TALEVENTURE', 112, 900, 1000
def wordmark_geom():
    spr, ox, oy, w, h = text_sprite(WM_TXT, WM_SIZE, 'InterDisplay-Black', track=0.01)
    return spr, ox, oy, w, h

def wm_line_pts(cam):
    spr, ox, oy, w, h = wordmark_geom()
    x0 = 540 - w / 2 + ox / S + 4; x1 = 540 + w / 2 - ox / S - 4
    return cam.P([(x0, LINE_Y), (x1, LINE_Y)]), x0, x1

def draw_wordmark(fr, cam, reveal=1.0, op=1.0, blur=0.0, y=WM_Y, scale=1.0, edge_glow=True):
    """'TALEVENTURE' revealed left->right by the light running under it (reveal 0..1 = wipe position)"""
    spr, ox, oy, w, h = wordmark_geom()
    if reveal < 1:
        sw = spr.shape[1]; xs = np.arange(sw, dtype=np.float32)
        edge = reveal * (sw + 120 * S) - 60 * S
        m = np.clip((edge - xs) / (70 * S), 0, 1)
        spr = spr * m[None, :, None]
    cx = 540
    quad = cam.P(rect_quad(cx, y + 6 * scale, w * scale, h * scale))
    place(fr, spr, quad, blur=blur, op=op)
    if edge_glow and 0 < reveal < 1:
        p = cam.P([(lerp(540 - w / 2, 540 + w / 2, reveal), y)])[0]
        add_glow(fr, p[0], p[1], 55 * S, ACC, 0.18 * op, sx=0.6, sy=1.6)

# phone ------------------------------------------------------------------------------------
PW, PH = 640, 1386
SCR = (22, 22, 618, 1364)                     # screen rect inside the phone sprite (design px)
_phone_body = {}
def phone_body():
    k = S
    if k in _phone_body: return _phone_body[k]
    w, h = int(PW * S), int(PH * S); ss_ = 2
    im = Image.new('RGBA', (w * ss_, h * ss_), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    R = int(96 * S * ss_)
    # titanium frame: layered rounded rects, light top-left, darker bottom-right
    for i, col in enumerate([(70, 70, 72), (150, 148, 144), (196, 193, 188), (120, 118, 116), (40, 40, 42)]):
        inset = int(i * 2.2 * S * ss_)
        d.rounded_rectangle([inset, inset, w * ss_ - 1 - inset, h * ss_ - 1 - inset], radius=max(2, R - inset), fill=col + (255,))
    inset = int(11 * S * ss_)
    d.rounded_rectangle([inset, inset, w * ss_ - 1 - inset, h * ss_ - 1 - inset], radius=R - inset, fill=(4, 4, 5, 255))
    im = im.resize((w, h), Image.LANCZOS)
    a = np.asarray(im, np.float32) / 255
    # soft specular sweep on the frame
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    spec = np.exp(-((xx / w + yy / h * 0.6 - 0.35) ** 2) / 0.02) * 0.25
    rgb = a[..., :3] + spec[..., None] * (a[..., :3] > 0.3)
    spr = np.dstack([np.clip(rgb, 0, 1) * a[..., 3:4], a[..., 3:4]]).astype(np.float32)
    smask = rounded_mask(int((SCR[2] - SCR[0]) * S), int((SCR[3] - SCR[1]) * S), int(76 * S))
    _phone_body[k] = (spr, smask)
    return _phone_body[k]

def phone_sprite(screen_rgb):
    """phone body + screen content (HxWx3 float, screen-sized) -> premultiplied RGBA"""
    body, smask = phone_body()
    spr = body.copy()
    x0, y0 = int(SCR[0] * S), int(SCR[1] * S)
    sh, sw = smask.shape
    sc = screen_rgb[:sh, :sw]
    m = smask[..., None]
    reg = spr[y0:y0 + sh, x0:x0 + sw]
    reg[..., :3] = reg[..., :3] * (1 - m) + sc * m
    # dynamic island
    iw, ih = int(150 * S), int(42 * S)
    isl = rounded_mask(iw, ih, ih // 2)
    ix, iy = int((PW / 2 - 75) * S), int(44 * S)
    spr[iy:iy + ih, ix:ix + iw, :3] *= (1 - isl[..., None])
    return spr

class Screen:
    """drawing helper for the phone UI in screen-local design px (596 x 1342), dark mode"""
    BG, CARD, MUTED = (15, 17, 17), (33, 36, 38), (150, 155, 160)
    def __init__(self):
        self.w, self.h = SCR[2] - SCR[0], SCR[3] - SCR[1]
        self.im = Image.new('RGB', (int(self.w * S), int(self.h * S)), self.BG)
        self.d = ImageDraw.Draw(self.im)
    def s(self, *v): return [int(round(x * S)) for x in v]
    def text(self, xy, txt, size, font='Inter-SemiBold', fill=(255, 255, 255), anchor='la'):
        self.d.text(tuple(self.s(*xy)), txt, font=F(font, size), fill=fill, anchor=anchor)
    def rrect(self, box, r, fill=None, outline=None, width=1):
        self.d.rounded_rectangle(self.s(*box), radius=int(r * S), fill=fill, outline=outline, width=max(1, int(width * S)))
    def status(self):
        self.text((44, 30), '9:41', 22, 'Inter-SemiBold')
        for i in range(4): self.rrect((470 + i * 9, 44 - i * 4, 476 + i * 9, 52), 1, fill=(255, 255, 255))
        self.rrect((515, 34, 552, 52), 5, outline=(255, 255, 255), width=2); self.rrect((519, 38, 543, 48), 2, fill=(255, 255, 255))
    def mag(self, x, y, r=10, col=(150, 155, 160)):
        self.d.ellipse(self.s(x - r, y - r, x + r, y + r), outline=col, width=max(1, int(2.6 * S)))
        self.d.line(self.s(x + r * .7, y + r * .7, x + r * 1.5, y + r * 1.5), fill=col, width=max(1, int(3 * S)))
    def paste_img(self, name, box, r=16):
        x0, y0, x1, y1 = box; w, h = int((x1 - x0) * S), int((y1 - y0) * S)
        spr = card_sprite(name, (x1 - x0), (y1 - y0), r)
        rgb = (spr[..., :3] * 255).astype(np.uint8); a = (spr[..., 3] * 255).astype(np.uint8)
        self.im.paste(Image.fromarray(rgb), (int(x0 * S), int(y0 * S)), Image.fromarray(a))
    def arr(self): return np.asarray(self.im, np.float32) / 255

CARDS = [('p09b', 'From Dinosaurs to Humans'), ('e01', 'How Earth Was Born'), ('p07', 'The Age of Giants'),
         ('h05', 'The First Artists'), ('l04', 'Life Leaves the Sea'), ('b08', 'Our Blue Planet')]
QUERY = 'dinosaurs to humans'
SUGG = ['dinosaurs to humans', 'dinosaurs to humans full story', 'dinosaurs to humans evolution', 'dinosaurs extinction asteroid']

def grid_box(i):
    col, row = i % 2, i // 2
    x0 = 24 + col * 286; y0 = 300 + row * 236
    return (x0, y0, x0 + 262, y0 + 147)

def screen_search(t):
    sc = Screen(); sc.status()
    sc.text((24, 92), 'Ideas', 46, 'InterDisplay-Bold')
    sc.rrect((24, 172, 572, 244), 36, fill=sc.CARD)
    sc.mag(62, 207)
    n = int(len(QUERY) * sg(t, 2.50, 3.30))
    typed = QUERY[:n]
    if n == 0: sc.text((92, 191), 'Search stories', 27, 'Inter-Regular', fill=sc.MUTED)
    else: sc.text((92, 191), typed, 27, 'Inter-Medium')
    if 2.4 < t < 3.45 and (int(t * 3.2) % 2 == 0 or 2.5 < t < 3.3):
        cx = 92 + F('Inter-Medium', 27).getlength(typed) / S + 3
        sc.rrect((cx, 190, cx + 3, 226), 1, fill=ACC8)
    rows_op = sg(t, 2.62, 2.75) * (1 - sg(t, 3.30, 3.42))
    if rows_op > 0 and n > 0:
        for i, sgg in enumerate(SUGG):
            if not sgg.startswith(typed[:max(1, min(n, 9))]): continue
            y = 286 + i * 82; c = int(255 * rows_op)
            sc.mag(44, y + 22, 9, col=tuple(int(v * rows_op) for v in sc.MUTED))
            m = min(len(typed), len(sgg))
            sc.text((76, y + 6), sgg[:m], 27, 'Inter-SemiBold', fill=(c, c, c))
            w0 = F('Inter-SemiBold', 27).getlength(sgg[:m]) / S
            sc.text((76 + w0, y + 6), sgg[m:], 27, 'Inter-Regular', fill=tuple(int(v * rows_op) for v in sc.MUTED))
            sc.d.line(sc.s(76, y + 66, 572, y + 66), fill=(int(40 * rows_op),) * 3, width=max(1, int(S)))
    grid_op = sg(t, 3.30, 3.42)
    if grid_op > 0:
        sc.text((24, 262), 'Top stories', 24, 'Inter-SemiBold', fill=sc.MUTED)
        for i, (nm, ttl) in enumerate(CARDS):
            if t > 3.40: continue                  # lifted off the screen: drawn as 3D cards instead
            sc.paste_img(nm, grid_box(i), 16)
    return sc.arr()

def screen_project(t):
    sc = Screen(); sc.status()
    sc.paste_img('p09b', (0, 0, 596, 380), 0)
    sc.d.ellipse(sc.s(22, 64, 70, 112), fill=(0, 0, 0)); sc.d.line(sc.s(52, 76, 40, 88, 52, 100), fill=(255, 255, 255), width=max(1, int(3 * S)))
    sc.text((28, 404), 'From Dinosaurs', 44, 'InterDisplay-Bold'); sc.text((28, 456), 'to Humans', 44, 'InterDisplay-Bold')
    sc.text((28, 522), 'Episode 1  ·  11:32  ·  2K  ·  92 shots', 23, 'Inter-Medium', fill=sc.MUTED)
    for i in range(5): sc.text((28 + i * 30, 566), '★', 26, 'Inter-SemiBold', fill=ACC8)
    sc.text((186, 568), '4.9', 23, 'Inter-SemiBold', fill=(230, 230, 230))
    sc.text((28, 620), '4.5 billion years in eleven minutes:', 24, 'Inter-Regular', fill=(205, 208, 210))
    sc.text((28, 654), 'the first cells, the giants, the asteroid', 24, 'Inter-Regular', fill=(205, 208, 210))
    sc.text((28, 688), 'and the first humans.', 24, 'Inter-Regular', fill=(205, 208, 210))
    sc.text((28, 748), 'Ready to render', 25, 'Inter-SemiBold', fill=(230, 230, 230))
    sc.text((222, 748), 'Today', 25, 'Inter-SemiBold', fill=ACC8)
    # render button (the line fills it), save button
    fill = sg(t, 5.50, 5.97)
    press = 1 - 0.035 * math.sin(math.pi * sg(t, 6.0, 6.12))
    bx0, by0, bx1, by1 = 24, 812, 572, 900
    cx, cy = (bx0 + bx1) / 2, (by0 + by1) / 2
    hw, hh = (bx1 - bx0) / 2 * press, (by1 - by0) / 2 * press
    sc.rrect((cx - hw, cy - hh, cx + hw, cy + hh), 44, fill=(42, 45, 47))
    if fill > 0:
        m = Image.new('L', sc.im.size, 0); md = ImageDraw.Draw(m)
        md.rounded_rectangle(sc.s(cx - hw, cy - hh, cx + hw, cy + hh), radius=int(44 * S), fill=255)
        md.rectangle(sc.s(cx - hw + fill * 2 * hw, 0, 2000, 2000), fill=0)
        sc.im.paste(ACC8, (0, 0), m)
    done = t > 6.03
    label = 'Rendering…' if done else 'Render video'
    sc.text((cx, cy), label, 30, 'InterDisplay-Bold', fill=(255, 255, 255) if fill > 0.5 else (235, 235, 235), anchor='mm')
    sc.rrect((24, 920, 572, 1008), 44, outline=(90, 94, 98), width=2)
    sc.text((298, 964), 'Save idea', 28, 'InterDisplay-SemiBold', fill=(225, 225, 225), anchor='mm')
    # toast
    to = sg(t, 6.10, 6.32) * (1 - sg(t, 6.95, 7.1))
    if to > 0:
        y = lerp(1360, 1170, eo(sg(t, 6.10, 6.38)))
        sc.rrect((24, y, 572, y + 112), 26, fill=(36, 40, 42))
        sc.d.ellipse(sc.s(48, y + 30, 100, y + 82), fill=ACC8)
        sc.d.line(sc.s(62, y + 57, 72, y + 67, 88, y + 46), fill=(255, 255, 255), width=max(1, int(5 * S)))
        sc.text((120, y + 26), 'Render started', 28, 'InterDisplay-Bold')
        sc.text((120, y + 62), '2,160 chunks on 4 render farms', 22, 'Inter-Regular', fill=sc.MUTED)
    return sc.arr(), (cx - hw, cy, cx + hw, cy), (cx, cy)

def screen_player(t, prog=0.0):
    sc = Screen(); sc.status()
    # the player area (16:9) is where the floating frame lands; keep it black, the frame is composited on top
    sc.d.rectangle(sc.s(0, 120, 596, 455), fill=(0, 0, 0))
    sc.text((24, 482), 'From Dinosaurs to Humans', 32, 'InterDisplay-Bold')
    sc.text((24, 526), 'TALEVENTURE  ·  New  ·  Episode 1', 22, 'Inter-Medium', fill=sc.MUTED)
    sc.d.ellipse(sc.s(24, 580, 84, 640), fill=ACC8)
    sc.text((54, 610), 'T', 30, 'InterDisplay-Black', anchor='mm')
    sc.text((100, 592), 'TALEVENTURE', 25, 'InterDisplay-Bold'); sc.text((100, 624), 'Stories in 3D', 20, 'Inter-Regular', fill=sc.MUTED)
    sc.rrect((420, 588, 572, 634), 23, fill=(245, 245, 245)); sc.text((496, 611), 'Subscribe', 21, 'InterDisplay-Bold', fill=(15, 15, 15), anchor='mm')
    for i, (nm, ttl) in enumerate(CARDS[1:4]):
        y = 676 + i * 180
        sc.paste_img(nm, (24, y, 264, y + 135), 14)
        sc.text((284, y + 8), ttl, 25, 'InterDisplay-Bold'); sc.text((284, y + 46), 'TALEVENTURE', 20, 'Inter-Regular', fill=sc.MUTED)
    return sc.arr()

# ---------------------------------------------------------------- 3D helpers (cards, city)
def proj3(pts, f=1500.0, c=(540, 960)):
    """simple perspective: (x, y, z) design px, z into the screen"""
    p = np.float32(pts).reshape(-1, 3); k = f / (f + p[:, 2])
    return np.stack([c[0] + (p[:, 0] - c[0]) * k, c[1] + (p[:, 1] - c[1]) * k], 1), k

def card_quad3(cx, cy, cz, w, h, yaw=0.0, roll=0.0, pitch=0.0):
    pts = []
    for dx, dy in ((-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)):
        x, y, z = dx * math.cos(roll) - dy * math.sin(roll), dx * math.sin(roll) + dy * math.cos(roll), 0.0
        x, z = x * math.cos(yaw) + z * math.sin(yaw), -x * math.sin(yaw) + z * math.cos(yaw)
        y, z = y * math.cos(pitch) - z * math.sin(pitch), y * math.sin(pitch) + z * math.cos(pitch)
        pts.append((cx + x, cy + y, cz + z))
    q, k = proj3(pts)
    return q, float(k.mean())

class Cam3:
    """look-at camera for the render city (world: x right, y forward, z up)"""
    def __init__(self, target, dist, pitch, yaw, f=1350, center=(540, 960)):
        self.t = np.float32(target)
        cp, sp, cy_, sy_ = math.cos(pitch), math.sin(pitch), math.cos(yaw), math.sin(yaw)
        self.pos = self.t + dist * np.float32([cp * sy_, -cp * cy_, sp])
        fwd = self.t - self.pos; fwd /= np.linalg.norm(fwd)
        up = np.float32([0, 0, 1]) if abs(fwd[2]) < 0.999 else np.float32([0, 1, 0])
        right = np.cross(fwd, up); right /= np.linalg.norm(right)
        upv = np.cross(right, fwd)
        self.R = np.stack([right, -upv, fwd]); self.f = f; self.c = center
    def P(self, pts):
        p = (np.float32(pts).reshape(-1, 3) - self.pos) @ self.R.T
        z = np.maximum(p[:, 2], 1.0)
        return np.stack([self.c[0] + p[:, 0] * self.f / z, self.c[1] + p[:, 1] * self.f / z], 1), p[:, 2]

rng0 = np.random.default_rng(7)
CITY_N = 6
BLOCKS = []
for gx in range(-CITY_N, CITY_N + 1):
    for gy in range(-11, 12):
        BLOCKS.append(dict(x=gx * 100.0, y=gy * 100.0, h=float(rng0.uniform(18, 150) * (1.25 if abs(gx) + abs(gy) < 4 else 1)),
                           s=float(rng0.uniform(56, 72)), lit=rng0.random((4, 3)), d=math.hypot(gx, gy),
                           hue=int(rng0.integers(0, 3))))
ROUTE = [(-650, -450), (-450, -450), (-450, -250), (-250, -250), (-250, -50), (-50, -50), (-50, 150), (150, 150), (150, 250)]
PIN = (150, 300)

def draw_city(fr, t, cam3, rise, route_b, cam2):
    lay = np.zeros((H, W, 3), np.uint8)
    # ground + street grid
    g = [(-720, -1200, 0), (720, -1200, 0), (720, 1200, 0), (-720, 1200, 0)]
    gq, gz = cam3.P(g)
    if (gz > 1).all():
        cv2.fillConvexPoly(lay, np.int32(cam2.P(gq) * 16), (12, 10, 10), cv2.LINE_AA, 4)
    for k in range(-CITY_N, CITY_N + 1):
        v = k * 100 + 50
        for a, b in (((v, -1150, 0.5), (v, 1150, 0.5)), ((-700, v, 0.5), (700, v, 0.5)), ((-700, v + 500, 0.5), (700, v + 500, 0.5)), ((-700, v - 500, 0.5), (700, v - 500, 0.5))):
            q, z = cam3.P([a, b])
            if (z > 1).all():
                cv2.line(lay, tuple(np.int32(cam2.P(q)[0] * 16)), tuple(np.int32(cam2.P(q)[1] * 16)), (26, 24, 24), max(1, int(1.2 * S)), cv2.LINE_AA, 4)
    # blocks, far to near
    order = sorted(BLOCKS, key=lambda b: -np.linalg.norm(np.float32([b['x'], b['y'], b['h'] / 2]) - cam3.pos))
    for b in order:
        rz = ss(cl((rise - b['d'] * 0.05) / 0.5))
        if rz <= 0: continue
        hgt = b['h'] * rz; s2 = b['s'] / 2; x, y = b['x'], b['y']
        top = [(x - s2, y - s2, hgt), (x + s2, y - s2, hgt), (x + s2, y + s2, hgt), (x - s2, y + s2, hgt)]
        bot = [(x - s2, y - s2, 0), (x + s2, y - s2, 0), (x + s2, y + s2, 0), (x - s2, y + s2, 0)]
        faces = []
        for i in range(4):
            j = (i + 1) % 4; quad = [bot[i], bot[j], top[j], top[i]]
            cen = np.mean(np.float32(quad), 0); nrm = cen[:2] - np.float32([x, y])
            view = cam3.pos[:2] - cen[:2]
            if np.dot(nrm, view) > 0: faces.append((quad, 0.55 + 0.25 * (i % 2)))
        faces.append((top, 1.0))
        for quad, sh in faces:
            q, z = cam3.P(quad)
            if (z <= 1).any(): continue
            col = np.float32([30, 30, 34]) * sh if sh < 1 else np.float32([44, 42, 46])
            cv2.fillConvexPoly(lay, np.int32(cam2.P(q) * 16), tuple(int(c) for c in col[::-1]), cv2.LINE_AA, 4)
            if sh < 1 and hgt > 30:                          # window strips: render nodes at work
                for r in range(1, int(hgt // 22)):
                    zz = r * 22.0
                    if zz > hgt - 6: break
                    lit = b['lit'][r % 4, int(sh * 10) % 3]
                    if lit < 0.45: continue
                    p0 = np.float32(quad[0]) + (np.float32(quad[1]) - np.float32(quad[0])) * 0.15; p1 = np.float32(quad[0]) + (np.float32(quad[1]) - np.float32(quad[0])) * 0.85
                    p0[2] = p1[2] = zz
                    qq, zq = cam3.P([p0, p1])
                    if (zq <= 1).any(): continue
                    warm = (lit - 0.45) / 0.55
                    c = (40 + 150 * warm, 90 + 70 * warm, 140 + 100 * warm) if b['hue'] else (60, 120, 230)
                    cv2.line(lay, tuple(np.int32(cam2.P(qq)[0] * 16)), tuple(np.int32(cam2.P(qq)[1] * 16)), c, max(1, int(2 * S)), cv2.LINE_AA, 4)
    f = lay.astype(np.float32)[:, :, ::-1] / 255
    m = (lay.max(2) > 0)[..., None]
    fr[:] = np.where(m, f + fr * 0.15, fr)
    # the route = the line
    rq, rz_ = cam3.P([(x, y, 3) for x, y in ROUTE])
    return cam2.P(rq)

def frosted(fr, box, op=1.0, r=40):
    """frosted glass card: blurred, darkened backdrop + faint white tint and a hairline border (box in screen px / S)"""
    x0, y0, x1, y1 = [int(v * S) for v in box]
    x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, W), min(y1, H)
    if x1 <= x0 or y1 <= y0 or op <= 0: return
    roi = fr[y0:y1, x0:x1]
    bl = cv2.GaussianBlur(roi, (0, 0), 26 * S + 1) * 0.5 + 0.055
    m = rounded_mask(x1 - x0, y1 - y0, int(r * S))
    inner = cv2.erode(m, np.ones((3, 3), np.uint8), iterations=max(1, int(1.5 * S)))
    m3 = m[..., None] * op
    roi[:] = roi * (1 - m3) + bl * m3 + (m - inner)[..., None] * 0.22 * op

def draw_text(fr, cam, txt, size, x, y, font='InterDisplay-Bold', color=(1, 1, 1), op=1.0, anchor='c', blur=0.0, scale=1.0):
    spr, ox, oy, w, h = text_sprite(txt, size, font, color)
    cx = x if anchor == 'c' else x + w / 2 - ox / S if anchor == 'l' else x - w / 2 + ox / S
    place(fr, spr, cam.P(rect_quad(cx, y, w * scale, h * scale)), blur=blur, op=op)
    return cx - w / 2 + ox / S, cx + w / 2 - ox / S

def tracker(fr, cam, t, box, step, op):
    x0, y0, x1, y1 = box
    q = cam.P([(x0, y0), (x1, y1)]) / S
    frosted(fr, (q[0][0], q[0][1], q[1][0], q[1][1]), op)
    done = t > 9.6
    draw_text(fr, cam, 'Render complete' if done else 'Rendering', 46, x0 + 44, y0 + 66, 'InterDisplay-Bold', op=op, anchor='l')
    draw_text(fr, cam, '2,160 chunks  ·  4 render farms', 27, x0 + 44, y0 + 120, 'Inter-Medium', (0.72, 0.74, 0.76), op=op, anchor='l')
    names = ['Script', 'Voice', 'Render', 'Upload']
    bx0, bx1, by = x0 + 70, x1 - 70, y0 + 196
    pa, pb = cam.P([(bx0, by), (bx1, by)])
    cv2.line(fr, tuple(np.int32(pa * 16)), tuple(np.int32(pb * 16)), (0.25, 0.25, 0.27), max(1, int(5 * S)), cv2.LINE_AA, 4)
    prog = cl(step / 3)
    pc = pa + (pb - pa) * prog
    cv2.line(fr, tuple(np.int32(pa * 16)), tuple(np.int32(pc * 16)), tuple(float(c) * op for c in ACC), max(1, int(5 * S)), cv2.LINE_AA, 4)
    for i, nm in enumerate(names):
        x = lerp(bx0, bx1, i / 3); p = cam.P([(x, by)])[0]
        on = step >= i - 0.02
        col = tuple(float(c) * op for c in (ACC if on else np.float32([0.35, 0.35, 0.37])))
        cv2.circle(fr, tuple(np.int32(p * 16)), int(13 * S * 16), col, -1, cv2.LINE_AA, 4)
        if on: cv2.circle(fr, tuple(np.int32(p * 16)), int(5 * S * 16), (op, op, op), -1, cv2.LINE_AA, 4)
        draw_text(fr, cam, nm, 23, x, by + 46, 'Inter-SemiBold', (0.9, 0.9, 0.9) if on else (0.5, 0.5, 0.52), op=op)

def notification(fr, M, t0, t, op=1.0):
    """iOS-style banner inside the phone screen (M maps screen-local design px -> screen px)"""
    u = eo(sg(t, t0, t0 + 0.35)); o = sg(t, t0, t0 + 0.2) * op
    if o <= 0: return
    y = lerp(-140, 70, u)
    sc_w = SCR[2] - SCR[0]
    w, h = int(548 * S), int(118 * S)
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=int(30 * S), fill=(48, 50, 54, 245))
    d.rounded_rectangle([int(18 * S), int(22 * S), int(92 * S), int(96 * S)], radius=int(18 * S), fill=ACC8)
    d.polygon([(int(46 * S), int(42 * S)), (int(46 * S), int(76 * S)), (int(74 * S), int(59 * S))], fill=(255, 255, 255))
    d.text((int(110 * S), int(22 * S)), 'TALEVENTURE', font=F('InterDisplay-Bold', 23), fill=(255, 255, 255))
    d.text((int(500 * S), int(24 * S)), 'now', font=F('Inter-Regular', 20), fill=(170, 170, 175), anchor='ra')
    d.text((int(110 * S), int(54 * S)), 'Upload complete', font=F('Inter-SemiBold', 23), fill=(240, 240, 240))
    d.text((int(110 * S), int(84 * S)), 'From Dinosaurs to Humans is live', font=F('Inter-Regular', 20), fill=(190, 190, 195))
    a = np.asarray(im, np.float32) / 255
    spr = np.dstack([a[..., :3] * a[..., 3:4], a[..., 3:4]])
    loc = [(24, y), (24 + 548, y), (24 + 548, y + 118), (24, y + 118)]
    place(fr, spr, mapM(M, [((p[0] + SCR[0]) * S, (p[1] + SCR[1]) * S) for p in loc]), op=o)

# ---------------------------------------------------------------- the film: one function of time
def phone_quad(cam, cx, cy, scale=1.0, tilt=0.0, yaw=0.0):
    q, k = card_quad3(cx, cy, 0, PW * scale, PH * scale, yaw=yaw, pitch=tilt)
    return cam.P(q)

def scene(t):
    fr = background(t)
    dx, dy, roll = drift(t)
    # ---------------- S1 + S7 wordmark and its line
    if t < 2.6 or t >= 16.45:
        hero = t >= 16.45
        t0 = 16.80 if hero else 0.17
        sx, sy = shake(t, t0, 18 if not hero else 13)
        zoom = 1.0 + 0.025 * sg(t, t0, t0 + 2.5) if not hero else 1.0 + 0.03 * sg(t, 16.8, 19.2)
        cam = Cam(zoom, 540, 960, dx * 0.4 + sx, dy * 0.4 + sy, roll * 0.5)
        lp, x0, x1 = wm_line_pts(cam)
        if not hero:
            rise = eio(sg(t, 1.60, 2.30))
            wy = lerp(WM_Y, 430, rise); wsc = lerp(1.0, 0.62, rise); wop = 1 - sg(t, 1.95, 2.35)
            reveal = eo(sg(t, 0.23, 0.67), 2)
            draw_wordmark(fr, cam, reveal, op=wop, y=wy, scale=wsc)
            if t < 0.17:                                   # streak rushing in from deep space
                u = eo(sg(t, -0.12, 0.17), 2.2)
                z = lerp(5200, 0, u)
                pts3 = [(x0, LINE_Y, z), (x1, LINE_Y, z)]
                q, k = proj3(pts3)
                tail = [(x0, LINE_Y, z + 900 * (1 - u) + 60), (x1, LINE_Y, z + 900 * (1 - u) + 60)]
                qt, _ = proj3(tail)
                mid = cam.P([(q[0] + q[1]) / 2])[0]; midt = cam.P([(qt[0] + qt[1]) / 2])[0]
                light(fr, cam.P(q), 0, 1, wd=7 * max(0.25, k[0]), heat=1, head=0.6, glow=0.8)
                for j in range(5):                                       # orange strands trailing the streak
                    off = (j - 2) * 30 * k[0]
                    light(fr, np.float32([midt + [off * S * 3, 0], mid + [off * S, 0]]), 0, 1, wd=2, heat=0.4, head=0, op=0.5)
            else:
                ly = lerp(LINE_Y, 430 + (LINE_Y - WM_Y) * 0.62, rise)
                lx0, lx1 = lerp(x0, 540 - (540 - x0) * 0.62, rise), lerp(x1, 540 + (x1 - 540) * 0.62, rise)
                lq = cam.P([(lx0, ly), (lx1, ly)])
                light(fr, lq, 0, 1, wd=7, heat=1 - 0.5 * sg(t, 0.17, 1.2), head=0.25 + 0.75 * (1 - sg(t, 0.67, 1.0)), op=1 - sg(t, 2.0, 2.4))
                if 0.23 <= t <= 0.75:                                    # the light runs d -> s under the name
                    rx = lerp(lq[0][0], lq[1][0], eo(sg(t, 0.23, 0.67), 2))
                    add_glow(fr, rx, lq[0][1], 10 * S, WHITE, 1.1 * (1 - sg(t, 0.62, 0.75)))
                    add_glow(fr, rx, lq[0][1], 34 * S, ACC, 0.6 * (1 - sg(t, 0.62, 0.75)))
                if t < 0.65:                                             # light shards from the slam
                    for j in range(14):
                        ang = (j / 14) * math.tau + 0.4; u = eo(sg(t, 0.17, 0.62), 2)
                        bx = lerp(x0, x1, (j * 0.37) % 1)
                        p0 = (bx + math.cos(ang) * 30 * u, LINE_Y + math.sin(ang) * 30 * u)
                        p1 = (bx + math.cos(ang) * (40 + 260 * u), LINE_Y + math.sin(ang) * (40 + 200 * u))
                        light(fr, cam.P([p0, p1]), 0.4 * u, 1, wd=2.5, heat=0.8, head=0.3, op=(1 - u) * 0.9)
                    add_glow(fr, *cam.P([(540, LINE_Y)])[0], 180 * S, ACC, 0.35 * (1 - sg(t, 0.17, 0.5)) if t > 0.17 else 0, sx=2.2, sy=0.6)
            # the light copy that peels off and drops into the phone's search field
            if 2.05 <= t < 2.6:
                u = eio(sg(t, 2.05, 2.42))
                fq = phone_search_line(t, s23_cam(t, dx, dy, roll))
                src = cam.P([(lx0, ly), (lx1, ly)])
                pts = np.float32([lerp(src[0], fq[0], u), lerp(src[1], fq[1], u)])
                light(fr, pts, 0, 1, wd=6, heat=1, head=1, op=1)
        else:
            # S7 hero: the line arrives from the type and slots under the name on the hit (16.80)
            if t < 16.80:
                u = ei(sg(t, 16.50, 16.80), 2.4)
                src = s6_line_pts(Cam(1.0 + 0.02 * sg(t, 13.3, 16.5), 540, 960, dx, dy, roll))
                a0, a1 = src[0], src[-1]
                pts = np.float32([lerp(a0, lp[0], u), lerp(a1, lp[1], u)])
                light(fr, pts, 0, 1, wd=6, heat=1, head=1, op=0.35 + 0.65 * u)
            else:
                reveal = eo(sg(t, 16.85, 17.30), 2)
                dof = 26 * S * ss(sg(t, 18.55, 19.25))
                wop = 1 - 0.85 * sg(t, 18.8, 19.3)
                draw_wordmark(fr, cam, reveal, op=wop, blur=dof)
                collapse = eio(sg(t, 18.6, 19.0))
                a = collapse * 0.999
                lq = lp
                if t < 19.0:
                    light(fr, lq, a, 1, wd=7, heat=0.6 + 0.4 * (1 - sg(t, 16.8, 17.4)), head=0.8 + 0.4 * collapse,
                          op=1, glow=1 + collapse * 0.5)
                if 17.4 < t < 18.7:                                       # a slow light passing beneath the name
                    rx = lerp(lq[0][0], lq[1][0], ss(sg(t, 17.4, 18.6)))
                    add_glow(fr, rx, lq[0][1], 40 * S, ACC, 0.45 * math.sin(math.pi * sg(t, 17.4, 18.7)), sx=2.5, sy=0.6)
                if t < 17.3:
                    for j in range(12):
                        ang = (j / 12) * math.tau + 0.2; u = eo(sg(t, 16.8, 17.25), 2)
                        bx = lerp(x0, x1, (j * 0.41) % 1)
                        p0 = (bx + math.cos(ang) * 30 * u, LINE_Y + math.sin(ang) * 30 * u)
                        p1 = (bx + math.cos(ang) * (40 + 220 * u), LINE_Y + math.sin(ang) * (40 + 170 * u))
                        light(fr, cam.P([p0, p1]), 0.4 * u, 1, wd=2.5, heat=0.8, head=0.3, op=(1 - u) * 0.8)
                so = sg(t, 17.55, 17.95) * (1 - sg(t, 18.6, 19.0))
                draw_text(fr, cam, 'New stories every week', 30, 540, 1092, 'Inter-Medium', (0.70, 0.71, 0.73), op=so)
                if t >= 19.0:                                             # the head's light becomes a single dot
                    p = lq[1] + (cam.P([(540, 760)])[0] - lq[1]) * ss(sg(t, 19.0, 19.5))
                    pulse = 1 + 0.15 * math.sin(t * 5)
                    add_glow(fr, p[0], p[1], 6 * S + 1, WHITE, 1.25 * pulse)
                    add_glow(fr, p[0], p[1], 22 * S + 1, ACC, 0.75 * pulse)
                if t >= 19.2:
                    eo_ = sg(t, 19.3, 19.75)
                    ec = Cam(1.0 + 0.02 * sg(t, 19.2, 21.2), 540, 960, dx * 0.3, dy * 0.3, 0)
                    draw_text(fr, ec, 'NEW VIDEO', 30, 540, 838, 'InterDisplay-Bold', tuple(ACC), op=eo_)
                    draw_text(fr, ec, 'From Dinosaurs', 92, 540, 940, 'InterDisplay-Black', op=eo_, scale=lerp(0.96, 1, eo(eo_)))
                    draw_text(fr, ec, 'to Humans', 92, 540, 1046, 'InterDisplay-Black', op=eo_, scale=lerp(0.96, 1, eo(eo_)))
                    draw_text(fr, ec, 'Watch now on TALEVENTURE', 31, 540, 1162, 'Inter-Medium', (0.72, 0.72, 0.74), op=sg(t, 19.6, 20.0))
    # ---------------- S2 search / cards, S3 project page
    if 1.7 <= t < 7.3:
        s23(fr, t, dx, dy, roll)
    # ---------------- S4 render city
    if 7.05 <= t < 10.15:
        s4(fr, t, dx, dy, roll)
    # ---------------- S5 the screen
    if 9.9 <= t < 13.6:
        s5(fr, t, dx, dy, roll)
    # ---------------- S6 type
    if 13.15 <= t < 16.8:
        s6(fr, t, dx, dy, roll)
    return fr

def phone_center(t):
    u = sg(t, 1.75, 2.40)
    return 540, lerp(2700, 1000, back(u, 0.9)) if u < 1 else 1000

def phone_search_line(t, cam):
    """screen px of the search field's focus line on the phone"""
    M = phone_M(t, cam)
    return mapM(M, [((SCR[0] + 44) * S, (SCR[1] + 252) * S), ((SCR[0] + 552) * S, (SCR[1] + 252) * S)])

def phone_M(t, cam, extra_zoom=1.0):
    cx, cy = phone_center(t)
    tilt = -0.32 * (1 - eo(sg(t, 1.75, 2.45)))
    q = phone_quad(cam, cx, cy, 1.0, tilt=tilt, yaw=0.05 * math.sin(0.6 * t))
    src = np.float32([[0, 0], [PW * S, 0], [PW * S, PH * S], [0, PH * S]])
    return cv2.getPerspectiveTransform(src, np.float32(q))

#      card, roll, x, y, yaw, z   (z < 0: in front of the phone)
FAN = [(0, 0.0, 540, 640, 0.0, -300), (1, -0.16, 250, 520, 0.38, -90), (2, 0.16, 830, 520, -0.38, -90),
       (3, -0.10, 230, 900, 0.30, -130), (4, 0.10, 850, 900, -0.30, -130), (5, 0.0, 540, 1080, 0.0, -60)]

def s23_cam(t, dx, dy, roll):
    # push toward card 1 (4.2-4.8), then glide to the Render button (5.0-5.5), then fly through the screen (6.75-7.3)
    z = 1.0 + 0.10 * eio(sg(t, 4.15, 4.85)) - 0.10 * eio(sg(t, 4.75, 5.05))
    z += 0.32 * eio(sg(t, 4.95, 5.55)) - 0.12 * eio(sg(t, 6.25, 6.7))
    fz = ei(sg(t, 6.75, 7.30), 3.2)
    z *= 1 + 9.0 * fz
    cxy = lerp2((540, 960), (540, 700), eio(sg(t, 4.15, 4.85)))
    cxy = lerp2(cxy, (540, 960), eio(sg(t, 4.75, 5.05)))
    cxy = lerp2(cxy, (540, 1170), eio(sg(t, 4.95, 5.55)))
    cxy = lerp2(cxy, (540, 900), eio(sg(t, 6.25, 6.9)))
    sx, sy = shake(t, 2.40, 7, 16, 60)
    return Cam(z, cxy[0], cxy[1], dx + sx, dy + sy, roll)

def s23(fr, t, dx, dy, roll):
    cam = s23_cam(t, dx, dy, roll)
    fly = sg(t, 6.75, 7.30)
    if t < 4.85:
        scr = screen_search(t)
    else:
        scr, btn_line, btn_c = screen_project(t)
    spr = phone_sprite(scr)
    cx, cy = phone_center(t)
    tilt = -0.32 * (1 - eo(sg(t, 1.75, 2.45)))
    q = phone_quad(cam, cx, cy, 1.0, tilt=tilt, yaw=0.05 * math.sin(0.6 * t))
    # soft shadow
    if t > 1.9:
        sc = cam.P([(cx, cy + PH / 2 + 30)])[0]
        add_glow(fr, sc[0], sc[1], 120 * S * cam.z, np.float32([-0.02, -0.02, -0.02]), 1.0, sx=2.2, sy=0.35)
    M = place(fr, spr, q, op=1.0)
    if fly > 0.85:
        fr *= 1 - ss(sg(fly, 0.85, 1.0)) * 0.6
    # the focus line of the search field (THE line)
    if 2.38 <= t < 3.42:
        fq = mapM(M, [((SCR[0] + 44) * S, (SCR[1] + 252) * S), ((SCR[0] + 552) * S, (SCR[1] + 252) * S)])
        light(fr, fq, 0, 1, wd=4.5, heat=0.7, head=0.7 + 0.3 * math.sin(t * 9), op=1 - sg(t, 3.3, 3.42) * 0.6)
    # cards lift off into 3D, fan, line traces card 1
    if 3.40 <= t < 5.0:
        u_all = sg(t, 3.40, 4.37)
        items = []
        for i, (nm, ttl) in enumerate(CARDS):
            fi = [f for f in FAN if f[0] == i][0]
            u = eo(sg(t, 3.40 + i * 0.05, 4.10 + i * 0.05), 3)
            b = grid_box(i)
            src_q = mapM(M, [((SCR[0] + b[0]) * S, (SCR[1] + b[1]) * S), ((SCR[0] + b[2]) * S, (SCR[1] + b[1]) * S),
                             ((SCR[0] + b[2]) * S, (SCR[1] + b[3]) * S), ((SCR[0] + b[0]) * S, (SCR[1] + b[3]) * S)])
            wcard, hcard = 470, 264
            z = fi[5] * u
            dq, k = card_quad3(fi[2], fi[3], fi[5], wcard, hcard, yaw=fi[4], roll=fi[1])
            dq = cam.P(dq)
            qq = np.float32(src_q) * (1 - u) + dq * u if u < 1 else dq
            fade = 1.0
            if t > 4.40 and i != 0: fade = 1 - sg(t, 4.40 + 0.04 * i, 4.80)
            items.append((z if u > 0 else 999, i, nm, ttl, qq, fade, u))
        for z, i, nm, ttl, qq, fade, u in sorted(items, key=lambda r: (r[0] if r[6] > 0 else 999, -r[1]), reverse=True):
            if i == 0 and t > 4.62: continue
            spr_c = card_sprite(nm, 470, 264, 26, title=ttl)
            blur = 0 if i == 0 else 1.6 * S * u * (1 + sg(t, 4.0, 4.4) * 2)
            sc_ = np.mean(qq, 0)
            add_glow(fr, sc_[0], sc_[1] + 40 * S, 120 * S, np.float32([-0.03] * 3), 0.9 * u * fade, sx=1.6, sy=0.8)
            place(fr, spr_c, qq, blur=blur, op=fade)
            if i == 0 and 3.95 < t < 4.75:
                loop = list(qq) + [qq[0]]
                pa = eio(sg(t, 3.98, 4.55))
                light(fr, loop, max(0, pa - 0.35), pa, wd=4.5, heat=1, head=1, op=1 - sg(t, 4.5, 4.75))
        # card 1 grows into the project page's hero image
        if 4.55 <= t < 4.95:
            u = eio(sg(t, 4.55, 4.92))
            fi = FAN[0]
            dq, k = card_quad3(fi[2], fi[3], fi[5], 470, 264)
            dq = cam.P(dq)
            hq = mapM(M, [((SCR[0]) * S, (SCR[1]) * S), ((SCR[2]) * S, (SCR[1]) * S), ((SCR[2]) * S, (SCR[1] + 380) * S), ((SCR[0]) * S, (SCR[1] + 380) * S)])
            place(fr, card_sprite('p09b', 470, 264, 26, title=CARDS[0][1]), dq * (1 - u) + np.float32(hq) * u, op=1 - sg(t, 4.86, 4.95))
    if t >= 4.85:
        # the line becomes the Render button's fill; its hot head is the leading edge
        if 5.48 <= t < 6.15:
            a, b = mapM(M, [(btn_line[0] * S + SCR[0] * S, btn_line[1] * S + SCR[1] * S), (btn_line[2] * S + SCR[0] * S, btn_line[3] * S + SCR[1] * S)])
            # come in from the left edge of the frame first
            fill = sg(t, 5.50, 5.97)
            pts = np.float32([a + (a - b) * 0.0, b])
            light(fr, pts, 0, max(0.002, fill), wd=6, heat=1, head=1.1, op=1 - sg(t, 6.0, 6.15))
        if 6.03 <= t < 6.6:                                   # tap
            c = mapM(M, [((btn_c[0] + SCR[0]) * S, (btn_c[1] + SCR[1]) * S)])[0]
            u = eo(sg(t, 6.03, 6.5))
            r = (40 + 380 * u) * S * cam.z
            ring = np.zeros((H, W), np.uint8)
            cv2.circle(ring, tuple(np.int32(c * 16)), int(r * 16), 255, max(1, int(4 * S)), cv2.LINE_AA, 4)
            fr += cv2.GaussianBlur(ring.astype(np.float32) / 255, (0, 0), 3 * S + 1)[..., None] * ACC * (1 - u) * 1.6
            add_glow(fr, c[0], c[1], 50 * S, WHITE, 0.6 * (1 - sg(t, 6.03, 6.25)))
        if 6.60 <= t < 7.3:                                   # the line shoots out of the button and up through the screen
            c = mapM(M, [((btn_c[0] + SCR[0]) * S, (btn_c[1] + SCR[1]) * S)])[0]
            top = np.float32([W * 0.5, -200 * S])
            u = ei(sg(t, 6.60, 7.0), 2)
            pts = np.float32([c, c + (top - c) * u + 1e-3])
            light(fr, pts, max(0, u - 0.6), 1, wd=7, heat=1, head=1.2, op=1 - sg(t, 7.1, 7.3))

def s4(fr, t, dx, dy, roll):
    u = sg(t, 7.05, 7.25)
    lay = background(t, 0.6) * 0.7
    swoop = eio(sg(t, 7.35, 8.7))
    pitch = lerp(math.pi / 2 - 0.001, 0.92, swoop)
    yaw = lerp(-0.15, 0.32, sg(t, 7.2, 10.0))
    dist = lerp(1500, 1250, swoop) - 260 * ei(sg(t, 9.55, 10.1), 2)
    target = (lerp(0, 60, swoop), lerp(0, 90, swoop), 0)
    cam3 = Cam3(target, dist, pitch, yaw)
    cam2 = Cam(1.0 + 0.6 * ei(sg(t, 9.6, 10.15), 2), 540, 960, dx, dy, roll)
    rise = sg(t, 7.2, 8.4) * 1.3
    rq = draw_city(lay, t, cam3, rise, 0, cam2)
    b = eio(sg(t, 7.55, 9.6))
    if b > 0:
        light(lay, rq, 0, b, wd=6, heat=1, head=1.1)
    # the pin
    po = sg(t, 9.35, 9.6)
    if po > 0:
        pq, pz = cam3.P([(PIN[0], PIN[1], 3), (PIN[0], PIN[1], 3 + 60 * back(po))])
        pq = cam2.P(pq)
        cv2.line(lay, tuple(np.int32(pq[0] * 16)), tuple(np.int32(pq[1] * 16)), tuple(float(c) for c in ACC), max(1, int(3 * S)), cv2.LINE_AA, 4)
        cv2.circle(lay, tuple(np.int32(pq[1] * 16)), int(16 * S * 16), tuple(float(c) for c in ACC), -1, cv2.LINE_AA, 4)
        cv2.circle(lay, tuple(np.int32(pq[1] * 16)), int(6 * S * 16), (1, 1, 1), -1, cv2.LINE_AA, 4)
        add_glow(lay, pq[1][0], pq[1][1], 30 * S, ACC, 0.6 * po)
        ring = sg(t, 9.6, 10.1)
        if ring > 0:
            rr = np.zeros((H, W), np.uint8)
            cv2.circle(rr, tuple(np.int32(pq[0] * 16)), int((20 + 140 * ring) * S * 16), 255, max(1, int(3 * S)), cv2.LINE_AA, 4)
            lay += (rr.astype(np.float32) / 255)[..., None] * ACC * (1 - ring)
    # glass card with the 4-step tracker
    co = sg(t, 7.7, 8.1) * (1 - sg(t, 9.75, 10.0))
    if co > 0:
        step = 2 * sg(t, 7.7, 8.2) + 1 * sg(t, 8.2, 9.6) + 0.999 * sg(t, 9.6, 9.75)
        cam_card = Cam(1.0, 540, 960, dx * 0.5, dy * 0.5 + 30 * (1 - eo(sg(t, 7.7, 8.2))), 0)
        tracker(lay, cam_card, t, (70, 1480, 1010, 1770), step, co)
    dive = ss(sg(t, 9.6, 10.15))
    if dive > 0:
        lay = cv2.GaussianBlur(lay, (0, 0), 1 + 40 * S * dive)
    fr[:] = fr * (1 - u) + lay * u if u < 1 else lay

def s5_frame_quad(t, cam, M_phone):
    hover = 14 * math.sin(2.1 * t)
    land = eio(sg(t, 11.55, 12.0))
    fw, fh = 900, 506
    big = rect_quad(540, 760 + hover * (1 - land), fw, fh, rot=0.02 * math.sin(1.3 * t) * (1 - land))
    bq = cam.P(big)
    if M_phone is None or land <= 0: return bq, land
    pl = mapM(M_phone, [((SCR[0]) * S, (SCR[1] + 120) * S), ((SCR[2]) * S, (SCR[1] + 120) * S), ((SCR[2]) * S, (SCR[1] + 455) * S), ((SCR[0]) * S, (SCR[1] + 455) * S)])
    return np.float32(bq) * (1 - land) + np.float32(pl) * land, land

def s5(fr, t, dx, dy, roll):
    u_in = sg(t, 9.9, 10.15)
    lay = background(t)
    sx, sy = shake(t, 12.0, 10, 14, 60)
    cam = Cam(1.0 + 0.04 * sg(t, 10, 13.3) - 0.06 * eio(sg(t, 11.2, 12.0)), 540, 960 + 120 * eio(sg(t, 11.2, 12.0)), dx + sx, dy + sy, roll)
    # the phone rises to receive the frame
    pu = eo(sg(t, 11.0, 11.75), 3)
    M = None
    if pu > 0:
        py = lerp(2700, 1060, pu)
        q, k = card_quad3(540, py, 0, PW, PH)
        q = cam.P(q)
        M = place(lay, phone_sprite(screen_player(t)), q)
    fq, land = s5_frame_quad(t, cam, M)
    if land < 1:
        sc_ = np.mean(fq, 0)
        add_glow(lay, sc_[0], sc_[1] + 300 * S * (1 - land), 260 * S, np.float32([-0.025] * 3), 1.0, sx=1.6, sy=0.25)
    place(lay, card_sprite('p07', 900, 506, 28 * (1 - land) + 2), fq)
    # THE line: in from the top, wraps the frame once, lands on its face as the progress bar and cools into ink
    p = np.float32(fq)
    bar_y = lambda a, b_: a + (b_ - a) * 0.93
    bl, br = p[3] + (p[0] - p[3]) * 0.07 + (p[2] - p[3]) * 0.04, p[2] + (p[1] - p[2]) * 0.07 - (p[2] - p[3]) * 0.04
    entry = np.float32([p[0][0] + (p[1][0] - p[0][0]) * 0.3, -60 * S])
    path = [entry, p[0] + (p[1] - p[0]) * 0.3, p[1], p[2], p[3], p[0], p[0] + (p[1] - p[0]) * 0.3 - (p[1] - p[0]) * 0.001]
    L1 = path_len(path)
    # after the wrap the light settles along the bottom as the progress bar
    wrap = eio(sg(t, 9.95, 10.83))
    cool = ss(sg(t, 10.83, 11.5))
    if t < 10.9:
        light(lay, path, max(0, wrap - 0.42), wrap, wd=5, heat=1, head=1.1)
    prog_end = 0.34 + 0.08 * sg(t, 11.5, 13.3)
    bar = np.float32([bl, bl + (br - bl) * prog_end])
    if t >= 10.7:
        bo = sg(t, 10.7, 10.9)
        light(lay, bar, 0, 1, wd=4 if land < 1 else 3, heat=1 - cool, head=1 - cool * 0.7, cool=cool * 0.75, op=bo)
        if cool > 0.3:
            rest = np.float32([bar[1], br])
            light(lay, rest, 0, 1, wd=2, heat=0, head=0, cool=1, op=0.25 * cool)
    if M is not None:
        notification(lay, M, 12.25, t)
    out = sg(t, 13.1, 13.5)
    if out > 0:
        lay = cv2.GaussianBlur(lay, (0, 0), 1 + 30 * S * out) * (1 - 0.5 * out)
    fr[:] = fr * (1 - u_in) + lay * u_in if u_in < 1 else lay
    return fr

S6_A = [('Stories', 760), ("you've never", 900), ('seen.', 1040)]
S6_B = [('From idea', 860), ('to screen.', 1010)]
FILLS = ['a01', 'e01', 'p07', 'b08', 'h07', 'p09a', 'l04', 'd04', 'p08', 'h05', 'c13', 'k06', 'h03', 'b05']

_lc = {}
def letters_fill(txt, size, t, settle, accent_word=None):
    """text sprite whose letters are filled with frames of the film (each letter its own shot), settling to white"""
    k = (txt, size)
    if k not in _lc:
        f = F('InterDisplay-Black', size); pad = int(10 * S)
        tw = int(f.getlength(txt)); asc, desc = f.getmetrics()
        im = Image.new('L', (tw + 2 * pad, asc + desc + 2 * pad), 0); d = ImageDraw.Draw(im)
        d.text((pad, pad), txt, font=f, fill=255)
        alpha = np.asarray(im, np.float32) / 255
        # per-letter x spans
        spans = []; x = pad
        for i, ch in enumerate(txt):
            w_ = f.getlength(txt[:i + 1]) - f.getlength(txt[:i]); spans.append((int(x), int(x + w_ + 1))); x += w_
        _lc[k] = (alpha, spans, pad)
    alpha, spans, pad = _lc[k]
    h, w = alpha.shape
    rgb = np.ones((h, w, 3), np.float32)
    if settle < 1:
        fill = np.zeros((h, w, 3), np.float32)
        for i, (x0, x1) in enumerate(spans):
            if txt[i] == ' ': continue
            src = img(FILLS[(i * 5 + len(txt)) % len(FILLS)])
            zoom = 1.25 + 0.15 * math.sin(t * 0.8 + i)
            sh_, sw_ = src.shape[:2]
            ww = max(2, x1 - x0); sc = max(h / sh_, ww / sw_) * zoom
            rs = cv2.resize(src, (int(sw_ * sc) + 2, int(sh_ * sc) + 2), interpolation=cv2.INTER_AREA)
            oy = (rs.shape[0] - h) // 2; ox = (rs.shape[1] - ww) // 2 + int(10 * math.sin(t * 1.3 + i))
            ox = int(cl(ox, 0, rs.shape[1] - ww))
            fill[:, x0:x0 + ww] = (rs[oy:oy + h, ox:ox + ww] * 1.25)[:, :min(ww, w - x0)]
        rgb = fill * (1 - settle) + rgb * settle
    if settle < 1:
        er = cv2.erode(alpha, np.ones((3, 3), np.uint8), iterations=max(1, int(2 * S)))
        rim = np.clip(alpha - er, 0, 1)[..., None]
        rgb = rgb * (1 - rim * 0.7 * (1 - settle)) + rim * 0.7 * (1 - settle)
    if accent_word:
        i0 = txt.find(accent_word)
        if i0 >= 0:
            x0, x1 = spans[i0][0], spans[i0 + len(accent_word) - 1][1]
            rgb[:, x0:x1] = rgb[:, x0:x1] * (1 - settle) + ACC * settle
    return np.dstack([rgb * alpha[..., None], alpha]).astype(np.float32), pad

def s6_cam(t, dx, dy, roll):
    return Cam(1.0 + 0.02 * sg(t, 13.3, 16.5), 540, 960, dx, dy, roll)

def s6_line_pts(cam):
    """the line runs from under 'idea' to under 'screen.' (one smooth stroke) - S7 picks it up from here"""
    fB = F('InterDisplay-Black', 132)
    w1 = fB.getlength('From idea') / S; w2 = fB.getlength('to screen.') / S
    xi0 = 540 - w1 / 2 + fB.getlength('From ') / S
    xi1 = 540 + w1 / 2
    y1 = 860 + 92; y2 = 1010 + 92
    x2a, x2b = 540 - w2 / 2 + fB.getlength('to ') / S, 540 + w2 / 2 - 10
    pts = np.concatenate([np.float32([(xi0, y1)]), bez((xi0 + 20, y1), (xi1 + 60, y1), (x2a - 120, y2 - 10), (x2a, y2), 30), np.float32([(x2b, y2)])])
    return cam.P(pts)

def s6(fr, t, dx, dy, roll):
    cam = s6_cam(t, dx, dy, roll)
    u_in = sg(t, 13.15, 13.5)
    lay = background(t)
    settle = ss(sg(t, 14.30, 14.80))
    swap = sg(t, 14.85, 15.15)
    out = sg(t, 16.48, 16.78)
    if swap < 1:
        for li, (txt, y) in enumerate(S6_A):
            spr, pad = letters_fill(txt, 128, t, settle, accent_word='never' if 'never' in txt else None)
            a = eo(sg(t, 13.30 + li * 0.12, 13.80 + li * 0.12))
            sc_ = lerp(0.92, 1.0, a) * (1 + 0.08 * swap)
            h_, w_ = spr.shape[:2]
            q = cam.P(rect_quad(540, y + 40, w_ / S * sc_, h_ / S * sc_))
            place(lay, spr, q, blur=10 * S * swap, op=a * (1 - swap))
    if swap > 0:
        for li, (txt, y) in enumerate(S6_B):
            spr, ox, oy, w_, h_ = text_sprite(txt, 132, 'InterDisplay-Black')
            sc_ = lerp(1.06, 1.0, eo(swap))
            q = cam.P(rect_quad(540, y + 40, w_ * sc_, h_ * sc_))
            place(lay, spr, q, blur=8 * S * (1 - swap), op=swap * (1 - out))
        lb = eio(sg(t, 15.20, 16.00))
        if lb > 0:
            light(lay, s6_line_pts(cam), 0, lb, wd=7, heat=1, head=1.1, op=1 - out * 0.6)
    fr[:] = fr * (1 - u_in) + lay * u_in if u_in < 1 else lay

# ---------------------------------------------------------------- frame = average of sub-frames (motion blur)
def frame(fi):
    t = fi / FPS
    acc = None
    shutter = 0.65 / FPS
    for k in range(SUB):
        ts = t + ((k + 0.5) / SUB - 0.5) * shutter if SUB > 1 else t
        f = scene(max(0.0, ts))
        acc = f if acc is None else acc + f
    return finish(acc / SUB, fi)

def save(fr, path):
    cv2.imwrite(path, (fr[:, :, ::-1] * 255 + 0.5).astype(np.uint8))

if __name__ == '__main__':
    mode = sys.argv[1]
    if mode == 'frames':
        a, b, out = int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
        os.makedirs(out, exist_ok=True)
        for fi in range(a, b):
            save(frame(fi), os.path.join(out, 'f_%05d.png' % fi))
            if fi % 10 == 0: print('frame', fi, flush=True)
    elif mode == 'stills':
        ts = [float(x) for x in sys.argv[2].split(',')]; out = sys.argv[3]
        os.makedirs(out, exist_ok=True)
        for t in ts:
            save(frame(int(round(t * FPS))), os.path.join(out, 't_%05.2f.png' % t))
            print('still', t, flush=True)
