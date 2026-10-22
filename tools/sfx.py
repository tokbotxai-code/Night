"""Procedural horror sound effects (numpy only, no external samples, no licensing).

Every function returns a mono float32 array at SR, roughly peak-normalized to 1.0.
Mixing levels are decided by the caller.
"""
import numpy as np

SR = 44100
_rng = np.random.default_rng(1312)


def _t(dur):
    return np.arange(int(dur * SR)) / SR


def _norm(x, peak=1.0):
    m = np.max(np.abs(x)) or 1.0
    return (x / m * peak).astype(np.float32)


def fft_filter(x, lo=None, hi=None):
    """Brick-ish band filter in the frequency domain with soft edges."""
    n = len(x)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1 / SR)
    g = np.ones_like(f)
    if hi:
        g *= 1 / (1 + (f / hi) ** 4)
    if lo:
        g *= 1 / (1 + (lo / np.maximum(f, 1e-3)) ** 4)
    return np.fft.irfft(X * g, n).astype(np.float32)


def reverb(x, seconds=1.6, wet=0.35, damp=3500):
    """Convolution reverb with a synthetic exponentially decaying noise IR."""
    n = int(seconds * SR)
    ir = _rng.standard_normal(n) * np.exp(-6.0 * _t(seconds) / seconds)
    ir = fft_filter(ir, hi=damp)
    ir /= np.sqrt(np.sum(ir ** 2)) + 1e-9
    size = len(x) + n
    nfft = 1 << (size - 1).bit_length()
    y = np.fft.irfft(np.fft.rfft(x, nfft) * np.fft.rfft(ir, nfft), nfft)[:size]
    dry = np.concatenate([x, np.zeros(n, dtype=np.float32)])
    y = y / (np.max(np.abs(y)) + 1e-9) * np.max(np.abs(x))
    return ((1 - wet) * dry + wet * y).astype(np.float32)


def fade(x, fin=0.01, fout=0.05):
    x = x.copy()
    a, b = int(fin * SR), int(fout * SR)
    if a:
        x[:a] *= np.linspace(0, 1, a)
    if b:
        x[-b:] *= np.linspace(1, 0, b)
    return x


# ---------------------------------------------------------------- effects

def vibrate():
    """Two phone buzzes, like a phone vibrating on a couch cushion."""
    out = []
    for _ in range(2):
        t = _t(0.38)
        buzz = np.sign(np.sin(2 * np.pi * 172 * t)) * 0.6 + np.sin(2 * np.pi * 344 * t) * 0.4
        buzz *= 0.75 + 0.25 * np.sin(2 * np.pi * 31 * t)
        buzz = fft_filter(buzz, lo=80, hi=1400)
        out += [fade(buzz, 0.015, 0.03), np.zeros(int(0.16 * SR))]
    return _norm(np.concatenate(out))


def hit(seconds=2.2):
    """Low cinematic boom: pitch-dropping sine + noise transient + tail."""
    t = _t(seconds)
    freq = 38 + 70 * np.exp(-t * 9)
    phase = 2 * np.pi * np.cumsum(freq) / SR
    body = np.sin(phase) * np.exp(-t * 2.2)
    trans = fft_filter(_rng.standard_normal(len(t)), hi=900) * np.exp(-t * 25) * 0.6
    x = np.tanh((body + trans) * 2.2)
    return _norm(reverb(x, 2.0, 0.3, 1200)[: int((seconds + 1) * SR)])


def knock():
    t = _t(0.25)
    thud = (np.sin(2 * np.pi * 95 * t) + 0.6 * np.sin(2 * np.pi * 210 * t)) * np.exp(-t * 32)
    crack = fft_filter(_rng.standard_normal(len(t)), lo=300, hi=3000) * np.exp(-t * 90) * 0.7
    return thud + crack


def knock3(spacing=0.85):
    """Three slow knocks on a wooden door, roomy."""
    n = int((spacing * 2 + 0.3) * SR)
    x = np.zeros(n, dtype=np.float32)
    for i in range(3):
        k = knock() * (1.0 - 0.08 * i)
        s = int(i * spacing * SR)
        x[s:s + len(k)] += k
    return _norm(reverb(x, 1.8, 0.4, 2500))


