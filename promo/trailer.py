"""TALEVENTURE - "From Dinosaurs to Humans" 9:16 trailer (1080x1920, 60 fps).
Real footage from the film (promo/clips/shot_<id>.mp4, 1920x1080 @ 24) cropped to vertical with smooth pans, one orange
light line that runs through the whole trailer (the timeline of life at the bottom, the wipes between eras, the title).

usage:  python3 trailer.py frames A B outdir | stills "t1,t2" outdir | video out.mp4
"""
import os, sys, math, json
import numpy as np, cv2
import render as R
from render import cl, sg, ss, eo, ei, eio, back, lerp, light, add_glow, text_sprite, place, rect_quad, ACC, WHITE

HERE = os.path.dirname(os.path.abspath(__file__)); CLIPS = os.environ.get('CLIPS', os.path.join(HERE, 'clips'))
W, H, S, FPS = R.W, R.H, R.S, 60

# ---------------------------------------------------------------- the edit
# id, start (s), clip, source start (s in clip), speed, crop: (cx0, cx1) centre in source px, (z0, z1) zoom, cy, transition in
SHOTS = [
    dict(t=0.55, clip='e01', ss=0.5, sp=1.0, cx=(1000, 930), z=(1.0, 1.10), cy=540, tin=('open', .7)),
    dict(t=3.30, clip='e02', ss=1.2, sp=1.0, cx=(980, 1060), z=(1.08, 1.18), cy=520, tin=('cut', 0)),
    dict(t=5.15, clip='e03', ss=.75, sp=1.0, cx=(700, 760), z=(1.0, 1.06), cy=540, tin=('flash', .25)),
    dict(t=5.75, clip='e07', ss=1.5, sp=1.0, cx=(1000, 880), z=(1.0, 1.12), cy=540, tin=('wipe', .45)),
    dict(t=8.55, clip='k03', ss=8.6, sp=1.0, cx=(1000, 1060), z=(1.25, 1.5), cy=450, tin=('cut', 0)),
    dict(t=9.95, clip='l04', ss=2.6, sp=1.0, cx=(900, 930), z=(1.15, 1.25), cy=600, tin=('wipe', .45)),
    dict(t=11.95, clip='p07', ss=1.2, sp=1.0, cx=(820, 700), z=(1.0, 1.06), cy=540, tin=('wipe', .45)),
    dict(t=13.70, clip='p11', ss=.4, sp=1.0, cx=(790, 790), z=(1.05, 1.28), cy=560, tin=('cut', 0)),
    dict(t=14.90, clip='a03', ss=1.2, sp=1.0, cx=(860, 860), z=(1.0, 1.05), cy=540, tin=('cut', 0), streak=(850, 240)),
    dict(t=16.30, clip='a04', ss=2.0, sp=1.0, cx=(1080, 1100), z=(1.0, 1.08), cy=540, tin=('flash', .5)),
    dict(t=17.90, clip=None, tin=('cut', 0)),                                    # black beat
    dict(t=18.60, clip='n04', ss=5.0, sp=1.0, cx=(1000, 1010), z=(1.05, 1.12), cy=520, tin=('fade', .3)),
    dict(t=19.55, clip='h05', ss=7.0, sp=1.0, cx=(880, 900), z=(1.05, 1.12), cy=560, tin=('cut', 0)),
    dict(t=20.45, clip='h07', ss=8.0, sp=1.0, cx=(620, 700), z=(1.0, 1.05), cy=560, tin=('cut', 0)),
    dict(t=21.65, clip='c04', ss=.1, sp=1.0, cx=(780, 780), z=(1.0, 1.06), cy=540, tin=('wipe', .4), panel=1),
    dict(t=24.35, clip='c05', ss=.5, sp=1.0, cx=(880, 880), z=(1.0, 1.06), cy=540, tin=('cut', 0), panel=1),
    dict(t=25.90, clip='p08', ss=3.0, sp=.6, cx=(900, 1000), z=(1.05, 1.12), cy=540, tin=('fade', .6), dim=1),
]
END = 32.5
ERAS = [(0.0, '4.5 BILLION YEARS AGO'), (5.75, '3.5 BILLION YEARS AGO'), (8.55, '541 MILLION YEARS AGO'), (9.95, '375 MILLION YEARS AGO'),
        (11.95, '150 MILLION YEARS AGO'), (14.90, '66 MILLION YEARS AGO'), (18.60, '55 MILLION YEARS AGO'), (19.55, '300,000 YEARS AGO'),
        (20.45, '40,000 YEARS AGO'), (21.65, 'TODAY')]
