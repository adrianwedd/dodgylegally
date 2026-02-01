"""Built-in arrangement strategies."""

from __future__ import annotations

import json
from pathlib import Path


def _read_analysis(filepath: str) -> dict | None:
    """Read the analysis block from a file's JSON sidecar."""
    sidecar = Path(filepath).with_suffix(".json")
    if not sidecar.exists():
        return None
    try:
        data = json.loads(sidecar.read_text())
        return data.get("analysis")
    except (json.JSONDecodeError, KeyError):
        return None


class SequentialStrategy:
    """Keep files in their original (sorted) order."""

    @property
    def name(self) -> str:
        return "sequential"

    def arrange(self, files: list[str], **kwargs) -> list[str]:
        return sorted(files)


class LoudnessStrategy:
    """Order files by LUFS loudness."""

    @property
    def name(self) -> str:
        return "loudness"

    def arrange(self, files: list[str], **kwargs) -> list[str]:
        descending = kwargs.get("descending", False)

        def _lufs(f: str) -> float:
            analysis = _read_analysis(f)
            if analysis and "loudness_lufs" in analysis:
                return analysis["loudness_lufs"]
            return -70.0  # unknown = very quiet

        return sorted(files, key=_lufs, reverse=descending)


class TempoStrategy:
    """Group files by similar BPM."""

    @property
    def name(self) -> str:
        return "tempo"

    def arrange(self, files: list[str], **kwargs) -> list[str]:
        def _bpm(f: str) -> float:
            analysis = _read_analysis(f)
            if analysis and analysis.get("bpm"):
                return analysis["bpm"]
            return 0.0

        return sorted(files, key=_bpm)


class KeyCompatibleStrategy:
    """Group files by harmonically compatible keys.

    Uses the circle of fifths distance to sort keys so that
    related keys (e.g., C major / A minor) are adjacent.
    """

    # Circle of fifths ordering for major keys
    _CIRCLE = ["C", "G", "D", "A", "E", "B", "F#", "C#", "G#", "D#", "A#", "F"]

    # Relative minor for each major key
    _RELATIVE_MINOR = {
        "C": "A", "G": "E", "D": "B", "A": "F#", "E": "C#", "B": "G#",
        "F#": "D#", "C#": "A#", "G#": "F", "D#": "C", "A#": "G", "F": "D",
    }

    @property
    def name(self) -> str:
        return "key_compatible"

    def _key_sort_value(self, key_str: str | None) -> float:
        """Map a key string to a sort value on the circle of fifths."""
        if not key_str:
            return 99.0  # unknown keys last

        parts = key_str.split()
        root = parts[0]
        mode = parts[1] if len(parts) > 1 else "major"

        # For minor keys, map to their relative major position
        if mode == "minor":
            for major, minor in self._RELATIVE_MINOR.items():
                if minor == root:
                    root = major
                    break
            # Add a small offset so minor sorts just after its relative major
            try:
                return self._CIRCLE.index(root) + 0.5
            except ValueError:
                return 99.0

        try:
            return float(self._CIRCLE.index(root))
        except ValueError:
            return 99.0

    def arrange(self, files: list[str], **kwargs) -> list[str]:
        def _key_val(f: str) -> float:
            analysis = _read_analysis(f)
            if analysis and analysis.get("key"):
                return self._key_sort_value(analysis["key"])
            return 99.0

        return sorted(files, key=_key_val)


class LayeredStrategy:
    """Return files grouped for layered overlay (no reordering, just grouping)."""

    @property
    def name(self) -> str:
        return "layered"

    def arrange(self, files: list[str], **kwargs) -> list[str]:
        # Layered just returns all files — the combine step handles overlay logic
        return sorted(files)
