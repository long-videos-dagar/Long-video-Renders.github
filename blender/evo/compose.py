"""python3 compose.py <chunk_dir> <out.mp4>  - From Dinosaurs to Humans (DAGAR CLIPS, 16:9).
Each shot becomes an exact-length segment (its transition built in: dissolve from the previous shot's handle, fade from/to
black, white flash, iris through the chalk eye, split screen), captions only where the script asks for them, then all
segments are joined and upscaled to 2560x1440.  Sound = the voices (placed from voice.json) + synthesised sound effects at
20-30 % of the narrator level.  No music, no subtitles, no logo."""
import json, os, sys, glob, subprocess, tempfile, math, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
H = os.path.dirname(os.path.abspath(__file__)); art, outp = sys.argv[1], sys.argv[2]
sys.path.insert(0, os.path.join(os.path.dirname(H), 'gta')); import typo
film = json.load(open(os.path.join(H, 'shots.json'))); fps = film['fps']; VOICE = json.load(open(os.path.join(H, 'voice.json')))
SHOTS = [s for s in film['shots'] if not s.get('part_of')]; BY = {s['id']: s for s in film['shots']}
W, Hh = [int(v) for v in os.environ.get('SEG', '1920x1080').split('x')]; OW, OH = [int(v) for v in os.environ.get('OUT', '2560x1440').split('x')]
TOTAL = SHOTS[-1]['t0'] + SHOTS[-1]['dur']
tmp = tempfile.mkdtemp()
def sh(*a): subprocess.run(a, check=True)

# transitions INTO a shot: kind, seconds
TR = {'c13': ('iris', .7), 'e06': ('dissolve', .25), 'm04': ('fadeblack', .4), 'm06': ('dissolve', .25), 'k01': ('fadeblack', .5),
      'l01': ('dissolve', .25), 'l05': ('fadeblack', .3), 'p01': ('fadeblack', .5), 'p03': ('fadeout', .6), 'p04': ('fadein', 1.2),
      'p06': ('dissolve', .25), 'p10': ('dissolve', .25), 'p12': ('fadeblack', .3), 'd01': ('fadeblack', .5), 'd06': ('fadeblack', .3),
      'a01': ('fadeblack', .5), 'a04': ('white', .5), 'n01': ('fadein', 1.0), 'n05': ('fadeblack', .3), 'h01': ('dissolve', .25),
      'h08': ('dissolve', .25), 't01': ('dissolve', .25), 't03': ('white', .3), 'b01': ('iris', .6), 'b08': ('white', .5), 'b09': ('dissolve', .25)}
OUT_BLACK = {'p02': .8, 'a07': .0, 'b09': 1.0}            # fade to black at the end of these shots (seconds)
# captions only where the script calls for them
CAP = {'p01': [('252 MILLION YEARS AGO', 'PERMIAN MASS EXTINCTION', .8, None, 'era')], 'd02': [('NOT A DINOSAUR', '', 2.2, 5.8, 'tag')],
       'b09': [('LIFE IS STILL EVOLVING.', '(And so is Kevin\'s homework.)', .4, None, 'end')]}


def shotfile(sid):
    ps = sorted(glob.glob(f"{art}/chunk_{sid}_[0-9]*.mp4"))
    if not ps: return None
    lst = os.path.join(tmp, sid + '.txt'); open(lst, 'w').write(''.join(f"file '{os.path.abspath(p)}'\n" for p in ps))
    o = os.path.join(tmp, sid + '_src.mp4'); sh('ffmpeg', '-loglevel', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst, '-c', 'copy', o); return o


def src(sid):
    f = shotfile(sid)
    if f is None:
        f = os.path.join(tmp, sid + '_black.mp4'); d = BY[sid]['dur'] + .3
        sh('ffmpeg', '-loglevel', 'error', '-y', '-f', 'lavfi', '-i', f'color=c=black:s={W}x{Hh}:r={fps}:d={d:.3f}', '-pix_fmt', 'yuv420p', f); print('MISSING', sid)
    return f


