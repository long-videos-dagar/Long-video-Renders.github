"""Train an RVC voice model (Applio, MIT) on your own recordings - built for free Google Colab, resumable.

Put your recording(s) (wav / mp3 / m4a / flac / ogg, any length; wrong takes are fine) in Google Drive folder
MyDrive/TaleVoice/ and run:   python colab_train.py
If Colab disconnects, run it again: it restores the backup from Drive and continues training from the last save.

Options: --drive /content/drive/MyDrive/TaleVoice  --model TaleVoice  --epochs 300  --batch 8  --gpu 0 (use - for CPU)
"""
import argparse, glob, os, shutil, subprocess, sys, time, json, wave

ap = argparse.ArgumentParser()
ap.add_argument('--drive', default='/content/drive/MyDrive/TaleVoice')
ap.add_argument('--model', default='TaleVoice')
ap.add_argument('--epochs', type=int, default=300)
ap.add_argument('--save-every', type=int, default=25)
ap.add_argument('--batch', type=int, default=8)
ap.add_argument('--gpu', default='0')
ap.add_argument('--sr', type=int, default=40000)
ap.add_argument('--root', default='/content')
ap.add_argument('--sync-every', type=int, default=240, help='seconds between backups to Drive')
a = ap.parse_args()

APPLIO_COMMIT = '6d5d9511b7e719b1f613362bc767e841ad72fa72'
APP = os.path.join(a.root, 'Applio'); PY = os.path.join(APP, '.venv', 'bin', 'python')
LOGS = os.path.join(APP, 'logs'); MDIR = os.path.join(LOGS, a.model)
BACK = os.path.join(a.drive, 'backup', a.model); FINAL = os.path.join(a.drive, 'final')
DATA = os.path.join(a.root, 'dataset')
AUDIO_EXT = ('.wav', '.mp3', '.m4a', '.flac', '.ogg', '.aac', '.opus', '.webm', '.mp4')


def say(*x): print('\n>>>', *x, flush=True)


def sh(cmd, cwd=None, check=True):
    print('$', cmd if isinstance(cmd, str) else ' '.join(cmd), flush=True)
    r = subprocess.run(cmd, cwd=cwd, shell=isinstance(cmd, str))
    if check and r.returncode: sys.exit(f'FAILED ({r.returncode}): {cmd}')
    return r.returncode


def core(*args): return sh([PY, 'core.py', *map(str, args)], cwd=APP)


# ---------------------------------------------------------------- 1. install Applio (once per Colab session)
if not os.path.exists(os.path.join(APP, '.ready')):
    say('Installing Applio (5-8 min, only once per session)...')
    if not os.path.isdir(APP):
        sh(['git', 'clone', '-q', 'https://github.com/IAHispano/Applio', APP])
    sh(['git', '-c', 'advice.detachedHead=false', 'checkout', '-q', APPLIO_COMMIT], cwd=APP)
    if not shutil.which('uv') and not os.path.exists(os.path.expanduser('~/.local/bin/uv')):
        sh('curl -LsSf https://astral.sh/uv/install.sh | sh')
    uv = shutil.which('uv') or os.path.expanduser('~/.local/bin/uv')
    if not os.path.exists(PY): sh([uv, 'venv', '-q', '.venv', '--python', '3.12', '--seed'], cwd=APP)
    idx = 'https://download.pytorch.org/whl/cu128' if a.gpu != '-' else 'https://download.pytorch.org/whl/cpu'
    sh([uv, 'pip', 'install', '-q', '-r', 'requirements-engine.txt', '--extra-index-url', idx,
        '--index-strategy', 'unsafe-best-match', '--python', PY], cwd=APP)
    core('prerequisites', '--models', '--pretraineds-hifigan')
    if os.path.exists(os.path.join(APP, 'assets', 'config_template.json')) and not os.path.exists(os.path.join(APP, 'assets', 'config.json')):
        shutil.copy(os.path.join(APP, 'assets', 'config_template.json'), os.path.join(APP, 'assets', 'config.json'))
    open(os.path.join(APP, '.ready'), 'w').write('ok')
else:
    say('Applio already installed')

if a.gpu != '-':
    ok = subprocess.run([PY, '-c', 'import torch,sys; sys.exit(0 if torch.cuda.is_available() else 1)']).returncode == 0
    if not ok:
        sys.exit('\n!!! GPU nahi mila. Colab menu: Runtime > Change runtime type > T4 GPU > Save, phir dubara Run karo.\n')

os.makedirs(a.drive, exist_ok=True); os.makedirs(LOGS, exist_ok=True)


def ckpts(d): return sorted(glob.glob(os.path.join(d, 'G_*.pth')))


