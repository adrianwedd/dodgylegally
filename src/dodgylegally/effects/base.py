"""Base protocol and chain class for audio effects."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from pydub import AudioSegment


@runtime_checkable
class AudioEffect(Protocol):
    """Protocol for audio effects. Implement apply() to create a new effect."""

    @property
    def name(self) -> str:
        ...

    def apply(self, audio: AudioSegment, params: dict) -> AudioSegment:
        """Apply the effect to an AudioSegment and return the result."""
        ...


@dataclass
class EffectChain:
    """An ordered chain of effects to apply sequentially."""

    effects: list[tuple[AudioEffect, dict]] = field(default_factory=list)

    def apply(self, audio: AudioSegment) -> AudioSegment:
        """Apply all effects in order."""
        result = audio
        for effect, params in self.effects:
            result = effect.apply(result, params)
        return result
