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


@patch("dodgylegally.transcript.probe_captions")
@patch("dodgylegally.sources.youtube.YoutubeDL")
def test_spoken_word_found_on_first_result(mock_ydl_class, mock_probe, tmp_path):
    """search_and_download_spoken_word finds caption on first candidate."""
    from dodgylegally.sources.base import SearchResult
    from dodgylegally.sources.youtube import YouTubeSource
    from dodgylegally.clip import ClipSpec, ClipPosition
    from pydub.generators import WhiteNoise

    mock_probe.return_value = 5.0

    # Mock search
    mock_ydl_search = MagicMock()
    mock_ydl_search.extract_info.return_value = {
        "entries": [
            {"title": "Video 1", "webpage_url": "https://youtube.com/watch?v=a", "duration": 60},
            {"title": "Video 2", "webpage_url": "https://youtube.com/watch?v=b", "duration": 60},
        ],
    }

    # Mock download
    mock_ydl_dl = MagicMock()
    def fake_download(urls):
        wav = tmp_path / "test-a.wav"
        WhiteNoise().to_audio_segment(duration=1500).export(str(wav), format="wav")
    mock_ydl_dl.download.side_effect = fake_download

    call_count = [0]
    def ydl_enter(self_mock):
        call_count[0] += 1
        if call_count[0] == 1:
            return mock_ydl_search
        return mock_ydl_dl
    mock_ydl_class.return_value.__enter__ = ydl_enter
    mock_ydl_class.return_value.__exit__ = MagicMock(return_value=False)

    source = YouTubeSource()
    spec = ClipSpec(position=ClipPosition.MIDPOINT, duration_s=1.5)
    sw = source.search_and_download_spoken_word("confetti", tmp_path, clip_spec=spec)

    assert sw.caption_found is True
    assert sw.timestamp_s == 5.0
    assert sw.candidates_probed == 1
    assert sw.clip.path.suffix == ".wav"
    mock_probe.assert_called_once_with("https://youtube.com/watch?v=a", "confetti")


@patch("dodgylegally.transcript.probe_captions")
@patch("dodgylegally.sources.youtube.YoutubeDL")
def test_spoken_word_found_on_third_result(mock_ydl_class, mock_probe, tmp_path):
    """search_and_download_spoken_word finds caption on third candidate after two misses."""
    from dodgylegally.sources.youtube import YouTubeSource
    from dodgylegally.clip import ClipSpec, ClipPosition
    from pydub.generators import WhiteNoise

    mock_probe.side_effect = [None, None, 12.5]

    mock_ydl_search = MagicMock()
    mock_ydl_search.extract_info.return_value = {
        "entries": [
            {"title": f"Video {i}", "webpage_url": f"https://youtube.com/watch?v={i}", "duration": 60}
            for i in range(5)
        ],
    }

    mock_ydl_dl = MagicMock()
    def fake_download(urls):
        wav = tmp_path / "test-2.wav"
        if not wav.exists():
            WhiteNoise().to_audio_segment(duration=1500).export(str(wav), format="wav")
    mock_ydl_dl.download.side_effect = fake_download

    call_count = [0]
    def ydl_enter(self_mock):
        call_count[0] += 1
        if call_count[0] == 1:
            return mock_ydl_search
        return mock_ydl_dl
    mock_ydl_class.return_value.__enter__ = ydl_enter
    mock_ydl_class.return_value.__exit__ = MagicMock(return_value=False)

    source = YouTubeSource()
    spec = ClipSpec(position=ClipPosition.MIDPOINT, duration_s=1.5)
    sw = source.search_and_download_spoken_word("confetti", tmp_path, clip_spec=spec)

    assert sw.caption_found is True
    assert sw.timestamp_s == 12.5
    assert sw.candidates_probed == 3
    assert mock_probe.call_count == 3


@patch("dodgylegally.transcript.transcribe_and_find", return_value=None)
@patch("dodgylegally.transcript.probe_captions")
@patch("dodgylegally.sources.youtube.YoutubeDL")
def test_spoken_word_not_found_falls_back(mock_ydl_class, mock_probe, mock_transcribe, tmp_path):
    """search_and_download_spoken_word falls back when no captions match."""
    from dodgylegally.sources.youtube import YouTubeSource
    from dodgylegally.clip import ClipSpec, ClipPosition
    from pydub.generators import WhiteNoise

    mock_probe.return_value = None

    mock_ydl_search = MagicMock()
    mock_ydl_search.extract_info.return_value = {
        "entries": [
            {"title": f"Video {i}", "webpage_url": f"https://youtube.com/watch?v={i}", "duration": 60}
            for i in range(3)
        ],
    }

    mock_ydl_dl = MagicMock()
    def fake_download(urls):
        wav = tmp_path / "test-0.wav"
        if not wav.exists():
            WhiteNoise().to_audio_segment(duration=1500).export(str(wav), format="wav")
    mock_ydl_dl.download.side_effect = fake_download

    call_count = [0]
    def ydl_enter(self_mock):
        call_count[0] += 1
        if call_count[0] == 1:
            return mock_ydl_search
        return mock_ydl_dl
    mock_ydl_class.return_value.__enter__ = ydl_enter
    mock_ydl_class.return_value.__exit__ = MagicMock(return_value=False)

    source = YouTubeSource()
    spec = ClipSpec(position=ClipPosition.MIDPOINT, duration_s=1.5)

    def mock_download_full(result, tmp_dir):
        wav = tmp_dir / "confetti-0.wav"
        WhiteNoise().to_audio_segment(duration=30000).export(str(wav), format="wav")
        return wav
    source._download_full_audio = mock_download_full

    sw = source.search_and_download_spoken_word("confetti", tmp_path, clip_spec=spec, max_candidates=3)

    assert sw.caption_found is False
    assert sw.timestamp_s is None
    assert sw.candidates_probed == 3
    assert sw.method == "fallback"
    assert mock_probe.call_count == 3


