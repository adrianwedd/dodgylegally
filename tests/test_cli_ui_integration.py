"""Tests for --verbose and --quiet CLI flags and ui integration in cli.py."""

from click.testing import CliRunner


def test_cli_has_verbose_flag():
    """CLI group accepts --verbose flag."""
    from dodgylegally.cli import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["--verbose", "search", "--count", "1"])
    assert result.exit_code == 0


def test_cli_has_quiet_flag():
    """CLI group accepts --quiet flag."""
    from dodgylegally.cli import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["--quiet", "search", "--count", "1"])
    assert result.exit_code == 0


def test_verbose_and_quiet_mutually_exclusive():
    """Cannot pass both --verbose and --quiet."""
    from dodgylegally.cli import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["--verbose", "--quiet", "search", "--count", "1"])
    assert result.exit_code != 0


def test_quiet_suppresses_search_stderr():
    """In quiet mode, search subcommand still produces phrase output."""
    from dodgylegally.cli import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["--quiet", "search", "--count", "2"])
    assert result.exit_code == 0
    # stdout should have the phrases
    assert len(result.output.strip().splitlines()) == 2
