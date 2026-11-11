"""python3 scripts/asr_check.py <lines.json> -> transcribes every rendered line with faster-whisper (small.en) and
reports how intelligible each voice is (word similarity to the script) next to the line's duration."""
import json, os, sys, difflib, re, wave
from faster_whisper import WhisperModel
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
L = json.load(open(sys.argv[1])); m = WhisperModel('small.en', device='cpu', compute_type='int8')
norm = lambda s: re.sub(r'[^a-z0-9 ]', ' ', s.lower()).split()
rep = []
for l in L:
    p = os.path.join(ROOT, l['out'])
    if not os.path.exists(p): rep.append(f"MISSING {l['out']}"); continue
    segs, _ = m.transcribe(p, beam_size=5); txt = ' '.join(s.text for s in segs).strip()
    a, b = norm(l['text']), norm(txt); sim = difflib.SequenceMatcher(None, a, b).ratio()
    w = wave.open(p); dur = w.getnframes() / w.getframerate()
    rep.append(f"{sim:4.2f}  {dur:4.1f}s  {l['voice']:22s} {l['out'].rsplit('/', 1)[-1]:28s} | {txt}")
out = os.path.join(os.path.dirname(os.path.join(ROOT, sys.argv[1])), 'asr_report.txt'); open(out, 'w').write('\n'.join(rep) + '\n'); print('\n'.join(rep))
