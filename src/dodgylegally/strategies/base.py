"""Base protocol for arrangement strategies."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ArrangementStrategy(Protocol):
    """Protocol for sample arrangement strategies."""

    @property
    def name(self) -> str:
        ...

    def arrange(self, files: list[str], **kwargs) -> list[str]:
        """Arrange files according to the strategy. Returns ordered file list."""
        ...