ERA_OFF = (17.9, 18.6)   # no chip in the black beat
TL_END = 21.65            # the timeline line reaches the right edge here


# ---------------------------------------------------------------- footage
class Clip:
    def __init__(self, name):
        self.cap = cv2.VideoCapture(os.path.join(CLIPS, f'shot_{name}.mp4')); self.i = -1; self.f = None
        self.n = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1

    def get(self, fi):
        fi = max(0, min(self.n - 1, fi))
        if fi < self.i or fi > self.i + 48:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, fi); self.i = fi - 1
        while self.i < fi:
            ok, f = self.cap.read()
            if not ok: break
            self.f = f; self.i += 1
        return self.f


_clips = {}
def clip(name):
    if name not in _clips: _clips[name] = Clip(name)
    return _clips[name]


def shot_frame(k, t):
    """shot k at global time t -> float RGB frame (H, W, 3)"""
    s = SHOTS[k]
    if not s.get('clip'): return np.zeros((H, W, 3), np.float32)
    nxt = SHOTS[k + 1]['t'] if k + 1 < len(SHOTS) else END
    u = cl((t - s['t']) / max(nxt - s['t'], .1))
    src = clip(s['clip']).get(int((s['ss'] + (t - s['t']) * s['sp']) * 24))
    if src is None: return np.zeros((H, W, 3), np.float32)
    z = lerp(s['z'][0], s['z'][1], eio(u)); cx = lerp(s['cx'][0], s['cx'][1], eio(u)); cy = s['cy']
    sc = H / 1080 * z                      # source px -> output px
    M = np.float32([[sc, 0, W / 2 - cx * sc], [0, sc, H / 2 - cy * sc]])
    if s.get('panel'):                     # classroom: the whole 16:9 frame as a card over a blurred, darkened fill
        small = cv2.resize(src, (480, 270), interpolation=cv2.INTER_AREA); scb = H / 270
        bg = cv2.warpAffine(small, np.float32([[scb, 0, W / 2 - 240 * scb], [0, scb, H / 2 - 135 * scb]]), (W, H), flags=cv2.INTER_LINEAR)
        bg = cv2.GaussianBlur(bg, (0, 0), 28 * S).astype(np.float32)[:, :, ::-1] / 255 * .32
        pw = int(1000 * S) // 2 * 2; ph = int(pw * 1080 / 1920) // 2 * 2; zz = 1 + .05 * eio(u)
        fgw, fgh = int(pw * zz), int(ph * zz)
        fg = cv2.resize(src, (fgw, fgh), interpolation=cv2.INTER_AREA)[(fgh - ph) // 2:(fgh - ph) // 2 + ph, (fgw - pw) // 2:(fgw - pw) // 2 + pw]
        fg = fg[:, :, ::-1].astype(np.float32) / 255
        m = R.rounded_mask(pw, ph, int(26 * S))[..., None]
        x0, y0 = (W - pw) // 2, int(960 * S) - ph // 2
        f = bg.copy(); roi = f[y0:y0 + ph, x0:x0 + pw]; f[y0:y0 + ph, x0:x0 + pw] = roi * (1 - m) + fg * m
        light(f, [(x0, y0 + ph + 26 * S), (x0 + pw, y0 + ph + 26 * S)], 0, 1, wd=3, heat=.6, op=.9, head=0, glow=.6)
        return grade(f)
    out = cv2.warpAffine(src, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
    f = out[:, :, ::-1].astype(np.float32) / 255
    bl = cv2.GaussianBlur(f, (0, 0), 1.6 * S + .1); f = np.clip(f + (f - bl) * .55, 0, 1)   # recover detail after the upscale
    if s.get('dim'): f *= .42
    if s.get('streak'):                    # the line becomes the asteroid: a burning streak racing down onto the bright dot
        tl = t - s['t']; px, py = s['streak']; X, Y = W / 2 + (px - cx) * sc, H / 2 + (py - cy) * sc
        k = eo(cl((tl - .1) / .75)); hx, hy = lerp(W * 1.25, X, k), lerp(-H * .12, Y, k)
        heat = sg(tl, .0, 1.3)
        f += np.float32([.35, .12, .02]) * heat * .45 * np.exp(-((_yy - Y) ** 2 + (_xx - X) ** 2) / (2 * (700 * S) ** 2))[..., None]
        light(f, [(W * 1.25 + (W * 1.25 - hx) * .0, -H * .12), (hx, hy)], max(0, k - .55), 1, wd=6 + 6 * heat, heat=1, op=1, head=1.4 + heat, glow=1.3)
    return grade(f)


def grade(f):
    """gentle trailer grade: lift contrast, warm highlights, cool shadows"""
    l = f.mean(2, keepdims=True)
    f = (f - .5) * 1.08 + .5
    f = f + (np.float32([.03, .012, -.02]) * np.clip(l - .45, 0, 1) + np.float32([-.012, .0, .018]) * np.clip(.4 - l, 0, 1))
    return np.clip(f, 0, 1)


def active(t):
    k = 0
    for i, s in enumerate(SHOTS):
        if s['t'] <= t: k = i
    return k


# ---------------------------------------------------------------- the line, chips, titles
def wipe_geom(u, d=1):
    """diagonal line sweeping across the frame; returns (p0, p1) endpoints and the mask of the new side"""
    off = lerp(-1.25, 1.25, eio(u)) * d
    cx, cy = W / 2 + off * W * .62, H / 2
    ang = math.radians(74)
    dx, dy = math.cos(ang) * H, math.sin(ang) * H
    return (cx - dx, cy - dy), (cx + dx, cy + dy)


_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)
def side_mask(p0, p1, soft=2.0):
    nx, ny = p1[1] - p0[1], -(p1[0] - p0[0]); n = math.hypot(nx, ny)
    dist = ((_xx - p0[0]) * nx + (_yy - p0[1]) * ny) / n
    return np.clip(.5 - dist / soft, 0, 1)[..., None]


def era_at(t):
    e = ERAS[0]
    for x in ERAS:
        if x[0] <= t: e = x
    return e


def chip(fr, t):
    if ERA_OFF[0] <= t < ERA_OFF[1] or t < .9 or t > 25.5: return
    t0, txt = era_at(t)
    op = sg(t, t0, t0 + .25) if t0 > 0 else sg(t, .9, 1.4)
    op *= 1 - sg(t, 25.1, 25.5)
    nxt = [x[0] for x in ERAS if x[0] > t0]
    if nxt and t > nxt[0] - .15: op *= 1 - sg(t, nxt[0] - .15, nxt[0])
    if op <= 0: return
    spr, ox, oy, w, h = text_sprite(txt, 38, 'InterDisplay-SemiBold', (1, 1, 1), track=.12)
    x, y = 96, 228
    sh = np.zeros_like(spr); sh[..., 3] = spr[..., 3] * .55
    place(fr, sh, rect_quad((x + w / 2 + 2) * S, (y + 3) * S, w * S, h * S), blur=6 * S, op=op)
    place(fr, spr, rect_quad((x + w / 2 + 8 * (1 - eo(sg(t, t0, t0 + .4)))) * S, y * S, w * S, h * S), op=op)
    add_glow(fr, (x - 30) * S, (y + 1) * S, 6 * S + 1, ACC, 1.2 * op); add_glow(fr, (x - 30) * S, (y + 1) * S, 2.5 * S + 1, WHITE, 1.1 * op)
    # underline grows with each new era
    ln = (w - 30) * eo(sg(t, t0, t0 + .5))
    light(fr, [((x - 30) * S, (y + 34) * S), ((x - 30 + ln) * S, (y + 34) * S)], 0, 1, wd=2.5, heat=.4, op=op * .9, head=.6, glow=.5)


def timeline(fr, t):
    """the line of life along the bottom: grows from left to right with the trailer, its head glowing"""
    if t < .55 or t > 25.6: return
    y = 1712 * S; u = ss(sg(t, .55, TL_END))
    op = sg(t, .55, 1.0) * (1 - sg(t, 25.2, 25.6))
    if ERA_OFF[0] <= t < ERA_OFF[1]: op *= .5
    x1 = lerp(70, 1010, u) * S
    light(fr, [(70 * S, y), (1010 * S, y)], 0, 1, wd=1.5, heat=0, op=op * .22, head=0, glow=.0, cool=1)   # faint rail
    light(fr, [(70 * S, y), (x1, y)], 0, 1, wd=4, heat=.8, op=op, head=1.0, glow=.8)
    for i, (te, _) in enumerate(ERAS):     # era ticks light up as the head passes them
        xe = lerp(70, 1010, ss(sg(te, .55, TL_END))) * S
        if xe <= x1 + 1: add_glow(fr, xe, y, 3 * S + 1, WHITE if i == len(ERAS) - 1 else ACC, .9 * op)


def big_text(fr, txt, size, x, y, op, font='InterDisplay-Black', color=(1, 1, 1), track=0.0, rise=0.0, blur=0.0, scale=1.0):
    if op <= 0: return None
    spr, ox, oy, w, h = text_sprite(txt, size, font, color, track)
    sh = np.zeros_like(spr); sh[..., 3] = spr[..., 3] * .6
    place(fr, sh, rect_quad(x * S, (y + rise + 6) * S, w * S * scale, h * S * scale), blur=14 * S, op=op)
    place(fr, spr, rect_quad(x * S, (y + rise) * S, w * S * scale, h * S * scale), blur=blur * S, op=op)
    return w * scale, h * scale


def title(fr, t):
    """FROM DINOSAURS / TO HUMANS, drawn by the line, then the TALEVENTURE end card"""
    if t < 25.9: return
    # line sweeps in from the left and draws the bar between the two title lines
    a = sg(t, 25.95, 26.6)
    y_bar = 968
    if t < 29.4:
        u = eo(a); op = 1 - sg(t, 29.0, 29.4)
        light(fr, [(80 * S, y_bar * S), (1000 * S, y_bar * S)], 0, u, wd=5, heat=.9, op=op, head=1 - sg(t, 26.6, 27.0) * .7)
        for i, (txt, yy, col, t0) in enumerate((('FROM DINOSAURS', 888, (1, 1, 1), 26.05), ('TO HUMANS', 1060, (1.0, .52, .32), 26.35))):
            k = eo(sg(t, t0, t0 + .55)); op2 = k * op
            big_text(fr, txt, 108 if i == 0 else 132, 540, yy, op2, track=.02, rise=(1 - k) * (40 if i == 0 else -40), blur=(1 - k) * 8,
                     color=col, scale=1 + .04 * (1 - k) + .015 * sg(t, 26.4, 29.4))
        k = eo(sg(t, 27.0, 27.5))
        big_text(fr, 'A 4.5 BILLION YEAR STORY IN 11 MINUTES', 32, 540, 1170, k * op, font='Inter-SemiBold', color=(.86, .86, .86), track=.14)
    if t >= 29.2:
        k = eo(sg(t, 29.35, 29.9)); op = 1 - sg(t, END - .45, END)
        big_text(fr, 'NOW ON', 36, 540, 880, k * op, font='Inter-SemiBold', color=(.85, .85, .85), track=.3, rise=(1 - k) * 16)
        k2 = eo(sg(t, 29.55, 30.2))
        wv = big_text(fr, 'TALEVENTURE', 118, 540, 975, k2 * op, track=.06, scale=.94 + .06 * k2 + .01 * sg(t, 30.2, END), blur=(1 - k2) * 10)
        if wv:
            hw = wv[0] / 2 - 10
            light(fr, [((540 - hw) * S, 1062 * S), ((540 + hw) * S, 1062 * S)], 0, eo(sg(t, 29.8, 30.5)), wd=5, heat=.9, op=op, head=1 - sg(t, 30.5, 31) * .8)
        k3 = eo(sg(t, 30.4, 30.9))
        big_text(fr, 'FULL VIDEO  •  FROM DINOSAURS TO HUMANS', 30, 540, 1140, k3 * op, font='Inter-SemiBold', color=(.8, .8, .8), track=.12)


def opener(fr, t):
    """0-0.55 s: the line ignites in the dark as a horizon; it then splits open into the first shot"""
    if t > 1.4: return
    u = eo(sg(t, .05, .5))
    y = H / 2
    op = 1 - sg(t, .95, 1.3)
    light(fr, [(W / 2 - u * W * .55, y), (W / 2 + u * W * .55, y)], 0, 1, wd=4 + 3 * sg(t, .3, .55), heat=1, op=op, head=0, glow=1.3)
    add_glow(fr, W / 2, y, 30 * S, ACC, .5 * op * (1 - sg(t, .55, 1.2)), sx=8, sy=1)


# ---------------------------------------------------------------- frame
def frame_at(t, fi=0):
    k = active(t); s = SHOTS[k]
    fr = shot_frame(k, t) if t >= SHOTS[0]['t'] else np.zeros((H, W, 3), np.float32)
    kind, d = s['tin']; u = (t - s['t']) / d if d else 1
    if u < 1 and k > 0:
        if kind == 'wipe':
            prev = shot_frame(k - 1, t); p0, p1 = wipe_geom(u, 1 if k % 2 else -1)
            m = side_mask(p0, p1, 2.5 * S) if k % 2 else 1 - side_mask(p0, p1, 2.5 * S)
            fr = prev * (1 - m) + fr * m
            light(fr, [p0, p1], 0, 1, wd=6, heat=1, op=1 - sg(u, .85, 1), head=0, glow=1.2)
        elif kind == 'flash':
            fr = fr + (1 - fr) * (1 - eo(u)) ** 1.5
        elif kind == 'fade':
            fr = fr * ss(u)
    if k == 0 and kind == 'open' and u < 1:   # the horizon line opens like an eye
        hh = eio(u) * H / 2; y0, y1 = int(H / 2 - hh), int(H / 2 + hh)
        o = np.zeros_like(fr); o[max(0, y0):y1] = fr[max(0, y0):y1]; fr = o
        if 0 < hh < H / 2:
            for yy in (H / 2 - hh, H / 2 + hh):
                light(fr, [(0, yy), (W, yy)], 0, 1, wd=4, heat=1, op=1 - sg(u, .7, 1), head=0, glow=1.1)
    # end of the black beat: everything already black; the end card sits on dimmed footage (dim flag)
    opener(fr, t)
    timeline(fr, t); chip(fr, t); title(fr, t)
    if t > END - .45: fr *= 1 - sg(t, END - .45, END)
    return R.finish(fr, fi)


def save(fr, path): cv2.imwrite(path, (fr[:, :, ::-1] * 255 + .5).astype(np.uint8))


if __name__ == '__main__':
    mode = sys.argv[1]
    if mode == 'frames':
        a, b, out = int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]; os.makedirs(out, exist_ok=True)
        for fi in range(a, b):
            save(frame_at(fi / FPS, fi), os.path.join(out, 'f_%05d.png' % fi))
            if fi % 30 == 0: print('frame', fi, flush=True)
    elif mode == 'stills':
        out = sys.argv[3]; os.makedirs(out, exist_ok=True)
        for x in sys.argv[2].split(','):
            t = float(x); save(frame_at(t, int(t * FPS)), os.path.join(out, 't_%05.2f.png' % t)); print('still', t, flush=True)
    elif mode == 'video':
        out = sys.argv[2]; n = int(round(END * FPS))
        import subprocess
        p = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                              '-c:v', 'libx264', '-preset', 'medium', '-crf', '15', '-pix_fmt', 'yuv420p', out], stdin=subprocess.PIPE)
        a = int(sys.argv[3]) if len(sys.argv) > 3 else 0; b = int(sys.argv[4]) if len(sys.argv) > 4 else n
        for fi in range(a, b):
            p.stdin.write((frame_at(fi / FPS, fi) * 255 + .5).astype(np.uint8).tobytes())
            if fi % 60 == 0: print('frame', fi, '/', b, flush=True)
        p.stdin.close(); p.wait()
