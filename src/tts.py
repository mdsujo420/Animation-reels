"""Free Bangla text-to-speech via Microsoft Edge voices (edge-tts)."""
import asyncio
import os
import subprocess
import numpy as np
import edge_tts

VOICE = os.getenv("TTS_VOICE", "bn-BD-NabanitaNeural")   # female. male: bn-BD-PradeepNeural
RATE = os.getenv("TTS_RATE", "+8%")
PITCH = os.getenv("TTS_PITCH", "+4Hz")
SR = 24000


async def _save(text, path):
    await edge_tts.Communicate(text, VOICE, rate=RATE, pitch=PITCH).save(path)


def synth(text, mp3_path):
    asyncio.run(_save(text, mp3_path))
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", mp3_path, "-ar", str(SR), "-ac", "1", "-f", "s16le", "-"],
        check=True, capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.int16)