@patch("dodgylegally.sources.youtube.YoutubeDL")
def test_spoken_word_no_results_raises(mock_ydl_class):
    """search_and_download_spoken_word raises when search returns no results."""
    from dodgylegally.sources.youtube import YouTubeSource
    from pathlib import Path

    mock_ydl = MagicMock()
    mock_ydl.extract_info.return_value = {"entries": []}
    mock_ydl_class.return_value.__enter__ = MagicMock(return_value=mock_ydl)
    mock_ydl_class.return_value.__exit__ = MagicMock(return_value=False)

    source = YouTubeSource()
    with pytest.raises(RuntimeError, match="No results for 'confetti'"):
        source.search_and_download_spoken_word("confetti", Path("/tmp/test"))


@patch("dodgylegally.transcript.probe_captions")
@patch("dodgylegally.sources.youtube.YoutubeDL")
def test_spoken_word_caption_hit_sets_method_caption(mock_ydl_class, mock_probe, tmp_path):
    """search_and_download_spoken_word sets method='caption' on caption hit."""
    from dodgylegally.sources.youtube import YouTubeSource
    from dodgylegally.clip import ClipSpec, ClipPosition
    from pydub.generators import WhiteNoise

    mock_probe.return_value = 5.0

    mock_ydl_search = MagicMock()
    mock_ydl_search.extract_info.return_value = {
        "entries": [
            {"title": "Video 1", "webpage_url": "https://youtube.com/watch?v=a", "duration": 60},
        ],
    }

    mock_ydl_dl = MagicMock()
    def fake_download(urls):
        wav = tmp_path / "test-a.wav"
        WhiteNoise().to_audio_segment(duration=1500).export(str(wav), format="wav")
    mock_ydl_dl.download.side_effect = fake_download

    call_count = [0]
    def ydl_enter(self_mock):
        call_count[0] += 1
        if call_count[0] == 1:
            return mock_ydl_search
        return mock_ydl_dl
    mock_ydl_class.return_value.__enter__ = ydl_enter
    mock_ydl_class.return_value.__exit__ = MagicMock(return_value=False)

    source = YouTubeSource()
    spec = ClipSpec(position=ClipPosition.MIDPOINT, duration_s=1.5)
    sw = source.search_and_download_spoken_word("confetti", tmp_path, clip_spec=spec)

    assert sw.method == "caption"
    assert sw.caption_found is True
    assert sw.timestamp_s == 5.0


@patch("dodgylegally.transcript.transcribe_and_find")
@patch("dodgylegally.transcript.probe_captions")
@patch("dodgylegally.sources.youtube.YoutubeDL")
def test_spoken_word_whisper_hit(mock_ydl_class, mock_probe, mock_transcribe, tmp_path):
    """search_and_download_spoken_word falls back to Whisper and reports method='whisper'."""
    from dodgylegally.sources.youtube import YouTubeSource
    from dodgylegally.clip import ClipSpec, ClipPosition
    from dodgylegally.transcript import WordSpan
    from pydub.generators import WhiteNoise

    mock_probe.return_value = None
    mock_transcribe.return_value = WordSpan(start_s=8.3, end_s=8.9)

    mock_ydl_search = MagicMock()
    mock_ydl_search.extract_info.return_value = {
        "entries": [
            {"title": "Video 1", "webpage_url": "https://youtube.com/watch?v=a", "duration": 60},
        ],
    }

    # _download_full_audio and download both use YoutubeDL
    mock_ydl_dl = MagicMock()
    def fake_download(urls):
        # Detect if this is for full audio (tmp dir) or clip download
        wav_dir = tmp_path
        for f in tmp_path.rglob("*.wav"):
            return  # already created
        wav = tmp_path / "confetti-a.wav"
        WhiteNoise().to_audio_segment(duration=30000).export(str(wav), format="wav")
    mock_ydl_dl.download.side_effect = fake_download

    call_count = [0]
    def ydl_enter(self_mock):
        call_count[0] += 1
        if call_count[0] == 1:
            return mock_ydl_search
        return mock_ydl_dl
    mock_ydl_class.return_value.__enter__ = ydl_enter
    mock_ydl_class.return_value.__exit__ = MagicMock(return_value=False)

    source = YouTubeSource()
    spec = ClipSpec(position=ClipPosition.MIDPOINT, duration_s=1.5)

    # We need to mock _download_full_audio to write into the tmp_dir it receives
    original_download_full = source._download_full_audio
    def mock_download_full(result, tmp_dir):
        wav = tmp_dir / "confetti-a.wav"
        WhiteNoise().to_audio_segment(duration=30000).export(str(wav), format="wav")
        return wav
    source._download_full_audio = mock_download_full

    sw = source.search_and_download_spoken_word(
        "confetti", tmp_path, clip_spec=spec, whisper_model="tiny",
    )

    assert sw.method == "whisper"
    assert sw.caption_found is False
    assert sw.timestamp_s == 8.3
    assert sw.clip.path.exists()
    # transcribe_and_find is called with the temp dir path (not tmp_path)
    mock_transcribe.assert_called_once()
    call_args = mock_transcribe.call_args
    assert call_args[0][1] == "confetti"
    assert call_args[1]["model_size"] == "tiny"


