"""YouTube audio source — wraps yt-dlp for search and download."""

from __future__ import annotations

import glob
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path

from yt_dlp import YoutubeDL

from dodgylegally.clip import ClipPosition, ClipSpec, DownloadRangeFunc, DEFAULT_CLIP_SPEC
from dodgylegally.sources.base import AudioSource, DownloadedClip, SearchResult

logger = logging.getLogger(__name__)


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


@dataclass
class SpokenWordResult:
    """Result of a spoken-word search across multiple YouTube candidates."""

    clip: DownloadedClip
    caption_found: bool
    timestamp_s: float | None = None
    candidates_probed: int = 0
    method: str = "fallback"  # "caption" | "whisper" | "fallback"


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

    def _download_full_audio(self, result: SearchResult, tmp_dir: Path) -> Path:
        """Download full audio of a video to a temp directory as WAV."""
        safe_phrase = _sanitize_phrase(result.metadata.get("query", result.title))
        before = set(glob.glob(str(tmp_dir / "*.wav")))
        opts = {
            "format": "bestaudio/best",
            "paths": {"home": str(tmp_dir)},
            "outtmpl": {"default": f"{safe_phrase}-%(id)s.%(ext)s"},
            "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "wav"}],
            "quiet": True,
            "no_warnings": True,
        }
        with YoutubeDL(opts) as ydl:
            ydl.download([result.url])
        new_files = list(set(glob.glob(str(tmp_dir / "*.wav"))) - before)
        if not new_files:
            raise RuntimeError("Full audio download produced no output file")
        return Path(new_files[0])

    def search_and_download_spoken_word(
        self,
        query: str,
        output_dir: Path,
        clip_spec: ClipSpec | None = None,
        max_candidates: int = 5,
        whisper_model: str = "base",
        **download_kwargs,
    ) -> SpokenWordResult:
        """Search multiple candidates for captions containing the query word.

        Probes up to max_candidates videos for captions. Downloads from the
        first match at the caption timestamp. If no captions match, tries
        local STT via faster-whisper on the first result. Falls back to a
        midpoint clip if both methods fail.
        """
        from dodgylegally.transcript import probe_captions, transcribe_and_find

        spec = clip_spec or DEFAULT_CLIP_SPEC
        results = self.search(query, max_results=max_candidates)
        if not results:
            raise RuntimeError(f"No results for '{query}'")

        # Phase 1: try captions (fast, no download needed)
        for i, result in enumerate(results):
            timestamp = probe_captions(result.url, query)
            if timestamp is not None:
                caption_spec = ClipSpec(
                    position=ClipPosition.TIMESTAMP,
                    duration_s=spec.duration_s,
                    timestamp_s=timestamp,
                )
                clip = self.download(
                    result, output_dir, clip_spec=caption_spec, **download_kwargs,
                )
                return SpokenWordResult(
                    clip=clip,
                    caption_found=True,
                    timestamp_s=timestamp,
                    candidates_probed=i + 1,
                    method="caption",
                )

        # Phase 2: try Whisper on first result (downloads full audio)
        import shutil
        import tempfile
        tmp_dir = tempfile.mkdtemp()
        try:
            full_audio = self._download_full_audio(results[0], Path(tmp_dir))
            span = transcribe_and_find(
                str(full_audio), query, model_size=whisper_model,
            )
            if span is not None:
                from pydub import AudioSegment
                from dodgylegally.process import trim_word_centered

                audio = AudioSegment.from_file(str(full_audio))
                trimmed = trim_word_centered(
                    audio, span.start_s, span.end_s, spec.duration_s,
                )

                output_dir = Path(output_dir)
                output_dir.mkdir(parents=True, exist_ok=True)
                out_name = full_audio.stem + "_spoken.wav"
                out_path = output_dir / out_name
                trimmed.export(str(out_path), format="wav")

                clip = DownloadedClip(
                    path=out_path,
                    source_result=results[0],
                    duration_ms=len(trimmed),
                    clip_spec=ClipSpec(
                        position=ClipPosition.TIMESTAMP,
                        duration_s=spec.duration_s,
                        timestamp_s=span.start_s,
                    ),
                )
                return SpokenWordResult(
                    clip=clip,
                    caption_found=False,
                    timestamp_s=span.start_s,
                    candidates_probed=len(results),
                    method="whisper",
                )
        except Exception:
            logger.debug("Whisper fallback failed for '%s'", query, exc_info=True)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

        # Phase 3: final fallback — midpoint clip
        clip = self.download(
            results[0], output_dir, clip_spec=spec, **download_kwargs,
        )
        return SpokenWordResult(
            clip=clip,
            caption_found=False,
            candidates_probed=len(results),
            method="fallback",
        )

    def dry_run(self, query: str) -> dict:
        """Return what would be searched/downloaded, without network calls."""
        return {
            "source": "youtube",
            "phrase": query,
            "url": f'ytsearch1:"{query}"',
            "action": "would search YouTube and download 1s clip from midpoint",
        }
