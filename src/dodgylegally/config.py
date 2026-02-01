"""Preset configuration loading and merging."""

from __future__ import annotations

from pathlib import Path

import yaml


_BUNDLED_DIR = Path(__file__).parent / "presets"


def load_preset(name: str, search_dirs: list[Path] | None = None) -> dict:
    """Load a preset by name from bundled presets or user directories.

    Searches user directories first, then bundled presets.
    Raises FileNotFoundError if preset not found.
    """
    dirs = list(search_dirs or []) + [_BUNDLED_DIR]
    for d in dirs:
        path = Path(d) / f"{name}.yaml"
        if path.exists():
            with open(path) as f:
                return yaml.safe_load(f) or {}
    raise FileNotFoundError(
        f"Preset '{name}' not found. Searched: {', '.join(str(d) for d in dirs)}"
    )


def merge_config(preset: dict, overrides: dict) -> dict:
    """Merge preset config with CLI overrides. None values in overrides are ignored."""
    result = dict(preset)
    for key, value in overrides.items():
        if value is not None:
            result[key] = value
    return result


def list_presets(search_dirs: list[Path] | None = None) -> list[str]:
    """List available preset names from bundled and user directories."""
    dirs = list(search_dirs or []) + [_BUNDLED_DIR]
    names = set()
    for d in dirs:
        d = Path(d)
        if d.is_dir():
            for f in d.glob("*.yaml"):
                names.add(f.stem)
    return sorted(names)
