"""Arrangement templates — YAML-defined section-based compositions."""

from __future__ import annotations

import glob
import os
import random
from pathlib import Path

import yaml
from pydub import AudioSegment

from dodgylegally.strategies import get_strategy


def _bundled_dir() -> Path:
    """Return the path to bundled templates."""
    return Path(__file__).resolve().parent.parent / "templates"


def _user_dir() -> Path:
    """Return the user templates directory."""
    return Path.home() / ".config" / "dodgylegally" / "templates"


def load_template(name: str, search_dirs: list[Path] | None = None) -> dict:
    """Load a template by name from bundled or user directories.

    Raises FileNotFoundError if the template doesn't exist.
    """
    dirs = search_dirs or [_user_dir(), _bundled_dir()]

    for d in dirs:
        path = d / f"{name}.yaml"
        if path.exists():
            return yaml.safe_load(path.read_text())

    available = list_templates(search_dirs)
    raise FileNotFoundError(
        f"Template '{name}' not found. Available: {', '.join(available)}"
    )


def list_templates(search_dirs: list[Path] | None = None) -> list[str]:
    """Return sorted list of available template names."""
    dirs = search_dirs or [_user_dir(), _bundled_dir()]
    names = set()
    for d in dirs:
        if d.exists():
            for f in d.glob("*.yaml"):
                names.add(f.stem)
    return sorted(names)


def apply_template(template: dict, loop_dir: str, output_path: str,
                   repeats: tuple[int, int] = (3, 4)) -> str:
    """Apply a template to loop files and produce a combined output.

    Each section uses its declared strategy to order a subset of files,
    then concatenates them (with repeats) up to the section's duration.

    Files are distributed across sections round-robin style. If there
    are fewer files than sections, files are reused.
    """
    wav_files = sorted(glob.glob(os.path.join(loop_dir, "*.wav")))
    if not wav_files:
        # Create a silent placeholder
        silence = AudioSegment.silent(duration=1000)
        silence.export(output_path, format="wav")
        return output_path

    sections = template.get("sections", [])
    if not sections:
        sections = [{"name": "default", "strategy": "sequential", "duration_s": 10}]

    # Distribute files across sections
    file_groups = _distribute_files(wav_files, len(sections))

    combined = AudioSegment.empty()

    for i, section in enumerate(sections):
        strategy_name = section.get("strategy", "sequential")
        duration_s = section.get("duration_s", 8)
        kwargs = section.get("kwargs", {})
        target_ms = int(duration_s * 1000)

        # Get files for this section (may be empty if few files)
        section_files = file_groups[i] if i < len(file_groups) else wav_files

        if not section_files:
            section_files = wav_files  # fallback: use all files

        # Apply strategy
        strategy = get_strategy(strategy_name)
        ordered = strategy.arrange(section_files, **kwargs)

        # Build section audio up to target duration
        section_audio = AudioSegment.empty()
        for filepath in ordered:
            if len(section_audio) >= target_ms:
                break
            sound = AudioSegment.from_file(filepath, format="wav")
            repeat_count = random.randint(repeats[0], repeats[1])
            section_audio += sound * repeat_count

        # Trim to target duration
        if len(section_audio) > target_ms:
            section_audio = section_audio[:target_ms]

        combined += section_audio

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    combined.export(output_path, format="wav")
    return output_path


def _distribute_files(files: list[str], n_groups: int) -> list[list[str]]:
    """Distribute files across n groups round-robin."""
    groups: list[list[str]] = [[] for _ in range(n_groups)]
    for i, f in enumerate(files):
        groups[i % n_groups].append(f)
    return groups
