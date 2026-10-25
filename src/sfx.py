"""Tiny sound-effect synthesizer (no files needed)."""
import numpy as np

SR = 24000


def _t(dur):
    return np.arange(int(SR * dur)) / SR


def _norm(x, peak=0.55):
    m = np.max(np.abs(x)) or 1.0
    return (x / m * peak * 32767).astype(np.int16)


def _sweep(f0, f1, dur, decay):
    t = _t(dur)
    f = f0 * (f1 / f0) ** (t / dur)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-decay * t)


def make(name):
    if name == "pop":
        return _norm(_sweep(300, 1400, 0.12, 18))
    if name == "thud":
        return _norm(_sweep(140, 42, 0.38, 9) + 0.25 * np.random.default_rng(2).standard_normal(int(SR * 0.38)) * np.exp(-40 * _t(0.38)))
    if name == "whoosh":
        t = _t(0.5)
        n = np.random.default_rng(1).standard_normal(len(t))
        k = np.ones(40) / 40
        return _norm(np.convolve(n, k, mode="same") * np.sin(np.pi * t / 0.5) ** 2)
    if name == "ding":
        t = _t(0.7)
        return _norm((np.sin(2 * np.pi * 1320 * t) + 0.4 * np.sin(2 * np.pi * 1980 * t)) * np.exp(-6 * t))
    if name == "boing":
        t = _t(0.55)
        f = 260 + 170 * np.sin(2 * np.pi * 9 * t) * np.exp(-5 * t)
        return _norm(np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-3.5 * t))
    if name == "sad":
        out = []
        for f0, d in ((392, 0.32), (370, 0.32), (349, 0.32), (330, 0.9)):
            t = _t(d)
            vib = 1 + (0.025 * np.sin(2 * np.pi * 6 * t) if d > 0.5 else 0)
            ph = 2 * np.pi * np.cumsum(f0 * vib * (1 - 0.12 * t / d)) / SR
            w = np.sin(ph) + 0.5 * np.sin(2 * ph) + 0.3 * np.sin(3 * ph)
            out.append(w * np.minimum(1, t * 40) * np.exp(-1.6 * t))
        return _norm(np.concatenate(out), 0.45)
    if name == "scratch":
        t = _t(0.4)
        n = np.random.default_rng(3).standard_normal(len(t))
        saw = 2 * ((np.cumsum(2200 * (0.1 ** (t / 0.4))) / SR) % 1) - 1
        return _norm((0.6 * saw + 0.4 * n) * np.exp(-4 * t))
    return np.zeros(0, dtype=np.int16)
