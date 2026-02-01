"""Tests for the source abstraction layer and YouTubeSource."""

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


def test_search_result_dataclass():
    """SearchResult holds source, title, url, duration, metadata."""
    from dodgylegally.sources.base import SearchResult

    r = SearchResult(
        source="youtube",
        title="Rain Sounds",
        url="https://youtube.com/watch?v=abc",
        duration_s=120.0,
        metadata={"query": "rain thunder"},
    )
    assert r.source == "youtube"
    assert r.duration_s == 120.0
    assert r.metadata["query"] == "rain thunder"


def test_downloaded_clip_dataclass():
    """DownloadedClip holds path, source_result, duration_ms."""
    from dodgylegally.sources.base import SearchResult, DownloadedClip

    result = SearchResult("youtube", "test", "http://x", 10.0, {})
    clip = DownloadedClip(
        path=Path("/tmp/test.wav"),
        source_result=result,
        duration_ms=1000,
    )
    assert clip.path == Path("/tmp/test.wav")
    assert clip.source_result.source == "youtube"


def test_get_source_returns_youtube_by_default():
    """get_source('youtube') returns a YouTubeSource instance."""
    from dodgylegally.sources import get_source

    source = get_source("youtube")
    assert source.name == "youtube"


def test_get_source_unknown_raises():
    """get_source with unknown name raises KeyError."""
    from dodgylegally.sources import get_source

    with pytest.raises(KeyError, match="unknown_source"):
        get_source("unknown_source")


def test_list_sources_includes_youtube():
    """list_sources returns at least 'youtube'."""
    from dodgylegally.sources import list_sources

    names = list_sources()
    assert "youtube" in names


def test_youtube_source_has_name():
    """YouTubeSource.name is 'youtube'."""
    from dodgylegally.sources.youtube import YouTubeSource

    source = YouTubeSource()
    assert source.name == "youtube"


@patch("dodgylegally.sources.youtube.YoutubeDL")
def test_youtube_source_search(mock_ydl_class):
    """YouTubeSource.search returns SearchResult list."""
    from dodgylegally.sources.youtube import YouTubeSource

    mock_ydl = MagicMock()
    mock_ydl.extract_info.return_value = {
        "entries": [{
            "title": "Rain Video",
            "webpage_url": "https://youtube.com/watch?v=abc",
            "duration": 60,
        }],
    }
    mock_ydl_class.return_value.__enter__ = MagicMock(return_value=mock_ydl)
    mock_ydl_class.return_value.__exit__ = MagicMock(return_value=False)

    source = YouTubeSource()
    results = source.search("rain thunder")
    assert len(results) == 1
    assert results[0].source == "youtube"
    assert results[0].title == "Rain Video"


@patch("dodgylegally.sources.youtube.YoutubeDL")
def test_youtube_source_download(mock_ydl_class, tmp_path):
    """YouTubeSource.download creates a WAV file and returns DownloadedClip."""
    from dodgylegally.sources.base import SearchResult
    from dodgylegally.sources.youtube import YouTubeSource
    from pydub.generators import WhiteNoise

    def fake_download(urls):
        wav = tmp_path / "test-abc.wav"
        WhiteNoise().to_audio_segment(duration=1000).export(str(wav), format="wav")

    mock_ydl = MagicMock()
    mock_ydl.download.side_effect = fake_download
    mock_ydl_class.return_value.__enter__ = MagicMock(return_value=mock_ydl)
    mock_ydl_class.return_value.__exit__ = MagicMock(return_value=False)

    source = YouTubeSource()
    result = SearchResult("youtube", "Test", "https://youtube.com/watch?v=abc", 60.0, {})
    clip = source.download(result, tmp_path)
    assert clip.path.suffix == ".wav"
    assert clip.source_result.source == "youtube"


def test_youtube_source_dry_run():
    """YouTubeSource.dry_run returns info dict without network calls."""
    from dodgylegally.sources.youtube import YouTubeSource

    source = YouTubeSource()
    info = source.dry_run("rain thunder")
    assert info["phrase"] == "rain thunder"
    assert "ytsearch" in info["url"]


@patch("dodgylegally.sources.youtube.YoutubeDL")
def test_youtube_source_download_with_clip_spec(mock_ydl_class, tmp_path):
    """YouTubeSource.download passes clip_spec to DownloadRangeFunc."""
    from dodgylegally.sources.base import SearchResult
    from dodgylegally.sources.youtube import YouTubeSource
    from dodgylegally.clip import ClipSpec, ClipPosition
    from pydub.generators import WhiteNoise

    def fake_download(urls):
        wav = tmp_path / "test-abc.wav"
        WhiteNoise().to_audio_segment(duration=2000).export(str(wav), format="wav")

    mock_ydl = MagicMock()
    mock_ydl.download.side_effect = fake_download
    mock_ydl_class.return_value.__enter__ = MagicMock(return_value=mock_ydl)
    mock_ydl_class.return_value.__exit__ = MagicMock(return_value=False)

    spec = ClipSpec(position=ClipPosition.RANDOM, duration_s=2.0)
    source = YouTubeSource()
    result = SearchResult("youtube", "Test", "https://youtube.com/watch?v=abc", 60.0, {})
    clip = source.download(result, tmp_path, clip_spec=spec)
    assert clip.duration_ms == 2000
    assert clip.clip_spec is spec


@patch("dodgylegally.sources.youtube.YoutubeDL")
def test_youtube_source_download_default_clip_spec(mock_ydl_class, tmp_path):
    """YouTubeSource.download defaults to midpoint 1s when no clip_spec."""
    from dodgylegally.sources.base import SearchResult
    from dodgylegally.sources.youtube import YouTubeSource
    from dodgylegally.clip import ClipPosition
    from pydub.generators import WhiteNoise

    def fake_download(urls):
        wav = tmp_path / "test-abc.wav"
        WhiteNoise().to_audio_segment(duration=1000).export(str(wav), format="wav")

    mock_ydl = MagicMock()
    mock_ydl.download.side_effect = fake_download
    mock_ydl_class.return_value.__enter__ = MagicMock(return_value=mock_ydl)
    mock_ydl_class.return_value.__exit__ = MagicMock(return_value=False)

    source = YouTubeSource()
    result = SearchResult("youtube", "Test", "https://youtube.com/watch?v=abc", 60.0, {})
    clip = source.download(result, tmp_path)
    assert clip.duration_ms == 1000
    assert clip.clip_spec.position is ClipPosition.MIDPOINT


def test_cli_download_accepts_source_flag():
    """CLI download subcommand accepts --source flag."""
    from click.testing import CliRunner
    from dodgylegally.cli import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["download", "--source", "youtube", "--dry-run", "--phrase", "test"])
    assert result.exit_code == 0
