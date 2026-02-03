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


class DelayEffect:
    """Echo/delay with geometric feedback decay.

    Each repeat is attenuated by feedback**i. Output length extends by
    delay_ms * repeats when mix > 0. mix=0 returns dry (original length),
    mix=1.0 returns wet-only with tail.
    """

    @property
    def name(self) -> str:
        return "delay"

    def apply(self, audio: AudioSegment, params: dict) -> AudioSegment:
        delay_ms = int(params.get("delay_ms", 250))
        feedback = float(params.get("feedback", 0.4))
        repeats = int(params.get("repeats", 3))
        mix = float(params.get("mix", 0.5))

        feedback = max(0.0, min(feedback, 0.95))
        repeats = max(0, min(repeats, 20))
        mix = max(0.0, min(mix, 1.0))

        if repeats == 0:
            return audio

        tail_ms = delay_ms * repeats
        wet = AudioSegment.silent(
            duration=len(audio) + tail_ms,
            frame_rate=audio.frame_rate,
        )
        # Ensure matching channels/sample_width
        wet = wet.set_channels(audio.channels).set_sample_width(audio.sample_width)

        for i in range(1, repeats + 1):
            gain = feedback ** i
            if gain < 0.001:
                break
            offset = delay_ms * i
            tap = audio.apply_gain(20 * np.log10(gain)) if gain > 0 else audio
            wet = wet.overlay(tap, position=offset)

        if mix <= 0.0:
            return audio

        if mix >= 1.0:
            return wet

        # Crossfade: attenuate dry by (1-mix), wet by mix
        dry = audio + AudioSegment.silent(
            duration=tail_ms,
            frame_rate=audio.frame_rate,
        ).set_channels(audio.channels).set_sample_width(audio.sample_width)

        dry_gain = 20 * np.log10(1.0 - mix)
        wet_gain = 20 * np.log10(mix)

        return dry.apply_gain(dry_gain).overlay(wet.apply_gain(wet_gain))
