"""python3 compose.py <chunk_dir> <out.mp4>: shots (hard cuts, exact sync) + split-screen + subtitles + logo tail + audio mix (voice + storm + music)."""
import json, os, sys, glob, subprocess, tempfile, math
from PIL import Image, ImageDraw, ImageFont
H = os.path.dirname(os.path.abspath(__file__)); art, outp = sys.argv[1], sys.argv[2]
film = json.load(open(os.path.join(H, 'film.json'))); fps = film['fps']; W, Hh = film['w'], film['h']; TOTAL = film['total']; MAINEND = 71.4
def sh(*a): subprocess.run(a, check=True)
tmp = tempfile.mkdtemp(); parts = []
def shotfile(sid):
    ps = sorted(glob.glob(f"{art}/chunk_{sid}_[0-9]*.mp4"))
    if not ps: return None
    lst = os.path.join(tmp, sid + '.txt'); open(lst, 'w').write(''.join(f"file '{os.path.abspath(p)}'\n" for p in ps))
    o = os.path.join(tmp, sid + '.mp4'); sh('ffmpeg', '-loglevel', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst, '-c', 'copy', o); return o
fontB = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', int(W * .06))
for s in film['shots']:
    if s['id'] == 'split_b': continue
    if s['id'] == 'split_a':
        a, b = shotfile('split_a'), shotfile('split_b')
        if not a or not b: print('missing split'); continue
        lab = Image.new('RGBA', (W, Hh), (0, 0, 0, 0)); d = ImageDraw.Draw(lab)
        for txt, y in (('WITHOUT OIL', Hh * .06), ('WITH OIL', Hh * .56)):
            d.text((W / 2, y + Hh * .03), txt, font=fontB, fill='white', anchor='mm', stroke_width=max(3, int(W * .008)), stroke_fill='black')
        d.rectangle([0, Hh / 2 - 4, W, Hh / 2 + 4], fill=(255, 255, 255, 255)); lp = os.path.join(tmp, 'lab.png'); lab.save(lp)
        o = os.path.join(tmp, 'split.mp4')
        sh('ffmpeg', '-loglevel', 'error', '-y', '-i', a, '-i', b, '-i', lp, '-filter_complex',
           f"[0:v]crop={W}:{Hh // 2}:0:{Hh // 4}[t];[1:v]crop={W}:{Hh // 2}:0:{Hh // 4}[b];[t][b]vstack[v];[v][2:v]overlay[o]", '-map', '[o]', '-c:v', 'libx264', '-crf', '14', '-preset', 'fast', '-pix_fmt', 'yuv420p', '-r', str(fps), o)
        parts.append(o); continue
    o = shotfile(s['id'])
    if o: parts.append(o)
    else: print('missing shot', s['id'])
