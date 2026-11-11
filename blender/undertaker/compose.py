"""python3 compose.py <chunk_dir> <out.mp4>  - The Undertaker's Best Customer.
Joins chunks into shots (cuts / dissolves), optional subtitles / end card (off by default), and mixes the voice with a
synthesised dark-comedy funeral score (tuba oom-pah, brass stabs, clarinet line, the diegetic brass band, bell tolls),
ambience and SFX.  Music sits at half the voice level; SFX at or below that."""
import json, os, sys, glob, subprocess, tempfile, math, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont
H = os.path.dirname(os.path.abspath(__file__)); art, outp = sys.argv[1], sys.argv[2]
film = json.load(open(os.path.join(H, 'shots.json'))); fps = film['fps']
W, Hh = 1440, 2560
NOSUBS = bool(os.environ.get('NOSUBS')); NOLOGO = bool(os.environ.get('NOLOGO'))
NOSUBS = NOSUBS or not film.get('subs'); NOLOGO = NOLOGO or not os.environ.get('LOGO')
MAINEND = film['shots'][-1]['t0'] + film['shots'][-1]['dur']; TOTAL = MAINEND + (0.0 if NOLOGO else 3.0)
HANDLE = float(os.environ.get('HANDLE', .25))
TRANS = film.get('trans', {})            # shot id -> ('dissolve', seconds) for the transition INTO that shot
def sh(*a): subprocess.run(a, check=True)
tmp = tempfile.mkdtemp()
FB = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'


def shotfile(sid):
    ps = sorted(glob.glob(f"{art}/chunk_{sid}_[0-9]*.mp4"))
    if not ps: return None
    lst = os.path.join(tmp, sid + '.txt'); open(lst, 'w').write(''.join(f"file '{os.path.abspath(p)}'\n" for p in ps))
    o = os.path.join(tmp, sid + '.mp4'); sh('ffmpeg', '-loglevel', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst, '-c', 'copy', o); return o


def probe_wh(p):
    r = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v', '-show_entries', 'stream=width,height', '-of', 'csv=p=0', p], capture_output=True, text=True).stdout.strip().split(',')
    return int(r[0]), int(r[1])


# ---------------------------------------------------------------- picture: shots chained with xfade (1-frame = cut)
shots = film['shots']; files = []
for s in shots:
    f = shotfile(s['id'])
    if f is None:     # missing shot: black placeholder so the timeline never shifts
        f = os.path.join(tmp, s['id'] + '_black.mp4'); sh('ffmpeg', '-loglevel', 'error', '-y', '-f', 'lavfi', '-i', f'color=c=black:s={W}x{Hh}:r={fps}:d={s["dur"] + HANDLE:.3f}', '-pix_fmt', 'yuv420p', f); print('missing shot', s['id'])
    files.append(f)
W, Hh = probe_wh(files[0])
inputs = []; fc = []
for i, (s, f) in enumerate(zip(shots, files)):
    nxt = TRANS.get(shots[i + 1]['id'], ['cut', 0])[1] if i + 1 < len(shots) else 0
    keep = s['dur'] + max(1.0 / fps, nxt)
    inputs += ['-i', f]; fc.append(f"[{i}:v]trim=0:{keep:.4f},setpts=PTS-STARTPTS,fps={fps},scale={W}:{Hh},format=yuv420p[c{i}]")
acc = '[c0]'
for i in range(1, len(shots)):
    tr = TRANS.get(shots[i]['id'], ['cut', 0]); d = max(1.0 / fps, tr[1] if tr[0] == 'dissolve' else 1.0 / fps)
    fc.append(f"{acc}[c{i}]xfade=transition={'fade' if tr[0] == 'dissolve' else 'fade'}:duration={d:.4f}:offset={shots[i]['t0']:.4f}[x{i}]"); acc = f'[x{i}]'
