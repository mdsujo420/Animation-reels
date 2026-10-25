"""Free Bangla TTS: Microsoft Edge voices (edge-tts), gTTS as a safety net.
Each character has its own voice; the emotion changes speed and pitch."""
import asyncio
import os
import subprocess
import time

import numpy as np

SR = 24000
BASE_RATE = int(os.getenv("TTS_RATE", "6"))

# id -> (edge voice, base pitch Hz, fallback edge voice, fallback pitch factor for gTTS)
VOICES = {
    "A": ("bn-BD-NabanitaNeural", 3, "bn-BD-NabanitaNeural", 1.0),
    "B": ("bn-BD-PradeepNeural", -2, "bn-BD-PradeepNeural", 0.80),
    "C": ("bn-IN-TanishaaNeural", -6, "bn-BD-NabanitaNeural", 0.88),
}
# emotion -> (rate %, pitch Hz)
EMO = {
    "neutral": (0, 0), "angry": (10, -4), "surprised": (4, 10), "happy": (8, 6),
    "scared": (14, 12), "sad": (-10, -6), "smug": (-5, -2), "laugh": (10, 8),
}


async def _edge(text, voice, rate, pitch, path):
    import edge_tts
    await edge_tts.Communicate(text, voice, rate=rate, pitch=pitch).save(path)


def _try_edge(text, voice, rate, pitch, path):
    last = None
    for i in range(3):
        try:
            asyncio.run(_edge(text, voice, rate, pitch, path))
            if os.path.exists(path) and os.path.getsize(path) > 500:
                return True
        except Exception as e:
            last = e
        time.sleep(1.5)
    print("edge-tts failed:", voice, str(last)[:120])
    return False


def _try_gtts(text, path):
    try:
        from gtts import gTTS
        gTTS(text, lang="bn").save(path)
        return os.path.getsize(path) > 500
    except Exception as e:
        print("gTTS failed:", str(e)[:120])
        return False


def _decode(path, factor=1.0):
    af = "aresample=%d" % SR
    if abs(factor - 1.0) > 0.01:
        af += f",asetrate={SR * factor:.0f},aresample={SR},atempo={1 / factor:.4f}"
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-af", af, "-ar", str(SR), "-ac", "1", "-f", "s16le", "-"],
                         check=True, capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.int16)


def _clean(pcm):
    """Trim silence at both ends and even out loudness."""
    x = pcm.astype(np.float64)
    idx = np.where(np.abs(x) > 500)[0]
    if len(idx) == 0:
        return pcm
    a, b = max(0, idx[0] - int(0.03 * SR)), min(len(x), idx[-1] + int(0.06 * SR))
    x = x[a:b]
    peak = np.percentile(np.abs(x), 99) or 1.0
    x = np.clip(x / peak * 21000, -32000, 32000)
    return x.astype(np.int16)


def synth(text, speaker, emotion, path):
    voice, base_pitch, fb_voice, factor = VOICES.get(speaker, VOICES["A"])
    rate_d, pitch_d = EMO.get(emotion, (0, 0))
    rate = f"{BASE_RATE + rate_d:+d}%"
    pitch = f"{base_pitch + pitch_d:+d}Hz"
    if _try_edge(text, voice, rate, pitch, path):
        return _clean(_decode(path))
    if fb_voice != voice and _try_edge(text, fb_voice, rate, f"{pitch_d:+d}Hz", path):
        return _clean(_decode(path))
    if _try_gtts(text, path):
        return _clean(_decode(path, factor))
    raise RuntimeError("all TTS engines failed (edge-tts and gTTS)")
