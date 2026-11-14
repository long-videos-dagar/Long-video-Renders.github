"""Sound for the TALEVENTURE trailer: narrator (Kokoro bm_george) + Kevin / teacher lines from the film,
a synthesised trailer score (drone, ticking clock, braams, riser, hopeful pads) and sound effects.
Music sits about 12 dB under the voice while someone speaks and comes up in the gaps.
usage: python3 promo/audio.py out.wav"""
import os, sys, json
import numpy as np, soundfile as sf
from scipy.signal import lfilter, butter, sosfilt, resample_poly

HERE = os.path.dirname(os.path.abspath(__file__)); EVO = os.path.join(HERE, '..', 'blender', 'evo', 'voice')
SR = 48000; END = 32.5; N = int(END * SR); rng = np.random.default_rng(11)
voice, music, sfx = np.zeros(N), np.zeros(N), np.zeros(N)


def load(p, cut=None):
    a, sr = sf.read(p); a = a if a.ndim == 1 else a.mean(1)
    if cut: a = a[:int(cut * sr)]
    return resample_poly(a, SR, sr)


def add(dst, sig, t, g=1.0):
    i = int(t * SR); j = min(len(dst), i + len(sig))
    if 0 <= i < len(dst) and j > i: dst[i:j] += g * sig[:j - i]


def tt(d): return np.arange(int(d * SR)) / SR
def lp(x, fc, o=2): return sosfilt(butter(o, min(fc, SR / 2.2), 'low', fs=SR, output='sos'), x)
def hp(x, fc, o=2): return sosfilt(butter(o, fc, 'high', fs=SR, output='sos'), x)
def bp(x, a, b, o=2): return sosfilt(butter(o, [a, b], 'band', fs=SR, output='sos'), x)
def adsr(n, a=.01, r=.3):
    x = np.arange(n) / SR; d = n / SR
    return np.minimum(1, x / max(a, 1e-4)) * np.clip((d - x) / max(r, 1e-4), 0, 1)
def saw(f, x, det=0.0): return 2 * ((f * (1 + det) * x) % 1) - 1
def sweep_lp(x, f0, f1):
    """time-varying low-pass by block processing"""
    out = np.zeros_like(x); B = 2048; zi = None
    for k in range(0, len(x), B):
        fc = f0 + (f1 - f0) * (k / max(1, len(x) - 1))
        b, a = butter(2, min(fc, SR / 2.3) / (SR / 2))
        if zi is None or len(zi) != 2: zi = np.zeros(2)
        out[k:k + B], zi = lfilter(b, a, x[k:k + B], zi=zi)
    return out


# ---------------------------------------------------------------- voice
VO = [('n1', .75), ('n2', 3.55), ('n3', 5.95), ('n4', 8.75), ('n5', 10.1), ('n6', 12.1), ('n7', 15.0), ('n8', 18.75), ('n9', 26.4), ('n10', 29.8)]
for k, t in VO: add(voice, load(f'{HERE}/audio/bm_george_{k}.wav'), t)
add(voice, load(f'{EVO}/L001.wav'), 21.8)                    # Kevin: Sir, does that mean humans came from dinosaurs?
l2 = load(f'{EVO}/L002.wav')                                 # teacher: "No, Kevin." (first phrase only)
env_ = np.convolve(np.abs(l2), np.ones(1200) / 1200, 'same'); thr = .04 * env_.max()
on = np.where(env_ > thr)[0]; st = on[0]; gap = None
for i in range(st + int(.45 * SR), len(env_) - int(.12 * SR)):
    if env_[i:i + int(.12 * SR)].max() < thr: gap = i; break
l2 = l2[max(0, st - 600):(gap or st + int(1.1 * SR)) + 1200]; l2[-1200:] *= np.linspace(1, 0, 1200)
add(voice, l2, 24.75)

# ---------------------------------------------------------------- score
def braam(t, root=55.0, dur=3.2, amp=1.0, bright=1800):
    x = tt(dur); s = sum(saw(root * m, x, d) for m in (1, 1.5, 2) for d in (-.004, 0, .005)) / 9
    s = np.tanh(2.5 * s); e = np.exp(-x * 1.1) * adsr(len(x), .015, .6)
    f = sweep_lp(s, bright, 160)
    sub = np.sin(2 * np.pi * root / 2 * x) * np.exp(-x * 1.5)
    add(music, amp * (f * e + .7 * sub * adsr(len(x), .01, .4)), t)


