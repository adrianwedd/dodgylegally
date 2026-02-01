"""Tests for BPM-aware looping."""

import numpy as np
import soundfile as sf
from pathlib import Path

import pytest


def _make_click_track(path: Path, bpm: float = 120.0, duration_s: float = 4.0, sr: int = 22050):
    """Generate a click track WAV at the given BPM."""
    n_samples = int(sr * duration_s)
    audio = np.zeros(n_samples)
    interval = int(sr * 60.0 / bpm)
    for i in range(0, n_samples, interval):
        end = min(i + 200, n_samples)
        audio[i:end] = 0.8 * np.exp(-np.linspace(0, 5, end - i))
    sf.write(str(path), audio, sr)
    return path


def _make_sine_wav(path: Path, freq: float = 440.0, duration_s: float = 2.0, sr: int = 22050):
    """Generate a sine wave WAV file."""
    t = np.linspace(0, duration_s, int(sr * duration_s), endpoint=False)
    audio = 0.5 * np.sin(2 * np.pi * freq * t)
    sf.write(str(path), audio, sr)
    return path


def test_beat_duration_ms_calculation():
    """beat_duration_ms returns correct milliseconds per beat."""
    from dodgylegally.looping import beat_duration_ms

    assert beat_duration_ms(120.0) == 500.0  # 60000 / 120 = 500
    assert beat_duration_ms(60.0) == 1000.0
    assert beat_duration_ms(140.0) == pytest.approx(428.57, abs=0.1)


def test_beat_aligned_length_rounds_to_beats():
    """beat_aligned_length returns a duration that's an integer number of beats."""
    from dodgylegally.looping import beat_aligned_length

    # At 120 BPM, one beat = 500ms. Target ~1000ms -> 2 beats = 1000ms
    length = beat_aligned_length(bpm=120.0, target_ms=1000)
    assert length == 1000

    # At 140 BPM, one beat ≈ 428ms. Target ~1000ms -> 2 beats ≈ 857ms
    length = beat_aligned_length(bpm=140.0, target_ms=1000)
    assert length == pytest.approx(857.14, abs=1.0)


def test_beat_aligned_length_at_least_one_beat():
    """beat_aligned_length never returns less than one beat."""
    from dodgylegally.looping import beat_aligned_length

    # At 60 BPM, one beat = 1000ms. Target 200ms -> still 1 beat = 1000ms
    length = beat_aligned_length(bpm=60.0, target_ms=200)
    assert length == 1000.0


def test_find_zero_crossing_near():
    """find_zero_crossing finds a zero crossing near the target sample."""
    from dodgylegally.looping import find_zero_crossing

    # Create array with known zero crossings
    samples = np.array([0.5, 0.3, 0.1, -0.1, -0.3, 0.2, 0.4], dtype=np.float32)

    # Should find the crossing near index 3 (where sign changes)
    idx = find_zero_crossing(samples, target=3, search_range=5)
    assert 2 <= idx <= 3


def test_find_zero_crossing_returns_target_when_none_found():
    """find_zero_crossing returns target when no crossing exists in range."""
    from dodgylegally.looping import find_zero_crossing

    # All positive — no zero crossing
    samples = np.array([0.5, 0.3, 0.6, 0.8, 0.9], dtype=np.float32)
    idx = find_zero_crossing(samples, target=2, search_range=2)
    assert idx == 2


def test_time_stretch_audio():
    """time_stretch changes duration without crashing."""
    from dodgylegally.looping import time_stretch_audio

    sr = 22050
    y = 0.5 * np.sin(2 * np.pi * 440 * np.linspace(0, 1, sr, endpoint=False))

    # Stretch to 150% — should get longer
    stretched = time_stretch_audio(y.astype(np.float32), sr, rate=0.667)
    assert len(stretched) > len(y) * 0.9


def test_make_bpm_loop_creates_file(tmp_path):
    """make_bpm_loop creates a WAV file at the output path."""
    from dodgylegally.looping import make_bpm_loop

    wav = _make_click_track(tmp_path / "clicks.wav", bpm=120, duration_s=4.0)
    out = tmp_path / "loop.wav"

    make_bpm_loop(str(wav), str(out), target_bpm=120.0)
    assert out.exists()


def test_make_bpm_loop_fallback_on_none_bpm(tmp_path):
    """make_bpm_loop falls back to fixed-length when target_bpm is None."""
    from dodgylegally.looping import make_bpm_loop

    wav = _make_sine_wav(tmp_path / "sine.wav", duration_s=2.0)
    out = tmp_path / "loop.wav"

    make_bpm_loop(str(wav), str(out), target_bpm=None)
    assert out.exists()


def test_cli_process_accepts_target_bpm_flag():
    """CLI process subcommand accepts --target-bpm flag."""
    from click.testing import CliRunner
    from dodgylegally.cli import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["process", "--help"])
    assert "--target-bpm" in result.output
