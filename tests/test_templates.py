"""Tests for arrangement templates."""

import json
from pathlib import Path

import pytest
from pydub import AudioSegment
from pydub.generators import Sine


def _make_wav(path: Path, freq: float = 440.0, duration_ms: int = 1000):
    """Generate a sine wave WAV file."""
    seg = Sine(freq).to_audio_segment(duration=duration_ms).apply_gain(-10)
    seg.export(str(path), format="wav")
    return path


def _make_wav_with_analysis(path: Path, freq: float = 440.0, duration_ms: int = 1000,
                             bpm: float = 120.0, key: str = "C major", lufs: float = -12.0):
    """Generate a WAV and write a fake analysis sidecar."""
    _make_wav(path, freq=freq, duration_ms=duration_ms)
    sidecar = path.with_suffix(".json")
    sidecar.write_text(json.dumps({
        "analysis": {
            "bpm": bpm, "key": key, "loudness_lufs": lufs,
            "duration_ms": duration_ms, "spectral_centroid": freq,
            "rms_energy": 0.1, "zero_crossing_rate": 0.05,
        }
    }, indent=2))
    return path


def test_load_template_bundled():
    """load_template loads a bundled template by name."""
    from dodgylegally.strategies.templates import load_template

    template = load_template("build-and-drop")
    assert "sections" in template
    assert len(template["sections"]) > 0


def test_load_template_missing_raises():
    """load_template raises FileNotFoundError for unknown templates."""
    from dodgylegally.strategies.templates import load_template

    with pytest.raises(FileNotFoundError):
        load_template("nonexistent_template")


def test_list_templates_includes_builtins():
    """list_templates returns bundled template names."""
    from dodgylegally.strategies.templates import list_templates

    names = list_templates()
    assert "build-and-drop" in names
    assert "ambient-drift" in names


def test_template_section_has_required_fields():
    """Each template section has strategy and duration_s."""
    from dodgylegally.strategies.templates import load_template

    template = load_template("build-and-drop")
    for section in template["sections"]:
        assert "name" in section
        assert "strategy" in section
        assert "duration_s" in section


def test_apply_template_produces_output(tmp_path):
    """apply_template creates an output WAV file."""
    from dodgylegally.strategies.templates import load_template, apply_template

    # Create sample files with analysis
    loop_dir = tmp_path / "loops"
    loop_dir.mkdir()
    for i, name in enumerate(["a.wav", "b.wav", "c.wav", "d.wav"]):
        _make_wav_with_analysis(loop_dir / name, freq=200 + i * 100, lufs=-20 + i * 3)

    template = load_template("build-and-drop")
    out = tmp_path / "out.wav"

    result = apply_template(template, str(loop_dir), str(out))
    assert Path(result).exists()


def test_apply_template_with_few_files(tmp_path):
    """apply_template works even with fewer files than sections."""
    from dodgylegally.strategies.templates import load_template, apply_template

    loop_dir = tmp_path / "loops"
    loop_dir.mkdir()
    _make_wav_with_analysis(loop_dir / "only.wav", lufs=-12.0)

    template = load_template("build-and-drop")
    out = tmp_path / "out.wav"

    result = apply_template(template, str(loop_dir), str(out))
    assert Path(result).exists()


def test_spoken_word_reveal_template_loads():
    """spoken-word-reveal template loads with 4 sections."""
    from dodgylegally.strategies.templates import load_template

    template = load_template("spoken-word-reveal")
    assert template["name"] == "spoken-word-reveal"
    assert len(template["sections"]) == 4
    names = [s["name"] for s in template["sections"]]
    assert names == ["texture", "emerge", "reveal", "echo"]


def test_spoken_word_reveal_template_applies(tmp_path):
    """apply_template with spoken-word-reveal produces output."""
    from dodgylegally.strategies.templates import load_template, apply_template

    loop_dir = tmp_path / "loops"
    loop_dir.mkdir()
    for i, name in enumerate(["a.wav", "b.wav", "c.wav", "d.wav", "e.wav"]):
        _make_wav_with_analysis(loop_dir / name, freq=200 + i * 80, lufs=-18 + i * 2)

    template = load_template("spoken-word-reveal")
    out = tmp_path / "reveal.wav"

    result = apply_template(template, str(loop_dir), str(out))
    assert Path(result).exists()
    seg = AudioSegment.from_file(result, format="wav")
    # Total template duration: 6 + 5 + 4 + 5 = 20s
    assert len(seg) >= 15000  # allow some margin


def test_cli_combine_accepts_template_flag():
    """CLI combine subcommand accepts --template flag."""
    from click.testing import CliRunner
    from dodgylegally.cli import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["combine", "--help"])
    assert "--template" in result.output