def drone(t0, t1, root=55.0, amp=.35, open_=(300, 1400)):
    x = tt(t1 - t0); s = (saw(root, x, -.003) + saw(root, x, .004) + .6 * saw(root * 2, x, .002)) / 2.6
    s = sweep_lp(s, *open_); g = adsr(len(x), 1.2, .4) * (.6 + .4 * x / (t1 - t0))
    add(music, amp * s * g, t0)


def clock(t0, t1, p0=.55, p1=.18, amp=.35):
    t = t0
    while t < t1:
        u = (t - t0) / (t1 - t0); n = int(.03 * SR); x = np.arange(n) / SR
        k = hp(rng.standard_normal(n), 2500) * np.exp(-x * 160) + .5 * np.sin(2 * np.pi * 1800 * x) * np.exp(-x * 90)
        add(music, amp * (.5 + .5 * u) * k, t)
        nn = int(.18 * SR); xx = np.arange(nn) / SR      # soft pulse kick under the tick
        add(music, amp * .9 * np.sin(2 * np.pi * (48 + 60 * np.exp(-xx * 30)) * xx) * np.exp(-xx * 14), t)
        t += p0 + (p1 - p0) * u ** 1.4


def riser(t0, t1, amp=.5):
    x = tt(t1 - t0); u = x / (t1 - t0)
    nz = sweep_lp(rng.standard_normal(len(x)), 300, 9000) * u ** 2
    tone = np.sin(2 * np.pi * np.cumsum(220 + 1100 * u ** 2) / SR) * u ** 2 * .35
    add(music, amp * (nz + tone), t0)


def pad(t, notes, dur, amp=.16):
    x = tt(dur); s = sum(saw(f, x, d) for f in notes for d in (-.003, .003)) / (2 * len(notes))
    s = lp(s, 1500); add(music, amp * s * adsr(len(x), .25, .5), t)


def pluck(t, f, amp=.12):
    x = tt(.7); s = np.sin(2 * np.pi * f * x) + .4 * np.sin(4 * np.pi * f * x)
    add(music, amp * s * np.exp(-x * 6) * adsr(len(x), .003, .1), t)


def hz(n): return 440 * 2 ** ((n - 69) / 12)


drone(.4, 17.85, 55, .30, (250, 1600))
clock(.6, 16.25, .6, .16, .28)
braam(.55, 55, 3.5, .8, 1200); braam(3.55, 55, 3.0, .9, 1700)
pad(8.7, [hz(57), hz(64), hz(69), hz(73)], 1.6, .18)          # "Life." - first major colour
braam(13.7, 49, 2.6, .9, 1500); riser(14.9, 16.3, .45); braam(16.3, 41.2, 4.0, 1.2, 2400)
for i, ch in enumerate(([57, 61, 64], [54, 57, 61], [50, 54, 57], [52, 56, 59])):   # A  F#m  D  E  (hope)
    pad(18.6 + i * .76, [hz(n) for n in ch], .95, .16)
    for j, n in enumerate(ch + [ch[0] + 12]): pluck(18.6 + i * .76 + j * .19, hz(n + 12), .07)
braam(26.0, 55, 3.4, .95, 1600); pad(26.0, [hz(45), hz(52), hz(57), hz(61)], 3.3, .16)
braam(29.5, 55, 3.0, .8, 2200); pad(29.5, [hz(50), hz(57), hz(62), hz(66)], 2.9, .15)
x = tt(.9); add(music, .18 * (np.sin(2 * np.pi * hz(81) * x) + .4 * np.sin(2 * np.pi * hz(88) * x)) * np.exp(-x * 3), 31.6)   # final glint

# ---------------------------------------------------------------- sound effects
def noise(d): return rng.standard_normal(int(d * SR))
def boom(t, amp=1.0, dur=2.5, f=40):
    x = tt(dur); add(sfx, amp * (np.sin(2 * np.pi * f * x * (1 - .35 * x / dur)) * np.exp(-x * 2.4) + 1.5 * lp(noise(dur), 180) * np.exp(-x * 1.6)), t)
