"""Tests for download resilience: retry logic, delay, timeout, dry-run."""

import time
from unittest.mock import patch, MagicMock, call

import pytest


def test_download_audio_retries_on_transient_error(tmp_path):
    """download_audio retries on network errors up to max_retries."""
    from dodgylegally.download import download_audio

    call_count = 0

    def fake_download(urls):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise Exception("HTTP Error 500")
        # On 3rd attempt, create a file
        wav = tmp_path / "test-abc.wav"
        from pydub.generators import WhiteNoise
        WhiteNoise().to_audio_segment(duration=500).export(str(wav), format="wav")

    with patch("dodgylegally.download.YoutubeDL") as mock_ydl_class:
        mock_ydl = MagicMock()
        mock_ydl.download.side_effect = fake_download
        mock_ydl_class.return_value.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl_class.return_value.__exit__ = MagicMock(return_value=False)
        result = download_audio("test phrase", str(tmp_path), max_retries=3)
    assert call_count == 3
    assert len(result) == 1


def test_download_audio_gives_up_after_max_retries(tmp_path):
    """download_audio raises after max_retries exceeded."""
    from dodgylegally.download import download_audio

    with patch("dodgylegally.download.YoutubeDL") as mock_ydl_class:
        mock_ydl = MagicMock()
        mock_ydl.download.side_effect = Exception("HTTP Error 500")
        mock_ydl_class.return_value.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl_class.return_value.__exit__ = MagicMock(return_value=False)
        with pytest.raises(Exception, match="HTTP Error 500"):
            download_audio("test phrase", str(tmp_path), max_retries=2)


def test_download_audio_no_retry_on_not_found(tmp_path):
    """download_audio does not retry when video is not found."""
    from dodgylegally.download import download_audio, DownloadSkipError

    call_count = 0

    def fake_download(urls):
        nonlocal call_count
        call_count += 1
        raise Exception("no video results")

    with patch("dodgylegally.download.YoutubeDL") as mock_ydl_class:
        mock_ydl = MagicMock()
        mock_ydl.download.side_effect = fake_download
        mock_ydl_class.return_value.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl_class.return_value.__exit__ = MagicMock(return_value=False)
        with pytest.raises(DownloadSkipError):
            download_audio("nonexistent", str(tmp_path), max_retries=3)
    assert call_count == 1  # no retries for not-found


def test_download_audio_respects_delay(tmp_path):
    """download_audio waits delay seconds between retries."""
    from dodgylegally.download import download_audio

    call_count = 0

    def fake_download(urls):
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise Exception("HTTP Error 500")
        wav = tmp_path / "test-abc.wav"
        from pydub.generators import WhiteNoise
        WhiteNoise().to_audio_segment(duration=500).export(str(wav), format="wav")

    with patch("dodgylegally.download.YoutubeDL") as mock_ydl_class:
        mock_ydl = MagicMock()
        mock_ydl.download.side_effect = fake_download
        mock_ydl_class.return_value.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl_class.return_value.__exit__ = MagicMock(return_value=False)
        with patch("time.sleep") as mock_sleep:
            download_audio("test", str(tmp_path), max_retries=3, delay=2.0)
            mock_sleep.assert_called()
            # Sleep should have been called with a value >= delay
            assert any(c.args[0] >= 2.0 for c in mock_sleep.call_args_list)


def test_dry_run_download_returns_empty(tmp_path):
    """In dry-run mode, download_audio returns empty list without making network calls."""
    from dodgylegally.download import download_audio

    with patch("dodgylegally.download.YoutubeDL") as mock_ydl_class:
        result = download_audio("test phrase", str(tmp_path), dry_run=True)
        mock_ydl_class.assert_not_called()
    assert result == []


def test_dry_run_download_returns_phrase_info(tmp_path):
    """In dry-run mode, download_audio_dry_run returns search info."""
    from dodgylegally.download import download_audio_dry_run

    info = download_audio_dry_run("rain thunder")
    assert info["phrase"] == "rain thunder"
    assert "ytsearch" in info["url"]


def test_cli_download_has_delay_flag():
    """CLI download subcommand accepts --delay flag."""
    from click.testing import CliRunner
    from dodgylegally.cli import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["download", "--delay", "2", "--phrase", "test"])
    # Should not fail with "no such option"
    assert "no such option" not in (result.output or "")


def test_cli_download_has_dry_run_flag():
    """CLI download subcommand accepts --dry-run flag."""
    from click.testing import CliRunner
    from dodgylegally.cli import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["download", "--dry-run", "--phrase", "test"])
    assert result.exit_code == 0


def test_cli_run_has_delay_flag():
    """CLI run subcommand accepts --delay flag."""
    from click.testing import CliRunner
    from dodgylegally.cli import cli

    runner = CliRunner()
    # Just check the flag is accepted (will fail on ffmpeg but not on flag parsing)
    result = runner.invoke(cli, ["run", "--count", "1", "--delay", "1"])
    assert "no such option" not in (result.output or "")


def test_cli_run_has_dry_run_flag():
    """CLI run subcommand accepts --dry-run flag."""
    from click.testing import CliRunner
    from dodgylegally.cli import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["run", "--count", "1", "--dry-run"])
    assert result.exit_code == 0
