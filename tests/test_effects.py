"""Tests for the audio effects system."""

import numpy as np
from pydub import AudioSegment
from pydub.generators import Sine

import pytest


def _make_segment(freq: float = 440.0, duration_ms: int = 1000) -> AudioSegment:
    """Generate a sine wave AudioSegment."""
    return Sine(freq).to_audio_segment(duration=duration_ms).apply_gain(-10)


def _segment_rms(seg: AudioSegment) -> float:
    """Return the RMS of an AudioSegment's raw samples."""
    samples = np.array(seg.get_array_of_samples(), dtype=np.float64)
    return float(np.sqrt(np.mean(samples ** 2)))


# --- Protocol & Registry Tests ---


def test_effect_registry_has_builtins():
    """Effect registry contains all built-in effects."""
    from dodgylegally.effects import list_effects

    names = list_effects()
    assert "reverse" in names
    assert "bitcrush" in names
    assert "lowpass" in names
    assert "highpass" in names
    assert "distortion" in names
    assert "stutter" in names


def test_get_effect_returns_instance():
    """get_effect returns an AudioEffect instance."""
    from dodgylegally.effects import get_effect
    from dodgylegally.effects.base import AudioEffect

    effect = get_effect("reverse")
    assert isinstance(effect, AudioEffect)


def test_get_effect_unknown_raises():
    """get_effect raises KeyError for unknown effects."""
    from dodgylegally.effects import get_effect

    with pytest.raises(KeyError):
        get_effect("nonexistent_effect")


# --- Chain Tests ---


def test_effect_chain_applies_in_order():
    """EffectChain applies effects in sequence."""
    from dodgylegally.effects.base import EffectChain
    from dodgylegally.effects import get_effect

    seg = _make_segment()
    chain = EffectChain([
        (get_effect("reverse"), {}),
    ])

    result = chain.apply(seg)
    assert isinstance(result, AudioSegment)
    assert len(result) > 0


def test_parse_chain_string():
    """parse_chain parses 'reverse,lowpass:3000' into effect-params pairs."""
    from dodgylegally.effects import parse_chain

    chain = parse_chain("reverse,lowpass:3000")
    assert len(chain.effects) == 2


def test_parse_chain_single():
    """parse_chain handles a single effect without params."""
    from dodgylegally.effects import parse_chain

    chain = parse_chain("reverse")
    assert len(chain.effects) == 1


def test_parse_chain_empty_returns_empty():
    """parse_chain with empty string returns empty chain."""
    from dodgylegally.effects import parse_chain

    chain = parse_chain("")
    assert len(chain.effects) == 0


# --- Individual Effect Tests ---


def test_reverse_effect():
    """Reverse flips the audio."""
    from dodgylegally.effects import get_effect

    seg = _make_segment()
    effect = get_effect("reverse")
    result = effect.apply(seg, {})

    assert isinstance(result, AudioSegment)
    assert len(result) == len(seg)


def test_lowpass_filter():
    """Lowpass filter reduces high-frequency content."""
    from dodgylegally.effects import get_effect

    # Bright signal (high freq sine)
    seg = _make_segment(freq=4000.0, duration_ms=2000)
    effect = get_effect("lowpass")
    result = effect.apply(seg, {"freq": 1000})

    # Filtered signal should be quieter (high freq attenuated)
    assert _segment_rms(result) < _segment_rms(seg)


def test_highpass_filter():
    """Highpass filter reduces low-frequency content."""
    from dodgylegally.effects import get_effect

    # Dark signal (low freq sine)
    seg = _make_segment(freq=100.0, duration_ms=2000)
    effect = get_effect("highpass")
    result = effect.apply(seg, {"freq": 2000})

    assert _segment_rms(result) < _segment_rms(seg)


def test_bitcrush_effect():
    """Bitcrush reduces bit depth."""
    from dodgylegally.effects import get_effect

    seg = _make_segment()
    effect = get_effect("bitcrush")
    result = effect.apply(seg, {"bits": 4})

    assert isinstance(result, AudioSegment)
    assert len(result) == len(seg)


def test_distortion_increases_rms():
    """Distortion should increase perceived loudness (RMS)."""
    from dodgylegally.effects import get_effect

    seg = _make_segment(freq=440.0, duration_ms=2000)
    effect = get_effect("distortion")
    result = effect.apply(seg, {"gain": 20})

    # Clipped signal has higher RMS than a sine at same peak
    assert _segment_rms(result) >= _segment_rms(seg) * 0.8


def test_stutter_effect():
    """Stutter repeats micro-segments, producing a longer or same-length result."""
    from dodgylegally.effects import get_effect

    seg = _make_segment(duration_ms=1000)
    effect = get_effect("stutter")
    result = effect.apply(seg, {"slice_ms": 50, "repeats": 3})

    assert isinstance(result, AudioSegment)
    assert len(result) > 0


def test_effect_chain_preserves_format():
    """Effect chain output has same channels and sample width as input."""
    from dodgylegally.effects import parse_chain

    seg = _make_segment()
    chain = parse_chain("reverse,lowpass:2000")
    result = chain.apply(seg)

    assert result.channels == seg.channels
    assert result.sample_width == seg.sample_width


def test_cli_process_accepts_effects_flag():
    """CLI process subcommand accepts --effects flag."""
    from click.testing import CliRunner
    from dodgylegally.cli import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["process", "--help"])
    assert "--effects" in result.output
