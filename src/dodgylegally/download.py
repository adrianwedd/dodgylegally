import glob
import os

from yt_dlp import YoutubeDL


class _DownloadRangeFunc:
    """Extract 1-second segment from video midpoint."""

    def __call__(self, info_dict, ydl):
        duration = info_dict.get("duration")
        timestamp = (duration / 2) if duration else 0
        yield {"start_time": timestamp, "end_time": timestamp + 1}


def make_download_options(phrase: str, output_dir: str) -> dict:
    """Build yt-dlp options dict."""
    safe_phrase = "".join(x for x in phrase if x.isalnum() or x in "._- ").strip()
    if not safe_phrase:
        safe_phrase = "download"
    return {
        "format": "bestaudio/best",
        "paths": {"home": output_dir},
        "outtmpl": {"default": f"{safe_phrase}-%(id)s.%(ext)s"},
        "download_ranges": _DownloadRangeFunc(),
        "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "wav"}],
        "quiet": True,
        "no_warnings": True,
    }


def _find_new_files(directory: str, before: set[str]) -> list[str]:
    """Return WAV files in directory that weren't in the before set."""
    after = set(glob.glob(os.path.join(directory, "*.wav")))
    return list(after - before)


def download_audio(phrase: str, output_dir: str) -> list[str]:
    """Download 1s audio clip from YouTube search for phrase. Returns list of downloaded file paths."""
    os.makedirs(output_dir, exist_ok=True)
    before = set(glob.glob(os.path.join(output_dir, "*.wav")))
    url = f'ytsearch1:"{phrase}"'
    opts = make_download_options(phrase, output_dir)
    with YoutubeDL(opts) as ydl:
        ydl.download([url])
    return _find_new_files(output_dir, before)


def download_url(url: str, output_dir: str) -> list[str]:
    """Download 1s audio clip from a specific YouTube URL. Returns list of downloaded file paths."""
    os.makedirs(output_dir, exist_ok=True)
    before = set(glob.glob(os.path.join(output_dir, "*.wav")))
    opts = make_download_options("url_download", output_dir)
    with YoutubeDL(opts) as ydl:
        ydl.download([url])
    return _find_new_files(output_dir, before)
