"""Tests for arrangement strategies."""

import json
import numpy as np
import soundfile as sf
from pathlib import Path

import pytest
from pydub import AudioSegment
from pydub.generators import Sine


def _make_wav(path: Path, freq: float = 440.0, duration_ms: int = 1000, amplitude: float = 0.5):
    """Generate a sine wave WAV file via pydub."""
    seg = Sine(freq).to_audio_segment(duration=duration_ms).apply_gain(-10 if amplitude > 0.3 else -30)
    seg.export(str(path), format="wav")
    return path


def _make_wav_with_analysis(path: Path, freq: float = 440.0, duration_ms: int = 1000,
                             bpm: float = 120.0, key: str = "C major", lufs: float = -12.0):
    """Generate a WAV and write a fake analysis sidecar for strategy testing."""
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


# --- Registry Tests ---


def test_strategy_registry_has_builtins():
    """Strategy registry contains all built-in strategies."""
    from dodgylegally.strategies import list_strategies

    names = list_strategies()
    assert "sequential" in names
    assert "loudness" in names
    assert "layered" in names


def test_get_strategy_returns_instance():
    """get_strategy returns an ArrangementStrategy instance."""
    from dodgylegally.strategies import get_strategy
    from dodgylegally.strategies.base import ArrangementStrategy

    strategy = get_strategy("sequential")
    assert isinstance(strategy, ArrangementStrategy)


def test_get_strategy_unknown_raises():
    """get_strategy raises KeyError for unknown strategies."""
    from dodgylegally.strategies import get_strategy

    with pytest.raises(KeyError):
        get_strategy("nonexistent_strategy")


# --- Sequential Strategy ---


def test_sequential_preserves_order(tmp_path):
    """Sequential strategy keeps files in their original order."""
    from dodgylegally.strategies import get_strategy

    files = []
    for i, name in enumerate(["aaa.wav", "bbb.wav", "ccc.wav"]):
        f = _make_wav(tmp_path / name, freq=200 + i * 200)
        files.append(str(f))

    strategy = get_strategy("sequential")
    ordered = strategy.arrange(files)
    assert [Path(f).name for f in ordered] == ["aaa.wav", "bbb.wav", "ccc.wav"]


# --- Loudness Strategy ---


def test_loudness_orders_by_lufs(tmp_path):
    """Loudness strategy orders files quiet-to-loud by default."""
    from dodgylegally.strategies import get_strategy

    _make_wav_with_analysis(tmp_path / "loud.wav", lufs=-6.0)
    _make_wav_with_analysis(tmp_path / "medium.wav", lufs=-12.0)
    _make_wav_with_analysis(tmp_path / "quiet.wav", lufs=-24.0)

    files = [str(tmp_path / "loud.wav"), str(tmp_path / "medium.wav"), str(tmp_path / "quiet.wav")]
    strategy = get_strategy("loudness")
    ordered = strategy.arrange(files)

    names = [Path(f).name for f in ordered]
    assert names == ["quiet.wav", "medium.wav", "loud.wav"]


def test_loudness_descending(tmp_path):
    """Loudness strategy with descending=True orders loud-to-quiet."""
    from dodgylegally.strategies import get_strategy

    _make_wav_with_analysis(tmp_path / "loud.wav", lufs=-6.0)
    _make_wav_with_analysis(tmp_path / "quiet.wav", lufs=-24.0)

    files = [str(tmp_path / "quiet.wav"), str(tmp_path / "loud.wav")]
    strategy = get_strategy("loudness")
    ordered = strategy.arrange(files, descending=True)

    names = [Path(f).name for f in ordered]
    assert names == ["loud.wav", "quiet.wav"]


# --- Tempo Strategy ---


def test_tempo_groups_by_similar_bpm(tmp_path):
    """Tempo strategy groups files with similar BPM together."""
    from dodgylegally.strategies import get_strategy

    _make_wav_with_analysis(tmp_path / "fast.wav", bpm=140.0)
    _make_wav_with_analysis(tmp_path / "slow.wav", bpm=80.0)
    _make_wav_with_analysis(tmp_path / "fast2.wav", bpm=138.0)

    files = [str(tmp_path / "fast.wav"), str(tmp_path / "slow.wav"), str(tmp_path / "fast2.wav")]
    strategy = get_strategy("tempo")
    ordered = strategy.arrange(files)

    # fast and fast2 should be adjacent
    names = [Path(f).name for f in ordered]
    fast_idx = names.index("fast.wav")
    fast2_idx = names.index("fast2.wav")
    assert abs(fast_idx - fast2_idx) == 1


# --- Key Compatible Strategy ---


def test_key_compatible_groups_related_keys(tmp_path):
    """Key-compatible strategy groups harmonically related keys."""
    from dodgylegally.strategies import get_strategy

    _make_wav_with_analysis(tmp_path / "c_major.wav", key="C major")
    _make_wav_with_analysis(tmp_path / "a_minor.wav", key="A minor")
    _make_wav_with_analysis(tmp_path / "fsharp_major.wav", key="F# major")

    files = [str(tmp_path / f) for f in ["c_major.wav", "fsharp_major.wav", "a_minor.wav"]]
    strategy = get_strategy("key_compatible")
    ordered = strategy.arrange(files)

    # C major and A minor are relative keys — should be adjacent
    names = [Path(f).name for f in ordered]
    c_idx = names.index("c_major.wav")
    a_idx = names.index("a_minor.wav")
    assert abs(c_idx - a_idx) == 1


# --- Layered Strategy ---


def test_layered_produces_output(tmp_path):
    """Layered strategy produces an AudioSegment combining files."""
    from dodgylegally.strategies import get_strategy

    for name in ["a.wav", "b.wav", "c.wav"]:
        _make_wav(tmp_path / name, duration_ms=500)

    files = [str(tmp_path / f) for f in ["a.wav", "b.wav", "c.wav"]]
    strategy = get_strategy("layered")
    result = strategy.arrange(files, max_layers=2)

    assert isinstance(result, list)
    assert len(result) > 0


# --- CLI ---


def test_cli_combine_accepts_strategy_flag():
    """CLI combine subcommand accepts --strategy flag."""
    from click.testing import CliRunner
    from dodgylegally.cli import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["combine", "--help"])
    assert "--strategy" in result.output
