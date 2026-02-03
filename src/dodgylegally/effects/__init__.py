"""Audio effects registry — get_effect, list_effects, parse_chain."""

from __future__ import annotations

from dodgylegally.effects.base import AudioEffect, EffectChain

_REGISTRY: dict[str, type] = {}


def register_effect(name: str, cls: type) -> None:
    """Register an AudioEffect implementation by name."""
    _REGISTRY[name] = cls


def get_effect(name: str) -> AudioEffect:
    """Return an instance of the named effect. Raises KeyError if unknown."""
    if name not in _REGISTRY:
        raise KeyError(f"Unknown effect: '{name}'. Available: {', '.join(_REGISTRY)}")
    return _REGISTRY[name]()


def list_effects() -> list[str]:
    """Return sorted list of registered effect names."""
    return sorted(_REGISTRY.keys())


def parse_chain(spec: str) -> EffectChain:
    """Parse an effect chain string into an EffectChain.

    Format: 'effect1:param,effect2:param,...'
    Examples:
        'reverse' -> [(ReverseEffect, {})]
        'reverse,lowpass:3000' -> [(ReverseEffect, {}), (LowpassEffect, {freq: 3000})]
        'bitcrush:4,distortion:20' -> [(BitcrushEffect, {bits: 4}), (DistortionEffect, {gain: 20})]
    """
    if not spec or not spec.strip():
        return EffectChain()

    effects = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if ":" in part:
            name, value = part.split(":", 1)
            effect = get_effect(name)
            # Map single param value to the effect's primary parameter
            params = _default_param(name, value)
        else:
            effect = get_effect(part)
            params = {}
        effects.append((effect, params))

    return EffectChain(effects=effects)


def _default_param(effect_name: str, value: str) -> dict:
    """Map a single parameter value to the correct param name for an effect."""
    _param_map = {
        "lowpass": "freq",
        "highpass": "freq",
        "bitcrush": "bits",
        "distortion": "gain",
        "stutter": "slice_ms",
        "delay": "delay_ms",
    }
    key = _param_map.get(effect_name, "value")
    try:
        return {key: float(value)}
    except ValueError:
        return {key: value}


# Register built-in effects
from dodgylegally.effects.builtin import (  # noqa: E402
    ReverseEffect,
    LowpassEffect,
    HighpassEffect,
    BitcrushEffect,
    DistortionEffect,
    StutterEffect,
    DelayEffect,
)

register_effect("reverse", ReverseEffect)
register_effect("lowpass", LowpassEffect)
register_effect("highpass", HighpassEffect)
register_effect("bitcrush", BitcrushEffect)
register_effect("distortion", DistortionEffect)
register_effect("stutter", StutterEffect)
register_effect("delay", DelayEffect)
