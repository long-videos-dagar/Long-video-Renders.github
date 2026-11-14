"""Kokoro TTS for the TALEVENTURE trailer: one wav per line and voice (24 kHz), plus timing.json with each clip's speech length."""
import json, os, sys, numpy as np, soundfile as sf
from kokoro import KPipeline
cfg = json.load(open(os.path.join(os.path.dirname(__file__), 'lines.json')))
out = os.path.join(os.path.dirname(__file__), 'audio'); os.makedirs(out, exist_ok=True)
PIPES = {}
info = {}
for v in [cfg['voice']] + cfg.get('alt_voices', []):
    pipe = PIPES.setdefault(v[0], KPipeline(lang_code=v[0]))
    for ln in cfg['lines']:
        wav = np.concatenate([np.asarray(a, dtype=np.float32) for _, _, a in pipe(ln['text'], voice=v, speed=cfg['speed'])])
        nz = np.where(np.abs(wav) > 0.01)[0]
        wav = wav[max(0, nz[0] - 480): nz[-1] + 2400] if len(nz) else wav       # trim silence, keep 20 ms before / 100 ms after
        sf.write(f'{out}/{v}_{ln["id"]}.wav', wav, 24000)
        info[f'{v}_{ln["id"]}'] = round(len(wav) / 24000, 3)
        print(v, ln['id'], info[f'{v}_{ln["id"]}'], 's', flush=True)
json.dump(info, open(f'{out}/timing.json', 'w'), indent=1)