def whoosh(t, dur=.5, amp=.4):
    x = tt(dur); u = x / dur; add(sfx, amp * sweep_lp(noise(dur), 400, 5000) * np.sin(np.pi * u) ** 2, t)
def rumble(t0, t1, amp=.3): x = tt(t1 - t0); add(sfx, amp * lp(noise(t1 - t0), 120) * 3 * adsr(len(x), .4, .5), t0)
def splash(t, amp=.6): x = tt(1.2); add(sfx, amp * bp(noise(1.2), 300, 4000) * np.exp(-x * 3.5) * adsr(len(x), .02, .2), t)
def bubbles(t0, t1, amp=.1):
    for t in np.arange(t0, t1, .12):
        t += rng.uniform(0, .1); x = tt(.06); f = rng.uniform(500, 1400)
        add(sfx, amp * np.sin(2 * np.pi * f * (1 + 6 * x) * x) * np.exp(-x * 60), t)
def roar(t, dur=1.4, amp=.8, f0=75):
    x = tt(dur); shape = np.sin(np.pi * np.minimum(1, x / dur)) ** .5
    f = f0 * (1 + .35 * np.sin(np.pi * x / dur)) * (1 + .08 * lp(noise(dur), 30) * 8)
    ph = 2 * np.pi * np.cumsum(f) / SR; tone = np.tanh(3 * (np.sin(ph) + .5 * np.sin(2 * ph) + .3 * np.sin(3.1 * ph)))
    add(sfx, amp * shape * (.6 * tone * (1 + .4 * np.sin(2 * np.pi * 24 * x)) + .9 * bp(noise(dur), 200, 2500)), t)
def cricket(t, n=3, amp=.06):
    for k in range(n):
        x = tt(.09); add(sfx, amp * np.sin(2 * np.pi * 4300 * x) * (.5 + .5 * np.sign(np.sin(2 * np.pi * 40 * x))) * np.sin(np.pi * x / .09), t + k * .35)
def thud(t, amp=.5, f=60): x = tt(.5); add(sfx, amp * (np.sin(2 * np.pi * f * x) * np.exp(-x * 9) + lp(noise(.5), 300) * np.exp(-x * 25)), t)

rumble(.55, 5.2, .35); boom(3.75, .6); boom(4.5, .5, 2.0, 46); whoosh(3.35, .5, .35)
splash(5.15, .6); bubbles(5.8, 8.5, .08)
for tw in (5.75, 9.95, 11.95, 21.65): whoosh(tw - .1, .55, .3)        # the line wipes
whoosh(8.45, .35, .25); thud(12.6, .4, 45); thud(13.1, .45, 42); roar(13.75, 1.3, .8)
whoosh(14.95, 1.3, .35); boom(16.3, 1.0, 3.2, 34); rumble(16.3, 17.85, .35)
thud(19.86, .2, 90)                                                     # cut to the cave
cricket(25.45, 3, .05)
x = tt(4.0); add(sfx, .012 * lp(noise(4.0), 500) * adsr(len(x), .2, .2), 21.65)    # classroom room tone
whoosh(25.85, .7, .3); whoosh(29.35, .6, .25)


# ---------------------------------------------------------------- mix: music ~12 dB under the voice while it speaks
def grms(a):
    m = np.abs(a).max() + 1e-12; g = a[np.abs(a) > .02 * m]; return np.sqrt(np.mean(g ** 2)) if len(g) else 1e-9
vr = grms(voice)
act = np.convolve((np.abs(voice) > .02 * np.abs(voice).max()).astype(float), np.ones(int(.25 * SR)) / int(.25 * SR), 'same')
act = np.clip(act * 3, 0, 1); act = lp(act, 6)
duck = 1 - .55 * act                                            # -7 dB extra under speech
bed = music * duck + sfx * (1 - .35 * act)
bed *= (.25 * vr) / grms(bed)                                  # whole bed at about -12 dB vs the voice (gated RMS)
mix = voice + bed
mix = np.tanh(mix / .9) * .9
out = np.stack([mix, mix], 1)
sf.write(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'mix.wav'), out, SR, subtype='PCM_16')
print('voice rms %.3f  bed vs voice %.1f dB  peak %.2f' % (vr, 20 * np.log10(grms(bed) / vr), np.abs(mix).max()))
