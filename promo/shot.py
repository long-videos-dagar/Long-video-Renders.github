"""python3 promo/shot.py <shot> <chunk_dir> <out.mp4>: join one evo shot's chunks (mixed sizes / overlaps) into one clip."""
import glob, os, re, subprocess, sys, tempfile
sid, d, out = sys.argv[1:4]; tmp = tempfile.mkdtemp()
ps = sorted(glob.glob(f'{d}/chunk_{sid}_[0-9]*.mp4'), key=lambda p: int(re.search(r'_(\d+)\.mp4$', p).group(1)))
keep, end = [], 0
for p in ps:
    a = int(re.search(r'_(\d+)\.mp4$', p).group(1))
    n = int(subprocess.run(['ffprobe', '-v', 'error', '-count_packets', '-select_streams', 'v:0', '-show_entries', 'stream=nb_read_packets', '-of', 'csv=p=0', p],
                           capture_output=True, text=True).stdout.strip() or 0)
    if n <= 0 or a + n - 1 <= end: continue
    if a > end + 1: print('GAP', sid, end + 1, a - 1)
    if a <= end:
        q = f'{tmp}/trim_{a:05d}.mp4'
        subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', p, '-vf', f'trim=start_frame={end - a + 1},setpts=PTS-STARTPTS', '-c:v', 'libx264', '-crf', '14', '-pix_fmt', 'yuv420p', q], check=True); p = q
    keep.append(p); end = a + n - 1
open(f'{tmp}/l.txt', 'w').write(''.join(f"file '{os.path.abspath(p)}'\n" for p in keep))
subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', f'{tmp}/l.txt', '-vf', 'scale=1920:1080,fps=24', '-c:v', 'libx264', '-preset', 'slow',
                '-crf', '16', '-pix_fmt', 'yuv420p', '-an', out], check=True)
print(sid, 'frames', end)
