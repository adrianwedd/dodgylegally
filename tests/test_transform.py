"""Tests for pitch and time transforms."""

import numpy as np
import soundfile as sf
from pathlib import Path

import pytest


def _make_sine_wav(path: Path, freq: float = 440.0, duration_s: float = 2.0, sr: int = 22050):
    """Generate a sine wave WAV file."""
    t = np.linspace(0, duration_s, int(sr * duration_s), endpoint=False)
    audio = 0.5 * np.sin(2 * np.pi * freq * t)
    sf.write(str(path), audio, sr)
    return path


def test_time_stretch_changes_duration(tmp_path):
    """time_stretch_file at rate 2.0 halves the duration."""
    from dodgylegally.transform import time_stretch_file

    wav = _make_sine_wav(tmp_path / "sine.wav", duration_s=2.0)
    out = tmp_path / "stretched.wav"

    time_stretch_file(str(wav), str(out), rate=2.0)
    assert out.exists()

    y, sr = sf.read(str(out))
    duration_ms = len(y) / sr * 1000
    # At rate 2.0, ~1000ms (half of 2000ms), allow margin
    assert 800 < duration_ms < 1200


def test_time_stretch_slower(tmp_path):
    """time_stretch_file at rate 0.5 doubles the duration."""
    from dodgylegally.transform import time_stretch_file

    wav = _make_sine_wav(tmp_path / "sine.wav", duration_s=1.0)
    out = tmp_path / "stretched.wav"

    time_stretch_file(str(wav), str(out), rate=0.5)
    y, sr = sf.read(str(out))
    duration_ms = len(y) / sr * 1000
    assert 1600 < duration_ms < 2400


def test_pitch_shift_file_creates_output(tmp_path):
    """pitch_shift_file produces a WAV file."""
    from dodgylegally.transform import pitch_shift_file

    wav = _make_sine_wav(tmp_path / "sine.wav")
    out = tmp_path / "shifted.wav"

    pitch_shift_file(str(wav), str(out), semitones=3)
    assert out.exists()

    y, sr = sf.read(str(out))
    assert len(y) > 0


def test_pitch_shift_preserves_duration(tmp_path):
    """pitch_shift_file doesn't change duration."""
    from dodgylegally.transform import pitch_shift_file

    wav = _make_sine_wav(tmp_path / "sine.wav", duration_s=2.0)
    out = tmp_path / "shifted.wav"

    pitch_shift_file(str(wav), str(out), semitones=5)
    y_in, sr_in = sf.read(str(wav))
    y_out, sr_out = sf.read(str(out))

    dur_in = len(y_in) / sr_in * 1000
    dur_out = len(y_out) / sr_out * 1000
    assert abs(dur_in - dur_out) < 100


def test_semitones_between_keys():
    """semitones_between computes shortest-path intervals."""
    from dodgylegally.transform import semitones_between

    # C to G = -5 (shortest: 5 down) rather than +7 up
    assert semitones_between("C", "G") == -5
    # A to C = 3 semitones up
    assert semitones_between("A", "C") == 3
    # Same key = 0
    assert semitones_between("D", "D") == 0


def test_semitones_between_wraps():
    """semitones_between picks shortest path (never more than 6)."""
    from dodgylegally.transform import semitones_between

    # B to C — 1 semitone up, not 11 down
    assert semitones_between("B", "C") == 1
    # F# to C — 6 semitones (shortest path)
    assert abs(semitones_between("F#", "C")) <= 6


def test_key_match_file(tmp_path):
    """key_match_file produces a valid WAV."""
    from dodgylegally.transform import key_match_file

    wav = _make_sine_wav(tmp_path / "sine.wav", freq=440.0)
    out = tmp_path / "matched.wav"

    key_match_file(str(wav), str(out), target_key="C major")
    assert out.exists()

    y, sr = sf.read(str(out))
    assert len(y) > 0


def test_cli_process_stretch_applies(tmp_path):
    """CLI process --stretch actually calls time_stretch_file."""
    from unittest.mock import patch
    from click.testing import CliRunner
    from dodgylegally.cli import cli

    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    _make_sine_wav(raw_dir / "test.wav", duration_s=2.0)

    with patch("dodgylegally.transform.time_stretch_file") as mock_stretch:
        # Make mock return a valid path so processing can continue
        mock_stretch.side_effect = lambda inp, out, rate: (
            sf.write(out, np.zeros(22050), 22050) or out
        )
        runner = CliRunner()
        result = runner.invoke(cli, [
            "--output", str(tmp_path),
            "process", "--stretch", "2.0",
        ])
        assert result.exit_code == 0, result.output
        mock_stretch.assert_called_once()
        _, kwargs = mock_stretch.call_args
        assert kwargs.get("rate") == 2.0 or mock_stretch.call_args[0][2] == 2.0


def test_cli_process_pitch_applies(tmp_path):
    """CLI process --pitch actually calls pitch_shift_file."""
    from unittest.mock import patch
    from click.testing import CliRunner
    from dodgylegally.cli import cli

    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    _make_sine_wav(raw_dir / "test.wav", duration_s=2.0)

    with patch("dodgylegally.transform.pitch_shift_file") as mock_pitch:
        mock_pitch.side_effect = lambda inp, out, semitones: (
            sf.write(out, np.zeros(22050), 22050) or out
        )
        runner = CliRunner()
        result = runner.invoke(cli, [
            "--output", str(tmp_path),
            "process", "--pitch", "3",
        ])
        assert result.exit_code == 0, result.output
        mock_pitch.assert_called_once()


def test_cli_process_accepts_transform_flags():
    """CLI process subcommand accepts --stretch, --pitch, --target-key flags."""
    from click.testing import CliRunner
    from dodgylegally.cli import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["process", "--help"])
    assert "--stretch" in result.output
    assert "--pitch" in result.output
    assert "--target-key" in result.output


def test_cli_process_transform_cleans_temps_on_error(tmp_path):
    """Transform temp files are cleaned up even when process_file raises."""
    import os
    import tempfile
    from unittest.mock import patch
    from click.testing import CliRunner
    from dodgylegally.cli import cli

    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    _make_sine_wav(raw_dir / "test.wav", duration_s=2.0)

    temp_dir = tempfile.gettempdir()
    before = {f for f in os.listdir(temp_dir) if f.endswith(".wav")}

    with patch("dodgylegally.transform.time_stretch_file") as mock_stretch:
        # Make stretch write a real temp file, then process_file will fail
        mock_stretch.side_effect = lambda inp, out, rate: (
            sf.write(out, np.zeros(22050), 22050) or out
        )
        with patch("dodgylegally.process.process_file", side_effect=RuntimeError("boom")):
            runner = CliRunner()
            result = runner.invoke(cli, [
                "--output", str(tmp_path),
                "process", "--stretch", "2.0",
            ])

    after = {f for f in os.listdir(temp_dir) if f.endswith(".wav")}
    leaked = after - before
    assert len(leaked) == 0, f"Leaked temp files: {leaked}"
