from __future__ import annotations

import glob
import os
import time

from yt_dlp import YoutubeDL

from dodgylegally.clip import ClipSpec, DownloadRangeFunc, DEFAULT_CLIP_SPEC


class DownloadSkipError(Exception):
    """Raised when a download should be skipped (e.g., no results found)."""


_SKIP_PATTERNS = [
    "no video results",
    "no suitable video",
    "is not a valid url",
    "unable to extract",
    "video unavailable",
]


def _is_skip_error(error: Exception) -> bool:
    """Check if an error indicates the download should be skipped (not retried)."""
    msg = str(error).lower()
    return any(pattern in msg for pattern in _SKIP_PATTERNS)


def make_download_options(
    phrase: str,
    output_dir: str,
    clip_spec: ClipSpec | None = None,
) -> dict:
    """Build yt-dlp options dict."""
    spec = clip_spec or DEFAULT_CLIP_SPEC
    safe_phrase = "".join(x for x in phrase if x.isalnum() or x in "._- ").strip()
    if not safe_phrase:
        safe_phrase = "download"
    return {
        "format": "bestaudio/best",
        "paths": {"home": output_dir},
        "outtmpl": {"default": f"{safe_phrase}-%(id)s.%(ext)s"},
        "download_ranges": DownloadRangeFunc(spec=spec),
        "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "wav"}],
        "quiet": True,
        "no_warnings": True,
    }


def _find_new_files(directory: str, before: set[str]) -> list[str]:
    """Return WAV files in directory that weren't in the before set."""
    after = set(glob.glob(os.path.join(directory, "*.wav")))
    return list(after - before)


def download_audio(
    phrase: str,
    output_dir: str,
    max_retries: int = 3,
    delay: float = 0,
    dry_run: bool = False,
    clip_spec: ClipSpec | None = None,
) -> list[str]:
    """Download audio clip from YouTube search for phrase.

    Returns list of downloaded file paths.
    Retries transient errors up to max_retries with exponential backoff.
    Raises DownloadSkipError for non-retryable errors (no results, etc.).
    In dry_run mode, returns empty list without making network calls.
    """
    if dry_run:
        return []

    os.makedirs(output_dir, exist_ok=True)
    before = set(glob.glob(os.path.join(output_dir, "*.wav")))
    url = f'ytsearch1:"{phrase}"'
    opts = make_download_options(phrase, output_dir, clip_spec=clip_spec)

    last_error = None
    for attempt in range(max_retries):
        try:
            with YoutubeDL(opts) as ydl:
                ydl.download([url])
            return _find_new_files(output_dir, before)
        except Exception as e:
            if _is_skip_error(e):
                raise DownloadSkipError(str(e)) from e
            last_error = e
            if attempt < max_retries - 1:
                backoff = delay + (2 ** attempt)
                time.sleep(backoff)

    raise last_error


def download_url(
    url: str,
    output_dir: str,
    clip_spec: ClipSpec | None = None,
) -> list[str]:
    """Download audio clip from a specific YouTube URL. Returns list of downloaded file paths."""
    os.makedirs(output_dir, exist_ok=True)
    before = set(glob.glob(os.path.join(output_dir, "*.wav")))
    opts = make_download_options("url_download", output_dir, clip_spec=clip_spec)
    with YoutubeDL(opts) as ydl:
        ydl.download([url])
    return _find_new_files(output_dir, before)


def download_audio_dry_run(phrase: str) -> dict:
    """Return info about what would be downloaded without making network calls."""
    return {
        "phrase": phrase,
        "url": f'ytsearch1:"{phrase}"',
        "action": "would search and download 1s clip",
    }
