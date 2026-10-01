"""Synthesise the 15 s soundtrack (48 kHz stereo WAV), timed to the ad's scene cuts.

Scene cuts: 2.5 (dive into orb), 6.4 (glass wipe), 10.0 (warp), 12.5 (logo).
120 BPM, so one beat = 0.5 s.  Writes audio.wav.
"""
import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve
from scipy.io import wavfile

SR, DUR = 48000, 15.0
N = int(SR * DUR)
rng = np.random.default_rng(7)
dry = np.zeros((2, N)); verb = np.zeros((2, N)); pads = np.zeros((2, N))

def mf(m): return 440.0 * 2 ** ((m - 69) / 12)
def tt(d): return np.arange(int(d * SR)) / SR
def filt(x, kind, f): return sosfilt(butter(2 if kind != "band" else 2, f, kind, fs=SR, output="sos"), x)
def put(bus, sig, t0, gain=1.0, pan=0.0):
    i0 = int(t0 * SR); n = min(len(sig), N - i0)
    if n <= 0 or i0 < 0: return
    l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    bus[0, i0:i0 + n] += sig[:n] * gain * l * 1.414; bus[1, i0:i0 + n] += sig[:n] * gain * r * 1.414
def env(n, a, d_tau):
    t = np.arange(n) / SR; e = np.exp(-t / d_tau); ai = int(a * SR)
    if ai > 0: e[:ai] *= np.linspace(0, 1, ai)
    return e

# ---------------- harmony ----------------
CHORDS = [  # (start, end, bass midi, voicing)
    (0.0, 2.5, 38, [50, 57, 61, 64, 66]),    # Dmaj9
    (2.5, 4.5, 35, [54, 57, 61, 62, 66]),    # Bm9
    (4.5, 6.5, 43, [50, 59, 62, 66, 69]),    # Gmaj9
    (6.5, 8.5, 40, [55, 59, 62, 66, 71]),    # Em9
    (8.5, 10.0, 45, [52, 57, 59, 64, 69]),   # Asus
    (10.0, 11.25, 43, [55, 59, 62, 66, 69]), # Gmaj9 (build)
    (11.25, 12.5, 45, [57, 61, 64, 67, 71]), # A7sus-ish (build)
    (12.5, 15.0, 38, [50, 57, 61, 64, 66, 69, 73]),  # Dmaj9 resolve
]

def saw(f, n, ph):
    t = np.arange(n) / SR
    return 2 * ((f * t + ph) % 1.0) - 1

for k, (a, b, bass, notes) in enumerate(CHORDS):
    d = b - a + 0.6; n = int(d * SR)
    sig = np.zeros(n)
    for m in notes:
        for det in (-0.09, 0.0, 0.08):
            sig += saw(mf(m + det), n, rng.random()) * 0.05
    cut = 900 if k < 5 else (1400 if k < 7 else 2200)
    if k in (5, 6): cut = 900 + 1800 * ((k - 4) / 2)
    sig = filt(sig, "low", cut)
    e = np.ones(n); att = int((0.9 if k in (0, 7) else 0.25) * SR); rel = int(0.6 * SR)
    e[:att] = np.linspace(0, 1, att) ** 1.5; e[-rel:] *= np.linspace(1, 0, rel)
    if k == 7: e *= np.concatenate([np.ones(n - int(1.2 * SR)), np.linspace(1, 0, int(1.2 * SR))])
    put(pads, sig * e, a - (0.0 if k == 0 else 0.15), 0.9, -0.25); put(pads, np.roll(sig, 311) * e, a - (0.0 if k == 0 else 0.15), 0.9, 0.25)
    # soft sub bass under the chord
    bn = int((b - a) * SR); bt = np.arange(bn) / SR
    bs = np.sin(2 * np.pi * mf(bass) * bt) * 0.5 + np.sin(4 * np.pi * mf(bass) * bt) * 0.12
    be = np.minimum(1, bt / 0.05) * np.minimum(1, (b - a - bt) / 0.08)
    if 2.5 <= a < 12.45:   # pulsing 8th-note bass in the beat section
        be *= 0.55 + 0.45 * np.exp(-((bt % 0.25)) / 0.09)
    put(dry, bs * be * (0.0 if a < 2.4 else (0.6 if a >= 12.5 else 1.0)), a, 0.26)

# ---------------- arpeggio (glassy plucks, ping-pong delay) ----------------
arp = np.zeros((2, N))
def pluck(f, d=0.35):
    t = tt(d); return (np.sin(2 * np.pi * f * t) + 0.35 * np.sin(4 * np.pi * f * t) + 0.12 * np.sin(6 * np.pi * f * t + 0.3)) * env(len(t), 0.002, 0.11)
