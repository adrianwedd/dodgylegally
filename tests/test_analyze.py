"""Tests for the audio analysis module."""

import json
import numpy as np
import soundfile as sf
from pathlib import Path

import pytest


def _make_sine_wav(path: Path, freq: float = 440.0, duration_s: float = 2.0, sr: int = 22050, amplitude: float = 0.5):
    """Generate a sine wave WAV file at the given frequency."""
    t = np.linspace(0, duration_s, int(sr * duration_s), endpoint=False)
    audio = amplitude * np.sin(2 * np.pi * freq * t)
    sf.write(str(path), audio, sr)
    return path


def _make_click_track(path: Path, bpm: float = 120.0, duration_s: float = 4.0, sr: int = 22050):
    """Generate a click track at the given BPM."""
    n_samples = int(sr * duration_s)
    audio = np.zeros(n_samples)
    interval = int(sr * 60.0 / bpm)
    for i in range(0, n_samples, interval):
        end = min(i + 200, n_samples)
        audio[i:end] = 0.8 * np.exp(-np.linspace(0, 5, end - i))
    sf.write(str(path), audio, sr)
    return path


def _make_noise_wav(path: Path, duration_s: float = 2.0, sr: int = 22050, amplitude: float = 0.3):
    """Generate white noise WAV file."""
    rng = np.random.default_rng(42)
    audio = amplitude * rng.standard_normal(int(sr * duration_s))
    sf.write(str(path), audio.astype(np.float32), sr)
    return path


def test_analyze_returns_dataclass(tmp_path):
    """analyze_file returns an AudioAnalysis with all expected fields."""
    from dodgylegally.analyze import analyze_file, AudioAnalysis

    wav = _make_sine_wav(tmp_path / "sine.wav")
    result = analyze_file(wav)

    assert isinstance(result, AudioAnalysis)
    assert result.duration_ms > 0
    assert result.rms_energy >= 0
    assert result.zero_crossing_rate >= 0
    assert result.spectral_centroid >= 0


def test_analyze_duration_correct(tmp_path):
    """analyze_file reports correct duration."""
    from dodgylegally.analyze import analyze_file

    wav = _make_sine_wav(tmp_path / "sine.wav", duration_s=2.0)
    result = analyze_file(wav)

    assert 1900 < result.duration_ms < 2100


def test_analyze_bpm_detection(tmp_path):
    """analyze_file detects BPM from a click track within reasonable margin."""
    from dodgylegally.analyze import analyze_file

    wav = _make_click_track(tmp_path / "clicks.wav", bpm=120.0, duration_s=8.0)
    result = analyze_file(wav)

    assert result.bpm is not None
    assert 100 < result.bpm < 140, f"Expected ~120 BPM, got {result.bpm}"


def test_analyze_loudness_is_negative(tmp_path):
    """LUFS loudness should be negative for any reasonable signal."""
    from dodgylegally.analyze import analyze_file

    wav = _make_sine_wav(tmp_path / "sine.wav", amplitude=0.5)
    result = analyze_file(wav)

    assert result.loudness_lufs < 0, f"Expected negative LUFS, got {result.loudness_lufs}"


def test_analyze_loud_vs_quiet(tmp_path):
    """A louder signal should have higher RMS energy than a quiet one."""
    from dodgylegally.analyze import analyze_file

    loud = _make_sine_wav(tmp_path / "loud.wav", amplitude=0.8)
    quiet = _make_sine_wav(tmp_path / "quiet.wav", amplitude=0.05)

    loud_result = analyze_file(loud)
    quiet_result = analyze_file(quiet)

    assert loud_result.rms_energy > quiet_result.rms_energy


def test_analyze_noise_higher_zcr_than_sine(tmp_path):
    """White noise should have a higher zero-crossing rate than a sine wave."""
    from dodgylegally.analyze import analyze_file

    sine = _make_sine_wav(tmp_path / "sine.wav", freq=220.0)
    noise = _make_noise_wav(tmp_path / "noise.wav")

    sine_result = analyze_file(sine)
    noise_result = analyze_file(noise)

    assert noise_result.zero_crossing_rate > sine_result.zero_crossing_rate


def test_analyze_bright_vs_dark_centroid(tmp_path):
    """A high-frequency sine should have a higher spectral centroid than a low one."""
    from dodgylegally.analyze import analyze_file

    bright = _make_sine_wav(tmp_path / "bright.wav", freq=4000.0)
    dark = _make_sine_wav(tmp_path / "dark.wav", freq=200.0)

    bright_result = analyze_file(bright)
    dark_result = analyze_file(dark)

    assert bright_result.spectral_centroid > dark_result.spectral_centroid


def test_analyze_key_returns_string_or_none(tmp_path):
    """Key detection should return a key string or None."""
    from dodgylegally.analyze import analyze_file

    wav = _make_sine_wav(tmp_path / "sine.wav", freq=440.0)
    result = analyze_file(wav)

    assert result.key is None or isinstance(result.key, str)


def test_analyze_caching_uses_sidecar(tmp_path):
    """Second call to analyze_file with use_cache=True reads from sidecar."""
    from dodgylegally.analyze import analyze_file
    from dodgylegally.metadata import read_sidecar

    wav = _make_sine_wav(tmp_path / "sine.wav")

    # First call — computes and writes sidecar
    result1 = analyze_file(wav, use_cache=True)
    sidecar = read_sidecar(wav)
    assert "analysis" in sidecar

    # Second call — reads from cache (should return same values)
    result2 = analyze_file(wav, use_cache=True)
    assert result1.duration_ms == result2.duration_ms
    assert result1.rms_energy == result2.rms_energy


def test_analyze_nonexistent_raises(tmp_path):
    """analyze_file raises FileNotFoundError for missing files."""
    from dodgylegally.analyze import analyze_file

    with pytest.raises(FileNotFoundError):
        analyze_file(tmp_path / "ghost.wav")


def test_cli_analyze_subcommand(tmp_path):
    """CLI 'analyze' subcommand runs and outputs analysis."""
    from click.testing import CliRunner
    from dodgylegally.cli import cli

    wav = _make_sine_wav(tmp_path / "sample.wav")

    runner = CliRunner()
    result = runner.invoke(cli, ["analyze", "--input", str(tmp_path)])
    assert result.exit_code == 0
    assert "sample.wav" in result.output
