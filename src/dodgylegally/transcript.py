"""Fetch and parse YouTube captions for spoken-word timestamp extraction."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from urllib.request import urlopen

from yt_dlp import YoutubeDL

logger = logging.getLogger(__name__)

_TIMESTAMP_RE = re.compile(
    r"(\d{1,2}:)?(\d{2}):(\d{2})\.(\d{3})\s*-->\s*(\d{1,2}:)?(\d{2}):(\d{2})\.(\d{3})"
)
_HTML_TAG_RE = re.compile(r"<[^>]+>")


@dataclass
class CaptionSegment:
    """A single caption cue with start/end times and text."""

    start_s: float
    end_s: float
    text: str


@dataclass
class WordSpan:
    """Start and end timestamps of a word or phrase in audio."""

    start_s: float
    end_s: float


def _parse_timestamp(hours: str | None, minutes: str, seconds: str, millis: str) -> float:
    """Convert VTT timestamp components to seconds."""
    h = int(hours.rstrip(":")) if hours else 0
    return h * 3600 + int(minutes) * 60 + int(seconds) + int(millis) / 1000


def parse_vtt(vtt_text: str) -> list[CaptionSegment]:
    """Parse WebVTT text into a list of CaptionSegments.

    Handles HTML tags (YouTube auto-captions use <c> tags),
    multi-line cues, optional cue identifiers, and positioning metadata.
    """
    segments: list[CaptionSegment] = []
    blocks = re.split(r"\n\n+", vtt_text.strip())

    for block in blocks:
        lines = block.strip().splitlines()
        timestamp_idx = None
        for i, line in enumerate(lines):
            if _TIMESTAMP_RE.search(line):
                timestamp_idx = i
                break

        if timestamp_idx is None:
            continue

        m = _TIMESTAMP_RE.search(lines[timestamp_idx])
        if not m:
            continue

        start_s = _parse_timestamp(m.group(1), m.group(2), m.group(3), m.group(4))
        end_s = _parse_timestamp(m.group(5), m.group(6), m.group(7), m.group(8))

        text_lines = lines[timestamp_idx + 1 :]
        raw_text = " ".join(text_lines)
        clean_text = _HTML_TAG_RE.sub("", raw_text).strip()
        # Collapse multiple spaces
        clean_text = re.sub(r"\s+", " ", clean_text)

        if clean_text:
            segments.append(CaptionSegment(start_s=start_s, end_s=end_s, text=clean_text))

    return segments


def find_word_timestamp(segments: list[CaptionSegment], word: str) -> float | None:
    """Find the timestamp of the first segment containing the word.

    Uses word-boundary matching to avoid partial matches.
    Case-insensitive. For multi-word queries, searches each word
    individually and returns the earliest match.

    Returns the start_s of the matching segment, or None.
    """
    if not segments:
        return None

    words = word.strip().split()
    best_time: float | None = None

    for w in words:
        pattern = re.compile(r"\b" + re.escape(w) + r"\b", re.IGNORECASE)
        for seg in segments:
            if pattern.search(seg.text):
                if best_time is None or seg.start_s < best_time:
                    best_time = seg.start_s
                break  # first occurrence of this word found

    return best_time


def _find_vtt_url(caption_list: list[dict]) -> str | None:
    """Find the VTT format URL from a list of caption format dicts."""
    for fmt in caption_list:
        if fmt.get("ext") == "vtt":
            return fmt.get("url")
    return None


def fetch_captions(
    video_url: str,
    lang: str = "en",
) -> list[CaptionSegment] | None:
    """Fetch and parse captions for a YouTube video.

    Tries manual subtitles first, then auto-generated captions.
    Returns parsed segments, or None if captions are unavailable.
    """
    try:
        opts = {"quiet": True, "no_warnings": True}
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
    except Exception:
        logger.debug("Failed to extract info for captions: %s", video_url)
        return None

    if not info:
        return None

    subtitles = info.get("subtitles", {})
    auto_captions = info.get("automatic_captions", {})

    # Prefer manual subs over auto-generated
    vtt_url = None
    if lang in subtitles:
        vtt_url = _find_vtt_url(subtitles[lang])
    if vtt_url is None and lang in auto_captions:
        vtt_url = _find_vtt_url(auto_captions[lang])

    if vtt_url is None:
        return None

    try:
        with urlopen(vtt_url) as resp:
            vtt_text = resp.read().decode("utf-8")
    except Exception:
        logger.debug("Failed to download VTT from %s", vtt_url)
        return None

    return parse_vtt(vtt_text)


def transcribe_and_find(
    audio_path: str,
    word: str,
    model_size: str = "base",
    model: object | None = None,
) -> WordSpan | None:
    """Transcribe audio with faster-whisper and find word timestamp.

    Returns a WordSpan with start/end times of the matched word or phrase,
    or None if the word is not found or whisper is unavailable.

    For multi-word queries, finds all query words within a 3-second window
    and returns a span covering the full sequence.

    If *model* is provided (a pre-loaded WhisperModel instance), it is
    used directly and *model_size* is ignored.  This avoids reloading the
    model on every call when processing many files.
    """
    if model is None:
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            logger.info("faster-whisper not installed, skipping STT")
            return None
        model = WhisperModel(model_size, compute_type="int8")

    segments_iter, _info = model.transcribe(audio_path, word_timestamps=True)

    query_words = word.strip().split()
    patterns = [
        re.compile(r"\b" + re.escape(qw) + r"\b", re.IGNORECASE)
        for qw in query_words
    ]

    # Collect all word objects across segments for multi-word matching
    all_words: list = []
    all_segments: list = []
    for segment in segments_iter:
        if segment.words:
            all_words.extend(segment.words)
        all_segments.append(segment)

    # Multi-word: find the sequence within a 3s window
    if len(query_words) > 1 and all_words:
        for i, w in enumerate(all_words):
            if patterns[0].search(w.word):
                # Try to find remaining words after this one within 3s
                matched = [w]
                pat_idx = 1
                for j in range(i + 1, len(all_words)):
                    if all_words[j].start - w.start > 3.0:
                        break
                    if pat_idx < len(patterns) and patterns[pat_idx].search(all_words[j].word):
                        matched.append(all_words[j])
                        pat_idx += 1
                        if pat_idx == len(patterns):
                            break
                if pat_idx == len(patterns):
                    return WordSpan(start_s=matched[0].start, end_s=matched[-1].end)

    # Single word: find in collected words
    if all_words:
        for w in all_words:
            if patterns[0].search(w.word):
                return WordSpan(start_s=w.start, end_s=w.end)

    # Segment-text fallback (no word-level data)
    for segment in all_segments:
        if not segment.words and patterns[0].search(segment.text):
            return WordSpan(start_s=segment.start, end_s=segment.start + 0.3)

    return None


def transcribe_and_find_all(
    audio_path: str,
    word: str,
    model_size: str = "base",
    model: object | None = None,
) -> list[WordSpan]:
    """Transcribe audio and return *all* occurrences of a word or phrase.

    Same matching logic as :func:`transcribe_and_find` but collects every
    match instead of returning at the first one.  Useful for extracting
    multiple clips from a single long recording.

    If *model* is provided, it is used directly (see :func:`transcribe_and_find`).
    """
    if model is None:
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            logger.info("faster-whisper not installed, skipping STT")
            return []
        model = WhisperModel(model_size, compute_type="int8")

    segments_iter, _info = model.transcribe(audio_path, word_timestamps=True)

    query_words = word.strip().split()
    patterns = [
        re.compile(r"\b" + re.escape(qw) + r"\b", re.IGNORECASE)
        for qw in query_words
    ]

    all_words: list = []
    all_segments: list = []
    for segment in segments_iter:
        if segment.words:
            all_words.extend(segment.words)
        all_segments.append(segment)

    results: list[WordSpan] = []

    if len(query_words) > 1 and all_words:
        used: set[int] = set()
        for i, w in enumerate(all_words):
            if i in used:
                continue
            if patterns[0].search(w.word):
                matched = [w]
                matched_idx = [i]
                pat_idx = 1
                for j in range(i + 1, len(all_words)):
                    if all_words[j].start - w.start > 3.0:
                        break
                    if pat_idx < len(patterns) and patterns[pat_idx].search(all_words[j].word):
                        matched.append(all_words[j])
                        matched_idx.append(j)
                        pat_idx += 1
                        if pat_idx == len(patterns):
                            break
                if pat_idx == len(patterns):
                    results.append(WordSpan(start_s=matched[0].start, end_s=matched[-1].end))
                    used.update(matched_idx)
    elif all_words:
        for w in all_words:
            if patterns[0].search(w.word):
                results.append(WordSpan(start_s=w.start, end_s=w.end))

    if not results:
        for segment in all_segments:
            if not segment.words and patterns[0].search(segment.text):
                results.append(WordSpan(start_s=segment.start, end_s=segment.start + 0.3))

    return results


def probe_captions(video_url: str, word: str, lang: str = "en") -> float | None:
    """Fetch captions for a video and search for a word.

    Convenience wrapper around fetch_captions + find_word_timestamp.
    Returns the timestamp in seconds, or None if captions are unavailable
    or the word is not found.
    """
    segments = fetch_captions(video_url, lang=lang)
    if segments is None:
        return None
    return find_word_timestamp(segments, word)
