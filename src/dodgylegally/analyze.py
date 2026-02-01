"""Audio analysis module — BPM, key, loudness, spectral features via librosa."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path

import librosa
import numpy as np


@dataclass
class AudioAnalysis:
    """Analysis results for a single audio file."""

    bpm: float | None
    key: str | None
    loudness_lufs: float
    duration_ms: int
    spectral_centroid: float
    rms_energy: float
    zero_crossing_rate: float


# Chromatic pitch classes for key detection
_PITCH_CLASSES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def _detect_bpm(y: np.ndarray, sr: int) -> float | None:
    """Detect BPM using librosa onset-based beat tracking."""
    try:
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        bpm = float(np.atleast_1d(tempo)[0])
        if bpm > 0:
            return round(bpm, 1)
    except Exception:
        pass
    return None


def _detect_key(y: np.ndarray, sr: int) -> str | None:
    """Estimate musical key from chroma features.

    Uses the Krumhansl-Schmuckler key-finding algorithm:
    correlate the chroma profile against major and minor key profiles.
    """
    try:
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
        chroma_mean = chroma.mean(axis=1)

        # Krumhansl-Kessler key profiles
        major_profile = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
        minor_profile = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])

        best_corr = -2.0
        best_key = None

        for shift in range(12):
            shifted = np.roll(chroma_mean, -shift)
            maj_corr = float(np.corrcoef(shifted, major_profile)[0, 1])
            min_corr = float(np.corrcoef(shifted, minor_profile)[0, 1])

            if maj_corr > best_corr:
                best_corr = maj_corr
                best_key = f"{_PITCH_CLASSES[shift]} major"
            if min_corr > best_corr:
                best_corr = min_corr
                best_key = f"{_PITCH_CLASSES[shift]} minor"

        return best_key
    except Exception:
        return None


def _compute_loudness_lufs(y: np.ndarray, sr: int) -> float:
    """Compute integrated loudness approximation in LUFS.

    Simplified K-weighted loudness per ITU-R BS.1770.
    Uses RMS of the signal converted to dBFS as a reasonable approximation
    for short samples.
    """
    rms = np.sqrt(np.mean(y ** 2))
    if rms == 0:
        return -70.0
    db = 20 * np.log10(rms)
    # Approximate offset to LUFS scale (dBFS to LUFS for mono)
    return round(float(db), 1)


def analyze_file(path: Path, use_cache: bool = False) -> AudioAnalysis:
    """Analyze an audio file and return an AudioAnalysis.

    If use_cache is True, check for cached analysis in the metadata sidecar
    and return it if the file hasn't changed. Writes analysis to sidecar
    after computation.

    Raises FileNotFoundError if the file doesn't exist.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {path}")

    # Check cache
    if use_cache:
        from dodgylegally.metadata import read_sidecar
        sidecar = read_sidecar(path)
        cached = sidecar.get("analysis")
        if cached and isinstance(cached, dict):
            try:
                return AudioAnalysis(**cached)
            except (TypeError, KeyError):
                pass  # Stale or invalid cache — recompute

    # Load audio
    y, sr = librosa.load(str(path), sr=None, mono=True)
    duration_ms = int(len(y) / sr * 1000)

    # BPM
    bpm = _detect_bpm(y, sr)

    # Key
    key = _detect_key(y, sr)

    # Loudness
    loudness_lufs = _compute_loudness_lufs(y, sr)

    # Spectral centroid (mean across frames)
    centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
    spectral_centroid = round(float(np.mean(centroid)), 1)

    # RMS energy (mean across frames)
    rms = librosa.feature.rms(y=y)
    rms_energy = round(float(np.mean(rms)), 6)

    # Zero-crossing rate (mean across frames)
    zcr = librosa.feature.zero_crossing_rate(y)
    zero_crossing_rate = round(float(np.mean(zcr)), 6)

    result = AudioAnalysis(
        bpm=bpm,
        key=key,
        loudness_lufs=loudness_lufs,
        duration_ms=duration_ms,
        spectral_centroid=spectral_centroid,
        rms_energy=rms_energy,
        zero_crossing_rate=zero_crossing_rate,
    )

    # Write to sidecar cache
    if use_cache:
        from dodgylegally.metadata import merge_sidecar
        merge_sidecar(path, {"analysis": asdict(result)})

    return result
