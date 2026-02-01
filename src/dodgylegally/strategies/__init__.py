"""Arrangement strategy registry — get_strategy, list_strategies, register_strategy."""

from __future__ import annotations

from dodgylegally.strategies.base import ArrangementStrategy

_REGISTRY: dict[str, type] = {}


def register_strategy(name: str, cls: type) -> None:
    """Register an ArrangementStrategy implementation by name."""
    _REGISTRY[name] = cls


def get_strategy(name: str) -> ArrangementStrategy:
    """Return an instance of the named strategy. Raises KeyError if unknown."""
    if name not in _REGISTRY:
        raise KeyError(f"Unknown strategy: '{name}'. Available: {', '.join(_REGISTRY)}")
    return _REGISTRY[name]()


def list_strategies() -> list[str]:
    """Return sorted list of registered strategy names."""
    return sorted(_REGISTRY.keys())


# Register built-in strategies
from dodgylegally.strategies.builtin import (  # noqa: E402
    SequentialStrategy,
    LoudnessStrategy,
    TempoStrategy,
    KeyCompatibleStrategy,
    LayeredStrategy,
)

register_strategy("sequential", SequentialStrategy)
register_strategy("loudness", LoudnessStrategy)
register_strategy("tempo", TempoStrategy)
register_strategy("key_compatible", KeyCompatibleStrategy)
register_strategy("layered", LayeredStrategy)
