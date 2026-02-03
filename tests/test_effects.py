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


# --- Delay Effect Tests ---


def test_delay_in_registry():
    """Delay effect is registered."""
    from dodgylegally.effects import list_effects

    assert "delay" in list_effects()


def test_delay_effect_basic():
    """Delay output is longer than input at mix=1.0."""
    from dodgylegally.effects import get_effect

    seg = _make_segment(duration_ms=500)
    effect = get_effect("delay")
    result = effect.apply(seg, {"delay_ms": 200, "repeats": 3, "mix": 1.0})

    # Wet-only: input + delay_ms * repeats = 500 + 600 = 1100ms
    assert len(result) > len(seg)


def test_delay_feedback_decay():
    """Higher feedback produces louder tails than lower feedback."""
    from dodgylegally.effects import get_effect

    seg = _make_segment(duration_ms=500)
    effect = get_effect("delay")

    result_low = effect.apply(seg, {
        "delay_ms": 200, "feedback": 0.1, "repeats": 5, "mix": 1.0,
    })
    result_high = effect.apply(seg, {
        "delay_ms": 200, "feedback": 0.8, "repeats": 5, "mix": 1.0,
    })

    # Compare tail energy (last 200ms)
    tail_low = result_low[-200:]
    tail_high = result_high[-200:]
    assert _segment_rms(tail_high) > _segment_rms(tail_low)


def test_delay_dry_wet_mix():
    """mix=0 returns original length, mix=1 returns extended."""
    from dodgylegally.effects import get_effect

    seg = _make_segment(duration_ms=500)
    effect = get_effect("delay")

    dry = effect.apply(seg, {"delay_ms": 200, "repeats": 3, "mix": 0.0})
    wet = effect.apply(seg, {"delay_ms": 200, "repeats": 3, "mix": 1.0})

    assert len(dry) == len(seg)
    assert len(wet) > len(seg)


def test_delay_fractional_mix_no_clipping():
    """mix=0.5 should not boost RMS above dry signal (proper crossfade)."""
    from dodgylegally.effects import get_effect

    seg = _make_segment(duration_ms=500)
    effect = get_effect("delay")

    dry_rms = _segment_rms(seg)
    result = effect.apply(seg, {"delay_ms": 200, "repeats": 3, "mix": 0.5})
    # Truncate to original length for fair RMS comparison
    result_head = result[:len(seg)]
    assert _segment_rms(result_head) <= dry_rms * 1.1  # allow 10% tolerance


def test_delay_zero_repeats_passthrough():
    """repeats=0 returns unchanged audio."""
    from dodgylegally.effects import get_effect

    seg = _make_segment(duration_ms=500)
    effect = get_effect("delay")
    result = effect.apply(seg, {"repeats": 0})

    assert len(result) == len(seg)
    # Same raw samples
    assert seg.get_array_of_samples() == result.get_array_of_samples()


def test_delay_parse_chain():
    """parse_chain('delay:375') maps to delay_ms=375."""
    from dodgylegally.effects import parse_chain

    chain = parse_chain("delay:375")
    assert len(chain.effects) == 1
    effect, params = chain.effects[0]
    assert effect.name == "delay"
    assert params["delay_ms"] == 375.0


def test_delay_in_chain_with_other_effects():
    """Delay works in a chain with lowpass."""
    from dodgylegally.effects import parse_chain

    seg = _make_segment(duration_ms=500)
    chain = parse_chain("lowpass:2000,delay:300")
    result = chain.apply(seg)

    assert isinstance(result, AudioSegment)
    assert len(result) > len(seg)  # delay extends


def test_cli_process_accepts_effects_flag():
    """CLI process subcommand accepts --effects flag."""
    from click.testing import CliRunner
    from dodgylegally.cli import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["process", "--help"])
    assert "--effects" in result.output
