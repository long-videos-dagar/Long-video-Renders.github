"""python3 compose.py <chunk_dir> <out.mp4>
Joins rendered chunks into shots, links shots with cuts / dissolves (shots carry a short tail handle), burns 1-3 word
subtitles, adds the DAGAR CLIPS end card, and mixes voice + western score (plucked guitar, synthesised) + ambience + SFX.
Music sits at about half the voice level."""
import json, os, sys, glob, subprocess, tempfile, math, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont
H = os.path.dirname(os.path.abspath(__file__)); art, outp = sys.argv[1], sys.argv[2]
film = json.load(open(os.path.join(H, 'shots.json'))); fps = film['fps']
W, Hh = 1440, 2560
NOSUBS = bool(os.environ.get('NOSUBS')); NOLOGO = bool(os.environ.get('NOLOGO'))
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
SR = 48000; N = int(TOTAL * SR); rng = np.random.default_rng(3)
def pluck(freq, dur, amp=.3, bright=.5):
    """Karplus-Strong plucked string"""
    n = int(dur * SR); p = max(2, int(SR / freq)); buf = rng.uniform(-1, 1, p) * amp; out = np.zeros(n)
    for i in range(n):
        out[i] = buf[i % p]; nxt = (i + 1) % p
        buf[i % p] = (.5 - .5 * (1 - bright) * .2) * (buf[i % p] + buf[nxt]) * .996
    return out
def add(dst, sig, t):
    i = int(t * SR); j = min(len(dst), i + len(sig))
    if i < len(dst): dst[i:j] += sig[:j - i]
NOTE = {n: 440 * 2 ** ((k - 9) / 12) for k, n in enumerate(['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'])}
def f(n, o): return NOTE[n] * 2 ** (o - 4)
music = np.zeros(N)
chords = [('A', [('A', 2), ('E', 3), ('A', 3), ('C', 4), ('E', 4)]), ('E', [('E', 2), ('B', 2), ('E', 3), ('G#', 3), ('B', 3)]),
          ('F', [('F', 2), ('C', 3), ('F', 3), ('A', 3), ('C', 4)]), ('E', [('E', 2), ('B', 2), ('E', 3), ('G#', 3), ('B', 3)])]
beat = 60 / 84.0; t = .2; ci = 0
cache = {}
while t < TOTAL - 2.5:
    _, notes = chords[ci % 4]
    for k, idx in enumerate([0, 2, 3, 4, 3, 2, 1, 2]):
        nm, oc = notes[idx]; key = (nm, oc)
        if key not in cache: cache[key] = pluck(f(nm, oc), 2.2, .22 if idx == 0 else .14)
        add(music, cache[key], t + k * beat / 2)
    t += 4 * beat; ci += 1
# whistle melody over the hook and the payoff (sine with vibrato)
def whistle(t0, seq):
    tt = t0
    for nm, oc, d in seq:
        n = int(d * SR); x = np.arange(n) / SR; fr = f(nm, oc) * (1 + .006 * np.sin(2 * np.pi * 5.5 * x))
        env = np.minimum(1, x / .06) * np.minimum(1, (d - x) / .15); add(music, .12 * env * np.sin(2 * np.pi * np.cumsum(fr) / SR), tt); tt += d
whistle(.4, [('E', 5, .5), ('A', 5, .9), ('B', 5, .3), ('C', 6, .9), ('B', 5, .4), ('A', 5, 1.2)])
whistle(64.3, [('A', 5, .6), ('C', 6, .6), ('E', 6, 1.0), ('D', 6, .5), ('C', 6, .5), ('A', 5, 1.8)])
# tension: low drum heartbeat through the bank scene
for tt in np.arange(28.0, 44.8, beat):
    n = int(.35 * SR); x = np.arange(n) / SR; add(music, .5 * np.exp(-x * 14) * np.sin(2 * np.pi * (60 - 20 * x) * x), tt)
# ambience
amb = np.zeros(N)
wind = rng.standard_normal(N); wind = np.convolve(wind, np.ones(400) / 400, 'same'); wind *= .06 * (1 + .5 * np.sin(np.arange(N) / SR * .3))
amb += wind
for t0, t1 in ((20.85, 28.05),):                                  # night crickets
    n = int((t1 - t0) * SR); x = np.arange(n) / SR
    cr = .018 * np.sin(2 * np.pi * 4300 * x) * (np.sin(2 * np.pi * 28 * x) > .3) * (np.sin(2 * np.pi * .9 * x) > -.2); add(amb, cr, t0)
