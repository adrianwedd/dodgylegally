"""Audio source registry — get_source, list_sources, register_source, weighted selection."""

from __future__ import annotations

import random

from dodgylegally.sources.base import AudioSource

_REGISTRY: dict[str, type] = {}


def register_source(name: str, cls: type) -> None:
    """Register an AudioSource implementation by name."""
    _REGISTRY[name] = cls


def get_source(name: str) -> AudioSource:
    """Return an instance of the named audio source. Raises KeyError if unknown."""
    if name not in _REGISTRY:
        raise KeyError(f"Unknown source: '{name}'. Available: {', '.join(_REGISTRY)}")
    return _REGISTRY[name]()


def list_sources() -> list[str]:
    """Return sorted list of registered source names."""
    return sorted(_REGISTRY.keys())


def parse_source_weight(spec: str) -> tuple[str, int]:
    """Parse a 'name:weight' string. Weight defaults to 1 if omitted.

    Examples: 'youtube:7' -> ('youtube', 7), 'local' -> ('local', 1)
    Raises ValueError if weight is not a valid integer.
    """
    if ":" in spec:
        name, weight_str = spec.rsplit(":", 1)
        try:
            weight = int(weight_str)
        except ValueError:
            raise ValueError(f"Invalid weight in '{spec}': '{weight_str}' is not an integer")
        return name, weight
    return spec, 1


def weighted_select(sources: list[tuple[str, int]]) -> str:
    """Select a source name randomly according to weights.

    sources: list of (name, weight) tuples.
    Returns the selected source name.
    """
    names = [s[0] for s in sources]
    weights = [s[1] for s in sources]
    return random.choices(names, weights=weights, k=1)[0]


# Register built-in sources
from dodgylegally.sources.youtube import YouTubeSource  # noqa: E402
from dodgylegally.sources.local import LocalSource  # noqa: E402
register_source("youtube", YouTubeSource)
register_source("local", LocalSource)
