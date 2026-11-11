"""Offline text-to-speech for the cast (no paid API).

  python3 scripts/tts.py audition               # every candidate voice says the character's test line
  python3 scripts/tts.py lines <lines.json>     # [{"who": "adrian-cross", "text": "...", "out": "audio/dialogue/ep1/a_001.wav"}]

Engines: Kokoro-82M (pip install kokoro soundfile; needs espeak-ng) and Piper (piper-tts).
Models download once from Hugging Face into ~/.cache (cached by the workflow).
"""
import json, os, sys, subprocess, urllib.request, wave
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = json.load(open(os.path.join(ROOT, 'audio/voices/voices.json')))
PIPER_DIR = os.path.expanduser('~/.cache/piper-voices')
_kokoro = {}


def kokoro(voice, text, out, speed=1.0):
    from kokoro import KPipeline
    import numpy as np, soundfile as sf
    lang = voice[0]                                    # a=US English, b=UK English, h=Hindi
    if lang not in _kokoro: _kokoro[lang] = KPipeline(lang_code=lang, repo_id='hexgrad/Kokoro-82M')
    chunks = [a for _, _, a in _kokoro[lang](text, voice=voice, speed=speed)]
    sf.write(out, np.concatenate(chunks), 24000)


def piper_model(name):
    lang, rest = name.split('-', 1); region = lang; who, q = rest.rsplit('-', 1)
    base = f'https://huggingface.co/rhasspy/piper-voices/resolve/main/{lang.split("_")[0]}/{region}/{who}/{q}/{name}'
    os.makedirs(PIPER_DIR, exist_ok=True)
    for ext in ('.onnx', '.onnx.json'):
        f = os.path.join(PIPER_DIR, name + ext)
        if not os.path.exists(f): urllib.request.urlretrieve(base + ext, f)
    return os.path.join(PIPER_DIR, name + '.onnx')


def piper(voice, text, out, speed=1.0):
    m = piper_model(voice)
    r = subprocess.run([sys.executable, '-m', 'piper', '-m', m, '-f', out, '--length-scale', str(round(1 / speed, 3))], input=text.encode(), capture_output=True)
    if r.returncode != 0: raise RuntimeError(r.stderr.decode()[-800:])


def say(spec, text, out, speed=1.0, gap=None):
    eng, voice = spec.split(':', 1)
    os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
    paras = [p.strip() for p in text.split('\n\n') if p.strip()]
    if gap is None or len(paras) < 2:
        (kokoro if eng == 'kokoro' else piper)(voice, text, out, speed)
    else:
        # one paragraph at a time with a real pause between them (better timing for the edit)
        import numpy as np, soundfile as sf
        parts, sr = [], None
        for i, p in enumerate(paras):
            tmp = out + f'.part{i}.wav'
            (kokoro if eng == 'kokoro' else piper)(voice, p, tmp, speed)
            a, sr = sf.read(tmp); os.remove(tmp)
            if a.ndim > 1: a = a.mean(axis=1)
            parts += [a, np.zeros(int(sr * (gap * 1.6 if len(p.split()) <= 3 else gap)))]
        sf.write(out, np.concatenate(parts[:-1]), sr, subtype='PCM_16')
    with wave.open(out) as w: return w.getnframes() / w.getframerate()


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else 'audition'
    report = []
    if mode == 'audition':
        outdir = os.path.join(ROOT, 'audio/voices/samples')
        for who, c in CFG['characters'].items():
            for spec in c['candidates']:
                out = os.path.join(outdir, f'{who}__{spec.replace(":", "_")}.wav')
                try: d = say(spec, c['line'], out, c.get('speed', 1.0)); report.append(f'OK   {who:15s} {spec:32s} {d:5.1f}s'); print(report[-1], flush=True)
                except Exception as e: report.append(f'FAIL {who:15s} {spec:32s} {str(e)[:200]}'); print(report[-1], flush=True)
    else:
        for L in json.load(open(sys.argv[2])):
            c = CFG['characters'].get(L['who'], {})
            d = say(L.get('voice') or c['pick'], L['text'], os.path.join(ROOT, L['out']), L.get('speed', c.get('speed', 1.0)), L.get('gap'))
            print(f'{L["out"]}  {d:.2f}s', flush=True)
    open(os.path.join(ROOT, 'audio/voices/tts_report.txt'), 'w').write('\n'.join(report) + '\n')
    if any(r.startswith('FAIL') for r in report): sys.exit(1)


if __name__ == '__main__':
    main()