@patch("dodgylegally.transcript.transcribe_and_find")
@patch("dodgylegally.transcript.probe_captions")
@patch("dodgylegally.sources.youtube.YoutubeDL")
def test_spoken_word_whisper_miss_falls_back(mock_ydl_class, mock_probe, mock_transcribe, tmp_path):
    """search_and_download_spoken_word falls to midpoint when Whisper finds nothing."""
    from dodgylegally.sources.youtube import YouTubeSource
    from dodgylegally.clip import ClipSpec, ClipPosition
    from pydub.generators import WhiteNoise

    mock_probe.return_value = None
    mock_transcribe.return_value = None

    mock_ydl_search = MagicMock()
    mock_ydl_search.extract_info.return_value = {
        "entries": [
            {"title": "Video 1", "webpage_url": "https://youtube.com/watch?v=a", "duration": 60},
        ],
    }

    mock_ydl_dl = MagicMock()
    def fake_download(urls):
        wav = tmp_path / "confetti-a.wav"
        if not wav.exists():
            WhiteNoise().to_audio_segment(duration=1500).export(str(wav), format="wav")
    mock_ydl_dl.download.side_effect = fake_download

    call_count = [0]
    def ydl_enter(self_mock):
        call_count[0] += 1
        if call_count[0] == 1:
            return mock_ydl_search
        return mock_ydl_dl
    mock_ydl_class.return_value.__enter__ = ydl_enter
    mock_ydl_class.return_value.__exit__ = MagicMock(return_value=False)

    source = YouTubeSource()
    spec = ClipSpec(position=ClipPosition.MIDPOINT, duration_s=1.5)

    def mock_download_full(result, tmp_dir):
        wav = tmp_dir / "confetti-a.wav"
        WhiteNoise().to_audio_segment(duration=30000).export(str(wav), format="wav")
        return wav
    source._download_full_audio = mock_download_full

    sw = source.search_and_download_spoken_word("confetti", tmp_path, clip_spec=spec)

    assert sw.method == "fallback"
    assert sw.caption_found is False
    assert sw.timestamp_s is None


@patch("dodgylegally.transcript.transcribe_and_find")
@patch("dodgylegally.transcript.probe_captions")
@patch("dodgylegally.sources.youtube.YoutubeDL")
def test_spoken_word_whisper_import_fails_gracefully(mock_ydl_class, mock_probe, mock_transcribe, tmp_path):
    """search_and_download_spoken_word falls back when faster-whisper is unavailable."""
    from dodgylegally.sources.youtube import YouTubeSource
    from dodgylegally.clip import ClipSpec, ClipPosition
    from pydub.generators import WhiteNoise

    mock_probe.return_value = None
    # transcribe_and_find returns None when faster-whisper isn't installed
    mock_transcribe.return_value = None

    mock_ydl_search = MagicMock()
    mock_ydl_search.extract_info.return_value = {
        "entries": [
            {"title": "Video 1", "webpage_url": "https://youtube.com/watch?v=a", "duration": 60},
        ],
    }

    mock_ydl_dl = MagicMock()
    def fake_download(urls):
        wav = tmp_path / "confetti-a.wav"
        if not wav.exists():
            WhiteNoise().to_audio_segment(duration=1500).export(str(wav), format="wav")
    mock_ydl_dl.download.side_effect = fake_download

    call_count = [0]
    def ydl_enter(self_mock):
        call_count[0] += 1
        if call_count[0] == 1:
            return mock_ydl_search
        return mock_ydl_dl
    mock_ydl_class.return_value.__enter__ = ydl_enter
    mock_ydl_class.return_value.__exit__ = MagicMock(return_value=False)

    source = YouTubeSource()
    spec = ClipSpec(position=ClipPosition.MIDPOINT, duration_s=1.5)

    def mock_download_full(result, tmp_dir):
        wav = tmp_dir / "confetti-a.wav"
        WhiteNoise().to_audio_segment(duration=30000).export(str(wav), format="wav")
        return wav
    source._download_full_audio = mock_download_full

    sw = source.search_and_download_spoken_word("confetti", tmp_path, clip_spec=spec)

    assert sw.method == "fallback"
    assert sw.caption_found is False
