"""python3 compose.py <chunk_dir> <out.mp4>: join shot chunks with 0.2 s dissolves, burn word subtitles (white, black outline, lower-centre)."""
import json, os, sys, glob, subprocess, tempfile
from PIL import Image, ImageDraw, ImageFont
H = os.path.dirname(os.path.abspath(__file__)); art, outp = sys.argv[1], sys.argv[2]
film = json.load(open(os.path.join(H, 'film.json'))); XF = .2; fps = film['fps']
W, Hh = film['w'], film['h']
def sh(*a): subprocess.run(a, check=True)
tmp = tempfile.mkdtemp(); shots = []
for s in film['shots']:
    parts = sorted(glob.glob(f"{art}/chunk_{s['id']}_*.mp4"))
    if not parts: print('missing shot', s['id']); continue
    lst = os.path.join(tmp, s['id'] + '.txt'); open(lst, 'w').write(''.join(f"file '{os.path.abspath(p)}'\n" for p in parts))
    o = os.path.join(tmp, s['id'] + '.mp4'); sh('ffmpeg', '-loglevel', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst, '-c', 'copy', o); shots.append((s, o))
# xfade chain
inputs = []; fc = []; t_end = 0.0; label = '[0:v]'
for i, (s, o) in enumerate(shots): inputs += ['-i', o]
off = 0.0
for i in range(1, len(shots)):
    off += shots[i - 1][0]['dur'] - XF
    nl = f'[x{i}]'; fc.append(f"{label}[{i}:v]xfade=transition=fade:duration={XF}:offset={off:.3f}{nl}"); label = nl
total = sum(s['dur'] for s, _ in shots) - XF * (len(shots) - 1)
# subtitle pngs; film.json subs are in 'authored' time (no overlap) -> shift by dissolves already consumed
def shift(t):
    k = 0
    for s, _ in shots:
        if t >= s['t0'] + s['dur'] - 1e-6: k += 1
    return t - XF * k
font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', int(W * .105))
pngs = []
for i, (txt, a, b) in enumerate(film['subs']):
    im = Image.new('RGBA', (W, Hh), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.text((W / 2, Hh * .70), txt, font=font, fill='white', anchor='mm', stroke_width=max(4, int(W * .012)), stroke_fill='black')
    p = os.path.join(tmp, f's{i}.png'); im.save(p); pngs.append((p, shift(a), shift(b)))
for p, a, b in pngs: inputs += ['-i', p]
n0 = len(shots)
for j, (p, a, b) in enumerate(pngs):
    nl = f'[s{j}]'; fc.append(f"{label}[{n0 + j}:v]overlay=enable='between(t,{a:.3f},{b:.3f})'{nl}"); label = nl
fc_s = ';'.join(fc) if fc else '[0:v]null[o]'
if not fc: label = '[o]'
sh('ffmpeg', '-loglevel', 'error', '-y', *inputs, '-filter_complex', fc_s, '-map', label, '-t', f'{total:.3f}', '-c:v', 'libx264', '-preset', 'slow', '-crf', '17', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', outp)
print('wrote', outp, f'{total:.1f}s')
