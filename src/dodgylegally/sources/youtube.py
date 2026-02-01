"""YouTube audio source — wraps yt-dlp for search and download."""

from __future__ import annotations

import glob
import os
import time
from pathlib import Path

from yt_dlp import YoutubeDL

from dodgylegally.clip import ClipSpec, DownloadRangeFunc, DEFAULT_CLIP_SPEC
from dodgylegally.sources.base import AudioSource, DownloadedClip, SearchResult


_SKIP_PATTERNS = [
    "no video results",
    "no suitable video",
    "is not a valid url",
    "unable to extract",
    "video unavailable",
]


class DownloadSkipError(Exception):
    """Raised when a download should be skipped (not retried)."""


def _is_skip_error(error: Exception) -> bool:
    msg = str(error).lower()
    return any(pattern in msg for pattern in _SKIP_PATTERNS)


def _sanitize_phrase(phrase: str) -> str:
    safe = "".join(x for x in phrase if x.isalnum() or x in "._- ").strip()
    return safe or "download"


class YouTubeSource:
    """Audio source that searches and downloads from YouTube via yt-dlp."""

    @property
    def name(self) -> str:
        return "youtube"

    def search(self, query: str, max_results: int = 1) -> list[SearchResult]:
        """Search YouTube and return metadata without downloading."""
        url = f"ytsearch{max_results}:{query}"
        opts = {"quiet": True, "no_warnings": True, "extract_flat": False}
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
        results = []
        for entry in (info or {}).get("entries", []):
            if entry:
                results.append(SearchResult(
                    source="youtube",
                    title=entry.get("title", ""),
                    url=entry.get("webpage_url", ""),
                    duration_s=entry.get("duration"),
                    metadata={"query": query},
                ))
        return results

    def download(
        self,
        result: SearchResult,
        output_dir: Path,
        max_retries: int = 3,
        delay: float = 0,
        clip_spec: ClipSpec | None = None,
    ) -> DownloadedClip:
        """Download a clip from a YouTube video.

        Uses clip_spec for position and duration. Defaults to midpoint, 1 second.
        """
        spec = clip_spec or DEFAULT_CLIP_SPEC
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        before = set(glob.glob(str(output_dir / "*.wav")))

        safe_phrase = _sanitize_phrase(result.metadata.get("query", result.title))
        opts = {
            "format": "bestaudio/best",
            "paths": {"home": str(output_dir)},
            "outtmpl": {"default": f"{safe_phrase}-%(id)s.%(ext)s"},
            "download_ranges": DownloadRangeFunc(spec=spec),
            "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "wav"}],
            "quiet": True,
            "no_warnings": True,
        }

        last_error = None
        for attempt in range(max_retries):
            try:
                with YoutubeDL(opts) as ydl:
                    ydl.download([result.url])
                new_files = list(set(glob.glob(str(output_dir / "*.wav"))) - before)
                if new_files:
                    path = Path(new_files[0])
                    return DownloadedClip(
                        path=path,
                        source_result=result,
                        duration_ms=int(spec.duration_s * 1000),
                        clip_spec=spec,
                    )
                raise RuntimeError("Download produced no output file")
            except Exception as e:
                if _is_skip_error(e):
                    raise DownloadSkipError(str(e)) from e
                last_error = e
                if attempt < max_retries - 1:
                    backoff = delay + (2 ** attempt)
                    time.sleep(backoff)

        raise last_error

    def dry_run(self, query: str) -> dict:
        """Return what would be searched/downloaded, without network calls."""
        return {
            "source": "youtube",
            "phrase": query,
            "url": f'ytsearch1:"{query}"',
            "action": "would search YouTube and download 1s clip from midpoint",
        }
