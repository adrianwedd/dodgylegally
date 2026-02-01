"""Metadata sidecar system — JSON companion files for every audio sample."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def sidecar_path(audio_path: Path) -> Path:
    """Return the .json sidecar path for an audio file."""
    return audio_path.with_suffix(".json")


def write_sidecar(audio_path: Path, metadata: dict) -> Path:
    """Write a JSON sidecar alongside an audio file.

    Adds a 'created_at' timestamp if not already present.
    Returns the path to the sidecar file.
    """
    path = sidecar_path(Path(audio_path))
    data = dict(metadata)
    if "created_at" not in data:
        data["created_at"] = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(data, indent=2, default=str))
    return path


def read_sidecar(audio_path: Path) -> dict:
    """Read a JSON sidecar for an audio file. Returns empty dict if none exists."""
    path = sidecar_path(Path(audio_path))
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def merge_sidecar(audio_path: Path, new_metadata: dict) -> dict:
    """Merge new metadata into an existing sidecar without overwriting.

    Existing keys are preserved. New keys are added.
    Returns the merged metadata.
    """
    existing = read_sidecar(audio_path)
    merged = {**existing, **{k: v for k, v in new_metadata.items() if k not in existing}}
    path = sidecar_path(Path(audio_path))
    path.write_text(json.dumps(merged, indent=2, default=str))
    return merged


def sidecar_from_clip(clip) -> dict:
    """Create metadata dict from a DownloadedClip."""
    result = clip.source_result
    meta = {
        "source": result.source,
        "title": result.title,
        "url": result.url,
        "duration_s": result.duration_s,
        "clip_duration_ms": clip.duration_ms,
    }
    meta.update(result.metadata)
    return meta
