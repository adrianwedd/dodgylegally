"""Audio source registry — get_source, list_sources, register_source."""

from __future__ import annotations

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


# Register built-in sources
from dodgylegally.sources.youtube import YouTubeSource  # noqa: E402
register_source("youtube", YouTubeSource)