for t0, t1 in ((0, 7.55), (47.3, 49.75), (53.85, 69.7)):         # crowd murmur
    n = int((t1 - t0) * SR); mm = rng.standard_normal(n); mm = np.convolve(mm, np.hanning(120) / 60, 'same')
    mm *= .05 * (1 + .6 * np.sin(np.arange(n) / SR * 3.1) * np.sin(np.arange(n) / SR * 1.7)); add(amb, mm, t0)
# SFX
sfx = np.zeros(N)
def click(t, a=.6, fr=2500, d=.03):
    n = int(d * SR); x = np.arange(n) / SR; add(sfx, a * np.exp(-x * 160) * np.sin(2 * np.pi * fr * x) + a * .4 * rng.standard_normal(n) * np.exp(-x * 220), t)
click(34.9, .5); click(35.05, .5, 1800); click(36.6, .7, 1200)                   # hammer cocked
n = int(1.0 * SR); x = np.arange(n) / SR; add(sfx, .25 * np.sin(2 * np.pi * (70 + 30 * np.sin(x * 9)) * x) * np.exp(-x * 1.4), 30.6)   # vault groan
add(sfx, .6 * np.exp(-np.arange(int(.4 * SR)) / SR * 9) * rng.standard_normal(int(.4 * SR)) * .5, 31.35)       # vault clunk
for tt in (32.2, 32.9, 33.6): click(tt, .3, 3800, .08)                          # gold clinks
gn = int(.7 * SR); gx = np.arange(gn) / SR; gasp = rng.standard_normal(gn) * np.exp(-((gx - .2) / .18) ** 2) * .25; add(sfx, np.convolve(gasp, np.ones(30) / 30, 'same'), 64.5)
for tt in np.arange(7.6, 10.0, .42): click(tt, .25, 400, .06); click(tt + .14, .2, 500, .05)   # hooves
def write(path, a):
    a = np.clip(a, -1, 1); s = (a * 32767).astype(np.int16)
    with wave.open(path, 'wb') as w_: w_.setnchannels(1); w_.setsampwidth(2); w_.setframerate(SR); w_.writeframes(s.tobytes())
# levels: music RMS ~ half the voice RMS (speech parts)
vw = os.path.join(tmp, 'voice.wav'); sh('ffmpeg', '-loglevel', 'error', '-y', '-i', os.path.join(H, film['voice']), '-ac', '1', '-ar', str(SR), vw)
v = np.frombuffer(wave.open(vw).readframes(10 ** 9), dtype=np.int16).astype(np.float32) / 32767
vr = np.sqrt(np.mean(v[np.abs(v) > .02] ** 2)) if np.any(np.abs(v) > .02) else .1
fade = np.ones(N); fade[int((TOTAL - 3) * SR):] = np.linspace(1, 0, N - int((TOTAL - 3) * SR)); music *= fade
mr = np.sqrt(np.mean(music ** 2)) + 1e-9; music *= .5 * vr / mr
amb *= .35 * vr / (np.sqrt(np.mean(amb ** 2)) + 1e-9); sfx *= .8
bed = music + amb + sfx
for p_, a in (('bed.wav', bed / max(1.0, np.abs(bed).max())),): write(os.path.join(tmp, p_), a)
mixa = os.path.join(tmp, 'mix.m4a')
sh('ffmpeg', '-loglevel', 'error', '-y', '-i', vw, '-i', os.path.join(tmp, 'bed.wav'), '-filter_complex',
   f"[0:a]apad,atrim=0:{TOTAL}[v];[1:a]atrim=0:{TOTAL}[b];[v][b]amix=inputs=2:normalize=0:duration=longest,pan=stereo|c0=c0|c1=c0,loudnorm=I=-14:TP=-1.0:LRA=11[a]",
   '-map', '[a]', '-c:a', 'aac', '-b:a', '192k', mixa)
lst2 = os.path.join(tmp, 'fin.txt'); open(lst2, 'w').write(f"file '{main}'\n" + ('' if NOLOGO else f"file '{logo}'\n")); vid = os.path.join(tmp, 'video.mp4')
sh('ffmpeg', '-loglevel', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst2, '-c', 'copy', vid)
sh('ffmpeg', '-loglevel', 'error', '-y', '-i', vid, '-i', mixa, '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', outp)
print('wrote', outp)
