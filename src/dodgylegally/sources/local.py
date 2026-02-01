"""Local file audio source — uses files on disk as sample material."""

from __future__ import annotations

import random
from pathlib import Path

from pydub import AudioSegment

from dodgylegally.clip import ClipPosition, ClipSpec
from dodgylegally.sources.base import DownloadedClip, SearchResult

_SUPPORTED_EXTENSIONS = {".wav", ".mp3", ".flac", ".ogg", ".aif", ".aiff"}


class LocalSource:
    """Audio source that draws from local files on disk."""

    def __init__(self, base_path: Path | None = None):
        self._base_path = Path(base_path) if base_path else Path(".")

    @property
    def name(self) -> str:
        return "local"

    def search(self, query: str, max_results: int = 1) -> list[SearchResult]:
        """Find audio files matching a glob pattern in base_path.

        The query is used as a glob pattern. Use '*' for all files.
        Returns a random selection of up to max_results files.
        """
        files = [
            f for f in self._base_path.rglob(query)
            if f.is_file() and f.suffix.lower() in _SUPPORTED_EXTENSIONS
        ]
        if not files:
            return []
        selected = random.sample(files, min(len(files), max_results))
        results = []
        for f in selected:
            try:
                audio = AudioSegment.from_file(str(f))
                duration_s = len(audio) / 1000.0
            except Exception:
                duration_s = None
            results.append(SearchResult(
                source="local",
                title=f.name,
                url=str(f),
                duration_s=duration_s,
                metadata={"base_path": str(self._base_path), "query": query},
            ))
        return results

    def download(
        self,
        result: SearchResult,
        output_dir: Path,
        clip_spec: ClipSpec | None = None,
        **kwargs,
    ) -> DownloadedClip:
        """Extract a clip from a local audio file.

        Uses clip_spec for position and duration. Defaults to random position,
        1 second duration (preserving original behavior).
        """
        spec = clip_spec or ClipSpec(position=ClipPosition.RANDOM, duration_s=1.0)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        audio = AudioSegment.from_file(result.url)
        duration_ms = len(audio)
        clip_duration_ms = int(spec.duration_s * 1000)

        if duration_ms <= clip_duration_ms:
            clip = audio
        else:
            start_s = spec.compute_start_time(duration_ms / 1000.0)
            start_ms = int(start_s * 1000)
            start_ms = max(0, min(start_ms, duration_ms - clip_duration_ms))
            clip = audio[start_ms:start_ms + clip_duration_ms]

        out_name = Path(result.title).stem + "_clip.wav"
        out_path = output_dir / out_name
        clip.export(str(out_path), format="wav")

        return DownloadedClip(
            path=out_path,
            source_result=result,
            duration_ms=len(clip),
            clip_spec=spec,
        )

    def dry_run(self, query: str) -> dict:
        """Describe what would happen without reading files."""
        return {
            "source": "local",
            "phrase": query,
            "url": str(self._base_path),
            "action": f"would select random audio files from {self._base_path}",
        }