def cap_png(sid, j, a, b, style):
    im = Image.new('RGBA', (W, Hh), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    def txt(xy, s, f, fill, anchor='mm', sw=0):
        sh_ = Image.new('RGBA', (W, Hh), (0, 0, 0, 0)); ImageDraw.Draw(sh_).text((xy[0] + 3, xy[1] + 4), s, font=f, fill=(0, 0, 0, 170), anchor=anchor)
        im.alpha_composite(sh_.filter(ImageFilter.GaussianBlur(6))); d.text(xy, s, font=f, fill=fill, anchor=anchor, stroke_width=sw, stroke_fill=(0, 0, 0, 255))
    if style == 'era':
        txt((W / 2, Hh * .40), a, typo.font('bebas', 120 * W / 1920), (255, 255, 255, 255)); d.rectangle([W / 2 - 330 * W / 1920, Hh * .40 + 70 * W / 1920, W / 2 + 330 * W / 1920, Hh * .40 + 74 * W / 1920], fill=(220, 60, 40, 255))
        txt((W / 2, Hh * .40 + 125 * W / 1920), b, typo.font('oswald_b', 54 * W / 1920), (230, 70, 50, 255))
    elif style == 'tag':
        txt((W * .5, Hh * .2), a, typo.font('anton', 110 * W / 1920), (255, 220, 70, 255), sw=4)
    elif style == 'end':
        txt((W / 2, Hh * .44), a, typo.font('montserrat', 92 * W / 1920), (255, 255, 255, 255)); txt((W / 2, Hh * .44 + 105 * W / 1920), b, typo.font('caveat', 70 * W / 1920), (255, 214, 120, 255))
    p = os.path.join(tmp, f'cap_{sid}_{j}.png'); im.save(p); return p


def crack_png():
    im = Image.new('RGBA', (W, Hh), (0, 0, 0, 0)); d = ImageDraw.Draw(im); pts = []
    import random; r = random.Random(3)
    for k in range(13): pts.append((W / 2 + r.uniform(-26, 26), k * Hh / 12))
    d.line(pts, fill=(10, 8, 6, 255), width=16); d.line(pts, fill=(255, 240, 210, 255), width=4)
    p = os.path.join(tmp, 'crack.png'); im.save(p); return p


def segment(i, s):
    sid = s['id']; n = round(s['dur'] * fps); d_ = n / fps; o = os.path.join(tmp, f'seg_{i:03d}.mp4')
    ins, fc = [], []
    if s.get('parts'):
        a, b = s['parts']; ins += ['-i', src(a), '-i', src(b), '-loop', '1', '-i', crack_png()]
        fc.append(f"[0:v]crop=iw/2:ih:iw/4:0[l];[1:v]crop=iw/2:ih:iw/4:0[r];[l][r]hstack,scale={W}:{Hh}[hs];[hs][2:v]overlay=0:0:shortest=1[v0]")
    else:
        ins += ['-i', src(sid)]; fc.append(f"[0:v]scale={W}:{Hh},fps={fps},format=yuv420p[v0]")
    lab = '[v0]'; tr = TR.get(sid)
    if tr and tr[0] == 'dissolve' and i > 0:
        p = SHOTS[i - 1]; k = sum(1 for x in ins if x == '-i')
        ins += ['-i', src(p['id']) if not p.get('parts') else src(p['parts'][0])]
        fc.append(f"[{k}:v]trim={p['dur']:.4f}:{p['dur'] + tr[1]:.4f},setpts=PTS-STARTPTS,scale={W}:{Hh},fps={fps},format=yuv420p[pv]")
        fc.append(f"[pv]{lab}xfade=transition=fade:duration={tr[1]:.3f}:offset=0[v1]"); lab = '[v1]'
    elif tr and tr[0] in ('fadeblack', 'fadein'):
        fc.append(f"{lab}fade=t=in:st=0:d={tr[1]:.3f}[v1]"); lab = '[v1]'
    elif tr and tr[0] == 'white':
        fc.append(f"{lab}fade=t=in:st=0:d={tr[1]:.3f}:color=white[v1]"); lab = '[v1]'
    elif tr and tr[0] == 'iris':
        R = f"(hypot({W},{Hh})/2)*min(1,T/{tr[1]:.3f})^2"
        fc.append(f"color=c=black:s={W}x{Hh}:r={fps}:d={tr[1] + .1:.3f},format=yuva420p,geq=lum='0':cb='128':cr='128':a='if(lt(hypot(X-{W / 2},Y-{Hh / 2}),{R}),0,255)'[ir]")
        fc.append(f"{lab}[ir]overlay=0:0:eof_action=pass[v1]"); lab = '[v1]'
    if sid in ('p03',): fc.append(f"{lab}drawbox=0:0:iw:ih:black:t=fill[v2]"); lab = '[v2]'
    nxt = SHOTS[i + 1]['id'] if i + 1 < len(SHOTS) else None
    fo = OUT_BLACK.get(sid) or ((TR[nxt][1]) if nxt and TR.get(nxt, ('',))[0] == 'fadeblack' else 0) or ((TR[nxt][1]) if nxt and TR.get(nxt, ('',))[0] == 'iris' else 0)
    if fo: fc.append(f"{lab}fade=t=out:st={d_ - fo:.3f}:d={fo:.3f}[v3]"); lab = '[v3]'
    for j, (a, b, t0, t1, style) in enumerate(CAP.get(sid, [])):
        p = cap_png(sid, j, a, b, style)
        k = sum(1 for x in ins if x == '-i'); ins += ['-loop', '1', '-i', p]; t1 = t1 or d_
        fc.append(f"[{k}:v]format=rgba,fade=t=in:st=0:d=0.35:alpha=1,fade=t=out:st={max(0, t1 - t0 - .35):.3f}:d=0.35:alpha=1,setpts=PTS+{t0:.3f}/TB[c{j}]")
        fc.append(f"{lab}[c{j}]overlay=0:0:eof_action=pass:shortest=0[v4{j}]"); lab = f'[v4{j}]'
    fc.append(f"{lab}trim=end_frame={n},setpts=PTS-STARTPTS,format=yuv420p[vo]")
    sh('ffmpeg', '-loglevel', 'error', '-y', *ins, '-filter_complex', ';'.join(fc), '-map', '[vo]', '-frames:v', str(n), '-r', str(fps),
       '-c:v', 'libx264', '-crf', '12', '-preset', 'fast', '-pix_fmt', 'yuv420p', o)
    return o


segs = [segment(i, s) for i, s in enumerate(SHOTS)]
lst = os.path.join(tmp, 'segs.txt'); open(lst, 'w').write(''.join(f"file '{p}'\n" for p in segs))
pic = os.path.join(tmp, 'picture.mp4')
sh('ffmpeg', '-loglevel', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst, '-vf', f"scale={OW}:{OH}:flags=lanczos,unsharp=5:5:0.45:5:5:0.0",
   '-c:v', 'libx264', '-crf', '16', '-preset', 'medium', '-pix_fmt', 'yuv420p', '-r', str(fps), pic)

# ---------------------------------------------------------------- sound
SR = 48000; N = int((TOTAL + .5) * SR); rng = np.random.default_rng(7)
voice = np.zeros(N)
for v in VOICE:
    p = os.path.join(H, 'voice', v['id'] + '.wav'); r = os.path.join(tmp, v['id'] + '.wav')
    sh('ffmpeg', '-loglevel', 'error', '-y', '-i', p, '-ac', '1', '-ar', str(SR), r)
    a = np.frombuffer(wave.open(r).readframes(10 ** 9), dtype=np.int16).astype(np.float32) / 32767
    i = int(v['t'] * SR); j = min(N, i + len(a)); voice[i:j] += a[:j - i]
sfx = np.zeros(N); amb = np.zeros(N)
def T0(sid): return BY[sid]['t0']
def add(dst, sig, t):
    i = int(t * SR); j = min(len(dst), i + len(sig))
    if 0 <= i < len(dst) and j > i: dst[i:j] += sig[:j - i]
def lp(x, k):
    """one-pole low-pass, k = 0..1 (smaller = darker)"""
    out = np.empty_like(x); c = 0.0
    a = np.full(len(x), k) if np.isscalar(k) else k
    for i in range(len(x)): c += a[i] * (x[i] - c); out[i] = c
    return out
def lpf(x, n): return np.convolve(x, np.ones(n) / n, 'same')
def env(n, a=.01, r=.1):
    x = np.arange(n) / SR; d = n / SR
    return np.minimum(1, x / max(a, 1e-4)) * np.minimum(1, np.maximum(0, (d - x) / max(r, 1e-4)))
def brown(dur, n_=200): return lpf(rng.standard_normal(int(dur * SR)), n_)
def whoosh(t, dur=.6, amp=.4):
    n = int(dur * SR); x = np.arange(n) / SR; s = rng.standard_normal(n)
    add(sfx, amp * lp(s, np.linspace(.02, .35, n) * np.sin(np.pi * x / dur) + .01) * np.sin(np.pi * x / dur) * 3, t)
def boom(t, amp=1.0, dur=3.0, fr=38):
    n = int(dur * SR); x = np.arange(n) / SR
    add(sfx, amp * (np.sin(2 * np.pi * fr * x * (1 - .3 * x / dur)) * np.exp(-x * 2.2) + 3 * lpf(rng.standard_normal(n), 60) * np.exp(-x * 1.4)), t)
def thud(t, amp=.6, fr=60, dec=9): n = int(.5 * SR); x = np.arange(n) / SR; add(sfx, amp * (np.sin(2 * np.pi * fr * x) * np.exp(-x * dec) + 2 * lpf(rng.standard_normal(n), 30) * np.exp(-x * 25)), t)
def rumble(t0, t1, amp=.25, n_=400): add(amb, amp * brown(t1 - t0, n_) * 6 * env(int((t1 - t0) * SR), .5, .5), t0)
def crackle(t0, t1, amp=.2, rate=14):
    for tt in np.arange(t0, t1, 1 / rate):
        tt += rng.uniform(0, 1 / rate); n = int(.012 * SR); add(amb, amp * rng.uniform(.3, 1) * rng.standard_normal(n) * np.exp(-np.arange(n) / SR * 400), tt)
def wind(t0, t1, amp=.12):
    n = int((t1 - t0) * SR); g = .5 + .5 * np.sin(np.arange(n) / SR * .7 + rng.uniform(0, 6)); add(amb, amp * lpf(rng.standard_normal(n), 40) * 4 * g * env(n, .6, .6), t0)
def water(t0, t1, amp=.12):
    n = int((t1 - t0) * SR); add(amb, amp * (lpf(rng.standard_normal(n), 120) * 8) * env(n, .5, .5), t0)
    for tt in np.arange(t0, t1, .35): bubble(tt + rng.uniform(0, .3), amp * .6)
def bubble(t, amp=.1):
    n = int(.06 * SR); x = np.arange(n) / SR; f0 = rng.uniform(500, 1400); add(amb, amp * np.sin(2 * np.pi * f0 * (1 + 6 * x) * x) * np.exp(-x * 60), t)
def birds(t0, t1, amp=.04, gap=1.1):
    for tt in np.arange(t0, t1, gap):
        tt += rng.uniform(0, gap * .6); n = int(.14 * SR); x = np.arange(n) / SR; f0 = rng.uniform(2600, 4200)
        add(amb, amp * np.sin(2 * np.pi * (f0 + 700 * np.sin(2 * np.pi * rng.uniform(12, 22) * x)) * x) * np.sin(np.pi * x / .14), tt)
def insects(t0, t1, amp=.02):
    n = int((t1 - t0) * SR); x = np.arange(n) / SR; add(amb, amp * np.sin(2 * np.pi * 4300 * x) * (.5 + .5 * np.sign(np.sin(2 * np.pi * 18 * x))) * (.5 + .5 * np.sin(x * .9)) * env(n, .5, .5), t0)
def step(t, amp=.5, fr=45): thud(t, amp, fr, 7)
def roar(t, dur=2.2, amp=.9, f0=70):
    """synthetic big-animal roar: growling low tone with jitter + breathy band of noise, rising then falling"""
    n = int(dur * SR); x = np.arange(n) / SR; shape = np.sin(np.pi * np.minimum(1, x / dur)) ** .6
    f = f0 * (1 + .35 * np.sin(np.pi * x / dur)) * (1 + .06 * lpf(rng.standard_normal(n), 300) * 20)
    ph = 2 * np.pi * np.cumsum(f) / SR; tone = np.tanh(3 * (np.sin(ph) + .5 * np.sin(2 * ph) + .3 * np.sin(3.1 * ph)))
    br = lpf(rng.standard_normal(n), 8) - lpf(rng.standard_normal(n), 60)
    add(sfx, amp * shape * (.6 * tone * (1 + .4 * np.sin(2 * np.pi * 24 * x)) + 1.2 * br), t)
def chirp(t, amp=.15): n = int(.18 * SR); x = np.arange(n) / SR; add(sfx, amp * np.sin(2 * np.pi * (1800 + 1600 * x / .18) * x) * np.sin(np.pi * x / .18), t)
def flap(t, amp=.12, n_=6, rate=9):
    for k in range(n_): add(sfx, amp * lpf(rng.standard_normal(int(.05 * SR)), 6) * np.exp(-np.arange(int(.05 * SR)) / SR * 50), t + k / rate)
def ding(t, amp=.25): n = int(.8 * SR); x = np.arange(n) / SR; add(sfx, amp * (np.sin(2 * np.pi * 1320 * x) + .5 * np.sin(2 * np.pi * 1980 * x)) * np.exp(-x * 5), t)
def tick(t, amp=.15): n = int(.02 * SR); add(sfx, amp * rng.standard_normal(n) * np.exp(-np.arange(n) / SR * 300), t)
def chalk(t0, t1, amp=.08):
    for tt in np.arange(t0, t1, .22):
        n = int(.16 * SR); x = np.arange(n) / SR; s = rng.standard_normal(n) - lpf(rng.standard_normal(n), 4)
        add(sfx, amp * s * (.6 + .4 * np.sin(2 * np.pi * 70 * x)) * np.sin(np.pi * x / .16), tt + rng.uniform(0, .05))
def room(t0, t1, amp=.02): add(amb, amp * brown(t1 - t0, 80) * 6, t0)

for s in SHOTS:
    sid, a, b = s['id'], s['t0'], s['t0'] + s['dur']; w = s['world']
    if w == 'classroom': room(a, b); birds(a, b, .012, 3.0)
    elif w in ('young_earth',): rumble(a, b, .35); crackle(a, b, .12, 10)
    elif w in ('microbes',): water(a, b, .06)
    elif w in ('shallows', 'ediacaran', 'cambrian', 'devonian_sea'): water(a, b, .1)
    elif w in ('coast', 'coast_cretaceous'): wind(a, b, .1); water(a, b, .06)
    elif w in ('permian', 'triassic', 'jurassic', 'cretaceous', 'paleogene', 'savanna'):
        wind(a, b, .08); insects(a, b, .012)
        if w in ('cretaceous', 'paleogene', 'savanna'): birds(a, b, .03)
    elif w == 'impact': wind(a, b, .14)
    elif w == 'cave': crackle(a, b, .1, 16); wind(a, b, .04)
    elif w == 'city': room(a, b, .05); birds(a, b, .01, 2)
    elif w == 'livingroom': room(a, b, .015)
    elif w == 'space': pass
    if TR.get(sid, ('',))[0] in ('iris', 'white', 'dissolve'): whoosh(a - .35, .7, .35)

# per-shot events (shot-local seconds)
whoosh(T0('c12') + BY['c12']['dur'] - .9, 1.2, .5)                                             # into the chalk eye
for sid, t0, t1 in (('c02', .2, 2.8), ('c08', .2, 2.5)): chalk(T0(sid) + t0, T0(sid) + t1)
roar(T0('c13') + .05, 2.4, 1.0, 55); boom(T0('e01'), .3, 4)
for k in range(9): boom(T0('e02') + .5 + k * BY['e02']['dur'] / 10 + 1.6, .7, 2.5)               # meteor hits (matches s_e02)
boom(T0('e03') + .8, 1.0, 3.5, 30); water(T0('e03') + .8, T0('e03') + 2.2, .3)
crackle(T0('e04') + 4.2, T0('e04') + 8.9, .25, 30)                                              # the drink on fire
whoosh(T0('e06') + .5, 1.0, .4); water(T0('e06') + 1.0, T0('e06') + 2.0, .2)                     # splash under
tick(T0('e08') + 3.2, .3)                                                                         # bonk
for k in range(30): bubble(T0('m02') + k * .4, .12)
ding(T0('k04') + .8, .0); whoosh(T0('k04') + 1.1, .5, .4)
thud(T0('k06') + 5.0, .7, 90, 14); [tick(T0('k06') + 5.0 + k * .03, .2) for k in range(6)]
for k, t in enumerate((2.0, 5.5, 8.0)): whoosh(T0('p02') + t, 1.2, .3); boom(T0('p02') + t + 1.0, .5, 2.0, 50)
rumble(T0('p02'), T0('p02') + BY['p02']['dur'], .5, 600)
for k in range(10): step(T0('p07') + k / .55, .9, 32)
flap(T0('p07') + 1.2, .15, 12, 11)
for k in range(int(BY['p05']['dur'] * 6)): tick(T0('p05') + k / 6 + rng.uniform(0, .05), .05)
roar(T0('p11') + .7, 1.9, 1.0, 60)
for k in range(int(BY['d01']['dur'] / 1.6)): step(T0('d01') + k * 1.6, .45, 30)
roar(T0('d03') + 1.5, 1.2, .6, 75); [step(T0('d03') + k * .45, .5, 40) for k in range(8)]
flap(T0('d04') + 4.0, .2, 20, 14)
flap(T0('d05'), .14, 30, 9); chirp(T0('d05') + 5.1, .18)
whoosh(T0('a02') + 2.0, BY['a02']['dur'] - 2, .25)
for k in range(3): whoosh(T0('a03') + k * .6, 1.2, .5)
boom(T0('a04'), 1.4, 6.0, 26); rumble(T0('a04'), T0('a04') + BY['a04']['dur'], .9, 800)
for k in range(4): thud(T0('a04') + 3.0 + k * .4, .5, 50)
crackle(T0('a05'), T0('a05') + BY['a05']['dur'], .25, 25); thud(T0('a05') + 6.5, .5, 45)
flap(T0('a06'), .14, int(BY['a06']['dur'] * 9), 9)
chirp(T0('a07') + BY['a07']['dur'] - 1.2, .06)
for k in range(int(BY['n01']['dur'] * 8)): tick(T0('n01') + k / 8 + rng.uniform(0, .06), .05)
flap(T0('n02'), .05, int(BY['n02']['dur'] * 12), 12)
for k in range(int(BY['h04']['dur'] / .55)): tick(T0('h04') + .14 + k * .55, .35)
ding(T0('t02') + 1.0, .25); whoosh(T0('t02') + 1.6, .4, .3); thud(T0('t02') + 2.1, .25, 120, 20)
rumble(T0('t03'), T0('t03') + BY['t03']['dur'], .7, 120)
for k in range(8): tick(T0('t04') + .5 + k * .5, .05)
thud(T0('b04') + .5, 1.0, 55, 6); [tick(T0('b04') + .5 + k * .02, .3) for k in range(10)]; tick(T0('b04') + 1.4, .25); tick(T0('b04') + 1.55, .12)
whoosh(T0('b07') + BY['b07']['dur'] - .6, 1.2, .4)

def grms(a):
    m = np.abs(a).max() + 1e-12; g = a[np.abs(a) > .02 * m]
    return np.sqrt(np.mean(g ** 2)) if len(g) else 1e-9
vr = grms(voice); bed = sfx + amb
lvl = float(os.environ.get('SFXLVL', .25))                       # sound effects at 25 % of the narrator (-12 dB)
bed *= lvl * vr / grms(bed)
pk = .5 * np.abs(voice).max(); bed = np.tanh(bed / pk) * pk         # no hit pokes out over the narration
print('levels dB vs voice (gated RMS): sfx+ambience %.1f' % (20 * np.log10(grms(bed) / vr)))
mix = voice + bed; mix *= .89 / max(1e-6, np.abs(mix).max()) if np.abs(mix).max() > .89 else 1.0
def write(path, a):
    s = (np.clip(a, -1, 1) * 32767).astype(np.int16)
    with wave.open(path, 'wb') as w_: w_.setnchannels(1); w_.setsampwidth(2); w_.setframerate(SR); w_.writeframes(s.tobytes())
mw = os.path.join(tmp, 'mix.wav'); write(mw, mix)
sh('ffmpeg', '-loglevel', 'error', '-y', '-i', pic, '-i', mw, '-filter_complex', '[1:a]pan=stereo|c0=c0|c1=c0,loudnorm=I=-14:TP=-1.0:LRA=11[a]',
   '-map', '0:v', '-map', '[a]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '256k', '-ar', '48000', '-shortest', '-movflags', '+faststart', outp)
print('wrote', outp, 'duration', round(TOTAL, 2))
