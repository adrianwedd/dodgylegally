"""Pitch and time transforms — stretch, shift, key-match via librosa."""

from __future__ import annotations

import librosa
import numpy as np
import soundfile as sf


_PITCH_CLASSES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# Map enharmonic equivalents
_ENHARMONIC = {
    "Db": "C#", "Eb": "D#", "Fb": "E", "Gb": "F#",
    "Ab": "G#", "Bb": "A#", "Cb": "B", "B#": "C",
    "E#": "F",
}


def _normalize_pitch(name: str) -> str:
    """Normalize a pitch name to its canonical sharp-based form."""
    name = name.strip()
    return _ENHARMONIC.get(name, name)


def time_stretch_file(input_path: str, output_path: str, rate: float) -> str:
    """Time-stretch an audio file. rate > 1.0 = faster, rate < 1.0 = slower."""
    y, sr = librosa.load(input_path, sr=None, mono=True)
    stretched = librosa.effects.time_stretch(y, rate=rate)
    sf.write(output_path, stretched, sr)
    return output_path


def pitch_shift_file(input_path: str, output_path: str, semitones: float) -> str:
    """Pitch-shift an audio file by the given number of semitones."""
    y, sr = librosa.load(input_path, sr=None, mono=True)
    shifted = librosa.effects.pitch_shift(y, sr=sr, n_steps=semitones)
    sf.write(output_path, shifted, sr)
    return output_path


def semitones_between(source_pitch: str, target_pitch: str) -> int:
    """Calculate the shortest semitone interval from source to target pitch class.

    Returns a value in [-6, 6] representing the shortest path around
    the chromatic circle.
    """
    src = _normalize_pitch(source_pitch)
    tgt = _normalize_pitch(target_pitch)

    src_idx = _PITCH_CLASSES.index(src)
    tgt_idx = _PITCH_CLASSES.index(tgt)

    diff = (tgt_idx - src_idx) % 12
    if diff > 6:
        diff -= 12
    return diff


def key_match_file(input_path: str, output_path: str, target_key: str) -> str:
    """Pitch-shift a file to match a target key.

    Detects the source key via chroma analysis, then shifts by the
    shortest interval to reach the target key's root.
    """
    from dodgylegally.analyze import analyze_file

    analysis = analyze_file(input_path)

    # Parse target key root
    parts = target_key.strip().split()
    target_root = parts[0]

    if analysis.key is None:
        # Can't detect source key — copy as-is
        y, sr = librosa.load(input_path, sr=None, mono=True)
        sf.write(output_path, y, sr)
        return output_path

    # Parse source key root
    source_parts = analysis.key.split()
    source_root = source_parts[0]

    shift = semitones_between(source_root, target_root)

    if shift == 0:
        y, sr = librosa.load(input_path, sr=None, mono=True)
        sf.write(output_path, y, sr)
    else:
        pitch_shift_file(input_path, output_path, semitones=shift)

    return output_path
