"""Base types for audio sources."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable


@dataclass
class SearchResult:
    """A single result from searching an audio source."""

    source: str
    title: str
    url: str
    duration_s: float | None
    metadata: dict = field(default_factory=dict)


@dataclass
class DownloadedClip:
    """A downloaded and extracted audio clip."""

    path: Path
    source_result: SearchResult
    duration_ms: int


@runtime_checkable
class AudioSource(Protocol):
    """Protocol that all audio sources must implement."""

    @property
    def name(self) -> str: ...

    def search(self, query: str, max_results: int = 1) -> list[SearchResult]: ...

    def download(self, result: SearchResult, output_dir: Path) -> DownloadedClip: ...

    def dry_run(self, query: str) -> dict: ...
