"""Tests for multi-track stem export."""

import json
from pathlib import Path

import pytest
from pydub.generators import Sine


def _make_wav(path: Path, freq: float = 440.0, duration_ms: int = 1000):
    """Generate a sine wave WAV file."""
    seg = Sine(freq).to_audio_segment(duration=duration_ms).apply_gain(-10)
    seg.export(str(path), format="wav")
    return path


def test_export_stems_creates_files(tmp_path):
    """export_stems creates individual stem WAV files."""
    from dodgylegally.stems import export_stems

    loop_dir = tmp_path / "loops"
    loop_dir.mkdir()
    for name in ["a.wav", "b.wav", "c.wav"]:
        _make_wav(loop_dir / name, duration_ms=500)

    stem_dir = tmp_path / "stems"
    result = export_stems(str(loop_dir), str(stem_dir))

    assert (stem_dir).exists()
    stem_files = list(stem_dir.glob("stem_*.wav"))
    assert len(stem_files) == 3


def test_export_stems_creates_manifest(tmp_path):
    """export_stems creates a manifest.json."""
    from dodgylegally.stems import export_stems

    loop_dir = tmp_path / "loops"
    loop_dir.mkdir()
    for name in ["a.wav", "b.wav"]:
        _make_wav(loop_dir / name, duration_ms=500)

    stem_dir = tmp_path / "stems"
    export_stems(str(loop_dir), str(stem_dir))

    manifest_path = stem_dir / "manifest.json"
    assert manifest_path.exists()

    manifest = json.loads(manifest_path.read_text())
    assert "tracks" in manifest
    assert len(manifest["tracks"]) == 2


def test_manifest_has_timing_info(tmp_path):
    """Manifest tracks include start_ms and duration_ms."""
    from dodgylegally.stems import export_stems

    loop_dir = tmp_path / "loops"
    loop_dir.mkdir()
    _make_wav(loop_dir / "clip.wav", duration_ms=1000)

    stem_dir = tmp_path / "stems"
    export_stems(str(loop_dir), str(stem_dir), repeats=(2, 2))

    manifest = json.loads((stem_dir / "manifest.json").read_text())
    track = manifest["tracks"][0]

    assert "start_ms" in track
    assert "duration_ms" in track
    assert "source" in track
    assert "stem_file" in track
    assert track["start_ms"] == 0
    assert track["duration_ms"] > 0


def test_export_stems_creates_full_mix(tmp_path):
    """export_stems also creates a full mix WAV."""
    from dodgylegally.stems import export_stems

    loop_dir = tmp_path / "loops"
    loop_dir.mkdir()
    _make_wav(loop_dir / "a.wav", duration_ms=500)
    _make_wav(loop_dir / "b.wav", duration_ms=500)

    stem_dir = tmp_path / "stems"
    result = export_stems(str(loop_dir), str(stem_dir))

    assert "full_mix" in result
    assert Path(result["full_mix"]).exists()


def test_export_stems_empty_dir(tmp_path):
    """export_stems returns empty result for empty directory."""
    from dodgylegally.stems import export_stems

    loop_dir = tmp_path / "loops"
    loop_dir.mkdir()

    stem_dir = tmp_path / "stems"
    result = export_stems(str(loop_dir), str(stem_dir))

    assert result["tracks"] == []


def test_manifest_timing_is_sequential(tmp_path):
    """Manifest track start times are sequential (non-overlapping)."""
    from dodgylegally.stems import export_stems

    loop_dir = tmp_path / "loops"
    loop_dir.mkdir()
    for name in ["a.wav", "b.wav", "c.wav"]:
        _make_wav(loop_dir / name, duration_ms=500)

    stem_dir = tmp_path / "stems"
    export_stems(str(loop_dir), str(stem_dir), repeats=(1, 1))

    manifest = json.loads((stem_dir / "manifest.json").read_text())
    tracks = manifest["tracks"]

    for i in range(1, len(tracks)):
        prev_end = tracks[i - 1]["start_ms"] + tracks[i - 1]["duration_ms"]
        assert tracks[i]["start_ms"] == prev_end


def test_cli_combine_accepts_stems_flag():
    """CLI combine subcommand accepts --stems flag."""
    from click.testing import CliRunner
    from dodgylegally.cli import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["combine", "--help"])
    assert "--stems" in result.output
