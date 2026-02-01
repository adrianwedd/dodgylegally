from unittest.mock import patch, MagicMock

from pydub.generators import WhiteNoise

from dodgylegally.download import download_audio, download_url, make_download_options


def test_make_download_options():
    opts = make_download_options("rain thunder", "/tmp/out")
    assert opts["format"] == "bestaudio/best"
    assert opts["paths"]["home"] == "/tmp/out"
    assert "rain thunder" in opts["outtmpl"]["default"]


def test_make_download_options_sanitizes_phrase():
    opts = make_download_options("bad/phrase!@#", "/tmp/out")
    template = opts["outtmpl"]["default"]
    assert "!" not in template
    assert "@" not in template
    assert "#" not in template


@patch("dodgylegally.download.YoutubeDL")
def test_download_audio_calls_ytdlp(mock_ydl_class, tmp_path):
    mock_ydl = MagicMock()
    mock_ydl_class.return_value.__enter__ = MagicMock(return_value=mock_ydl)
    mock_ydl_class.return_value.__exit__ = MagicMock(return_value=False)
    result = download_audio("test phrase", str(tmp_path))
    mock_ydl.download.assert_called_once()
    assert isinstance(result, list)


@patch("dodgylegally.download.YoutubeDL")
def test_download_url_calls_ytdlp(mock_ydl_class, tmp_path):
    mock_ydl = MagicMock()
    mock_ydl_class.return_value.__enter__ = MagicMock(return_value=mock_ydl)
    mock_ydl_class.return_value.__exit__ = MagicMock(return_value=False)
    result = download_url("https://youtube.com/watch?v=abc", str(tmp_path))
    mock_ydl.download.assert_called_once()
    assert isinstance(result, list)


@patch("dodgylegally.download.YoutubeDL")
def test_download_audio_returns_new_files(mock_ydl_class, tmp_path):
    """Simulate yt-dlp creating a file, verify it's returned."""
    def fake_download(urls):
        wav = tmp_path / "test-abc123.wav"
        WhiteNoise().to_audio_segment(duration=500).export(str(wav), format="wav")

    mock_ydl = MagicMock()
    mock_ydl.download.side_effect = fake_download
    mock_ydl_class.return_value.__enter__ = MagicMock(return_value=mock_ydl)
    mock_ydl_class.return_value.__exit__ = MagicMock(return_value=False)
    result = download_audio("test phrase", str(tmp_path))
    assert len(result) == 1
    assert result[0].endswith(".wav")


def test_download_range_func_end_time():
    """Verify that DownloadRangeFunc sets correct start/end times."""
    from dodgylegally.clip import DownloadRangeFunc
    func = DownloadRangeFunc()
    result = list(func({"duration": 100}, None))
    assert len(result) == 1
    assert result[0]["start_time"] == 49.5
    assert result[0]["end_time"] == 50.5


def test_make_download_options_empty_phrase_fallback():
    opts = make_download_options("!!!", "/tmp/out")
    template = opts["outtmpl"]["default"]
    assert "download" in template


def test_download_range_func_no_duration():
    """Verify fallback when duration is None."""
    from dodgylegally.clip import DownloadRangeFunc
    func = DownloadRangeFunc()
    result = list(func({"duration": None}, None))
    assert result[0]["start_time"] == 0
    assert result[0]["end_time"] == 1.0


def test_make_download_options_with_clip_spec():
    """make_download_options uses provided ClipSpec."""
    from dodgylegally.clip import ClipSpec, ClipPosition, DownloadRangeFunc
    spec = ClipSpec(position=ClipPosition.MIDPOINT, duration_s=2.5)
    opts = make_download_options("test", "/tmp/out", clip_spec=spec)
    range_func = opts["download_ranges"]
    assert isinstance(range_func, DownloadRangeFunc)
    result = list(range_func({"duration": 100}, None))
    assert result[0]["end_time"] - result[0]["start_time"] == 2.5


def test_make_download_options_default_clip_spec():
    """make_download_options uses default spec when none provided."""
    from dodgylegally.clip import DownloadRangeFunc
    opts = make_download_options("test", "/tmp/out")
    range_func = opts["download_ranges"]
    assert isinstance(range_func, DownloadRangeFunc)
    result = list(range_func({"duration": 60}, None))
    assert result[0]["end_time"] - result[0]["start_time"] == 1.0
