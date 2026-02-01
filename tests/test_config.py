"""Tests for the preset configuration system."""

import pytest
import yaml


def test_load_bundled_preset():
    """Loading a bundled preset by name returns a dict."""
    from dodgylegally.config import load_preset

    preset = load_preset("default")
    assert isinstance(preset, dict)


def test_load_bundled_preset_ambient():
    """The ambient preset has expected keys."""
    from dodgylegally.config import load_preset

    preset = load_preset("ambient")
    assert "count" in preset or "delay" in preset or "combine" in preset


def test_load_missing_preset_raises():
    """Loading a nonexistent preset raises FileNotFoundError."""
    from dodgylegally.config import load_preset

    with pytest.raises(FileNotFoundError, match="nonexistent"):
        load_preset("nonexistent")


def test_merge_preset_with_overrides():
    """CLI overrides take precedence over preset values."""
    from dodgylegally.config import merge_config

    preset = {"count": 20, "delay": 3.0}
    overrides = {"count": 5}
    result = merge_config(preset, overrides)
    assert result["count"] == 5
    assert result["delay"] == 3.0


def test_merge_config_ignores_none_overrides():
    """None values in overrides don't replace preset values."""
    from dodgylegally.config import merge_config

    preset = {"count": 20, "delay": 3.0}
    overrides = {"count": None, "delay": None}
    result = merge_config(preset, overrides)
    assert result["count"] == 20
    assert result["delay"] == 3.0


def test_load_user_preset(tmp_path):
    """Loading a preset from a user directory works."""
    from dodgylegally.config import load_preset

    preset_file = tmp_path / "custom.yaml"
    preset_file.write_text(yaml.dump({"count": 42, "delay": 1.5}))
    preset = load_preset("custom", search_dirs=[tmp_path])
    assert preset["count"] == 42
    assert preset["delay"] == 1.5


def test_list_presets_includes_bundled():
    """list_presets returns at least the bundled preset names."""
    from dodgylegally.config import list_presets

    names = list_presets()
    assert "default" in names


def test_cli_run_preset_flag():
    """CLI run subcommand accepts --preset flag."""
    from click.testing import CliRunner
    from dodgylegally.cli import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["run", "--count", "1", "--preset", "default", "--dry-run"])
    assert result.exit_code == 0
