"""python3 compose.py <chunk_dir> <out.mp4>  - The Slowest Zombie Apocalypse.
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
def pluck(freq, dur, amp=.2):
    n = int(dur * SR); x = np.arange(n) / SR
    s = np.sin(2 * np.pi * freq * x) + .5 * np.sin(4 * np.pi * freq * x) + .25 * np.sin(6 * np.pi * freq * x)
    return amp * s * np.exp(-x * 7) * env(n, .003, .05)
def organ(freq, dur, amp=.06):
    n = int(dur * SR); x = np.arange(n) / SR; s = np.zeros(n)
    for h, a in ((1, 1), (2, .5), (3, .3), (4, .2), (6, .1)): s += a * np.sin(2 * np.pi * freq * h * x * (1 + .003 * np.sin(2 * np.pi * 5.5 * x)))
    return amp * s * env(n, .08, .2)
def creep(t0, t1, bpm=66, amp=1.0):
    """the 'scary' zombie theme, played far too slowly: pizzicato minor bass walk + spooky organ chords + a tiptoe triangle"""
    beat = 60 / bpm; seq = [('A', 2), ('C', 3), ('E', 3), ('D#', 3), ('E', 3), ('C', 3), ('B', 2), ('G#', 2)]
    chords = [[('A', 3), ('C', 4), ('E', 4)], [('F', 3), ('A', 3), ('C', 4)], [('D', 3), ('F', 3), ('A', 3)], [('E', 3), ('G#', 3), ('B', 3)]]
    t = t0; k = 0
    while t < t1 - .05:
        nm, oc = seq[k % len(seq)]; add(music, amp * pluck(f(nm, oc), beat * .9, .32), t)
        if k % 4 == 0:
            for c in chords[(k // 4) % len(chords)]: add(music, amp * organ(f(*c), min(beat * 3.8, t1 - t), .035), t)
        if k % 2 == 1: n = int(.12 * SR); x = np.arange(n) / SR; add(music, amp * .03 * np.sin(2 * np.pi * 2600 * x) * np.exp(-x * 30), t)
        t += beat; k += 1
def jingle(t0, amp=1.0):
    """TV news brass fanfare"""
    for k, (nm, oc, d) in enumerate((('C', 5, .18), ('E', 5, .18), ('G', 5, .18), ('C', 6, .7))):
        add(music, amp * brass(f(nm, oc), d + .1, .1, 8), t0 + k * .18)
        add(music, amp * brass(f(nm, oc - 1), d + .1, .06, 6), t0 + k * .18)
def happy(t0, t1, bpm=104, amp=1.0):
    """after the reveal: a light ukulele-ish strum in C major"""
    beat = 60 / bpm; prog = [[('C', 4), ('E', 4), ('G', 4)], [('A', 3), ('C', 4), ('E', 4)], [('F', 3), ('A', 3), ('C', 4)], [('G', 3), ('B', 3), ('D', 4)]]
    t = t0; k = 0
    while t < t1 - .05:
        ch = prog[(k // 4) % 4]
        for j, c in enumerate(ch): add(music, amp * pluck(f(*c), beat * .9, .1), t + j * .012)
        if k % 2 == 0: add(music, amp * pluck(f(ch[0][0], 2), beat * .9, .2), t)
        t += beat * (1 if k % 4 != 3 else 1); k += 1
creep(0.25, 11.8)                                   # Tuesday... very, very slowly; the jogger
n = int(2.1 * SR); x = np.arange(n) / SR; add(music, .05 * np.sin(2 * np.pi * f('A', 2) * x) * env(n, .05, .4), 11.85)   # held note under the siren
creep(13.95, 19.55, bpm=96, amp=1.0)                # boarding up / panic buying: same theme, faster
creep(19.6, 26.3, bpm=58, amp=.9)                   # noon -> sunset at the bus stop: slower still
creep(26.4, 28.6, bpm=58, amp=.7)
jingle(28.7)                                        # the evening news
creep(31.25, 37.85, bpm=72)                         # the coffee cart
creep(37.9, 42.8, bpm=84, amp=1.1)                  # day three: tension
for tt in np.arange(40.7, 42.8, .25): add(music, drum(.18), tt)            # snare-ish drum roll under 'took aim'
n = int(1.6 * SR); x = np.arange(n) / SR; add(music, .07 * (np.sin(2 * np.pi * 55 * x) + .5 * np.sin(2 * np.pi * 82.4 * x)) * env(n, .05, .5), 42.9)   # low horror hit
for k, (nm, oc) in enumerate((('A#', 3), ('A', 3), ('G#', 3), ('G', 3))):  # sad trombone 'wah wah wah wahhh' on 'Gently'
    add(music, brass(f(nm, oc), .38 if k < 3 else 1.1, .1, 5), 46.9 + k * .38)
creep(50.1, 53.3, bpm=60, amp=.6)
happy(54.75, TOTAL - .3)

amb = np.zeros(N)
city = np.convolve(rng.standard_normal(N), np.ones(300) / 300, 'same') * .05          # distant traffic rumble
for a0, a1 in ((28.65, 31.25),): city[int(a0 * SR):int(a1 * SR)] *= .05                 # studio
amb += city
def murmur(t0, t1, a=.05):
    n = int((t1 - t0) * SR); mm = rng.standard_normal(n); mm = np.convolve(mm, np.hanning(140) / 70, 'same')
    x = np.arange(n) / SR; add(amb, a * mm * (1 + .6 * np.sin(x * 3.1) * np.sin(x * 1.7)) * env(n, .4, .5), t0)
murmur(13.95, 19.5, .05); murmur(37.9, 42.8, .04); murmur(54.75, 62.0, .05)
for t0, t1 in ((24.0, 26.3),):                                                            # crickets at sunset
    n = int((t1 - t0) * SR); x = np.arange(n) / SR; add(amb, .012 * np.sin(2 * np.pi * 4300 * x) * (np.sin(2 * np.pi * 28 * x) > .3), t0)

sfx = np.zeros(N)
def thump(t, a=.6, fr=90, d=.35, noise=.4):
    n = int(d * SR); x = np.arange(n) / SR; add(sfx, a * np.exp(-x * 11) * np.sin(2 * np.pi * fr * x) + a * noise * rng.standard_normal(n) * np.exp(-x * 35), t)
def clack(t, a=.4): thump(t, a, 380, .12, .8)
def clink(t, a=.25):
    n = int(.4 * SR); x = np.arange(n) / SR; add(sfx, a * (np.sin(2 * np.pi * 3100 * x) + .6 * np.sin(2 * np.pi * 4700 * x)) * np.exp(-x * 14), t)
def shuffle(t0, t1, every=1.1, a=.05):
    for tt in np.arange(t0, t1, every): n = int(.35 * SR); add(sfx, a * np.convolve(rng.standard_normal(n), np.ones(30) / 30, 'same') * np.hanning(n), tt)
shuffle(3.5, 6.3, .9, .08)                                                 # slippers on asphalt
n = int(2.0 * SR); x = np.arange(n) / SR                                   # the siren
add(sfx, .12 * np.sin(2 * np.pi * (650 + 250 * np.sin(2 * np.pi * 1.2 * x)) * x) * env(n, .1, .4), 11.95)
for k in range(9): thump(14.05 + k * .26, .4, 220, .12, .7)                # hammering
for k in range(6): thump(16.3 + k * .2, .12, 140, .15, .9)                 # running feet
for k in range(4): clack(40.8 + k * .33, .25)                              # pistols cocked
n = int(1.0 * SR); x = np.arange(n) / SR                                   # the groan
add(sfx, .14 * np.sin(2 * np.pi * (95 + 15 * np.sin(2 * np.pi * 3 * x)) * x) * (1 + .5 * np.sin(2 * np.pi * 7 * x)) * env(n, .1, .3), 43.1)
n = int(.3 * SR); x = np.arange(n) / SR; add(sfx, .18 * np.convolve(rng.standard_normal(n), np.ones(60) / 60, 'same') * np.exp(-x * 9), 45.3)   # gummy 'chomp'
for tt in (46.95, 47.4): n = int(.25 * SR); x = np.arange(n) / SR; add(sfx, .1 * np.convolve(rng.standard_normal(n), np.ones(80) / 80, 'same') * np.exp(-x * 10), tt)   # gum gum
clink(35.3, .2); clink(35.45, .15)                                         # coin on the cart
n = int(.45 * SR); x = np.arange(n) / SR                                   # record scratch on 'It wasn't a zombie'
add(sfx, .12 * np.sin(2 * np.pi * (300 + 1400 * x) * x) * np.exp(-x * 4) + .06 * rng.standard_normal(n) * np.exp(-x * 6), 53.3)
for tt in (53.6, 53.9, 54.2): n = int(.12 * SR); add(sfx, .05 * rng.standard_normal(n) * np.hanning(n), tt)   # wipe wipe
n = int(.5 * SR); x = np.arange(n) / SR; add(sfx, .06 * np.sin(2 * np.pi * 880 * x) * np.exp(-x * 6), 60.0)    # phone 'bloop'

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
music *= .25 * vr / grms(music)          # background at 25% of the narrator (-12 dB)
sfx *= .22 * vr / grms(sfx)
sfx = np.clip(sfx, -.4 * np.abs(v).max(), .4 * np.abs(v).max())
amb *= .12 * vr / (np.sqrt(np.mean(amb ** 2)) + 1e-9)
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