# subtitles: bold white, black outline, ~70% height, 1-3 words
font = ImageFont.truetype(FB, int(W * .095)); k = len(shots); lab = acc
for j, (txt, a, b) in enumerate([] if NOSUBS else film['subs']):
    im = Image.new('RGBA', (W, Hh), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.text((W / 2, Hh * .70), txt, font=font, fill='white', anchor='mm', stroke_width=max(5, int(W * .011)), stroke_fill='black')
    p = os.path.join(tmp, f's{j}.png'); im.save(p); inputs += ['-i', p]
    fc.append(f"{lab}[{k}:v]overlay=enable='between(t,{a:.3f},{b:.3f})'[s{j}]"); lab = f'[s{j}]'; k += 1
fc.append(f"{lab}fade=t=out:st={MAINEND - .8:.2f}:d=0.8,trim=0:{MAINEND:.4f}[vo]")
main = os.path.join(tmp, 'main.mp4')
sh('ffmpeg', '-loglevel', 'error', '-y', *inputs, '-filter_complex', ';'.join(fc), '-map', '[vo]', '-c:v', 'libx264', '-crf', '15', '-preset', 'medium', '-pix_fmt', 'yuv420p', '-r', str(fps), main)
# end card
lg = Image.new('RGB', (W, Hh), (6, 5, 4)); d = ImageDraw.Draw(lg); f1 = ImageFont.truetype(FB, int(W * .13)); f2 = ImageFont.truetype(FB, int(W * .045))
cx, cy = W / 2, Hh * .44; r = W * .11
d.rounded_rectangle([cx - r, cy - r * 1.5, cx + r, cy - r * .1], radius=int(r * .28), fill=(214, 168, 56))
d.polygon([(cx - r * .3, cy - r * 1.2), (cx - r * .3, cy - r * .4), (cx + r * .45, cy - r * .8)], fill=(6, 5, 4))
d.text((cx, cy + r * .75), 'DAGAR', font=f1, fill='white', anchor='mm'); d.text((cx, cy + r * 1.95), 'C L I P S', font=f1, fill=(214, 168, 56), anchor='mm')
d.text((cx, cy + r * 3.0), 'STORIES YOU CAN SEE', font=f2, fill=(150, 150, 150), anchor='mm')
lp = os.path.join(tmp, 'logo.png'); lg.save(lp); logo = os.path.join(tmp, 'logo.mp4')
if not NOLOGO: sh('ffmpeg', '-loglevel', 'error', '-y', '-loop', '1', '-i', lp, '-t', f'{TOTAL - MAINEND:.3f}', '-vf', f"fps={fps},fade=t=in:st=0:d=0.7,fade=t=out:st={TOTAL - MAINEND - 0.6:.2f}:d=0.6", '-c:v', 'libx264', '-crf', '15', '-pix_fmt', 'yuv420p', logo)

# ---------------------------------------------------------------- sound
SR = 48000; N = int(TOTAL * SR); rng = np.random.default_rng(7)
NOTE = {n: 440 * 2 ** ((k - 9) / 12) for k, n in enumerate(['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'])}
def f(n, o): return NOTE[n] * 2 ** (o - 4)
def add(dst, sig, t):
    i = int(t * SR); j = min(len(dst), i + len(sig))
    if 0 <= i < len(dst): dst[i:j] += sig[:j - i]
def env(n, a=.01, r=.1, sus=1.0):
    x = np.arange(n) / SR; d = n / SR
    return np.minimum(1, x / a) * np.minimum(1, np.maximum(0, (d - x) / r)) * sus
def brass(freq, dur, amp=.2, bright=6):
    n = int(dur * SR); x = np.arange(n) / SR; s = np.zeros(n)
    for h in range(1, bright + 1): s += np.sin(2 * np.pi * freq * h * x * (1 + .002 * np.sin(2 * np.pi * 5 * x))) / h ** 1.2
    return amp * s * env(n, .03, .08)
def tuba(freq, dur, amp=.35):
    n = int(dur * SR); x = np.arange(n) / SR
    s = np.sin(2 * np.pi * freq * x) + .45 * np.sin(4 * np.pi * freq * x) + .2 * np.sin(6 * np.pi * freq * x)
    return amp * s * env(n, .02, .12) * np.exp(-x * 2.2)
def clar(freq, dur, amp=.12):
    n = int(dur * SR); x = np.arange(n) / SR; vib = 1 + .005 * np.sin(2 * np.pi * 5.2 * x)
    s = np.sin(2 * np.pi * freq * vib * x) + .35 * np.sin(6 * np.pi * freq * vib * x) + .15 * np.sin(10 * np.pi * freq * vib * x)
    return amp * s * env(n, .05, .12)
def drum(amp=.4):
    n = int(.3 * SR); x = np.arange(n) / SR; return amp * np.exp(-x * 13) * np.sin(2 * np.pi * (70 - 30 * x) * x) + amp * .25 * rng.standard_normal(n) * np.exp(-x * 40)
def cymbal(amp=.08):
    n = int(.25 * SR); x = np.arange(n) / SR; return amp * rng.standard_normal(n) * np.exp(-x * 18)

music = np.zeros(N)
MINOR = [(('A', 1), [('A', 3), ('C', 4), ('E', 4)]), (('E', 1), [('G#', 3), ('B', 3), ('E', 4)]), (('F', 1), [('A', 3), ('C', 4), ('F', 4)]), (('E', 1), [('G#', 3), ('B', 3), ('D', 4)])]
MAJOR = [(('C', 2), [('E', 4), ('G', 4), ('C', 5)]), (('F', 1), [('F', 4), ('A', 4), ('C', 5)]), (('G', 1), [('G', 4), ('B', 4), ('D', 5)]), (('C', 2), [('E', 4), ('G', 4), ('C', 5)])]
def march(t0, t1, prog, bpm, lead=None, band=False, amp=1.0):
    beat = 60 / bpm; t = t0; bar = 0
    while t < t1 - .05:
        root, ch = prog[bar % len(prog)]
        for b in range(4):
            tb = t + b * beat
            if tb >= t1: break
            if b in (0, 2): add(music, amp * tuba(f(root[0], root[1] + (1 if b == 2 and band else 0)), beat * .9, .38), tb)
            else:
                for nm, oc in ch: add(music, amp * brass(f(nm, oc), beat * .45, .055 if not band else .07), tb)
            if band: add(music, amp * drum(.3 if b in (0, 2) else .12), tb); add(music, amp * cymbal(.04 if b in (1, 3) else 0), tb)
        t += 4 * beat; bar += 1
    if lead:
        tt = t0 + lead[0]
        for nm, oc, d in lead[1]:
            if tt >= t1: break
            if nm != 'R': add(music, amp * (brass(f(nm, oc), min(d, t1 - tt) * beat, .09, 8) if band else clar(f(nm, oc), min(d, t1 - tt) * beat, .11)), tt)
            tt += d * beat
FUN = [('A', 4, 1), ('C', 5, .5), ('B', 4, .5), ('A', 4, 1), ('E', 4, 1), ('F', 4, 1.5), ('E', 4, .5), ('D', 4, 1), ('R', 0, 1),
       ('E', 4, 1), ('G#', 4, .5), ('A', 4, .5), ('B', 4, 1), ('C', 5, 1), ('B', 4, 1.5), ('G#', 4, .5), ('A', 4, 2)] * 3
HAP = [('C', 5, 1), ('E', 5, .5), ('G', 5, .5), ('C', 6, 1), ('G', 5, 1), ('A', 5, 1), ('F', 5, 1), ('G', 5, 2),
       ('E', 5, 1), ('G', 5, .5), ('E', 5, .5), ('D', 5, 1), ('C', 5, 1), ('D', 5, 1.5), ('E', 5, .5), ('C', 5, 2)] * 3
march(0.3, 43.6, MINOR, 72, lead=(5.0, FUN))                 # sombre-silly funeral march under the first four funerals
march(43.6, 59.7, MAJOR, 84, lead=(2.2, HAP), band=True)     # the perfect funeral: the band strikes up (cuts dead on 'stopped')
march(61.55, 72.9, MAJOR, 92, lead=(.0, HAP), band=True, amp=1.1)   # 'The band played' -> laughter, cuts on 'He didn't.'
# 'stopped': one last heartbeat, then a held low drone until the band comes back
for tt, a in ((58.9, .6), (59.55, .35)): add(music, drum(a), tt)
n = int(1.9 * SR); x = np.arange(n) / SR; add(music, .06 * np.sin(2 * np.pi * 55 * x) * env(n, .4, .8), 59.7)
# three days: a slow church bell per day + low drone, fading out
def bell(fr, amp=.22, d=3.5):
    n = int(d * SR); x = np.arange(n) / SR; s = np.zeros(n)
    for k, (m, a) in enumerate(((.5, 1), (1, .8), (1.19, .5), (1.5, .4), (2.0, .35), (2.52, .2), (2.66, .15), (3.01, .12))):
        s += a * np.sin(2 * np.pi * fr * m * x) * np.exp(-x * (1.2 + k * .6))
    return amp * s
for tt in (75.35, 76.3, 77.25): add(music, bell(f('E', 3)), tt)
n = int(3.3 * SR); x = np.arange(n) / SR; add(music, .05 * np.sin(2 * np.pi * 41.2 * x) * env(n, .6, 1.5), 75.3)

# ambience: wind outdoors, shop room tone, crowd murmur + laughter on the hill
amb = np.zeros(N)
wind = rng.standard_normal(N); wind = np.convolve(wind, np.ones(500) / 500, 'same'); wind *= .06 * (1 + .6 * np.sin(np.arange(N) / SR * .35))
for a0, a1 in ((29.8, 32.8), (43.6, 45.75)): wind[int(a0 * SR):int(a1 * SR)] *= .15          # indoors
wind[int(37.35 * SR):int(40.25 * SR)] *= 2.2                                                     # the empty funeral: gusts
amb += wind
def murmur(t0, t1, a=.05, laugh=False):
    n = int((t1 - t0) * SR); mm = rng.standard_normal(n); mm = np.convolve(mm, np.hanning(140) / 70, 'same')
    x = np.arange(n) / SR; mod = (1 + .6 * np.sin(x * 3.1) * np.sin(x * 1.7))
    if laugh: mod *= 1 + 1.4 * (np.sin(2 * np.pi * 5.5 * x) > .2) * (np.sin(2 * np.pi * .7 * x) > -.3)
    add(amb, a * mm * mod * env(n, .5, .6), t0)
murmur(64.25, 67.5, .05); murmur(67.5, 72.85, .08, laugh=True)
for t0, t1 in ((75.6, 76.1), (76.55, 77.05), (77.5, 78.0)):                                     # crickets on the nights
    n = int((t1 - t0) * SR); x = np.arange(n) / SR; add(amb, .015 * np.sin(2 * np.pi * 4300 * x) * (np.sin(2 * np.pi * 28 * x) > .3), t0)

# SFX (frames of the picture were locked first)
sfx = np.zeros(N)
def thump(t, a=.6, fr=90, d=.35, noise=.4):
    n = int(d * SR); x = np.arange(n) / SR; add(sfx, a * np.exp(-x * 11) * np.sin(2 * np.pi * fr * x) + a * noise * rng.standard_normal(n) * np.exp(-x * 35), t)
def clack(t, a=.4): thump(t, a, 380, .12, .8)
def whoosh(t, a=.25, d=.5):
    n = int(d * SR); x = np.arange(n) / SR; s = np.convolve(rng.standard_normal(n), np.ones(40) / 40, 'same'); add(sfx, a * s * np.sin(np.pi * x / d) ** 2, t)
def clink(t, a=.25):
    n = int(.4 * SR); x = np.arange(n) / SR; add(sfx, a * (np.sin(2 * np.pi * 3100 * x) + .6 * np.sin(2 * np.pi * 4700 * x)) * np.exp(-x * 14), t)
thump(3.42, .55); clack(3.45, .35)                                   # lid bangs open
n = int(.25 * SR); x = np.arange(n) / SR; add(sfx, .35 * np.convolve(rng.standard_normal(n), np.ones(12) / 12, 'same') * np.exp(-x * 14), 13.62)   # tiny cough
for tt in (14.22, 15.67): add(sfx, sum(brass(f(nm, oc), .9, .07) for nm, oc in (('A', 2), ('C', 3), ('E', 3))), tt)                           # 'Funeral.' stings
thump(21.8, .6, 70); clack(21.82, .5); whoosh(21.85, .3, .7); thump(22.75, .35, 120)   # lid kicked off, flies, lands
for tt in (30.95, 31.55): thump(tt, .45, 140, .2, .6)                # DOUBLE stamp
for k in range(14):                                                    # pencil scratching
    tt = 32.9 + k * .11 + rng.uniform(0, .03); n = int(.07 * SR); add(sfx, .08 * rng.standard_normal(n) * np.hanning(n), tt)
whoosh(37.6, .25, 1.4); whoosh(38.9, .2, 1.2)                         # tumbleweed gust
thump(44.47, .55, 110, .3, .7)                                         # palm slams the ledger
for tt in (50.55, 51.25): clink(tt)                                    # coins
n = int(.5 * SR); x = np.arange(n) / SR; add(sfx, .05 * np.sin(2 * np.pi * 2200 * x) * np.exp(-x * 9), 59.72)   # the 'tink' on stopped
for k in range(10): thump(64.3 + k * .3, .08, 160, .1, .9)            # footsteps arriving
def write(path, a):
    a = np.clip(a, -1, 1); s = (a * 32767).astype(np.int16)
    with wave.open(path, 'wb') as w_: w_.setnchannels(1); w_.setsampwidth(2); w_.setframerate(SR); w_.writeframes(s.tobytes())
# levels: music at half the voice level (gated RMS), SFX at or below that, ambience low
vw = os.path.join(tmp, 'voice.wav'); sh('ffmpeg', '-loglevel', 'error', '-y', '-i', os.path.join(H, film['voice']), '-ac', '1', '-ar', str(SR), vw)
v = np.frombuffer(wave.open(vw).readframes(10 ** 9), dtype=np.int16).astype(np.float32) / 32767
def grms(a):
    m = np.abs(a).max() + 1e-12; g = a[np.abs(a) > .02 * m]
    return np.sqrt(np.mean(g ** 2)) if len(g) else 1e-9
vr = grms(v)
fade = np.ones(N); fade[int((TOTAL - 1.2) * SR):] = np.linspace(1, 0, N - int((TOTAL - 1.2) * SR)); music *= fade
music *= .5 * vr / grms(music)
sfx *= .45 * vr / grms(sfx)
sfx = np.clip(sfx, -.7 * np.abs(v).max(), .7 * np.abs(v).max())
amb *= .3 * vr / (np.sqrt(np.mean(amb ** 2)) + 1e-9)
print('levels dB vs voice (gated RMS): music %.1f  sfx %.1f' % (20 * np.log10(grms(music) / vr), 20 * np.log10(grms(sfx) / vr)))
bed = (music + amb + sfx) * float(os.environ.get('BED', '1'))      # BED=.5 -> background 50% quieter
write(os.path.join(tmp, 'bed.wav'), bed / max(1.0, np.abs(bed).max()))
mixa = os.path.join(tmp, 'mix.m4a')
sh('ffmpeg', '-loglevel', 'error', '-y', '-i', vw, '-i', os.path.join(tmp, 'bed.wav'), '-filter_complex',
   f"[0:a]apad,atrim=0:{TOTAL}[v];[1:a]atrim=0:{TOTAL}[b];[v][b]amix=inputs=2:normalize=0:duration=longest,pan=stereo|c0=c0|c1=c0,volume=1.6,alimiter=limit=0.89[a]",
   '-map', '[a]', '-c:a', 'aac', '-b:a', '192k', mixa)
lst2 = os.path.join(tmp, 'fin.txt'); open(lst2, 'w').write(f"file '{main}'\n" + ('' if NOLOGO else f"file '{logo}'\n")); vid = os.path.join(tmp, 'video.mp4')
sh('ffmpeg', '-loglevel', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst2, '-c', 'copy', vid)
sh('ffmpeg', '-loglevel', 'error', '-y', '-i', vid, '-i', mixa, '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', outp)
print('wrote', outp)
