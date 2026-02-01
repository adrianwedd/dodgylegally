from click.testing import CliRunner

from dodgylegally.cli import cli, _parse_repeats
from dodgylegally.search import generate_phrases

import pytest


def test_search_subcommand():
    runner = CliRunner()
    result = runner.invoke(cli, ["search", "--count", "3"])
    assert result.exit_code == 0
    lines = result.output.strip().splitlines()
    assert len(lines) == 3


def test_search_with_phrase():
    runner = CliRunner()
    result = runner.invoke(cli, ["search", "--phrase", "rain thunder"])
    assert result.exit_code == 0
    assert "rain thunder" in result.output


def test_run_requires_count():
    runner = CliRunner()
    result = runner.invoke(cli, ["run"])
    assert result.exit_code != 0


def test_download_requires_input():
    runner = CliRunner()
    result = runner.invoke(cli, ["download"])
    assert result.exit_code != 0


def test_parse_repeats_valid():
    assert _parse_repeats("3-4") == (3, 4)
    assert _parse_repeats("1-1") == (1, 1)
    assert _parse_repeats("2-10") == (2, 10)


def test_parse_repeats_invalid():
    from click import BadParameter
    with pytest.raises(BadParameter):
        _parse_repeats("3")
    with pytest.raises(BadParameter):
        _parse_repeats("a-b")
    with pytest.raises(BadParameter):
        _parse_repeats("4-3")  # min > max
    with pytest.raises(BadParameter):
        _parse_repeats("0-4")  # min < 1
    with pytest.raises(BadParameter):
        _parse_repeats("3-4-5")


def test_combine_invalid_repeats():
    runner = CliRunner()
    result = runner.invoke(cli, ["combine", "--repeats", "bad"])
    assert result.exit_code != 0


def test_process_missing_input_dir(tmp_path):
    runner = CliRunner()
    result = runner.invoke(cli, ["-o", str(tmp_path / "out"), "process", "-i", str(tmp_path / "nonexistent")])
    assert result.exit_code != 0


def test_generate_phrases_too_few_words():
    with pytest.raises(ValueError, match="at least 2 words"):
        generate_phrases(["only_one"], 5)
    with pytest.raises(ValueError, match="at least 2 words"):
        generate_phrases([], 5)


def test_download_accepts_clip_position_flag():
    """CLI download subcommand accepts --clip-position flag."""
    runner = CliRunner()
    result = runner.invoke(cli, ["download", "--clip-position", "random", "--dry-run", "--phrase", "test"])
    assert result.exit_code == 0


def test_download_accepts_clip_duration_flag():
    """CLI download subcommand accepts --clip-duration flag."""
    runner = CliRunner()
    result = runner.invoke(cli, ["download", "--clip-duration", "2.5", "--dry-run", "--phrase", "test"])
    assert result.exit_code == 0


def test_download_accepts_timestamp_position():
    """CLI download subcommand accepts a numeric --clip-position."""
    runner = CliRunner()
    result = runner.invoke(cli, ["download", "--clip-position", "30.5", "--dry-run", "--phrase", "test"])
    assert result.exit_code == 0


def test_download_rejects_invalid_clip_position():
    """CLI download subcommand rejects invalid --clip-position values."""
    runner = CliRunner()
    result = runner.invoke(cli, ["download", "--clip-position", "bogus", "--dry-run", "--phrase", "test"])
    assert result.exit_code != 0


def test_run_accepts_clip_flags(tmp_path):
    """run subcommand accepts --clip-position and --clip-duration flags."""
    runner = CliRunner()
    result = runner.invoke(cli, [
        "-o", str(tmp_path),
        "run", "--count", "1", "--dry-run",
        "--clip-position", "random", "--clip-duration", "2.0",
    ])
    assert result.exit_code == 0


def test_run_passes_repeats_to_combine(tmp_path):
    """run subcommand passes parsed --repeats value to combine_loops."""
    from unittest.mock import patch, MagicMock
    import numpy as np
    import soundfile as sf

    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    # Create a test wav so process_file has something to work with
    t = np.linspace(0, 0.5, 11025, endpoint=False)
    audio = 0.5 * np.sin(2 * np.pi * 440 * t)
    sf.write(str(raw_dir / "test.wav"), audio, 22050)

    with patch("dodgylegally.combine.combine_loops") as mock_combine, \
         patch("dodgylegally.sources.get_source") as mock_get_source:
        # Set up mock source that returns a clip
        mock_source = MagicMock()
        mock_source.name = "youtube"
        mock_source.search.return_value = [MagicMock()]
        mock_clip = MagicMock()
        mock_clip.path = raw_dir / "test.wav"
        mock_source.download.return_value = mock_clip
        mock_get_source.return_value = mock_source

        mock_combine.return_value = None

        runner = CliRunner()
        result = runner.invoke(cli, [
            "-o", str(tmp_path),
            "run", "--count", "1", "--repeats", "5-6",
        ])
        assert result.exit_code == 0, result.output
        mock_combine.assert_called_once()
        call_kwargs = mock_combine.call_args
        # repeats should be (5, 6), not the default (3, 4)
        assert call_kwargs[1].get("repeats") == (5, 6) or \
               (len(call_kwargs[0]) > 2 and call_kwargs[0][2] == (5, 6))