def tv_static(seconds):
    """Quiet TV static hiss with slow wobble."""
    t = _t(seconds)
    n = fft_filter(_rng.standard_normal(len(t)), lo=1500, hi=9000)
    n *= 0.8 + 0.2 * np.sin(2 * np.pi * 0.7 * t + 1.3)
    hum = 0.15 * np.sin(2 * np.pi * 60 * t)
    return _norm(fade(n + hum, 0.3, 0.2))


def room_tone(seconds):
    """Brown-ish noise bed so silence never feels digital."""
    w = _rng.standard_normal(int(seconds * SR))
    b = np.cumsum(w)
    b -= np.convolve(b, np.ones(4410) / 4410, mode="same")
    return _norm(fft_filter(b, lo=30, hi=400))


def drone(seconds):
    """Dissonant low drone that swells toward the end."""
    t = _t(seconds)
    x = np.zeros_like(t)
    for f, a in ((55, 1.0), (58.3, 0.8), (82.4, 0.5), (110.6, 0.3), (164.8, 0.15)):
        x += a * np.sin(2 * np.pi * f * t + _rng.uniform(0, 6.28))
    x += 0.3 * fft_filter(_rng.standard_normal(len(t)), lo=60, hi=500)
    env = (t / seconds) ** 1.6 * 0.85 + 0.15
    return _norm(fade(np.tanh(x * 0.7) * env, 0.8, 0.01))


def riser(seconds):
    """Rising tension: upward-sweeping filtered noise + detuned tones."""
    t = _t(seconds)
    f = 80 + 300 * (t / seconds) ** 2
    ph = 2 * np.pi * np.cumsum(f) / SR
    tone = np.sin(ph) + 0.6 * np.sin(ph * 1.059) + 0.3 * np.sin(ph * 1.5)
    noise = fft_filter(_rng.standard_normal(len(t)), lo=400, hi=6000) * 0.5
    env = (t / seconds) ** 2.2
    return _norm(fade((tone * 0.6 + noise) * env, 0.5, 0.01))


def creak(seconds=1.3):
    """Wood/leather creak: grainy stick-slip pulses with wandering pitch."""
    t = _t(seconds)
    rate = 55 + 35 * np.sin(2 * np.pi * 0.6 * t) + 10 * _rng.standard_normal(len(t)).cumsum() / np.sqrt(len(t))
    ph = np.cumsum(rate) / SR
    pulses = (np.mod(ph, 1.0) < 0.08).astype(np.float32)
    pulses *= 0.5 + 0.5 * np.abs(np.sin(2 * np.pi * 1.4 * t))
    x = fft_filter(pulses, lo=150, hi=2500)
    return _norm(reverb(fade(x, 0.08, 0.2), 0.8, 0.25, 3000))


def heartbeat(seconds):
    """Slow muffled heartbeat (lub-dub), ~70 bpm."""
    n = int(seconds * SR)
    x = np.zeros(n, dtype=np.float32)
    beat = 60 / 70
    tt = _t(0.18)
    thump = np.sin(2 * np.pi * 50 * tt) * np.exp(-tt * 28)
    pos = 0.0
    while pos < seconds:
        for off, amp in ((0.0, 1.0), (0.22, 0.65)):
            s = int((pos + off) * SR)
            e = min(n, s + len(thump))
            if s < n:
                x[s:e] += (thump * amp)[: e - s]
        pos += beat
    return _norm(fft_filter(x, hi=200))


EFFECTS = {
    "vibrate": lambda d: vibrate(),
    "hit": lambda d: hit(),
    "knock3": lambda d: knock3(),
    "creak": lambda d: creak(),
    "tv": lambda d: tv_static(d),
    "drone": lambda d: drone(d),
    "riser": lambda d: riser(d),
    "heartbeat": lambda d: heartbeat(d),
}

# default mix gains (linear) relative to narration peak ~0.9
DEFAULT_GAIN = {
    "vibrate": 0.45, "hit": 0.8, "knock3": 0.9, "creak": 0.35,
    "tv": 0.06, "drone": 0.3, "riser": 0.28, "heartbeat": 0.5,
}
