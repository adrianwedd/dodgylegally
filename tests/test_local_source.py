"""Tests for the local file audio source."""

from pathlib import Path

import pytest
from pydub.generators import WhiteNoise


def _make_wav(path: Path, duration_ms: int = 2000) -> Path:
    """Helper: create a WAV file with white noise."""
    path.parent.mkdir(parents=True, exist_ok=True)
    WhiteNoise().to_audio_segment(duration=duration_ms).export(str(path), format="wav")
    return path


def test_local_source_has_name():
    from dodgylegally.sources.local import LocalSource
    assert LocalSource().name == "local"


def test_local_source_registered():
    from dodgylegally.sources import get_source
    source = get_source("local")
    assert source.name == "local"


def test_local_source_search_finds_wav_files(tmp_path):
    """search returns SearchResults for WAV files in the directory."""
    from dodgylegally.sources.local import LocalSource

    _make_wav(tmp_path / "one.wav")
    _make_wav(tmp_path / "two.wav")
    _make_wav(tmp_path / "three.mp3", 1000)  # non-wav, should still match

    source = LocalSource(base_path=tmp_path)
    results = source.search("*", max_results=10)
    # Should find at least the .wav files
    assert len(results) >= 2
    assert all(r.source == "local" for r in results)


def test_local_source_search_respects_max_results(tmp_path):
    """search returns at most max_results items."""
    from dodgylegally.sources.local import LocalSource

    for i in range(5):
        _make_wav(tmp_path / f"file{i}.wav")

    source = LocalSource(base_path=tmp_path)
    results = source.search("*", max_results=2)
    assert len(results) == 2


def test_local_source_download_extracts_clip(tmp_path):
    """download extracts a 1-second clip from a random position."""
    from dodgylegally.sources.local import LocalSource
    from dodgylegally.sources.base import SearchResult

    source_file = _make_wav(tmp_path / "source" / "long.wav", duration_ms=5000)
    output_dir = tmp_path / "output"

    source = LocalSource(base_path=tmp_path / "source")
    result = SearchResult("local", "long.wav", str(source_file), 5.0, {})
    clip = source.download(result, output_dir)

    assert clip.path.exists()
    assert clip.path.suffix == ".wav"
    assert clip.duration_ms == 1000
    assert clip.source_result.source == "local"


def test_local_source_download_short_file_gets_full_duration(tmp_path):
    """Files shorter than 1 second are returned in full."""
    from dodgylegally.sources.local import LocalSource
    from dodgylegally.sources.base import SearchResult

    source_file = _make_wav(tmp_path / "source" / "short.wav", duration_ms=500)
    output_dir = tmp_path / "output"

    source = LocalSource(base_path=tmp_path / "source")
    result = SearchResult("local", "short.wav", str(source_file), 0.5, {})
    clip = source.download(result, output_dir)

    assert clip.path.exists()
    assert clip.duration_ms <= 500


def test_local_source_dry_run():
    """dry_run returns info dict."""
    from dodgylegally.sources.local import LocalSource

    source = LocalSource(base_path=Path("/fake"))
    info = source.dry_run("*.wav")
    assert info["source"] == "local"
    assert "phrase" in info


def test_local_source_search_empty_dir(tmp_path):
    """search on empty directory returns empty list."""
    from dodgylegally.sources.local import LocalSource

    source = LocalSource(base_path=tmp_path)
    results = source.search("*")
    assert results == []