# ---------------------------------------------------------------- 2. restore a backup, or prepare the data
restored = False
if os.path.isdir(BACK) and ckpts(BACK) and not ckpts(MDIR):
    say('Pichli training ka backup mila - wahin se continue kar rahe hain')
    sh(['rsync', '-a', BACK + '/', MDIR + '/'])
    restored = True
elif ckpts(MDIR):
    say('Is session mein training pehle se chal chuki hai - continue')
    restored = True

if not restored:
    srcs = [p for p in sorted(glob.glob(os.path.join(a.drive, '*'))) if p.lower().endswith(AUDIO_EXT)]
    if not srcs:
        sys.exit(f'\n!!! {a.drive} mein koi audio file nahi mili. Apni recording Google Drive ke "TaleVoice" folder mein daalo.\n')
    shutil.rmtree(DATA, ignore_errors=True); os.makedirs(DATA)
    tot = 0.0
    for i, p in enumerate(srcs):
        out = os.path.join(DATA, f'rec_{i:02d}.wav')
        # mono 44.1k, rumble cut, gentle denoise. The slicer later drops the silences between takes.
        sh(['ffmpeg', '-loglevel', 'error', '-y', '-i', p, '-vn', '-ac', '1', '-ar', '44100',
            '-af', 'highpass=f=70,afftdn=nr=10:nf=-30', out])
        with wave.open(out) as w: d = w.getnframes() / w.getframerate()
        tot += d; print(f'   {os.path.basename(p)}: {d / 60:.1f} min')
    say(f'Total recording: {tot / 60:.1f} min')
    if tot < 120: print('   (2 min se kam hai - model weak banega. 10+ min best hai.)')
    say('Step 1/3: audio ko chhote tukdon mein kaat rahe hain')
    core('preprocess', '--model-name', a.model, '--dataset-path', DATA, '--sample-rate', a.sr, '--cpu-cores', os.cpu_count() or 2,
         '--cut-preprocess', 'Automatic', '--chunk-len', '3.0', '--overlap-len', '0.3', '--normalization-mode', 'post')
    say('Step 2/3: awaaz ki pitch aur features nikal rahe hain')
    core('extract', '--model-name', a.model, '--f0-method', 'rmvpe', '--sample-rate', a.sr, '--cpu-cores', os.cpu_count() or 2,
         '--gpu', a.gpu, '--embedder-model', 'contentvec', '--include-mutes', '2')
    core('index', '--model-name', a.model, '--index-algorithm', 'Auto')

# ---------------------------------------------------------------- 3. train, backing up to Drive every few minutes
say(f'Step 3/3: training ({a.epochs} epochs). Ye sabse lamba step hai - browser tab khula rakho.')
os.makedirs(BACK, exist_ok=True)
sync = subprocess.Popen(['bash', '-c', f'while true; do sleep {a.sync_every}; rsync -a --delete "{MDIR}/" "{BACK}/" 2>/dev/null; done'])
try:
    core('train', '--model-name', a.model, '--save-every-epoch', a.save_every, '--total-epoch', a.epochs, '--sample-rate', a.sr,
         '--batch-size', a.batch, '--gpu', a.gpu, '--vocoder', 'HiFi-GAN', '--pretrained', '--save-only-latest', '--save-every-weights')
finally:
    sync.terminate()
    sh(['rsync', '-a', '--delete', MDIR + '/', BACK + '/'], check=False)

# ---------------------------------------------------------------- 4. final files
idx = sorted(glob.glob(os.path.join(MDIR, '*.index')), key=os.path.getmtime)
wts = sorted(glob.glob(os.path.join(MDIR, f'{a.model}*.pth')), key=os.path.getmtime)
if not wts or not idx: sys.exit('!!! training ke baad model files nahi mili - log upar dekho')
os.makedirs(FINAL, exist_ok=True)
shutil.copy(wts[-1], os.path.join(FINAL, f'{a.model}.pth')); shutil.copy(idx[-1], os.path.join(FINAL, f'{a.model}.index'))
json.dump({'model': a.model, 'weights_from': os.path.basename(wts[-1]), 'index_from': os.path.basename(idx[-1]),
           'epochs': a.epochs, 'sample_rate': a.sr, 'applio': APPLIO_COMMIT}, open(os.path.join(FINAL, 'info.json'), 'w'), indent=1)
say('DONE! Tumhara voice model Google Drive mein ready hai:')
for f in sorted(os.listdir(FINAL)): print('   TaleVoice/final/' + f, f'({os.path.getsize(os.path.join(FINAL, f)) / 1e6:.0f} MB)')
print('\nAb ye 2 files (TaleVoice.pth aur TaleVoice.index) Claude ko bhej do.')
