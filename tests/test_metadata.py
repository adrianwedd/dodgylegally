"""Tests for the metadata sidecar system."""

import json
from pathlib import Path
from datetime import datetime

import pytest


def test_write_sidecar_creates_json(tmp_path):
    """write_sidecar creates a .json file alongside the .wav."""
    from dodgylegally.metadata import write_sidecar

    wav_path = tmp_path / "sample.wav"
    wav_path.touch()
    meta = {"source": "youtube", "query": "rain thunder"}
    write_sidecar(wav_path, meta)

    json_path = tmp_path / "sample.json"
    assert json_path.exists()
    data = json.loads(json_path.read_text())
    assert data["source"] == "youtube"


def test_read_sidecar_returns_dict(tmp_path):
    """read_sidecar reads existing JSON sidecar."""
    from dodgylegally.metadata import write_sidecar, read_sidecar

    wav_path = tmp_path / "sample.wav"
    wav_path.touch()
    write_sidecar(wav_path, {"source": "local", "query": "*"})

    data = read_sidecar(wav_path)
    assert data["source"] == "local"


def test_read_sidecar_missing_returns_empty(tmp_path):
    """read_sidecar returns empty dict when no sidecar exists."""
    from dodgylegally.metadata import read_sidecar

    wav_path = tmp_path / "no_sidecar.wav"
    wav_path.touch()
    data = read_sidecar(wav_path)
    assert data == {}


def test_merge_sidecar_extends_metadata(tmp_path):
    """merge_sidecar adds new keys without overwriting existing ones."""
    from dodgylegally.metadata import write_sidecar, merge_sidecar, read_sidecar

    wav_path = tmp_path / "sample.wav"
    wav_path.touch()
    write_sidecar(wav_path, {"source": "youtube", "query": "rain"})
    merge_sidecar(wav_path, {"processed": True, "oneshot_path": "/out/sample_os.wav"})

    data = read_sidecar(wav_path)
    assert data["source"] == "youtube"  # preserved
    assert data["processed"] is True    # added


def test_write_sidecar_includes_timestamp(tmp_path):
    """write_sidecar adds a timestamp if not present."""
    from dodgylegally.metadata import write_sidecar, read_sidecar

    wav_path = tmp_path / "sample.wav"
    wav_path.touch()
    write_sidecar(wav_path, {"source": "youtube"})

    data = read_sidecar(wav_path)
    assert "created_at" in data
    # Should be parseable as ISO timestamp
    datetime.fromisoformat(data["created_at"])


def test_sidecar_from_downloaded_clip(tmp_path):
    """sidecar_from_clip creates metadata dict from a DownloadedClip."""
    from dodgylegally.metadata import sidecar_from_clip
    from dodgylegally.sources.base import SearchResult, DownloadedClip

    result = SearchResult("youtube", "Test Video", "https://yt.com/abc", 60.0, {"query": "test"})
    clip = DownloadedClip(path=tmp_path / "clip.wav", source_result=result, duration_ms=1000)

    meta = sidecar_from_clip(clip)
    assert meta["source"] == "youtube"
    assert meta["title"] == "Test Video"
    assert meta["url"] == "https://yt.com/abc"
    assert meta["clip_duration_ms"] == 1000
    assert meta["query"] == "test"


def test_read_sidecar_malformed_json_returns_empty(tmp_path):
    """read_sidecar returns empty dict when sidecar has malformed JSON."""
    from dodgylegally.metadata import read_sidecar

    wav_path = tmp_path / "corrupted.wav"
    wav_path.touch()
    json_path = tmp_path / "corrupted.json"
    json_path.write_text("{bad json content")

    data = read_sidecar(wav_path)
    assert data == {}


def test_sidecar_path_helper():
    """sidecar_path returns .json path for a .wav path."""
    from dodgylegally.metadata import sidecar_path

    assert sidecar_path(Path("/foo/bar.wav")) == Path("/foo/bar.json")
    assert sidecar_path(Path("/foo/bar.mp3")) == Path("/foo/bar.json")
