"""Tests for multi-source weighted selection."""

import pytest


def test_parse_source_weight_simple():
    """Parse 'youtube:7' into ('youtube', 7)."""
    from dodgylegally.sources import parse_source_weight

    name, weight = parse_source_weight("youtube:7")
    assert name == "youtube"
    assert weight == 7


def test_parse_source_weight_no_weight():
    """Parse 'youtube' (no weight) defaults to weight 1."""
    from dodgylegally.sources import parse_source_weight

    name, weight = parse_source_weight("youtube")
    assert name == "youtube"
    assert weight == 1


def test_parse_source_weight_invalid():
    """Parse 'youtube:abc' raises ValueError."""
    from dodgylegally.sources import parse_source_weight

    with pytest.raises(ValueError):
        parse_source_weight("youtube:abc")


def test_weighted_selection_distribution():
    """weighted_select with weights [7, 3] produces roughly 70/30 split."""
    from dodgylegally.sources import weighted_select

    sources = [("youtube", 7), ("local", 3)]
    selections = [weighted_select(sources) for _ in range(1000)]
    youtube_count = selections.count("youtube")
    local_count = selections.count("local")
    # Allow generous margin: 55-85% youtube, 15-45% local
    assert 550 < youtube_count < 850, f"youtube: {youtube_count}"
    assert 150 < local_count < 450, f"local: {local_count}"


def test_weighted_select_single_source():
    """Single source always returns that source."""
    from dodgylegally.sources import weighted_select

    sources = [("youtube", 1)]
    assert weighted_select(sources) == "youtube"


def test_cli_run_accepts_source_flag():
    """CLI run subcommand accepts --source flag."""
    from click.testing import CliRunner
    from dodgylegally.cli import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["run", "--count", "2", "--source", "youtube:7", "--dry-run"])
    assert result.exit_code == 0


def test_cli_run_multiple_source_flags():
    """CLI run subcommand accepts multiple --source flags."""
    from click.testing import CliRunner
    from dodgylegally.cli import cli

    runner = CliRunner()
    result = runner.invoke(cli, [
        "run", "--count", "2",
        "--source", "youtube:7", "--source", "local:3",
        "--dry-run",
    ])
    assert result.exit_code == 0
