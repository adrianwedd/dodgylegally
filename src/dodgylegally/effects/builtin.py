"""Built-in audio effects."""

from __future__ import annotations

import numpy as np
from pydub import AudioSegment


class ReverseEffect:
    """Reverse the audio."""

    @property
    def name(self) -> str:
        return "reverse"

    def apply(self, audio: AudioSegment, params: dict) -> AudioSegment:
        return audio.reverse()


class LowpassEffect:
    """Simple lowpass filter via pydub."""

    @property
    def name(self) -> str:
        return "lowpass"

    def apply(self, audio: AudioSegment, params: dict) -> AudioSegment:
        freq = int(params.get("freq", 3000))
        return audio.low_pass_filter(freq)


class HighpassEffect:
    """Simple highpass filter via pydub."""

    @property
    def name(self) -> str:
        return "highpass"

    def apply(self, audio: AudioSegment, params: dict) -> AudioSegment:
        freq = int(params.get("freq", 300))
        return audio.high_pass_filter(freq)


class BitcrushEffect:
    """Reduce bit depth for lo-fi character."""

    @property
    def name(self) -> str:
        return "bitcrush"

    def apply(self, audio: AudioSegment, params: dict) -> AudioSegment:
        bits = int(params.get("bits", 8))
        samples = np.array(audio.get_array_of_samples(), dtype=np.float64)

        # Quantize to reduced bit depth
        max_val = 2 ** (bits - 1)
        samples = np.round(samples / (2 ** 15 / max_val)) * (2 ** 15 / max_val)
        samples = np.clip(samples, -32768, 32767).astype(np.int16)

        crushed = audio._spawn(samples.tobytes())
        return crushed


class DistortionEffect:
    """Soft clipping distortion."""

    @property
    def name(self) -> str:
        return "distortion"

    def apply(self, audio: AudioSegment, params: dict) -> AudioSegment:
        gain_db = float(params.get("gain", 12))

        # Apply gain then clip
        boosted = audio.apply_gain(gain_db)
        samples = np.array(boosted.get_array_of_samples(), dtype=np.float64)

        # Soft clip using tanh
        samples = np.tanh(samples / 32768.0) * 32768.0
        samples = np.clip(samples, -32768, 32767).astype(np.int16)

        return audio._spawn(samples.tobytes())


class StutterEffect:
    """Repeat micro-segments for glitch effects."""

    @property
    def name(self) -> str:
        return "stutter"

    def apply(self, audio: AudioSegment, params: dict) -> AudioSegment:
        slice_ms = int(params.get("slice_ms", 100))
        repeats = int(params.get("repeats", 4))

        pieces = []
        for i in range(0, len(audio), slice_ms):
            chunk = audio[i:i + slice_ms]
            for _ in range(repeats):
                pieces.append(chunk)

        if not pieces:
            return audio

        result = pieces[0]
        for p in pieces[1:]:
            result = result + p
        return result