PAT = [0, 2, 4, 1, 3, 4, 2, 0, 1, 3, 4, 2, 3, 1, 4, 2]
step = 0
for a, b, bass, notes in CHORDS[:7]:
    tone = sorted(set([n + 12 for n in notes[1:]]))
    t = a
    dt = 0.25 if a < 2.5 else 0.125
    while t < b - 1e-6 and t < 12.42:
        m = tone[PAT[step % 16] % len(tone)] + (12 if (step // 16) % 2 and a >= 6.4 else 0)
        g = 0.18 if a < 2.5 else (0.22 if a < 10 else 0.26)
        put(arp, pluck(mf(m)), t, g, 0.35 * np.sin(step * 1.3))
        t += dt; step += 1
# ping-pong delay (dotted 8th)
dl = int(0.375 * SR); wet = np.zeros_like(arp); src = arp.copy()
for rep in range(1, 5):
    g = 0.38 ** rep; ch = rep % 2
    wet[ch, dl * rep:] += (src[0, :-dl * rep] + src[1, :-dl * rep]) * 0.5 * g
dry += arp * 1.35 + filt(wet, "low", 3500) * 1.0; verb += arp * 0.6

# ---------------- drums (beat section 2.5 to 12.45) ----------------
def kick():
    t = tt(0.45); f = 45 + 85 * np.exp(-t / 0.035); ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * env(len(t), 0.001, 0.16) + filt(rng.standard_normal(len(t)), "high", 3000) * env(len(t), 0, 0.004) * 0.3
def hat(d=0.05): t = tt(0.12); return filt(rng.standard_normal(len(t)), "high", 7500) * env(len(t), 0, d)
def clap():
    t = tt(0.3); n = filt(rng.standard_normal(len(t)), "band", [900, 2600]); e = np.zeros(len(t))
    for o in (0, 0.011, 0.023): e += env(len(t), 0, 0.012 if o < 0.02 else 0.11) * (np.arange(len(t)) >= int(o * SR))
    return n * e
duck = np.ones(N)
beats = np.arange(2.5, 12.45, 0.5)
for i, bt in enumerate(beats):
    put(dry, kick(), bt, 0.78)
    s = int(bt * SR); m = min(N - s, int(0.45 * SR)); duck[s:s + m] = np.minimum(duck[s:s + m], 1 - 0.55 * np.exp(-np.arange(m) / SR / 0.11))
    put(dry, hat(0.035), bt + 0.25, 0.34, 0.3)
    put(dry, hat(0.015), bt + 0.125, 0.14, -0.3); put(dry, hat(0.015), bt + 0.375, 0.14, -0.3)
    if i % 2 == 1: put(dry, clap(), bt, 0.32); put(verb, clap(), bt, 0.25)
# snare roll building into the logo drop
t = 11.3; gap = 0.125
while t < 12.42:
    g = 0.08 + 0.3 * (t - 11.3) / 1.1
    put(dry, clap(), t, g, 0.2 * np.sin(t * 9)); t += gap; gap = max(0.045, gap * 0.9)

# ---------------- effects ----------------
def noise(d): return rng.standard_normal(int(d * SR))
def whoosh(t0, d, peak, lo=500, hi=6000, pan0=-0.8, pan1=0.8, g=0.5):
    n = int(d * SR); x = noise(d); a = filt(x, "band", [lo, lo * 3]); b = filt(x, "band", [hi / 3, hi])
    t = np.arange(n) / n; mix = np.clip((t - 0.1) / max(peak, 1e-3), 0, 1)
    e = np.where(t < peak, (t / peak) ** 2, np.exp(-(t - peak) / 0.18))
    sig = (a * (1 - mix) + b * mix) * e
    for ch, sgn in ((0, -1), (1, 1)):
        pan = pan0 + (pan1 - pan0) * t; gain = np.sqrt(np.clip(0.5 + 0.5 * sgn * pan, 0, 1))
        i0 = int(t0 * SR); m = min(n, N - i0); dry[ch, i0:i0 + m] += sig[:m] * gain[:m] * g; verb[ch, i0:i0 + m] += sig[:m] * gain[:m] * g * 0.6
def impact(t0, g=1.0):
    t = tt(2.2); f = 34 + 40 * np.exp(-t / 0.08)
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(len(t), 0.002, 0.65)
    hit = filt(noise(2.2), "low", 2500) * env(len(t), 0, 0.09) * 0.5
    put(dry, boom * 0.75 + hit, t0, 0.9 * g); put(verb, hit, t0, 0.8 * g)
def bell(f, t0, g=0.2, pan=0.0, d=2.0):
    t = tt(d); I = 2.2 * np.exp(-t / 0.25)
    s = np.sin(2 * np.pi * f * t + I * np.sin(2 * np.pi * f * 3.5 * t)) * env(len(t), 0.001, 0.55)
    put(dry, s, t0, g, pan); put(verb, s, t0, g * 0.9, pan)
def tink(f, t0, g=0.12, pan=0.0):
    t = tt(0.4); s = (np.sin(2 * np.pi * f * t) + 0.4 * np.sin(2 * np.pi * f * 2.76 * t)) * env(len(t), 0.0005, 0.07)
    put(dry, s, t0, g, pan); put(verb, s, t0, g * 0.8, pan)
def riser(t0, t1, f0, f1, g):
    n = int((t1 - t0) * SR); t = np.arange(n) / n
    f = f0 * (f1 / f0) ** t; ph = 2 * np.pi * np.cumsum(f * (1 + 0.006 * np.sin(2 * np.pi * 6 * t * (t1 - t0)))) / SR
    tone = (np.sin(ph) + 0.3 * np.sin(2 * ph)) * t ** 2
    nz = filt(noise(t1 - t0), "high", 1800) * t ** 2.5 * 0.6
    put(dry, (tone * 0.5 + nz), t0, g); put(verb, (tone * 0.5 + nz), t0, g * 0.6)

# scene 1: shimmer, title chimes, chips
for i, (tc, m) in enumerate([(0.35, 81), (0.8, 85), (1.15, 88), (1.5, 90)]):
    bell(mf(m), tc, 0.07, (-0.6, 0.6, -0.3, 0.3)[i], 1.6)
riser(1.3, 2.5, 220, 1400, 0.16); whoosh(1.7, 0.9, 0.85, pan0=0, pan1=0, g=0.45)
impact(2.5, 0.85); bell(mf(86), 2.5, 0.12, 0, 2.5)
# scene 2: typing ticks, explode whoosh, callout blips, segment click
for i in range(5): tink(3800 + 250 * i, 2.95 + 0.11 * i, 0.07, -0.2)
whoosh(3.45, 0.9, 0.45, lo=300, hi=5000, pan0=-0.5, pan1=0.5, g=0.35)
for i, tb in enumerate([3.95, 4.05, 4.15]): tink(mf(88 + 3 * i), tb, 0.08, 0.5)
tink(2600, 5.6, 0.07, 0.1)
# glass wipe 6.1-6.62
whoosh(5.75, 1.15, 0.65, lo=400, hi=9000, pan0=-0.9, pan1=0.9, g=0.6); bell(mf(83), 6.45, 0.09, 0.4, 1.8)
# scene 3: HUD data blips + scan sweep
for k, tb in enumerate(np.arange(6.75, 9.9, 0.125)):
    if rng.random() < 0.38:
        f = 1600 + 1600 * rng.integers(0, 4); t = tt(0.05)
        put(dry, np.sign(np.sin(2 * np.pi * f * t)) * env(len(t), 0, 0.012) * 0.5, tb, 0.05, rng.uniform(-0.7, 0.7))
whoosh(7.2, 1.6, 0.5, lo=200, hi=3000, pan0=-0.9, pan1=0.9, g=0.18)
riser(9.2, 10.0, 300, 2400, 0.16); whoosh(9.4, 0.7, 0.85, pan0=0, pan1=0, g=0.45)
impact(10.0, 0.8)
# scene 4: warp riser + card pass-bys
riser(10.0, 12.45, 120, 3200, 0.28)
for i, tb in enumerate(np.arange(10.3, 12.3, 0.38)):
    whoosh(tb, 0.35, 0.6, lo=600, hi=7000, pan0=(1 if i % 2 else -1) * 0.2, pan1=(1 if i % 2 else -1) * 0.95, g=0.16)
# scene 5: drop, logo chimes, letter tinks, CTA
impact(12.5, 1.1)
for i, m in enumerate([74, 78, 81, 85, 90]): bell(mf(m + 12), 12.5 + 0.06 * i, 0.06, -0.4 + 0.2 * i, 2.4)
bell(mf(93), 13.55, 0.15, 0, 2.2); bell(mf(86), 13.57, 0.1, 0.2, 2.2)
for i in range(8): tink(mf(86 + [0, 2, 4, 7, 9, 12, 14, 16][i]), 13.65 + 0.06 * i, 0.06, -0.6 + 0.17 * i)
bell(mf(81), 13.95, 0.08, 0, 1.6)

# ---------------- mix ----------------
pads *= np.where((np.arange(N) / SR > 2.45) & (np.arange(N) / SR < 12.45), duck, 1.0)
dry += pads * 0.8; verb += pads * 0.45
ir_t = np.arange(int(2.4 * SR)) / SR
ir = np.stack([rng.standard_normal(len(ir_t)) * np.exp(-ir_t / 0.55) for _ in range(2)])
ir = np.stack([filt(ch, "low", 6000) for ch in ir]); ir /= np.abs(ir).sum(axis=1, keepdims=True) ** 0.5 * 30
rev = np.stack([fftconvolve(verb[c], ir[c])[:N] for c in range(2)])
mix = dry + rev * 0.9
mix = filt(mix, "high", 28)
fade = np.ones(N); fl = int(0.5 * SR); fade[-fl:] = np.linspace(1, 0, fl) ** 1.5
mix *= fade; mix[:, :int(0.02 * SR)] *= np.linspace(0, 1, int(0.02 * SR))
mix /= np.abs(mix).max(); mix = np.tanh(mix * 1.6) / np.tanh(1.6)
mix *= 10 ** (-1 / 20) / np.abs(mix).max()
wavfile.write("audio.wav", SR, (mix.T * 32767).astype(np.int16))
print("audio.wav written,", f"{DUR}s", "rms", round(float(np.sqrt((mix ** 2).mean())), 3))