lst = os.path.join(tmp, 'all.txt'); open(lst, 'w').write(''.join(f"file '{p}'\n" for p in parts))
body = os.path.join(tmp, 'body.mp4'); sh('ffmpeg', '-loglevel', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst, '-c:v', 'libx264', '-crf', '14', '-preset', 'fast', '-pix_fmt', 'yuv420p', '-r', str(fps), body)
# subtitles
font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', int(W * .105))
inputs = ['-i', body]; fc = []; label = '[0:v]'; k = 1
for i, (txt, a, b) in enumerate(film['subs']):
    im = Image.new('RGBA', (W, Hh), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.text((W / 2, Hh * .70), txt, font=font, fill='white', anchor='mm', stroke_width=max(4, int(W * .012)), stroke_fill='black')
    p = os.path.join(tmp, f's{i}.png'); im.save(p); inputs += ['-i', p]
    fc.append(f"{label}[{k}:v]overlay=enable='between(t,{a:.3f},{b:.3f})'[s{i}]"); label = f'[s{i}]'; k += 1
fc.append(f"{label}fade=t=out:st={MAINEND - .8:.2f}:d=0.8[vo]")
main = os.path.join(tmp, 'main.mp4')
sh('ffmpeg', '-loglevel', 'error', '-y', *inputs, '-filter_complex', ';'.join(fc), '-map', '[vo]', '-t', f'{MAINEND:.3f}', '-c:v', 'libx264', '-crf', '15', '-preset', 'fast', '-pix_fmt', 'yuv420p', '-r', str(fps), main)
# logo tail
lg = Image.new('RGB', (W, Hh), (4, 4, 6)); d = ImageDraw.Draw(lg); f1 = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', int(W * .13)); f2 = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', int(W * .045))
cx, cy = W / 2, Hh * .44; r = W * .11
d.rounded_rectangle([cx - r, cy - r * 1.5, cx + r, cy - r * .1], radius=int(r * .28), fill=(214, 168, 56))
d.polygon([(cx - r * .3, cy - r * 1.2), (cx - r * .3, cy - r * .4), (cx + r * .45, cy - r * .8)], fill=(4, 4, 6))
d.text((cx, cy + r * .75), 'DAGAR', font=f1, fill='white', anchor='mm'); d.text((cx, cy + r * 1.95), 'C L I P S', font=f1, fill=(214, 168, 56), anchor='mm')
d.text((cx, cy + r * 3.0), 'STORIES YOU CAN SEE', font=f2, fill=(150, 150, 150), anchor='mm')
lp = os.path.join(tmp, 'logo.png'); lg.save(lp); logo = os.path.join(tmp, 'logo.mp4')
sh('ffmpeg', '-loglevel', 'error', '-y', '-loop', '1', '-i', lp, '-t', f'{TOTAL - MAINEND:.3f}', '-vf', f"fps={fps},fade=t=in:st=0:d=0.7,fade=t=out:st={TOTAL - MAINEND - 0.6:.2f}:d=0.6", '-c:v', 'libx264', '-crf', '15', '-pix_fmt', 'yuv420p', logo)
# audio: voice + storm bed + rain + thunder + music pad
th = [1.4, 8.6, 15.9, 24.3, 31.1, 44.1]
ain = ['-i', os.path.join(H, film['voice'])]; af = []
ain += ['-f', 'lavfi', '-t', f'{TOTAL}', '-i', 'anoisesrc=c=brown:a=0.6:r=48000']; ain += ['-f', 'lavfi', '-t', f'{TOTAL}', '-i', 'anoisesrc=c=white:a=0.5:r=48000']
for i, t in enumerate(th): ain += ['-f', 'lavfi', '-t', '3', '-i', 'anoisesrc=c=brown:a=0.9:r=48000']
for j, fr in enumerate((110.0, 164.81, 220.0, 261.63)): ain += ['-f', 'lavfi', '-t', f'{TOTAL}', '-i', f'sine=f={fr}:r=48000']
af += ['[1:a]lowpass=f=700,volume=0.9,tremolo=f=0.11:d=0.5[bed]', '[2:a]highpass=f=2500,lowpass=f=9000,volume=0.13[rain]']
tl = []
for i, t in enumerate(th):
    af.append(f"[{3 + i}:a]lowpass=f=220,afade=t=in:d=0.08,afade=t=out:st=0.4:d=2.4,volume=2.2,adelay={int((t + .35) * 1000)}|{int((t + .35) * 1000)}[th{i}]"); tl.append(f'[th{i}]')
m0 = 3 + len(th)
af.append(f"[{m0}:a][{m0 + 1}:a][{m0 + 2}:a][{m0 + 3}:a]amix=inputs=4:normalize=0,lowpass=f=900,tremolo=f=0.18:d=0.6,volume=0.055,afade=t=in:d=3,afade=t=out:st={TOTAL - 3:.1f}:d=3[mus]")
af.append("[0:a]aresample=48000,pan=stereo|c0=c0|c1=c0,apad,volume=1.0[v]")
af.append(f"[v][bed][rain]{''.join(tl)}[mus]amix=inputs={4 + len(th)}:normalize=0:duration=longest,atrim=0:{TOTAL},afade=t=out:st={TOTAL - 1.2:.1f}:d=1.2,loudnorm=I=-14:TP=-1.0:LRA=11[a]")
mixa = os.path.join(tmp, 'mix.m4a'); sh('ffmpeg', '-loglevel', 'error', '-y', *ain, '-filter_complex', ';'.join(af), '-map', '[a]', '-c:a', 'aac', '-b:a', '192k', mixa)
lst2 = os.path.join(tmp, 'fin.txt'); open(lst2, 'w').write(f"file '{main}'\nfile '{logo}'\n"); vid = os.path.join(tmp, 'video.mp4')
sh('ffmpeg', '-loglevel', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst2, '-c', 'copy', vid)
sh('ffmpeg', '-loglevel', 'error', '-y', '-i', vid, '-i', mixa, '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'copy', '-shortest', '-movflags', '+faststart', outp)
print('wrote', outp)
