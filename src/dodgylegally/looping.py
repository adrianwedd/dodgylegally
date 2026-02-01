"""BPM-aware looping — beat-aligned loop points, time-stretching, zero-crossing snapping."""

from __future__ import annotations

import math

import librosa
import numpy as np
import soundfile as sf
from pydub import AudioSegment, effects


def beat_duration_ms(bpm: float) -> float:
    """Return the duration of one beat in milliseconds."""
    return 60000.0 / bpm


def beat_aligned_length(bpm: float, target_ms: int = 1000) -> float:
    """Return a loop length in ms that's an integer number of beats.

    Always at least one beat long.
    """
    one_beat = beat_duration_ms(bpm)
    n_beats = max(1, round(target_ms / one_beat))
    return round(one_beat * n_beats, 2)


def find_zero_crossing(samples: np.ndarray, target: int, search_range: int = 512) -> int:
    """Find the nearest zero-crossing to the target sample index.

    Returns target if no crossing is found within search_range.
    """
    lo = max(0, target - search_range)
    hi = min(len(samples) - 1, target + search_range)

    region = samples[lo:hi]
    if len(region) < 2:
        return target

    # Find sign changes
    signs = np.sign(region)
    crossings = np.where(np.diff(signs) != 0)[0]

    if len(crossings) == 0:
        return target

    # Find crossing nearest to target
    crossing_indices = crossings + lo
    distances = np.abs(crossing_indices - target)
    return int(crossing_indices[np.argmin(distances)])


def time_stretch_audio(y: np.ndarray, sr: int, rate: float) -> np.ndarray:
    """Time-stretch audio by the given rate.

    rate > 1.0 = faster (shorter), rate < 1.0 = slower (longer).
    """
    return librosa.effects.time_stretch(y, rate=rate)


def make_bpm_loop(input_path: str, output_path: str, target_bpm: float | None = None) -> str:
    """Create a loop aligned to beat boundaries.

    If target_bpm is None, falls back to a fixed 1-second loop with
    cross-fade (original behavior).

    If target_bpm is provided:
    1. Detect source BPM
    2. Calculate beat-aligned loop length
    3. Time-stretch if source BPM differs from target
    4. Snap endpoints to zero crossings
    5. Apply cross-fade and normalize
    """
    y, sr = librosa.load(input_path, sr=None, mono=True)
    duration_ms = int(len(y) / sr * 1000)

    if target_bpm is None or duration_ms < 500:
        # Fallback: fixed-length loop via pydub (original behavior)
        sound = AudioSegment.from_file(input_path, "wav")
        final_length = min(2000, len(sound))
        half = int(final_length / 2)
        fade_length = int(final_length / 4)
        beg = sound[:half]
        end = sound[half:]
        end = end[:fade_length]
        beg = beg.fade_in(duration=fade_length)
        end = end.fade_out(duration=fade_length)
        sound = beg.overlay(end)
        sound = effects.normalize(sound)
        sound.export(output_path, format="wav")
        return output_path

    # Detect source BPM
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    source_bpm = float(np.atleast_1d(tempo)[0])

    if source_bpm <= 0:
        # BPM detection failed — fallback
        return make_bpm_loop(input_path, output_path, target_bpm=None)

    # Time-stretch to target BPM if needed
    if abs(source_bpm - target_bpm) > 1.0:
        rate = source_bpm / target_bpm
        y = time_stretch_audio(y, sr, rate=rate)

    # Calculate beat-aligned loop length
    loop_ms = beat_aligned_length(target_bpm, target_ms=1000)
    loop_samples = int(loop_ms / 1000.0 * sr)

    if loop_samples >= len(y):
        loop_samples = len(y)

    # Snap start and end to zero crossings
    start = find_zero_crossing(y, 0, search_range=256)
    end = find_zero_crossing(y, start + loop_samples, search_range=256)
    end = min(end, len(y))

    loop_audio = y[start:end]

    if len(loop_audio) == 0:
        return make_bpm_loop(input_path, output_path, target_bpm=None)

    # Cross-fade for seamless looping
    fade_samples = min(len(loop_audio) // 4, int(sr * 0.05))
    if fade_samples > 1:
        fade_in = np.linspace(0, 1, fade_samples)
        fade_out = np.linspace(1, 0, fade_samples)
        loop_audio[:fade_samples] *= fade_in
        loop_audio[-fade_samples:] *= fade_out

    # Normalize
    peak = np.max(np.abs(loop_audio))
    if peak > 0:
        loop_audio = loop_audio / peak * 0.9

    sf.write(output_path, loop_audio, sr)
    return output_path
