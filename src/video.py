"""Frame-by-frame renderer piped straight into ffmpeg."""
import math
import os
import random
import subprocess
import wave
import numpy as np
from PIL import Image, ImageDraw

from . import tts
from .backgrounds import VW, VH, background
from .captions import draw_caption, load_font
from .character import character, OUT_SCALE

FPS = 24
TAIL = 0.35          # seconds of silence after each line
CHAR_Y = 380


def _mouth_levels(pcm, frames):
    spf = tts.SR // FPS
    rms = np.zeros(frames)
    for i in range(frames):
        seg = pcm[i * spf:(i + 1) * spf].astype(np.float64)
        rms[i] = math.sqrt(np.mean(seg ** 2)) if len(seg) else 0.0
    ref = np.percentile(rms[rms > 0], 90) if np.any(rms > 0) else 1.0
    lv = np.clip(np.round(rms / ref * 5), 0, 5).astype(int)
    lv = np.where(lv < 1, 0, lv)
    return lv


def build(script, workdir, out_path):
    os.makedirs(workdir, exist_ok=True)
    font = load_font(66)
    spf = tts.SR // FPS

    scenes = []
    for i, sc in enumerate(script["scenes"]):
        pcm = tts.synth(sc["text"], os.path.join(workdir, f"s{i}.mp3"))
        frames = math.ceil((len(pcm) / tts.SR + TAIL) * FPS)
        pad = np.zeros(frames * spf, dtype=np.int16)
        pad[:len(pcm)] = pcm
        scenes.append((sc, pad, frames))

    audio = np.concatenate([p for _, p, _ in scenes])
    wav_path = os.path.join(workdir, "voice.wav")
    with wave.open(wav_path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(tts.SR)
        w.writeframes(audio.tobytes())

    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{VW}x{VH}",
           "-r", str(FPS), "-i", "-", "-i", wav_path, "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out_path]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    rng = random.Random(7)
    for sc, pcm, frames in scenes:
        levels = _mouth_levels(pcm, frames)
        bg = background(sc["setting"])
        shaky = sc["emotion"] in ("angry", "scared")
        blink_at = rng.randint(30, 60)
        for f in range(frames):
            t = f / FPS
            blink = (f % 72) in (blink_at % 72, (blink_at + 1) % 72)
            char = character(sc["emotion"], int(levels[f]), blink)

            frame = bg.copy().convert("RGBA")
            dy = int(math.sin(t * 2 * math.pi * 1.2) * 7)
            dx = rng.randint(-5, 5) if shaky else 0
            frame.alpha_composite(char, (int((VW - char.width) / 2) + dx, CHAR_Y + dy))
            ImageDraw.Draw(frame)
            draw_caption(ImageDraw.Draw(frame), sc["text"], font)
            img = frame.convert("RGB")

            zoom = 1.0 + 0.07 * (f / max(frames - 1, 1))
            if zoom > 1.001:
                cw, ch = int(VW / zoom), int(VH / zoom)
                x0, y0 = (VW - cw) // 2, (VH - ch) // 2 + 60
                img = img.crop((x0, y0, x0 + cw, y0 + ch)).resize((VW, VH), Image.BILINEAR)
            proc.stdin.write(img.tobytes())

    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError("ffmpeg failed")
    return out_path
